# mcp_for_agents

A small Python library for building local, offline MCP servers that
expose the documentation of your favorite open-source packages to AI
agents (opencode, Claude Code, etc.). Zero network dependency at query
time.

## What it is

A reusable `build_server()` factory plus a thin per-package template.
Each package's MCP server becomes a 3-line Python file:

```python
from mcp_for_agents import build_server

if __name__ == "__main__":
    build_server().run()
```

The library handles indexing the docs mirror, scoring search queries,
and exposing the three tools (`list_doc_sources`, `search_docs`,
`get_doc`) over stdio.

## Repository layout

| Path | Purpose |
|---|---|
| `src/mcp_for_agents/` | The library. Exports `build_server`. |
| `tests/` | Unit and integration tests for the library. |
| `template/` | A 3-line `server.py` and README skeleton. Copy this once per package. |
| `playbook.md` | The end-to-end process for adding a new package. |
| `CHANGELOG.md` | Version history. Bump when you change the library. |

## Reference implementation

`../MLOps_Tutorials/other_notes/Automations/opencode/mcp-servers/langgraph-docs/`
is a working example of a per-package MCP server built using this
library (the library was extracted from that standalone script). It
mirrors what a copy of `template/` looks like after per-package
customization.

## Quick start

To use the library in a per-package MCP server:

```bash
mkdir -p ~/.config/opencode/mcp-servers/<name>-docs
cp -R <PATH_TO_THIS_REPO>/template/ ~/.config/opencode/mcp-servers/<name>-docs/
cd ~/.config/opencode/mcp-servers/<name>-docs

uv init --no-readme
uv add /path/to/mcp_for_agents
```

The library gets installed as a regular dependency. `server.py` runs as
a thin entry point. To work on the library itself, see **Development**
below.

## Development

```bash
cd /path/to/mcp_for_agents

# Install the library in editable mode with dev deps
uv sync --dev

# Run tests
uv run pytest

# Lint and format
uv run ruff check .
uv run ruff format .
```

To verify a package's mirror after setting it up:

```bash
uv run mcp-for-agents-test ~/docs-mirror/<name>
```

(Install the CLI globally with `uv tool install /path/to/mcp_for_agents`
if you want it on PATH.)

## Releasing

Releases are cut with `scripts/release.sh`, which keeps the three
version sources (`pyproject.toml`,
`src/mcp_for_agents/__init__.py`, and the git tag) in sync. The
script never pushes; pushing stays manual so nothing leaves the
machine unreviewed.

Prerequisites: clean tree, on `main`, `uv` on PATH.

```bash
./scripts/release.sh patch   # or: minor, major
```

What the script does, in order:

1. Aborts unless the tree is clean and you are on `main`.
2. Reads the current version from both `pyproject.toml` and
   `__init__.py`, and aborts if they disagree (version drift must be
   fixed by hand first).
3. Computes the next version (semver; `major`/`minor` reset the lower
   segments to zero) and aborts if the tag already exists. This check
   runs before anything is modified, so a duplicate tag cannot leave
   a half-done commit behind.
4. Writes the new version to both files and stubs a `CHANGELOG.md`
   entry above the newest existing one.
5. Runs `ruff check`, `ruff format --check`, and `pytest` (all
   `--frozen`, so the lockfile cannot shift). Any failure aborts
   before the commit.
6. Commits the three files as `[chore] release vX.Y.Z` and creates
   annotated tag `vX.Y.Z`.

After it finishes:

```bash
git show HEAD && git show vX.Y.Z   # review
# fill in the TODO stubs in CHANGELOG.md, then:
git add CHANGELOG.md && git commit -m "[docs] describe vX.Y.Z changes"
git push origin main --follow-tags  # ship
```

## Adding a new package

See `playbook.md` for the three-phase process: review the upstream
repo, sparse-clone the docs mirror, and wire the MCP server using the
template.

## Requirements

- `uv` 0.4+ on `PATH`
- `git`
- Python 3.14+ (uv will fetch one if missing)
