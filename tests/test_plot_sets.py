from __future__ import annotations

from pathlib import Path
import json
import subprocess

import yaml

from mplgallery.core.plot_sets import apply_mpl_yaml, discover_plot_sets, load_mpl_yaml
from mplgallery.core.studio import build_csv_studio_index


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_plot_set_scanner_discovers_only_results_by_default(tmp_path: Path) -> None:
    write(tmp_path / "data" / "processed" / "ignored.csv", "x,y\n0,1\n")
    write(tmp_path / "results" / "response_curve" / "response_curve.csv", "time_s,response\n0,1\n")
    write(tmp_path / "results" / "response_curve" / "response_curve.svg", "<svg></svg>")
    write(tmp_path / "results" / "response_curve" / "response_curve.png", "not-real")
    write(
        tmp_path / "results" / "response_curve" / "response_curve.mpl.yaml",
        "version: 1\nplot_id: response_curve\nmatplotlib:\n  x: x\n  y:\n    - y\n",
    )
    write(tmp_path / ".mplgallery" / "cache" / "internal.svg", "<svg></svg>")

    plot_sets = discover_plot_sets(tmp_path)

    assert [plot_set.plot_set_id for plot_set in plot_sets] == ["response_curve"]
    plot_set = plot_sets[0]
    assert plot_set.relative_path.as_posix() == "results/response_curve"
    assert [path.name for path in plot_set.csv_files] == ["response_curve.csv"]
    assert [path.name for path in plot_set.figure_files] == ["response_curve.png", "response_curve.svg"]
    assert plot_set.mpl_yaml_path is not None
    assert plot_set.editable is True


def test_mpl_yaml_parsing_supports_render_command_and_matplotlib_contract(tmp_path: Path) -> None:
    sidecar = write(
        tmp_path / "results" / "response_curve" / "response_curve.mpl.yaml",
        """
version: 1
plot_id: response_curve
title: Response curve
files:
  figures:
    - response_curve.svg
  data:
    - response_curve.csv
render:
  command: uv run python scripts/render_figures.py --plot response_curve
matplotlib:
  kind: line
  x: time_s
  title: Response curve
  xlabel: Time
  xlabel_unit: "$\\\\mathrm{s}$"
  ylabel: Response
  grid: true
  legend_location: best
  figure:
    width_inches: 6
    height_inches: 4
    dpi: 150
  series:
    - y: response
      label: Model
      color: "#1f77b4"
      linestyle: "-"
      marker: "o"
""".lstrip(),
    )

    sidecar_record = load_mpl_yaml(sidecar)

    assert sidecar_record.plot_id == "response_curve"
    assert sidecar_record.title == "Response curve"
    assert sidecar_record.render_command == "uv run python scripts/render_figures.py --plot response_curve"
    assert sidecar_record.figure_files == [Path("response_curve.svg")]
    assert sidecar_record.data_files == [Path("response_curve.csv")]
    assert sidecar_record.redraw is not None
    assert sidecar_record.redraw.x == "time_s"
    assert sidecar_record.redraw.xlabel_unit == "$\\mathrm{s}$"
    assert sidecar_record.redraw.figure.width_inches == 6
    assert sidecar_record.redraw.series[0].color == "#1f77b4"


def test_apply_mpl_yaml_helper_updates_matplotlib_axes(tmp_path: Path) -> None:
    import matplotlib.pyplot as plt

    sidecar = write(
        tmp_path / "results" / "response_curve" / "response_curve.mpl.yaml",
        """
version: 1
plot_id: response_curve
matplotlib:
  title: Response curve
  xlabel: Time
  xlabel_unit: "$\\\\mathrm{s}$"
  ylabel: Response
  grid: true
  legend_location: upper left
""".lstrip(),
    )
    figure, ax = plt.subplots()
    ax.plot([0, 1], [0, 1], label="Model")

    apply_mpl_yaml(ax, sidecar)

    assert ax.get_title() == "Response curve"
    assert ax.get_xlabel() == "Time ($\\mathrm{s}$)"
    assert ax.get_ylabel() == "Response"
    assert ax.get_legend() is not None
    plt.close(figure)


def test_existing_figures_without_mpl_yaml_are_view_only(tmp_path: Path) -> None:
    write(tmp_path / "results" / "static_only" / "static_only.svg", "<svg></svg>")

    plot_sets = discover_plot_sets(tmp_path)

    assert len(plot_sets) == 1
    assert plot_sets[0].plot_set_id == "static_only"
    assert plot_sets[0].editable is False
    assert plot_sets[0].render_command is None


def test_plot_set_manifest_never_infers_render_command_from_python_files(tmp_path: Path) -> None:
    write(tmp_path / "scripts" / "render_figures.py", "print('not inferred')\n")
    write(tmp_path / "results" / "response_curve" / "response_curve.csv", "x,y\n0,1\n")
    write(tmp_path / "results" / "response_curve" / "response_curve.svg", "<svg></svg>")
    write(
        tmp_path / "results" / "response_curve" / "response_curve.mpl.yaml",
        "version: 1\nplot_id: response_curve\nmatplotlib:\n  x: x\n  y:\n    - y\n",
    )

    plot_sets = discover_plot_sets(tmp_path)

    assert plot_sets[0].editable is True
    assert plot_sets[0].render_command is None


def test_csv_studio_index_exposes_plot_sets_without_mplgallery_internals(tmp_path: Path) -> None:
    write(tmp_path / "results" / "response_curve" / "response_curve.csv", "x,y\n0,1\n")
    write(tmp_path / "results" / "response_curve" / "response_curve.svg", "<svg></svg>")
    write(
        tmp_path / "results" / "response_curve" / "response_curve.mpl.yaml",
        "version: 1\nplot_id: response_curve\nmatplotlib:\n  x: x\n  y:\n    - y\n",
    )
    write(tmp_path / "results" / ".mplgallery" / "cache" / "noise.svg", "<svg></svg>")

    index = build_csv_studio_index(tmp_path, ensure_drafts=False)

    assert [plot_set.plot_set_id for plot_set in index.plot_sets] == ["response_curve"]
    assert [record.plot_id for record in index.records] == ["results__response_curve__response_curve"]
    assert index.records[0].redraw is not None
    assert index.records[0].mode.value == "recipe"
    assert index.records[0].metadata_files == [tmp_path / "results" / "response_curve" / "response_curve.mpl.yaml"]
    assert all(".mplgallery" not in path.as_posix() for plot_set in index.plot_sets for path in plot_set.figure_files)
    serialized = yaml.safe_load(index.model_dump_json())
    assert serialized["plot_sets"][0]["plot_set_id"] == "response_curve"


def test_scan_cli_json_reports_plot_sets(tmp_path: Path) -> None:
    write(tmp_path / "results" / "response_curve" / "response_curve.csv", "x,y\n0,1\n")
    write(tmp_path / "results" / "response_curve" / "response_curve.svg", "<svg></svg>")
    write(tmp_path / "results" / "response_curve" / "response_curve.mpl.yaml", "version: 1\nplot_id: response_curve\n")

    completed = subprocess.run(
        ["uv", "run", "mplgallery", "scan", str(tmp_path), "--json"],
        cwd=Path(__file__).parents[1],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["mode"] == "plot-set-manager"
    assert payload["plot_sets_discovered"] == 1
    assert payload["plot_sets"][0]["plot_set_id"] == "response_curve"
    assert payload["plot_sets"][0]["editable"] is True
