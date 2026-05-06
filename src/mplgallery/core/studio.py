"""CSV-first plot studio discovery, draft generation, and imports."""

from __future__ import annotations

import hashlib
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
    MatplotlibFigureAttributes,
    PlotMode,
    PlotRecipeRecord,
    PlotRecord,
    RedrawMetadata,
    SeriesStyle,
)
from mplgallery.core.renderer import DEFAULT_COLOR_CYCLE, render_matplotlib_figure
from mplgallery.core.scanner import scan_project

CSV_ROOT_NAMES = {"data", "out", "outputs", "result", "results"}
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
    """Find named CSV folders that MPLGallery owns beside source CSVs."""
    root = Path(project_root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Project root does not exist: {root}")

    roots: list[CSVRootRecord] = []
    for directory in _walk_candidate_directories(root):
        if directory.name.lower() not in CSV_ROOT_NAMES:
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
    include_artifacts: bool = False,
    sample_rows: int = DEFAULT_SAMPLE_ROWS,
) -> CSVStudioIndex:
    """Build the CSV-first index used by the CLI and Streamlit host."""
    root = Path(project_root).expanduser().resolve()
    csv_roots = find_csv_roots(root)
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

    imported_artifacts: list[PlotRecord] = []
    if include_artifacts:
        scan = scan_project(root)
        manifest = load_manifests(root)
        imported_artifacts = build_plot_records(scan, manifest=manifest)
        records.extend(imported_artifacts)
        ignored_count += scan.ignored_dir_count

    return CSVStudioIndex(
        project_root=root,
        csv_roots=csv_roots,
        datasets=datasets,
        records=records,
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


def _draft_csv(
    csv_path: Path,
    csv_root: Path,
    project_root: Path,
    workspace: CSVStudioWorkspace,
    manifest: ProjectManifest,
    sample_rows: int,
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

    slug = _recipe_slug(csv_path.relative_to(csv_root))
    plot_ready_path = workspace.plot_ready_dir / f"{slug}.csv"
    recipe_path = workspace.recipes_dir / f"{slug}.yaml"
    script_path = workspace.scripts_dir / f"render_{slug}.py"
    cache_path = workspace.cache_dir / f"{slug}.svg"
    redraw, plot_frame = _infer_draft_redraw(csv_path, frame, numeric_columns, categorical_columns)
    plot_ready_path.parent.mkdir(parents=True, exist_ok=True)
    plot_frame.to_csv(plot_ready_path, index=False)

    manifest_record = manifest.record_for_plot(cache_path.relative_to(csv_root))
    if manifest_record and manifest_record.redraw is not None:
        redraw = manifest_record.redraw

    recipe = PlotRecipeRecord(
        source_csv_path=csv_path.relative_to(csv_root),
        plot_ready_path=plot_ready_path.relative_to(csv_root),
        cache_path=cache_path.relative_to(csv_root),
        script_path=script_path.relative_to(csv_root),
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
            plot_path=cache_path.relative_to(csv_root),
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
            }
        ),
        record,
    )


def _infer_draft_redraw(
    csv_path: Path,
    frame: pd.DataFrame,
    numeric_columns: list[str],
    categorical_columns: list[str],
) -> tuple[RedrawMetadata, pd.DataFrame]:
    plot_frame = frame.copy()
    title = _human_title(csv_path.stem)
    if categorical_columns and len(numeric_columns) == 1:
        x_column = categorical_columns[0]
        y_columns = [numeric_columns[0]]
        kind = "bar"
    elif len(numeric_columns) >= 2:
        x_column = numeric_columns[0]
        y_columns = numeric_columns[1:5]
        kind = "line"
    else:
        x_column = "mplgallery_index"
        y_columns = [numeric_columns[0]]
        plot_frame.insert(0, x_column, range(len(plot_frame)))
        kind = "line"

    series = [
        SeriesStyle(
            y=column,
            label=_human_title(column),
            color=DEFAULT_COLOR_CYCLE[index % len(DEFAULT_COLOR_CYCLE)],
            linewidth=1.6,
            marker="o" if kind == "line" else None,
            markersize=4 if kind == "line" else None,
            alpha=0.9,
        )
        for index, column in enumerate(y_columns)
    ]
    return (
        RedrawMetadata(
            kind=kind,
            x=x_column,
            y=y_columns,
            title=title,
            xlabel=_human_title(x_column),
            ylabel=_human_title(y_columns[0]) if len(y_columns) == 1 else "Value",
            grid=True,
            figure=MatplotlibFigureAttributes(width_inches=7.0, height_inches=4.5, dpi=150),
            series=series,
        ),
        plot_frame,
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
    fig, _ax = render_matplotlib_figure(frame, redraw, fallback_title=cache_path.stem)
    try:
        fig.tight_layout()
        fig.savefig(cache_path, format="svg")
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
        metadata_files=[recipe_path, script_path],
    )


def _non_mutating_dataset_records(csv_root: CSVRootRecord, project_root: Path) -> list[DatasetRecord]:
    manifest = load_manifest(csv_root.path)
    records: list[DatasetRecord] = []
    for csv_path in _csvs_for_root(csv_root.path):
        recipe_path = _recipe_path_for_csv(csv_path, csv_root.path)
        matched = _manifest_record_for_source(manifest, csv_path.relative_to(csv_root.path))
        records.append(
            _dataset_record(csv_path, project_root, csv_root.path).model_copy(
                update={
                    "draft_status": "drafted" if recipe_path.exists() else "not_initialized",
                    "recipe_path": recipe_path if recipe_path.exists() else None,
                    "plot_ready_path": csv_root.path / matched.plot_csv_path
                    if matched and matched.plot_csv_path
                    else None,
                    "cache_path": csv_root.path / matched.plot_path if matched else None,
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
    for path in directory.rglob("*.csv"):
        if not path.is_file():
            continue
        local_parts = {part.lower() for part in path.relative_to(directory).parts}
        if ".mplgallery" in local_parts or "_build" in local_parts:
            continue
        if local_parts & (STUDIO_IGNORE_DIRS - CSV_ROOT_NAMES):
            continue
        csvs.append(path)
    return sorted(csvs, key=lambda path: path.relative_to(directory).as_posix().lower())


def _walk_candidate_directories(root: Path) -> list[Path]:
    directories: list[Path] = []
    stack = [root]
    while stack:
        directory = stack.pop()
        if _is_ignored_directory(directory, root):
            continue
        directories.append(directory)
        for child in sorted((item for item in directory.iterdir() if item.is_dir()), reverse=True):
            if not _is_ignored_directory(child, root):
                stack.append(child)
    return directories


def _is_ignored_directory(directory: Path, project_root: Path) -> bool:
    if directory == project_root:
        return False
    parts = {part.lower() for part in directory.relative_to(project_root).parts}
    if "_build" in parts:
        return True
    return bool(parts & STUDIO_IGNORE_DIRS)


def _count_ignored_directories(root: Path) -> int:
    count = 0
    stack = [root]
    while stack:
        directory = stack.pop()
        for child in (item for item in directory.iterdir() if item.is_dir()):
            if _is_ignored_directory(child, root):
                count += 1
            else:
                stack.append(child)
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
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:8]
    return f"{stem}_{digest}"


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
        "\n".join(
            [
                '"""Reproducible draft render script generated by MPLGallery."""',
                "",
                "from __future__ import annotations",
                "",
                "from pathlib import Path",
                "",
                "import matplotlib.pyplot as plt",
                "import pandas as pd",
                "",
                "",
                "ROOT = Path(__file__).resolve().parents[2]",
                f"PLOT_READY_CSV = ROOT / {recipe.plot_ready_path.as_posix()!r}",
                f"CACHE_PATH = ROOT / {recipe.cache_path.as_posix()!r}",
                f"REDRAW = {payload!r}",
                "",
                "",
                "def main() -> None:",
                "    frame = pd.read_csv(PLOT_READY_CSV)",
                "    fig, ax = plt.subplots(figsize=(",
                "        REDRAW.get('figure', {}).get('width_inches', 7.0),",
                "        REDRAW.get('figure', {}).get('height_inches', 4.5),",
                "    ), dpi=REDRAW.get('figure', {}).get('dpi', 150))",
                "    x = REDRAW.get('x') or frame.columns[0]",
                "    kind = REDRAW.get('kind', 'line')",
                "    for series in REDRAW.get('series', []):",
                "        y = series['y']",
                "        kwargs = {",
                "            'label': series.get('label') or y,",
                "            'color': series.get('color'),",
                "            'alpha': series.get('alpha'),",
                "        }",
                "        if kind == 'bar':",
                "            ax.bar(frame[x], frame[y], **kwargs)",
                "        elif kind == 'scatter':",
                "            ax.scatter(frame[x], frame[y], **kwargs)",
                "        else:",
                "            ax.plot(",
                "                frame[x],",
                "                frame[y],",
                "                linewidth=series.get('linewidth', 1.6),",
                "                linestyle=series.get('linestyle') or '-',",
                "                marker=series.get('marker'),",
                "                markersize=series.get('markersize', 4),",
                "                **kwargs,",
                "            )",
                "    ax.set_title(REDRAW.get('title') or CACHE_PATH.stem)",
                "    ax.set_xlabel(REDRAW.get('xlabel') or x)",
                "    ax.set_ylabel(REDRAW.get('ylabel') or '')",
                "    ax.grid(bool(REDRAW.get('grid', True)), alpha=0.25)",
                "    ax.legend(loc=REDRAW.get('legend_location') or 'best')",
                "    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)",
                "    fig.tight_layout()",
                "    fig.savefig(CACHE_PATH)",
                "    plt.close(fig)",
                "",
                "",
                "if __name__ == '__main__':",
                "    main()",
                "",
            ]
        ),
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


def _human_title(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").strip().title()
