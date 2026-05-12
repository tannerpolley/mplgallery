from __future__ import annotations

import tomllib
from pathlib import Path
from unittest.mock import MagicMock

from typer.testing import CliRunner

import mplgallery.cli as cli
from mplgallery.cli import app


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = CliRunner()


def test_base_dependencies_keep_dvc_and_mlflow_optional() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())

    dependencies = "\n".join(pyproject["project"]["dependencies"]).lower()
    optional = pyproject["project"]["optional-dependencies"]
    dependency_groups = pyproject["dependency-groups"]

    assert "dvc" not in dependencies
    assert "mlflow" not in dependencies
    assert optional["dvc"] == ["dvc>=3.0"]
    assert optional["mlflow"] == ["mlflow>=2.0"]
    assert "windows-dist" in dependency_groups


def test_package_declares_frontend_dist_and_excludes_node_modules() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    wheel_config = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]
    sdist_config = pyproject["tool"]["hatch"]["build"]["targets"]["sdist"]
    desktop_source = (REPO_ROOT / "src" / "mplgallery" / "desktop.py").read_text(encoding="utf-8")

    assert (REPO_ROOT / "src/mplgallery/ui/frontend/dist/index.html").exists()
    assert (REPO_ROOT / "src/mplgallery/assets/mplgallery-icon.png").exists()
    assert (REPO_ROOT / "src/mplgallery/assets/mplgallery.ico").exists()
    assert (REPO_ROOT / "src/mplgallery/ui/frontend/public/favicon.png").exists()
    assert wheel_config["packages"] == ["src/mplgallery"]
    assert "src/mplgallery/ui/frontend/node_modules/**" in wheel_config["exclude"]
    assert "src/mplgallery/ui/frontend/node_modules/**" in sdist_config["exclude"]
    assert (REPO_ROOT / "scripts" / "build_windows_dist.py").exists()
    assert (REPO_ROOT / "packaging" / "windows" / "mplgallery.ico").exists()
    assert (REPO_ROOT / "scripts" / "install_windows_app.ps1").exists()
    assert (REPO_ROOT / "scripts" / "install_windows_app.cmd").exists()
    assert (REPO_ROOT / "scripts" / "run_windows_setup.cmd").exists()
    assert 'if __name__ == "__main__":' in desktop_source
    assert "gui_main()" in desktop_source


def test_console_script_and_run_command_expose_root_launcher() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())

    assert pyproject["project"]["scripts"]["mplgallery"] == "mplgallery.cli:main"
    assert pyproject["project"]["gui-scripts"]["mplgallery-desktop"] == "mplgallery.desktop:gui_main"

    result = RUNNER.invoke(app, ["run", "--help"])
    assert result.exit_code == 0, result.output
    assert "Open the static React browser preview" in result.output

    choose_root_result = RUNNER.invoke(app, ["run", "--choose-root", "--help"])
    assert choose_root_result.exit_code == 0, choose_root_result.output


def test_desktop_command_exposes_tauri_mode_and_browser_preview(monkeypatch) -> None:
    launch_mock = MagicMock(return_value=0)
    preview_mock = MagicMock(return_value=0)
    preview_url_mock = MagicMock(return_value="http://127.0.0.1:8765/browser-preview.html")
    monkeypatch.setattr(cli, "launch_desktop_app", launch_mock)
    monkeypatch.setattr(cli, "launch_browser_preview", preview_mock)
    monkeypatch.setattr(cli, "prepare_browser_preview", preview_url_mock)

    desktop_help = RUNNER.invoke(app, ["desktop", "--help"])
    assert desktop_help.exit_code == 0, desktop_help.output
    assert "tauri desktop app" in desktop_help.output.lower()

    desktop_result = RUNNER.invoke(app, ["desktop", "."])
    assert desktop_result.exit_code == 0, desktop_result.output
    launch_mock.assert_called_once()

    browser_result = RUNNER.invoke(app, ["desktop", ".", "--browser"])
    assert browser_result.exit_code == 0, browser_result.output
    preview_mock.assert_called_once()

    preview_url_result = RUNNER.invoke(app, ["preview-url", "."])
    assert preview_url_result.exit_code == 0, preview_url_result.output
    assert "http://127.0.0.1:8765/browser-preview.html" in preview_url_result.output


def test_windows_dist_build_embeds_app_metadata() -> None:
    build_script = (REPO_ROOT / "scripts" / "build_windows_dist.py").read_text(encoding="utf-8")
    installer_script = (REPO_ROOT / "scripts" / "install_windows_app.ps1").read_text(encoding="utf-8")
    release_workflow = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )

    assert "cargo" in build_script
    assert "npm.cmd" in build_script
    assert "mplgallery-desktop.exe" in build_script
    assert "tauri.conf.json" in build_script
    assert "Install MPLGallery.cmd" in build_script
    assert "MPLGallery Setup.exe" in build_script
    assert "run_windows_setup.cmd" in build_script
    assert "iexpress.exe" in build_script
    assert "Stop-MplGalleryProcesses" in installer_script
    assert "Start Menu" in installer_script
    assert "Desktop" in installer_script
    assert "windows-latest" in release_workflow
    assert "actions/setup-node@v4" in release_workflow
    assert "dtolnay/rust-toolchain@stable" in release_workflow
    assert "build_windows_dist.py" in release_workflow
