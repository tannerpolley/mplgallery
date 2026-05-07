from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from mplgallery.core.plot_sets import apply_mpl_yaml, load_mpl_yaml


ROOT = Path(__file__).resolve().parents[1]


def render_response_curve() -> None:
    plot_set = ROOT / "results" / "response_curve"
    plot_set.mkdir(parents=True, exist_ok=True)
    plotted_csv = plot_set / "response_curve.csv"
    frame = pd.read_csv(plotted_csv)

    sidecar_path = plot_set / "response_curve.mpl.yaml"
    sidecar = load_mpl_yaml(sidecar_path)
    metadata = sidecar.redraw
    if metadata is None:
        raise RuntimeError(f"Missing matplotlib metadata in {sidecar_path}")

    figure, ax = plt.subplots()
    for series in metadata.series:
        ax.plot(
            frame[metadata.x],
            frame[series.y],
            label=series.label or series.y,
            color=series.color,
            linestyle=series.linestyle,
            marker=series.marker,
            linewidth=series.linewidth,
            alpha=series.alpha,
        )
    apply_mpl_yaml(ax, sidecar)
    for figure_path in sidecar.figure_files:
        figure.savefig(plot_set / figure_path, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plot", default="response_curve")
    args = parser.parse_args()
    if args.plot != "response_curve":
        raise SystemExit(f"Unknown plot set: {args.plot}")
    render_response_curve()


if __name__ == "__main__":
    main()
