"""Recursive target-project file scanning."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PIL import Image

from mplgallery.core.models import DiscoveredFile, FileKind, ScanResult

SUPPORTED_SUFFIXES = {".png", ".svg", ".csv"}
DEFAULT_IGNORE_DIRS = {
    ".git",
    ".dvc",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    ".ipynb_checkpoints",
    "build",
    "dist",
    "env",
    "mlruns",
    "node_modules",
    "venv",
}


def scan_project(project_root: Path | str) -> ScanResult:
    root = Path(project_root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Project root does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Project root is not a directory: {root}")

    files: list[DiscoveredFile] = []
    ignored_dir_count = 0
    stack = [root]

    while stack:
        directory = stack.pop()
        for child in sorted(directory.iterdir(), key=lambda path: path.name.lower()):
            if child.is_dir():
                if _should_ignore_dir(child, root):
                    ignored_dir_count += 1
                    continue
                stack.append(child)
                continue

            if not child.is_file() or child.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue

            files.append(_discover_file(child, root))

    files.sort(key=lambda file: file.relative_path.as_posix().lower())
    return ScanResult(project_root=root, files=files, ignored_dir_count=ignored_dir_count)


def _should_ignore_dir(path: Path, root: Path) -> bool:
    name = path.name
    relative_parts = path.relative_to(root).parts

    if len(relative_parts) >= 2 and relative_parts[-2] == ".mplgallery" and relative_parts[-1] == "cache":
        return True
    if name in DEFAULT_IGNORE_DIRS:
        return True
    return name.startswith(".") and name != ".mplgallery"


def _discover_file(path: Path, root: Path) -> DiscoveredFile:
    stat = path.stat()
    suffix = path.suffix.lower()
    width_px, height_px, image_format = _read_image_metadata(path, suffix)
    return DiscoveredFile(
        path=path.resolve(),
        relative_path=path.relative_to(root),
        kind=FileKind.CSV if suffix == ".csv" else FileKind.IMAGE,
        suffix=suffix,
        stem=path.stem,
        parent_dir=path.parent.relative_to(root),
        size_bytes=stat.st_size,
        modified_at=datetime.fromtimestamp(stat.st_mtime),
        created_at=datetime.fromtimestamp(stat.st_ctime),
        width_px=width_px,
        height_px=height_px,
        image_format=image_format,
    )


def _read_image_metadata(path: Path, suffix: str) -> tuple[int | None, int | None, str | None]:
    if suffix != ".png":
        return None, None, suffix.removeprefix(".").upper() if suffix == ".svg" else None

    try:
        with Image.open(path) as image:
            width, height = image.size
            return width, height, image.format
    except OSError:
        return None, None, "PNG"
