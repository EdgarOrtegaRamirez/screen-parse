"""Screenshot image parser — analyzes screenshots to detect UI elements."""

from __future__ import annotations

import logging
import pathlib
import time
from typing import Any

import numpy as np
from PIL import Image

from screenparse.element import BoundingBox, ElementType, ParseResult, UIElement
from screenparse.utils import (
    generate_element_id,
    is_solid_region,
    sanitize_path,
    validate_extension,
)

logger = logging.getLogger(__name__)

# Element type heuristics
BUTTON_COLOR_PATTERNS = [
    # Blue tones (common for primary buttons)
    lambda r, g, b: 30 <= r <= 100 and 100 <= g <= 180 and 180 <= b <= 255,
    # Green tones (success/confirm buttons)
    lambda r, g, b: 30 <= r <= 100 and 150 <= g <= 220 and 30 <= b <= 100,
    # Red tones (danger/delete buttons)
    lambda r, g, b: 180 <= r <= 255 and 30 <= g <= 80 and 30 <= b <= 80,
]

MIN_BUTTON_AREA = 500
MIN_TEXT_AREA = 200
MAX_ELEMENT_AREA = 1_000_000  # Cap to avoid detecting entire screen as one element


class ImageParser:
    """Parses screenshot images to detect UI elements."""

    def __init__(
        self,
        min_element_area: int = 100,
        color_threshold: float = 0.15,
        max_elements: int = 200,
    ) -> None:
        self.min_element_area = min_element_area
        self.color_threshold = color_threshold
        self.max_elements = max_elements

    def parse(
        self,
        image_path: str | pathlib.Path,
        verbose: bool = False,
    ) -> ParseResult:
        """Parse a screenshot image and extract UI elements.

        Args:
            image_path: Path to the screenshot image.
            verbose: If True, include debug information.

        Returns:
            ParseResult with detected UI elements.
        """
        start_time = time.perf_counter()

        path = sanitize_path(image_path)
        validate_extension(path, {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif"})

        logger.info("Parsing image: %s", path)

        try:
            img = Image.open(path)
            img.load()  # Force load to catch corrupt files early
        except Exception as e:
            raise ValueError(f"Failed to open image: {e}")

        width, height = img.size
        logger.info("Image dimensions: %dx%d", width, height)

        # Convert to RGB for analysis
        rgb_img = img.convert("RGB") if img.mode == "RGBA" else img.convert("RGB")

        pixels = np.array(rgb_img)

        # Detect UI elements using region analysis
        elements = self._detect_elements(pixels, width, height, verbose)

        # Sort elements by position (top-to-bottom, left-to-right)
        elements.sort(key=lambda e: (e.bbox.top, e.bbox.left))

        # Limit elements
        if len(elements) > self.max_elements:
            elements = elements[: self.max_elements]
            logger.warning(
                "Limited to %d elements (max: %d)", self.max_elements, len(elements)
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        result = ParseResult(
            elements=elements,
            source_type="image",
            source_path=str(path),
            image_width=width,
            image_height=height,
            parse_time_ms=elapsed_ms,
        )

        logger.info(
            "Parsed %d elements in %.2f ms", len(elements), elapsed_ms
        )

        return result

    def _detect_elements(
        self,
        pixels: np.ndarray,
        width: int,
        height: int,
        verbose: bool = False,
    ) -> list[UIElement]:
        """Detect UI elements in the image using color region analysis.

        Uses connected component analysis on color-differentiated regions.
        """
        elements: list[UIElement] = []

        # Step 1: Find color boundaries to identify regions
        regions = self._find_color_regions(pixels)

        # Step 2: Classify each region
        for region in regions:
            if len(elements) >= self.max_elements:
                break

            bbox = region["bbox"]
            region_pixels = region["pixels"]

            # Convert numpy array to flat Python list for safe indexing
            if hasattr(region_pixels, "tolist"):
                region_pixels = region_pixels.tolist()
            # Flatten nested lists
            if region_pixels and isinstance(region_pixels[0], list):
                flat: list[int] = []
                for row in region_pixels:
                    if isinstance(row, int):
                        flat.append(row)
                    else:
                        flat.extend(row)
                region_pixels = flat

            # Skip regions that are too small or too large
            if bbox.area < self.min_element_area:
                continue
            if bbox.area > MAX_ELEMENT_AREA:
                continue

            # Classify the region
            element_type = self._classify_region(
                region_pixels, bbox, region["color"]
            )
            confidence = self._estimate_confidence(
                region_pixels, element_type
            )

            # Extract text estimate from region
            text = self._estimate_region_text(
                region_pixels, bbox
            )

            element = UIElement(
                element_id=generate_element_id(len(elements), "img"),
                element_type=element_type,
                text=text,
                bbox=bbox,
                confidence=confidence,
                metadata={
                    "dominant_color": region["color"],
                    "pixel_count": len(region_pixels),
                    "source": "image_analysis",
                },
            )

            elements.append(element)

        # Step 3: Post-process — merge overlapping small elements
        elements = self._merge_overlapping(elements)

        return elements

    def _find_color_regions(
        self, pixels: np.ndarray
    ) -> list[dict[str, Any]]:
        """Find distinct color regions in the image using connected components.

        Uses a simple flood-fill approach with color quantization.
        """
        regions: list[dict[str, Any]] = []

        # Quantize colors to reduce complexity
        quantized = (pixels // 32) * 32
        quantized = np.clip(quantized, 0, 255)

        # Get unique colors and their positions
        h, w = quantized.shape[:2]
        reshaped = quantized.reshape(-1, 3)

        # Find unique colors
        unique_colors, inverse = np.unique(
            reshaped, axis=0, return_inverse=True
        )

        # Group by color
        color_positions: dict[tuple, list[tuple[int, int]]] = {}
        for idx, pos_idx in enumerate(inverse):
            color = tuple(unique_colors[pos_idx])
            if color not in color_positions:
                color_positions[color] = []
            y, x = divmod(idx, w)
            color_positions[color].append((y, x))

        # Find connected components for each color
        visited = np.zeros((h, w), dtype=bool)

        for color, positions in color_positions.items():
            if len(positions) < self.min_element_area:
                continue

            # Build a mask for this color
            mask = np.zeros((h, w), dtype=bool)
            for y, x in positions:
                if not visited[y, x]:
                    mask[y, x] = True

            # Find connected components on the mask
            components = self._connected_components(mask)

            for comp in components:
                ys, xs = comp
                if len(ys) < self.min_element_area:
                    continue

                # Calculate bounding box
                y_min, y_max = ys.min(), ys.max()
                x_min, x_max = xs.min(), xs.max()

                bbox = BoundingBox(
                    x=int(x_min),
                    y=int(y_min),
                    width=int(x_max - x_min + 1),
                    height=int(y_max - y_min + 1),
                )

                # Extract region pixels from original image
                region_mask = np.zeros((h, w), dtype=bool)
                region_mask[ys, xs] = True
                region_pixels = pixels[region_mask]

                regions.append({
                    "bbox": bbox,
                    "pixels": region_pixels,
                    "color": color,
                    "pixel_count": len(ys),
                })

                visited[ys, xs] = True

        # Sort by pixel count (largest first)
        regions.sort(key=lambda r: r["pixel_count"], reverse=True)

        return regions

    def _connected_components(
        self, mask: np.ndarray
    ) -> list[np.ndarray]:
        """Find connected components in a binary mask using flood fill.

        Returns list of (y_coords, x_coords) arrays for each component.
        """
        h, w = mask.shape
        visited = np.zeros((h, w), dtype=bool)
        components: list[np.ndarray] = []

        for start_y in range(h):
            for start_x in range(w):
                if visited[start_y, start_x] or not mask[start_y, start_x]:
                    continue

                # BFS flood fill
                component_ys: list[int] = []
                component_xs: list[int] = []
                queue: list[tuple[int, int]] = [(start_y, start_x)]

                while queue:
                    cy, cx = queue.pop(0)
                    if visited[cy, cx]:
                        continue
                    if cy < 0 or cy >= h or cx < 0 or cx >= w:
                        continue
                    if not mask[cy, cx]:
                        continue

                    visited[cy, cx] = True
                    component_ys.append(cy)
                    component_xs.append(cx)

                    # Add neighbors
                    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx]:
                            queue.append((ny, nx))

                if component_ys:
                    components.append(
                        np.array([component_ys, component_xs])
                    )

        return components

    def _classify_region(
        self,
        pixels: list[int] | np.ndarray,
        bbox: BoundingBox,
        dominant_color: tuple[int, int, int],
    ) -> ElementType:
        """Classify a region as a specific UI element type.

        Uses color patterns, aspect ratio, and text density heuristics.
        """
        if len(pixels) == 0:
            return ElementType.UNKNOWN

        aspect_ratio = bbox.aspect_ratio
        # Handle both list and numpy array
        pixel_list = pixels if isinstance(pixels, list) else pixels.tolist()
        is_solid = is_solid_region(pixel_list, self.color_threshold)

        r, g, b = dominant_color

        # Check for button-like colors
        for pattern in BUTTON_COLOR_PATTERNS:
            if pattern(r, g, b):
                return ElementType.BUTTON

        # Small, square-ish regions with solid color are likely icons
        if (
            bbox.area < 2000
            and 0.5 <= aspect_ratio <= 2.0
            and is_solid
        ):
            return ElementType.ICON

        # Wide, short regions are likely text lines
        if aspect_ratio < 0.5 and bbox.area > MIN_TEXT_AREA:
            return ElementType.TEXT

        # Tall, narrow regions could be input fields or list items
        if aspect_ratio > 3.0 and bbox.area > MIN_TEXT_AREA:
            return ElementType.INPUT

        # Medium-sized solid regions are likely buttons or containers
        if is_solid and MIN_BUTTON_AREA <= bbox.area <= 50000:
            return ElementType.BUTTON

        # Large solid regions are likely containers/backgrounds
        if is_solid and bbox.area > 50000:
            return ElementType.CONTAINER

        # Default: check text density
        if len(pixels) >= 12:
            text_ratio = sum(
                1 for i in range(0, min(len(pixels), 100), 3)
                if abs(pixels[i] - pixels[i+1]) > 40
                or abs(pixels[i] - pixels[i+2]) > 40
                or abs(pixels[i+1] - pixels[i+2]) > 40
            ) / (len(pixels) // 3)

            if text_ratio > 0.3:
                return ElementType.TEXT

        return ElementType.IMAGE

    def _estimate_confidence(
        self, pixels: list[int] | np.ndarray, element_type: ElementType
    ) -> float:
        """Estimate confidence in the classification."""
        if len(pixels) < 10:
            return 0.3

        pixel_list = pixels if isinstance(pixels, list) else pixels.tolist()
        is_solid = is_solid_region(pixel_list, self.color_threshold)

        base_confidence = 0.7

        # Solid regions are more confidently classified
        if is_solid:
            base_confidence += 0.15

        # Larger regions give more data for classification
        area_factor = min(len(pixels) / 1000, 0.15)

        return min(base_confidence + area_factor, 0.95)

    def _estimate_region_text(
        self, pixels: list[int] | np.ndarray, bbox: BoundingBox
    ) -> str:
        """Estimate text content from a region.

        This is a lightweight heuristic — for production use, integrate
        with an OCR engine like Tesseract.
        """
        if len(pixels) < 50:
            return ""

        # Sample the region for text-like patterns
        sample_size = min(len(pixels), 500)
        step = max(1, len(pixels) // sample_size)
        sample = pixels[::step][:sample_size]

        # Count high-contrast pixels (likely text)
        text_pixels = 0
        total = 0

        for i in range(0, len(sample) - 2, 3):
            r, g, b = sample[i], sample[i + 1], sample[i + 2]
            total += 1

            # High saturation or high contrast suggests text
            max_c = max(r, g, b)
            min_c = min(r, g, b)
            if max_c - min_c > 80:
                text_pixels += 1

        if total == 0:
            return ""

        text_ratio = text_pixels / total

        # Estimate text length based on area and text ratio
        estimated_chars = int(bbox.area * text_ratio * 0.01)
        estimated_chars = max(0, min(estimated_chars, 50))

        if estimated_chars == 0:
            return ""

        # Return a placeholder with estimated length
        return f"[text: ~{estimated_chars} chars]"

    def _merge_overlapping(
        self, elements: list[UIElement]
    ) -> list[UIElement]:
        """Merge overlapping small elements into parent containers.

        Small overlapping elements are likely parts of a larger UI element.
        """
        if len(elements) <= 1:
            return elements

        # Sort by area (smallest first)
        sorted_elements = sorted(elements, key=lambda e: e.bbox.area)

        merged_ids: set[str] = set()

        for i, elem in enumerate(sorted_elements):
            if elem.element_id in merged_ids:
                continue

            # Check if this element overlaps with any larger element
            for other in sorted_elements[i + 1 :]:
                if other.element_id in merged_ids:
                    continue
                if elem.bbox.overlaps(other.bbox) and elem.bbox.area < other.bbox.area * 0.5:
                        # Merge into parent
                        other.children.append(elem)
                        merged_ids.add(elem.element_id)
                        break

        # Filter out merged elements
        result = [e for e in elements if e.element_id not in merged_ids]

        return result
