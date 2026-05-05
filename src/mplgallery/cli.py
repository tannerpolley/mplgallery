from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import typer

from mplgallery.core.associations import build_plot_records
from mplgallery.core.manifest import load_manifests
from mplgallery.core.scanner import scan_project

app = typer.Typer(help="Browse and manage Matplotlib-generated plot galleries.")


@app.command()
def scan(project_root: Path = typer.Argument(Path("."), help="Project directory to scan.")) -> None:
    """Scan a project for PNG/SVG plots and CSV data."""
    result = scan_project(project_root)
    manifest = load_manifests(result.project_root)
    records = build_plot_records(result, manifest=manifest)

    matched = sum(1 for record in records if record.csv is not None)
    typer.echo(f"Project: {result.project_root}")
    typer.echo(f"Files: {len(result.files)} discovered")
    typer.echo(f"Plots: {len(records)} discovered, {matched} matched to CSV")
    typer.echo(f"Ignored directories: {result.ignored_dir_count}")

    for record in records:
        csv_path = record.csv.relative_path.as_posix() if record.csv else "unmatched"
        typer.echo(
            f"- {record.plot_id}: {record.image.relative_path.as_posix()} -> {csv_path} "
            f"({record.association_confidence.value}; {record.association_reason})"
        )


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
