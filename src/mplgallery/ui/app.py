"""Streamlit application entry point for the local CSV plot studio."""

from __future__ import annotations

import argparse
from pathlib import Path

import streamlit as st

from mplgallery.core.models import CacheMetadata, PlotRecord
from mplgallery.core.renderer import render_cached_plot
from mplgallery.core.studio import build_csv_studio_index
from mplgallery.ui.component import (
    build_component_payload,
    component_errors,
    process_component_event,
    render_plot_browser,
    selected_plot_id_from_state_or_query,
)


def main() -> None:
    args = _parse_args()
    project_root = args.project_root.expanduser().resolve()
    st.set_page_config(page_title="MPLGallery", layout="wide", initial_sidebar_state="collapsed")
    _render_host_chrome(project_root)

    try:
        records = _load_records(project_root, include_artifacts=args.include_artifacts)
    except Exception as exc:  # pragma: no cover - Streamlit display path
        st.error(f"Unable to scan project: {exc}")
        return

    st.session_state["mplgallery_records"] = records
    selected_plot_id = selected_plot_id_from_state_or_query(records)
    payload = build_component_payload(
        project_root=project_root,
        records=records,
        selected_plot_id=selected_plot_id,
        errors=component_errors(),
    )
    result = render_plot_browser(payload)
    if process_component_event(event=result.event, project_root=project_root):
        st.rerun()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--include-artifacts", action="store_true")
    return parser.parse_args()


def _render_host_chrome(project_root: Path) -> None:
    st.markdown(
        """
        <style>
        :root { color-scheme: light; }
        .stApp, [data-testid="stAppViewContainer"], .main {
            background: #f6f7f9;
            color: #17202f;
        }
        header[data-testid="stHeader"] { background: transparent; }
        .block-container {
            padding: 0.8rem 0.9rem 1rem;
            max-width: 1920px;
        }
        h1 {
            color: #17202f;
            font-size: 1.35rem !important;
            margin-bottom: 0 !important;
        }
        [data-testid="stCaptionContainer"] {
            color: #6b7483;
            font-size: 0.72rem;
            margin-bottom: 0.35rem;
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
    st.title("MPLGallery")
    st.caption(str(project_root))


def _load_records(project_root: Path, *, include_artifacts: bool = False) -> list[PlotRecord]:
    index = build_csv_studio_index(
        project_root,
        ensure_drafts=True,
        include_artifacts=include_artifacts,
    )
    records = index.records
    return _render_records(project_root, records)


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
