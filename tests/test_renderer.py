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


def test_render_cached_plot_uses_svg_cache_for_svg_artifacts(tmp_path: Path) -> None:
    image_path = touch(tmp_path / "plots" / "alpha.svg", "<svg></svg>")
    data_path = tmp_path / "data" / "alpha.csv"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"time_s": [0, 1, 2], "value": [1.0, 1.5, 2.0]}).to_csv(
        data_path,
        index=False,
    )
    manifest = ProjectManifest.from_mapping(
        {
            "records": [
                {
                    "plot_path": "plots/alpha.svg",
                    "csv_path": "data/alpha.csv",
                    "redraw": {"x": "time_s", "series": [{"y": "value"}]},
                }
            ]
        }
    )
    [record] = build_plot_records(scan_project(tmp_path), manifest=manifest)

    updated = render_cached_plot(tmp_path, record)

    assert updated.cache is not None
    assert updated.cache.cache_path is not None
    assert updated.cache.cache_path.exists()
    assert updated.cache.cache_path.suffix == ".svg"
    assert image_path.read_text() == "<svg></svg>"


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


def test_render_cached_plot_reuses_fresh_preview_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    image_path = touch(tmp_path / "plots" / "alpha.png", "original image")
    data_path = tmp_path / "data" / "alpha.csv"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"time_s": [0, 1, 2], "signal": [1.0, 1.5, 2.0]}).to_csv(data_path, index=False)
    manifest = ProjectManifest.from_mapping(
        {
            "records": [
                {
                    "plot_path": "plots/alpha.png",
                    "csv_path": "data/alpha.csv",
                    "redraw": {"x": "time_s", "series": [{"y": "signal"}]},
                }
            ]
        }
    )
    [record] = build_plot_records(scan_project(tmp_path), manifest=manifest)
    rendered = render_cached_plot(tmp_path, record)
    assert rendered.cache is not None
    assert rendered.cache.cache_path is not None

    def fail_render(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("fresh cache should avoid rerendering")

    monkeypatch.setattr("mplgallery.core.renderer.render_matplotlib_figure", fail_render)
    reused = render_cached_plot(tmp_path, record)

    assert reused.cache is not None
    assert reused.cache.cache_path == rendered.cache.cache_path
    assert image_path.read_text() == "original image"


def test_render_cached_plot_invalidates_cache_when_redraw_metadata_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    touch(tmp_path / "plots" / "alpha.png", "original image")
    data_path = tmp_path / "data" / "alpha.csv"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"time_s": [0, 1, 2], "signal": [1.0, 1.5, 2.0]}).to_csv(data_path, index=False)
    manifest = ProjectManifest.from_mapping(
        {
            "records": [
                {
                    "plot_path": "plots/alpha.png",
                    "csv_path": "data/alpha.csv",
                    "redraw": {"x": "time_s", "title": "Original", "series": [{"y": "signal"}]},
                }
            ]
        }
    )
    [record] = build_plot_records(scan_project(tmp_path), manifest=manifest)
    rendered = render_cached_plot(tmp_path, record)
    assert rendered.cache is not None
    assert rendered.cache.redraw_fingerprint is not None
    assert record.redraw is not None

    changed_record = record.model_copy(update={"redraw": record.redraw.model_copy(update={"title": "Changed"})})
    did_render = False

    def render_stub(*_args: object, **_kwargs: object) -> tuple[plt.Figure, plt.Axes]:
        nonlocal did_render
        did_render = True
        fig, ax = plt.subplots()
        ax.plot([0, 1], [0, 1])
        return fig, ax

    monkeypatch.setattr("mplgallery.core.renderer.render_matplotlib_figure", render_stub)
    rerendered = render_cached_plot(tmp_path, changed_record)

    assert did_render is True
    assert rerendered.cache is not None
    assert rerendered.cache.redraw_fingerprint is not None
    assert rerendered.cache.redraw_fingerprint != rendered.cache.redraw_fingerprint


def test_render_matplotlib_figure_applies_axes_figure_grid_and_series_styles() -> None:
    frame = pd.DataFrame({"time_s": [1.0, 2.0, 3.0], "signal": [2.0, 4.0, 8.0]})
    redraw = RedrawMetadata(
        kind="line",
        x="time_s",
        title="Styled Plot",
        xlabel="Elapsed time",
        xlabel_unit=r"$\mathrm{s}$",
        ylabel="Response",
        ylabel_unit=r"$\mathrm{V}$",
        xscale="linear",
        yscale="log",
        xlim=(1.0, 3.0),
        ylim=(1.0, 10.0),
        grid=True,
        legend_title="Signals",
        figure={"width_inches": 5.5, "height_inches": 3.25, "dpi": 180},
        series=[
            {
                "y": "signal",
                "label": "Signal",
                "color": "#2a6f97",
                "linewidth": 2.5,
                "linestyle": "--",
                "marker": "s",
                "markersize": 9,
                "alpha": 0.7,
                "zorder": 3,
            }
        ],
    )

    fig, ax = render_matplotlib_figure(frame, redraw, fallback_title="Fallback")
    try:
        line = ax.get_lines()[0]
        assert ax.get_title() == "Styled Plot"
        assert ax.get_xlabel() == r"Elapsed time ($\mathrm{s}$)"
        assert ax.get_ylabel() == r"Response ($\mathrm{V}$)"
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
        assert line.get_markersize() == pytest.approx(9)
        assert line.get_alpha() == pytest.approx(0.7)
        assert line.get_zorder() == pytest.approx(3)
        assert ax.xaxis._major_tick_kw["gridOn"] is True
        assert ax.get_legend().get_title().get_text() == "Signals"
    finally:
        plt.close(fig)


def test_render_matplotlib_figure_applies_bar_style_controls() -> None:
    frame = pd.DataFrame({"category": [0, 1, 2], "count": [3, 5, 4]})
    redraw = RedrawMetadata(
        kind="bar",
        x="category",
        title="Styled bars",
        grid=True,
        grid_axis="y",
        grid_alpha=0.4,
        series=[
            {
                "y": "count",
                "label": "Count",
                "color": "#9467bd",
                "edgecolor": "#17202f",
                "linewidth": 0.8,
                "hatch": "/",
                "bar_width": 0.5,
                "alpha": 0.65,
            }
        ],
    )

    fig, ax = render_matplotlib_figure(frame, redraw, fallback_title="Fallback")
    try:
        patch = ax.patches[0]
        assert len(ax.patches) == 3
        assert patch.get_hatch() == "/"
        assert patch.get_linewidth() == pytest.approx(0.8)
        assert patch.get_alpha() == pytest.approx(0.65)
        assert patch.get_width() == pytest.approx(0.5)
        assert ax.xaxis._major_tick_kw["gridOn"] is False
        assert ax.yaxis._major_tick_kw["gridOn"] is True
    finally:
        plt.close(fig)


def test_render_matplotlib_figure_supports_shared_subplot_figure() -> None:
    frame = pd.DataFrame(
        {
            "time_s": [0, 1, 2, 3],
            "response": [0.0, 0.8, 0.2, -0.1],
            "fit": [0.1, 0.7, 0.25, -0.05],
            "residual": [0.1, 0.1, 0.05, 0.05],
        }
    )
    redraw = RedrawMetadata(
        title="Shared figure",
        subplot_rows=2,
        subplot_cols=1,
        sharex=True,
        figure={"width_inches": 6.0, "height_inches": 5.0, "dpi": 120},
        subplots=[
            {
                "subplot_id": "response",
                "kind": "line",
                "x": "time_s",
                "title": "Response",
                "series": [
                    {"y": "response", "label": "Response", "color": "#1f77b4"},
                    {"y": "fit", "label": "Fit", "color": "#d62728", "linestyle": "--"},
                ],
            },
            {
                "subplot_id": "residual",
                "kind": "bar",
                "x": "time_s",
                "title": "Residual",
                "grid_axis": "y",
                "series": [{"y": "residual", "label": "Residual", "color": "#2ca02c"}],
            },
        ],
    )

    fig, ax = render_matplotlib_figure(frame, redraw, fallback_title="Fallback")
    try:
        visible_axes = [axis for axis in fig.axes if axis.get_visible()]
        assert ax is visible_axes[0]
        assert len(visible_axes) == 2
        assert fig._suptitle is not None
        assert fig._suptitle.get_text() == "Shared figure"
        assert visible_axes[0].get_title() == "Response"
        assert len(visible_axes[0].get_lines()) == 2
        assert visible_axes[1].get_title() == "Residual"
        assert len(visible_axes[1].patches) == 4
    finally:
        plt.close(fig)


def test_render_matplotlib_figure_supports_histogram_and_scatter_variants() -> None:
    hist_frame = pd.DataFrame({"residual": [0.1, 0.2, -0.1, 0.3, 0.0]})
    hist_redraw = RedrawMetadata(
        kind="hist",
        title="Histogram",
        xlabel="Residual",
        xlabel_unit=r"$\mathrm{mV}$",
        bins=8,
        series=[{"y": "residual", "color": "#ff7f0e", "alpha": 0.8}],
    )
    fig, ax = render_matplotlib_figure(hist_frame, hist_redraw, fallback_title="Fallback")
    try:
        assert ax.get_title() == "Histogram"
        assert ax.get_xlabel() == r"Residual ($\mathrm{mV}$)"
    finally:
        plt.close(fig)

    scatter_frame = pd.DataFrame({"x": [0, 1, 2], "y": [1.0, 1.2, 1.5]})
    scatter_redraw = RedrawMetadata(
        kind="scatter",
        x="x",
        series=[{"y": "y", "label": "Points", "color": "#2ca02c", "marker": "o", "alpha": 0.9}],
    )
    fig, ax = render_matplotlib_figure(scatter_frame, scatter_redraw, fallback_title="Fallback")
    try:
        assert ax.collections
        assert ax.get_legend().get_texts()[0].get_text() == "Points"
    finally:
        plt.close(fig)
