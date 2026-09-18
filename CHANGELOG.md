# Changelog

All notable changes to this project are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/), and the
project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-09-18

### Added

- `index_directory` now indexes `.rst` files alongside `.md` / `.mdx`,
  covering scientific Python projects (scikit-learn, numpy, pandas)
  whose docs are largely reStructuredText.
- `title_from_body` recognises RST title underlines (a non-blank line
  followed by `=` / `-` / `~` / `^` / `"` / `'` / `` ` `` / `#`
  repeated at least as long as the title).
- Tests for RST indexing and RST title extraction, including the
  short-underline rejection case.

## [0.1.0] - 2026-09-18

### Added

- Initial library extraction from the standalone
  `langgraph-docs/langgraph_docs_mcp.py` script.
- `build_server(docs_path, *, label)` factory returning a configured
  FastMCP server with three tools: `list_doc_sources`, `search_docs`,
  `get_doc`.
- `index_directory(docs_root)` returning a list of `Doc` records for
  `.md` / `.mdx` files under the path.
- `corpus_label(docs_root, acronyms=None)` deriving a display label
  from the directory basename.
- `mcp-for-agents-test` CLI for ad-hoc tool testing from the command
  line.
- `template/` directory with a 3-line per-package `server.py` and a
  README skeleton.
- Tests for the indexer (`tests/test_indexer.py`) and server
  (`tests/test_server.py`).
