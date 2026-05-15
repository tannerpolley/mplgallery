from __future__ import annotations

import json
import socket
from pathlib import Path

import mplgallery.desktop as desktop
from mplgallery.preview_server import IdlePreviewServer


def test_tauri_command_prefers_cargo_for_repo_runs(monkeypatch, tmp_path: Path) -> None:
    packaged = tmp_path / "dist" / "windows" / "mplgallery-desktop.exe"
    packaged.parent.mkdir(parents=True, exist_ok=True)
    packaged.write_bytes(b"exe")

    monkeypatch.setattr(desktop, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(desktop, "TAURI_ROOT", tmp_path / "src-tauri")
    monkeypatch.setattr(desktop.shutil, "which", lambda name: "C:/Rust/bin/cargo.exe" if name == "cargo" else None)

    command = desktop._tauri_command()

    assert command == [
        "C:/Rust/bin/cargo.exe",
        "run",
        "--manifest-path",
        str((tmp_path / "src-tauri" / "Cargo.toml")),
    ]


def test_tauri_command_falls_back_to_packaged_executable_without_cargo(monkeypatch, tmp_path: Path) -> None:
    packaged = tmp_path / "dist" / "windows" / "mplgallery-desktop.exe"
    packaged.parent.mkdir(parents=True, exist_ok=True)
    packaged.write_bytes(b"exe")

    monkeypatch.setattr(desktop, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(desktop, "TAURI_ROOT", tmp_path / "src-tauri")
    monkeypatch.setattr(desktop.shutil, "which", lambda name: None)

    command = desktop._tauri_command()

    assert command == [str(packaged)]


def test_preview_html_path_requires_built_frontend(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(desktop, "FRONTEND_DIST_ROOT", tmp_path / "dist")

    try:
        desktop._preview_html_path()
    except RuntimeError as exc:
        assert "npm --prefix src/mplgallery/ui/frontend run build" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected browser preview lookup to fail without built assets")


def test_write_self_test_records_tauri_launcher(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "self-test.json"
    preview_root = tmp_path / "frontend-dist"
    preview_root.mkdir(parents=True, exist_ok=True)
    (preview_root / "index.html").write_text("<html></html>", encoding="utf-8")

    monkeypatch.setattr(desktop, "FRONTEND_DIST_ROOT", preview_root)
    monkeypatch.setattr(desktop, "_tauri_command", lambda: ["C:/dist/mplgallery-desktop.exe"])

    desktop._write_self_test(output)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["version"] == desktop.APP_VERSION
    assert payload["app_id"] == desktop.APP_USER_MODEL_ID
    assert payload["launcher_command"] == ["C:/dist/mplgallery-desktop.exe"]
    assert payload["preview_html"].endswith("index.html")


def test_browser_preview_html_injects_real_payload(tmp_path: Path, monkeypatch) -> None:
    frontend_dist = tmp_path / "frontend-dist"
    frontend_dist.mkdir(parents=True, exist_ok=True)
    (frontend_dist / "index.html").write_text(
        '<!doctype html><html><head><script type="module" src="./assets/index.js"></script></head><body></body></html>',
        encoding="utf-8",
    )
    monkeypatch.setattr(desktop, "FRONTEND_DIST_ROOT", frontend_dist)
    monkeypatch.setattr(desktop, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        desktop,
        "_browser_preview_payload",
        lambda project_root, include_artifacts, image_library: {"projectRoot": str(project_root), "records": []},
    )

    result = desktop._browser_preview_html_path(
        project_root=tmp_path / "examples",
        include_artifacts=True,
        image_library=False,
    )

    html = result.read_text(encoding="utf-8")
    assert result.name == "browser-preview.html"
    assert "window.__MPLGALLERY_BROWSER_PAYLOAD__" in html
    assert '"projectRoot":"' in html


def test_launch_browser_preview_opens_localhost_url(tmp_path: Path, monkeypatch) -> None:
    frontend_dist = tmp_path / "frontend-dist"
    frontend_dist.mkdir(parents=True, exist_ok=True)
    preview = frontend_dist / "browser-preview.html"
    preview.write_text("<html></html>", encoding="utf-8")

    monkeypatch.setattr(
        desktop,
        "_browser_preview_html_path",
        lambda project_root, include_artifacts, image_library: preview,
    )

    opened_urls: list[str] = []
    monkeypatch.setattr(desktop.webbrowser, "open", opened_urls.append)
    monkeypatch.setattr(
        desktop,
        "_start_browser_preview_server",
        lambda preview_root, preview_name, project_root, include_artifacts, image_library: f"http://127.0.0.1:9988/{preview_name}",
    )

    result = desktop.launch_browser_preview(tmp_path / "examples")

    assert result == 0
    assert opened_urls == ["http://127.0.0.1:9988/browser-preview.html"]


def test_prepare_browser_preview_returns_localhost_url(tmp_path: Path, monkeypatch) -> None:
    frontend_dist = tmp_path / "frontend-dist"
    frontend_dist.mkdir(parents=True, exist_ok=True)
    preview = frontend_dist / "browser-preview.html"
    preview.write_text("<html></html>", encoding="utf-8")

    monkeypatch.setattr(
        desktop,
        "_browser_preview_html_path",
        lambda project_root, include_artifacts, image_library: preview,
    )
    monkeypatch.setattr(
        desktop,
        "_start_browser_preview_server",
        lambda preview_root, preview_name, project_root, include_artifacts, image_library: f"http://127.0.0.1:8765/{preview_name}",
    )

    result = desktop.prepare_browser_preview(tmp_path / "examples")

    assert result == "http://127.0.0.1:8765/browser-preview.html"


def test_find_open_port_skips_occupied_preferred_port() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen()
        preferred = int(occupied.getsockname()[1])

        selected = desktop._find_open_port(preferred=preferred)

    assert selected != preferred


def test_preview_server_disallows_duplicate_port_reuse() -> None:
    assert IdlePreviewServer.allow_reuse_address is False
