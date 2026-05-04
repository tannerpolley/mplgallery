"""Generate deterministic sample plots for local mplgallery testing."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
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


if __name__ == "__main__":
    main()
