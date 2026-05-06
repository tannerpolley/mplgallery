from __future__ import annotations

import subprocess
import sys
import tomllib
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
