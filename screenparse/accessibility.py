"""Accessibility data parsers for Android XML and iOS plist formats."""

from __future__ import annotations

import logging
import pathlib
import re
import time
import xml.etree.ElementTree as ET

from screenparse.element import BoundingBox, ElementType, ParseResult, UIElement
from screenparse.utils import (
    generate_element_id,
    sanitize_path,
)

logger = logging.getLogger(__name__)


class AccessibilityParser:
    """Parses accessibility dump files to extract UI element information."""

    ANDROID_TAG_MAP = {
        "android.widget.Button": ElementType.BUTTON,
        "android.widgetImageButton": ElementType.BUTTON,
        "android.widget.Toolbar": ElementType.BUTTON,
        "android.widget.TextView": ElementType.TEXT,
        "android.widget.EditText": ElementType.INPUT,
        "android.widget.SearchView": ElementType.INPUT,
        "android.widget.AutoCompleteTextView": ElementType.INPUT,
        "android.widget.ImageView": ElementType.IMAGE,
        "android.widget.ImageButton": ElementType.ICON,
        "android.widget.CheckBox": ElementType.CHECKBOX,
        "android.widget.RadioButton": ElementType.RADIO,
        "android.widget.ScrollView": ElementType.CONTAINER,
        "android.widget.FrameLayout": ElementType.CONTAINER,
        "android.widget.LinearLayout": ElementType.CONTAINER,
        "android.widget.RelativeLayout": ElementType.CONTAINER,
        "android.widget.RecyclerView": ElementType.LIST,
        "android.widget.ListView": ElementType.LIST,
        "android.widget.GridView": ElementType.LIST,
        "android.widget.TabHost": ElementType.CONTAINER,
        "android.widget.Switch": ElementType.BUTTON,
        "android.widget.SeekBar": ElementType.INPUT,
        "android.widget.ProgressBar": ElementType.IMAGE,
        "android.widget.WebView": ElementType.CONTAINER,
        "android.widget.CalendarView": ElementType.CONTAINER,
        "android.widget.Gallery": ElementType.LIST,
        "android.widget.Spinner": ElementType.INPUT,
        "android.widget.TimePicker": ElementType.CONTAINER,
        "android.widget.DatePicker": ElementType.CONTAINER,
    }

    DEFAULT_TYPE = ElementType.UNKNOWN

    def parse(
        self,
        accessibility_path: str | pathlib.Path,
        include_hidden: bool = False,
        include_content_description: bool = True,
    ) -> ParseResult:
        """Parse an Android XML accessibility dump."""
        start_time = time.perf_counter()
        path = sanitize_path(accessibility_path)

        logger.info("Parsing accessibility dump: %s", path)

        try:
            tree = ET.parse(str(path))
            root = tree.getroot()
        except ET.ParseError as e:
            raise ValueError(f"Failed to parse XML: {e}")

        # Collect all elements in a flat list
        elements: list[UIElement] = []
        self._collect_flat(root, elements, include_hidden, include_content_description)

        # Build parent-child hierarchy based on spatial containment
        elements = self._build_hierarchy(elements)

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        max_width = max((e.bbox.right for e in elements), default=0)
        max_height = max((e.bbox.bottom for e in elements), default=0)

        result = ParseResult(
            elements=elements,
            source_type="accessibility",
            source_path=str(path),
            image_width=max_width,
            image_height=max_height,
            parse_time_ms=elapsed_ms,
        )

        logger.info("Parsed %d elements in %.2f ms", len(elements), elapsed_ms)
        return result

    # Layout containers that should be skipped during collection
    # (they wrap UI elements but aren't themselves interactive)
    LAYOUT_CONTAINERS = {
        "android.widget.FrameLayout",
        "android.widget.LinearLayout",
        "android.widget.RelativeLayout",
        "android.widget.ScrollView",
        "android.widget.ScrollView",
        "android.widget.WebView",
        "android.widget.TabHost",
        "android.widget.CalendarView",
        "android.widget.TimePicker",
        "android.widget.DatePicker",
    }

    def _collect_flat(
        self,
        node: ET.Element,
        elements: list[UIElement],
        include_hidden: bool,
        include_content_description: bool,
    ) -> None:
        """Recursively collect all UI elements into a flat list.

        Skips intermediate layout containers — only collects actual
        UI widget elements (buttons, text, inputs, etc.).
        """
        node_class = node.get("class", "")

        # Skip layout containers — recurse into them without collecting
        if node_class in self.LAYOUT_CONTAINERS:
            for child in node:
                element = self._node_to_element(child, include_hidden, include_content_description)
                if element is not None:
                    elements.append(element)
                self._collect_flat(child, elements, include_hidden, include_content_description)
            return

        for child in node:
            child_class = child.get("class", "")
            # Don't collect layout containers — just recurse into them
            if child_class not in self.LAYOUT_CONTAINERS:
                element = self._node_to_element(child, include_hidden, include_content_description)
                if element is not None:
                    elements.append(element)
            # Always recurse (layout containers skip themselves but process children)
            self._collect_flat(child, elements, include_hidden, include_content_description)

    def _node_to_element(
        self,
        node: ET.Element,
        include_hidden: bool,
        include_content_description: bool,
    ) -> UIElement | None:
        """Convert a single XML node to a UIElement."""
        if not self._is_node_visible(node) and not include_hidden:
            return None

        bbox = self._extract_bbox(node) or BoundingBox(0, 0, 0, 0)
        element_type = self._infer_type(node)
        text = self._extract_text(node, include_content_description)
        accessibility_role = node.get("class", "") or node.tag
        accessibility_label = node.get("content-desc", "") if include_content_description else ""
        is_enabled = self._is_node_enabled(node)

        return UIElement(
            element_id="",  # Assigned during hierarchy building
            element_type=element_type,
            text=text,
            bbox=bbox,
            confidence=0.95,
            accessibility_role=accessibility_role,
            accessibility_label=accessibility_label,
            is_visible=self._is_node_visible(node),
            is_enabled=is_enabled,
            metadata={"source": "accessibility_xml", "view_class": node.tag},
        )

    def _is_node_visible(self, node: ET.Element) -> bool:
        visible_str = node.get("visible-to-user", "").lower()
        if visible_str == "true":
            return True
        if visible_str == "false":
            return False
        bounds = node.get("bounds")
        if bounds:
            bbox = self._parse_bounds_string(bounds)
            if bbox and bbox.width > 0 and bbox.height > 0:
                return True
        return False

    def _is_node_enabled(self, node: ET.Element) -> bool:
        enabled_str = node.get("enabled", "").lower()
        if enabled_str == "true":
            return True
        return enabled_str != "false"

    def _extract_bbox(self, node: ET.Element) -> BoundingBox | None:
        bounds = node.get("bounds")
        if not bounds:
            return None
        return self._parse_bounds_string(bounds)

    def _parse_bounds_string(self, bounds_str: str) -> BoundingBox:
        pattern = r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]"
        match = re.match(pattern, bounds_str)
        if not match:
            return BoundingBox(0, 0, 0, 0)
        x1, y1, x2, y2 = (int(v) for v in match.groups())
        return BoundingBox(
            x=min(x1, x2),
            y=min(y1, y2),
            width=abs(x2 - x1),
            height=abs(y2 - y1),
        )

    def _infer_type(self, node: ET.Element) -> ElementType:
        tag = node.tag
        # Check class attribute first (Android accessibility uses class attribute)
        node_class = node.get("class", "")
        if node_class in self.ANDROID_TAG_MAP:
            return self.ANDROID_TAG_MAP[node_class]
        # Fall back to tag name
        if tag in self.ANDROID_TAG_MAP:
            return self.ANDROID_TAG_MAP[tag]

        node_type = node.get("type", "").lower()
        if "button" in node_type:
            return ElementType.BUTTON
        if "text" in node_type or "label" in node_type:
            return ElementType.TEXT
        if "edit" in node_type or "input" in node_type:
            return ElementType.INPUT
        if "image" in node_type or "icon" in node_type:
            return ElementType.IMAGE
        if "check" in node_type:
            return ElementType.CHECKBOX
        if "radio" in node_type:
            return ElementType.RADIO
        if "list" in node_type or "recycler" in node_type:
            return ElementType.LIST
        if "container" in node_type or "layout" in node_type:
            return ElementType.CONTAINER

        content_desc = node.get("content-desc", "").lower()
        if any(w in content_desc for w in ("icon", "image", "picture")):
            return ElementType.IMAGE
        if any(w in content_desc for w in ("button", "click", "tap")):
            return ElementType.BUTTON

        return self.DEFAULT_TYPE

    def _extract_text(self, node: ET.Element, include_content_description: bool) -> str:
        text = node.get("text", "")
        if text and text != "null":
            return text
        if include_content_description:
            cd = node.get("content-desc", "")
            if cd and cd != "null":
                return cd
        return ""

    def _build_hierarchy(self, elements: list[UIElement]) -> list[UIElement]:
        """Assign IDs and build parent-child relationships.

        A child element is one whose bounding box is fully contained within
        a parent's box. We only nest elements that are significantly smaller
        (at least 3x area difference) to avoid over-nesting.

        Screen-frame containers (large containers covering the full screen)
        are excluded from results.
        """
        if not elements:
            return elements

        # Sort by area descending so parents are processed first
        elements.sort(key=lambda e: e.bbox.area, reverse=True)

        # Assign IDs
        for i, elem in enumerate(elements):
            elem.element_id = generate_element_id(i, "acc")

        # Identify screen-frame containers: full-screen bounds + container class
        screen_frame = None
        for elem in elements:
            if elem.bbox.width >= 1000 and elem.bbox.height >= 1800:
                # Check if it's a container type, not a regular UI element
                role = elem.accessibility_role.lower()
                if any(
                    c in role
                    for c in (
                        "framelayout",
                        "linearlayout",
                        "relativelayout",
                        "scrollview",
                        "webview",
                        "tabhost",
                        "container",
                    )
                ):
                    screen_frame = elem
                    break

        # Build hierarchy: each element finds its best parent
        for i, child in enumerate(elements):
            if child.bbox.area == 0:
                continue
            if screen_frame and child.element_id == screen_frame.element_id:
                continue
            for j, parent in enumerate(elements):
                if i == j:
                    continue
                if screen_frame and parent.element_id == screen_frame.element_id:
                    continue
                if parent.bbox.area == 0:
                    continue
                # Child must be fully contained within parent
                if (
                    child.bbox.x >= parent.bbox.x
                    and child.bbox.y >= parent.bbox.y
                    and child.bbox.right <= parent.bbox.right
                    and child.bbox.bottom <= parent.bbox.bottom
                    and parent.bbox.area > child.bbox.area * 3
                ):
                    parent.children.append(child)
                    break

        # Return top-level elements (excluding screen frame if found)
        child_ids = {c.element_id for e in elements for c in e.children}
        exclude_ids = child_ids | ({screen_frame.element_id} if screen_frame else set())
        top_level = [e for e in elements if e.element_id not in exclude_ids]
        top_level.sort(key=lambda e: (e.bbox.y, e.bbox.x))
        return top_level
