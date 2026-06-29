"""Utility functions for screen parsing."""

from __future__ import annotations

import colorsys
import logging
import pathlib
import time

logger = logging.getLogger(__name__)

# Safe file extensions
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif"}
ACCESSIBILITY_EXTENSIONS = {".xml", ".plist"}


def sanitize_path(path: str | pathlib.Path) -> pathlib.Path:
    """Safely resolve a file path, preventing path traversal attacks.

    Raises:
        ValueError: If the path contains traversal attempts.
        FileNotFoundError: If the file doesn't exist.
    """
    raw = pathlib.Path(path)

    # Check for path traversal attempts in the raw path before resolving
    raw_str = str(raw)
    if ".." in raw_str:
        raise ValueError(f"Path traversal not allowed: {raw_str}")

    path = raw.resolve()

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if not path.is_file():
        raise ValueError(f"Not a file: {path}")

    logger.debug("Sanitized path: %s", path)
    return path


def validate_extension(path: pathlib.Path, extensions: set[str]) -> None:
    """Validate that a file has an allowed extension.

    Raises:
        ValueError: If the extension is not in the allowed set.
    """
    if path.suffix.lower() not in extensions:
        allowed = ", ".join(sorted(extensions))
        raise ValueError(
            f"Unsupported file extension '{path.suffix}'. "
            f"Allowed: {allowed}"
        )


def human_readable_size(bytes_val: int) -> str:
    """Convert bytes to human readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} TB"


def measure_time(func):
    """Decorator that measures execution time and logs it."""
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        logger.debug("Function %s executed in %.2f ms", func.__name__, elapsed)
        return result
    return wrapper


def generate_element_id(index: int, prefix: str = "el") -> str:
    """Generate a unique element ID."""
    return f"{prefix}_{index:04d}"


def _flatten_pixels(pixels: list[int] | list[list[int]]) -> list[int]:
    """Flatten nested pixel lists to a single list of ints."""
    if not pixels:
        return []
    if isinstance(pixels[0], int):
        return pixels
    result: list[int] = []
    for row in pixels:
        if isinstance(row, int):
            result.append(row)
        else:
            result.extend(_flatten_pixels(row))
    return result


def is_solid_region(
    pixels: list[int] | list[list[int]], threshold: float = 0.05
) -> bool:
    """Check if pixel values are mostly uniform (solid color region).

    Args:
        pixels: List of RGB values (flat list of ints or nested).
        threshold: Max allowed color deviation ratio.

    Returns:
        True if the region appears to be a solid color.
    """
    flat = _flatten_pixels(pixels)
    if not flat:
        return True

    # Sample pixels for performance
    sample_size = min(len(flat), 200)
    step = max(1, len(flat) // sample_size)
    sample = flat[::step][:sample_size]

    if len(sample) < 3:
        return True

    # Convert to RGB tuples
    rgb_values: list[tuple[int, int, int]] = []
    for i in range(0, len(sample) - 2, 3):
        rgb_values.append((sample[i], sample[i + 1], sample[i + 2]))

    if not rgb_values:
        return True

    # Calculate mean color
    mean_r = sum(c[0] for c in rgb_values) / len(rgb_values)
    mean_g = sum(c[1] for c in rgb_values) / len(rgb_values)
    mean_b = sum(c[2] for c in rgb_values) / len(rgb_values)

    # Calculate standard deviation
    var_r = sum((c[0] - mean_r) ** 2 for c in rgb_values) / len(rgb_values)
    var_g = sum((c[1] - mean_g) ** 2 for c in rgb_values) / len(rgb_values)
    var_b = sum((c[2] - mean_b) ** 2 for c in rgb_values) / len(rgb_values)

    std_dev = (var_r + var_g + var_b) / 3

    # Normalize by mean intensity
    mean_intensity = (mean_r + mean_g + mean_b) / 3
    if mean_intensity == 0:
        return True

    cv = (std_dev ** 0.5) / mean_intensity  # coefficient of variation

    return cv < threshold


def estimate_text_density(
    pixels: list[int], min_alpha: int = 200
) -> float:
    """Estimate the proportion of pixels that might be text.

    Text pixels tend to have high contrast against background.

    Returns:
        Ratio of text-like pixels (0.0 to 1.0).
    """
    if not pixels:
        return 0.0

    sample_size = min(len(pixels), 1000)
    step = max(1, len(pixels) // sample_size)
    sample = pixels[::step][:sample_size]

    if len(sample) < 9:
        return 0.0

    text_count = 0
    total = 0

    for i in range(0, len(sample) - 2, 3):
        r, g, b = sample[i], sample[i + 1], sample[i + 2]

        # Skip fully transparent or very uniform pixels
        if b < min_alpha:
            continue

        total += 1

        # High contrast colors suggest text on background
        if abs(r - g) > 60 or abs(r - b) > 60 or abs(g - b) > 60:
            text_count += 1

    if total == 0:
        return 0.0

    return text_count / total


def dominant_colors(pixels: list[int], max_colors: int = 8) -> list[tuple[int, int, int, int]]:
    """Find dominant colors in a region.

    Args:
        pixels: List of RGBA values (4 bytes each).
        max_colors: Maximum number of colors to return.

    Returns:
        List of (r, g, b, count) tuples, sorted by count descending.
    """
    if not pixels:
        return []

    sample_size = min(len(pixels), 5000)
    step = max(1, len(pixels) // sample_size)
    sample = pixels[::step][:sample_size]

    color_counts: dict[tuple[int, int, int], int] = {}

    for i in range(0, len(sample) - 3, 4):
        r, g, b, a = sample[i], sample[i + 1], sample[i + 2], sample[i + 3]

        # Skip transparent pixels
        if a < 128:
            continue

        # Quantize to reduce color space
        r_q = (r // 32) * 32
        g_q = (g // 32) * 32
        b_q = (b // 32) * 32

        key = (r_q, g_q, b_q)
        color_counts[key] = color_counts.get(key, 0) + 1

    # Sort by count and limit
    sorted_colors = sorted(color_counts.items(), key=lambda x: x[1], reverse=True)
    return [(r, g, b, count) for (r, g, b), count in sorted_colors[:max_colors]]


def color_distance(
    color1: tuple[int, int, int],
    color2: tuple[int, int, int],
) -> float:
    """Calculate perceptual distance between two RGB colors."""
    r1, g1, b1 = colorsys.rgb_to_hls(
        color1[0] / 255.0, color1[1] / 255.0, color1[2] / 255.0
    )
    r2, g2, b2 = colorsys.rgb_to_hls(
        color2[0] / 255.0, color2[1] / 255.0, color2[2] / 255.0
    )

    # Perceptual distance using HLS space
    return ((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2) ** 0.5
