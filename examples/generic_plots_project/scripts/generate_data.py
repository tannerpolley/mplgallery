from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    rng = np.random.default_rng(1234)

    raw_dir = root / "data" / "raw"
    plot_ready_dir = root / "data" / "plot_ready"
    raw_dir.mkdir(parents=True, exist_ok=True)
    plot_ready_dir.mkdir(parents=True, exist_ok=True)

    elapsed_s = np.linspace(0.0, 10.0, 50)
    conversion = 1.0 - np.exp(-elapsed_s / 4.2) + rng.normal(0.0, 0.015, size=elapsed_s.size)
    reference = 1.0 - np.exp(-elapsed_s / 4.0)

    raw_conversion = pd.DataFrame(
        {
            "elapsed_s": elapsed_s,
            "conversion_raw": conversion,
            "reference_raw": reference,
            "run_id": "run-001",
        }
    )
    plot_conversion = raw_conversion.rename(
        columns={"conversion_raw": "conversion", "reference_raw": "reference"}
    )[
        ["elapsed_s", "conversion", "reference"]
    ]
    raw_conversion.to_csv(raw_dir / "conversion_raw.csv", index=False)
    plot_conversion.to_csv(plot_ready_dir / "conversion_plot.csv", index=False)

    x = rng.normal(0.0, 1.0, size=140)
    y = 0.8 * x + rng.normal(0.0, 0.45, size=140)
    raw_scatter = pd.DataFrame(
        {
            "sample_index": np.arange(1, x.size + 1),
            "signal_x_raw": x,
            "signal_y_raw": y,
            "group": np.where(x > 0, "positive", "negative"),
        }
    )
    plot_scatter = raw_scatter.rename(
        columns={"signal_x_raw": "signal_x", "signal_y_raw": "signal_y"}
    )[["sample_index", "signal_x", "signal_y", "group"]]
    raw_scatter.to_csv(raw_dir / "scatter_raw.csv", index=False)
    plot_scatter.to_csv(plot_ready_dir / "scatter_plot.csv", index=False)


if __name__ == "__main__":
    main()
