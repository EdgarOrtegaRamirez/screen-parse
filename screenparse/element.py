"""UI element data models for screen parsing."""

from __future__ import annotations

import dataclasses
import enum
from typing import Any


def _make_serializable(obj: Any) -> Any:
    """Recursively convert numpy types to Python native types for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_serializable(item) for item in obj]
    # Handle numpy types
    try:
        import numpy as np

        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, (np.ndarray,)):
            return obj.tolist()
    except ImportError:
        pass
    return obj


class ElementType(str, enum.Enum):
    """Types of UI elements that can be detected."""

    BUTTON = "button"
    TEXT = "text"
    IMAGE = "image"
    INPUT = "input"
    ICON = "icon"
    CONTAINER = "container"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    LIST = "list"
    LINK = "link"
    UNKNOWN = "unknown"


@dataclasses.dataclass
class BoundingBox:
    """A bounding box with x, y, width, height."""

    x: int
    y: int
    width: int
    height: int

    @property
    def left(self) -> int:
        return self.x

    @property
    def top(self) -> int:
        return self.y

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2.0

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2.0

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def aspect_ratio(self) -> float:
        if self.width == 0:
            return 0.0
        return self.height / self.width

    def contains(self, point_x: int, point_y: int) -> bool:
        """Check if a point is inside this bounding box."""
        return self.left <= point_x < self.right and self.top <= point_y < self.bottom

    def overlaps(self, other: BoundingBox) -> bool:
        """Check if this box overlaps with another box."""
        return not (
            self.right <= other.left
            or self.left >= other.right
            or self.bottom <= other.top
            or self.top >= other.bottom
        )

    def intersection(self, other: BoundingBox) -> BoundingBox | None:
        """Return the intersection box, or None if no overlap."""
        if not self.overlaps(other):
            return None
        return BoundingBox(
            x=max(self.left, other.left),
            y=max(self.top, other.top),
            width=min(self.right, other.right) - max(self.left, other.left),
            height=min(self.bottom, other.bottom) - max(self.top, other.top),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "left": self.left,
            "top": self.top,
            "right": self.right,
            "bottom": self.bottom,
            "center_x": round(self.center_x, 2),
            "center_y": round(self.center_y, 2),
            "area": self.area,
            "aspect_ratio": round(self.aspect_ratio, 2),
        }


@dataclasses.dataclass
class UIElement:
    """A single UI element detected on screen."""

    element_id: str
    element_type: ElementType
    text: str = ""
    bbox: BoundingBox = dataclasses.field(default_factory=lambda: BoundingBox(0, 0, 0, 0))
    confidence: float = 1.0
    accessibility_role: str = ""
    accessibility_label: str = ""
    is_visible: bool = True
    is_enabled: bool = True
    children: list[UIElement] = dataclasses.field(default_factory=list)
    metadata: dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary for JSON serialization."""
        result: dict[str, Any] = {
            "id": self.element_id,
            "type": self.element_type.value,
            "text": self.text,
            "bbox": self.bbox.to_dict(),
            "confidence": self.confidence,
            "visible": self.is_visible,
            "enabled": self.is_enabled,
        }
        if self.accessibility_role:
            result["accessibility_role"] = self.accessibility_role
        if self.accessibility_label:
            result["accessibility_label"] = self.accessibility_label
        if self.children:
            result["children"] = [child.to_dict() for child in self.children]
        if self.metadata:
            result["metadata"] = _make_serializable(self.metadata)
        return result


@dataclasses.dataclass
class ParseResult:
    """Result of parsing a screenshot or accessibility dump."""

    elements: list[UIElement]
    source_type: str  # "image" or "accessibility"
    source_path: str
    image_width: int = 0
    image_height: int = 0
    parse_time_ms: float = 0.0
    warnings: list[str] = dataclasses.field(default_factory=list)

    @property
    def element_count(self) -> int:
        """Total number of elements including nested."""
        total = len(self.elements)
        for elem in self.elements:
            total += len(elem.children)
        return total

    @property
    def top_level_elements(self) -> int:
        """Number of top-level elements (not including nested children)."""
        return len(self.elements)

    @property
    def type_counts(self) -> dict[str, int]:
        """Count of elements by type."""
        counts: dict[str, int] = {}
        for elem in self.elements:
            key = elem.element_type.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary for JSON serialization."""
        return {
            "source_type": self.source_type,
            "source_path": self.source_path,
            "image_dimensions": {
                "width": self.image_width,
                "height": self.image_height,
            },
            "parse_time_ms": round(self.parse_time_ms, 2),
            "element_count": self.element_count,
            "top_level_elements": len(self.elements),
            "type_counts": self.type_counts,
            "warnings": self.warnings,
            "elements": [elem.to_dict() for elem in self.elements],
        }
