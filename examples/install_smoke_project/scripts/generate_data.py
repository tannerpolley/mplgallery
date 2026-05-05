from __future__ import annotations

from pathlib import Path

import pandas as pd


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    raw_dir = root / "data" / "raw"
    plot_ready_dir = root / "data" / "plot_ready"
    raw_dir.mkdir(parents=True, exist_ok=True)
    plot_ready_dir.mkdir(parents=True, exist_ok=True)

    frame = pd.DataFrame({"x": [0, 1, 2, 3], "y_raw": [0.0, 0.25, 0.65, 0.9]})
    frame.to_csv(raw_dir / "smoke_raw.csv", index=False)
    frame.rename(columns={"y_raw": "y"}).to_csv(plot_ready_dir / "smoke_plot.csv", index=False)


if __name__ == "__main__":
    main()
