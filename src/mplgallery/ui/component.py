"""Streamlit component bridge and payload helpers for the plot browser."""

from __future__ import annotations

import base64
import html
import os
from collections import defaultdict
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
from mplgallery.ui.root_state import browse_active_root, change_active_root, reset_active_root


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
        "draft_dataset_with_preferences",
        "draft_checked_datasets",
        "select_folder",
        "toggle_plot_set_checked",
        "set_checked_plot_sets",
        "select_plot_set",
        "set_preferred_attachment_view",
        "toggle_show_ungrouped",
        "refresh_index",
        "browse_project_root",
        "change_project_root",
        "reset_project_root",
        "forget_recent_root",
    ]
    plot_id: str | None = None
    plot_set_id: str | None = None
    plot_set_ids: list[str] = Field(default_factory=list)
    dataset_id: str | None = None
    dataset_ids: list[str] = Field(default_factory=list)
    folder_path: str | None = None
    attachment_id: str | None = None
    checked: bool | None = None
    show: bool | None = None
    root_path: str | None = None
    redraw: RedrawMetadata | None = None
    output_format: str | None = None


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
    hydrated_plot_set_ids: set[str] | None = None,
    app_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    associated_plot_ids = _associated_plot_ids_by_dataset(records)
    checked_plot_set_ids = set(st.session_state.get("mplgallery_checked_plot_set_ids", []))
    selected_plot_set_id = st.session_state.get("mplgallery_selected_plot_set_id")
    if hydrated_plot_set_ids is None:
        hydrated_plot_set_ids = set(checked_plot_set_ids)
        if isinstance(selected_plot_set_id, str):
            hydrated_plot_set_ids.add(selected_plot_set_id)
    else:
        hydrated_plot_set_ids = set(hydrated_plot_set_ids)
    selected_folder = str(st.session_state.get("mplgallery_selected_folder_path", ".") or ".")
    plot_sets = _plot_set_payloads(
        records,
        datasets or [],
        checked_plot_set_ids=checked_plot_set_ids,
        hydrated_plot_set_ids=hydrated_plot_set_ids,
    )
    hydrated_dataset_ids, hydrated_plot_ids = _hydrated_source_ids(plot_sets, hydrated_plot_set_ids)
    if selected_plot_id:
        hydrated_plot_ids.add(selected_plot_id)
    folder_view = _folder_view_payload(plot_sets, project_root, selected_folder)
    files_view = _files_view_payload(plot_sets)
    return {
        "projectRoot": str(project_root),
        "appInfo": app_info or {},
        "rootContext": {
            "activeRoot": str(project_root),
            "launchRoot": str(launch_root or project_root),
            "recentRoots": [str(root) for root in recent_roots],
            "error": root_error,
            "showRootChooser": show_root_chooser,
        },
        "selectedPlotId": selected_plot_id,
        "datasets": [
            _dataset_payload(
                dataset,
                associated_plot_ids.get(dataset.dataset_id, []),
                include_preview=dataset.dataset_id in hydrated_dataset_ids,
            )
            for dataset in datasets or []
        ],
        "plotSets": plot_sets,
        "folderView": folder_view,
        "filesView": files_view,
        "records": [
            _record_payload(record, include_heavy=record.plot_id in hydrated_plot_ids)
            for record in records
        ],
        "files": _file_item_payloads(project_root, records, datasets or []),
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
        _clear_plot_set_ui_state()
        _change_project_root(event.root_path or "")
        return True

    if event.type == "reset_project_root":
        _clear_plot_set_ui_state()
        _reset_project_root(launch_root or project_root)
        return True

    if event.type == "browse_project_root":
        _browse_project_root(project_root)
        return True

    if event.type == "forget_recent_root" and event.root_path:
        _forget_recent_root(event.root_path)
        return True

    if event.type == "refresh_index":
        return True

    if event.type == "select_folder" and event.folder_path:
        st.session_state["mplgallery_selected_folder_path"] = event.folder_path
        return True

    if event.type == "toggle_plot_set_checked" and event.plot_set_id:
        checked = set(st.session_state.get("mplgallery_checked_plot_set_ids", []))
        if event.checked:
            checked.add(event.plot_set_id)
        else:
            checked.discard(event.plot_set_id)
        st.session_state["mplgallery_checked_plot_set_ids"] = sorted(checked)
        st.session_state["mplgallery_selected_plot_set_id"] = event.plot_set_id
        return True

    if event.type == "set_checked_plot_sets":
        valid_ids = sorted({plot_set_id for plot_set_id in event.plot_set_ids if plot_set_id})
        st.session_state["mplgallery_checked_plot_set_ids"] = valid_ids
        if valid_ids:
            st.session_state["mplgallery_selected_plot_set_id"] = valid_ids[-1]
        return True

    if event.type == "select_plot_set" and event.plot_set_id:
        st.session_state["mplgallery_selected_plot_set_id"] = event.plot_set_id
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

    if event.type == "draft_dataset_with_preferences" and event.dataset_id and event.redraw:
        _draft_datasets_by_id(
            project_root,
            [event.dataset_id],
            redraw=event.redraw,
            output_format=event.output_format or "svg",
        )
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


def _clear_plot_set_ui_state() -> None:
    for key in (
        "mplgallery_checked_plot_set_ids",
        "mplgallery_selected_plot_set_id",
        "mplgallery_selected_folder_path",
    ):
        st.session_state.pop(key, None)


def component_errors() -> dict[str, str]:
    errors = st.session_state.get("mplgallery_component_errors", {})
    return errors if isinstance(errors, dict) else {}


def _hydrated_source_ids(
    plot_sets: list[dict[str, Any]],
    hydrated_plot_set_ids: set[str],
) -> tuple[set[str], set[str]]:
    dataset_ids: set[str] = set()
    plot_ids: set[str] = set()
    for plot_set in plot_sets:
        if plot_set.get("plotSetId") not in hydrated_plot_set_ids:
            continue
        for attachment in plot_set.get("attachments", []):
            dataset_id = attachment.get("datasetId")
            plot_id = attachment.get("plotId")
            if isinstance(dataset_id, str) and dataset_id:
                dataset_ids.add(dataset_id)
            if isinstance(plot_id, str) and plot_id:
                plot_ids.add(plot_id)
    return dataset_ids, plot_ids


def _record_payload(record: PlotRecord, *, include_heavy: bool = True) -> dict[str, Any]:
    source_csv = record.plot_csv or record.csv
    redraw = record.redraw or RedrawMetadata()
    if include_heavy:
        preview_columns, preview_rows, preview_truncated, preview_error = _record_preview(record)
        image_src = _image_data_uri(
            record.cache.cache_path if record.cache and record.cache.cache_path else record.image.path
        )
        csv_preview = _csv_preview(record)
        axis_defaults = _axis_defaults(record)
        series = _series_for_editor(record)
    else:
        preview_columns = _csv_columns(record)
        preview_rows = []
        preview_truncated = False
        preview_error = None
        image_src = None
        csv_preview = None
        axis_defaults = {"x": None, "y": None, "subplots": {}}
        series = record.redraw.series if record.redraw else []
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
        "imageSrc": image_src,
        "cachePath": record.cache.cache_path.as_posix()
        if record.cache and record.cache.cache_path
        else None,
        "renderError": record.cache.render_error if record.cache else None,
        "csvPreview": csv_preview,
        "csvColumns": _csv_columns(record),
        "previewColumns": preview_columns,
        "previewRows": preview_rows,
        "previewTruncated": preview_truncated,
        "previewError": preview_error,
        "axisDefaults": axis_defaults,
        "editable": bool(record.redraw and source_csv),
        "redraw": redraw.model_dump(mode="json", exclude_none=True),
        "series": [style.model_dump(mode="json", exclude_none=True) for style in series],
        "plotKind": redraw.kind,
    }


def _dataset_payload(
    dataset: DatasetRecord,
    associated_plot_ids: list[str] | None = None,
    *,
    include_preview: bool = True,
) -> dict[str, Any]:
    if include_preview:
        preview_columns, preview_rows, preview_truncated, preview_error = _dataset_preview(dataset)
    else:
        preview_columns = dataset.columns
        preview_rows = []
        preview_truncated = False
        preview_error = None
    plot_ids = list(dict.fromkeys([*(associated_plot_ids or []), *([dataset.associated_plot_id] if dataset.associated_plot_id else [])]))
    return {
        "id": dataset.dataset_id,
        "displayName": dataset.display_name,
        "path": dataset.relative_path.as_posix(),
        "csvRootId": dataset.csv_root_relative_path.as_posix(),
        "csvRootPath": dataset.csv_root_relative_path.as_posix(),
        "draftStatus": dataset.draft_status,
        "associatedPlotId": dataset.associated_plot_id,
        "associatedPlotIds": plot_ids,
        "rowCountSampled": dataset.row_count_sampled,
        "columns": dataset.columns,
        "numericColumns": dataset.numeric_columns,
        "categoricalColumns": dataset.categorical_columns,
        "previewColumns": preview_columns,
        "previewRows": preview_rows,
        "previewTruncated": preview_truncated,
        "previewError": preview_error,
    }


def _associated_plot_ids_by_dataset(records: list[PlotRecord]) -> dict[str, list[str]]:
    linked: dict[str, list[str]] = {}
    for record in records:
        if not record.source_dataset_id:
            continue
        linked.setdefault(record.source_dataset_id, []).append(record.plot_id)
    return linked


def _plot_set_payloads(
    records: list[PlotRecord],
    datasets: list[DatasetRecord],
    *,
    checked_plot_set_ids: set[str] | None = None,
    hydrated_plot_set_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    checked_plot_set_ids = checked_plot_set_ids or set()
    hydrated_plot_set_ids = hydrated_plot_set_ids or set()
    dataset_by_id = {dataset.dataset_id: dataset for dataset in datasets}
    dataset_by_relative_path = {dataset.relative_path.as_posix(): dataset for dataset in datasets}
    records_by_dataset: dict[str, list[PlotRecord]] = defaultdict(list)
    standalone_records: list[PlotRecord] = []

    for record in records:
        dataset_id = record.source_dataset_id
        if dataset_id is None:
            source = record.plot_csv or record.csv
            if source is not None:
                matched = dataset_by_relative_path.get(source.relative_path.as_posix())
                if matched is not None:
                    dataset_id = matched.dataset_id
        if dataset_id is not None and dataset_id in dataset_by_id:
            records_by_dataset[dataset_id].append(record)
        else:
            standalone_records.append(record)

    plot_sets: list[dict[str, Any]] = []
    for dataset in datasets:
        linked_records = sorted(
            records_by_dataset.get(dataset.dataset_id, []),
            key=lambda record: record.image.relative_path.as_posix().lower(),
        )
        attachments: list[dict[str, Any]] = [
            {
                "id": f"{dataset.dataset_id}:csv",
                "type": "csv",
                "displayName": dataset.relative_path.name,
                "sourcePath": dataset.relative_path.as_posix(),
                "datasetId": dataset.dataset_id,
                "plotId": linked_records[0].plot_id if linked_records else None,
            }
        ]
        _extend_plot_set_attachments(
            attachments,
            linked_records,
            include_text_preview=dataset.dataset_id in hydrated_plot_set_ids,
        )
        preferred = _preferred_figure_attachment(attachments)
        plot_sets.append(
            {
                "plotSetId": dataset.dataset_id,
                "title": _plot_set_title(dataset.display_name, linked_records),
                "folderPath": dataset.relative_path.parent.as_posix()
                if dataset.relative_path.parent != Path(".")
                else ".",
                "attachments": attachments,
                "preferredFigure": preferred,
                "editable": bool(any(_record_is_editable(record) for record in linked_records)),
                "checked": dataset.dataset_id in checked_plot_set_ids,
                "renderStatus": _render_status_for_records(linked_records, preferred is not None),
            }
        )

    standalone_groups: dict[tuple[str, str], list[PlotRecord]] = defaultdict(list)
    for record in standalone_records:
        parent = record.image.relative_path.parent.as_posix()
        stem = record.image.relative_path.stem.lower()
        standalone_groups[(parent, stem)].append(record)

    for (parent, stem), grouped_records in sorted(
        standalone_groups.items(),
        key=lambda item: f"{item[0][0]}/{item[0][1]}",
    ):
        sorted_records = sorted(
            grouped_records,
            key=lambda record: record.image.relative_path.as_posix().lower(),
        )
        plot_set_id = f"plotset::{parent}::{stem}".replace("/", "__")
        attachments: list[dict[str, Any]] = []
        _extend_plot_set_attachments(
            attachments,
            sorted_records,
            include_text_preview=plot_set_id in hydrated_plot_set_ids,
        )
        csv_source = sorted_records[0].plot_csv or sorted_records[0].csv
        if csv_source is not None:
            attachments.insert(
                0,
                {
                    "id": f"standalone:{parent}:{stem}:csv",
                    "type": "csv",
                    "displayName": csv_source.relative_path.name,
                    "sourcePath": csv_source.relative_path.as_posix(),
                    "datasetId": None,
                    "plotId": sorted_records[0].plot_id,
                },
            )
        preferred = _preferred_figure_attachment(attachments)
        title = _plot_set_title(sorted_records[0].image.relative_path.stem, sorted_records)
        plot_sets.append(
            {
                "plotSetId": plot_set_id,
                "title": title,
                "folderPath": parent if parent else ".",
                "attachments": attachments,
                "preferredFigure": preferred,
                "editable": bool(any(_record_is_editable(record) for record in sorted_records)),
                "checked": plot_set_id in checked_plot_set_ids,
                "renderStatus": _render_status_for_records(sorted_records, preferred is not None),
            }
        )

    return sorted(plot_sets, key=lambda item: item["title"].lower())


def _record_is_editable(record: PlotRecord) -> bool:
    return bool(record.redraw and (record.plot_csv or record.csv))


def _plot_set_title(fallback: str, records: list[PlotRecord]) -> str:
    for record in records:
        redraw = record.redraw
        if redraw and redraw.title:
            return redraw.title
    return fallback


def _extend_plot_set_attachments(
    attachments: list[dict[str, Any]],
    records: list[PlotRecord],
    *,
    include_text_preview: bool = True,
) -> None:
    seen_paths = {str(attachment["sourcePath"]) for attachment in attachments}
    for record in records:
        image_path = record.image.relative_path.as_posix()
        if image_path not in seen_paths:
            attachments.append(
                {
                    "id": record.plot_id,
                    "type": record.image.suffix.lower().removeprefix("."),
                    "displayName": record.image.relative_path.name,
                    "sourcePath": image_path,
                    "datasetId": record.source_dataset_id,
                    "plotId": record.plot_id,
                }
            )
            seen_paths.add(image_path)
        for metadata_path in record.metadata_files:
            if metadata_path.suffix.lower() not in {".yaml", ".yml"}:
                continue
            relative = metadata_path.as_posix()
            if relative in seen_paths:
                continue
            attachment_type = "mpl_yaml" if metadata_path.name.endswith(".mpl.yaml") else "other"
            attachment = {
                "id": f"{record.plot_id}:{metadata_path.name}",
                "type": attachment_type,
                "displayName": metadata_path.name,
                "sourcePath": relative,
                "datasetId": record.source_dataset_id,
                "plotId": record.plot_id,
            }
            if include_text_preview:
                attachment["textPreview"] = _text_preview(metadata_path)
                attachment["textPreviewTruncated"] = _text_preview_truncated(metadata_path)
            attachments.append(attachment)
            seen_paths.add(relative)


def _preferred_figure_attachment(attachments: list[dict[str, Any]]) -> dict[str, Any] | None:
    figures = [attachment for attachment in attachments if attachment["type"] in {"svg", "png"}]
    if not figures:
        return None
    svg = next((attachment for attachment in figures if attachment["type"] == "svg"), None)
    if svg is not None:
        return svg
    return figures[0]


def _text_preview(path: Path, *, limit: int = 5000) -> str | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    return text[:limit]


def _text_preview_truncated(path: Path, *, limit: int = 5000) -> bool:
    try:
        return path.stat().st_size > limit
    except OSError:
        return False


def _render_status_for_records(records: list[PlotRecord], has_figure: bool) -> str:
    if any(record.cache and record.cache.render_error for record in records):
        return "error"
    if has_figure:
        return "ready"
    return "missing_figure"


def _folder_view_payload(
    plot_sets: list[dict[str, Any]],
    project_root: Path,
    selected_folder: str = ".",
) -> dict[str, Any]:
    root_label = project_root.name or "project"
    paths = {"."}
    png_roots: set[str] = set()
    for plot_set in plot_sets:
        attachment_types = {str(attachment.get("type")) for attachment in plot_set.get("attachments", [])}
        if "png" not in attachment_types:
            continue
        folder = str(plot_set.get("folderPath") or ".")
        parts = [part for part in folder.split("/") if part and part != "."]
        if parts:
            png_roots.add(parts[0])

    for plot_set in plot_sets:
        folder = str(plot_set.get("folderPath") or ".")
        parts = [part for part in folder.split("/") if part and part != "."]
        if not parts or parts[0] not in png_roots:
            continue
        current = ""
        paths.add(".")
        for part in parts:
            current = f"{current}/{part}" if current else part
            paths.add(current)
    nodes: list[dict[str, Any]] = []
    for path in sorted(paths, key=lambda value: (value.count("/"), value.lower())):
        if path == ".":
            label = root_label
            parent = None
            depth = 0
        else:
            label = path.split("/")[-1]
            parent = path.rsplit("/", 1)[0] if "/" in path else "."
            depth = path.count("/") + 1
        child_count = sum(
            1
            for candidate in paths
            if candidate != path and (candidate.rsplit("/", 1)[0] if "/" in candidate else ".") == path
        )
        plot_set_count = sum(1 for plot_set in plot_sets if str(plot_set.get("folderPath") or ".") == path)
        nodes.append(
            {
                "id": path,
                "path": path,
                "label": label,
                "parentId": parent,
                "depth": depth,
                "childCount": child_count,
                "plotSetCount": plot_set_count,
                "autoFlatten": False,
            }
        )
    valid_paths = {str(node["path"]) for node in nodes}
    default_selected = selected_folder if selected_folder in valid_paths else "."
    return {"nodes": nodes, "rootId": ".", "defaultSelectedPath": default_selected}


def _files_view_payload(plot_sets: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for plot_set in plot_sets:
        attachments = plot_set.get("attachments", [])
        attachment_types = [str(attachment.get("type")) for attachment in attachments]
        rows.append(
            {
                "plotSetId": plot_set["plotSetId"],
                "title": plot_set["title"],
                "folderPath": plot_set["folderPath"],
                "attachmentTypes": attachment_types,
                "figureCount": sum(1 for item in attachment_types if item in {"svg", "png"}),
                "csvCount": sum(1 for item in attachment_types if item == "csv"),
                "editable": plot_set.get("editable", False),
                "renderStatus": plot_set.get("renderStatus", "ready"),
            }
        )
    return {"rows": rows}


def _dataset_preview(
    dataset: DatasetRecord,
    *,
    limit: int = 200,
) -> tuple[list[str], list[dict[str, Any]], bool, str | None]:
    return _tabular_preview(dataset.path, limit=limit)


def _record_preview(
    record: PlotRecord,
    *,
    limit: int = 200,
) -> tuple[list[str], list[dict[str, Any]], bool, str | None]:
    source_csv = record.plot_csv or record.csv
    if source_csv is None:
        return [], [], False, None
    return _tabular_preview(source_csv.path, limit=limit)


def _tabular_preview(
    csv_path: Path,
    *,
    limit: int = 200,
) -> tuple[list[str], list[dict[str, Any]], bool, str | None]:
    try:
        frame = pd.read_csv(csv_path, nrows=limit + 1)
    except Exception as exc:
        return [], [], False, str(exc)
    columns = [str(column) for column in frame.columns]
    truncated = len(frame) > limit
    if truncated:
        frame = frame.iloc[:limit]
    rows: list[dict[str, Any]] = []
    for row in frame.to_dict(orient="records"):
        serialized = {str(key): _preview_value(value) for key, value in row.items()}
        rows.append(serialized)
    return columns, rows, truncated, None


def _preview_value(value: Any) -> str | int | float | bool | None:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _file_item_payloads(
    project_root: Path,
    records: list[PlotRecord],
    datasets: list[DatasetRecord],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for dataset in datasets:
        relative = dataset.relative_path.as_posix()
        items.append(
            {
                "id": f"csv:{dataset.dataset_id}",
                "kind": "csv",
                "path": relative,
                "name": dataset.relative_path.name,
                "parentPath": dataset.relative_path.parent.as_posix()
                if dataset.relative_path.parent != Path(".")
                else ".",
                "iconKind": "csv-drafted" if dataset.associated_plot_id else "csv",
                "draftStatus": dataset.draft_status,
                "plotId": dataset.associated_plot_id,
                "datasetId": dataset.dataset_id,
            }
        )
    for record in records:
        relative = record.image.relative_path.as_posix()
        items.append(
            {
                "id": f"plot:{record.plot_id}",
                "kind": "image",
                "path": relative,
                "name": record.image.relative_path.name,
                "parentPath": record.image.relative_path.parent.as_posix()
                if record.image.relative_path.parent != Path(".")
                else ".",
                "iconKind": "image",
                "suffix": record.image.suffix.lower(),
                "visibilityRole": record.visibility_role,
                "plotId": record.plot_id,
                "datasetId": record.source_dataset_id,
            }
        )
    return sorted(
        items,
        key=lambda item: (
            str(item["path"]).lower(),
            0 if item["kind"] == "image" else 1,
            str(item["id"]),
        ),
    )


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


def _draft_datasets_by_id(
    project_root: Path,
    dataset_ids: list[str],
    *,
    redraw: RedrawMetadata | None = None,
    output_format: str = "svg",
) -> None:
    datasets = st.session_state.get("mplgallery_datasets", [])
    for dataset_id in dataset_ids:
        try:
            dataset = _dataset_by_id(datasets, dataset_id)
            draft_csv_dataset(
                dataset.path,
                csv_root=dataset.csv_root,
                project_root=project_root,
                redraw=redraw,
                output_format=output_format,
            )
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


def _browse_project_root(project_root: Path) -> None:
    result = browse_active_root(load_user_settings(), project_root)
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
