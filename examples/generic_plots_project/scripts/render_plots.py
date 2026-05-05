from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    plot_dir = root / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)

    conversion = pd.read_csv(root / "data" / "plot_ready" / "conversion_plot.csv")
    fig, ax = plt.subplots(figsize=(6, 4), dpi=150)
    ax.plot(conversion["elapsed_s"], conversion["conversion"], color="#1f77b4", label="Conversion")
    ax.plot(conversion["elapsed_s"], conversion["reference"], color="#d62728", linestyle="--", label="Reference")
    ax.set_title("Conversion curve")
    ax.set_xlabel(r"Elapsed time ($\mathrm{s}$)")
    ax.set_ylabel("Conversion")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(plot_dir / "conversion.png")
    plt.close(fig)

    scatter = pd.read_csv(root / "data" / "plot_ready" / "scatter_plot.csv")
    fig, ax = plt.subplots(figsize=(6, 4), dpi=150)
    ax.scatter(scatter["signal_x"], scatter["signal_y"], s=18, alpha=0.78, color="#2ca02c")
    ax.set_title("Signal scatter")
    ax.set_xlabel(r"Signal x ($\mu\mathrm{m}$)")
    ax.set_ylabel(r"Signal y ($\mu\mathrm{m}$)")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(plot_dir / "scatter.svg")
    plt.close(fig)


if __name__ == "__main__":
    main()
