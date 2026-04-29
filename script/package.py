#!/usr/bin/env python3
"""Build platform-specific Ops Agent release archives."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"
RELEASE_DIR = ROOT / "release"
BUILD_DIR = ROOT / "build" / "package"
APP_NAME = "ops-agent"


def run(command: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    print(f"$ {' '.join(command)}")
    subprocess.run(command, cwd=cwd, env=env, check=True)


def detect_platform() -> tuple[str, str]:
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "windows":
        os_name = "windows"
    elif system == "darwin":
        os_name = "macos"
    elif system == "linux":
        os_name = "linux"
    else:
        raise SystemExit(f"Unsupported platform: {platform.system()}")

    if machine in {"amd64", "x86_64"}:
        arch = "x64"
    elif machine in {"arm64", "aarch64"}:
        arch = "arm64"
    else:
        arch = machine or "unknown"

    return os_name, arch


def executable(name: str) -> str:
    return f"{name}.exe" if platform.system().lower() == "windows" else name


def clean() -> None:
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)


def require_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError as exc:
        raise SystemExit("PyInstaller is required. Install project packaging dependencies before running this script.") from exc


def require_frontend_dist() -> None:
    if not (WEB_DIR / "dist").exists():
        raise SystemExit("web/dist does not exist. Run without --skip-frontend or build the frontend first.")


def build_frontend() -> None:
    run(["npm", "ci"], cwd=WEB_DIR)
    run(["npm", "run", "build"], cwd=WEB_DIR)


def build_backend(os_name: str) -> Path:
    require_pyinstaller()
    env = os.environ.copy()
    src_path = str(ROOT / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else src_path

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onefile",
        "--name",
        APP_NAME,
        "--hidden-import",
        "uvicorn",
    ]
    if os_name == "windows":
        command.extend(["--hidden-import", "winpty"])
    command.extend(
        [
            "--paths",
            str(ROOT / "src"),
            "--distpath",
            str(BUILD_DIR / "backend"),
            "--workpath",
            str(BUILD_DIR / "pyinstaller"),
            str(ROOT / "src" / "app" / "main.py"),
        ]
    )

    run(command, env=env)

    binary = BUILD_DIR / "backend" / executable(APP_NAME)
    if not binary.exists():
        raise SystemExit(f"Backend binary was not created: {binary}")
    return binary


def stage_release(binary: Path, os_name: str, arch: str) -> Path:
    stage_dir = BUILD_DIR / f"{APP_NAME}-{os_name}-{arch}"
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    stage_dir.mkdir(parents=True)

    shutil.copy2(binary, stage_dir / binary.name)

    web_dist = WEB_DIR / "dist"
    if web_dist.exists():
        shutil.copytree(web_dist, stage_dir / "web" / "dist")

    shutil.copy2(ROOT / "README.md", stage_dir / "README.md")

    launcher = stage_dir / ("start.bat" if os_name == "windows" else "start.sh")
    if os_name == "windows":
        launcher.write_text(
            "@echo off\r\n"
            "set OPS_AGENT_HOST=127.0.0.1\r\n"
            "set OPS_AGENT_PORT=8000\r\n"
            f"%~dp0{binary.name}\r\n",
            encoding="utf-8",
        )
    else:
        launcher.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "SCRIPT_DIR=\"$(cd \"$(dirname \"${BASH_SOURCE[0]}\")\" && pwd)\"\n"
            "export OPS_AGENT_HOST=127.0.0.1\n"
            "export OPS_AGENT_PORT=8000\n"
            f"exec \"$SCRIPT_DIR/{binary.name}\"\n",
            encoding="utf-8",
        )
        launcher.chmod(0o755)

    return stage_dir


def archive_release(stage_dir: Path, os_name: str, arch: str) -> Path:
    output_dir = RELEASE_DIR / os_name
    output_dir.mkdir(parents=True, exist_ok=True)

    if os_name == "windows":
        archive = output_dir / f"{APP_NAME}-{os_name}-{arch}.zip"
        if archive.exists():
            archive.unlink()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in stage_dir.rglob("*"):
                if file_path.is_file():
                    zip_file.write(file_path, file_path.relative_to(stage_dir.parent))
        return archive

    archive = output_dir / f"{APP_NAME}-{os_name}-{arch}.tar.gz"
    if archive.exists():
        archive.unlink()
    with tarfile.open(archive, "w:gz") as tar_file:
        tar_file.add(stage_dir, arcname=stage_dir.name)
    return archive


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Ops Agent for the current operating system.")
    parser.add_argument("--skip-frontend", action="store_true", help="Reuse the existing web/dist build.")
    parser.add_argument("--no-clean", action="store_true", help="Do not remove previous build outputs first.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os_name, arch = detect_platform()

    if not args.no_clean:
        clean()

    if args.skip_frontend:
        require_frontend_dist()
    else:
        build_frontend()

    binary = build_backend(os_name)
    stage_dir = stage_release(binary, os_name, arch)
    archive = archive_release(stage_dir, os_name, arch)

    print(f"Built {os_name}/{arch} package: {archive}")


if __name__ == "__main__":
    main()
