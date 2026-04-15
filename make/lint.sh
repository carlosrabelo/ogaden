#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

"$ROOT_DIR/.venv/bin/ruff" check "$ROOT_DIR/ogaden/" "$ROOT_DIR/tests/"
