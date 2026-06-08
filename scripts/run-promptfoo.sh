#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "从 Admin TestCases 导出 Promptfoo tests..."
curl -sf http://127.0.0.1:8155/api/agent-runtime/promptfoo/sync | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"Exported {d['count']} cases -> {d['path']}\")"

npx --yes promptfoo@latest eval -c harness/promptfoo/promptfooconfig.yaml --tests harness/promptfoo/tests.yaml.active "$@"
echo "View: npx promptfoo view"
