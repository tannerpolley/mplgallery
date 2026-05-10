from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

import streamlit as st

from mplgallery.core.models import DiscoveredFile, FileKind, PlotRecord
from mplgallery.core.user_settings import (
    UserSettings,
    forget_recent_root,
    load_user_settings,
    remember_recent_root,
    save_user_settings,
    settings_path,
)
from mplgallery.ui.component import ComponentEvent, process_component_event
from mplgallery.ui.root_state import change_active_root, reset_active_root, resolve_initial_root


def test_settings_path_respects_config_home(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MPLGALLERY_CONFIG_HOME", str(tmp_path / "config-home"))

    assert settings_path() == tmp_path / "config-home" / "settings.json"


def test_recent_roots_are_persisted_deduplicated_ordered_and_capped(tmp_path: Path) -> None:
    settings = UserSettings()
    roots = [tmp_path / f"project-{index}" for index in range(12)]
    for root in roots:
        settings = remember_recent_root(settings, root, max_recent_roots=8)
    settings = remember_recent_root(settings, roots[3], max_recent_roots=8)

    assert settings.recent_roots[0] == roots[3].resolve()
    assert len(settings.recent_roots) == 8
    assert len(set(settings.recent_roots)) == 8
    assert settings.last_active_root == roots[3].resolve()

    path = tmp_path / "settings.json"
    save_user_settings(settings, path=path)

    loaded = load_user_settings(path=path)
    assert loaded == settings


def test_settings_persist_project_memory_preferences(tmp_path: Path) -> None:
    settings = UserSettings(
        remember_recent_projects=False,
        restore_last_project_on_startup=True,
    )
    path = tmp_path / "settings.json"

    save_user_settings(settings, path=path)

    loaded = load_user_settings(path=path)
    assert loaded.remember_recent_projects is False
    assert loaded.restore_last_project_on_startup is True


def test_legacy_settings_default_project_memory_preferences(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "recent_roots": [str(root)],
                "last_active_root": str(root),
            }
        ),
        encoding="utf-8",
    )

    loaded = load_user_settings(path=path)

    assert loaded.remember_recent_projects is True
    assert loaded.restore_last_project_on_startup is False


def test_invalid_settings_json_falls_back_safely(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{not-json", encoding="utf-8")

    assert load_user_settings(path=path) == UserSettings()


def test_forget_recent_root_removes_root_and_last_active(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    settings = remember_recent_root(remember_recent_root(UserSettings(), first), second)

    updated = forget_recent_root(settings, second)

    assert updated.recent_roots == (first.resolve(),)
    assert updated.last_active_root is None


def test_root_selection_accepts_existing_directory_and_rejects_missing_path(tmp_path: Path) -> None:
    existing = tmp_path / "analysis"
    existing.mkdir()
    settings = UserSettings()

    result = change_active_root(str(existing), settings)

    assert result.active_root == existing.resolve()
    assert result.error is None
    assert result.settings.last_active_root == existing.resolve()
    assert result.settings.recent_roots == (existing.resolve(),)

    missing = change_active_root(str(tmp_path / "missing"), result.settings)

    assert missing.active_root is None
    assert "does not exist" in missing.error
    assert missing.settings == result.settings


def test_resolve_initial_root_opens_explicit_project_path(tmp_path: Path) -> None:
    launch_root = tmp_path / "launch"
    recent_root = tmp_path / "recent"
    launch_root.mkdir()
    recent_root.mkdir()
    settings = remember_recent_root(UserSettings(), recent_root)

    result = resolve_initial_root(
        launch_root,
        settings,
        choose_root=False,
        blank_start=False,
    )

    assert result.active_root == launch_root.resolve()
    assert result.error is None


def test_resolve_initial_root_uses_blank_start_by_default(tmp_path: Path) -> None:
    launch_root = tmp_path / "launch"
    recent_root = tmp_path / "recent"
    launch_root.mkdir()
    recent_root.mkdir()
    settings = remember_recent_root(UserSettings(), recent_root)

    result = resolve_initial_root(
        launch_root,
        settings,
        choose_root=False,
        blank_start=True,
    )

    assert result.active_root is None
    assert result.error is None


def test_resolve_initial_root_restores_last_project_when_enabled(tmp_path: Path) -> None:
    launch_root = tmp_path / "launch"
    recent_root = tmp_path / "recent"
    launch_root.mkdir()
    recent_root.mkdir()
    settings = remember_recent_root(
        UserSettings(restore_last_project_on_startup=True),
        recent_root,
    )

    result = resolve_initial_root(
        launch_root,
        settings,
        choose_root=False,
        blank_start=True,
    )

    assert result.active_root == recent_root.resolve()
    assert result.error is None


def test_resolve_initial_root_warns_when_restored_project_is_missing(tmp_path: Path) -> None:
    launch_root = tmp_path / "launch"
    missing_root = tmp_path / "missing"
    launch_root.mkdir()
    settings = UserSettings(
        last_active_root=missing_root,
        restore_last_project_on_startup=True,
    )

    result = resolve_initial_root(
        launch_root,
        settings,
        choose_root=False,
        blank_start=True,
    )

    assert result.active_root is None
    assert result.error is not None
    assert "Last project is not available" in result.error


def test_remember_recent_root_honors_disabled_project_memory(tmp_path: Path) -> None:
    root = tmp_path / "project"
    settings = UserSettings(remember_recent_projects=False)

    updated = remember_recent_root(settings, root)

    assert updated.recent_roots == ()
    assert updated.last_active_root is None


def test_reset_active_root_returns_launch_root_and_persists_it(tmp_path: Path) -> None:
    launch_root = tmp_path / "launch"
    launch_root.mkdir()

    result = reset_active_root(launch_root, UserSettings())

    assert result.active_root == launch_root.resolve()
    assert result.error is None
    assert result.settings.last_active_root == launch_root.resolve()


def test_settings_file_shape_is_plain_json(tmp_path: Path) -> None:
    root = tmp_path / "project"
    settings = remember_recent_root(UserSettings(), root)
    path = tmp_path / "settings.json"

    save_user_settings(settings, path=path)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload == {
        "recent_roots": [str(root.resolve())],
        "last_active_root": str(root.resolve()),
        "remember_recent_projects": True,
        "restore_last_project_on_startup": False,
    }


def test_component_root_event_updates_session_and_clears_stale_state(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("MPLGALLERY_CONFIG_HOME", str(tmp_path / "config-home"))
    next_root = tmp_path / "next-root"
    launch_root = tmp_path / "launch-root"
    next_root.mkdir()
    launch_root.mkdir()
    st.session_state.clear()
    st.session_state["mplgallery_selected_plot_id"] = "stale-plot"
    st.session_state["mplgallery_component_errors"] = {"stale-plot": "bad"}
    st.session_state["mplgallery_records"] = ["stale"]
    st.session_state["mplgallery_datasets"] = ["stale"]

    changed = process_component_event(
        event=ComponentEvent(
            id="root-change-1",
            type="change_project_root",
            root_path=str(next_root),
        ),
        project_root=launch_root,
        launch_root=launch_root,
    )

    assert changed is True
    assert st.session_state["mplgallery_active_project_root"] == str(next_root.resolve())
    assert "mplgallery_selected_plot_id" not in st.session_state
    assert "mplgallery_component_errors" not in st.session_state
    assert load_user_settings().last_active_root == next_root.resolve()


def test_component_root_event_rejects_missing_root_without_switching(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("MPLGALLERY_CONFIG_HOME", str(tmp_path / "config-home"))
    launch_root = tmp_path / "launch-root"
    launch_root.mkdir()
    st.session_state.clear()
    st.session_state["mplgallery_active_project_root"] = str(launch_root)

    changed = process_component_event(
        event=ComponentEvent(
            id="root-change-missing",
            type="change_project_root",
            root_path=str(tmp_path / "missing"),
        ),
        project_root=launch_root,
        launch_root=launch_root,
    )

    assert changed is True
    assert st.session_state["mplgallery_active_project_root"] == str(launch_root)
    assert "does not exist" in st.session_state["mplgallery_root_error"]


def test_component_browse_root_event_reports_picker_unavailable(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("MPLGALLERY_CONFIG_HOME", str(tmp_path / "config-home"))
    monkeypatch.setattr("mplgallery.ui.root_state._pick_directory", lambda initial_root: None)
    launch_root = tmp_path / "launch-root"
    launch_root.mkdir()
    st.session_state.clear()
    st.session_state["mplgallery_active_project_root"] = str(launch_root)

    changed = process_component_event(
        event=ComponentEvent(id="browse-root-1", type="browse_project_root"),
        project_root=launch_root,
        launch_root=launch_root,
    )

    assert changed is True
    assert st.session_state["mplgallery_active_project_root"] == str(launch_root)
    assert "Folder selection was cancelled" in st.session_state["mplgallery_root_error"]


def test_component_user_setting_event_persists_project_memory_toggle(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("MPLGALLERY_CONFIG_HOME", str(tmp_path / "config-home"))
    st.session_state.clear()

    changed = process_component_event(
        event=ComponentEvent(
            id="setting-toggle-1",
            type="set_user_setting",
            setting_key="restore_last_project_on_startup",
            setting_value=True,
        ),
        project_root=tmp_path,
        launch_root=tmp_path,
    )

    assert changed is True
    assert load_user_settings().restore_last_project_on_startup is True


def test_component_clear_recent_roots_event_removes_project_memory(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("MPLGALLERY_CONFIG_HOME", str(tmp_path / "config-home"))
    root = tmp_path / "project"
    save_user_settings(remember_recent_root(UserSettings(), root))
    st.session_state.clear()

    changed = process_component_event(
        event=ComponentEvent(id="clear-recents-1", type="clear_recent_roots"),
        project_root=tmp_path,
        launch_root=tmp_path,
    )

    assert changed is True
    assert load_user_settings().recent_roots == ()
    assert load_user_settings().last_active_root is None


def test_component_set_browse_mode_event_updates_session_state(tmp_path: Path) -> None:
    st.session_state.clear()

    changed = process_component_event(
        event=ComponentEvent(
            id="browse-mode-1",
            type="set_browse_mode",
            browse_mode="image-library",
        ),
        project_root=tmp_path,
        launch_root=tmp_path,
    )

    assert changed is True
    assert st.session_state["mplgallery_browse_mode"] == "image-library"


def test_component_save_yaml_attachment_writes_attached_sidecar(monkeypatch, tmp_path: Path) -> None:
    project = tmp_path / "project"
    sidecar = project / "results" / "alpha.mpl.yaml"
    image = project / "results" / "alpha.svg"
    sidecar.parent.mkdir(parents=True)
    sidecar.write_text("kind: line\n", encoding="utf-8")
    image.write_text("<svg />", encoding="utf-8")
    monkeypatch.setattr(st, "toast", lambda message: None)
    st.session_state.clear()
    st.session_state["mplgallery_records"] = [
        PlotRecord(
            plot_id="plots__alpha",
            image=DiscoveredFile(
                path=image,
                relative_path=Path("results/alpha.svg"),
                kind=FileKind.IMAGE,
                suffix=".svg",
                stem="alpha",
                parent_dir=image.parent,
                size_bytes=image.stat().st_size,
                modified_at=datetime.now(),
            ),
            metadata_files=[Path("results/alpha.mpl.yaml")],
        )
    ]

    changed = process_component_event(
        event=ComponentEvent(
            id="save-yaml-1",
            type="save_yaml_attachment",
            plot_id="plots__alpha",
            attachment_path="results/alpha.mpl.yaml",
            yaml_text="kind: scatter\nx: time\n",
        ),
        project_root=project,
        launch_root=project,
    )

    assert changed is True
    assert sidecar.read_text(encoding="utf-8") == "kind: scatter\nx: time\n"
