# Playbook: Building a Local Offline Docs MCP Server

A repeatable process for mirroring an open-source project's documentation
locally and serving it to agents (opencode, Claude Code, etc.) over MCP,
with zero network dependency at query time.

This guide covers three phases:

1. **Reviewing the repo** to find out what you actually need to clone
2. **Cloning only those paths** with a blob-filtered sparse checkout
3. **Wiring the mirror into an MCP server** using the `mcp_for_agents` library

Prerequisites: `uv` 0.4+ on `PATH` (install from
<https://astral.sh/uv>), `git`, and Python 3.14+.

---

## Phase 1: Manually review the repo before cloning anything

Guessing paths and patching gaps one at a time is slow and error-prone.
Sparse-checkout paths need to match the repo's real structure, not an
assumed one. Do this reconnaissance first, before running any clone
command.

### 1.1 Find the actual docs source

The docs you read on a project's website often live in a separate repo
from the code, or in a `docs/` folder that is not obviously named. Check:

- The site's footer/GitHub link (often "Edit this page" links point at
  the real source repo)
- The org's repo list for something named `docs`, `website`, or similar
- A `docs/` folder inside the main repo, if there is no separate docs
  repo

### 1.2 List the full repo tree without cloning it

Use GitHub's API to see the complete file tree first, so you know what
exists before deciding what to clone:

```bash
# Replace <org>/<repo> and <branch>
curl -s "https://api.github.com/repos/<org>/<repo>/git/trees/<branch>?recursive=1" \
  | grep '"path"' | sed 's/.*"path": "\(.*\)",/\1/'
```

Or, once you have any local clone of the repo (even a shallow/blobless
one - see Phase 2), query the object store directly, which is faster and
does not hit API rate limits:

```bash
git -C /path/to/clone ls-tree -r --name-only HEAD
```

### 1.3 Search that tree for what you actually need

Grep the full listing for the topics you care about. Cast a wide net -
do not assume things live under an obvious top-level folder (e.g.
"LangGraph" docs may not live under a folder literally named
`langgraph`):

```bash
git -C /path/to/clone ls-tree -r --name-only HEAD | grep -iE "<topic1>|<topic2>|<topic3>"
```

What to look for in the output:

- Which top-level directories actually contain the doc pages you want
- Whether the docs use snippet/import references instead of inline code
  (e.g. `<SomeSnippet />` tags or `import X from '/snippets/...'`
  at the top of a file). If so, note the snippets directory too, or
  your mirror will have prose with invisible gaps where code examples
  should be
- Whether JS/TS and Python (or other language variants) live in
  separate paths. Decide up front whether you want both or just one;
  docs repos are often 2-3x larger than necessary if you clone every
  language variant
- Doc file extensions in use. `.md`, `.mdx`, `.rst` are all common;
  this determines what your indexer needs to look for

### 1.4 Write down your final path list

Before cloning, have a concrete list like:

```
src/oss/python
src/oss/langgraph
src/oss/langchain/multi-agent
src/oss/deepagents
src/snippets/code-samples
```

Every path on this list should be something you confirmed exists via
`ls-tree`, not something you guessed by pattern-matching a URL you saw
on the docs site.

---

## Phase 2: Clone only those paths

### 2.1 The two mechanisms that make this possible

- `--filter=blob:none` (blobless partial clone). Fetches all
  commit/tree metadata, but skips downloading file contents until
  something actually needs them. Combined with sparse-checkout, this
  means content for paths outside your scope is never fetched at all -
  not downloaded-then-hidden.
- `--sparse`. Tells Git to only materialize a chosen set of paths on
  disk. Starts with just root-level files until you
  `sparse-checkout set`.

### 2.2 The clone command

```bash
git clone --filter=blob:none --sparse --depth 1 \
  https://github.com/<org>/<repo>.git ~/docs-mirror/<name>

cd ~/docs-mirror/<name>

git sparse-checkout set \
  <path-1> \
  <path-2> \
  <path-3>
```

Replace the path list with the one you built in Phase 1.3. `--depth 1`
keeps history shallow - docs do not need blame/log history, so this
saves significant space on top of the blob filter.

### 2.3 Verify the clone matches your intent

```bash
git sparse-checkout list                              # confirm the scope
du -sh .                                               # sanity-check total size
find . -iname "*.mdx" -o -iname "*.md" | wc -l         # sanity-check file count
```

### 2.4 Adding paths later (when you discover a gap)

Do not guess a path and add it blind. Confirm it exists first:

```bash
git -C ~/docs-mirror/<name> ls-tree -r --name-only HEAD | grep -i <keyword>
```

Then add only confirmed paths:

```bash
cd ~/docs-mirror/<name>
git sparse-checkout add <confirmed-path>
```

### 2.5 Refreshing the mirror

```bash
cd ~/docs-mirror/<name>
git fetch origin --depth 1 && git reset --hard origin/main
```

`git pull` can fail on shallow mirrors if upstream force-pushes or
rebases; `fetch --depth 1` + `reset --hard` is the robust equivalent
and always works. If it ever goes sideways regardless, deleting and
re-cloning is a safe fallback since this is a read-only mirror with no
local commits.

### 2.6 One caveat with blob-filtered clones

Because content is fetched on demand, the first time you touch a path
outside current scope - including running `git sparse-checkout add` for
a new directory - Git reaches out to the remote to backfill those
blobs. That is expected. It means "offline" here specifically means no
network at MCP query time; corpus-management commands (`add`, `fetch`)
still need connectivity, same as any git operation would.

---

## Phase 3: Wire the mirror into an MCP server

The `mcp_for_agents` library at the root of this repo handles indexing,
search scoring, and tool registration. Each per-package MCP server is a
3-line entry point that delegates to the library. The `template/`
directory contains that entry point plus a README skeleton.

### 3.1 One-time per-package setup

```bash
cp -R <PATH_TO_THIS_REPO>/template/ ~/.config/opencode/mcp-servers/<name>-docs/
cd ~/.config/opencode/mcp-servers/<name>-docs

uv init --no-readme
uv add /path/to/mcp_for_agents
```

The `uv add` step installs the library and its `fastmcp` transitive
dep into this per-package venv. Do this once per new package.

### 3.2 Point the server at your new mirror

No code changes needed - `template/server.py` reads `DOCS_PATH` from
the environment. Edit your `opencode.jsonc`:

```jsonc
"mcp": {
  "<name>-docs-mcp": {
    "type": "local",
    "command": ["uv", "run", "python", "server.py"],
    "cwd": "~/.config/opencode/mcp-servers/<name>-docs",
    "environment": {
      "DOCS_PATH": "~/docs-mirror/<name>"
    },
    "enabled": true
  }
}
```

The opencode command is just `uv run python server.py` - no
`--with fastmcp` or `--isolated` flag, since `uv run` resolves both
the library and its transitive `fastmcp` dep from this directory's own
`pyproject.toml`.

### 3.3 Smoke-test from the command line

Before wiring the opencode entry, exercise the library directly
against your mirror using the bundled CLI:

```bash
DOCS_PATH=~/docs-mirror/<name> \
  uv run mcp-for-agents-test ~/docs-mirror/<name>
```

This spawns the server in-process (no opencode needed) and lists the
available tools plus their input schemas. Then exercise each tool:

```bash
# 1. Confirm coverage
DOCS_PATH=~/docs-mirror/<name> \
  uv run mcp-for-agents-test ~/docs-mirror/<name> \
  list_doc_sources '{}'

# 2. Exercise search
DOCS_PATH=~/docs-mirror/<name> \
  uv run mcp-for-agents-test ~/docs-mirror/<name> \
  search_docs '{"query": "<topic>", "limit": 5}'

# 3. Confirm a real page returns complete, correct content - not
#    empty, not truncated, and check whether it is full of unresolved
#    <SomeSnippet /> tags (a sign the snippets directory needs adding)
DOCS_PATH=~/docs-mirror/<name> \
  uv run mcp-for-agents-test ~/docs-mirror/<name> \
  get_doc '{"path": "<a real path from step 2>"}'
```

(The `DOCS_PATH=` env var on the left is for any subprocesses the CLI
spawns internally; the path positional arg on the right is what
`mcp-for-agents-test` itself reads.)

### 3.4 Restart opencode

The server indexes the mirror once at process startup, not per-call,
so opencode needs a restart to pick up either a code change or a
refreshed mirror (`git fetch` + `reset --hard` from 2.5). There is no
live-reload; this is a deliberate tradeoff for query speed on a large
corpus.

### 3.5 Confirm end-to-end from inside opencode

Ask something like: "list the docs you can search" - should report the
corpus label and file count matching what you verified in 3.3.

---

## Quick reference: full checklist for a new package

- [ ] Find the real docs source repo (may differ from the code repo)
- [ ] List the full tree via API or a throwaway clone
- [ ] Grep for your topics; note any snippet/import-reference convention
- [ ] Write down the confirmed path list
- [ ] `git clone --filter=blob:none --sparse --depth 1 ...`
- [ ] `git sparse-checkout set <paths>`
- [ ] Verify size/file count look sane
- [ ] Copy `template/` into a new per-package dir; `uv init --no-readme`
- [ ] `uv add /path/to/mcp_for_agents`
- [ ] Smoke-test via `uv run mcp-for-agents-test`
      against the mirror, exercising `list_doc_sources`, `search_docs`,
      and `get_doc` on a real path
- [ ] Add the `opencode.jsonc` entry with the right `DOCS_PATH`
- [ ] Restart opencode and confirm from inside the agent
