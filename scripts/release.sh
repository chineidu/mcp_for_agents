#!/usr/bin/env bash
#
# Cut a release: bump the version, stub the CHANGELOG, commit, tag.
#
# Usage:
#   scripts/release.sh [major|minor|patch]
#
# The version lives in two places (pyproject.toml and
# src/mcp_for_agents/__init__.py) plus the git tag. This script updates
# all three together so they cannot drift. It never pushes; review the
# commit, fill in the CHANGELOG TODO stubs, then run:
#   git push origin main --follow-tags
set -euo pipefail

PART="${1:-patch}"
case "$PART" in
  major|minor|patch) ;;
  *) echo "usage: $0 [major|minor|patch]" >&2; exit 1 ;;
esac

command -v uv >/dev/null || { echo "error: uv not found on PATH" >&2; exit 1; }

# Abort on a dirty tree.
if [ -n "$(git status --porcelain)" ]; then
  echo "error: working tree is not clean; commit or stash first" >&2
  exit 1
fi

# Only release from main.
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [ "$BRANCH" != "main" ]; then
  echo "error: must be on main (on $BRANCH)" >&2
  exit 1
fi

# Compute the new version and refuse if the two sources disagree.
VERSIONS="$(python3 - "$PART" <<'PY'
import re, sys
part = sys.argv[1]
pyproject = open("pyproject.toml").read()
init = open("src/mcp_for_agents/__init__.py").read()
m1 = re.search(r'^version = "(\d+)\.(\d+)\.(\d+)"$', pyproject, re.M)
m2 = re.search(r'^__version__ = "(\d+)\.(\d+)\.(\d+)"$', init, re.M)
if not m1 or not m2:
    sys.exit("error: could not parse current version")
old = m1.group(1) + "." + m1.group(2) + "." + m1.group(3)
if m2.group(1) + "." + m2.group(2) + "." + m2.group(3) != old:
    sys.exit("error: version drift between pyproject.toml and __init__.py; fix by hand first")
major, minor, patch = int(m1.group(1)), int(m1.group(2)), int(m1.group(3))
if part == "major":
    major, minor, patch = major + 1, 0, 0
elif part == "minor":
    minor, patch = minor + 1, 0
else:
    patch += 1
print(old, f"{major}.{minor}.{patch}")
PY
)"
OLD="${VERSIONS%% *}"
NEW="${VERSIONS##* }"
echo "bumping $OLD -> $NEW"

if git rev-parse "v$NEW" >/dev/null 2>&1; then
  echo "error: tag v$NEW already exists" >&2
  exit 1
fi

# Bump both version sources.
python3 - "$OLD" "$NEW" <<'PY'
import sys
old, new = sys.argv[1], sys.argv[2]
p = "pyproject.toml"
s = open(p).read().replace(f'version = "{old}"', f'version = "{new}"', 1)
open(p, "w").write(s)
p = "src/mcp_for_agents/__init__.py"
s = open(p).read().replace(f'__version__ = "{old}"', f'__version__ = "{new}"', 1)
open(p, "w").write(s)
PY

# Stub a CHANGELOG entry above the newest existing one.
TODAY="$(date +%F)"
python3 - "$NEW" "$TODAY" <<'PY'
import sys
new, today = sys.argv[1], sys.argv[2]
entry = f"## [{new}] - {today}\n\n### Added\n\n- TODO: describe changes.\n\n"
p = "CHANGELOG.md"
lines = open(p).read().splitlines(keepends=True)
for i, line in enumerate(lines):
    if line.startswith("## ["):
        lines.insert(i, entry)
        break
else:
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    lines.append("\n" + entry)
open(p, "w").write("".join(lines))
PY

# Verify before committing.
uv sync --extra dev --frozen -q
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen pytest -q

# Commit and tag. Push is always manual.
git add pyproject.toml src/mcp_for_agents/__init__.py CHANGELOG.md
git commit -m "[chore] release v$NEW" -m "- bump version to $NEW"
git tag -a "v$NEW" -m "v$NEW"

echo "released v$NEW (commit + tag, not pushed)"
echo "review: git show HEAD && git show v$NEW"
echo "fill in the CHANGELOG TODO stubs, commit the touch-up, then ship:"
echo "  git push origin main --follow-tags"
