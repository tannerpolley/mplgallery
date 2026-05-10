from __future__ import annotations

import json
from pathlib import Path

import mplgallery.desktop as desktop
from mplgallery.updater import UpdateCheckResult


def test_streamlit_command_uses_python_module_in_dev_mode(tmp_path: Path) -> None:
    command = desktop._streamlit_command(
        project_root=tmp_path,
        port=8615,
        choose_root=True,
        include_artifacts=True,
        image_library=True,
    )

    assert command[:3] == [desktop.sys.executable, "-m", "streamlit"]
    assert "--server.port=8615" in command
    assert "--choose-root" in command
    assert "--include-artifacts" in command
    assert "--image-library" in command


def test_streamlit_command_uses_internal_mode_when_frozen(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(desktop.sys, "frozen", True, raising=False)
    monkeypatch.setattr(desktop.sys, "executable", "C:/dist/mplgallery-desktop.exe")

    command = desktop._streamlit_command(
        project_root=tmp_path,
        port=8616,
        choose_root=False,
        include_artifacts=False,
        image_library=False,
    )

    assert command[0] == "C:/dist/mplgallery-desktop.exe"
    assert "--internal-streamlit" in command
    assert "--port=8616" in command


def test_write_self_test_records_runtime_details(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "self-test.json"
    monkeypatch.setattr(desktop.sys, "frozen", True, raising=False)
    monkeypatch.setattr(desktop.sys, "executable", "C:/dist/mplgallery-desktop.exe")
    monkeypatch.setattr(desktop.sys, "_MEIPASS", "C:/bundle", raising=False)

    desktop._write_self_test(output)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["frozen"] is True
    assert payload["executable"] == "C:/dist/mplgallery-desktop.exe"
    assert payload["app_id"] == desktop.APP_USER_MODEL_ID
    assert payload["app_path"].endswith("mplgallery\\ui\\app.py") or payload["app_path"].endswith("mplgallery/ui/app.py")


def test_streamlit_env_disables_development_mode(monkeypatch) -> None:
    monkeypatch.delenv("BROWSER", raising=False)
    monkeypatch.delenv("STREAMLIT_GLOBAL_DEVELOPMENT_MODE", raising=False)

    env = desktop._streamlit_env()

    assert env["BROWSER"] == "none"
    assert env["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] == "false"


def test_update_check_payload_uses_packaged_app_metadata(monkeypatch) -> None:
    monkeypatch.setattr(desktop, "check_for_updates", lambda: UpdateCheckResult(checked=True, available=False))
    monkeypatch.setattr(desktop.os, "name", "nt")
    monkeypatch.setattr(desktop.sys, "frozen", True, raising=False)

    payload = desktop._desktop_update_payload()

    assert payload["appId"] == desktop.APP_USER_MODEL_ID
    assert payload["version"] == desktop.APP_VERSION
    assert payload["canInstallUpdates"] is True
    assert payload["update"]["checked"] is True
