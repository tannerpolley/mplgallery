from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import typer

from mplgallery.core.associations import build_plot_records
from mplgallery.core.importers import import_epcsaft_manifest
from mplgallery.core.manifest import diagnose_manifest_references, load_manifests
from mplgallery.core.scanner import scan_project

app = typer.Typer(help="Browse and manage Matplotlib-generated plot galleries.")


@app.command()
def scan(
    project_root: Path = typer.Argument(Path("."), help="Project directory to scan."),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    """Scan a project for PNG/SVG plots and CSV data."""
    result = scan_project(project_root)
    manifest = load_manifests(result.project_root)
    records = build_plot_records(result, manifest=manifest)
    diagnostics = diagnose_manifest_references(result.project_root, manifest)

    matched = sum(1 for record in records if record.csv is not None)
    if json_output:
        typer.echo(
            json.dumps(
                {
                    "project_root": str(result.project_root),
                    "files_discovered": len(result.files),
                    "plots_discovered": len(records),
                    "plots_matched_to_csv": matched,
                    "ignored_directories": result.ignored_dir_count,
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
                            "confidence": record.association_confidence.value,
                            "reason": record.association_reason,
                        }
                        for record in records
                    ],
                },
                indent=2,
            )
        )
        return

    typer.echo(f"Project: {result.project_root}")
    typer.echo(f"Files: {len(result.files)} discovered")
    typer.echo(f"Plots: {len(records)} discovered, {matched} matched to CSV")
    typer.echo(f"Ignored directories: {result.ignored_dir_count}")
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

    for record in records:
        csv_path = record.csv.relative_path.as_posix() if record.csv else "unmatched"
        typer.echo(
            f"- {record.plot_id}: {record.image.relative_path.as_posix()} -> {csv_path} "
            f"({record.association_confidence.value}; {record.association_reason})"
        )


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
) -> None:
    """Launch the local Streamlit artifact browser."""
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
    raise typer.Exit(subprocess.run(command, check=False).returncode)


def main() -> None:
    app()
