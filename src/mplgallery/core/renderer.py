"""Headless Matplotlib rendering entry points."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from mplgallery.core.models import CacheMetadata, PlotRecord, RedrawMetadata, SeriesStyle


def render_cached_plot(project_root: Path | str, record: PlotRecord) -> PlotRecord:
    """Render a metadata-backed plot into `.mplgallery/cache`.

    Rendering is intentionally CSV-only: pandas reads the associated CSV and no
    discovered Python scripts are executed.
    """
    root = Path(project_root).expanduser().resolve()
    source_csv = record.plot_csv or record.csv
    if source_csv is None or record.redraw is None:
        return record

    frame = pd.read_csv(source_csv.path)
    fig, _ax = render_matplotlib_figure(frame, record.redraw, fallback_title=record.image.stem)
    try:
        cache_dir = root / ".mplgallery" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / f"{record.plot_id}.png"
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


def render_matplotlib_figure(
    frame: pd.DataFrame,
    redraw: RedrawMetadata,
    *,
    fallback_title: str,
) -> tuple[plt.Figure, plt.Axes]:
    """Build a Matplotlib figure from CSV data and manifest metadata."""
    x_column = redraw.x or frame.columns[0]
    series = _series_from_metadata(frame, redraw, x_column)
    if not series:
        raise ValueError("No y columns configured for redraw")

    figure = redraw.figure
    fig, ax = plt.subplots(figsize=(figure.width_inches, figure.height_inches), dpi=figure.dpi)

    for style in series:
        label = style.label or style.y
        if redraw.kind == "scatter":
            ax.scatter(
                frame[x_column],
                frame[style.y],
                label=label,
                color=style.color,
                marker=style.marker,
                alpha=style.alpha,
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
                markersize=3,
                alpha=style.alpha,
            )

    ax.set_title(redraw.title or fallback_title)
    ax.set_xlabel(redraw.xlabel or x_column)
    ax.set_ylabel(redraw.ylabel or ", ".join(style.y for style in series))
    ax.set_xscale(redraw.xscale)
    ax.set_yscale(redraw.yscale)
    if redraw.xlim is not None:
        ax.set_xlim(redraw.xlim)
    if redraw.ylim is not None:
        ax.set_ylim(redraw.ylim)
    ax.grid(redraw.grid, alpha=0.25)
    if len(series) > 1 or any(style.label for style in series):
        ax.legend()
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
