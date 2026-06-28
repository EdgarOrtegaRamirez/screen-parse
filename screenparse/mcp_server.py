"""MCP server for ScreenParse — provides UI parsing tools to AI agents."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Only import MCP if available
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


def _create_tools() -> list[dict]:
    """Define the MCP tools available."""
    return [
        {
            "name": "parse_screenshot",
            "description": (
                "Parse a screenshot image to extract UI elements including "
                "buttons, text, images, and input fields. Returns structured "
                "element data with positions, types, and text content."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Path to the screenshot image file (PNG, JPG, etc.)",
                    },
                    "stats": {
                        "type": "boolean",
                        "description": "Include summary statistics in the output",
                        "default": False,
                    },
                },
                "required": ["image_path"],
            },
        },
        {
            "name": "parse_accessibility",
            "description": (
                "Parse an accessibility dump file (Android XML or iOS plist) "
                "to extract UI element information with high accuracy. "
                "Uses accessibility attributes for precise element classification."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "accessibility_path": {
                        "type": "string",
                        "description": "Path to the accessibility dump file",
                    },
                },
                "required": ["accessibility_path"],
            },
        },
    ]


async def run_mcp_server() -> None:
    """Run the ScreenParse MCP server."""
    if not MCP_AVAILABLE:
        logger.error(
            "MCP server unavailable: mcp package not installed. "
            "Install with: pip install screen-parse[mcp]"
        )
        sys.exit(1)

    from screenparse.parser import ScreenParser

    app = Server("screenparse")

    @app.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name=tool["name"],
                description=tool["description"],
                inputSchema=tool["inputSchema"],
            )
            for tool in _create_tools()
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        parser = ScreenParser()
        
        try:
            if name == "parse_screenshot":
                image_path = arguments.get("image_path")
                if not image_path:
                    return [TextContent(type="text", text="Error: image_path is required")]
                
                result = parser.parse_image(image_path)
                output = result.to_dict()
                
                if arguments.get("stats"):
                    output["statistics"] = {
                        "total_elements": result.element_count,
                        "type_counts": result.type_counts,
                        "parse_time_ms": round(result.parse_time_ms, 2),
                    }
                
                return [TextContent(type="text", text=str(output))]
            
            elif name == "parse_accessibility":
                acc_path = arguments.get("accessibility_path")
                if not acc_path:
                    return [TextContent(type="text", text="Error: accessibility_path is required")]
                
                result = parser.parse_accessibility(acc_path)
                output = result.to_dict()
                
                return [TextContent(type="text", text=str(output))]
            
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
        
        except FileNotFoundError as e:
            return [TextContent(type="text", text=f"Error: {e}")]
        except ValueError as e:
            return [TextContent(type="text", text=f"Error: {e}")]

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, None)


def main() -> None:
    """Entry point for the MCP server."""
    import asyncio
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    
    asyncio.run(run_mcp_server())


if __name__ == "__main__":
    main()
