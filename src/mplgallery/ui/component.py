"""Streamlit component bridge and payload helpers for the plot browser."""

from __future__ import annotations

import base64
import html
import os
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from pydantic import BaseModel, Field, ValidationError

from mplgallery.core.models import DatasetRecord, PlotRecord, RedrawMetadata, SeriesStyle
from mplgallery.core.renderer import (
    DEFAULT_COLOR_CYCLE,
    LATEX_UNIT_SUGGESTIONS,
    LEGEND_LOCATION_CHOICES,
    PLOT_KIND_CHOICES,
)
from mplgallery.core.studio import draft_csv_dataset
from mplgallery.core.user_settings import forget_recent_root, load_user_settings, save_user_settings
from mplgallery.ui.root_state import change_active_root, reset_active_root


LINESTYLE_OPTIONS: tuple[tuple[str, str], ...] = (
    ("-", "Solid"),
    ("--", "Dashed"),
    ("-.", "Dash-dot"),
    (":", "Dotted"),
    ("", "None"),
)

MARKER_OPTIONS: tuple[tuple[str, str], ...] = (
    ("o", "●"),
    ("s", "■"),
    ("D", "◆"),
    ("^", "▲"),
    ("v", "▼"),
    ("x", "×"),
    ("+", "+"),
    (".", "•"),
    ("", "○"),
)

SCALE_OPTIONS: tuple[str, ...] = ("linear", "log", "symlog", "logit")
GRID_AXIS_OPTIONS: tuple[str, ...] = ("both", "x", "y")
HATCH_OPTIONS: tuple[tuple[str, str], ...] = (
    ("", "None"),
    ("/", "/"),
    ("\\", "\\"),
    ("|", "|"),
    ("-", "-"),
    ("+", "+"),
    ("x", "x"),
    ("o", "o"),
    (".", "."),
    ("*", "*"),
)

_COMPONENT_NAME = "mplgallery_browser"
_FRONTEND_BUILD_DIR = Path(__file__).parent / "frontend" / "dist"
_component = components.declare_component(_COMPONENT_NAME, path=str(_FRONTEND_BUILD_DIR))


class ComponentEvent(BaseModel):
    id: str
    type: Literal[
        "save_redraw_metadata",
        "request_rerender",
        "select_dataset",
        "draft_dataset",
        "draft_checked_datasets",
        "change_project_root",
        "reset_project_root",
        "forget_recent_root",
    ]
    plot_id: str | None = None
    dataset_id: str | None = None
    dataset_ids: list[str] = Field(default_factory=list)
    root_path: str | None = None
    redraw: RedrawMetadata | None = None


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
        st.session_state["mplgallery_component_bridge_error"] = str(exc)
        return ComponentResult(
            event=ComponentEvent(id="invalid-component-event", type="request_rerender")
        )


def build_component_payload(
    *,
    project_root: Path,
    records: list[PlotRecord],
    selected_plot_id: str | None,
    datasets: list[DatasetRecord] | None = None,
    errors: dict[str, str] | None = None,
    launch_root: Path | None = None,
    recent_roots: tuple[Path, ...] = (),
    root_error: str | None = None,
    show_root_chooser: bool = False,
) -> dict[str, Any]:
    return {
        "projectRoot": str(project_root),
        "rootContext": {
            "activeRoot": str(project_root),
            "launchRoot": str(launch_root or project_root),
            "recentRoots": [str(root) for root in recent_roots],
            "error": root_error,
            "showRootChooser": show_root_chooser,
        },
        "selectedPlotId": selected_plot_id,
        "datasets": [_dataset_payload(dataset) for dataset in datasets or []],
        "records": [_record_payload(record) for record in records],
        "options": {
            "plotKinds": list(PLOT_KIND_CHOICES),
            "lineStyles": [{"value": value, "label": label} for value, label in LINESTYLE_OPTIONS],
            "markers": [{"value": value, "label": label} for value, label in MARKER_OPTIONS],
            "colors": [
                {"value": color, "label": f"Matplotlib {index + 1}"}
                for index, color in enumerate(DEFAULT_COLOR_CYCLE)
            ],
            "units": [unit for unit in LATEX_UNIT_SUGGESTIONS if unit],
            "scales": list(SCALE_OPTIONS),
            "gridAxes": list(GRID_AXIS_OPTIONS),
            "legendLocations": list(LEGEND_LOCATION_CHOICES),
            "hatches": [{"value": value, "label": label} for value, label in HATCH_OPTIONS],
        },
        "errors": errors or {},
    }


def process_component_event(
    *,
    event: ComponentEvent | None,
    project_root: Path,
    launch_root: Path | None = None,
) -> bool:
    """Apply a component event. Returns True when Streamlit should rerun."""
    if event is None or _event_was_processed(event.id):
        return False

    st.session_state["mplgallery_last_event_id"] = event.id
    if event.type == "change_project_root":
        _change_project_root(event.root_path or "")
        return True

    if event.type == "reset_project_root":
        _reset_project_root(launch_root or project_root)
        return True

    if event.type == "forget_recent_root" and event.root_path:
        _forget_recent_root(event.root_path)
        return True

    if event.type == "save_redraw_metadata" and event.plot_id and event.redraw:
        try:
            record = _record_by_plot_id(st.session_state["mplgallery_records"], event.plot_id)
            from mplgallery.core.manifest import update_manifest_redraw

            manifest_root = _manifest_root_for_record(project_root, record)
            update_manifest_redraw(
                manifest_root,
                Path(os.path.relpath(record.image.path, manifest_root)),
                event.redraw,
            )
            _remove_cached_preview(project_root, record)
        except Exception as exc:
            _set_plot_error(event.plot_id, str(exc))
        else:
            _clear_plot_error(event.plot_id)
            st.toast("Plot metadata saved.")
        return True

    if event.type == "request_rerender" and event.plot_id:
        _clear_plot_error(event.plot_id)
        return True

    if event.type == "draft_dataset" and event.dataset_id:
        _draft_datasets_by_id(project_root, [event.dataset_id])
        return True

    if event.type == "draft_checked_datasets" and event.dataset_ids:
        _draft_datasets_by_id(project_root, event.dataset_ids)
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
    return None


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
        "sourceDatasetId": record.source_dataset_id,
        "ownedByMplgallery": record.owned_by_mplgallery,
        "visibilityRole": record.visibility_role,
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
        "axisDefaults": _axis_defaults(record),
        "editable": bool(record.redraw and source_csv),
        "redraw": redraw.model_dump(mode="json", exclude_none=True),
        "series": [style.model_dump(mode="json", exclude_none=True) for style in _series_for_editor(record)],
        "plotKind": redraw.kind,
    }


def _dataset_payload(dataset: DatasetRecord) -> dict[str, Any]:
    return {
        "id": dataset.dataset_id,
        "displayName": dataset.display_name,
        "path": dataset.relative_path.as_posix(),
        "csvRootId": dataset.csv_root_relative_path.as_posix(),
        "csvRootPath": dataset.csv_root_relative_path.as_posix(),
        "draftStatus": dataset.draft_status,
        "associatedPlotId": dataset.associated_plot_id,
        "rowCountSampled": dataset.row_count_sampled,
        "columns": dataset.columns,
        "numericColumns": dataset.numeric_columns,
        "categoricalColumns": dataset.categorical_columns,
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


def _axis_defaults(record: PlotRecord) -> dict[str, Any]:
    source_csv = record.plot_csv or record.csv
    if source_csv is None or record.redraw is None:
        return {"x": None, "y": None, "subplots": {}}
    try:
        frame = pd.read_csv(source_csv.path)
    except Exception:
        return {"x": None, "y": None, "subplots": {}}

    top_level = _limits_for_metadata(frame, record.redraw, _series_for_editor(record))
    subplots = {
        subplot.subplot_id: _limits_for_metadata(frame, subplot, subplot.series)
        for subplot in record.redraw.subplots
    }
    return {"x": top_level["x"], "y": top_level["y"], "subplots": subplots}


def _limits_for_metadata(
    frame: pd.DataFrame,
    metadata: Any,
    series: list[SeriesStyle],
) -> dict[str, tuple[float, float] | None]:
    if frame.empty:
        return {"x": None, "y": None}
    x_column = metadata.x or frame.columns[0]
    y_columns = [style.y for style in series] or list(getattr(metadata, "y", []) or [])
    return {
        "x": _numeric_limits(frame, [x_column]),
        "y": _numeric_limits(frame, y_columns),
    }


def _numeric_limits(frame: pd.DataFrame, columns: list[str]) -> tuple[float, float] | None:
    values: list[float] = []
    for column in columns:
        if column not in frame.columns:
            continue
        numeric = pd.to_numeric(frame[column], errors="coerce").dropna()
        if numeric.empty:
            continue
        values.extend([float(numeric.min()), float(numeric.max())])
    if not values:
        return None
    minimum = min(values)
    maximum = max(values)
    if minimum == maximum:
        padding = abs(minimum) * 0.05 or 1.0
        return (minimum - padding, maximum + padding)
    return (minimum, maximum)


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


def _dataset_by_id(datasets: list[DatasetRecord], dataset_id: str) -> DatasetRecord:
    return next(dataset for dataset in datasets if dataset.dataset_id == dataset_id)


def _draft_datasets_by_id(project_root: Path, dataset_ids: list[str]) -> None:
    datasets = st.session_state.get("mplgallery_datasets", [])
    for dataset_id in dataset_ids:
        try:
            dataset = _dataset_by_id(datasets, dataset_id)
            draft_csv_dataset(dataset.path, csv_root=dataset.csv_root, project_root=project_root)
            _clear_plot_error(dataset.associated_plot_id or dataset_id)
        except Exception as exc:
            _set_plot_error(dataset.associated_plot_id or dataset_id, str(exc))


def _change_project_root(root_path: str) -> None:
    result = change_active_root(root_path, load_user_settings())
    if result.error:
        st.session_state["mplgallery_root_error"] = result.error
        return
    if result.active_root is None:
        return
    save_user_settings(result.settings)
    _set_active_project_root(result.active_root)


def _reset_project_root(launch_root: Path) -> None:
    result = reset_active_root(launch_root, load_user_settings())
    if result.error:
        st.session_state["mplgallery_root_error"] = result.error
        return
    if result.active_root is None:
        return
    save_user_settings(result.settings)
    _set_active_project_root(result.active_root)


def _forget_recent_root(root_path: str) -> None:
    settings = forget_recent_root(load_user_settings(), Path(root_path))
    save_user_settings(settings)


def _set_active_project_root(project_root: Path) -> None:
    st.session_state["mplgallery_active_project_root"] = str(project_root)
    st.session_state.pop("mplgallery_root_error", None)
    st.session_state.pop("mplgallery_selected_plot_id", None)
    st.session_state.pop("mplgallery_component_errors", None)
    st.session_state.pop("mplgallery_records", None)
    st.session_state.pop("mplgallery_datasets", None)
    try:
        if "plot_id" in st.query_params:
            del st.query_params["plot_id"]
    except Exception:
        pass


def _manifest_root_for_record(project_root: Path, record: PlotRecord) -> Path:
    source = record.raw_csv or record.plot_csv or record.csv
    if source is not None:
        for parent in [source.path.parent, *source.path.parents]:
            if (parent / ".mplgallery" / "manifest.yaml").exists():
                return parent
    return project_root


def _set_plot_error(plot_id: str, message: str) -> None:
    errors = dict(component_errors())
    errors[plot_id] = message
    st.session_state["mplgallery_component_errors"] = errors


def _clear_plot_error(plot_id: str) -> None:
    errors = dict(component_errors())
    errors.pop(plot_id, None)
    st.session_state["mplgallery_component_errors"] = errors


def _remove_cached_preview(project_root: Path, record: PlotRecord) -> None:
    if record.owned_by_mplgallery:
        if record.cache and record.cache.cache_path is not None:
            record.cache.cache_path.with_name(f"{record.cache.cache_path.name}.meta.json").unlink(
                missing_ok=True
            )
        return
    if record.cache and record.cache.cache_path is not None:
        record.cache.cache_path.unlink(missing_ok=True)
        record.cache.cache_path.with_name(f"{record.cache.cache_path.name}.meta.json").unlink(
            missing_ok=True
        )
        return
    suffix = record.image.suffix.lower() if record.image.suffix.lower() in {".png", ".svg"} else ".png"
    cache_path = project_root / ".mplgallery" / "cache" / f"{record.plot_id}{suffix}"
    cache_path.unlink(missing_ok=True)
