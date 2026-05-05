from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    raw_dir = root / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(20260505)
    time = np.linspace(0.0, 12.0, 160)
    response = np.exp(-time / 5.0) * np.sin(time * 1.6) + rng.normal(0.0, 0.045, size=time.size)
    residual = response - np.exp(-time / 5.0) * np.sin(time * 1.6)

    pd.DataFrame({"time_s": time, "response": response, "residual": residual}).to_csv(
        raw_dir / "subplot_signals_raw.csv",
        index=False,
    )


if __name__ == "__main__":
    main()

