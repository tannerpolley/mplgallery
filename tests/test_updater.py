from __future__ import annotations

import json
import io
import zipfile
from pathlib import Path
from urllib.error import URLError

from mplgallery.updater import (
    UpdateCheckResult,
    _asset_score,
    _is_newer_version,
    check_for_updates,
    install_windows_update,
    stage_windows_update,
)


def test_version_comparison_accepts_release_tag_prefixes() -> None:
    assert _is_newer_version("0.2.0", "0.1.9") is True
    assert _is_newer_version("v0.2.0", "0.1.9") is True
    assert _is_newer_version("0.1.0", "0.1.0") is False
    assert _is_newer_version("not-a-version", "0.1.0") is False


def test_update_check_reports_new_windows_release_asset() -> None:
    payload = {
        "tag_name": "v0.2.0",
        "html_url": "https://github.com/tannerpolley/mplgallery/releases/tag/v0.2.0",
        "assets": [
            {
                "name": "mplgallery-desktop-0.2.0-windows-amd64.zip",
                "browser_download_url": "https://example.invalid/windows.zip",
            },
            {
                "name": "mplgallery-0.2.0.tar.gz",
                "browser_download_url": "https://example.invalid/source.tar.gz",
            },
        ],
        "body": "Release notes",
    }

    result = check_for_updates(
        current_version="0.1.0",
        opener=lambda _request, timeout: _FakeResponse(payload),
    )

    assert result.available is True
    assert result.latest_version == "0.2.0"
    assert result.download_url == "https://example.invalid/windows.zip"
    assert result.release_url.endswith("/v0.2.0")


def test_update_check_handles_network_errors() -> None:
    def raise_error(_request, timeout):
        raise URLError("offline")

    result = check_for_updates(current_version="0.1.0", opener=raise_error)

    assert result == UpdateCheckResult(checked=True, current_version="0.1.0", error="offline")


def test_windows_asset_score_prefers_desktop_zip_then_exe() -> None:
    assert _asset_score("mplgallery-desktop-0.2.0-windows-amd64.zip") > _asset_score(
        "mplgallery-desktop.exe"
    )


def test_stage_windows_update_extracts_desktop_zip(tmp_path: Path) -> None:
    archive_bytes = io.BytesIO()
    with zipfile.ZipFile(archive_bytes, "w") as archive:
        archive.writestr("mplgallery-desktop.exe", "exe")
        archive.writestr("install_windows_app.ps1", "installer")

    staged = stage_windows_update(
        "https://example.invalid/mplgallery-desktop-0.2.0-windows-amd64.zip",
        updates_root=tmp_path,
        opener=lambda _request, timeout: _BytesResponse(archive_bytes.getvalue()),
    )

    assert staged.exe_path.read_text(encoding="utf-8") == "exe"
    assert staged.installer_path.read_text(encoding="utf-8") == "installer"
    assert staged.source_url.endswith(".zip")


def test_install_windows_update_launches_helper_process(tmp_path: Path) -> None:
    archive_bytes = io.BytesIO()
    with zipfile.ZipFile(archive_bytes, "w") as archive:
        archive.writestr("mplgallery-desktop.exe", "exe")
        archive.writestr("install_windows_app.ps1", "installer")
        archive.writestr("Install MPLGallery.cmd", "wrapper")

    launched: list[list[str]] = []

    def launcher(command: list[str], **_kwargs) -> None:
        launched.append(command)

    result = install_windows_update(
        "https://example.invalid/mplgallery-desktop-0.2.0-windows-amd64.zip",
        updates_root=tmp_path,
        opener=lambda _request, timeout: _BytesResponse(archive_bytes.getvalue()),
        launcher=launcher,
        process_ids=[111, 222],
    )

    assert result.started is True
    assert result.staged.exe_path.exists()
    assert launched
    helper_text = result.helper_script.read_text(encoding="utf-8")
    assert "install_windows_app.ps1" in helper_text
    assert "mplgallery-desktop.exe" in helper_text
    assert "111, 222" in helper_text


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


class _BytesResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self) -> _BytesResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._payload
