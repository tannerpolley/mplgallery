from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    rng = np.random.default_rng(3210)

    raw_dir = root / "data" / "raw"
    plot_ready_dir = root / "data" / "plot_ready"
    raw_dir.mkdir(parents=True, exist_ok=True)
    plot_ready_dir.mkdir(parents=True, exist_ok=True)

    categories = np.array(["A", "B", "C", "D", "E"])
    counts = np.array([16, 24, 18, 31, 27], dtype=float)
    raw_bar = pd.DataFrame(
        {
            "category": categories,
            "count_raw": counts,
            "weight": rng.normal(1.0, 0.06, size=categories.size),
        }
    )
    plot_bar = raw_bar.rename(columns={"count_raw": "count"})[["category", "count", "weight"]]
    raw_bar.to_csv(raw_dir / "category_counts_raw.csv", index=False)
    plot_bar.to_csv(plot_ready_dir / "category_counts_plot.csv", index=False)

    residuals = rng.normal(0.0, 0.35, size=320)
    raw_hist = pd.DataFrame(
        {
            "sample_index": np.arange(1, residuals.size + 1),
            "residual_raw": residuals,
            "batch": np.where(residuals > 0, "positive", "negative"),
        }
    )
    plot_hist = raw_hist.rename(columns={"residual_raw": "residual"})[["sample_index", "residual", "batch"]]
    raw_hist.to_csv(raw_dir / "residuals_raw.csv", index=False)
    plot_hist.to_csv(plot_ready_dir / "residuals_plot.csv", index=False)


if __name__ == "__main__":
    main()
