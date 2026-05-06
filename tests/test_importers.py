from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from mplgallery.cli import app
from mplgallery.core.associations import build_plot_records
from mplgallery.core.importers import import_epcsaft_manifest
from mplgallery.core.manifest import diagnose_manifest_references, load_manifest
from mplgallery.core.scanner import scan_project


def touch(path: Path, content: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def test_import_epcsaft_manifest_writes_png_and_svg_records(tmp_path: Path) -> None:
    touch(tmp_path / "docs" / "plots" / "alpha.png")
    touch(tmp_path / "docs" / "plots" / "alpha.svg")
    touch(tmp_path / "docs" / "plots" / "alpha_plot_data.csv", "x,y\n0,1\n")
    manifest_json = tmp_path / "docs" / "plots" / "manifest.json"
    manifest_json.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "output_path": "docs/plots/alpha.png",
                        "svg_path": "docs/plots/alpha.svg",
                        "data_path": "docs/plots/alpha_plot_data.csv",
                        "source_path": "examples/alpha.py",
                        "title": "Alpha plot",
                    }
                ]
            }
        )
    )

    result = import_epcsaft_manifest(manifest_json, project_root=tmp_path)
    records = load_manifest(tmp_path).records
    plot_records = build_plot_records(scan_project(tmp_path), manifest=load_manifest(tmp_path))

    assert result.records_imported == 2
    assert result.missing_plot_paths == []
    assert result.missing_csv_paths == []
    assert [record.plot_path.as_posix() for record in records] == [
        "docs/plots/alpha.png",
        "docs/plots/alpha.svg",
    ]
    assert all(record.redraw and record.redraw.title == "Alpha plot" for record in records)
    assert all(record.csv is not None for record in plot_records)
    assert {record.association_reason for record in plot_records} == {"manifest override"}


def test_import_epcsaft_manifest_dry_run_reports_missing_files(tmp_path: Path) -> None:
    manifest_json = tmp_path / "manifest.json"
    manifest_json.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "output_path": "docs/plots/missing.png",
                        "svg_path": "docs/plots/missing.svg",
                        "data_path": "docs/plots/missing.csv",
                    }
                ]
            }
        )
    )

    result = import_epcsaft_manifest(manifest_json, project_root=tmp_path, dry_run=True)

    assert result.records_imported == 2
    assert result.manifest_path is None
    assert [path.as_posix() for path in result.missing_plot_paths] == [
        "docs/plots/missing.png",
        "docs/plots/missing.svg",
    ]
    assert [path.as_posix() for path in result.missing_csv_paths] == [
        "docs/plots/missing.csv"
    ]
    assert not (tmp_path / ".mplgallery" / "manifest.yaml").exists()


def test_validate_command_reports_missing_manifest_artifacts(tmp_path: Path) -> None:
    manifest_dir = tmp_path / ".mplgallery"
    manifest_dir.mkdir()
    (manifest_dir / "manifest.yaml").write_text(
        """
version: 1
records:
  - plot_path: plots/missing.png
    plot_csv_path: data/missing.csv
""".lstrip()
    )

    diagnostics = diagnose_manifest_references(tmp_path)
    result = CliRunner().invoke(app, ["validate", str(tmp_path)])

    assert diagnostics.has_errors is True
    assert result.exit_code == 1
    assert "Missing plot images: 1" in result.output
    assert "Missing CSV files: 1" in result.output


def test_scan_json_includes_manifest_diagnostics(tmp_path: Path) -> None:
    manifest_dir = tmp_path / ".mplgallery"
    manifest_dir.mkdir()
    (manifest_dir / "manifest.yaml").write_text(
        """
version: 1
records:
  - plot_path: plots/missing.png
    plot_csv_path: data/missing.csv
""".lstrip()
    )

    result = CliRunner().invoke(app, ["scan", str(tmp_path), "--json"])

    assert result.exit_code == 0
    assert '"manifest_records": 1' in result.output
    assert '"plots_discovered": 0' in result.output
    assert '"plots/missing.png"' in result.output
