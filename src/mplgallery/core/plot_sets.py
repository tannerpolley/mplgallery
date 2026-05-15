"""Project-local plot-set discovery and `.mpl.yaml` sidecar parsing."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from mplgallery.core.models import PlotSetRecord, PlotSetSidecar, RedrawMetadata

RESULTS_DIR_NAME = "results"
PLOT_SET_FIGURE_SUFFIXES = {".png", ".svg", ".pdf"}
PLOT_SET_DATA_SUFFIXES = {".csv"}
PLOT_SET_METADATA_SUFFIXES = {".json", ".md", ".txt", ".yaml", ".yml"}
PLOT_SET_IGNORE_DIRS = {
    ".git",
    ".hg",
    ".dvc",
    ".mplgallery",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "docs",
    "htmlcov",
    "node_modules",
    "site",
    "tests",
}
LEGACY_RESULTS_SUBTREES = {"final", "runs"}


def discover_plot_sets(project_root: Path | str) -> list[PlotSetRecord]:
    """Discover plot sets under `results/**`.

    A plot set is a folder inside a `results` tree containing any CSV, figure,
    or `.mpl.yaml` sidecar files. Direct files under `results/` are grouped by
    stem for compatibility, but the preferred layout is `results/<plot_set>/`.
    """
    root = Path(project_root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Project root does not exist: {root}")

    groups: dict[tuple[Path, str], list[Path]] = {}
    for results_root in _results_roots(root):
        for path in _iter_plot_set_files(results_root):
            if path.parent == results_root:
                group_key = (path.parent, _stem_without_mpl(path))
            else:
                group_key = (path.parent, path.parent.name)
            groups.setdefault(group_key, []).append(path)

    plot_sets: list[PlotSetRecord] = []
    for (group_dir, fallback_id), files in groups.items():
        sidecar_path = _first_sidecar(files)
        sidecar = load_mpl_yaml(sidecar_path) if sidecar_path is not None else None
        plot_set_id = sidecar.plot_id if sidecar is not None else fallback_id
        title = sidecar.title if sidecar is not None and sidecar.title else _human_title(plot_set_id)
        figure_files = sorted(
            (path for path in files if path.suffix.lower() in PLOT_SET_FIGURE_SUFFIXES),
            key=lambda item: item.name.lower(),
        )
        csv_files = sorted(
            (path for path in files if path.suffix.lower() in PLOT_SET_DATA_SUFFIXES),
            key=lambda item: item.name.lower(),
        )
        metadata_files = sorted(
            (path for path in files if path.suffix.lower() in PLOT_SET_METADATA_SUFFIXES),
            key=lambda item: item.name.lower(),
        )
        if not figure_files and not csv_files and sidecar_path is None:
            continue
        plot_sets.append(
            PlotSetRecord(
                plot_set_id=plot_set_id,
                title=title,
                path=group_dir,
                relative_path=_relative_to(group_dir, root),
                csv_files=csv_files,
                figure_files=figure_files,
                metadata_files=metadata_files,
                mpl_yaml_path=sidecar_path,
                editable=sidecar_path is not None,
                render_command=sidecar.render_command if sidecar is not None else None,
                redraw=sidecar.redraw if sidecar is not None else None,
            )
        )

    return sorted(plot_sets, key=lambda item: item.relative_path.as_posix().lower())


def load_mpl_yaml(path: Path | str) -> PlotSetSidecar:
    """Load the agent-authored Matplotlib sidecar contract.

    Matplotlib does not read this file natively. Project render scripts or
    MPLGallery helpers load this YAML and apply it to a Matplotlib figure.
    """
    sidecar_path = Path(path).expanduser().resolve()
    payload = yaml.safe_load(sidecar_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Expected mapping in {sidecar_path}")

    files = payload.get("files") if isinstance(payload.get("files"), dict) else {}
    render = payload.get("render") if isinstance(payload.get("render"), dict) else {}
    matplotlib_payload = payload.get("matplotlib")
    redraw = RedrawMetadata.model_validate(matplotlib_payload) if isinstance(matplotlib_payload, dict) else None
    plot_id = str(payload.get("plot_id") or _stem_without_mpl(sidecar_path))

    return PlotSetSidecar(
        version=int(payload.get("version") or 1),
        plot_id=plot_id,
        title=payload.get("title"),
        figure_files=[Path(value) for value in _list_field(files.get("figures"))],
        data_files=[Path(value) for value in _list_field(files.get("data"))],
        render_command=render.get("command") if isinstance(render.get("command"), str) else None,
        redraw=redraw,
    )


def apply_mpl_yaml(ax: Any, path: Path | str | PlotSetSidecar) -> PlotSetSidecar:
    """Apply a `.mpl.yaml` sidecar to an existing Matplotlib axes.

    This helper is intended for project render scripts. It deliberately does not
    execute render commands or infer Python files; callers own figure creation
    and data plotting, then use this to apply the sidecar style contract.
    """
    sidecar = path if isinstance(path, PlotSetSidecar) else load_mpl_yaml(path)
    metadata = sidecar.redraw
    if metadata is None:
        return sidecar

    if metadata.title is not None:
        ax.set_title(metadata.title)
    if metadata.xlabel is not None:
        ax.set_xlabel(_compose_axis_label(metadata.xlabel, metadata.xlabel_unit))
    if metadata.ylabel is not None:
        ax.set_ylabel(_compose_axis_label(metadata.ylabel, metadata.ylabel_unit))
    ax.set_xscale(metadata.xscale)
    ax.set_yscale(metadata.yscale)
    if metadata.xlim is not None:
        ax.set_xlim(metadata.xlim)
    if metadata.ylim is not None:
        ax.set_ylim(metadata.ylim)
    ax.grid(
        metadata.grid,
        axis=metadata.grid_axis or "both",
        alpha=metadata.grid_alpha if metadata.grid_alpha is not None else 0.25,
    )
    figure = ax.get_figure()
    figure.set_size_inches(metadata.figure.width_inches, metadata.figure.height_inches)
    figure.set_dpi(metadata.figure.dpi)
    if metadata.figure.facecolor:
        figure.set_facecolor(metadata.figure.facecolor)
    if metadata.legend_location or metadata.legend_title:
        ax.legend(title=metadata.legend_title or None, loc=metadata.legend_location or "best")
    return sidecar


def _results_roots(root: Path) -> list[Path]:
    roots: list[Path] = []
    for directory in _walk_directories(root):
        if directory.name != RESULTS_DIR_NAME:
            continue
        if _has_ignored_part(directory.relative_to(root)):
            continue
        roots.append(directory)
    return sorted(roots, key=lambda item: item.as_posix().lower())


def _iter_plot_set_files(results_root: Path) -> list[Path]:
    files: list[Path] = []
    for current_root, dir_names, file_names in os.walk(results_root):
        current = Path(current_root)
        relative_dir = current.relative_to(results_root)
        dir_names[:] = [
            name
            for name in dir_names
            if name.lower() not in LEGACY_RESULTS_SUBTREES and not _has_ignored_part(relative_dir / name)
        ]
        if _has_ignored_part(relative_dir):
            continue
        for file_name in file_names:
            path = current / file_name
            suffix = path.suffix.lower()
            if suffix in PLOT_SET_FIGURE_SUFFIXES or suffix in PLOT_SET_DATA_SUFFIXES or suffix in PLOT_SET_METADATA_SUFFIXES:
                files.append(path)
    return files


def _walk_directories(root: Path) -> list[Path]:
    directories: list[Path] = []
    for current_root, dir_names, _ in os.walk(root):
        directory = Path(current_root)
        relative = directory.relative_to(root)
        if _has_ignored_part(relative):
            dir_names[:] = []
            continue
        directories.append(directory)
        dir_names[:] = [name for name in dir_names if not _has_ignored_part(relative / name)]
    return directories


def _first_sidecar(files: list[Path]) -> Path | None:
    sidecars = sorted((path for path in files if path.name.endswith(".mpl.yaml")), key=lambda item: item.name.lower())
    return sidecars[0] if sidecars else None


def _stem_without_mpl(path: Path) -> str:
    name = path.name
    if name.endswith(".mpl.yaml"):
        return name.removesuffix(".mpl.yaml")
    return path.stem


def _list_field(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _has_ignored_part(path: Path) -> bool:
    return any(part.lower() in PLOT_SET_IGNORE_DIRS for part in path.parts)


def _relative_to(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return Path(path.name)


def _human_title(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").title()


def _compose_axis_label(label: str, unit: str | None) -> str:
    if not unit:
        return label
    if label.endswith(unit):
        return label
    return f"{label} ({unit})"
