"""Generate deterministic sample data and plots for local mplgallery testing."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def generate_csv_data() -> None:
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(exist_ok=True)

    rng = np.random.default_rng(42)
    time_s = np.linspace(0.0, 10.0, 80)
    conversion = 1.0 - np.exp(-time_s / 4.0) + rng.normal(0.0, 0.025, size=time_s.size)
    conversion_fit = 1.0 - np.exp(-time_s / 4.2)
    pd.DataFrame(
        {
            "time_s": time_s,
            "conversion": conversion,
            "fit": conversion_fit,
        }
    ).to_csv(data_dir / "experiment_001.csv", index=False)

    temperature_c = 22.0 + 3.0 * np.sin(time_s / 1.8) + rng.normal(0.0, 0.18, size=time_s.size)
    temperature_fit = 22.0 + 3.0 * np.sin(time_s / 1.8)
    pd.DataFrame(
        {
            "time_s": time_s,
            "temperature_c": temperature_c,
            "fit": temperature_fit,
        }
    ).to_csv(data_dir / "experiment_002.csv", index=False)


def render_matplotlib_images() -> None:
    plots_dir = PROJECT_ROOT / "plots"
    plots_dir.mkdir(exist_ok=True)

    first = pd.read_csv(PROJECT_ROOT / "data" / "experiment_001.csv")
    fig, ax = plt.subplots()
    ax.plot(first["time_s"], first["conversion"], marker="o", label="conversion")
    ax.plot(first["time_s"], first["fit"], linestyle="--", label="fit")
    ax.set_xlabel("time_s")
    ax.set_ylabel("conversion")
    ax.legend()
    fig.savefig(plots_dir / "experiment_001.png", dpi=150)
    plt.close(fig)

    second = pd.read_csv(PROJECT_ROOT / "data" / "experiment_002.csv")
    fig, ax = plt.subplots()
    ax.plot(second["time_s"], second["temperature_c"], marker="o", label="temperature_c")
    ax.plot(second["time_s"], second["fit"], linestyle="--", label="fit")
    ax.set_xlabel("time_s")
    ax.set_ylabel("temperature_c")
    ax.legend()
    fig.savefig(plots_dir / "experiment_002.svg")
    plt.close(fig)


def main() -> None:
    generate_csv_data()
    render_matplotlib_images()


if __name__ == "__main__":
    main()
