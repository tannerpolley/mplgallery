from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import typer

from mplgallery.core.importers import import_epcsaft_manifest
from mplgallery.core.manifest import diagnose_manifest_references
from mplgallery.core.studio import (
    build_csv_studio_index,
    draft_csv_root,
    import_artifact_references,
    init_csv_root,
)

app = typer.Typer(help="Browse and manage Matplotlib-generated plot galleries.")


@app.command()
def scan(
    project_root: Path = typer.Argument(Path("."), help="Project directory to scan."),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
    include_artifacts: bool = typer.Option(
        False,
        "--include-artifacts",
        help="Also include legacy PNG/SVG artifact-browser records.",
    ),
) -> None:
    """Scan a project for CSV roots and MPLGallery draft plot state."""
    index = build_csv_studio_index(project_root, include_artifacts=include_artifacts)
    diagnostics = diagnose_manifest_references(index.project_root)

    matched = sum(1 for record in index.records if record.csv is not None)
    if json_output:
        typer.echo(
            json.dumps(
                {
                    "mode": "csv-studio",
                    "project_root": str(index.project_root),
                    "csv_roots": [
                        {
                            "path": str(root.path),
                            "relative_path": root.relative_path.as_posix(),
                            "datasets": len(root.datasets),
                        }
                        for root in index.csv_roots
                    ],
                    "datasets": [
                        {
                            "path": str(dataset.path),
                            "relative_path": dataset.relative_path.as_posix(),
                            "csv_root": dataset.csv_root_relative_path.as_posix(),
                            "draft_status": dataset.draft_status,
                            "recipe_path": dataset.recipe_path.as_posix()
                            if dataset.recipe_path
                            else None,
                            "plot_ready_path": dataset.plot_ready_path.as_posix()
                            if dataset.plot_ready_path
                            else None,
                            "cache_path": dataset.cache_path.as_posix()
                            if dataset.cache_path
                            else None,
                        }
                        for dataset in index.datasets
                    ],
                    "files_discovered": len(index.datasets),
                    "plots_discovered": len(index.records),
                    "plots_matched_to_csv": matched,
                    "ignored_directories": index.ignored_dir_count,
                    "artifact_records": len(index.imported_artifacts),
                    "manifest_records": diagnostics.manifest_record_count,
                    "missing_plot_paths": [
                        path.as_posix() for path in diagnostics.missing_plot_paths
                    ],
                    "missing_csv_paths": [path.as_posix() for path in diagnostics.missing_csv_paths],
                    "records": [
                        {
                            "plot_id": record.plot_id,
                            "plot_path": record.image.relative_path.as_posix(),
                            "csv_path": record.csv.relative_path.as_posix() if record.csv else None,
                            "raw_csv_path": record.raw_csv.relative_path.as_posix()
                            if record.raw_csv
                            else None,
                            "plot_csv_path": record.plot_csv.relative_path.as_posix()
                            if record.plot_csv
                            else None,
                            "recipe_path": record.recipe_path.as_posix()
                            if record.recipe_path
                            else None,
                            "confidence": record.association_confidence.value,
                            "reason": record.association_reason,
                        }
                        for record in index.records
                    ],
                },
                indent=2,
            )
        )
        return

    typer.echo(f"Project: {index.project_root}")
    typer.echo("Mode: CSV Plot Studio")
    typer.echo(f"CSV roots: {len(index.csv_roots)}")
    typer.echo(f"Datasets: {len(index.datasets)}")
    typer.echo(f"Plots: {len(index.records)} discovered, {matched} matched to CSV")
    typer.echo(f"Ignored directories: {index.ignored_dir_count}")
    if diagnostics.missing_plot_paths:
        typer.echo(
            "Warning: manifest references "
            f"{len(diagnostics.missing_plot_paths)} missing plot image(s)."
        )
    if diagnostics.missing_csv_paths:
        typer.echo(
            "Warning: manifest references "
            f"{len(diagnostics.missing_csv_paths)} missing CSV file(s)."
        )

    for dataset in index.datasets:
        typer.echo(f"- dataset: {dataset.relative_path.as_posix()} ({dataset.draft_status})")
    for record in index.records:
        csv_path = record.csv.relative_path.as_posix() if record.csv else "unmatched"
        typer.echo(
            f"- {record.plot_id}: {record.image.relative_path.as_posix()} -> {csv_path} "
            f"({record.association_confidence.value}; {record.association_reason})"
        )


@app.command()
def init(
    data_folder: Path = typer.Argument(
        ...,
        help="CSV root to initialize, usually analyses/<id>/data or analyses/<id>/results/final/tables.",
    ),
) -> None:
    """Create the `.mplgallery` workspace beside a CSV folder without rendering."""
    workspace = init_csv_root(data_folder)
    typer.echo(f"Workspace: {workspace.root}")
    typer.echo(f"Manifest: {workspace.manifest_path}")


@app.command()
def draft(
    data_folder: Path = typer.Argument(
        ...,
        help="CSV root to draft, usually analyses/<id>/data or analyses/<id>/results/final/tables.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    """Create draft plot recipes, plot-ready CSVs, scripts, and cached previews."""
    root = Path(data_folder).expanduser().resolve()
    index = draft_csv_root(root, project_root=_project_root_for_csv_root(root))
    if json_output:
        typer.echo(
            json.dumps(
                {
                    "mode": "csv-studio-draft",
                    "csv_root": str(Path(data_folder).expanduser().resolve()),
                    "datasets": len(index.datasets),
                    "records": [
                        {
                            "plot_id": record.plot_id,
                            "plot_path": record.image.relative_path.as_posix(),
                            "csv_path": record.csv.relative_path.as_posix() if record.csv else None,
                            "recipe_path": record.recipe_path.as_posix()
                            if record.recipe_path
                            else None,
                        }
                        for record in index.records
                    ],
                },
                indent=2,
            )
        )
        return
    typer.echo(f"Datasets: {len(index.datasets)}")
    typer.echo(f"Draft plots: {len(index.records)}")


def _project_root_for_csv_root(csv_root: Path) -> Path:
    parts = tuple(part.lower() for part in csv_root.parts)
    if len(parts) >= 3 and parts[-3:] == ("results", "final", "tables"):
        return csv_root.parents[2]
    if csv_root.name.lower() == "data":
        return csv_root.parent
    return csv_root.parent


@app.command("import-artifacts")
def import_artifacts(
    folder: Path = typer.Argument(..., help="Folder containing PNG/SVG references to import."),
) -> None:
    """Import nearby PNG/SVG files as reference-only artifacts."""
    result = import_artifact_references(folder)
    typer.echo(f"Imported artifacts: {result.imported_count}")
    typer.echo(f"Manifest: {result.manifest_path}")


@app.command("import-manifest")
def import_manifest(
    manifest_json_path: Path = typer.Argument(..., help="Manifest JSON file to import."),
    project_root: Path = typer.Option(Path("."), "--project-root", help="Target project root."),
    format_name: str = typer.Option("epcsaft", "--format", help="Manifest format."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Report changes without writing YAML."),
) -> None:
    """Import an existing project plot manifest into .mplgallery/manifest.yaml."""
    if format_name != "epcsaft":
        raise typer.BadParameter("Only --format epcsaft is currently supported.")

    result = import_epcsaft_manifest(
        manifest_json_path,
        project_root=project_root,
        dry_run=dry_run,
    )
    typer.echo(f"Records imported: {result.records_imported}")
    if result.manifest_path is not None:
        typer.echo(f"Manifest written: {result.manifest_path}")
    else:
        typer.echo("Dry run: manifest was not written.")
    typer.echo(f"Missing plot images: {len(result.missing_plot_paths)}")
    typer.echo(f"Missing CSV files: {len(result.missing_csv_paths)}")


@app.command()
def validate(project_root: Path = typer.Argument(Path("."), help="Project directory to validate.")) -> None:
    """Validate manifest references against files present under a project root."""
    root = project_root.expanduser().resolve()
    diagnostics = diagnose_manifest_references(root)
    typer.echo(f"Manifest records: {diagnostics.manifest_record_count}")
    typer.echo(f"Missing plot images: {len(diagnostics.missing_plot_paths)}")
    for path in diagnostics.missing_plot_paths[:20]:
        typer.echo(f"- plot: {path.as_posix()}")
    typer.echo(f"Missing CSV files: {len(diagnostics.missing_csv_paths)}")
    for path in diagnostics.missing_csv_paths[:20]:
        typer.echo(f"- csv: {path.as_posix()}")
    if diagnostics.has_errors:
        raise typer.Exit(1)


@app.command()
def serve(
    project_root: Path = typer.Argument(Path("."), help="Project directory to serve."),
    port: int | None = typer.Option(None, help="Streamlit server port."),
    choose_root: bool = typer.Option(
        False,
        "--choose-root",
        help="Open with the root chooser emphasized and use the last recent root when available.",
    ),
    include_artifacts: bool = typer.Option(
        False,
        "--include-artifacts",
        help="Also show explicitly imported/legacy PNG/SVG artifacts.",
    ),
) -> None:
    """Launch the local Streamlit CSV plot studio."""
    raise typer.Exit(
        _run_streamlit_app(
            project_root,
            port=port,
            include_artifacts=include_artifacts,
            choose_root=choose_root,
        )
    )


@app.command("run")
def run_app(
    project_root: Path = typer.Argument(Path("."), help="Project directory to run from."),
    port: int | None = typer.Option(None, help="Streamlit server port."),
    choose_root: bool = typer.Option(
        False,
        "--choose-root",
        help="Open with the root chooser emphasized and use the last recent root when available.",
    ),
    include_artifacts: bool = typer.Option(
        False,
        "--include-artifacts",
        help="Also show explicitly imported/legacy PNG/SVG artifacts.",
    ),
) -> None:
    """Launch the local Streamlit CSV plot studio."""
    raise typer.Exit(
        _run_streamlit_app(
            project_root,
            port=port,
            include_artifacts=include_artifacts,
            choose_root=choose_root,
        )
    )


def _run_streamlit_app(
    project_root: Path,
    *,
    port: int | None,
    include_artifacts: bool,
    choose_root: bool,
) -> int:
    resolved_root = project_root.expanduser().resolve()
    app_path = Path(__file__).parent / "ui" / "app.py"
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
    ]
    if port is not None:
        command.append(f"--server.port={port}")
    command.extend(["--", "--project-root", str(resolved_root)])
    if choose_root:
        command.append("--choose-root")
    if include_artifacts:
        command.append("--include-artifacts")
    return subprocess.run(command, check=False).returncode


def main() -> None:
    app()
