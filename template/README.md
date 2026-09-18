# <NAME> Docs MCP

Offline <PACKAGE_DISPLAY_NAME> docs MCP server, built on the
`mcp_for_agents` library.

The server is a 3-line entry point (`server.py`) that delegates to the
shared library. The library handles indexing the docs mirror, scoring
search queries, and exposing three tools over stdio:

| Tool | Purpose |
|---|---|
| `list_doc_sources` | Return the corpus location, label, and file count |
| `search_docs` | Rank files by a query over title and body terms |
| `get_doc` | Return the body of a single file by relative path |

No outbound network required at runtime. The corpus is read from disk.

---

## Prerequisites

| Requirement | Why | How to install |
|---|---|---|
| `uv` 0.4+ on `PATH` | Spawns the server and resolves the library | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `git` | Clones and refreshes the docs mirror | Pre-installed on macOS; `brew install git` otherwise |
| Python 3.10+ | The MCP runtime requires it; `uv` fetches one if missing | Installed automatically by `uv run` |

Verify prerequisites:

```bash
uv --version
git --version
```

If `uv --version` prints nothing, the opencode TUI may inherit a
stripped `PATH` and fail with `ENOENT posix_spawn 'uv'`. See
**Troubleshooting -> PATH issues** below.

---

## Install (fresh machine, no global config yet)

1. **Install `uv` if missing:**

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

   This places `uv` at `~/.local/bin/uv`. Confirm with `uv --version`.

2. **Copy the template into opencode's per-server directory:**

   ```bash
   cp -R <PATH_TO_MCP_FOR_AGENTS>/template/ ~/.config/opencode/mcp-servers/<name>-docs/
   cd ~/.config/opencode/mcp-servers/<name>-docs
   uv init --no-readme
   ```

3. **Add the `mcp_for_agents` library as a dependency.** Use one of:

   ```bash
   # Local path install (recommended for personal use):
   uv add /absolute/path/to/mcp_for_agents

   # Git URL install:
   uv add git+https://github.com/<you>/mcp_for_agents.git

   # Published version (once you've published to PyPI):
   uv add mcp-for-agents
   ```

4. **Bootstrap the docs mirror** (first-time only - paths come from
   your Phase 1/2 work in `playbook.md`):

   ```bash
   git clone --filter=blob:none --sparse --depth 1 \
     https://github.com/<ORG>/<REPO>.git <MIRROR_PATH>

   cd <MIRROR_PATH>

   git sparse-checkout set \
     <MIRROR_PATH_1> \
     <MIRROR_PATH_2>
   ```

5. **Register the MCP server in opencode.** Add this block to your
   `~/.config/opencode/opencode.jsonc`:

   ```jsonc
   "<name>-docs-mcp": {
     "type": "local",
     "command": ["uv", "run", "python", "server.py"],
     "cwd": "~/.config/opencode/mcp-servers/<name>-docs",
     "environment": {
       "DOCS_PATH": "<MIRROR_PATH>",
       "PATH": "/Users/<YOUR_USER>/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
     },
     "timeout": 30000,
     "enabled": true
   }
   ```

   Note: no `--with fastmcp` or `--isolated` flag - `uv run` resolves
   the library and its transitive `fastmcp` dep from this directory's
   own `pyproject.toml`.

6. **Restart opencode.**

7. **Verify:**

   ```bash
   opencode mcp list
   ```

   `<name>-docs-mcp` should show `connected`. If it shows `failed`,
   jump to **Troubleshooting**.

8. **Smoke test from the command line (optional but recommended):**

   ```bash
   DOCS_PATH=<MIRROR_PATH> uv run mcp-for-agents-test <MIRROR_PATH>
   ```

   Should print the available tools and their schemas. To exercise a
   specific tool:

   ```bash
   DOCS_PATH=<MIRROR_PATH> uv run mcp-for-agents-test <MIRROR_PATH> \
     list_doc_sources '{}'
   ```

---

## Daily use

Once installed, the server is silent. Just ask `<PACKAGE_DISPLAY_NAME>`
questions in any opencode session; the model will call
`list_doc_sources`, `search_docs`, or `get_doc` automatically.

---

## Refresh the mirror

When upstream changes:

```bash
cd <MIRROR_PATH>
git fetch origin --depth 1
git reset --hard origin/main
```

Restart opencode after refresh so the server reindexes.

(`git pull` fails on shallow mirrors when the upstream force-pushes;
the fetch + reset pattern always works.)

Optional disk reclaim after several refreshes:

```bash
cd <MIRROR_PATH>
git reflog expire --expire=now --all
git gc --prune=now
```

---

## Configuration

The server reads `DOCS_PATH` from the environment. To point at a
different mirror, update `environment.DOCS_PATH` in your opencode.jsonc
entry.

`DOCS_PATH` accepts any directory containing `.md` / `.mdx` files - it
does not have to be a particular package's docs repo. The corpus label
reported to clients is derived from the directory basename
(e.g. `langchain` -> `LangChain`, `fastapi` -> `FastAPI`).

To add your package's preferred capitalization to the label map, extend
`DEFAULT_ACRONYMS` in `mcp_for_agents.indexer` (in the library repo),
bump the library's `__version__`, and run `uv sync` here.

---

## Upgrading the library

When the library has new features or fixes:

1. Bump `__version__` in `src/mcp_for_agents/__init__.py` and add a
   `CHANGELOG.md` entry in the library repo.
2. In this per-package directory, run `uv lock --upgrade-package mcp-for-agents`
   (or just `uv sync` if you want the latest).
3. Restart opencode so the server reloads the new library code.

To see what version you have:

```bash
uv pip show mcp-for-agents
```

---

## Files

| Path | Purpose |
|---|---|
| `server.py` | The 3-line entry point. Calls `build_server().run()`. |
| `pyproject.toml` | This package's metadata, with `mcp-for-agents` as a dependency. |
| `README.md` | This file. |

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `failed: MCP error -32000: Connection closed` | Mirror path missing | Run step 4 of the install. |
| `failed: ENOENT posix_spawn 'uv'` | `uv` not on PATH inside opencode TUI | See **PATH issues** below. |
| `failed: DOCS_PATH is not a directory: ...` | Mirror path wrong | Set `environment.DOCS_PATH` or fix the symlink. |
| `connected` but `list_doc_sources` returns 0 files | Sparse-checkout misconfigured | `cd <MIRROR_PATH> && git sparse-checkout set <paths>` |
| Stale content after `git pull` | Shallow mirror + force-push | Use `git fetch origin --depth 1 && git reset --hard origin/main` |
| Server shows old content after refresh | opencode did not restart | Restart opencode so the server reindexes from disk. |
| `ModuleNotFoundError: No module named 'mcp_for_agents'` | Library not installed in this venv | Run `uv add /path/to/mcp_for_agents` in this directory. |

### PATH issues

The opencode TUI on macOS inherits a minimal `PATH`
(`/usr/bin:/bin:/usr/sbin:/sbin`) and ignores shell `PATH` modifications
from `~/.zshrc` / `~/.bashrc`. This is a known opencode bug; see
[anomalyco/opencode#26356](https://github.com/anomalyco/opencode/issues/26356).

Workaround: include `~/.local/bin` (or wherever `uv` lives) in the
explicit `environment.PATH` in your opencode.jsonc entry. Each machine
adds its own `environment.PATH` after the first install if needed.

---

## Build provenance

This server was scaffolded from the `mcp_for_agents/template/`
directory. The library that powers it lives in `mcp_for_agents/src/`.
See `mcp_for_agents/playbook.md` for the three-phase process (review
the repo, sparse-clone the mirror, wire the MCP server).
