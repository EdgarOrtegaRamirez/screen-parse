# ScreenParse - Lightweight UI Element Parser for AI Phone Agents

A lightweight CLI tool that parses screenshots and accessibility data to extract structured UI element information for AI phone agents.

## What it does

ScreenParse analyzes mobile device screenshots and accessibility dumps to identify and extract UI elements like buttons, text fields, images, and navigation elements. It outputs structured JSON that AI agents can use to understand screen layout and interact with apps programmatically.

## Features

- **Screenshot analysis** — Detect UI elements from PNG/JPG screenshots using color region analysis
- **Accessibility parsing** — Parse Android XML accessibility dumps and iOS AX dumps
- **Element classification** — Classify elements as buttons, text, images, inputs, icons, containers
- **Spatial reasoning** — Calculate element positions, sizes, and relative relationships
- **Text extraction** — Extract visible text from UI elements using OCR-ready region detection
- **Structured output** — Clean JSON output suitable for AI agent consumption
- **MCP server** — Optional MCP server for AI coding agent integration

## Quick Start

### Install

```bash
pip install screen-parse
# or for development:
pip install -e ".[dev]"
```

### Parse a screenshot

```bash
# Analyze a screenshot and output element info
screenparse parse --image screenshot.png --output result.json

# Show summary statistics
screenparse parse --image screenshot.png --stats

# Parse with verbose output
screenparse parse --image screenshot.png --verbose
```

### Parse accessibility data

```bash
# Parse Android XML accessibility dump
screenparse parse --accessibility dump.xml --output result.json

# Parse accessibility with element types
screenparse parse --accessibility dump.xml --types button,input,text
```

### Python API

```python
from screenparse import ScreenParser

parser = ScreenParser()
result = parser.parse_image("screenshot.png")

for element in result.elements:
    print(f"{element.type}: '{element.text}' at {element.bbox}")
```

## CLI Reference

```
screenparse <command> [options]

Commands:
  parse          Parse an image or accessibility dump
  analyze        Analyze screen layout and element distribution
  info           Show project information and supported formats
  sample-config  Generate a sample configuration file

Parse Options:
  -i, --image PATH          Path to screenshot image
  -a, --accessibility PATH  Path to accessibility dump file
  -o, --output PATH         Output file path (default: stdout)
  -t, --types TEXT          Comma-separated element types to include
  --stats                   Show summary statistics
  --verbose                 Verbose output with debug info
```

## Configuration

Generate a sample config:

```bash
screenparse sample-config > screenparse.yaml
```

Edit the config file:

```yaml
# screenparse.yaml
image:
  min_element_area: 100
  color_threshold: 0.15
  max_elements: 200

accessibility:
  include_hidden: false
  include_content_description: true

output:
  format: json
  pretty_print: true
```

## Architecture

```
screenparse/
├── cli.py              # Click CLI interface
├── parser.py           # Main parser orchestration
├── image_parser.py     # Screenshot analysis engine
├── accessibility.py    # Accessibility dump parsers
├── element.py          # UI element data models
├── utils.py            # Helper utilities
└── mcp_server.py       # Optional MCP server
```

## Supported Formats

- **Images**: PNG, JPG, JPEG, BMP, WebP
- **Accessibility**: Android XML (uiautomator dump), iOS plist (basic)
- **Output**: JSON (default), YAML

## Security Notes

- No network calls or external API dependencies
- No hardcoded secrets or tokens
- File paths are validated before reading (no path traversal)
- Image parsing uses safe Pillow operations
- Input validation on all CLI arguments
- See [SECURITY.md](SECURITY.md) for details

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run linter
ruff check screenparse/ tests/

# Format code
ruff format screenparse/ tests/
```

## License

MIT — See [LICENSE](LICENSE) for details.
