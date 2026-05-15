from __future__ import annotations

from pathlib import Path

import pytest

from mplgallery.core.models import FileKind
from mplgallery.core.scanner import scan_project


def touch(path: Path, content: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def test_scan_project_discovers_png_svg_and_csv_with_relative_paths(tmp_path: Path) -> None:
    touch(tmp_path / "plots" / "experiment_001.png")
    touch(tmp_path / "plots" / "experiment_002.svg")
    touch(tmp_path / "data" / "experiment_001.csv", "x,y\n0,1\n")
    touch(tmp_path / "notes.txt")

    result = scan_project(tmp_path)

    discovered = {file.relative_path.as_posix(): file for file in result.files}
    assert set(discovered) == {
        "data/experiment_001.csv",
        "plots/experiment_001.png",
        "plots/experiment_002.svg",
    }
    assert discovered["data/experiment_001.csv"].kind is FileKind.CSV
    assert discovered["plots/experiment_001.png"].kind is FileKind.IMAGE


def test_scan_project_can_skip_image_metadata_for_fast_loads(tmp_path: Path) -> None:
    touch(tmp_path / "plots" / "experiment_001.png")

    result = scan_project(tmp_path, read_image_metadata=False)

    image = result.files[0]
    assert image.relative_path.as_posix() == "plots/experiment_001.png"
    assert image.image_format == "PNG"
    assert image.width_px is None
    assert image.height_px is None


def test_scan_project_ignores_default_runtime_directories(tmp_path: Path) -> None:
    touch(tmp_path / "plots" / "kept.png")
    touch(tmp_path / ".git" / "hidden.png")
    touch(tmp_path / ".dvc" / "hidden.csv")
    touch(tmp_path / "node_modules" / "hidden.svg")
    touch(tmp_path / "output" / "playwright" / "hidden.png")
    touch(tmp_path / "outputs" / "hidden.svg")
    touch(tmp_path / "playwright-report" / "hidden.png")
    touch(tmp_path / "test-results" / "hidden.png")
    touch(tmp_path / "coverage" / "hidden.csv")
    touch(tmp_path / ".mplgallery" / "cache" / "cached.png")
    touch(tmp_path / "nested" / ".mplgallery" / "cache" / "cached.png")

    result = scan_project(tmp_path)

    assert [file.relative_path.as_posix() for file in result.files] == ["plots/kept.png"]
    assert result.ignored_dir_count >= 10


def test_scan_project_rejects_missing_project_root(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        scan_project(tmp_path / "missing")
