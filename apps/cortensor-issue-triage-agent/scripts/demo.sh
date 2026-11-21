#!/usr/bin/env bash
# Demo: deep-triage the bundled fixture issue (openminion/openminion#778)
# with the real free model (Pollinations, no key, $0).
#
# Two model calls (classify + draft), paced >=45 s apart by the client,
# so the whole demo takes ~2 minutes. Nothing is sent to GitHub: the
# verdict + draft are printed and saved as a pending snapshot for a human
# to approve with `issue-triage approve --snapshot <id> --yes`.
set -euo pipefail
cd "$(dirname "$0")/.."

# Sandbox workaround: bare/bracketed IPv6 entries in NO_PROXY break httpx.
export NO_PROXY=localhost,127.0.0.1
export no_proxy=localhost,127.0.0.1

.venv/bin/issue-triage triage \
  --repo openminion/openminion \
  --fixture fixtures/openminion-issue-778.json

echo
echo "Demo done. The snapshot above is pending — nothing was posted."
echo "To execute it (needs GITHUB_TOKEN):"
echo "  issue-triage approve --snapshot <id> --yes"
