"""Headless Matplotlib rendering entry points."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from mplgallery.core.models import CacheMetadata, PlotRecord


def render_cached_plot(project_root: Path | str, record: PlotRecord) -> PlotRecord:
    """Render a metadata-backed plot into `.mplgallery/cache`.

    Rendering is intentionally CSV-only: pandas reads the associated CSV and no
    discovered Python scripts are executed.
    """
    root = Path(project_root).expanduser().resolve()
    if record.csv is None or record.redraw is None:
        return record

    frame = pd.read_csv(record.csv.path)
    redraw = record.redraw
    x_column = redraw.x or frame.columns[0]
    y_columns = redraw.y or [column for column in frame.columns if column != x_column]
    if not y_columns:
        raise ValueError(f"No y columns configured for {record.plot_id}")

    figure = redraw.figure
    fig, ax = plt.subplots(figsize=(figure.width_inches, figure.height_inches), dpi=figure.dpi)
    try:
        for y_column in y_columns:
            if redraw.kind == "scatter":
                ax.scatter(frame[x_column], frame[y_column], label=y_column)
            else:
                ax.plot(frame[x_column], frame[y_column], marker="o", markersize=3, label=y_column)

        ax.set_title(redraw.title or record.image.stem)
        ax.set_xlabel(redraw.xlabel or x_column)
        ax.set_ylabel(redraw.ylabel or ", ".join(y_columns))
        if len(y_columns) > 1:
            ax.legend()
        ax.grid(True, alpha=0.25)

        cache_dir = root / ".mplgallery" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / f"{record.plot_id}.png"
        fig.tight_layout()
        fig.savefig(cache_path)
    finally:
        plt.close(fig)

    csv_stat = record.csv.path.stat()
    return record.model_copy(
        update={
            "cache": CacheMetadata(
                cache_path=cache_path,
                source_size_bytes=csv_stat.st_size,
                source_modified_at=record.csv.modified_at,
            )
        }
    )
