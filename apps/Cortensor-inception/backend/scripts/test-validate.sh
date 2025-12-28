#!/usr/bin/env bash
set -euo pipefail

URL=${1:-http://localhost:3000/validate}

curl -s -X POST "$URL" -H "Content-Type: application/json" -d '{"task":{"prompt":"Is this safe?"},"policy":{"minValidators":1,"minAgreement":0.6}}' | jq
