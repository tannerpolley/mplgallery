"""Streamlit application entry point for the local CSV plot studio."""

from __future__ import annotations

import argparse
from pathlib import Path

import streamlit as st

from mplgallery.core.user_settings import (
    load_user_settings,
    remember_recent_root,
    save_user_settings,
)
from mplgallery.core.models import CSVStudioIndex, CacheMetadata, PlotRecord
from mplgallery.core.renderer import render_cached_plot
from mplgallery.core.studio import build_csv_studio_index
from mplgallery.ui.component import (
    build_component_payload,
    component_errors,
    process_component_event,
    render_plot_browser,
    selected_plot_id_from_state_or_query,
)
from mplgallery.ui.root_state import resolve_initial_root


def main() -> None:
    args = _parse_args()
    launch_root = args.project_root.expanduser().resolve()
    settings = load_user_settings()
    project_root = _active_project_root(launch_root, choose_root=args.choose_root, settings=settings)
    if project_root.is_dir():
        settings = remember_recent_root(settings, project_root)
        save_user_settings(settings)
    st.set_page_config(page_title="MPLGallery", layout="wide", initial_sidebar_state="collapsed")
    if _render_host_chrome(project_root=project_root, launch_root=launch_root, settings=settings):
        st.rerun()
        return

    try:
        index = _load_index(project_root, include_artifacts=args.include_artifacts)
    except Exception as exc:  # pragma: no cover - Streamlit display path
        st.error(f"Unable to scan project: {exc}")
        return

    records = _render_records(project_root, index.records)
    st.session_state["mplgallery_records"] = records
    st.session_state["mplgallery_datasets"] = index.datasets
    selected_plot_id = selected_plot_id_from_state_or_query(records)
    payload = build_component_payload(
        project_root=project_root,
        records=records,
        datasets=index.datasets,
        selected_plot_id=selected_plot_id,
        errors=component_errors(),
        launch_root=launch_root,
        recent_roots=settings.recent_roots,
        root_error=st.session_state.get("mplgallery_root_error"),
        show_root_chooser=args.choose_root,
    )
    result = render_plot_browser(payload)
    if process_component_event(event=result.event, project_root=project_root, launch_root=launch_root):
        st.rerun()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--choose-root", action="store_true")
    parser.add_argument("--include-artifacts", action="store_true", default=True)
    return parser.parse_args()


def _active_project_root(launch_root: Path, *, choose_root: bool, settings) -> Path:
    if "mplgallery_active_project_root" not in st.session_state:
        st.session_state["mplgallery_active_project_root"] = str(
            resolve_initial_root(launch_root, settings, choose_root=choose_root)
        )
    return Path(st.session_state["mplgallery_active_project_root"]).expanduser().resolve()


def _render_host_chrome(*, project_root: Path, launch_root: Path, settings) -> bool:
    _ = (project_root, launch_root, settings)
    st.markdown(
        """
        <style>
        :root { color-scheme: light; }
        html, body { color-scheme: light !important; }
        .stApp, [data-testid="stAppViewContainer"], .main {
            background: #f6f7f9;
            color: #17202f;
            color-scheme: light !important;
        }
        header[data-testid="stHeader"] { display: none !important; }
        [data-testid="stToolbar"] { display: none !important; }
        .stAppDeployButton { display: none !important; }
        .block-container {
            padding: 0 !important;
            max-width: 1920px;
        }
        [data-testid="stVerticalBlock"] { gap: 0 !important; }
        div[data-testid="stButton"] button {
            background: #ffffff !important;
            border: 1px solid #c6d0dd !important;
            color: #17202f !important;
            border-radius: 0.55rem !important;
            min-height: 1.9rem !important;
            padding: 0.18rem 0.62rem !important;
            box-shadow: none !important;
        }
        div[data-testid="stButton"] button:hover {
            border-color: #256f8f !important;
            color: #256f8f !important;
            background: #f8fbfd !important;
        }
        div[data-testid="stTextInput"] input {
            background: #ffffff !important;
            color: #17202f !important;
            border-color: #c6d0dd !important;
        }
        iframe,
        iframe[title^="mplgallery"],
        iframe[title="mplgallery.ui.component.mplgallery_browser"],
        [data-testid="stCustomComponentV1"] iframe {
            border: 0 !important;
            outline: 0 !important;
            max-width: 100% !important;
        }
        [data-testid="stCustomComponentV1"] {
            max-width: calc(100vw - 1.8rem) !important;
            overflow-x: hidden !important;
        }
        iframe:focus,
        iframe:focus-visible {
            outline: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    return False


def _load_index(project_root: Path, *, include_artifacts: bool = False) -> CSVStudioIndex:
    return build_csv_studio_index(
        project_root,
        ensure_drafts=False,
        include_artifacts=include_artifacts,
    )


def _render_records(project_root: Path, records: list[PlotRecord]) -> list[PlotRecord]:
    rendered: list[PlotRecord] = []
    for record in records:
        try:
            rendered.append(render_cached_plot(project_root, record))
        except Exception as exc:
            rendered.append(
                record.model_copy(update={"cache": CacheMetadata(render_error=str(exc))})
            )
    return rendered


if __name__ == "__main__":
    main()
