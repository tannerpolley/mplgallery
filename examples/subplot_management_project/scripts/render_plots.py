from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    raw_csv = root / "data" / "raw" / "subplot_signals_raw.csv"
    plot_ready_dir = root / "data" / "plot_ready"
    plot_dir = root / "plots"
    plot_ready_dir.mkdir(parents=True, exist_ok=True)
    plot_dir.mkdir(parents=True, exist_ok=True)

    raw = pd.read_csv(raw_csv)
    plot_ready = raw.assign(
        response_smooth=raw["response"].rolling(7, center=True, min_periods=1).mean(),
        residual_abs=raw["residual"].abs(),
    )
    plot_ready_csv = plot_ready_dir / "subplot_signals_plot.csv"
    plot_ready.to_csv(plot_ready_csv, index=False)

    fig, axes = plt.subplots(2, 1, figsize=(7.0, 5.2), dpi=150, sharex=True)
    axes[0].plot(plot_ready["time_s"], plot_ready["response"], color="#1f77b4", alpha=0.55, label="raw response")
    axes[0].plot(plot_ready["time_s"], plot_ready["response_smooth"], color="#d62728", linewidth=1.8, label="smoothed")
    axes[0].set_ylabel("Response (a.u.)")
    axes[0].set_title("Subplot signal review")
    axes[0].legend()
    axes[0].grid(True, alpha=0.25)

    axes[1].bar(plot_ready["time_s"], plot_ready["residual_abs"], width=0.055, color="#2ca02c", alpha=0.75, label="|residual|")
    axes[1].set_xlabel("Time (s)")
    axes[1].set_ylabel("Residual (a.u.)")
    axes[1].grid(True, alpha=0.25)

    fig.tight_layout()
    fig.savefig(plot_dir / "subplot_signal_review.svg")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.0, 3.4), dpi=150)
    ax.plot(plot_ready["time_s"], plot_ready["response"], color="#1f77b4", alpha=0.5, label="raw response")
    ax.plot(plot_ready["time_s"], plot_ready["response_smooth"], color="#d62728", linewidth=1.8, label="smoothed")
    ax.set_title("Response panel")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Response (a.u.)")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(plot_dir / "subplot_response_panel.svg")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.0, 3.0), dpi=150)
    ax.bar(plot_ready["time_s"], plot_ready["residual_abs"], width=0.055, color="#2ca02c", alpha=0.75)
    ax.set_title("Residual panel")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Residual (a.u.)")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(plot_dir / "subplot_residual_panel.svg")
    plt.close(fig)


if __name__ == "__main__":
    main()
