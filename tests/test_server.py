"""Tests for the server factory and tool behavior."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastmcp import Client, FastMCP

from mcp_for_agents import build_server


class TestBuildServer:
    def test_returns_fastmcp_instance(self, tmp_path: Path) -> None:
        # Given
        (tmp_path / "doc.md").write_text("# Hello\n\nWorld.")
        # When
        result = build_server(tmp_path)
        # Then
        assert isinstance(result, FastMCP)

    def test_invalid_path_raises(self, tmp_path: Path) -> None:
        # Given
        missing = tmp_path / "does-not-exist"
        # When / Then
        with pytest.raises(FileNotFoundError):
            build_server(missing)

    def test_label_override(self, tmp_path: Path) -> None:
        # Given
        (tmp_path / "doc.md").write_text("# Hello")
        # When
        mcp = build_server(tmp_path, label="CustomLabel")
        # Then
        assert mcp.name == "customlabel-docs"

    def test_default_label_from_basename(self, tmp_path: Path) -> None:
        # Given
        (tmp_path / "doc.md").write_text("# Hello")
        # When
        mcp = build_server(tmp_path, label="My Label")
        # Then
        assert mcp.name == "my label-docs"


class TestTools:
    async def test_list_doc_sources(self, tmp_path: Path) -> None:
        # Given
        (tmp_path / "doc.md").write_text("# Hello\n\nWorld.")
        mcp = build_server(tmp_path)
        # When
        async with Client(mcp) as client:
            result = await client.call_tool("list_doc_sources", {})
        # Then
        text = result.content[0].text
        assert "Indexed files (1 total)" in text
        assert "doc.md" in text

    async def test_search_docs_finds_match(self, tmp_path: Path) -> None:
        # Given
        (tmp_path / "langgraph.md").write_text("# LangGraph\n\nLangGraph is great.")
        mcp = build_server(tmp_path)
        # When
        async with Client(mcp) as client:
            result = await client.call_tool("search_docs", {"query": "langgraph"})
        # Then
        text = result.content[0].text
        assert "langgraph.md" in text

    async def test_search_docs_no_match(self, tmp_path: Path) -> None:
        # Given
        (tmp_path / "doc.md").write_text("# Hello\n\nWorld.")
        mcp = build_server(tmp_path)
        # When
        async with Client(mcp) as client:
            result = await client.call_tool("search_docs", {"query": "kubernetes"})
        # Then
        text = result.content[0].text
        assert "No matches" in text

    async def test_get_doc_returns_body(self, tmp_path: Path) -> None:
        # Given
        (tmp_path / "doc.md").write_text("# Hello\n\nWorld.")
        mcp = build_server(tmp_path)
        # When
        async with Client(mcp) as client:
            result = await client.call_tool("get_doc", {"path": "doc.md"})
        # Then
        text = result.content[0].text
        assert "Hello" in text
        assert "World." in text

    async def test_get_doc_rejects_traversal(self, tmp_path: Path) -> None:
        # Given
        (tmp_path / "doc.md").write_text("Content")
        mcp = build_server(tmp_path)
        # When
        async with Client(mcp) as client:
            result = await client.call_tool("get_doc", {"path": "../etc/passwd"})
        # Then
        text = result.content[0].text
        assert "Invalid path" in text

    async def test_get_doc_missing_returns_error(self, tmp_path: Path) -> None:
        # Given
        (tmp_path / "doc.md").write_text("Content")
        mcp = build_server(tmp_path)
        # When
        async with Client(mcp) as client:
            result = await client.call_tool("get_doc", {"path": "nope.md"})
        # Then
        text = result.content[0].text
        assert "Doc not found" in text
