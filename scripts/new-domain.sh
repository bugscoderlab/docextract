#!/usr/bin/env bash
# Create a new domain project from template/app, wired to this monorepo.
#
#   scripts/new-domain.sh ../my-domain
#
# Copies the starter, repoints its engine + UI dependencies at this monorepo
# (absolute paths, so it runs immediately), and inits a git repo. Swap the deps
# for git URLs once the engine and UI are published.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/.." && pwd)"
target="${1:-}"

if [[ -z "$target" ]]; then
  echo "usage: scripts/new-domain.sh <path>" >&2
  exit 1
fi
if [[ -e "$target" ]]; then
  echo "refusing to overwrite existing path: $target" >&2
  exit 1
fi

cp -R "$root/template/app" "$target"

python3 - "$target" "$root" <<'PY'
import pathlib
import sys

target, root = pathlib.Path(sys.argv[1]), sys.argv[2]

requirements = target / "api" / "requirements.txt"
requirements.write_text(requirements.read_text().replace("-e ../..", f"-e {root}"))

package = target / "frontend" / "package.json"
package.write_text(package.read_text().replace("file:../../../ui", f"file:{root}/ui"))
PY

[[ -d "$target/.git" ]] || git -C "$target" init -q

echo "created $target"
echo "next:  cd $target && make bootstrap && make dev"
