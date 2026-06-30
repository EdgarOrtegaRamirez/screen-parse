"""Tests for UI element data models."""

from __future__ import annotations

import pytest

from screenparse.element import BoundingBox, ElementType, ParseResult, UIElement


class TestBoundingBox:
    """Tests for the BoundingBox dataclass."""

    def test_basic_creation(self) -> None:
        bbox = BoundingBox(x=10, y=20, width=100, height=200)
        assert bbox.x == 10
        assert bbox.y == 20
        assert bbox.width == 100
        assert bbox.height == 200

    @pytest.mark.parametrize(
        "x,y,w,h,expected_left,expected_top,expected_right,expected_bottom",
        [
            (0, 0, 100, 100, 0, 0, 100, 100),
            (10, 20, 50, 60, 10, 20, 60, 80),
            (100, 200, 500, 600, 100, 200, 600, 800),
        ],
    )
    def test_properties(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        expected_left: int,
        expected_top: int,
        expected_right: int,
        expected_bottom: int,
    ) -> None:
        bbox = BoundingBox(x=x, y=y, width=w, height=h)
        assert bbox.left == expected_left
        assert bbox.top == expected_top
        assert bbox.right == expected_right
        assert bbox.bottom == expected_bottom

    def test_center(self) -> None:
        bbox = BoundingBox(x=10, y=20, width=100, height=200)
        assert bbox.center_x == 60.0
        assert bbox.center_y == 120.0

    def test_area(self) -> None:
        bbox = BoundingBox(x=0, y=0, width=10, height=20)
        assert bbox.area == 200

    def test_zero_area(self) -> None:
        bbox = BoundingBox(x=0, y=0, width=0, height=100)
        assert bbox.area == 0

    def test_aspect_ratio(self) -> None:
        bbox = BoundingBox(x=0, y=0, width=100, height=50)
        assert bbox.aspect_ratio == 0.5

    def test_zero_width_aspect_ratio(self) -> None:
        bbox = BoundingBox(x=0, y=0, width=0, height=100)
        assert bbox.aspect_ratio == 0.0

    def test_contains_inside(self) -> None:
        bbox = BoundingBox(x=0, y=0, width=100, height=100)
        assert bbox.contains(50, 50) is True

    def test_contains_edge_left(self) -> None:
        bbox = BoundingBox(x=0, y=0, width=100, height=100)
        assert bbox.contains(0, 50) is True

    def test_contains_edge_top(self) -> None:
        bbox = BoundingBox(x=0, y=0, width=100, height=100)
        assert bbox.contains(50, 0) is True

    def test_contains_outside_right(self) -> None:
        bbox = BoundingBox(x=0, y=0, width=100, height=100)
        assert bbox.contains(100, 50) is False

    def test_contains_outside_bottom(self) -> None:
        bbox = BoundingBox(x=0, y=0, width=100, height=100)
        assert bbox.contains(50, 100) is False

    def test_contains_negative(self) -> None:
        bbox = BoundingBox(x=0, y=0, width=100, height=100)
        assert bbox.contains(-1, 50) is False

    def test_overlaps_complete(self) -> None:
        a = BoundingBox(x=0, y=0, width=100, height=100)
        b = BoundingBox(x=50, y=50, width=100, height=100)
        assert a.overlaps(b) is True

    def test_overlaps_partial(self) -> None:
        a = BoundingBox(x=0, y=0, width=100, height=100)
        b = BoundingBox(x=50, y=0, width=50, height=100)
        assert a.overlaps(b) is True

    def test_overlaps_touching_edge(self) -> None:
        a = BoundingBox(x=0, y=0, width=100, height=100)
        b = BoundingBox(x=100, y=0, width=50, height=100)
        assert a.overlaps(b) is False

    def test_overlaps_touching_corner(self) -> None:
        a = BoundingBox(x=0, y=0, width=100, height=100)
        b = BoundingBox(x=100, y=100, width=50, height=50)
        assert a.overlaps(b) is False

    def test_no_overlap_separated(self) -> None:
        a = BoundingBox(x=0, y=0, width=50, height=50)
        b = BoundingBox(x=100, y=100, width=50, height=50)
        assert a.overlaps(b) is False

    def test_intersection(self) -> None:
        a = BoundingBox(x=0, y=0, width=100, height=100)
        b = BoundingBox(x=50, y=50, width=100, height=100)
        inter = a.intersection(b)
        assert inter is not None
        assert inter.x == 50
        assert inter.y == 50
        assert inter.width == 50
        assert inter.height == 50

    def test_intersection_none(self) -> None:
        a = BoundingBox(x=0, y=0, width=50, height=50)
        b = BoundingBox(x=100, y=100, width=50, height=50)
        assert a.intersection(b) is None

    def test_to_dict(self) -> None:
        bbox = BoundingBox(x=10, y=20, width=100, height=200)
        d = bbox.to_dict()
        assert d == {
            "x": 10,
            "y": 20,
            "width": 100,
            "height": 200,
            "left": 10,
            "top": 20,
            "right": 110,
            "bottom": 220,
            "center_x": 60.0,
            "center_y": 120.0,
            "area": 20000,
            "aspect_ratio": 2.0,
        }


class TestUIElement:
    """Tests for the UIElement dataclass."""

    def test_basic_creation(self) -> None:
        elem = UIElement(
            element_id="test_1",
            element_type=ElementType.BUTTON,
            text="Click me",
            bbox=BoundingBox(0, 0, 100, 50),
        )
        assert elem.element_id == "test_1"
        assert elem.element_type == ElementType.BUTTON
        assert elem.text == "Click me"
        assert elem.confidence == 1.0
        assert elem.is_visible is True
        assert elem.is_enabled is True

    def test_to_dict(self) -> None:
        bbox = BoundingBox(10, 20, 100, 50)
        elem = UIElement(
            element_id="el_0001",
            element_type=ElementType.BUTTON,
            text="Submit",
            bbox=bbox,
            confidence=0.95,
            accessibility_role="button",
            accessibility_label="Submit form",
            is_visible=True,
            is_enabled=True,
            children=[],
            metadata={"source": "test"},
        )
        d = elem.to_dict()
        assert d["id"] == "el_0001"
        assert d["type"] == "button"
        assert d["text"] == "Submit"
        assert d["bbox"]["x"] == 10
        assert d["confidence"] == 0.95
        assert d["visible"] is True
        assert d["enabled"] is True
        assert d["accessibility_role"] == "button"
        assert d["accessibility_label"] == "Submit form"
        assert d["metadata"]["source"] == "test"

    def test_with_children(self) -> None:
        parent = UIElement(
            element_id="p_001",
            element_type=ElementType.CONTAINER,
            children=[
                UIElement(
                    element_id="c_001",
                    element_type=ElementType.BUTTON,
                ),
                UIElement(
                    element_id="c_002",
                    element_type=ElementType.TEXT,
                    text="Label",
                ),
            ],
        )
        d = parent.to_dict()
        assert len(d["children"]) == 2
        assert d["children"][0]["type"] == "button"
        assert d["children"][1]["text"] == "Label"

    def test_minimal_creation(self) -> None:
        elem = UIElement(
            element_id="min_1",
            element_type=ElementType.UNKNOWN,
        )
        assert elem.bbox.x == 0
        assert elem.bbox.y == 0
        assert elem.bbox.width == 0
        assert elem.bbox.height == 0
        assert elem.text == ""
        assert elem.children == []
        assert elem.metadata == {}


class TestElementType:
    """Tests for the ElementType enum."""

    def test_all_types_present(self) -> None:
        expected = {
            "button",
            "text",
            "image",
            "input",
            "icon",
            "container",
            "checkbox",
            "radio",
            "list",
            "link",
            "unknown",
        }
        actual = {e.value for e in ElementType}
        assert actual == expected

    def test_type_values(self) -> None:
        assert ElementType.BUTTON.value == "button"
        assert ElementType.TEXT.value == "text"
        assert ElementType.IMAGE.value == "image"
        assert ElementType.INPUT.value == "input"
        assert ElementType.ICON.value == "icon"
        assert ElementType.CONTAINER.value == "container"
        assert ElementType.CHECKBOX.value == "checkbox"
        assert ElementType.RADIO.value == "radio"
        assert ElementType.LIST.value == "list"
        assert ElementType.LINK.value == "link"
        assert ElementType.UNKNOWN.value == "unknown"

    def test_enum_iteration(self) -> None:
        types = list(ElementType)
        assert len(types) == 11

    def test_string_comparison(self) -> None:
        assert ElementType.BUTTON == "button"
        assert ElementType.BUTTON.value == "button"


class TestParseResult:
    """Tests for the ParseResult dataclass."""

    def test_basic_creation(self) -> None:
        result = ParseResult(
            elements=[],
            source_type="image",
            source_path="/test/screenshot.png",
            image_width=1080,
            image_height=2340,
            parse_time_ms=150.5,
        )
        assert result.elements == []
        assert result.source_type == "image"
        assert result.element_count == 0
        assert result.top_level_elements == 0
        assert result.type_counts == {}

    def test_with_elements(self) -> None:
        elements = [
            UIElement(element_id="e1", element_type=ElementType.BUTTON),
            UIElement(element_id="e2", element_type=ElementType.TEXT),
            UIElement(element_id="e3", element_type=ElementType.BUTTON),
        ]
        result = ParseResult(
            elements=elements,
            source_type="image",
            source_path="/test/img.png",
        )
        assert result.element_count == 3
        assert result.type_counts == {"button": 2, "text": 1}

    def test_with_nested_children(self) -> None:
        elements = [
            UIElement(
                element_id="c1",
                element_type=ElementType.CONTAINER,
                children=[
                    UIElement(element_id="b1", element_type=ElementType.BUTTON),
                    UIElement(element_id="t1", element_type=ElementType.TEXT),
                ],
            ),
        ]
        result = ParseResult(
            elements=elements,
            source_type="accessibility",
            source_path="/test/dump.xml",
        )
        assert result.element_count == 3  # 1 container + 2 children
        assert result.top_level_elements == 1

    def test_to_dict(self) -> None:
        elements = [
            UIElement(
                element_id="el_0001",
                element_type=ElementType.BUTTON,
                text="Submit",
                bbox=BoundingBox(100, 200, 150, 50),
            ),
        ]
        result = ParseResult(
            elements=elements,
            source_type="image",
            source_path="/test/img.png",
            image_width=1080,
            image_height=2340,
            parse_time_ms=42.5,
            warnings=["Some elements could not be classified"],
        )
        d = result.to_dict()
        assert d["source_type"] == "image"
        assert d["source_path"] == "/test/img.png"
        assert d["image_dimensions"] == {"width": 1080, "height": 2340}
        assert d["parse_time_ms"] == 42.5
        assert d["element_count"] == 1
        assert d["top_level_elements"] == 1
        assert d["warnings"] == ["Some elements could not be classified"]
        assert len(d["elements"]) == 1
        assert d["elements"][0]["type"] == "button"
