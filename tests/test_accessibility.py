"""Tests for the accessibility parser."""

from __future__ import annotations

import pytest

from screenparse.accessibility import AccessibilityParser
from screenparse.element import ElementType


class TestAccessibilityParser:
    """Tests for Android XML accessibility parsing."""

    def test_parse_basic(self, temp_xml_file: str) -> None:
        parser = AccessibilityParser()
        result = parser.parse(str(temp_xml_file))

        assert result.source_type == "accessibility"
        assert result.source_path == str(temp_xml_file)
        assert result.element_count > 0
        assert result.parse_time_ms >= 0

    def test_parse_element_types(self, temp_xml_file: str) -> None:
        parser = AccessibilityParser()
        result = parser.parse(str(temp_xml_file))

        types_found = {e.element_type for e in result.elements}
        # Should find at least buttons, text, inputs, images
        assert ElementType.BUTTON in types_found
        assert ElementType.TEXT in types_found
        assert ElementType.INPUT in types_found

    def test_parse_element_text(self, temp_xml_file: str) -> None:
        parser = AccessibilityParser()
        result = parser.parse(str(temp_xml_file))

        text_elements = [e for e in result.elements if e.element_type == ElementType.TEXT]
        assert len(text_elements) > 0

        # Should find "Welcome to App" text
        texts = [e.text for e in text_elements if e.text]
        assert "Welcome to App" in texts

    def test_parse_element_accessibility_label(self, temp_xml_file: str) -> None:
        parser = AccessibilityParser()
        result = parser.parse(str(temp_xml_file))

        button_elements = [e for e in result.elements if e.element_type == ElementType.BUTTON]
        assert len(button_elements) > 0

        # The toolbar should have content-desc
        toolbar = [e for e in result.elements if e.accessibility_role == "android.widget.Toolbar"]
        assert len(toolbar) > 0
        assert toolbar[0].accessibility_label == "Navigation drawer"

    def test_parse_element_bounding_boxes(self, temp_xml_file: str) -> None:
        parser = AccessibilityParser()
        result = parser.parse(str(temp_xml_file))

        for elem in result.elements:
            assert elem.bbox.width >= 0
            assert elem.bbox.height >= 0
            assert elem.bbox.x >= 0
            assert elem.bbox.y >= 0

    def test_parse_hidden_elements_excluded(self, temp_hidden_xml_file: str) -> None:
        parser = AccessibilityParser()
        result = parser.parse(str(temp_hidden_xml_file))

        # Should only include visible element
        visible = [e for e in result.elements if e.is_visible]
        assert len(visible) == 1
        assert visible[0].text == "Visible Text"

        # Hidden element should not be present
        hidden = [e for e in result.elements if e.text == "Hidden Button"]
        assert len(hidden) == 0

    def test_parse_hidden_elements_included(self, temp_hidden_xml_file: str) -> None:
        parser = AccessibilityParser()
        result = parser.parse(
            str(temp_hidden_xml_file),
            include_hidden=True,
        )

        # Should include both visible and hidden
        assert result.element_count == 2

    def test_parse_empty_xml(self, temp_empty_xml_file: str) -> None:
        parser = AccessibilityParser()
        result = parser.parse(str(temp_empty_xml_file))

        assert result.elements == []
        assert result.element_count == 0

    def test_parse_invalid_xml(self, tmp_path: str) -> None:
        bad_xml = tmp_path / "bad.xml"
        bad_xml.write_text("not valid xml <<<", encoding="utf-8")

        parser = AccessibilityParser()
        with pytest.raises(ValueError, match="Failed to parse XML"):
            parser.parse(str(bad_xml))

    def test_parse_element_metadata(self, temp_xml_file: str) -> None:
        parser = AccessibilityParser()
        result = parser.parse(str(temp_xml_file))

        for elem in result.elements:
            assert "source" in elem.metadata
            assert elem.metadata["source"] == "accessibility_xml"

    def test_parse_element_enabled_state(self, temp_xml_file: str) -> None:
        parser = AccessibilityParser()
        result = parser.parse(str(temp_xml_file))

        # All elements in the sample are enabled
        for elem in result.elements:
            assert elem.is_enabled is True

    def test_parse_element_visibility(self, temp_xml_file: str) -> None:
        parser = AccessibilityParser()
        result = parser.parse(str(temp_xml_file))

        # All elements in the sample are visible
        for elem in result.elements:
            assert elem.is_visible is True

    def test_parse_to_dict(self, temp_xml_file: str) -> None:
        parser = AccessibilityParser()
        result = parser.parse(str(temp_xml_file))

        d = result.to_dict()
        assert d["source_type"] == "accessibility"
        assert "elements" in d
        assert len(d["elements"]) > 0
        assert "type" in d["elements"][0]
        assert "bbox" in d["elements"][0]
        assert "id" in d["elements"][0]

    def test_parse_inferred_types(self, temp_xml_file: str) -> None:
        """Test that various Android view types are correctly inferred."""
        parser = AccessibilityParser()
        result = parser.parse(str(temp_xml_file))

        {e.element_type.value: e for e in result.elements}

        # Check specific element types
        buttons = [e for e in result.elements if e.element_type == ElementType.BUTTON]
        assert len(buttons) >= 1  # Toolbar is classified as button

        texts = [e for e in result.elements if e.element_type == ElementType.TEXT]
        assert len(texts) >= 1  # "Welcome to App"

        inputs = [e for e in result.elements if e.element_type == ElementType.INPUT]
        assert len(inputs) >= 1  # EditText

    def test_parse_content_description_fallback(self, tmp_path: str) -> None:
        """Test that content-desc is used as text fallback when text is empty."""
        xml = tmp_path / "fallback.xml"
        xml.write_text(
            '<?xml version="1.0"?>\n'
            "<hierarchy>\n"
            '  <node class="android.widget.ImageView"\n'
            '        text="null"\n'
            '        content-desc="Search icon"\n'
            '        visible-to-user="true"\n'
            '        bounds="[100,100][200,200]"/>\n'
            "</hierarchy>",
            encoding="utf-8",
        )

        parser = AccessibilityParser()
        result = parser.parse(str(xml))

        assert len(result.elements) >= 1
        # Should use content-desc as text
        found = any(e.text == "Search icon" for e in result.elements)
        assert found

    def test_parse_multiple_children(self, tmp_path: str) -> None:
        """Test that child elements are properly parsed."""
        xml = tmp_path / "children.xml"
        xml.write_text(
            '<?xml version="1.0"?>\n'
            "<hierarchy>\n"
            '  <node class="android.widget.FrameLayout"\n'
            '        visible-to-user="true"\n'
            '        bounds="[0,0][1080,2340]">\n'
            '    <node class="android.widget.TextView"\n'
            '          text="Child 1"\n'
            '          visible-to-user="true"\n'
            '          bounds="[100,100][500,200]"/>\n'
            '    <node class="android.widget.TextView"\n'
            '          text="Child 2"\n'
            '          visible-to-user="true"\n'
            '          bounds="[100,300][500,400]"/>\n'
            "  </node>\n"
            "</hierarchy>",
            encoding="utf-8",
        )

        parser = AccessibilityParser()
        result = parser.parse(str(xml))

        # Should have both children
        texts = [e.text for e in result.elements if e.text]
        assert "Child 1" in texts
        assert "Child 2" in texts
