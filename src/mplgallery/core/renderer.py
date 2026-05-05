"""Headless Matplotlib rendering entry points."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from mplgallery.core.models import CacheMetadata, PlotRecord, RedrawMetadata, SeriesStyle, SubplotMetadata

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
        _write_cache_metadata(cache_path, record)
    finally:
        plt.close(fig)

    csv_stat = source_csv.path.stat()
    redraw_fingerprint = _redraw_fingerprint(record)
    return record.model_copy(
        update={
            "cache": CacheMetadata(
                cache_path=cache_path,
                source_size_bytes=csv_stat.st_size,
                source_modified_at=source_csv.modified_at,
                redraw_fingerprint=redraw_fingerprint,
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
    redraw_fingerprint = _redraw_fingerprint(record)
    if redraw_fingerprint is not None:
        cache_metadata = _read_cache_metadata(cache_path)
        if cache_metadata.get("redraw_fingerprint") != redraw_fingerprint:
            return None

    return record.model_copy(
        update={
            "cache": CacheMetadata(
                cache_path=cache_path,
                source_size_bytes=csv_stat.st_size,
                source_modified_at=source_csv.modified_at,
                redraw_fingerprint=redraw_fingerprint,
            )
        }
    )


def _cache_path_for_record(project_root: Path, record: PlotRecord) -> Path:
    cache_suffix = record.image.suffix.lower() if record.image.suffix.lower() in {".png", ".svg"} else ".png"
    return project_root / ".mplgallery" / "cache" / f"{record.plot_id}{cache_suffix}"


def _cache_metadata_path(cache_path: Path) -> Path:
    return cache_path.with_name(f"{cache_path.name}.meta.json")


def _redraw_fingerprint(record: PlotRecord) -> str | None:
    if record.redraw is None:
        return None
    payload = record.redraw.model_dump(mode="json", exclude_none=True)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_cache_metadata(cache_path: Path) -> dict[str, object]:
    metadata_path = _cache_metadata_path(cache_path)
    if not metadata_path.exists():
        return {}
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_cache_metadata(cache_path: Path, record: PlotRecord) -> None:
    metadata_path = _cache_metadata_path(cache_path)
    metadata_path.write_text(
        json.dumps({"redraw_fingerprint": _redraw_fingerprint(record)}, sort_keys=True),
        encoding="utf-8",
    )


def render_matplotlib_figure(
    frame: pd.DataFrame,
    redraw: RedrawMetadata,
    *,
    fallback_title: str,
) -> tuple[plt.Figure, plt.Axes]:
    """Build a Matplotlib figure from CSV data and manifest metadata."""
    if frame.empty:
        raise ValueError("CSV data is empty")
    if redraw.subplots:
        return _render_subplot_figure(frame, redraw, fallback_title=fallback_title)

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
        _render_axes(ax, frame, redraw, fallback_title=fallback_title)
    except Exception:
        plt.close(fig)
        raise
    return fig, ax


def _render_subplot_figure(
    frame: pd.DataFrame,
    redraw: RedrawMetadata,
    *,
    fallback_title: str,
) -> tuple[plt.Figure, plt.Axes]:
    figure = redraw.figure
    subplot_count = len(redraw.subplots)
    rows = redraw.subplot_rows or subplot_count
    cols = redraw.subplot_cols or 1
    if rows * cols < subplot_count:
        rows = subplot_count
        cols = 1

    fig, axes = plt.subplots(
        rows,
        cols,
        figsize=(figure.width_inches, figure.height_inches),
        dpi=figure.dpi,
        facecolor=figure.facecolor,
        constrained_layout=bool(figure.constrained_layout) if figure.constrained_layout is not None else False,
        sharex=redraw.sharex,
        sharey=redraw.sharey,
    )
    axes_list = list(axes.flat) if hasattr(axes, "flat") else [axes]
    try:
        for ax, subplot in zip(axes_list, redraw.subplots, strict=False):
            _render_axes(ax, frame, subplot, fallback_title=subplot.title or subplot.subplot_id)
        for ax in axes_list[subplot_count:]:
            ax.set_visible(False)
        if redraw.title:
            fig.suptitle(redraw.title)
    except Exception:
        plt.close(fig)
        raise
    return fig, axes_list[0]


def _render_axes(
    ax: plt.Axes,
    frame: pd.DataFrame,
    metadata: RedrawMetadata | SubplotMetadata,
    *,
    fallback_title: str,
) -> None:
    x_column = metadata.x or frame.columns[0]
    series = _series_from_metadata(frame, metadata, x_column)
    if not series:
        raise ValueError("No y columns configured for redraw")

    kind = metadata.kind if metadata.kind in PLOT_KIND_CHOICES else "line"
    if kind == "hist":
        _render_histogram(ax, frame, series, metadata)
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

    ax.set_title(metadata.title or fallback_title)
    ax.set_xlabel(_compose_axis_label(metadata.xlabel or x_column, metadata.xlabel_unit))
    ax.set_ylabel(_compose_axis_label(metadata.ylabel or ", ".join(style.y for style in series), metadata.ylabel_unit))
    ax.set_xscale(metadata.xscale)
    ax.set_yscale(metadata.yscale)
    if metadata.xlim is not None:
        ax.set_xlim(metadata.xlim)
    if metadata.ylim is not None:
        ax.set_ylim(metadata.ylim)
    ax.grid(
        metadata.grid,
        axis=metadata.grid_axis or "both",
        alpha=metadata.grid_alpha if metadata.grid_alpha is not None else 0.25,
    )
    if len(series) > 1 or any(style.label for style in series):
        ax.legend(title=metadata.legend_title or None, loc=metadata.legend_location or "best")


def _series_from_metadata(
    frame: pd.DataFrame,
    redraw: RedrawMetadata | SubplotMetadata,
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
    redraw: RedrawMetadata | SubplotMetadata,
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
