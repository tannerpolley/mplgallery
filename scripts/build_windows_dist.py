from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import tomllib
from pathlib import Path

from PyInstaller import __main__ as pyinstaller_main
from PyInstaller.utils.hooks import collect_all, collect_submodules


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = REPO_ROOT / "build" / "windows-dist"
DIST_ROOT = REPO_ROOT / "dist" / "windows"
SPEC_ROOT = BUILD_ROOT / "pyinstaller"
SELF_TEST_JSON = BUILD_ROOT / "self-test.json"
SMOKE_TEST_JSON = BUILD_ROOT / "smoke-test.json"
BUILD_REPORT_JSON = DIST_ROOT / "mplgallery-desktop-build.json"


def main() -> None:
    if platform.system() != "Windows":
        raise SystemExit("Windows distribution build is only supported on Windows hosts.")

    version = _project_version()
    exe_path = DIST_ROOT / "mplgallery-desktop.exe"
    zip_path = DIST_ROOT / _zip_name(version)

    _reset_paths()
    args = _pyinstaller_args(exe_path)
    pyinstaller_main.run(args)
    _verify_executable(exe_path)
    _write_zip(exe_path, zip_path)
    _write_report(exe_path, zip_path, version)

    print(exe_path)
    print(zip_path)
    print(BUILD_REPORT_JSON)


def _project_version() -> str:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(pyproject["project"]["version"])


def _reset_paths() -> None:
    shutil.rmtree(BUILD_ROOT, ignore_errors=True)
    DIST_ROOT.mkdir(parents=True, exist_ok=True)
    SPEC_ROOT.mkdir(parents=True, exist_ok=True)


def _pyinstaller_args(exe_path: Path) -> list[str]:
    datas: list[tuple[str, str]] = _mplgallery_runtime_datas()
    binaries: list[tuple[str, str]] = []
    hiddenimports: list[str] = collect_submodules("mplgallery")
    for package_name, include_py in (
        ("streamlit", False),
        ("webview", False),
    ):
        pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(package_name, include_py_files=include_py)
        datas.extend(pkg_datas)
        binaries.extend(pkg_binaries)
        hiddenimports.extend(pkg_hiddenimports)

    args = [
        str(REPO_ROOT / "src" / "mplgallery" / "desktop.py"),
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        "mplgallery-desktop",
        "--distpath",
        str(exe_path.parent),
        "--workpath",
        str(SPEC_ROOT / "work"),
        "--specpath",
        str(SPEC_ROOT),
    ]
    separator = ";" if os.name == "nt" else ":"
    for src, dest in datas:
        args.extend(["--add-data", f"{src}{separator}{dest}"])
    for src, dest in binaries:
        args.extend(["--add-binary", f"{src}{separator}{dest}"])
    for hiddenimport in sorted(set(hiddenimports)):
        args.extend(["--hidden-import", hiddenimport])
    return args


def _mplgallery_runtime_datas() -> list[tuple[str, str]]:
    ui_root = REPO_ROOT / "src" / "mplgallery" / "ui"
    frontend_dist = ui_root / "frontend" / "dist"
    datas = [(str(ui_root / "app.py"), "mplgallery/ui")]
    for file_path in frontend_dist.rglob("*"):
        if file_path.is_file():
            destination = Path("mplgallery/ui/frontend/dist") / file_path.relative_to(
                frontend_dist
            ).parent
            datas.append((str(file_path), destination.as_posix()))
    return datas


def _verify_executable(exe_path: Path) -> None:
    subprocess.run(
        [str(exe_path), "--self-test-out", str(SELF_TEST_JSON)],
        check=True,
        cwd=REPO_ROOT,
        timeout=180,
    )
    subprocess.run(
        [
            str(exe_path),
            "examples",
            "--smoke-browser-launch",
            "--port",
            "8626",
            "--self-test-out",
            str(SMOKE_TEST_JSON),
        ],
        check=True,
        cwd=REPO_ROOT,
        timeout=240,
    )


def _write_zip(exe_path: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", exe_path.parent, exe_path.name)


def _write_report(exe_path: Path, zip_path: Path, version: str) -> None:
    BUILD_REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": version,
        "platform": platform.platform(),
        "artifact": str(exe_path),
        "zip": str(zip_path),
        "self_test": json.loads(SELF_TEST_JSON.read_text(encoding="utf-8")),
        "smoke_test": json.loads(SMOKE_TEST_JSON.read_text(encoding="utf-8")),
    }
    BUILD_REPORT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _zip_name(version: str) -> str:
    machine = platform.machine().lower() or "unknown"
    return f"mplgallery-desktop-{version}-windows-{machine}.zip"


if __name__ == "__main__":
    main()
