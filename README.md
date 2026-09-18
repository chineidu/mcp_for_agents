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

## Adding a new package

See `playbook.md` for the three-phase process: review the upstream
repo, sparse-clone the docs mirror, and wire the MCP server using the
template.

## Requirements

- `uv` 0.4+ on `PATH`
- `git`
- Python 3.14+ (uv will fetch one if missing)
