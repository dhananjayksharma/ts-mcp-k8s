import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


MCP_SERVER_COMMAND = os.getenv("MCP_SERVER_COMMAND", "python")
MCP_SERVER_PATH = os.getenv("MCP_SERVER_PATH", "server.py")

REQUIRED_TOOLS = {
    "get_all_pods",
    "describe_pod",
    "get_events",
    "pod_logs",
}


def extract_text(result: Any) -> str:
    """Convert MCP CallToolResult content into plain text."""
    output: list[str] = []

    for item in getattr(result, "content", []):
        text = getattr(item, "text", None)
        if text:
            output.append(text)

    return "\n".join(output)


@asynccontextmanager
async def get_mcp_session() -> AsyncIterator[ClientSession]:
    """Start/connect to the existing stdio MCP server and yield a session."""
    server_params = StdioServerParameters(
        command=MCP_SERVER_COMMAND,
        args=[MCP_SERVER_PATH],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def list_tools(session: ClientSession) -> set[str]:
    """Return all MCP tool names exposed by server.py."""
    tools_result = await session.list_tools()
    return {tool.name for tool in tools_result.tools}


async def validate_required_tools(
    session: ClientSession,
    required_tools: set[str] | None = None,
) -> set[str]:
    """Validate that the existing server exposes all tools required by the agent."""
    required = required_tools or REQUIRED_TOOLS
    available = await list_tools(session)
    missing = required - available

    if missing:
        raise RuntimeError(
            "MCP server missing required tools: "
            + ", ".join(sorted(missing))
        )

    return available


async def call_tool(
    session: ClientSession,
    name: str,
    arguments: dict | None = None,
) -> str:
    """Call one MCP tool and return its text output."""
    result = await session.call_tool(name, arguments or {})

    if getattr(result, "isError", False):
        text = extract_text(result)
        raise RuntimeError(f"MCP tool {name} failed:\n{text}")

    return extract_text(result)
