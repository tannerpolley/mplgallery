"""Streamlit component bridge and payload helpers for the plot browser."""

from __future__ import annotations

import base64
import html
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from pydantic import BaseModel, ValidationError

from mplgallery.core.models import PlotRecord, RedrawMetadata, SeriesStyle


LINESTYLE_OPTIONS: tuple[tuple[str, str], ...] = (
    ("-", "━━ Solid"),
    ("--", "─ ─ Dashed"),
    ("-.", "─ · Dash-dot"),
    (":", "··· Dotted"),
    ("", "No connecting line"),
)

MARKER_OPTIONS: tuple[tuple[str, str], ...] = (
    ("o", "● Circle"),
    ("s", "■ Square"),
    ("D", "◆ Diamond"),
    ("^", "▲ Triangle up"),
    ("v", "▼ Triangle down"),
    ("x", "× X"),
    ("+", "+ Plus"),
    (".", "• Point"),
    ("", "No marker"),
)

SCALE_OPTIONS: tuple[str, ...] = ("linear", "log", "symlog", "logit")

_COMPONENT_NAME = "mplgallery_browser"
_FRONTEND_BUILD_DIR = Path(__file__).parent / "frontend" / "dist"
_component = components.declare_component(_COMPONENT_NAME, path=str(_FRONTEND_BUILD_DIR))


class ComponentEvent(BaseModel):
    id: str
    type: Literal[
        "select_plot",
        "save_redraw_metadata",
        "request_rerender",
        "set_tree_filter",
        "set_tile_size",
    ]
    plot_id: str | None = None
    redraw: RedrawMetadata | None = None
    value: str | int | float | bool | None = None


class ComponentResult(BaseModel):
    event: ComponentEvent | None = None


def render_plot_browser(payload: dict[str, Any]) -> ComponentResult:
    """Render the packaged frontend component and parse its latest event."""
    raw = _component(payload=payload, default=None, key="mplgallery_browser")
    if raw is None:
        return ComponentResult()
    try:
        return ComponentResult.model_validate(raw)
    except ValidationError as exc:
        return ComponentResult(
            event=ComponentEvent(id="invalid-component-event", type="request_rerender", value=str(exc))
        )


def build_component_payload(
    *,
    project_root: Path,
    records: list[PlotRecord],
    selected_plot_id: str | None,
    errors: dict[str, str] | None = None,
) -> dict[str, Any]:
    selected = selected_plot_id or _first_plot_id(records)
    return {
        "projectRoot": str(project_root),
        "selectedPlotId": selected,
        "records": [_record_payload(record) for record in records],
        "options": {
            "lineStyles": [{"value": value, "label": label} for value, label in LINESTYLE_OPTIONS],
            "markers": [{"value": value, "label": label} for value, label in MARKER_OPTIONS],
            "scales": list(SCALE_OPTIONS),
        },
        "errors": errors or {},
    }


def process_component_event(
    *,
    event: ComponentEvent | None,
    project_root: Path,
) -> bool:
    """Apply a component event. Returns True when Streamlit should rerun."""
    if event is None or _event_was_processed(event.id):
        return False

    st.session_state["mplgallery_last_event_id"] = event.id
    if event.type == "select_plot" and event.plot_id:
        st.session_state["mplgallery_selected_plot_id"] = event.plot_id
        st.query_params["plot_id"] = event.plot_id
        _clear_plot_error(event.plot_id)
        return True

    if event.type == "save_redraw_metadata" and event.plot_id and event.redraw:
        try:
            record = _record_by_plot_id(st.session_state["mplgallery_records"], event.plot_id)
            from mplgallery.core.manifest import update_manifest_redraw

            update_manifest_redraw(project_root, record.image.relative_path, event.redraw)
        except Exception as exc:
            _set_plot_error(event.plot_id, str(exc))
        else:
            _clear_plot_error(event.plot_id)
            st.toast("Plot metadata saved.")
        return True

    if event.type == "request_rerender" and event.plot_id:
        _clear_plot_error(event.plot_id)
        return True

    return False


def selected_plot_id_from_state_or_query(records: list[PlotRecord]) -> str | None:
    value = st.query_params.get("plot_id")
    if isinstance(value, list):
        query_plot_id = value[0] if value else None
    else:
        query_plot_id = value
    state_plot_id = st.session_state.get("mplgallery_selected_plot_id")
    candidate = query_plot_id or state_plot_id
    valid_ids = {record.plot_id for record in records}
    if candidate in valid_ids:
        return str(candidate)
    return _first_plot_id(records)


def component_errors() -> dict[str, str]:
    errors = st.session_state.get("mplgallery_component_errors", {})
    return errors if isinstance(errors, dict) else {}


def _record_payload(record: PlotRecord) -> dict[str, Any]:
    source_csv = record.plot_csv or record.csv
    redraw = record.redraw or RedrawMetadata()
    return {
        "id": record.plot_id,
        "name": record.image.relative_path.name,
        "kind": record.image.suffix.removeprefix(".").upper(),
        "imagePath": record.image.relative_path.as_posix(),
        "csvPath": source_csv.relative_path.as_posix() if source_csv else None,
        "rawCsvPath": record.raw_csv.relative_path.as_posix() if record.raw_csv else None,
        "confidence": record.association_confidence.value,
        "reason": record.association_reason,
        "imageSrc": _image_data_uri(
            record.cache.cache_path if record.cache and record.cache.cache_path else record.image.path
        ),
        "cachePath": record.cache.cache_path.as_posix()
        if record.cache and record.cache.cache_path
        else None,
        "renderError": record.cache.render_error if record.cache else None,
        "csvPreview": _csv_preview(record),
        "csvColumns": _csv_columns(record),
        "editable": bool(record.redraw and source_csv),
        "redraw": redraw.model_dump(mode="json", exclude_none=True),
        "series": [style.model_dump(mode="json", exclude_none=True) for style in _series_for_editor(record)],
    }


def _image_data_uri(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".svg":
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:image/svg+xml;base64,{encoded}"
    mime = "image/png" if suffix == ".png" else "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _csv_preview(record: PlotRecord) -> str | None:
    source_csv = record.plot_csv or record.csv
    if source_csv is None:
        return None
    try:
        frame = pd.read_csv(source_csv.path, nrows=5)
    except Exception as exc:
        return f"CSV preview failed: {html.escape(str(exc))}"
    return frame.to_string(index=False)


def _csv_columns(record: PlotRecord) -> list[str]:
    source_csv = record.plot_csv or record.csv
    if source_csv is None:
        return []
    try:
        frame = pd.read_csv(source_csv.path, nrows=0)
    except Exception:
        return []
    return [str(column) for column in frame.columns]


def _series_for_editor(record: PlotRecord) -> list[SeriesStyle]:
    if record.redraw is None:
        return []
    if record.redraw.series:
        return record.redraw.series
    if record.redraw.y:
        return [SeriesStyle(y=column) for column in record.redraw.y]
    source_csv = record.plot_csv or record.csv
    if source_csv is None:
        return []
    try:
        frame = pd.read_csv(source_csv.path, nrows=1)
    except Exception:
        return []
    x_column = record.redraw.x or frame.columns[0]
    return [SeriesStyle(y=column) for column in frame.columns if column != x_column]


def _first_plot_id(records: list[PlotRecord]) -> str | None:
    return records[0].plot_id if records else None


def _event_was_processed(event_id: str) -> bool:
    return st.session_state.get("mplgallery_last_event_id") == event_id


def _record_by_plot_id(records: list[PlotRecord], plot_id: str) -> PlotRecord:
    return next(record for record in records if record.plot_id == plot_id)


def _set_plot_error(plot_id: str, message: str) -> None:
    errors = dict(component_errors())
    errors[plot_id] = message
    st.session_state["mplgallery_component_errors"] = errors


def _clear_plot_error(plot_id: str) -> None:
    errors = dict(component_errors())
    errors.pop(plot_id, None)
    st.session_state["mplgallery_component_errors"] = errors
