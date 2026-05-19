#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WEB_DIR="$ROOT_DIR/web"

host_platform() {
  case "$(uname -s)" in
    Darwin) echo "macos" ;;
    Linux) echo "linux" ;;
    MINGW*|MSYS*|CYGWIN*|Windows_NT) echo "windows" ;;
    *) echo "unsupported" ;;
  esac
}

python_cmd() {
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
  elif command -v python >/dev/null 2>&1; then
    echo "python"
  else
    echo ""
  fi
}

build_native() {
  local platform="$1"
  local python
  python="$(python_cmd)"
  if [[ -z "$python" ]]; then
    echo "Python is required but was not found" >&2
    exit 1
  fi

  cd "$ROOT_DIR"
  if [[ -f ".venv/bin/activate" ]]; then
    source .venv/bin/activate
  elif [[ -f ".venv/Scripts/activate" ]]; then
    source .venv/Scripts/activate
  fi

  "$python" -m pip install -r requirements.txt >/dev/null
  "$python" -m pip install pyinstaller >/dev/null
  "$python" scripts/build_backend_binary.py --platform "$platform"

  cd "$WEB_DIR"
  rm -rf src-tauri/target/release/bundle
  pnpm install >/dev/null
  pnpm tauri:build

  echo "Desktop bundle build completed for $platform"
}

build_linux_in_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is required to build Linux bundles from macOS" >&2
    exit 1
  fi

  if ! docker info >/dev/null 2>&1; then
    echo "Docker daemon is not running. Start Docker Desktop and retry." >&2
    exit 1
  fi

  local debian_mirror="${OPS_AGENT_DEBIAN_MIRROR:-https://mirrors.tuna.tsinghua.edu.cn/debian}"
  local debian_security_mirror="${OPS_AGENT_DEBIAN_SECURITY_MIRROR:-https://mirrors.tuna.tsinghua.edu.cn/debian-security}"

  docker run --rm \
    --platform linux/amd64 \
    -v "$ROOT_DIR:/workspace" \
    -v ops-agent-apt-cache:/var/cache/apt \
    -v ops-agent-apt-lib:/var/lib/apt \
    -w /workspace \
    -e CI=true \
    -e OPS_AGENT_DEBIAN_MIRROR="$debian_mirror" \
    -e OPS_AGENT_DEBIAN_SECURITY_MIRROR="$debian_security_mirror" \
    node:22-bookworm \
    bash -lc 'set -euo pipefail
      sed -i "s|http://deb.debian.org/debian-security|${OPS_AGENT_DEBIAN_SECURITY_MIRROR}|g; s|http://deb.debian.org/debian|${OPS_AGENT_DEBIAN_MIRROR}|g" /etc/apt/sources.list.d/debian.sources
      apt-get -o Acquire::Retries=5 update
      for attempt in 1 2 3 4 5; do
        if apt-get -o Acquire::Retries=5 install -y --no-install-recommends \
          python3 python3-pip python3-venv libpython3.11 \
          curl ca-certificates build-essential pkg-config \
          libwebkit2gtk-4.1-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev patchelf; then
          break
        fi
        if [ "$attempt" = 5 ]; then
          exit 1
        fi
        apt-get -o Acquire::Retries=5 update
      done
      curl https://sh.rustup.rs -sSf | sh -s -- -y --profile minimal
      . "$HOME/.cargo/env"
      corepack enable
      corepack prepare pnpm@10 --activate
      rm -rf .venv-linux-build
      python3 -m venv .venv-linux-build
      . .venv-linux-build/bin/activate
      python -m pip install --upgrade pip
      pip install -r requirements.txt pyinstaller
      python scripts/build_backend_binary.py --platform linux
      cd web
      pnpm install --frozen-lockfile
      pnpm tauri:build
    '

  echo "Desktop bundle build completed for linux"
}

PLATFORM="${1:-$(host_platform)}"
HOST_PLATFORM="$(host_platform)"

if [[ "$HOST_PLATFORM" == "unsupported" ]]; then
  echo "Unsupported host platform: $(uname -s)" >&2
  exit 1
fi

case "$PLATFORM" in
  macos|linux|windows) ;;
  *)
    echo "Usage: $0 [macos|linux|windows]" >&2
    exit 1
    ;;
esac

if [[ "$PLATFORM" == "linux" && "$HOST_PLATFORM" == "macos" ]]; then
  build_linux_in_docker
  exit 0
fi

if [[ "$PLATFORM" != "$HOST_PLATFORM" ]]; then
  cat >&2 <<EOF
Cannot build $PLATFORM bundle on $HOST_PLATFORM with this script.
Linux can be built from macOS through Docker. Windows must be built on Windows.
EOF
  exit 1
fi

build_native "$PLATFORM"
