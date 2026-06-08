#!/bin/bash
# 运行 backend 单元测试（TDD / CI）
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/../backend"
PY="${PYTHON:-python3.10}"
if ! command -v "$PY" >/dev/null 2>&1; then PY=python3; fi
"$PY" -m pytest tests/ -v --tb=short "$@"
