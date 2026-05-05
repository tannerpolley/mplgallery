from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    plot_dir = root / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)

    frame = pd.read_csv(root / "data" / "plot_ready" / "smoke_plot.csv")
    fig, ax = plt.subplots(figsize=(5, 3), dpi=140)
    ax.plot(frame["x"], frame["y"], color="#1f77b4", marker="o")
    ax.set_title("Smoke test plot")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    fig.tight_layout()
    fig.savefig(plot_dir / "smoke.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
