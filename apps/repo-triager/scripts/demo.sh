#!/usr/bin/env bash
# Offline end-to-end demo: no credential, no network.
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PY:-.venv/bin/python}"
if [ ! -x "$PY" ]; then
  echo "run 'make install' first" >&2
  exit 1
fi

echo "== doctor =================================================="
"$PY" -m repo_triager.cli --provider scripted doctor
echo
echo "== demo ===================================================="
"$PY" -m repo_triager.cli --provider scripted demo "$@"
echo
echo "== staged plan ============================================="
for f in var/outbox/*/*.md; do
  [ -e "$f" ] || exit 0
  echo "--- $f"
  sed -n '1,14p' "$f"
done
