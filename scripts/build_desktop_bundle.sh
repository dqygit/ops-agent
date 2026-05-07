#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WEB_DIR="$ROOT_DIR/web"

PLATFORM="${1:-}"
if [[ -z "$PLATFORM" ]]; then
  case "$(uname -s)" in
    Darwin) PLATFORM="macos" ;;
    Linux) PLATFORM="linux" ;;
    MINGW*|MSYS*|CYGWIN*|Windows_NT) PLATFORM="windows" ;;
    *) echo "Unsupported platform"; exit 1 ;;
  esac
fi

cd "$ROOT_DIR"
if [[ -d ".venv" ]]; then
  source .venv/bin/activate
fi

python3 -m pip install -r requirements.txt >/dev/null
python3 -m pip install pyinstaller >/dev/null
python3 scripts/build_backend_binary.py --platform "$PLATFORM"

cd "$WEB_DIR"
pnpm install >/dev/null
pnpm tauri:build

echo "Desktop bundle build completed for $PLATFORM"
