from __future__ import annotations

from pathlib import Path

import pandas as pd

from mplgallery.core.associations import build_plot_records
from mplgallery.core.manifest import ProjectManifest
from mplgallery.core.renderer import render_cached_plot
from mplgallery.core.scanner import scan_project


def touch(path: Path, content: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def test_render_cached_plot_reads_csv_with_pandas_and_preserves_original(tmp_path: Path) -> None:
    image_path = touch(tmp_path / "plots" / "alpha.png", "original image")
    data_path = tmp_path / "data" / "alpha.csv"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"time_s": [0, 1, 2], "value": [1.0, 1.5, 2.0], "fit": [1.1, 1.4, 2.1]}).to_csv(
        data_path,
        index=False,
    )
    manifest = ProjectManifest.from_mapping(
        {
            "records": [
                {
                    "plot_path": "plots/alpha.png",
                    "csv_path": "data/alpha.csv",
                    "redraw": {
                        "kind": "line",
                        "x": "time_s",
                        "y": ["value", "fit"],
                        "title": "Alpha Redraw",
                        "xlabel": "time_s",
                        "ylabel": "value",
                        "figure": {"width_inches": 4.0, "height_inches": 3.0, "dpi": 120},
                    },
                }
            ]
        }
    )
    [record] = build_plot_records(scan_project(tmp_path), manifest=manifest)

    updated = render_cached_plot(tmp_path, record)

    assert updated.cache is not None
    assert updated.cache.cache_path is not None
    assert updated.cache.cache_path.exists()
    assert updated.cache.cache_path.suffix == ".png"
    assert image_path.read_text() == "original image"
