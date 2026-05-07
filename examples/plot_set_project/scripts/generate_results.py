from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    plot_set_dir = ROOT / "results" / "response_curve"
    plot_set_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(
        {
            "time_s": [0, 1, 2, 3, 4, 5],
            "response": [0.0, 0.18, 0.33, 0.49, 0.61, 0.70],
            "baseline": [0.02, 0.15, 0.28, 0.44, 0.58, 0.67],
        }
    )
    frame.to_csv(plot_set_dir / "response_curve.csv", index=False)


if __name__ == "__main__":
    main()
