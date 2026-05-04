from __future__ import annotations

from pathlib import Path

import typer

app = typer.Typer(help="Browse and manage Matplotlib-generated plot galleries.")


@app.command()
def scan(project_root: Path = typer.Argument(Path("."), help="Project directory to scan.")) -> None:
    """Placeholder for the Milestone 1 scanner command."""
    resolved_root = project_root.resolve()
    typer.echo(f"Scanner not implemented yet. Target project: {resolved_root}")


@app.command()
def serve(project_root: Path = typer.Argument(Path("."), help="Project directory to serve.")) -> None:
    """Placeholder for the future Streamlit UI command."""
    resolved_root = project_root.resolve()
    typer.echo(f"Streamlit UI not implemented yet. Target project: {resolved_root}")


def main() -> None:
    app()
