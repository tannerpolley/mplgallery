from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import tomllib
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = REPO_ROOT / "build" / "windows-dist"
DIST_ROOT = REPO_ROOT / "dist" / "windows"
BUILD_REPORT_JSON = DIST_ROOT / "mplgallery-desktop-build.json"
INSTALLER_SCRIPT = REPO_ROOT / "scripts" / "install_windows_app.ps1"
INSTALLER_WRAPPER = REPO_ROOT / "scripts" / "install_windows_app.cmd"
INSTALLER_WRAPPER_NAME = "Install MPLGallery.cmd"
SETUP_WRAPPER = REPO_ROOT / "scripts" / "run_windows_setup.cmd"
SETUP_WRAPPER_NAME = "run_windows_setup.cmd"
SETUP_EXE_NAME = "MPLGallery Setup.exe"
IEXPRESS_SED = BUILD_ROOT / "mplgallery-setup.sed"
TAURI_ROOT = REPO_ROOT / "src-tauri"
TAURI_TARGET = TAURI_ROOT / "target" / "release"
TAURI_EXE_NAME = "mplgallery-desktop.exe"
TAURI_CONF = TAURI_ROOT / "tauri.conf.json"
FRONTEND_ROOT = REPO_ROOT / "src" / "mplgallery" / "ui" / "frontend"


def main() -> None:
    if platform.system() != "Windows":
        raise SystemExit("Windows distribution build is only supported on Windows hosts.")

    version = _project_version()
    exe_path = DIST_ROOT / TAURI_EXE_NAME
    zip_path = DIST_ROOT / _zip_name(version)
    setup_path = DIST_ROOT / SETUP_EXE_NAME

    _reset_paths()
    _build_frontend()
    built_exe = _build_tauri_release()
    shutil.copy2(built_exe, exe_path)
    _verify_executable(exe_path)
    _write_installer_files(exe_path)
    _write_setup_exe(setup_path)
    _write_zip(exe_path, zip_path, setup_path)
    _write_report(exe_path, zip_path, setup_path, version)

    print(exe_path)
    print(setup_path)
    print(zip_path)
    print(BUILD_REPORT_JSON)


def _project_version() -> str:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(pyproject["project"]["version"])


def _reset_paths() -> None:
    shutil.rmtree(BUILD_ROOT, ignore_errors=True)
    shutil.rmtree(DIST_ROOT, ignore_errors=True)
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    DIST_ROOT.mkdir(parents=True, exist_ok=True)


def _run(command: list[str], *, cwd: Path) -> None:
    subprocess.run(command, check=True, cwd=cwd)


def _build_frontend() -> None:
    _run(["npm.cmd", "install"], cwd=FRONTEND_ROOT)
    _run(["npm.cmd", "run", "build"], cwd=FRONTEND_ROOT)


def _build_tauri_release() -> Path:
    tauri_cli = FRONTEND_ROOT / "node_modules" / ".bin" / "tauri.cmd"
    if not tauri_cli.exists():
        raise RuntimeError(f"Tauri CLI was not installed: {tauri_cli}")
    _run([str(tauri_cli), "build", "--config", str(TAURI_CONF)], cwd=REPO_ROOT)
    exe_path = TAURI_TARGET / TAURI_EXE_NAME
    if not exe_path.exists():
        raise RuntimeError(f"Expected Tauri executable was not created: {exe_path}")
    return exe_path


def _verify_executable(exe_path: Path) -> None:
    if not exe_path.exists():
        raise RuntimeError(f"Expected packaged executable does not exist: {exe_path}")
    if exe_path.stat().st_size <= 0:
        raise RuntimeError(f"Packaged executable is empty: {exe_path}")


def _write_installer_files(exe_path: Path) -> None:
    packaged_script = DIST_ROOT / INSTALLER_SCRIPT.name
    packaged_wrapper = DIST_ROOT / INSTALLER_WRAPPER_NAME
    packaged_setup_wrapper = DIST_ROOT / SETUP_WRAPPER_NAME
    shutil.copy2(INSTALLER_SCRIPT, packaged_script)
    shutil.copy2(INSTALLER_WRAPPER, packaged_wrapper)
    shutil.copy2(SETUP_WRAPPER, packaged_setup_wrapper)


def _write_setup_exe(setup_path: Path) -> None:
    iexpress_path = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "iexpress.exe"
    if not iexpress_path.exists():
        raise RuntimeError("iexpress.exe was not found; cannot build MPLGallery Setup.exe")
    if setup_path.exists():
        setup_path.unlink()
    IEXPRESS_SED.parent.mkdir(parents=True, exist_ok=True)
    IEXPRESS_SED.write_text(_iexpress_sed(setup_path), encoding="utf-8")
    subprocess.run([str(iexpress_path), "/N", str(IEXPRESS_SED)], check=True, cwd=DIST_ROOT)
    if not setup_path.exists():
        raise RuntimeError(f"Expected installer was not created: {setup_path}")


def _write_zip(exe_path: Path, zip_path: Path, setup_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(setup_path, setup_path.name)
        archive.write(exe_path, exe_path.name)
        archive.write(DIST_ROOT / INSTALLER_SCRIPT.name, INSTALLER_SCRIPT.name)
        archive.write(DIST_ROOT / INSTALLER_WRAPPER_NAME, INSTALLER_WRAPPER_NAME)
        archive.write(DIST_ROOT / SETUP_WRAPPER_NAME, SETUP_WRAPPER_NAME)


def _write_report(exe_path: Path, zip_path: Path, setup_path: Path, version: str) -> None:
    BUILD_REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": version,
        "platform": platform.platform(),
        "artifact": str(exe_path),
        "zip": str(zip_path),
        "setup": str(setup_path),
        "app_name": "MPLGallery",
        "app_id": "Tanner.MPLGallery",
        "installer": str(setup_path),
        "packaging_runtime": "tauri",
        "tauri_config": str(TAURI_CONF),
        "frontend_dist": str(FRONTEND_ROOT / "dist"),
        "self_test": {"status": "not_available", "reason": "tauri desktop binary has no CLI self-test mode"},
        "smoke_test": {"status": "not_available", "reason": "GUI smoke validation is performed outside the build script"},
    }
    BUILD_REPORT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _iexpress_sed(setup_path: Path) -> str:
    source_dir = str(DIST_ROOT) + "\\"
    return f"""[Version]
Class=IEXPRESS
SEDVersion=3
[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=0
HideExtractAnimation=0
UseLongFileName=1
InsideCompressed=0
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=%InstallPrompt%
DisplayLicense=%DisplayLicense%
FinishMessage=%FinishMessage%
TargetName=%TargetName%
FriendlyName=%FriendlyName%
AppLaunched=%AppLaunched%
PostInstallCmd=%PostInstallCmd%
AdminQuietInstCmd=%AdminQuietInstCmd%
UserQuietInstCmd=%UserQuietInstCmd%
SourceFiles=SourceFiles
[Strings]
InstallPrompt=
DisplayLicense=
FinishMessage=MPLGallery has been installed. Search for MPLGallery in the Windows Start menu.
TargetName={setup_path}
FriendlyName=MPLGallery Setup
AppLaunched={SETUP_WRAPPER_NAME}
PostInstallCmd=<None>
AdminQuietInstCmd={SETUP_WRAPPER_NAME}
UserQuietInstCmd={SETUP_WRAPPER_NAME}
FILE0={TAURI_EXE_NAME}
FILE1={INSTALLER_SCRIPT.name}
FILE2={SETUP_WRAPPER_NAME}
[SourceFiles]
SourceFiles0={source_dir}
[SourceFiles0]
%FILE0%=
%FILE1%=
%FILE2%=
"""


def _zip_name(version: str) -> str:
    machine = platform.machine().lower() or "unknown"
    return f"mplgallery-desktop-{version}-windows-{machine}.zip"


if __name__ == "__main__":
    main()
