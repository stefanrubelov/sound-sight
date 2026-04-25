"""LangChain ↔ MCP bridge: loads SoundSight MCP tools as LangChain tools."""

import logging

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient


log = logging.getLogger(__name__)

# Base URL for the in-process MCP server (same host as FastAPI)
_DEFAULT_BASE_URL = "http://localhost:8000"


async def get_mcp_tools(base_url: str = _DEFAULT_BASE_URL) -> list[BaseTool]:
    """Return SoundSight MCP tools as LangChain-compatible tools.

    Connects to the FastMCP server mounted at ``{base_url}/mcp`` using the
    streamable-HTTP transport.  Returns an empty list and logs a warning if
    the server is unreachable so callers can fall back to direct DB queries.
    """
    client = MultiServerMCPClient(
        {
            "soundsight": {
                "url": f"{base_url}/mcp",
                "transport": "streamable_http",
            }
        }
    )
    try:
        tools = await client.get_tools()
        log.debug("Loaded %d MCP tools from %s", len(tools), base_url)
        return tools
    except Exception as exc:
        log.warning("MCP tool load failed (%s) — falling back to direct DB queries", exc)
        return []
