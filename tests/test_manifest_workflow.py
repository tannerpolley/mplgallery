from __future__ import annotations

from pathlib import Path

from mplgallery.core.associations import build_plot_records
from mplgallery.core.manifest import ProjectManifest, load_manifest, load_manifests, update_manifest_redraw
from mplgallery.core.models import RedrawMetadata
from mplgallery.core.scanner import scan_project


def touch(path: Path, content: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def test_manifest_parses_raw_and_plot_ready_csv_paths_with_series_metadata() -> None:
    manifest = ProjectManifest.from_mapping(
        {
            "records": [
                {
                    "plot_path": "plots/alpha.png",
                    "raw_csv_path": "data/raw/alpha_raw.csv",
                    "plot_csv_path": "data/plot_ready/alpha_plot.csv",
                    "redraw": {
                        "kind": "line",
                        "x": "time_s",
                        "title": "Alpha",
                        "xlabel": "Time (s)",
                        "ylabel": "Signal",
                        "xscale": "linear",
                        "yscale": "log",
                        "xlim": [0.0, 10.0],
                        "ylim": [0.1, 100.0],
                        "grid": False,
                        "figure": {"width_inches": 7.0, "height_inches": 3.5, "dpi": 180},
                        "series": [
                            {
                                "y": "signal",
                                "label": "Signal",
                                "color": "#2a6f97",
                                "linewidth": 2.5,
                                "linestyle": "--",
                                "marker": "s",
                                "alpha": 0.8,
                            }
                        ],
                    },
                }
            ]
        }
    )

    [record] = manifest.records

    assert record.raw_csv_path == Path("data/raw/alpha_raw.csv")
    assert record.plot_csv_path == Path("data/plot_ready/alpha_plot.csv")
    assert record.redraw is not None
    assert record.redraw.series[0].y == "signal"
    assert record.redraw.series[0].color == "#2a6f97"
    assert record.redraw.xlim == (0.0, 10.0)
    assert record.redraw.ylim == (0.1, 100.0)


def test_manifest_association_uses_plot_ready_csv_and_keeps_raw_csv_as_provenance(
    tmp_path: Path,
) -> None:
    touch(tmp_path / "plots" / "alpha.png")
    touch(tmp_path / "data" / "raw" / "alpha_raw.csv", "time_s,signal\n0,100\n")
    touch(tmp_path / "data" / "plot_ready" / "alpha_plot.csv", "time_s,signal\n0,1\n")
    manifest = ProjectManifest.from_mapping(
        {
            "records": [
                {
                    "plot_path": "plots/alpha.png",
                    "raw_csv_path": "data/raw/alpha_raw.csv",
                    "plot_csv_path": "data/plot_ready/alpha_plot.csv",
                    "redraw": {"x": "time_s", "series": [{"y": "signal"}]},
                }
            ]
        }
    )

    [record] = build_plot_records(scan_project(tmp_path), manifest=manifest)

    assert record.csv is not None
    assert record.csv.relative_path == Path("data/plot_ready/alpha_plot.csv")
    assert record.plot_csv is not None
    assert record.plot_csv.relative_path == Path("data/plot_ready/alpha_plot.csv")
    assert record.raw_csv is not None
    assert record.raw_csv.relative_path == Path("data/raw/alpha_raw.csv")


def test_metadata_update_persists_manifest_without_modifying_data_or_artifact(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / ".mplgallery" / "manifest.yaml"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        """
version: 1
records:
  - plot_path: plots/alpha.png
    raw_csv_path: data/raw/alpha_raw.csv
    plot_csv_path: data/plot_ready/alpha_plot.csv
    redraw:
      x: time_s
      series:
        - y: signal
""".lstrip()
    )
    raw_path = touch(tmp_path / "data" / "raw" / "alpha_raw.csv", "time_s,signal\n0,100\n")
    artifact_path = touch(tmp_path / "plots" / "alpha.png", "original image")
    raw_before = raw_path.read_bytes()
    artifact_before = artifact_path.read_bytes()

    update_manifest_redraw(
        tmp_path,
        Path("plots/alpha.png"),
        RedrawMetadata(
            x="time_s",
            title="Edited Alpha",
            xlabel="Elapsed time",
            series=[{"y": "signal", "color": "#c44e52"}],
        ),
    )

    updated = load_manifest(tmp_path).record_for_plot(Path("plots/alpha.png"))
    serialized = manifest_path.read_text()
    assert updated is not None
    assert updated.redraw is not None
    assert updated.redraw.title == "Edited Alpha"
    assert updated.redraw.series[0].color == "#c44e52"
    assert "raw_csv_path: data/raw/alpha_raw.csv" in serialized
    assert "plot_csv_path: data/plot_ready/alpha_plot.csv" in serialized
    assert raw_path.read_bytes() == raw_before
    assert artifact_path.read_bytes() == artifact_before


def test_nested_manifests_are_loaded_from_parent_scan_root(tmp_path: Path) -> None:
    project_a = tmp_path / "project_a"
    project_b = tmp_path / "project_b"
    touch(project_a / "plots" / "alpha.png")
    touch(project_a / "data" / "plot_ready" / "alpha_plot.csv", "x,y\n0,1\n")
    touch(project_b / "plots" / "beta.svg")
    touch(project_b / "data" / "plot_ready" / "beta_plot.csv", "x,z\n0,2\n")
    (project_a / ".mplgallery").mkdir(parents=True)
    (project_b / ".mplgallery").mkdir(parents=True)
    (project_a / ".mplgallery" / "manifest.yaml").write_text(
        """
version: 1
records:
  - plot_path: plots/alpha.png
    plot_csv_path: data/plot_ready/alpha_plot.csv
    redraw:
      x: x
      series:
        - y: y
""".lstrip()
    )
    (project_b / ".mplgallery" / "manifest.yaml").write_text(
        """
version: 1
records:
  - plot_path: plots/beta.svg
    plot_csv_path: data/plot_ready/beta_plot.csv
    redraw:
      kind: scatter
      x: x
      series:
        - y: z
""".lstrip()
    )

    records = build_plot_records(scan_project(tmp_path), manifest=load_manifests(tmp_path))

    assert [record.image.relative_path.as_posix() for record in records] == [
        "project_a/plots/alpha.png",
        "project_b/plots/beta.svg",
    ]
    assert records[0].plot_csv is not None
    assert records[0].plot_csv.relative_path.as_posix() == "project_a/data/plot_ready/alpha_plot.csv"
    assert records[1].plot_csv is not None
    assert records[1].plot_csv.relative_path.as_posix() == "project_b/data/plot_ready/beta_plot.csv"
    assert records[1].redraw is not None
    assert records[1].redraw.kind == "scatter"
