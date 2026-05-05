"""Prepare plot-ready CSVs and render Matplotlib artifacts from manifest metadata."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from mplgallery.core.manifest import load_manifest
from mplgallery.core.renderer import render_matplotlib_figure


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def prepare_plot_ready_data() -> None:
    raw_dir = PROJECT_ROOT / "data" / "raw"
    plot_ready_dir = PROJECT_ROOT / "data" / "plot_ready"
    plot_ready_dir.mkdir(parents=True, exist_ok=True)

    first = pd.read_csv(raw_dir / "experiment_001_raw.csv")
    pd.DataFrame(
        {
            "time_s": first["time_s"],
            "conversion": first["conversion_model_output"].clip(lower=0.0, upper=1.0),
            "fit": first["conversion_reference_fit"],
        }
    ).to_csv(plot_ready_dir / "experiment_001_plot.csv", index=False)

    second = pd.read_csv(raw_dir / "experiment_002_raw.csv")
    pd.DataFrame(
        {
            "time_s": second["time_s"],
            "temperature_c": second["temperature_model_output_c"],
            "fit": second["temperature_reference_fit_c"],
        }
    ).to_csv(plot_ready_dir / "experiment_002_plot.csv", index=False)


def render_artifacts() -> None:
    manifest = load_manifest(PROJECT_ROOT)
    for record in manifest.records:
        if record.plot_csv_path is None or record.redraw is None:
            continue
        frame = pd.read_csv(PROJECT_ROOT / record.plot_csv_path)
        fig, _ax = render_matplotlib_figure(
            frame,
            record.redraw,
            fallback_title=record.plot_path.stem,
        )
        output_path = PROJECT_ROOT / record.plot_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fig.tight_layout()
            fig.savefig(output_path)
        finally:
            plt.close(fig)


def main() -> None:
    prepare_plot_ready_data()
    render_artifacts()


if __name__ == "__main__":
    main()
