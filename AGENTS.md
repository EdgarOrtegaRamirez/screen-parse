# AGENTS.md — Notes for AI Agents

## Project: ScreenParse

A lightweight CLI tool that parses screenshots and accessibility data to extract structured UI element information for AI phone agents.

## What it does

ScreenParse analyzes mobile device screenshots and accessibility dumps to identify and extract UI elements like buttons, text fields, images, and navigation elements. It outputs structured JSON that AI agents can use to understand screen layout and interact with apps programmatically.

## Quick reference

```bash
# Parse a screenshot
screenparse parse --image screenshot.png --output result.json

# Parse with stats
screenparse parse --image screenshot.png --stats

# Parse accessibility dump
screenparse parse --accessibility dump.xml

# Analyze screen layout
screenparse analyze --image screenshot.png

# Show info
screenparse info

# Generate config
screenparse sample-config > screenparse.yaml
```

## Python API

```python
from screenparse import ScreenParser

parser = ScreenParser()
result = parser.parse_image("screenshot.png")

for element in result.elements:
    print(f"{element.type}: '{element.text}' at {element.bbox}")
```

## Project structure

- `screenparse/cli.py` — Click CLI interface (parse, analyze, info, sample-config commands)
- `screenparse/parser.py` — Unified parser orchestration (ScreenParser class)
- `screenparse/image_parser.py` — Screenshot analysis engine (color region detection, connected components)
- `screenparse/accessibility.py` — Android XML accessibility dump parser
- `screenparse/element.py` — UI element data models (BoundingBox, UIElement, ParseResult, ElementType)
- `screenparse/utils.py` — Helper utilities (path sanitization, color analysis, region detection)
- `screenparse/mcp_server.py` — Optional MCP server for AI agent integration
- `tests/` — Test suite (pytest)

## Testing

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Dependencies

- `pillow>=10.0.0,<11.0.0` — Image processing
- `click>=8.1.7,<9.0.0` — CLI framework
- `pyyaml>=6.0,<7.0.0` — Config parsing
- `numpy>=1.24.0,<2.0.0` — Array operations

Optional: `mcp>=1.0.0,<2.0.0` — MCP server support

## Security notes

- No network calls or external API dependencies
- No hardcoded secrets
- File paths validated before reading (path traversal protection)
- All input handled safely
- Dependencies version-pinned

## Key implementation details

### Image Parsing
- Uses color quantization (32-level) to reduce complexity
- Connected component analysis via BFS flood fill
- Region classification based on color, aspect ratio, and text density
- Overlapping small elements merged into parent containers

### Accessibility Parsing
- Parses Android XML uiautomator dumps
- Maps Android view classes to element types
- Extracts bounding boxes from bounds attributes
- Supports content-desc as text fallback
- Handles hidden element filtering

### Element Classification Heuristics
- Button colors: blue, green, red tones
- Icons: small, square-ish, solid color regions
- Text: wide, short regions with high contrast
- Inputs: tall, narrow regions
- Containers: large solid regions
