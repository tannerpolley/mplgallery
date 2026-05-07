from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def plot_set_dir(name: str) -> Path:
    return ROOT / "results" / name


def write_csv(name: str, frame: pd.DataFrame) -> Path:
    path = plot_set_dir(name) / f"{name}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def save(fig: plt.Figure, name: str, suffix: str) -> None:
    path = plot_set_dir(name) / f"{name}.{suffix}"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main() -> None:
    x = np.linspace(0.0, 6.0, 48)

    line = pd.DataFrame({"time": x, "response": np.sin(x) + 0.15 * x})
    write_csv("line", line)
    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    ax.plot(line["time"], line["response"], color="#1f77b4", marker="o", markersize=3)
    ax.set(title="Line", xlabel="Time", ylabel="Response")
    ax.grid(alpha=0.25)
    save(fig, "line", "svg")

    scatter = pd.DataFrame({"x": x, "signal": np.cos(x) + 0.08 * np.arange(len(x))})
    write_csv("scatter", scatter)
    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    ax.scatter(scatter["x"], scatter["signal"], color="#d62728", alpha=0.78)
    ax.set(title="Scatter", xlabel="X", ylabel="Signal")
    ax.grid(alpha=0.2)
    save(fig, "scatter", "png")

    bar = pd.DataFrame({"category": ["A", "B", "C", "D"], "count": [12, 18, 9, 15]})
    write_csv("bar", bar)
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    ax.bar(bar["category"], bar["count"], color="#2ca02c", alpha=0.82)
    ax.set(title="Bar", xlabel="Category", ylabel="Count")
    save(fig, "bar", "svg")

    barh = pd.DataFrame({"case": ["baseline", "candidate", "screened", "final"], "score": [0.62, 0.76, 0.69, 0.84]})
    write_csv("barh", barh)
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    ax.barh(barh["case"], barh["score"], color="#9467bd", alpha=0.82)
    ax.set(title="Horizontal Bar", xlabel="Score", ylabel="Case")
    save(fig, "barh", "svg")

    area = pd.DataFrame({"time": x, "load": np.clip(np.sin(x) + 1.4, 0, None)})
    write_csv("area", area)
    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    ax.fill_between(area["time"], area["load"], color="#17becf", alpha=0.45)
    ax.plot(area["time"], area["load"], color="#256f8f", linewidth=1.6)
    ax.set(title="Area", xlabel="Time", ylabel="Load")
    ax.grid(alpha=0.2)
    save(fig, "area", "svg")

    rng = np.random.default_rng(7)
    hist = pd.DataFrame({"residual": rng.normal(loc=0.0, scale=0.9, size=180)})
    write_csv("hist", hist)
    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    ax.hist(hist["residual"], bins=20, color="#ff7f0e", edgecolor="#17202f", alpha=0.78)
    ax.set(title="Histogram", xlabel="Residual", ylabel="Frequency")
    save(fig, "hist", "png")

    step = pd.DataFrame({"stage": np.arange(8), "conversion": [0.05, 0.12, 0.2, 0.31, 0.44, 0.58, 0.71, 0.83]})
    write_csv("step", step)
    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    ax.step(step["stage"], step["conversion"], where="mid", color="#8c564b", linewidth=2.0)
    ax.set(title="Step", xlabel="Stage", ylabel="Conversion")
    ax.grid(alpha=0.25)
    save(fig, "step", "svg")


if __name__ == "__main__":
    main()
