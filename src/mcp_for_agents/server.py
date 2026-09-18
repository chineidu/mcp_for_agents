"""FastMCP server factory for offline docs mirrors."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from fastmcp import FastMCP

from mcp_for_agents.indexer import (
    Doc,
    build_index,
    corpus_label,
    index_directory,
    score,
    tokenize,
)

logger = logging.getLogger("mcp_for_agents.server")

_DEFAULT_DOCS_PATH = Path("~/docs-mirror")


def build_server(
    docs_path: str | os.PathLike[str] | None = None,
    *,
    label: str | None = None,
) -> FastMCP:
    """Build a FastMCP server for an offline docs mirror.

    Indexes `.md` / `.mdx` files under `docs_path` (or `DOCS_PATH` env,
    or `~/docs-mirror`) and registers three tools: `list_doc_sources`,
    `search_docs`, `get_doc`.

    Parameters
    ----------
    docs_path : str | os.PathLike[str] | None
        Directory containing the docs mirror. If None, uses the
        `DOCS_PATH` environment variable, falling back to
        `~/docs-mirror`.
    label : str | None
        Optional corpus label override. Defaults to deriving a
        title-cased label from `docs_path`'s basename.

    Returns
    -------
    FastMCP
        A configured FastMCP instance ready for `.run()`.

    Raises
    ------
    FileNotFoundError
        If the resolved docs path is not an existing directory.
    """
    resolved = _resolve_docs_path(docs_path)
    docs = index_directory(resolved)
    index = build_index(docs)
    by_path = {doc.rel_path: doc for doc in docs}
    final_label = label if label is not None else corpus_label(resolved)

    logger.info(
        "indexed docs_path=%s file_count=%d label=%s",
        resolved,
        len(docs),
        final_label,
    )

    mcp = FastMCP(
        name=f"{final_label.lower()}-docs",
        instructions=(
            f"Offline {final_label} docs. Use list_doc_sources to confirm "
            "coverage, search_docs to find relevant pages, and get_doc to "
            "read one page."
        ),
    )

    @mcp.tool
    def list_doc_sources() -> str:
        """List the indexed docs corpus and a sample of paths."""
        sample = "\n".join(f"- {d.rel_path}: {d.title}" for d in docs[:50])
        return f"{final_label}\nURL: file://{resolved}\n\nIndexed files ({len(docs)} total):\n{sample}"

    @mcp.tool
    def search_docs(query: str, limit: int = 10) -> str:
        """Rank docs by a query over title and body terms."""
        bounded_limit = max(1, min(limit, 50))
        tokens = tokenize(query)
        if not tokens:
            return f"No tokens in query: {query!r}"
        ranked = sorted(
            ((score(tokens, d, index), d) for d in docs),
            key=lambda p: p[0],
            reverse=True,
        )
        top = [(s, d) for s, d in ranked if s > 0][:bounded_limit]
        if not top:
            return f"No matches for: {query!r}"
        lines = [f"Top {len(top)} matches for: {query!r}"]
        lines += [f"- {d.rel_path} (score={s:.2f}) - {d.title}" for s, d in top]
        return "\n".join(lines)

    @mcp.tool
    def get_doc(path: str) -> str:
        """Return the body of one doc by its path from list_doc_sources."""
        candidate = Path(path)
        if candidate.is_absolute() or ".." in candidate.parts:
            return f"Invalid path (must be relative, no '..'): {path}"
        doc: Doc | None = by_path.get(str(candidate).lstrip("/"))
        if doc is None:
            return f"Doc not found: {path}"
        return doc.body

    return mcp


def _resolve_docs_path(docs_path: str | os.PathLike[str] | None) -> Path:
    """Resolve the docs path from argument, env, or default."""
    if docs_path is None:
        docs_path = os.environ.get("DOCS_PATH") or str(_DEFAULT_DOCS_PATH)
    candidate = Path(docs_path).expanduser().resolve()
    if not candidate.is_dir():
        raise FileNotFoundError(f"DOCS_PATH is not a directory: {candidate}")
    return candidate


if __name__ == "__main__":
    try:
        build_server().run()
    except FileNotFoundError as exc:
        print(f"{exc}", file=sys.stderr)
        sys.exit(2)
