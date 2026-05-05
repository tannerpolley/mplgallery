"""Compatibility wrapper for generating the sample analysis group."""

from __future__ import annotations

from generate_data import generate_raw_data
from render_plots import prepare_plot_ready_data, render_artifacts


def main() -> None:
    generate_raw_data()
    prepare_plot_ready_data()
    render_artifacts()


if __name__ == "__main__":
    main()
