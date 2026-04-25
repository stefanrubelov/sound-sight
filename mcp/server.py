"""Standalone MCP server entry point.

Run via stdio (for MCP clients that spawn a subprocess):
    python mcp/server.py

Or import `mcp` from the backend package when running in-process with FastAPI.
"""

import sys
from pathlib import Path

# Ensure the backend package is importable when running standalone
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.mcp.server import mcp  # noqa: E402

if __name__ == "__main__":
    mcp.run(transport="stdio")
