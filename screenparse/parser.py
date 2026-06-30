"""Main parser orchestration — unified interface for all parsing backends."""

from __future__ import annotations

import json
import logging
import pathlib

from screenparse.accessibility import AccessibilityParser
from screenparse.element import ParseResult
from screenparse.image_parser import ImageParser

logger = logging.getLogger(__name__)


class ScreenParser:
    """Unified parser for screenshots and accessibility data.

    Provides a simple interface to parse both image screenshots and
    accessibility dumps into structured UI element data.
    """

    def __init__(
        self,
        image_min_area: int = 100,
        image_color_threshold: float = 0.15,
        image_max_elements: int = 200,
        accessibility_include_hidden: bool = False,
    ) -> None:
        self._image_parser = ImageParser(
            min_element_area=image_min_area,
            color_threshold=image_color_threshold,
            max_elements=image_max_elements,
        )
        self._accessibility_parser = AccessibilityParser()
        self._include_hidden = accessibility_include_hidden

    def parse(
        self,
        image_path: str | pathlib.Path | None = None,
        accessibility_path: str | pathlib.Path | None = None,
        verbose: bool = False,
    ) -> ParseResult:
        """Parse either an image or accessibility dump.

        Args:
            image_path: Path to a screenshot image (PNG, JPG, etc.).
            accessibility_path: Path to an accessibility dump file (XML).
            verbose: If True, enable verbose logging.

        Returns:
            ParseResult with detected UI elements.

        Raises:
            ValueError: If neither path is provided or both are provided.
            FileNotFoundError: If the file doesn't exist.
        """
        if image_path and accessibility_path:
            raise ValueError("Provide either image_path or accessibility_path, not both.")
        if not image_path and not accessibility_path:
            raise ValueError("Must provide either image_path or accessibility_path.")

        if image_path:
            return self.parse_image(image_path, verbose)
        else:
            return self.parse_accessibility(accessibility_path)  # type: ignore[arg-type]

    def parse_image(
        self,
        image_path: str | pathlib.Path,
        verbose: bool = False,
    ) -> ParseResult:
        """Parse a screenshot image to extract UI elements.

        Args:
            image_path: Path to the screenshot image.
            verbose: If True, enable verbose logging.

        Returns:
            ParseResult with detected UI elements.
        """
        return self._image_parser.parse(image_path, verbose)

    def parse_accessibility(
        self,
        accessibility_path: str | pathlib.Path,
    ) -> ParseResult:
        """Parse an accessibility dump to extract UI elements.

        Args:
            accessibility_path: Path to the accessibility dump file.

        Returns:
            ParseResult with extracted UI elements.
        """
        return self._accessibility_parser.parse(
            accessibility_path,
            include_hidden=self._include_hidden,
        )

    def parse_and_output(
        self,
        image_path: str | pathlib.Path | None = None,
        accessibility_path: str | pathlib.Path | None = None,
        output_path: str | pathlib.Path | None = None,
        stats: bool = False,
        verbose: bool = False,
    ) -> ParseResult:
        """Parse and optionally output results.

        Args:
            image_path: Path to screenshot image.
            accessibility_path: Path to accessibility dump.
            output_path: Path to write JSON output. If None, writes to stdout.
            stats: If True, also output summary statistics.
            verbose: If True, enable verbose logging.

        Returns:
            ParseResult with detected UI elements.
        """
        result = self.parse(
            image_path=image_path,
            accessibility_path=accessibility_path,
            verbose=verbose,
        )

        output_data = result.to_dict()

        # Add stats if requested
        if stats:
            output_data["statistics"] = {
                "total_elements": result.element_count,
                "top_level_elements": len(result.elements),
                "type_counts": result.type_counts,
                "parse_time_ms": round(result.parse_time_ms, 2),
                "image_dimensions": (
                    f"{result.image_width}x{result.image_height}"
                    if result.image_width > 0
                    else "N/A"
                ),
            }

        # Output results
        json_str = json.dumps(output_data, indent=2)

        if output_path:
            out = pathlib.Path(output_path).resolve()
            # Ensure parent directory exists
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json_str, encoding="utf-8")
            logger.info("Results written to: %s", out)
        else:
            print(json_str)

        return result
