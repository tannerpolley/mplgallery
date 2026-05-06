from __future__ import annotations

import tomllib
from pathlib import Path

from typer.testing import CliRunner

from mplgallery.cli import app


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = CliRunner()


def test_base_dependencies_keep_dvc_and_mlflow_optional() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())

    dependencies = "\n".join(pyproject["project"]["dependencies"]).lower()
    optional = pyproject["project"]["optional-dependencies"]

    assert "dvc" not in dependencies
    assert "mlflow" not in dependencies
    assert optional["dvc"] == ["dvc>=3.0"]
    assert optional["mlflow"] == ["mlflow>=2.0"]


def test_package_declares_frontend_dist_and_excludes_node_modules() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    wheel_config = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]
    sdist_config = pyproject["tool"]["hatch"]["build"]["targets"]["sdist"]

    assert (REPO_ROOT / "src/mplgallery/ui/frontend/dist/index.html").exists()
    assert wheel_config["packages"] == ["src/mplgallery"]
    assert "src/mplgallery/ui/frontend/node_modules/**" in wheel_config["exclude"]
    assert "src/mplgallery/ui/frontend/node_modules/**" in sdist_config["exclude"]


def test_console_script_and_run_command_expose_root_launcher() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())

    assert pyproject["project"]["scripts"]["mplgallery"] == "mplgallery.cli:main"

    result = RUNNER.invoke(app, ["run", "--help"])
    assert result.exit_code == 0, result.output
    assert "Launch the local Streamlit CSV plot studio" in result.output
    assert "--choose-root" in result.output
