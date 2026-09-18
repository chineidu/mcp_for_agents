# Changelog

All notable changes to this project are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/), and the
project adheres to [Semantic Versioning](https://semver.org/).

## [0.3.0] - 2026-09-18

### Added

- `Index` dataclass carrying corpus-wide BM25 statistics (Robertson-
  Sparck Jones IDF and average document length), precomputed once per
  corpus.
- `build_index(docs)` to compute the `Index` from a `Doc` list.
- `score(query_tokens, doc, index, *, k1, b)` now uses Okapi BM25
  (k1=1.5, b=0.75 defaults) instead of the prior integer-style tf +
  body-substring score. Length normalization and IDF weighting apply.
- Server builds the `Index` at startup and threads it through
  `search_docs`. Score formatting in `search_docs` output changed from
  `{s:.0f}` to `{s:.2f}` to fit the new float range.

### Removed

- The body-substring bonus in `score`. BM25's per-term handling makes
  it redundant; dropping it restores the BM25 length-normalization
  guarantees that the bonus was silently breaking. Partial-token
  queries (e.g. `Pydant` matching `Pydantic`) no longer match.

### Tests

- `TestBuildIndex` covers `avgdl`, empty corpus, rare-vs-common IDF,
  and near-zero IDF for terms present in every document.
- `TestScore` covers BM25 properties: empty corpus, term absent, rare
  term outscoring a common one, and shorter doc winning for equal
  term frequency.

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
