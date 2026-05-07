from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mplgallery.core.user_settings import UserSettings, remember_recent_root


@dataclass(frozen=True)
class RootChangeResult:
    active_root: Path | None
    settings: UserSettings
    error: str | None = None


def resolve_initial_root(
    launch_root: Path,
    settings: UserSettings,
    *,
    choose_root: bool,
) -> Path:
    normalized_launch = launch_root.expanduser().resolve(strict=False)
    if choose_root and settings.last_active_root is not None and settings.last_active_root.is_dir():
        return settings.last_active_root.resolve()
    return normalized_launch


def change_active_root(root_path: str, settings: UserSettings) -> RootChangeResult:
    candidate_text = root_path.strip()
    if not candidate_text:
        return RootChangeResult(
            active_root=None,
            settings=settings,
            error="Enter a project root directory.",
        )
    candidate = Path(candidate_text).expanduser().resolve(strict=False)
    if not candidate.exists():
        return RootChangeResult(
            active_root=None,
            settings=settings,
            error=f"Project root does not exist: {candidate}",
        )
    if not candidate.is_dir():
        return RootChangeResult(
            active_root=None,
            settings=settings,
            error=f"Project root is not a directory: {candidate}",
        )
    return RootChangeResult(
        active_root=candidate.resolve(),
        settings=remember_recent_root(settings, candidate),
    )


def reset_active_root(launch_root: Path, settings: UserSettings) -> RootChangeResult:
    launch = launch_root.expanduser().resolve(strict=False)
    if not launch.is_dir():
        return RootChangeResult(
            active_root=None,
            settings=settings,
            error=f"Launch root is not available: {launch}",
        )
    return RootChangeResult(
        active_root=launch.resolve(),
        settings=remember_recent_root(settings, launch),
    )


def browse_active_root(settings: UserSettings, initial_root: Path | None = None) -> RootChangeResult:
    selected = _pick_directory(initial_root)
    if selected is None:
        return RootChangeResult(
            active_root=None,
            settings=settings,
            error="Folder selection was cancelled or is not available in this environment.",
        )
    return change_active_root(str(selected), settings)


def _pick_directory(initial_root: Path | None) -> Path | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return None

    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(
            initialdir=str(initial_root) if initial_root and initial_root.exists() else None,
            title="Choose MPLGallery project root",
        )
        root.destroy()
    except Exception:
        return None
    if not selected:
        return None
    return Path(selected)
