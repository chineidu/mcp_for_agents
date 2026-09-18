"""Offline docs indexer and search scoring."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("mcp_for_agents.indexer")

_TOKEN_PATTERN = re.compile(r"[a-z0-9]{3,}")
_DOC_EXTS = {".md", ".mdx"}
_FRONTMATTER_TITLE = re.compile(r'^title:\s*["\']?([^"\'\n]+)["\']?', re.MULTILINE)

# Known corpus labels. Add your package here when you want a particular
# capitalization (e.g. "FastAPI" instead of "Fastapi"). Anything not in
# the dict is title-cased automatically. Override per-call by passing
# `acronyms` to `corpus_label`.
DEFAULT_ACRONYMS: dict[str, str] = {
    "langchain": "LangChain",
    "langgraph": "LangGraph",
    "langsmith": "LangSmith",
    "fastapi": "FastAPI",
    "polars": "Polars",
    "numpy": "NumPy",
    "pandas": "pandas",
    "pydantic": "Pydantic",
    "sklearn": "scikit-learn",
}


@dataclass(slots=True, frozen=True)
class Doc:
    """One indexed document.

    Parameters
    ----------
    rel_path : str
        Path relative to the docs root, using forward slashes.
    title : str
        Extracted title (from frontmatter, first H1, or filename stem).
    body : str
        Full file contents as a string.
    term_freq : dict[str, int]
        Token-to-count map for the title plus body.
    """

    rel_path: str
    title: str
    body: str
    term_freq: dict[str, int] = field(default_factory=dict)


def tokenize(text: str) -> list[str]:
    """Lowercase `text` and extract 3+ character alphanumeric tokens."""
    return _TOKEN_PATTERN.findall(text.lower())


def term_frequency(tokens: list[str]) -> dict[str, int]:
    """Count occurrences of each token in `tokens`."""
    out: dict[str, int] = {}
    for tok in tokens:
        out[tok] = out.get(tok, 0) + 1
    return out


def title_from_body(body: str, rel_path: str) -> str:
    """Extract a doc title from frontmatter, first H1, or filename stem.

    Parameters
    ----------
    body : str
        Full file contents.
    rel_path : str
        Fallback path used to derive a title from the filename stem
        when no frontmatter or H1 is present.

    Returns
    -------
    str
        The extracted or derived title.
    """
    if body.startswith("---"):
        end = body.find("\n---", 3)
        if end != -1:
            frontmatter = body[3:end]
            m = _FRONTMATTER_TITLE.search(frontmatter)
            if m:
                return m.group(1).strip()
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return Path(rel_path).stem.replace("-", " ").replace("_", " ")


def index_directory(docs_root: Path) -> list[Doc]:
    """Walk `docs_root` and return a `Doc` for each `.md` / `.mdx` file.

    Skips dotfile directories and `node_modules` / `vendor`. Files
    that fail to read are logged and skipped, not raised.

    Parameters
    ----------
    docs_root : Path
        Directory containing the docs mirror.

    Returns
    -------
    list[Doc]
        Indexed documents, sorted by relative path.
    """
    docs: list[Doc] = []
    for path in sorted(docs_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in _DOC_EXTS:
            continue
        rel_parts = path.relative_to(docs_root).parts
        if any(part.startswith(".") for part in rel_parts):
            continue
        if any(part in {"node_modules", "vendor"} for part in rel_parts):
            continue
        rel_path = "/".join(rel_parts)
        try:
            body = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            logger.warning("skip_read_error path=%s", rel_path)
            continue
        title = title_from_body(body, rel_path)
        tokens = tokenize(title + "\n" + body)
        docs.append(Doc(rel_path, title, body, term_frequency(tokens)))
    return docs


def score(query_tokens: list[str], doc: Doc) -> float:
    """Score `doc` against a tokenized query.

    Combines term frequency in the precomputed `term_freq` with a
    substring count over the body (catches occurrences that the
    tokenizer would split differently).

    Parameters
    ----------
    query_tokens : list[str]
        Output of `tokenize(query)`.
    doc : Doc
        Candidate document to score.

    Returns
    -------
    float
        Combined relevance score. Zero when `query_tokens` is empty.
    """
    if not query_tokens:
        return 0.0
    tf_score = float(sum(doc.term_freq.get(tok, 0) for tok in query_tokens))
    body_lower = doc.body.lower()
    substring_bonus = float(sum(body_lower.count(tok) for tok in query_tokens))
    return tf_score + substring_bonus


def corpus_label(docs_root: Path, acronyms: dict[str, str] | None = None) -> str:
    """Derive a display label from `docs_root`'s basename.

    Looks up the normalized basename in `acronyms` (defaulting to
    `DEFAULT_ACRONYMS`); falls back to title-casing.

    Parameters
    ----------
    docs_root : Path
        The docs directory whose basename provides the label seed.
    acronyms : dict[str, str] | None
        Override mapping. Keys are lowercased, dash/underscore-stripped
        basenames; values are display labels.

    Returns
    -------
    str
        The corpus label, e.g. "FastAPI" or "Awesome Package".
    """
    stem = docs_root.name.strip()
    if not stem or stem in {".", "/"}:
        return "Documentation"
    normalized = stem.replace("-", " ").replace("_", " ").lower()
    mapping = acronyms if acronyms is not None else DEFAULT_ACRONYMS
    return mapping.get(normalized, normalized.title())
