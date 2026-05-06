from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from mplgallery.core.pandas_plotting import infer_pandas_draft, render_pandas_draft_figure


def test_infer_pandas_draft_uses_numeric_x_with_multiple_numeric_y_columns() -> None:
    frame = pd.DataFrame({"time": [0, 1, 2], "signal": [1.0, 2.0, 3.0], "fit": [0.8, 1.9, 3.1]})

    draft = infer_pandas_draft(Path("processed/experiment.csv"), frame)

    assert draft is not None
    assert draft.redraw.kind == "line"
    assert draft.redraw.x == "time"
    assert draft.redraw.y == ["signal", "fit"]
    assert draft.pandas_kind == "line"
    assert draft.plot_frame.columns.tolist() == ["time", "signal", "fit"]


def test_infer_pandas_draft_uses_bar_for_categorical_x_and_numeric_y() -> None:
    frame = pd.DataFrame({"category": ["a", "b"], "count": [4, 8]})

    draft = infer_pandas_draft(Path("processed/counts.csv"), frame)

    assert draft is not None
    assert draft.redraw.kind == "bar"
    assert draft.redraw.x == "category"
    assert draft.redraw.y == ["count"]
    assert draft.pandas_kind == "bar"


def test_infer_pandas_draft_adds_index_for_single_numeric_column() -> None:
    frame = pd.DataFrame({"value": [2.0, 3.0, 5.0]})

    draft = infer_pandas_draft(Path("processed/signal.csv"), frame)

    assert draft is not None
    assert draft.redraw.kind == "line"
    assert draft.redraw.x == "mplgallery_index"
    assert draft.redraw.y == ["value"]
    assert draft.plot_frame["mplgallery_index"].tolist() == [0, 1, 2]


def test_infer_pandas_draft_returns_none_for_no_numeric_columns() -> None:
    frame = pd.DataFrame({"name": ["a", "b"], "group": ["left", "right"]})

    assert infer_pandas_draft(Path("processed/labels.csv"), frame) is None


def test_render_pandas_draft_figure_still_applies_matplotlib_metadata() -> None:
    frame = pd.DataFrame({"time": [0, 1], "signal": [1.0, 2.0]})
    draft = infer_pandas_draft(Path("processed/signal.csv"), frame)
    assert draft is not None
    redraw = draft.redraw.model_copy(
        update={
            "title": "Edited",
            "xlabel": "Elapsed",
            "ylabel": "Signal",
            "xlim": (0.0, 2.0),
            "series": [
                draft.redraw.series[0].model_copy(
                    update={
                        "color": "#d62728",
                        "linestyle": "--",
                        "marker": "s",
                        "linewidth": 2.5,
                    }
                )
            ],
        }
    )

    fig, ax = render_pandas_draft_figure(draft.plot_frame, redraw, fallback_title="Fallback")
    try:
        line = ax.get_lines()[0]
        assert ax.get_title() == "Edited"
        assert ax.get_xlabel() == "Elapsed"
        assert ax.get_ylabel() == "Signal"
        assert ax.get_xlim() == (0.0, 2.0)
        assert line.get_color() == "#d62728"
        assert line.get_linestyle() == "--"
        assert line.get_marker() == "s"
        assert line.get_linewidth() == 2.5
    finally:
        plt.close(fig)
