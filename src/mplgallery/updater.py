from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
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


def _update_checks_disabled() -> bool:
    return os.getenv("MPLGALLERY_DISABLE_UPDATE_CHECK", "").strip().lower() in {"1", "true", "yes"}


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
