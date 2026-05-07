"""Streamlit application entry point for the local CSV plot studio."""

from __future__ import annotations

import argparse
from pathlib import Path

import streamlit as st

from mplgallery.core.user_settings import (
    forget_recent_root,
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
from mplgallery.ui.root_state import (
    browse_active_root,
    change_active_root,
    reset_active_root,
    resolve_initial_root,
)


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
        header[data-testid="stHeader"] { background: transparent; }
        [data-testid="stToolbar"] { display: none !important; }
        .stAppDeployButton { display: none !important; }
        .block-container {
            padding: 0.25rem 0.7rem 0.8rem;
            max-width: 1920px;
        }
        h1 {
            color: #17202f;
            font-size: 1.35rem !important;
            margin-bottom: 0 !important;
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
    title_root_col, action_col = st.columns([9, 2], vertical_alignment="center")
    with title_root_col:
        st.markdown(
            f"""
            <div style="line-height:1.1;">
              <div style="font-size:1.9rem;font-weight:700;color:#17202f;">MPLGallery</div>
              <div style="font-size:.78rem;color:#6b7483;overflow-wrap:anywhere;line-height:1.3;">
              <span style="font-weight:600;color:#4f5a6c;">Project root:</span> {project_root}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with action_col:
        if st.button(
            "Change root",
            key="mplgallery_host_root_toggle",
            type="secondary",
            use_container_width=False,
        ):
            st.session_state["mplgallery_host_root_open"] = not st.session_state.get(
                "mplgallery_host_root_open", False
            )
    if not st.session_state.get("mplgallery_host_root_open", False):
        return False

    st.session_state.setdefault("mplgallery_host_root_draft", str(project_root))
    st.text_input(
        "Project root",
        key="mplgallery_host_root_draft",
        placeholder="Paste a project folder path",
    )
    if error := st.session_state.get("mplgallery_root_error"):
        st.caption(error)

    action_cols = st.columns([1, 1, 1.4], vertical_alignment="center")
    if action_cols[0].button("Open root", key="mplgallery_host_open_root"):
        result = change_active_root(st.session_state.get("mplgallery_host_root_draft", ""), settings)
        return _apply_root_result(result)
    if action_cols[1].button("Browse...", key="mplgallery_host_browse_root"):
        result = browse_active_root(settings, project_root)
        return _apply_root_result(result)
    if action_cols[2].button("Use launch root", key="mplgallery_host_launch_root"):
        result = reset_active_root(launch_root, settings)
        return _apply_root_result(result)

    recent_roots = [root for root in settings.recent_roots if root.resolve() != project_root.resolve()]
    if recent_roots:
        st.caption("Recent roots")
        for index, recent_root in enumerate(recent_roots[:6]):
            recent_cols = st.columns([7, 2], vertical_alignment="center")
            if recent_cols[0].button(
                _short_root_label(recent_root),
                key=f"mplgallery_recent_root_{index}",
                help=str(recent_root),
                use_container_width=True,
            ):
                result = change_active_root(str(recent_root), settings)
                return _apply_root_result(result)
            if recent_cols[1].button(
                "Forget",
                key=f"mplgallery_forget_root_{index}",
                use_container_width=True,
            ):
                fresh = forget_recent_root(settings, recent_root)
                save_user_settings(fresh)
                return True
    return False


def _apply_root_result(result) -> bool:
    if result.error:
        st.session_state["mplgallery_root_error"] = result.error
        return False
    if result.active_root is None:
        return False
    save_user_settings(result.settings)
    _set_active_project_root(result.active_root)
    st.session_state["mplgallery_host_root_draft"] = str(result.active_root)
    st.session_state["mplgallery_host_root_open"] = False
    return True


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


def _short_root_label(root_path: Path) -> str:
    parts = root_path.as_posix().split("/")
    if len(parts) <= 2:
        return root_path.as_posix()
    return f".../{'/'.join(parts[-2:])}"


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
