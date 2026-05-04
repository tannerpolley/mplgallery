"""Generate deterministic raw CSV outputs for the sample analysis group."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def generate_raw_data() -> None:
    raw_dir = PROJECT_ROOT / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(42)
    time_s = np.linspace(0.0, 10.0, 80)

    conversion = 1.0 - np.exp(-time_s / 4.0) + rng.normal(0.0, 0.025, size=time_s.size)
    conversion_fit = 1.0 - np.exp(-time_s / 4.2)
    pd.DataFrame(
        {
            "time_s": time_s,
            "conversion_model_output": conversion,
            "conversion_reference_fit": conversion_fit,
        }
    ).to_csv(raw_dir / "experiment_001_raw.csv", index=False)

    temperature_c = 22.0 + 3.0 * np.sin(time_s / 1.8) + rng.normal(0.0, 0.18, size=time_s.size)
    temperature_fit = 22.0 + 3.0 * np.sin(time_s / 1.8)
    pd.DataFrame(
        {
            "time_s": time_s,
            "temperature_model_output_c": temperature_c,
            "temperature_reference_fit_c": temperature_fit,
        }
    ).to_csv(raw_dir / "experiment_002_raw.csv", index=False)


def main() -> None:
    generate_raw_data()


if __name__ == "__main__":
    main()
