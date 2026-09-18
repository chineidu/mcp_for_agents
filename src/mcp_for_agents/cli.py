"""CLI entry point for ad-hoc testing of a docs MCP server.

Usage:
    mcp-for-agents-test <docs_path> [tool_name] [tool_args]

With no tool_name: lists available tools and their schemas.
tool_args is a JSON string, e.g. '{"query": "langgraph", "limit": 5}'.
"""

from __future__ import annotations

import asyncio
import json
import sys

from fastmcp import Client

from mcp_for_agents import build_server


async def _list_tools(client: Client) -> None:
    """Print the available tools and their input schemas."""
    tools = await client.list_tools()
    print("Connected. Available tools:\n")
    for tool in tools:
        print(f"- {tool.name}: {tool.description}")
        schema = getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", None)
        print(f"  input schema: {json.dumps(schema, indent=2)}\n")
    print("Run again as: mcp-for-agents-test <docs_path> <tool_name> '<json args>'")


async def _call_tool(client: Client, tool_name: str, raw_args: str) -> None:
    """Print the request, send it, and print the response."""
    args = json.loads(raw_args) if raw_args else {}
    print("--- REQUEST ---")
    print(f"tool:      {tool_name}")
    print(f"arguments: {json.dumps(args, indent=2)}\n")

    result = await client.call_tool(tool_name, args)

    print("--- RAW RESPONSE OBJECT ---")
    print(repr(result))

    print("\n--- CONTENT ---")
    for block in getattr(result, "content", []):
        text = getattr(block, "text", None)
        print(text if text is not None else block)


async def _run(docs_path: str, tool_name: str | None, tool_args: str) -> None:
    """Spawn the server in-process and exercise the requested tool."""
    mcp = build_server(docs_path)
    async with Client(mcp) as client:
        if tool_name is None:
            await _list_tools(client)
        else:
            await _call_tool(client, tool_name, tool_args)


def main() -> None:
    """CLI entry point. See module docstring for usage."""
    if len(sys.argv) < 2:
        print("Usage: mcp-for-agents-test <docs_path> [tool_name] [tool_args]")
        print("  With no tool_name: lists available tools.")
        print('  tool_args is a JSON string, e.g. \'{"query": "langgraph", "limit": 5}\'')
        sys.exit(1)

    docs_path = sys.argv[1]
    tool_name = sys.argv[2] if len(sys.argv) > 2 else None
    tool_args = sys.argv[3] if len(sys.argv) > 3 else "{}"

    asyncio.run(_run(docs_path, tool_name, tool_args))


if __name__ == "__main__":
    main()
