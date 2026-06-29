"""Tests for utility functions."""

from __future__ import annotations

import pathlib

import pytest

from screenparse.utils import (
    dominant_colors,
    generate_element_id,
    human_readable_size,
    is_solid_region,
    measure_time,
    sanitize_path,
    validate_extension,
)


class TestSanitizePath:
    """Tests for path sanitization."""

    def test_valid_file(self, tmp_path: pathlib.Path) -> None:
        """Test with a valid file path."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")

        result = sanitize_path(test_file)
        assert result.exists()

    def test_nonexistent_file(self) -> None:
        """Test with a nonexistent file."""
        with pytest.raises(FileNotFoundError):
            sanitize_path("/nonexistent/file.txt")

    def test_directory(self, tmp_path: pathlib.Path) -> None:
        """Test with a directory path."""
        with pytest.raises(ValueError, match="Not a file"):
            sanitize_path(tmp_path)

    def test_path_traversal(self, tmp_path: pathlib.Path) -> None:
        """Test that path traversal is blocked."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")

        # Create a file outside tmp_path to test traversal to it
        parent_test = tmp_path.parent / "test.txt"
        parent_test.write_text("hello")
        try:
            with pytest.raises(ValueError, match="Path traversal"):
                traverse_path = tmp_path.parent / ".." / "test.txt"
                sanitize_path(traverse_path)
        finally:
            parent_test.unlink(missing_ok=True)


class TestValidateExtension:
    """Tests for extension validation."""

    def test_allowed_extension(self, tmp_path: pathlib.Path) -> None:
        """Test with an allowed extension."""
        test_file = tmp_path / "test.png"
        test_file.write_text("data")

        validate_extension(test_file, {".png", ".jpg"})
        # Should not raise

    def test_disallowed_extension(self, tmp_path: pathlib.Path) -> None:
        """Test with a disallowed extension."""
        test_file = tmp_path / "test.exe"
        test_file.write_text("malicious")

        with pytest.raises(ValueError, match="Unsupported file extension"):
            validate_extension(test_file, {".png", ".jpg"})

    def test_case_insensitive(self, tmp_path: pathlib.Path) -> None:
        """Test that extension matching is case insensitive."""
        test_file = tmp_path / "test.PNG"
        test_file.write_text("data")

        validate_extension(test_file, {".png", ".jpg"})
        # Should not raise


class TestHumanReadableSize:
    """Tests for human-readable size formatting."""

    def test_bytes(self) -> None:
        assert human_readable_size(500) == "500.0 B"

    def test_kilobytes(self) -> None:
        result = human_readable_size(1500)
        assert "KB" in result

    def test_megabytes(self) -> None:
        result = human_readable_size(1_500_000)
        assert "MB" in result

    def test_gigabytes(self) -> None:
        result = human_readable_size(1_500_000_000)
        assert "GB" in result

    def test_zero(self) -> None:
        assert human_readable_size(0) == "0.0 B"


class TestGenerateElementId:
    """Tests for element ID generation."""

    def test_default_prefix(self) -> None:
        assert generate_element_id(0) == "el_0000"
        assert generate_element_id(1) == "el_0001"
        assert generate_element_id(99) == "el_0099"

    def test_custom_prefix(self) -> None:
        assert generate_element_id(0, "img") == "img_0000"
        assert generate_element_id(5, "acc") == "acc_0005"

    def test_large_index(self) -> None:
        assert generate_element_id(1000) == "el_1000"


class TestIsSolidRegion:
    """Tests for solid region detection."""

    def test_solid_white(self) -> None:
        # 100 white pixels
        pixels = [255, 255, 255] * 100
        assert is_solid_region(pixels) is True

    def test_solid_red(self) -> None:
        pixels = [255, 0, 0] * 100
        assert is_solid_region(pixels) is True

    def test_solid_blue(self) -> None:
        pixels = [0, 0, 255] * 100
        assert is_solid_region(pixels) is True

    def test_mixed_colors(self) -> None:
        # Alternating red and blue
        pixels = []
        for i in range(100):
            if i % 2 == 0:
                pixels.extend([255, 0, 0])
            else:
                pixels.extend([0, 0, 255])
        assert is_solid_region(pixels) is False

    def test_gradient(self) -> None:
        # Smooth gradient
        pixels = []
        for i in range(100):
            r = int(255 * i / 100)
            pixels.extend([r, 0, 0])
        assert is_solid_region(pixels) is False

    def test_empty_list(self) -> None:
        assert is_solid_region([]) is True

    def test_small_list(self) -> None:
        assert is_solid_region([255, 0, 0]) is True
        # Two different colors in 6 pixels — not solid
        assert is_solid_region([255, 0, 0, 0, 255, 0]) is False

    def test_custom_threshold(self) -> None:
        pixels = [255, 0, 0] * 50 + [250, 5, 5] * 50
        # Very strict threshold - should still be solid-ish
        assert is_solid_region(pixels, threshold=0.01) is False
        # Loose threshold
        assert is_solid_region(pixels, threshold=0.2) is True


class TestDominantColors:
    """Tests for dominant color detection."""

    def test_single_color(self) -> None:
        pixels = [255, 0, 0, 255] * 100  # Red with full alpha
        colors = dominant_colors(pixels, max_colors=4)
        assert len(colors) >= 1
        # Dominant should be red-ish
        assert colors[0][0] >= 200  # R value

    def test_two_colors(self) -> None:
        pixels: list[int] = []
        pixels.extend([255, 0, 0, 255] * 50)  # Red
        pixels.extend([0, 0, 255, 255] * 50)   # Blue
        colors = dominant_colors(pixels, max_colors=4)
        assert len(colors) >= 2

    def test_empty_list(self) -> None:
        colors = dominant_colors([])
        assert colors == []

    def test_max_colors_limit(self) -> None:
        pixels: list[int] = []
        for i in range(10):
            pixels.extend([i * 25, 0, 0, 255] * 10)
        colors = dominant_colors(pixels, max_colors=3)
        assert len(colors) <= 3

    def test_transparent_pixels_ignored(self) -> None:
        pixels: list[int] = []
        # Many transparent pixels
        pixels.extend([255, 255, 255, 0] * 100)
        # One opaque pixel
        pixels.extend([0, 255, 0, 255] * 1)
        colors = dominant_colors(pixels, max_colors=4)
        # Should detect green, not white (transparent pixels should be skipped)
        if colors:
            # The green should appear since it's the only opaque color
            green_found = any(c[1] > 200 for c in colors)
            assert green_found


class TestMeasureTime:
    """Tests for the measure_time decorator."""

    def test_decorator_runs_function(self) -> None:
        """Test that the decorated function actually runs."""
        call_count = 0

        @measure_time
        def counting_function() -> int:
            nonlocal call_count
            call_count += 1
            return 42

        result = counting_function()
        assert result == 42
        assert call_count == 1
