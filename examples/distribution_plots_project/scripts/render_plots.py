from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    plot_dir = root / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)

    bar = pd.read_csv(root / "data" / "plot_ready" / "category_counts_plot.csv")
    fig, ax = plt.subplots(figsize=(6, 4), dpi=150)
    ax.bar(bar["category"], bar["count"], color="#9467bd")
    ax.set_title("Category counts")
    ax.set_xlabel("Category")
    ax.set_ylabel(r"Count ($\mathrm{a.u.}$)")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(plot_dir / "category_counts.png")
    plt.close(fig)

    hist = pd.read_csv(root / "data" / "plot_ready" / "residuals_plot.csv")
    fig, ax = plt.subplots(figsize=(6, 4), dpi=150)
    ax.hist(hist["residual"], bins=18, color="#ff7f0e", alpha=0.8)
    ax.set_title("Residual distribution")
    ax.set_xlabel(r"Residual ($\mathrm{mV}$)")
    ax.set_ylabel("Frequency")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(plot_dir / "residual_distribution.svg")
    plt.close(fig)


if __name__ == "__main__":
    main()
