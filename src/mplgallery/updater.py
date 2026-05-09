from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import uuid
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from mplgallery import __version__


DEFAULT_RELEASE_REPOSITORY = "tannerpolley/mplgallery"
DEFAULT_RELEASE_API = f"https://api.github.com/repos/{DEFAULT_RELEASE_REPOSITORY}/releases/latest"


@dataclass(frozen=True)
class UpdateCheckResult:
    checked: bool
    available: bool = False
    current_version: str = __version__
    latest_version: str | None = None
    release_url: str | None = None
    download_url: str | None = None
    error: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        return {
            "checked": payload["checked"],
            "available": payload["available"],
            "currentVersion": payload["current_version"],
            "latestVersion": payload["latest_version"],
            "releaseUrl": payload["release_url"],
            "downloadUrl": payload["download_url"],
            "error": payload["error"],
        }


UrlOpener = Callable[[Request, float], Any]
ProcessLauncher = Callable[..., Any]


@dataclass(frozen=True)
class StagedWindowsUpdate:
    source_url: str
    root: Path
    archive_path: Path
    extract_dir: Path
    exe_path: Path
    installer_path: Path


@dataclass(frozen=True)
class UpdateInstallResult:
    started: bool
    staged: StagedWindowsUpdate
    helper_script: Path


def check_for_updates(
    *,
    current_version: str = __version__,
    release_api_url: str | None = None,
    opener: UrlOpener = urlopen,
    timeout_seconds: float = 2.5,
) -> UpdateCheckResult:
    """Check GitHub Releases for a newer desktop-friendly release."""
    if _update_checks_disabled():
        return UpdateCheckResult(checked=False, current_version=current_version)

    url = release_api_url or os.getenv("MPLGALLERY_RELEASE_API_URL") or DEFAULT_RELEASE_API
    request = Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "mplgallery"})
    try:
        with opener(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            return UpdateCheckResult(checked=True, current_version=current_version)
        return UpdateCheckResult(checked=True, current_version=current_version, error=str(exc))
    except URLError as exc:
        return UpdateCheckResult(
            checked=True,
            current_version=current_version,
            error=str(exc.reason),
        )
    except Exception as exc:
        return UpdateCheckResult(checked=True, current_version=current_version, error=str(exc))

    latest = str(payload.get("tag_name") or payload.get("name") or "").lstrip("v")
    if not _is_newer_version(latest, current_version):
        return UpdateCheckResult(
            checked=True,
            current_version=current_version,
            latest_version=latest or None,
            release_url=_release_url(payload),
        )

    asset = _preferred_windows_asset(payload.get("assets", []))
    return UpdateCheckResult(
        checked=True,
        available=True,
        current_version=current_version,
        latest_version=latest,
        release_url=_release_url(payload),
        download_url=asset.get("browser_download_url") if asset else _release_url(payload),
    )


def stage_windows_update(
    download_url: str,
    *,
    updates_root: Path | None = None,
    opener: UrlOpener = urlopen,
    timeout_seconds: float = 60.0,
) -> StagedWindowsUpdate:
    """Download and extract a Windows release ZIP into an update staging folder."""
    if not download_url:
        raise ValueError("download_url is required")
    root = (updates_root or _default_updates_root()) / time.strftime("%Y%m%d-%H%M%S") / uuid.uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    archive_path = root / "mplgallery-update.zip"
    extract_dir = root / "payload"
    request = Request(download_url, headers={"User-Agent": "mplgallery-updater"})
    with opener(request, timeout=timeout_seconds) as response:
        archive_path.write_bytes(response.read())
    _extract_update_zip(archive_path, extract_dir)
    exe_path = _find_required_update_file(extract_dir, "mplgallery-desktop.exe")
    installer_path = _find_required_update_file(extract_dir, "install_windows_app.ps1")
    return StagedWindowsUpdate(
        source_url=download_url,
        root=root,
        archive_path=archive_path,
        extract_dir=extract_dir,
        exe_path=exe_path,
        installer_path=installer_path,
    )


def install_windows_update(
    download_url: str,
    *,
    updates_root: Path | None = None,
    opener: UrlOpener = urlopen,
    launcher: ProcessLauncher = subprocess.Popen,
    process_ids: list[int] | None = None,
    install_dir: Path | None = None,
    timeout_seconds: float = 60.0,
) -> UpdateInstallResult:
    """Stage a Windows release ZIP and launch a detached helper that installs it."""
    staged = stage_windows_update(
        download_url,
        updates_root=updates_root,
        opener=opener,
        timeout_seconds=timeout_seconds,
    )
    helper_script = staged.root / "install-update.ps1"
    _write_update_helper(
        helper_script,
        staged=staged,
        process_ids=process_ids or _current_process_ids(),
        install_dir=install_dir or _default_install_dir(),
    )
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(helper_script),
    ]
    kwargs: dict[str, Any] = {
        "cwd": str(staged.root),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    launcher(command, **kwargs)
    return UpdateInstallResult(started=True, staged=staged, helper_script=helper_script)


def _update_checks_disabled() -> bool:
    return os.getenv("MPLGALLERY_DISABLE_UPDATE_CHECK", "").strip().lower() in {"1", "true", "yes"}


def _default_updates_root() -> Path:
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "MPLGallery" / "updates"
    return Path.home() / ".mplgallery" / "updates"


def _default_install_dir() -> Path:
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "Programs" / "MPLGallery"
    return Path.home() / "MPLGallery"


def _extract_update_zip(archive_path: Path, extract_dir: Path) -> None:
    shutil.rmtree(extract_dir, ignore_errors=True)
    extract_dir.mkdir(parents=True, exist_ok=True)
    root = extract_dir.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            target = (extract_dir / member.filename).resolve()
            if root != target and root not in target.parents:
                raise RuntimeError(f"Unsafe update archive path: {member.filename}")
        archive.extractall(extract_dir)


def _find_required_update_file(root: Path, name: str) -> Path:
    matches = sorted(path for path in root.rglob(name) if path.is_file())
    if not matches:
        raise RuntimeError(f"Update archive is missing {name}")
    return matches[0]


def _current_process_ids() -> list[int]:
    process_ids = [os.getpid()]
    try:
        parent_pid = os.getppid()
    except AttributeError:
        parent_pid = 0
    if parent_pid > 0 and parent_pid not in process_ids:
        process_ids.append(parent_pid)
    return process_ids


def _write_update_helper(
    output_path: Path,
    *,
    staged: StagedWindowsUpdate,
    process_ids: list[int],
    install_dir: Path,
) -> None:
    pid_values = ", ".join(str(process_id) for process_id in process_ids if process_id > 0)
    installed_exe = install_dir / "mplgallery-desktop.exe"
    output_path.write_text(
        f"""$ErrorActionPreference = "Stop"
$sourceExe = {_powershell_string(staged.exe_path)}
$installer = {_powershell_string(staged.installer_path)}
$installDir = {_powershell_string(install_dir)}
$installedExe = {_powershell_string(installed_exe)}
$processIds = @({pid_values})

Start-Sleep -Seconds 1
foreach ($processId in $processIds) {{
    if ($processId -ne $PID) {{
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }}
}}
foreach ($processId in $processIds) {{
    Wait-Process -Id $processId -Timeout 20 -ErrorAction SilentlyContinue
}}

& powershell -NoProfile -ExecutionPolicy Bypass -File $installer -ExePath $sourceExe -InstallDir $installDir -DesktopShortcut
Start-Process -FilePath $installedExe
""",
        encoding="utf-8",
    )


def _powershell_string(path: Path) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def _release_url(payload: dict[str, Any]) -> str | None:
    value = payload.get("html_url")
    return str(value) if value else None


def _preferred_windows_asset(assets: object) -> dict[str, Any] | None:
    if not isinstance(assets, list):
        return None
    candidates = [asset for asset in assets if isinstance(asset, dict)]
    candidates.sort(key=lambda asset: _asset_score(str(asset.get("name") or "")), reverse=True)
    for asset in candidates:
        if _asset_score(str(asset.get("name") or "")) > 0:
            return asset
    return candidates[0] if candidates else None


def _asset_score(name: str) -> int:
    lowered = name.lower()
    score = 0
    if "windows" in lowered or lowered.endswith(".exe"):
        score += 10
    if "desktop" in lowered:
        score += 6
    if lowered.endswith(".zip"):
        score += 4
    if lowered.endswith(".exe"):
        score += 2
    if "source" in lowered or lowered.endswith(".tar.gz"):
        score -= 10
    return score


def _is_newer_version(candidate: str, current: str) -> bool:
    candidate_parts = _version_parts(candidate)
    current_parts = _version_parts(current)
    if candidate_parts is None or current_parts is None:
        return False
    width = max(len(candidate_parts), len(current_parts), 3)
    padded_candidate = candidate_parts + (0,) * (width - len(candidate_parts))
    padded_current = current_parts + (0,) * (width - len(current_parts))
    return padded_candidate > padded_current


def _version_parts(value: str) -> tuple[int, ...] | None:
    match = re.match(r"^v?(\d+(?:\.\d+){0,3})", value.strip())
    if match is None:
        return None
    return tuple(int(part) for part in match.group(1).split("."))
