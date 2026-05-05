"""Headless Matplotlib rendering entry points."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from mplgallery.core.models import CacheMetadata, PlotRecord, RedrawMetadata, SeriesStyle

DEFAULT_COLOR_CYCLE = (
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
)
LATEX_UNIT_SUGGESTIONS = (
    "",
    r"$\mathrm{s}$",
    r"$\mathrm{ms}$",
    r"$\mu\mathrm{m}$",
    r"$\mathrm{mm}$",
    r"$\mathrm{cm}$",
    r"$\mathrm{m}$",
    r"$\mathrm{kg}$",
    r"$\mathrm{g}$",
    r"$\mathrm{mol}$",
    r"$\mathrm{K}$",
    r"$^\circ\mathrm{C}$",
)
PLOT_KIND_CHOICES = ("line", "scatter", "bar", "barh", "area", "hist", "step")
LEGEND_LOCATION_CHOICES = (
    "best",
    "upper right",
    "upper left",
    "lower left",
    "lower right",
    "right",
    "center left",
    "center right",
    "lower center",
    "upper center",
    "center",
)


def render_cached_plot(project_root: Path | str, record: PlotRecord) -> PlotRecord:
    """Render a metadata-backed plot into `.mplgallery/cache`.

    Rendering is intentionally CSV-only: pandas reads the associated CSV and no
    discovered Python scripts are executed.
    """
    root = Path(project_root).expanduser().resolve()
    source_csv = record.plot_csv or record.csv
    if source_csv is None or record.redraw is None:
        return record

    fresh_record = record_with_fresh_cache(root, record)
    if fresh_record is not None:
        return fresh_record

    frame = pd.read_csv(source_csv.path)
    fig, _ax = render_matplotlib_figure(frame, record.redraw, fallback_title=record.image.stem)
    try:
        cache_dir = root / ".mplgallery" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = _cache_path_for_record(root, record)
        fig.tight_layout()
        fig.savefig(cache_path)
    finally:
        plt.close(fig)

    csv_stat = source_csv.path.stat()
    return record.model_copy(
        update={
            "cache": CacheMetadata(
                cache_path=cache_path,
                source_size_bytes=csv_stat.st_size,
                source_modified_at=source_csv.modified_at,
            )
        }
    )


def record_with_fresh_cache(project_root: Path | str, record: PlotRecord) -> PlotRecord | None:
    """Return `record` with cache metadata when the preview is already fresh."""
    root = Path(project_root).expanduser().resolve()
    source_csv = record.plot_csv or record.csv
    if source_csv is None or record.redraw is None:
        return None

    cache_path = _cache_path_for_record(root, record)
    if not cache_path.exists():
        return None

    csv_stat = source_csv.path.stat()
    cache_stat = cache_path.stat()
    if cache_stat.st_mtime < csv_stat.st_mtime:
        return None

    return record.model_copy(
        update={
            "cache": CacheMetadata(
                cache_path=cache_path,
                source_size_bytes=csv_stat.st_size,
                source_modified_at=source_csv.modified_at,
            )
        }
    )


def _cache_path_for_record(project_root: Path, record: PlotRecord) -> Path:
    cache_suffix = record.image.suffix.lower() if record.image.suffix.lower() in {".png", ".svg"} else ".png"
    return project_root / ".mplgallery" / "cache" / f"{record.plot_id}{cache_suffix}"


def render_matplotlib_figure(
    frame: pd.DataFrame,
    redraw: RedrawMetadata,
    *,
    fallback_title: str,
) -> tuple[plt.Figure, plt.Axes]:
    """Build a Matplotlib figure from CSV data and manifest metadata."""
    if frame.empty:
        raise ValueError("CSV data is empty")
    x_column = redraw.x or frame.columns[0]
    series = _series_from_metadata(frame, redraw, x_column)
    if not series:
        raise ValueError("No y columns configured for redraw")

    figure = redraw.figure
    fig, ax = plt.subplots(
        figsize=(figure.width_inches, figure.height_inches),
        dpi=figure.dpi,
        facecolor=figure.facecolor,
        constrained_layout=bool(figure.constrained_layout) if figure.constrained_layout is not None else False,
    )

    try:
        kind = redraw.kind if redraw.kind in PLOT_KIND_CHOICES else "line"
        if kind == "hist":
            _render_histogram(ax, frame, series, redraw)
        elif kind == "bar":
            _render_bar(ax, frame, series[0], x_column, horizontal=False)
        elif kind == "barh":
            _render_bar(ax, frame, series[0], x_column, horizontal=True)
        elif kind == "area":
            _render_area(ax, frame, series[0], x_column)
        elif kind == "step":
            _render_step(ax, frame, series, x_column)
        else:
            for style in series:
                label = style.label or style.y
                if kind == "scatter":
                    ax.scatter(
                        frame[x_column],
                        frame[style.y],
                        label=label,
                        color=style.color,
                        edgecolors=style.edgecolor,
                        marker=style.marker,
                        s=(style.markersize or 6) ** 2,
                        alpha=style.alpha,
                        zorder=style.zorder,
                    )
                else:
                    ax.plot(
                        frame[x_column],
                        frame[style.y],
                        label=label,
                        color=style.color,
                        linewidth=style.linewidth,
                        linestyle=style.linestyle,
                        marker=style.marker if style.marker is not None else "o",
                        markersize=style.markersize or 3,
                        alpha=style.alpha,
                        zorder=style.zorder,
                    )

        ax.set_title(redraw.title or fallback_title)
        ax.set_xlabel(_compose_axis_label(redraw.xlabel or x_column, redraw.xlabel_unit))
        ax.set_ylabel(_compose_axis_label(redraw.ylabel or ", ".join(style.y for style in series), redraw.ylabel_unit))
        ax.set_xscale(redraw.xscale)
        ax.set_yscale(redraw.yscale)
        if redraw.xlim is not None:
            ax.set_xlim(redraw.xlim)
        if redraw.ylim is not None:
            ax.set_ylim(redraw.ylim)
        ax.grid(
            redraw.grid,
            axis=redraw.grid_axis or "both",
            alpha=redraw.grid_alpha if redraw.grid_alpha is not None else 0.25,
        )
        if len(series) > 1 or any(style.label for style in series):
            ax.legend(title=redraw.legend_title or None, loc=redraw.legend_location or "best")
    except Exception:
        plt.close(fig)
        raise
    return fig, ax


def _series_from_metadata(
    frame: pd.DataFrame,
    redraw: RedrawMetadata,
    x_column: str,
) -> list[SeriesStyle]:
    if redraw.series:
        return redraw.series
    if redraw.y:
        return [SeriesStyle(y=column) for column in redraw.y]
    return [SeriesStyle(y=column) for column in frame.columns if column != x_column]


def _compose_axis_label(label: str, unit: str | None) -> str:
    if not unit:
        return label
    if label.endswith(unit):
        return label
    return f"{label} ({unit})"


def _render_histogram(
    ax: plt.Axes,
    frame: pd.DataFrame,
    series: list[SeriesStyle],
    redraw: RedrawMetadata,
) -> None:
    columns = [style.y for style in series]
    hist_frame = frame[columns]
    hist_frame.plot.hist(
        ax=ax,
        bins=redraw.bins or 20,
        alpha=series[0].alpha if series[0].alpha is not None else 0.75,
        color=series[0].color or DEFAULT_COLOR_CYCLE[0],
        edgecolor=series[0].edgecolor,
        legend=len(columns) > 1,
    )
    for patch in ax.patches:
        if series[0].hatch:
            patch.set_hatch(series[0].hatch)
        if series[0].zorder is not None:
            patch.set_zorder(series[0].zorder)


def _render_bar(ax: plt.Axes, frame: pd.DataFrame, style: SeriesStyle, x_column: str, *, horizontal: bool) -> None:
    label = style.label or style.y
    common_kwargs = {
        "label": label,
        "color": style.color or DEFAULT_COLOR_CYCLE[0],
        "edgecolor": style.edgecolor,
        "linewidth": style.linewidth,
        "hatch": style.hatch,
        "alpha": style.alpha if style.alpha is not None else 1.0,
        "zorder": style.zorder,
    }
    if horizontal:
        if style.bar_width is not None:
            common_kwargs["height"] = style.bar_width
        ax.barh(
            frame[x_column],
            frame[style.y],
            **common_kwargs,
        )
    else:
        if style.bar_width is not None:
            common_kwargs["width"] = style.bar_width
        ax.bar(
            frame[x_column],
            frame[style.y],
            **common_kwargs,
        )


def _render_area(ax: plt.Axes, frame: pd.DataFrame, style: SeriesStyle, x_column: str) -> None:
    y = frame[style.y]
    x = frame[x_column]
    ax.fill_between(
        x,
        y,
        alpha=style.alpha if style.alpha is not None else 0.35,
        color=style.color or DEFAULT_COLOR_CYCLE[0],
        label=style.label or style.y,
        zorder=style.zorder,
    )
    ax.plot(
        x,
        y,
        color=style.color or DEFAULT_COLOR_CYCLE[0],
        linewidth=style.linewidth or 1.5,
        linestyle=style.linestyle or "-",
        zorder=style.zorder,
    )


def _render_step(ax: plt.Axes, frame: pd.DataFrame, series: list[SeriesStyle], x_column: str) -> None:
    for style in series:
        ax.step(
            frame[x_column],
            frame[style.y],
            where="mid",
            label=style.label or style.y,
            color=style.color or DEFAULT_COLOR_CYCLE[0],
            linewidth=style.linewidth or 1.5,
            alpha=style.alpha if style.alpha is not None else 1.0,
            zorder=style.zorder,
        )
