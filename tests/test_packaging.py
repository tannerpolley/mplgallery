from __future__ import annotations

import json
import subprocess
import sys
import tomllib
import venv
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_base_dependencies_keep_dvc_and_mlflow_optional() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())

    dependencies = "\n".join(pyproject["project"]["dependencies"]).lower()
    optional = pyproject["project"]["optional-dependencies"]

    assert "dvc" not in dependencies
    assert "mlflow" not in dependencies
    assert optional["dvc"] == ["dvc>=3.0"]
    assert optional["mlflow"] == ["mlflow>=2.0"]


def test_wheel_includes_built_frontend_dist_without_node_modules(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(dist_dir),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    [wheel_path] = list(dist_dir.glob("*.whl"))
    with zipfile.ZipFile(wheel_path) as wheel:
        names = set(wheel.namelist())

    assert "mplgallery/ui/frontend/dist/index.html" in names
    assert not any("node_modules" in name for name in names)


def test_fresh_wheel_install_exposes_project_root_run_command(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(dist_dir),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    [wheel_path] = list(dist_dir.glob("*.whl"))

    venv_dir = tmp_path / "venv"
    venv.EnvBuilder(with_pip=True).create(venv_dir)
    python = venv_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    mplgallery = venv_dir / ("Scripts/mplgallery.exe" if sys.platform == "win32" else "bin/mplgallery")

    install = subprocess.run(
        [str(python), "-m", "pip", "install", str(wheel_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert install.returncode == 0, install.stdout + install.stderr

    external_project = tmp_path / "external_analysis"
    data_dir = external_project / "data" / "processed"
    data_dir.mkdir(parents=True)
    (data_dir / "model_results.csv").write_text(
        "time,response,baseline\n0,0.0,0.02\n1,0.2,0.15\n2,0.5,0.45\n",
        encoding="utf-8",
    )

    help_result = subprocess.run(
        [str(mplgallery), "run", "--help"],
        cwd=external_project,
        capture_output=True,
        text=True,
        check=False,
    )
    assert help_result.returncode == 0, help_result.stdout + help_result.stderr
    assert "Launch the local Streamlit CSV plot studio" in help_result.stdout
    choose_root_help_result = subprocess.run(
        [str(mplgallery), "run", "--choose-root", "--help"],
        cwd=external_project,
        capture_output=True,
        text=True,
        check=False,
    )
    assert choose_root_help_result.returncode == 0, (
        choose_root_help_result.stdout + choose_root_help_result.stderr
    )

    draft_result = subprocess.run(
        [str(mplgallery), "draft", "data", "--json"],
        cwd=external_project,
        capture_output=True,
        text=True,
        check=False,
    )
    assert draft_result.returncode == 0, draft_result.stdout + draft_result.stderr
    draft_payload = json.loads(draft_result.stdout)
    assert draft_payload["datasets"] == 1
    assert draft_payload["records"]
    generated_plot = external_project / draft_payload["records"][0]["plot_path"]
    assert generated_plot.exists()
    assert generated_plot.parent.as_posix().endswith("results/final/figures/mplgallery")

    scan_result = subprocess.run(
        [str(mplgallery), "scan", ".", "--json"],
        cwd=external_project,
        capture_output=True,
        text=True,
        check=False,
    )
    assert scan_result.returncode == 0, scan_result.stdout + scan_result.stderr
    scan_payload = json.loads(scan_result.stdout)
    assert any("model_results.csv" in dataset["relative_path"] for dataset in scan_payload["datasets"])
    assert scan_payload["plots_discovered"] >= 1
