from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pytest

from mplgallery.core.associations import build_plot_records
from mplgallery.core.manifest import ProjectManifest
from mplgallery.core.models import RedrawMetadata
from mplgallery.core.renderer import render_cached_plot, render_matplotlib_figure
from mplgallery.core.scanner import scan_project


def touch(path: Path, content: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def test_render_cached_plot_reads_csv_with_pandas_and_preserves_original(tmp_path: Path) -> None:
    image_path = touch(tmp_path / "plots" / "alpha.png", "original image")
    data_path = tmp_path / "data" / "alpha.csv"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"time_s": [0, 1, 2], "value": [1.0, 1.5, 2.0], "fit": [1.1, 1.4, 2.1]}).to_csv(
        data_path,
        index=False,
    )
    manifest = ProjectManifest.from_mapping(
        {
            "records": [
                {
                    "plot_path": "plots/alpha.png",
                    "csv_path": "data/alpha.csv",
                    "redraw": {
                        "kind": "line",
                        "x": "time_s",
                        "y": ["value", "fit"],
                        "title": "Alpha Redraw",
                        "xlabel": "time_s",
                        "ylabel": "value",
                        "figure": {"width_inches": 4.0, "height_inches": 3.0, "dpi": 120},
                    },
                }
            ]
        }
    )
    [record] = build_plot_records(scan_project(tmp_path), manifest=manifest)

    updated = render_cached_plot(tmp_path, record)

    assert updated.cache is not None
    assert updated.cache.cache_path is not None
    assert updated.cache.cache_path.exists()
    assert updated.cache.cache_path.suffix == ".png"
    assert image_path.read_text() == "original image"


def test_render_cached_plot_reads_plot_ready_csv_instead_of_raw_csv(tmp_path: Path) -> None:
    raw_path = tmp_path / "data" / "raw" / "alpha_raw.csv"
    plot_csv_path = tmp_path / "data" / "plot_ready" / "alpha_plot.csv"
    image_path = touch(tmp_path / "plots" / "alpha.png", "original image")
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    plot_csv_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"time_s": [0, 1, 2], "signal": [1000, 1001, 1002]}).to_csv(
        raw_path,
        index=False,
    )
    pd.DataFrame({"time_s": [0, 1, 2], "signal": [1.0, 1.5, 2.0]}).to_csv(
        plot_csv_path,
        index=False,
    )
    raw_before = raw_path.read_bytes()
    artifact_before = image_path.read_bytes()
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

    updated = render_cached_plot(tmp_path, record)

    assert updated.cache is not None
    assert updated.cache.source_size_bytes == plot_csv_path.stat().st_size
    assert raw_path.read_bytes() == raw_before
    assert image_path.read_bytes() == artifact_before


def test_render_matplotlib_figure_applies_axes_figure_grid_and_series_styles() -> None:
    frame = pd.DataFrame({"time_s": [1.0, 2.0, 3.0], "signal": [2.0, 4.0, 8.0]})
    redraw = RedrawMetadata(
        kind="line",
        x="time_s",
        title="Styled Plot",
        xlabel="Elapsed time",
        ylabel="Response",
        xscale="linear",
        yscale="log",
        xlim=(1.0, 3.0),
        ylim=(1.0, 10.0),
        grid=True,
        figure={"width_inches": 5.5, "height_inches": 3.25, "dpi": 180},
        series=[
            {
                "y": "signal",
                "label": "Signal",
                "color": "#2a6f97",
                "linewidth": 2.5,
                "linestyle": "--",
                "marker": "s",
                "alpha": 0.7,
            }
        ],
    )

    fig, ax = render_matplotlib_figure(frame, redraw, fallback_title="Fallback")
    try:
        line = ax.get_lines()[0]
        assert ax.get_title() == "Styled Plot"
        assert ax.get_xlabel() == "Elapsed time"
        assert ax.get_ylabel() == "Response"
        assert ax.get_xscale() == "linear"
        assert ax.get_yscale() == "log"
        assert ax.get_xlim() == pytest.approx((1.0, 3.0))
        assert ax.get_ylim() == pytest.approx((1.0, 10.0))
        assert fig.get_size_inches().tolist() == pytest.approx([5.5, 3.25])
        assert fig.dpi == pytest.approx(180)
        assert line.get_label() == "Signal"
        assert line.get_color() == "#2a6f97"
        assert line.get_linewidth() == pytest.approx(2.5)
        assert line.get_linestyle() == "--"
        assert line.get_marker() == "s"
        assert line.get_alpha() == pytest.approx(0.7)
        assert ax.xaxis._major_tick_kw["gridOn"] is True
    finally:
        plt.close(fig)
