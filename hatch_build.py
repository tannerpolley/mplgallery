from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    """Build the Streamlit component before Python package artifacts are created."""

    def initialize(self, version: str, build_data: dict[str, object]) -> None:
        if version == "editable" or os.environ.get("MPLGALLERY_SKIP_FRONTEND_BUILD") == "1":
            return
        frontend_root = Path(self.root) / "src" / "mplgallery" / "ui" / "frontend"
        npm = shutil.which("npm.cmd") or shutil.which("npm")
        if npm is None:
            raise RuntimeError("npm is required to build mplgallery's Streamlit component.")
        if not _frontend_dependencies_installed(frontend_root):
            install_command = "ci" if (frontend_root / "package-lock.json").exists() else "install"
            subprocess.run([npm, install_command], cwd=frontend_root, check=True)
        subprocess.run([npm, "run", "build"], cwd=frontend_root, check=True)


def _frontend_dependencies_installed(frontend_root: Path) -> bool:
    bin_dir = frontend_root / "node_modules" / ".bin"
    return any((bin_dir / name).exists() for name in ("tsc", "tsc.cmd"))
