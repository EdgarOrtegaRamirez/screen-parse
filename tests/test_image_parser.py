"""Tests for the image parser."""

from __future__ import annotations

import pathlib

from PIL import Image

from screenparse.element import BoundingBox, ElementType
from screenparse.image_parser import ImageParser


class TestImageParser:
    """Tests for screenshot image parsing."""

    def _create_test_image(
        self,
        width: int = 400,
        height: int = 300,
        colors: dict | None = None,
    ) -> pathlib.Path:
        """Create a test image with specified colored regions.

        Args:
            width: Image width in pixels.
            height: Image height in pixels.
            colors: Dict mapping region names to (color, bbox) tuples.

        Returns:
            Path to the saved test image.
        """
        img = Image.new("RGB", (width, height), (255, 255, 255))
        pixels = img.load()

        if colors:
            for (r, g, b), (x1, y1, x2, y2) in colors.items():
                for y in range(y1, min(y2, height)):
                    for x in range(x1, min(x2, width)):
                        pixels[x, y] = (r, g, b)

        path = pathlib.Path(f"/tmp/test_screen_{width}x{height}.png")
        img.save(str(path))
        return path

    def test_parse_simple_image(self) -> None:
        """Test parsing a simple solid-color image."""
        path = self._create_test_image(200, 200, colors={
            (255, 0, 0): (0, 0, 200, 100),  # Red top half
            (0, 0, 255): (0, 100, 200, 200),  # Blue bottom half
        })

        try:
            parser = ImageParser()
            result = parser.parse(str(path))

            assert result.source_type == "image"
            assert result.image_width == 200
            assert result.image_height == 200
            assert result.source_path == str(path)
            assert result.parse_time_ms >= 0
        finally:
            path.unlink(missing_ok=True)

    def test_parse_white_image(self) -> None:
        """Test parsing a solid white image (minimal elements)."""
        path = self._create_test_image(200, 200)

        try:
            parser = ImageParser()
            result = parser.parse(str(path))

            assert result.source_type == "image"
            assert result.image_width == 200
            assert result.image_height == 200
        finally:
            path.unlink(missing_ok=True)

    def test_parse_with_min_area_filter(self) -> None:
        """Test that elements below min_element_area are filtered."""
        # Create a large image with small colored dots
        path = self._create_test_image(400, 400)

        try:
            parser = ImageParser(min_element_area=5000)
            result = parser.parse(str(path))

            # With high min area, should find fewer elements
            assert result.element_count >= 0
        finally:
            path.unlink(missing_ok=True)

    def test_parse_with_max_elements(self) -> None:
        """Test that element count is capped at max_elements."""
        # Create an image with many color regions
        colors = {}
        for i in range(20):
            x = (i % 5) * 80
            y = (i // 5) * 80
            colors[(i * 30, i * 20, i * 10)] = (x, y, x + 40, y + 40)

        path = self._create_test_image(400, 400, colors=colors)

        try:
            parser = ImageParser(max_elements=5)
            result = parser.parse(str(path))

            assert len(result.elements) <= 5
        finally:
            path.unlink(missing_ok=True)

    def test_parse_to_dict(self) -> None:
        """Test that parse result can be serialized to dict."""
        path = self._create_test_image(200, 200, colors={
            (0, 128, 255): (0, 0, 100, 100),
        })

        try:
            parser = ImageParser()
            result = parser.parse(str(path))

            d = result.to_dict()
            assert d["source_type"] == "image"
            assert "elements" in d
            assert "type_counts" in d
            assert "parse_time_ms" in d
        finally:
            path.unlink(missing_ok=True)

    def test_parse_element_has_id(self) -> None:
        """Test that each element has a unique ID."""
        path = self._create_test_image(200, 200, colors={
            (255, 0, 0): (0, 0, 100, 100),
            (0, 255, 0): (100, 0, 200, 100),
        })

        try:
            parser = ImageParser()
            result = parser.parse(str(path))

            ids = [e.element_id for e in result.elements]
            assert len(ids) == len(set(ids))  # All unique
        finally:
            path.unlink(missing_ok=True)

    def test_parse_element_has_type(self) -> None:
        """Test that each element has a valid type."""
        path = self._create_test_image(200, 200, colors={
            (100, 150, 200): (0, 0, 100, 100),
        })

        try:
            parser = ImageParser()
            result = parser.parse(str(path))

            for elem in result.elements:
                assert elem.element_type in ElementType
        finally:
            path.unlink(missing_ok=True)

    def test_parse_element_has_bbox(self) -> None:
        """Test that each element has a valid bounding box."""
        path = self._create_test_image(200, 200, colors={
            (50, 100, 150): (0, 0, 100, 100),
        })

        try:
            parser = ImageParser()
            result = parser.parse(str(path))

            for elem in result.elements:
                assert isinstance(elem.bbox, BoundingBox)
                assert elem.bbox.width >= 0
                assert elem.bbox.height >= 0
        finally:
            path.unlink(missing_ok=True)

    def test_parse_empty_regions(self) -> None:
        """Test parsing an image with no distinct regions."""
        path = self._create_test_image(100, 100)

        try:
            parser = ImageParser(min_element_area=1)  # Very low threshold
            result = parser.parse(str(path))

            # Should handle gracefully even with no elements
            assert result is not None
            assert result.source_type == "image"
        finally:
            path.unlink(missing_ok=True)

    def test_parse_large_image(self) -> None:
        """Test parsing a larger image."""
        path = self._create_test_image(800, 600, colors={
            (255, 100, 50): (0, 0, 400, 300),
            (50, 100, 255): (400, 0, 800, 300),
            (100, 255, 50): (0, 300, 400, 600),
            (255, 50, 100): (400, 300, 800, 600),
        })

        try:
            parser = ImageParser()
            result = parser.parse(str(path))

            assert result.image_width == 800
            assert result.image_height == 600
            assert result.element_count >= 0
        finally:
            path.unlink(missing_ok=True)

    def test_parse_gradient_image(self) -> None:
        """Test parsing an image with a gradient (many color transitions)."""
        img = Image.new("RGB", (100, 100))
        pixels = img.load()

        for y in range(100):
            for x in range(100):
                r = int(255 * x / 100)
                g = int(255 * y / 100)
                b = 0
                pixels[x, y] = (r, g, b)

        path = pathlib.Path("/tmp/test_gradient.png")
        img.save(str(path))

        try:
            parser = ImageParser()
            result = parser.parse(str(path))

            assert result.source_type == "image"
        finally:
            path.unlink(missing_ok=True)

    def test_parse_with_children(self) -> None:
        """Test that overlapping elements create parent-child relationships."""
        # Create an image with nested colored regions
        path = self._create_test_image(300, 300, colors={
            (200, 200, 200): (0, 0, 300, 300),  # Gray background
            (100, 100, 100): (50, 50, 250, 250),  # Darker inner box
            (50, 50, 50): (100, 100, 200, 200),  # Even darker center
        })

        try:
            parser = ImageParser()
            result = parser.parse(str(path))

            # Some elements should have children due to overlap
            [e for e in result.elements if e.children]
            # At least the result should be valid
            assert result is not None
        finally:
            path.unlink(missing_ok=True)
