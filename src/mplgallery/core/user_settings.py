from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CONFIG_HOME_ENV = "MPLGALLERY_CONFIG_HOME"
MAX_RECENT_ROOTS = 8


@dataclass(frozen=True)
class UserSettings:
    recent_roots: tuple[Path, ...] = field(default_factory=tuple)
    last_active_root: Path | None = None


def settings_path() -> Path:
    config_home = os.environ.get(CONFIG_HOME_ENV)
    if config_home:
        return Path(config_home).expanduser() / "settings.json"
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata).expanduser() if appdata else Path.home() / "AppData" / "Roaming"
        return base / "mplgallery" / "settings.json"
    return Path.home() / ".config" / "mplgallery" / "settings.json"


def load_user_settings(*, path: Path | None = None) -> UserSettings:
    target = path or settings_path()
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return UserSettings()
    if not isinstance(payload, dict):
        return UserSettings()

    recent_roots = _paths_from_payload(payload.get("recent_roots"))
    last_active_root = _path_from_payload(payload.get("last_active_root"))
    if last_active_root is not None and last_active_root not in recent_roots:
        recent_roots = (last_active_root, *recent_roots)
    return UserSettings(
        recent_roots=recent_roots[:MAX_RECENT_ROOTS],
        last_active_root=last_active_root,
    )


def save_user_settings(settings: UserSettings, *, path: Path | None = None) -> None:
    target = path or settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "recent_roots": [str(root) for root in settings.recent_roots],
        "last_active_root": str(settings.last_active_root)
        if settings.last_active_root is not None
        else None,
    }
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def remember_recent_root(
    settings: UserSettings,
    root: Path,
    *,
    max_recent_roots: int = MAX_RECENT_ROOTS,
) -> UserSettings:
    normalized = _normalize_root(root)
    deduped = tuple(
        recent for recent in settings.recent_roots if _root_key(recent) != _root_key(normalized)
    )
    return UserSettings(
        recent_roots=(normalized, *deduped)[:max_recent_roots],
        last_active_root=normalized,
    )


def forget_recent_root(settings: UserSettings, root: Path) -> UserSettings:
    normalized = _normalize_root(root)
    recent_roots = tuple(
        recent for recent in settings.recent_roots if _root_key(recent) != _root_key(normalized)
    )
    last_active_root = settings.last_active_root
    if last_active_root is not None and _root_key(last_active_root) == _root_key(normalized):
        last_active_root = None
    return UserSettings(recent_roots=recent_roots, last_active_root=last_active_root)


def _paths_from_payload(value: Any) -> tuple[Path, ...]:
    if not isinstance(value, list):
        return ()
    paths: list[Path] = []
    seen: set[str] = set()
    for item in value:
        path = _path_from_payload(item)
        if path is None:
            continue
        key = _root_key(path)
        if key in seen:
            continue
        seen.add(key)
        paths.append(path)
    return tuple(paths)


def _path_from_payload(value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return _normalize_root(Path(value))


def _normalize_root(root: Path) -> Path:
    return root.expanduser().resolve(strict=False)


def _root_key(root: Path) -> str:
    return os.path.normcase(str(_normalize_root(root)))
