"""CSV-first plot studio discovery, draft generation, and imports."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import yaml

from mplgallery.core.associations import build_plot_records
from mplgallery.core.manifest import ProjectManifest, load_manifest, load_manifests, save_manifest
from mplgallery.core.models import (
    AssociationConfidence,
    CSVRootRecord,
    CSVStudioIndex,
    CacheMetadata,
    DatasetRecord,
    DiscoveredFile,
    FileKind,
    ManifestRecord,
    PlotMode,
    PlotRecipeRecord,
    PlotRecord,
    PlotSetRecord,
    RedrawMetadata,
    TablePrepMetadata,
)
from mplgallery.core.pandas_plotting import (
    generated_script_text,
    infer_pandas_draft,
    render_pandas_draft_figure,
)
from mplgallery.core.plot_sets import discover_plot_sets
from mplgallery.core.scanner import scan_project

CSV_ROOT_NAMES = {"data"}
RESULT_TABLE_PARTS = ("results", "final", "tables")
RESULT_FIGURE_PARTS = ("results", "final", "figures")
STUDIO_IGNORE_DIRS = {
    ".git",
    ".dvc",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    ".mplgallery",
    "build",
    "coverage",
    "dist",
    "docs",
    "htmlcov",
    "node_modules",
    "playwright-report",
    "site",
    "test-results",
    "tests",
}
STUDIO_SUBDIRS = ("recipes", "scripts", "plot_ready", "cache")
DEFAULT_SAMPLE_ROWS = 5000


@dataclass(frozen=True)
class CSVStudioWorkspace:
    root: Path
    manifest_path: Path
    recipes_dir: Path
    scripts_dir: Path
    plot_ready_dir: Path
    cache_dir: Path


@dataclass(frozen=True)
class ArtifactImportResult:
    manifest_path: Path
    imported_count: int
    imported_paths: tuple[Path, ...]


def find_csv_roots(project_root: Path | str) -> list[CSVRootRecord]:
    """Find architecture-standard CSV roots for source and final result tables."""
    root = Path(project_root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Project root does not exist: {root}")

    roots: list[CSVRootRecord] = []
    for directory in _walk_candidate_directories(root):
        if not _is_architecture_csv_root(directory, root):
            continue
        datasets = [_dataset_record(csv_path, root, directory) for csv_path in _csvs_for_root(directory)]
        if not datasets:
            continue
        roots.append(
            CSVRootRecord(
                path=directory,
                relative_path=_relative_to(directory, root),
                datasets=datasets,
            )
        )
    return sorted(roots, key=lambda item: item.relative_path.as_posix().lower())


def init_csv_root(csv_root: Path | str) -> CSVStudioWorkspace:
    """Create the portable `.mplgallery` workspace beside a CSV root."""
    root = Path(csv_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    workspace_root = root / ".mplgallery"
    for subdir in STUDIO_SUBDIRS:
        (workspace_root / subdir).mkdir(parents=True, exist_ok=True)
    manifest_path = workspace_root / "manifest.yaml"
    if not manifest_path.exists():
        save_manifest(root, ProjectManifest())
    return CSVStudioWorkspace(
        root=root,
        manifest_path=manifest_path,
        recipes_dir=workspace_root / "recipes",
        scripts_dir=workspace_root / "scripts",
        plot_ready_dir=workspace_root / "plot_ready",
        cache_dir=workspace_root / "cache",
    )


def build_csv_studio_index(
    project_root: Path | str,
    *,
    ensure_drafts: bool = False,
    include_artifacts: bool = True,
    image_library_mode: bool = False,
    sample_rows: int = DEFAULT_SAMPLE_ROWS,
) -> CSVStudioIndex:
    """Build the CSV-first index used by the CLI and desktop compatibility helpers."""
    root = Path(project_root).expanduser().resolve()
    if image_library_mode:
        scan = scan_project(root)
        records = [
            record
            for record in build_plot_records(scan, manifest=load_manifests(root))
            if _is_reference_artifact_path(record.image.relative_path)
        ]
        return CSVStudioIndex(
            project_root=root,
            browse_mode="image-library",
            records=records,
            ignored_dir_count=scan.ignored_dir_count,
            imported_artifacts=records,
        )

    csv_roots = find_csv_roots(root)
    plot_sets = discover_plot_sets(root)
    datasets: list[DatasetRecord] = []
    records: list[PlotRecord] = []
    ignored_count = _count_ignored_directories(root)

    for csv_root in csv_roots:
        if ensure_drafts:
            drafted = draft_csv_root(csv_root.path, project_root=root, sample_rows=sample_rows)
            datasets.extend(drafted.datasets)
            records.extend(drafted.records)
        else:
            datasets.extend(_non_mutating_dataset_records(csv_root, root))

    plot_set_records = _plot_set_records(root, plot_sets)
    records.extend(plot_set_records)
    existing_paths = {record.image.path for record in records}

    imported_artifacts = [
        record
        for record in _architecture_result_artifact_records(root)
        if record.image.path not in existing_paths
    ]
    records.extend(imported_artifacts)
    existing_paths.update(record.image.path for record in imported_artifacts)
    if include_artifacts:
        scan = scan_project(root)
        manifest = load_manifests(root)
        broad_artifacts = build_plot_records(scan, manifest=manifest)
        for record in broad_artifacts:
            if not _is_reference_artifact_path(record.image.relative_path):
                continue
            if record.image.path not in existing_paths:
                records.append(record)
                imported_artifacts.append(record)
                existing_paths.add(record.image.path)
        ignored_count += scan.ignored_dir_count

    auto_image_library = bool(records) and not csv_roots and not plot_sets
    return CSVStudioIndex(
        project_root=root,
        browse_mode="image-library" if auto_image_library else "plot-set-manager",
        csv_roots=csv_roots,
        datasets=datasets,
        records=records,
        plot_sets=plot_sets,
        ignored_dir_count=ignored_count,
        imported_artifacts=imported_artifacts,
    )


def draft_csv_root(
    csv_root: Path | str,
    *,
    project_root: Path | str | None = None,
    sample_rows: int = DEFAULT_SAMPLE_ROWS,
) -> CSVStudioIndex:
    """Create draft recipes, render scripts, plot-ready CSVs, and cached previews."""
    root = Path(csv_root).expanduser().resolve()
    project = Path(project_root).expanduser().resolve() if project_root is not None else root
    workspace = init_csv_root(root)
    manifest = load_manifest(root)
    datasets: list[DatasetRecord] = []
    records: list[PlotRecord] = []

    for csv_path in _csvs_for_root(root):
        dataset, record = _draft_csv(csv_path, root, project, workspace, manifest, sample_rows)
        datasets.append(dataset)
        if record is not None:
            records.append(record)

    save_manifest(root, manifest)
    csv_root_record = CSVRootRecord(path=root, relative_path=_relative_to(root, project), datasets=datasets)
    return CSVStudioIndex(
        project_root=project,
        csv_roots=[csv_root_record],
        datasets=datasets,
        records=records,
    )


def draft_csv_dataset(
    csv_path: Path | str,
    *,
    csv_root: Path | str | None = None,
    project_root: Path | str | None = None,
    sample_rows: int = DEFAULT_SAMPLE_ROWS,
    redraw: RedrawMetadata | None = None,
    output_format: str = "svg",
) -> CSVStudioIndex:
    """Create or refresh a draft for one source CSV."""
    source = Path(csv_path).expanduser().resolve()
    root = (
        Path(csv_root).expanduser().resolve()
        if csv_root is not None
        else _infer_csv_root_for_dataset(source, project_root)
    )
    project = Path(project_root).expanduser().resolve() if project_root is not None else root
    workspace = init_csv_root(root)
    manifest = load_manifest(root)
    dataset, record = _draft_csv(
        source,
        root,
        project,
        workspace,
        manifest,
        sample_rows,
        redraw_override=redraw,
        output_format=output_format,
    )
    save_manifest(root, manifest)
    records = [record] if record is not None else []
    return CSVStudioIndex(
        project_root=project,
        csv_roots=[CSVRootRecord(path=root, relative_path=_relative_to(root, project), datasets=[dataset])],
        datasets=[dataset],
        records=records,
    )


def import_artifact_references(folder: Path | str) -> ArtifactImportResult:
    """Import PNG/SVG files under a folder as reference-only manifest records."""
    root = Path(folder).expanduser().resolve()
    init_csv_root(root)
    manifest = load_manifest(root)
    imported: list[Path] = []
    for path in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if path.is_file() and path.suffix.lower() in {".png", ".svg"}:
            manifest.upsert_record(
                ManifestRecord(
                    plot_path=path.relative_to(root),
                    notes="Imported reference artifact",
                )
            )
            imported.append(path)
    manifest_path = save_manifest(root, manifest)
    return ArtifactImportResult(
        manifest_path=manifest_path,
        imported_count=len(imported),
        imported_paths=tuple(imported),
    )


def _plot_set_records(project_root: Path, plot_sets: list[PlotSetRecord]) -> list[PlotRecord]:
    records: list[PlotRecord] = []
    for plot_set in plot_sets:
        csv_path = plot_set.csv_files[0] if plot_set.csv_files else None
        csv = _discovered_file(csv_path, project_root, FileKind.CSV) if csv_path is not None else None
        for figure_path in plot_set.figure_files:
            if figure_path.suffix.lower() not in {".png", ".svg"}:
                continue
            image = _discovered_file(figure_path, project_root, FileKind.IMAGE)
            records.append(
                PlotRecord(
                    plot_id=_plot_id(image.relative_path),
                    image=image,
                    csv=csv,
                    raw_csv=csv,
                    plot_csv=csv,
                    association_confidence=AssociationConfidence.EXACT
                    if csv is not None
                    else AssociationConfidence.NONE,
                    association_reason="Plot set sidecar" if plot_set.editable else "Plot set folder",
                    redraw=plot_set.redraw,
                    mode=PlotMode.RECIPE if plot_set.editable else PlotMode.STATIC,
                    source_dataset_id=_dataset_id(csv.relative_path) if csv is not None else None,
                    owned_by_mplgallery=False,
                    visibility_role="reference",
                    metadata_files=[plot_set.mpl_yaml_path] if plot_set.mpl_yaml_path is not None else [],
                )
            )
    return records


def _architecture_result_artifact_records(project_root: Path) -> list[PlotRecord]:
    records: list[PlotRecord] = []
    manifest_records = _manifest_records_by_absolute_plot(project_root)
    for figures_dir in _architecture_result_figure_dirs(project_root):
        for path in _iter_supported_files(figures_dir, project_root, suffixes={".png", ".svg"}):
            if "mplgallery" in {part.lower() for part in path.relative_to(figures_dir).parts[:-1]}:
                continue
            image = _discovered_file(path, project_root, FileKind.IMAGE)
            manifest_match = manifest_records.get(path.resolve())
            if manifest_match is not None:
                manifest_root, manifest_record = manifest_match
                source_csv = _resolved_manifest_path(manifest_root, manifest_record.raw_csv_path or manifest_record.csv_path)
                plot_csv = _resolved_manifest_path(manifest_root, manifest_record.plot_csv_path or manifest_record.csv_path)
                raw_discovered = (
                    _discovered_file(source_csv, project_root, FileKind.CSV)
                    if source_csv is not None and source_csv.exists()
                    else None
                )
                plot_discovered = (
                    _discovered_file(plot_csv, project_root, FileKind.CSV)
                    if plot_csv is not None and plot_csv.exists()
                    else None
                )
                owned = manifest_record.notes == "MPLGallery CSV draft"
                records.append(
                    PlotRecord(
                        plot_id=_plot_id(image.relative_path),
                        image=image,
                        csv=plot_discovered,
                        raw_csv=raw_discovered,
                        plot_csv=plot_discovered,
                        association_confidence=AssociationConfidence.EXACT
                        if plot_discovered is not None
                        else AssociationConfidence.NONE,
                        association_reason=manifest_record.notes or "Architecture result figure",
                        redraw=manifest_record.redraw,
                        cache=CacheMetadata(cache_path=path) if owned else None,
                        recipe_path=_recipe_path_for_csv(source_csv, manifest_root)
                        if source_csv is not None and source_csv.exists()
                        else None,
                        mode=PlotMode.RECIPE if owned else PlotMode.STATIC,
                        source_dataset_id=_dataset_id(_relative_to(source_csv, project_root))
                        if source_csv is not None
                        else None,
                        owned_by_mplgallery=owned,
                        visibility_role="draft" if owned else "reference",
                    )
                )
                continue
            records.append(
                PlotRecord(
                    plot_id=_plot_id(image.relative_path),
                    image=image,
                    association_confidence=AssociationConfidence.NONE,
                    association_reason="Architecture result figure",
                    mode=PlotMode.STATIC,
                )
            )
    return records


def _architecture_result_figure_dirs(project_root: Path) -> list[Path]:
    directories: list[Path] = []
    for directory in _walk_candidate_directories(project_root):
        if _path_has_suffix_parts(directory, project_root, RESULT_FIGURE_PARTS):
            directories.append(directory)
    return sorted(directories, key=lambda item: item.relative_to(project_root).as_posix().lower())


def _is_reference_artifact_path(relative_path: Path) -> bool:
    parts = tuple(part.lower() for part in relative_path.parts)
    if ".mplgallery" in parts or "_build" in parts or "runs" in parts:
        return False
    for index in range(0, max(0, len(parts) - len(RESULT_FIGURE_PARTS))):
        if parts[index : index + len(RESULT_FIGURE_PARTS) + 1] == RESULT_FIGURE_PARTS + ("mplgallery",):
            return False
    if len(parts) >= 3 and parts[-3:-1] == ("results", "runs"):
        return False
    return True


def _draft_csv(
    csv_path: Path,
    csv_root: Path,
    project_root: Path,
    workspace: CSVStudioWorkspace,
    manifest: ProjectManifest,
    sample_rows: int,
    *,
    redraw_override: RedrawMetadata | None = None,
    output_format: str = "svg",
) -> tuple[DatasetRecord, PlotRecord | None]:
    frame = pd.read_csv(csv_path, nrows=sample_rows)
    dataset = _dataset_record(csv_path, project_root, csv_root, frame=frame)
    if frame.empty and not frame.columns.size:
        return dataset.model_copy(update={"draft_status": "empty_csv"}), None

    numeric_columns = _numeric_columns(frame)
    categorical_columns = [str(column) for column in frame.columns if str(column) not in numeric_columns]
    if not numeric_columns:
        return (
            dataset.model_copy(
                update={
                    "columns": [str(column) for column in frame.columns],
                    "categorical_columns": categorical_columns,
                    "draft_status": "no_numeric_columns",
                }
            ),
            None,
        )

    draft = infer_pandas_draft(csv_path.relative_to(csv_root), frame)
    if draft is None:
        return dataset.model_copy(update={"draft_status": "no_draft_plot"}), None

    slug = _recipe_slug(csv_path.relative_to(csv_root))
    plot_ready_path = workspace.plot_ready_dir / f"{slug}.csv"
    recipe_path = workspace.recipes_dir / f"{slug}.yaml"
    script_path = workspace.scripts_dir / f"render_{slug}.py"
    cache_path = _draft_figure_path(
        csv_root,
        project_root,
        csv_path.relative_to(csv_root),
        slug,
        output_format=output_format,
    )
    redraw = redraw_override or draft.redraw
    plot_frame = draft.plot_frame
    plot_ready_path.parent.mkdir(parents=True, exist_ok=True)
    plot_frame.to_csv(plot_ready_path, index=False)

    manifest_plot_path = _relative_path_between(cache_path, csv_root)
    manifest_record = manifest.record_for_plot(manifest_plot_path)
    if manifest_record and manifest_record.redraw is not None:
        redraw = manifest_record.redraw

    recipe = PlotRecipeRecord(
        draft_engine="pandas",
        source_csv_path=csv_path.relative_to(csv_root),
        plot_ready_path=plot_ready_path.relative_to(csv_root),
        cache_path=manifest_plot_path,
        script_path=script_path.relative_to(csv_root),
        prep=TablePrepMetadata(selected_columns=[str(column) for column in plot_frame.columns]),
        redraw=redraw,
        sample_rows=sample_rows,
    )
    _write_recipe(recipe_path, recipe)
    _write_render_script(script_path, recipe)
    record = _render_record(
        project_root=project_root,
        csv_root=csv_root,
        source_csv=csv_path,
        plot_ready_csv=plot_ready_path,
        cache_path=cache_path,
        redraw=redraw,
        recipe_path=recipe_path,
        script_path=script_path,
    )
    manifest.upsert_record(
        ManifestRecord(
            plot_path=manifest_plot_path,
            raw_csv_path=csv_path.relative_to(csv_root),
            plot_csv_path=plot_ready_path.relative_to(csv_root),
            redraw=redraw,
            notes="MPLGallery CSV draft",
        )
    )

    return (
        dataset.model_copy(
            update={
                "columns": [str(column) for column in frame.columns],
                "numeric_columns": numeric_columns,
                "categorical_columns": categorical_columns,
                "draft_status": "drafted",
                "recipe_path": recipe_path,
                "plot_ready_path": plot_ready_path,
                "cache_path": cache_path,
                "associated_plot_id": record.plot_id,
            }
        ),
        record,
    )


def _render_record(
    *,
    project_root: Path,
    csv_root: Path,
    source_csv: Path,
    plot_ready_csv: Path,
    cache_path: Path,
    redraw: RedrawMetadata,
    recipe_path: Path,
    script_path: Path,
) -> PlotRecord:
    frame = pd.read_csv(plot_ready_csv)
    fig, _ax = render_pandas_draft_figure(frame, redraw, fallback_title=cache_path.stem)
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        fig.tight_layout()
        fig.savefig(cache_path, format=cache_path.suffix.removeprefix(".") or "svg")
    finally:
        plt.close(fig)

    image = _discovered_file(cache_path, project_root, FileKind.IMAGE)
    raw_csv = _discovered_file(source_csv, project_root, FileKind.CSV)
    plot_csv = _discovered_file(plot_ready_csv, project_root, FileKind.CSV)
    csv_stat = plot_ready_csv.stat()
    return PlotRecord(
        plot_id=_plot_id(image.relative_path),
        image=image,
        csv=plot_csv,
        raw_csv=raw_csv,
        plot_csv=plot_csv,
        association_confidence=AssociationConfidence.EXACT,
        association_reason="MPLGallery CSV draft",
        redraw=redraw,
        cache=CacheMetadata(
            cache_path=cache_path,
            source_size_bytes=csv_stat.st_size,
            source_modified_at=_modified_at(plot_ready_csv),
        ),
        recipe_path=recipe_path,
        mode=PlotMode.RECIPE,
        source_dataset_id=_dataset_id(raw_csv.relative_path),
        owned_by_mplgallery=True,
        visibility_role="draft",
        metadata_files=[recipe_path, script_path],
    )


def _non_mutating_dataset_records(csv_root: CSVRootRecord, project_root: Path) -> list[DatasetRecord]:
    manifest = load_manifest(csv_root.path)
    records: list[DatasetRecord] = []
    for csv_path in _csvs_for_root(csv_root.path):
        recipe_path = _recipe_path_for_csv(csv_path, csv_root.path)
        matched = _manifest_record_for_source(manifest, csv_path.relative_to(csv_root.path))
        plot_path = _resolved_manifest_path(csv_root.path, matched.plot_path) if matched else None
        plot_ready_path = (
            _resolved_manifest_path(csv_root.path, matched.plot_csv_path)
            if matched and matched.plot_csv_path
            else None
        )
        try:
            frame = pd.read_csv(csv_path, nrows=DEFAULT_SAMPLE_ROWS)
        except Exception:
            frame = None
        records.append(
            _dataset_record(csv_path, project_root, csv_root.path, frame=frame).model_copy(
                update={
                    "draft_status": "drafted" if recipe_path.exists() else "not_initialized",
                    "recipe_path": recipe_path if recipe_path.exists() else None,
                    "plot_ready_path": plot_ready_path,
                    "cache_path": plot_path,
                    "associated_plot_id": _plot_id(_relative_to(plot_path, project_root))
                    if plot_path and plot_path.exists()
                    else None,
                }
            )
        )
    return records


def _manifest_record_for_source(
    manifest: ProjectManifest,
    source_csv_path: Path,
) -> ManifestRecord | None:
    normalized = source_csv_path.as_posix()
    for record in manifest.records:
        if record.raw_csv_path and record.raw_csv_path.as_posix() == normalized:
            return record
        if record.csv_path and record.csv_path.as_posix() == normalized:
            return record
    return None


def _dataset_record(
    csv_path: Path,
    project_root: Path,
    csv_root: Path,
    *,
    frame: pd.DataFrame | None = None,
) -> DatasetRecord:
    columns: list[str] = []
    numeric_columns: list[str] = []
    categorical_columns: list[str] = []
    row_count = 0
    if frame is not None:
        columns = [str(column) for column in frame.columns]
        numeric_columns = _numeric_columns(frame)
        categorical_columns = [column for column in columns if column not in numeric_columns]
        row_count = len(frame)
    return DatasetRecord(
        dataset_id=_dataset_id(_relative_to(csv_path, project_root)),
        display_name=csv_path.name,
        path=csv_path,
        relative_path=_relative_to(csv_path, project_root),
        csv_root=csv_root,
        csv_root_relative_path=_relative_to(csv_root, project_root),
        row_count_sampled=row_count,
        columns=columns,
        numeric_columns=numeric_columns,
        categorical_columns=categorical_columns,
    )


def _direct_csvs(directory: Path) -> list[Path]:
    return sorted(
        (path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".csv"),
        key=lambda path: path.name.lower(),
    )


def _csvs_for_root(directory: Path) -> list[Path]:
    csvs: list[Path] = []
    for path in _iter_supported_files(directory, directory, suffixes={".csv"}):
        local_parts = {part.lower() for part in path.relative_to(directory).parts}
        if "raw" in local_parts:
            continue
        if ".mplgallery" in local_parts or "_build" in local_parts:
            continue
        if local_parts & (STUDIO_IGNORE_DIRS - CSV_ROOT_NAMES):
            continue
        csvs.append(path)
    return sorted(csvs, key=lambda path: path.relative_to(directory).as_posix().lower())


def _is_architecture_csv_root(directory: Path, project_root: Path) -> bool:
    if directory.name.lower() in CSV_ROOT_NAMES:
        return True
    if directory.name.lower() == "plots":
        return True
    return _path_has_suffix_parts(directory, project_root, RESULT_TABLE_PARTS)


def _path_has_suffix_parts(path: Path, root: Path, suffix_parts: tuple[str, ...]) -> bool:
    try:
        parts = tuple(part.lower() for part in path.relative_to(root).parts)
    except ValueError:
        return False
    return len(parts) >= len(suffix_parts) and parts[-len(suffix_parts) :] == suffix_parts


def _walk_candidate_directories(root: Path) -> list[Path]:
    directories: list[Path] = []
    for current_root, dir_names, _ in os.walk(root):
        directory = Path(current_root)
        if _is_ignored_directory(directory, root):
            dir_names[:] = []
            continue
        directories.append(directory)
        dir_names[:] = sorted(
            (name for name in dir_names if not _is_ignored_directory(directory / name, root)),
            reverse=True,
        )
    return directories


def _iter_supported_files(root: Path, project_root: Path, *, suffixes: set[str]) -> list[Path]:
    files: list[Path] = []
    for current_root, dir_names, file_names in os.walk(root):
        directory = Path(current_root)
        if _is_ignored_directory(directory, project_root):
            dir_names[:] = []
            continue
        dir_names[:] = [
            name
            for name in dir_names
            if not _is_ignored_directory(directory / name, project_root)
        ]
        for file_name in file_names:
            path = directory / file_name
            if path.suffix.lower() in suffixes:
                files.append(path)
    return sorted(files, key=lambda path: path.relative_to(project_root).as_posix().lower())


def _is_ignored_directory(directory: Path, project_root: Path) -> bool:
    if directory == project_root:
        return False
    parts = {part.lower() for part in directory.relative_to(project_root).parts}
    if "_build" in parts:
        return True
    return bool(parts & STUDIO_IGNORE_DIRS)


def _count_ignored_directories(root: Path) -> int:
    count = 0
    for current_root, dir_names, _ in os.walk(root):
        directory = Path(current_root)
        kept: list[str] = []
        for name in dir_names:
            child = directory / name
            if _is_ignored_directory(child, root):
                count += 1
            else:
                kept.append(name)
        dir_names[:] = kept
    return count


def _numeric_columns(frame: pd.DataFrame) -> list[str]:
    numeric: list[str] = []
    for column in frame.columns:
        values = pd.to_numeric(frame[column], errors="coerce")
        if values.notna().any():
            numeric.append(str(column))
    return numeric


def _recipe_slug(relative_csv_path: Path) -> str:
    normalized = relative_csv_path.with_suffix("").as_posix()
    stem = re.sub(r"[^A-Za-z0-9]+", "_", normalized).strip("_").lower() or "table"
    return stem


def _dataset_id(relative_path: Path) -> str:
    return relative_path.with_suffix("").as_posix().replace("/", "__")


def _draft_figure_path(
    csv_root: Path,
    project_root: Path,
    relative_csv_path: Path,
    slug: str,
    *,
    output_format: str = "svg",
) -> Path:
    figures_dir = _draft_figures_dir(csv_root, project_root)
    suffix = output_format.lower().lstrip(".")
    if suffix not in {"svg", "png"}:
        suffix = "svg"
    return figures_dir / f"{slug}.{suffix}"


def _draft_figures_dir(csv_root: Path, project_root: Path) -> Path:
    if _path_has_suffix_parts(csv_root, project_root, RESULT_TABLE_PARTS):
        return csv_root.parent / "figures"
    if csv_root.name.lower() == "plots":
        return csv_root
    if csv_root.name.lower() == "data":
        return csv_root.parent / "results" / "final" / "figures"
    return project_root / "results" / "final" / "figures"


def _relative_path_between(path: Path, root: Path) -> Path:
    return Path(os.path.relpath(path, root))


def _resolved_manifest_path(manifest_root: Path, path: Path | None) -> Path | None:
    if path is None:
        return None
    candidate = path if path.is_absolute() else manifest_root / path
    return candidate.resolve()


def _manifest_records_by_absolute_plot(project_root: Path) -> dict[Path, tuple[Path, ManifestRecord]]:
    matches: dict[Path, tuple[Path, ManifestRecord]] = {}
    for directory in _walk_candidate_directories(project_root):
        manifest_path = directory / ".mplgallery" / "manifest.yaml"
        if not manifest_path.exists():
            continue
        manifest_root = directory
        manifest = load_manifest(manifest_root)
        for record in manifest.records:
            plot_path = _resolved_manifest_path(manifest_root, record.plot_path)
            if plot_path is not None:
                matches[plot_path] = (manifest_root, record)
    return matches


def _infer_csv_root_for_dataset(csv_path: Path, project_root: Path | str | None) -> Path:
    if project_root is not None:
        project = Path(project_root).expanduser().resolve()
        containing_roots = [
            root.path for root in find_csv_roots(project) if csv_path == root.path or csv_path.is_relative_to(root.path)
        ]
        if containing_roots:
            return max(containing_roots, key=lambda path: len(path.parts))
    for parent in [csv_path.parent, *csv_path.parents]:
        if parent.name.lower() in CSV_ROOT_NAMES:
            return parent
        parts = tuple(part.lower() for part in parent.parts)
        if len(parts) >= len(RESULT_TABLE_PARTS) and parts[-len(RESULT_TABLE_PARTS) :] == RESULT_TABLE_PARTS:
            return parent
    return csv_path.parent


def _recipe_path_for_csv(csv_path: Path, csv_root: Path) -> Path:
    return csv_root / ".mplgallery" / "recipes" / f"{_recipe_slug(csv_path.relative_to(csv_root))}.yaml"


def _write_recipe(recipe_path: Path, recipe: PlotRecipeRecord) -> None:
    recipe_path.parent.mkdir(parents=True, exist_ok=True)
    data = recipe.model_dump(mode="json", exclude_none=True)
    for key in ("source_csv_path", "plot_ready_path", "cache_path", "script_path"):
        if key in data:
            data[key] = Path(data[key]).as_posix()
    recipe_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _write_render_script(script_path: Path, recipe: PlotRecipeRecord) -> None:
    script_path.parent.mkdir(parents=True, exist_ok=True)
    payload = recipe.redraw.model_dump(mode="json", exclude_none=True)
    script_path.write_text(
        generated_script_text(payload, recipe.plot_ready_path, recipe.cache_path),
        encoding="utf-8",
    )


def _discovered_file(path: Path, project_root: Path, kind: FileKind) -> DiscoveredFile:
    stat = path.stat()
    modified_at = _modified_at(path)
    return DiscoveredFile(
        path=path,
        relative_path=_relative_to(path, project_root),
        kind=kind,
        suffix=path.suffix.lower(),
        stem=path.stem,
        parent_dir=_relative_to(path.parent, project_root),
        size_bytes=stat.st_size,
        modified_at=modified_at,
        created_at=datetime.fromtimestamp(stat.st_ctime),
        image_format=path.suffix.removeprefix(".").upper() if kind is FileKind.IMAGE else None,
    )


def _modified_at(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime)


def _relative_to(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def _plot_id(relative_path: Path) -> str:
    return relative_path.with_suffix("").as_posix().replace("/", "__")
