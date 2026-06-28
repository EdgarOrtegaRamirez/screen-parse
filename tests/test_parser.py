"""Tests for the unified parser and CLI."""

from __future__ import annotations

import json
import pathlib

import pytest

from screenparse.parser import ScreenParser


class TestScreenParser:
    """Tests for the unified ScreenParser class."""

    def test_parse_image(self, tmp_path: str) -> None:
        """Test parsing a screenshot image."""
        import pathlib
        from PIL import Image
        
        img = Image.new("RGB", (200, 200), (255, 0, 0))
        img_path = tmp_path / "test.png"
        img.save(str(img_path))
        
        try:
            parser = ScreenParser()
            result = parser.parse_image(str(img_path))
            
            assert result.source_type == "image"
            assert result.image_width == 200
            assert result.image_height == 200
        finally:
            img_path.unlink(missing_ok=True)

    def test_parse_accessibility(self, temp_xml_file: str) -> None:
        """Test parsing an accessibility dump."""
        parser = ScreenParser()
        result = parser.parse_accessibility(str(temp_xml_file))
        
        assert result.source_type == "accessibility"
        assert result.element_count > 0

    def test_parse_unified_image(self, tmp_path: str) -> None:
        """Test unified parse method with image."""
        import pathlib
        from PIL import Image
        
        img = Image.new("RGB", (100, 100), (0, 255, 0))
        img_path = tmp_path / "green.png"
        img.save(str(img_path))
        
        try:
            parser = ScreenParser()
            result = parser.parse(image_path=img_path)
            
            assert result.source_type == "image"
        finally:
            img_path.unlink(missing_ok=True)

    def test_parse_unified_accessibility(self, temp_xml_file: str) -> None:
        """Test unified parse method with accessibility dump."""
        parser = ScreenParser()
        result = parser.parse(accessibility_path=temp_xml_file)
        
        assert result.source_type == "accessibility"

    def test_parse_both_raises_error(self, tmp_path: str, temp_xml_file: str) -> None:
        """Test that providing both paths raises ValueError."""
        import pathlib
        from PIL import Image
        
        img = Image.new("RGB", (100, 100), (0, 0, 0))
        img_path = tmp_path / "black.png"
        img.save(str(img_path))
        
        try:
            parser = ScreenParser()
            with pytest.raises(ValueError, match="either"):
                parser.parse(image_path=img_path, accessibility_path=temp_xml_file)
        finally:
            img_path.unlink(missing_ok=True)

    def test_parse_neither_raises_error(self) -> None:
        """Test that providing neither path raises ValueError."""
        parser = ScreenParser()
        with pytest.raises(ValueError, match="Must provide"):
            parser.parse()

    def test_parse_output_to_file(self, tmp_path: pathlib.Path) -> None:
        """Test that results can be written to a file."""
        from PIL import Image
        
        img = Image.new("RGB", (100, 100), (128, 128, 128))
        img_path = tmp_path / "gray.png"
        output_path = tmp_path / "output.json"
        img.save(str(img_path))
        
        try:
            parser = ScreenParser()
            result = parser.parse_and_output(
                image_path=img_path,
                output_path=str(output_path),
            )
            
            assert output_path.exists()
            assert output_path.stat().st_size > 0
            
            # Verify JSON is valid
            content = output_path.read_text()
            data = json.loads(content)
            assert data["source_type"] == "image"
        finally:
            img_path.unlink(missing_ok=True)

    def test_parse_with_stats(self, tmp_path: str) -> None:
        """Test parsing with statistics enabled."""
        import pathlib
        from PIL import Image
        
        img = Image.new("RGB", (200, 200), (255, 255, 0))
        img_path = tmp_path / "yellow.png"
        img.save(str(img_path))
        
        try:
            parser = ScreenParser()
            result = parser.parse_and_output(
                image_path=img_path,
                stats=True,
            )
            
            assert result is not None
        finally:
            img_path.unlink(missing_ok=True)

    def test_parse_with_config_options(self, tmp_path: str) -> None:
        """Test parser with custom configuration options."""
        import pathlib
        from PIL import Image
        
        img = Image.new("RGB", (400, 400), (0, 0, 0))
        pixels = img.load()
        for y in range(400):
            for x in range(400):
                if x < 200 and y < 200:
                    pixels[x, y] = (255, 0, 0)
                elif x >= 200 and y < 200:
                    pixels[x, y] = (0, 255, 0)
        
        img_path = tmp_path / "quad.png"
        img.save(str(img_path))
        
        try:
            parser = ScreenParser(
                image_min_area=1000,
                image_color_threshold=0.1,
                image_max_elements=50,
            )
            result = parser.parse_image(str(img_path))
            
            assert result is not None
            assert len(result.elements) <= 50
        finally:
            img_path.unlink(missing_ok=True)

    def test_parse_accessibility_hidden_included(self, temp_hidden_xml_file: str) -> None:
        """Test that hidden elements can be included via parser config."""
        parser = ScreenParser(accessibility_include_hidden=True)
        result = parser.parse_accessibility(str(temp_hidden_xml_file))
        
        # Should include both visible and hidden
        assert result.element_count == 2

    def test_parse_accessibility_hidden_excluded(self, temp_hidden_xml_file: str) -> None:
        """Test that hidden elements are excluded by default."""
        parser = ScreenParser(accessibility_include_hidden=False)
        result = parser.parse_accessibility(str(temp_hidden_xml_file))
        
        # Should only include visible
        visible = [e for e in result.elements if e.is_visible]
        assert len(visible) == 1


class TestParseResultIntegration:
    """Integration tests for parse results."""

    def test_result_serialization(self, temp_xml_file: str) -> None:
        """Test that ParseResult can be fully serialized."""
        parser = ScreenParser()
        result = parser.parse_accessibility(str(temp_xml_file))
        
        d = result.to_dict()
        
        # Verify structure
        assert "source_type" in d
        assert "source_path" in d
        assert "elements" in d
        assert "type_counts" in d
        assert "parse_time_ms" in d
        assert "image_dimensions" in d
        
        # Verify element structure
        if d["elements"]:
            elem = d["elements"][0]
            assert "id" in elem
            assert "type" in elem
            assert "bbox" in elem

    def test_result_type_counts(self, temp_xml_file: str) -> None:
        """Test that type counts are accurate."""
        parser = ScreenParser()
        result = parser.parse_accessibility(str(temp_xml_file))
        
        counts = result.type_counts
        
        # Should have at least one of each major type
        total = sum(counts.values())
        assert total > 0
        assert total == result.top_level_elements

    def test_result_element_count_with_children(self, tmp_path: str) -> None:
        """Test that element count includes nested children."""
        import pathlib
        
        xml = tmp_path / "nested.xml"
        xml.write_text(
            '<?xml version="1.0"?>\n'
            '<hierarchy>\n'
            '  <node class="android.widget.FrameLayout"\n'
            '        visible-to-user="true"\n'
            '        bounds="[0,0][1080,2340]">\n'
            '    <node class="android.widget.TextView"\n'
            '          text="Parent"\n'
            '          visible-to-user="true"\n'
            '          bounds="[100,100][980,200]">\n'
            '      <node class="android.widget.Button"\n'
            '            text="Child Button"\n'
            '            visible-to-user="true"\n'
            '            bounds="[100,300][500,400]"/>\n'
            '    </node>\n'
            '  </node>\n'
            '</hierarchy>',
            encoding="utf-8",
        )
        
        parser = ScreenParser()
        result = parser.parse_accessibility(str(xml))
        
        assert result.element_count >= 2  # Parent + child button
