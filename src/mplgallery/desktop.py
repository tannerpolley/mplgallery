from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

from mplgallery import __version__


APP_NAME = "MPLGallery"
APP_VERSION = __version__
APP_USER_MODEL_ID = "Tanner.MPLGallery"

REPO_ROOT = Path(__file__).resolve().parents[2]
TAURI_ROOT = REPO_ROOT / "src-tauri"
FRONTEND_DIST_ROOT = REPO_ROOT / "src" / "mplgallery" / "ui" / "frontend" / "dist"


def launch_desktop_app(
    project_root: Path | None = None,
    *,
    choose_root: bool = False,
    include_artifacts: bool = True,
    image_library: bool = False,
    width: int = 1600,
    height: int = 1000,
    title: str = APP_NAME,
) -> int:
    command = _tauri_command()
    env = _tauri_env(
        project_root=project_root,
        choose_root=choose_root,
        include_artifacts=include_artifacts,
        image_library=image_library,
        width=width,
        height=height,
        title=title,
    )
    return subprocess.run(command, check=False, cwd=REPO_ROOT, env=env).returncode


def launch_browser_preview(
    project_root: Path | None = None,
    *,
    include_artifacts: bool = True,
    image_library: bool = False,
) -> int:
    preview_url = prepare_browser_preview(
        project_root=project_root,
        include_artifacts=include_artifacts,
        image_library=image_library,
    )
    webbrowser.open(preview_url)
    return 0


def prepare_browser_preview(
    project_root: Path | None = None,
    *,
    include_artifacts: bool = True,
    image_library: bool = False,
) -> str:
    preview_path = _browser_preview_html_path(
        project_root=project_root,
        include_artifacts=include_artifacts,
        image_library=image_library,
    )
    return _start_browser_preview_server(preview_path.parent, preview_path.name)


def gui_main() -> None:
    parser = argparse.ArgumentParser(prog="mplgallery-desktop")
    parser.add_argument("--self-test-out", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("project_root", nargs="?", default=None, help="Project directory to open.")
    parser.add_argument(
        "--choose-root",
        action="store_true",
        help="Start with the project picker emphasized when the desktop host supports it.",
    )
    parser.add_argument(
        "--include-artifacts",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Show PNG/SVG artifact records alongside CSV summaries.",
    )
    parser.add_argument(
        "--image-library",
        action="store_true",
        help="Browse loose PNG/SVG images instead of analysis-linked plot sets.",
    )
    parser.add_argument(
        "--browser",
        action="store_true",
        help="Open the static browser preview instead of the Tauri desktop app.",
    )
    parser.add_argument("--width", type=int, default=1600, help="Preferred desktop window width.")
    parser.add_argument("--height", type=int, default=1000, help="Preferred desktop window height.")
    args = parser.parse_args()

    if args.self_test_out is not None:
        _write_self_test(args.self_test_out)
        raise SystemExit(0)

    project_root = Path(args.project_root).expanduser().resolve() if args.project_root else None
    try:
        if args.browser:
            raise SystemExit(launch_browser_preview())
        raise SystemExit(
            launch_desktop_app(
                project_root,
                choose_root=args.choose_root,
                include_artifacts=args.include_artifacts,
                image_library=args.image_library,
                width=args.width,
                height=args.height,
            )
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc


def _tauri_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [str(Path(sys.executable))]
    cargo = shutil.which("cargo")
    if cargo is not None:
        return [cargo, "run", "--manifest-path", str(TAURI_ROOT / "Cargo.toml")]
    for candidate in _tauri_executable_candidates():
        if candidate.exists():
            return [str(candidate)]
    raise RuntimeError(
        "No Tauri desktop executable was found and cargo is unavailable. "
        "Build the desktop app first with `uv run python scripts/build_windows_dist.py` "
        "or install Rust to use the development launcher."
    )


def _tauri_executable_candidates() -> list[Path]:
    candidates = [
        TAURI_ROOT / "target" / "release" / "mplgallery-desktop.exe",
        TAURI_ROOT / "target" / "debug" / "mplgallery-desktop.exe",
        REPO_ROOT / "dist" / "windows" / "mplgallery-desktop.exe",
    ]
    return candidates


def _tauri_env(
    *,
    project_root: Path | None,
    choose_root: bool,
    include_artifacts: bool,
    image_library: bool,
    width: int,
    height: int,
    title: str,
) -> dict[str, str]:
    env = os.environ.copy()
    env["MPLGALLERY_ACTIVE_ROOT"] = str(project_root) if project_root is not None else ""
    env["MPLGALLERY_CHOOSE_ROOT"] = "1" if choose_root else "0"
    env["MPLGALLERY_INCLUDE_ARTIFACTS"] = "1" if include_artifacts else "0"
    env["MPLGALLERY_IMAGE_LIBRARY"] = "1" if image_library else "0"
    env["MPLGALLERY_WINDOW_WIDTH"] = str(width)
    env["MPLGALLERY_WINDOW_HEIGHT"] = str(height)
    env["MPLGALLERY_WINDOW_TITLE"] = title
    return env


def _preview_html_path() -> Path:
    preview = FRONTEND_DIST_ROOT / "index.html"
    if not preview.exists():
        raise RuntimeError(
            "Browser preview assets are missing. Build the frontend first with "
            "`npm --prefix src/mplgallery/ui/frontend run build`."
        )
    return preview


def _browser_preview_html_path(
    *,
    project_root: Path | None,
    include_artifacts: bool,
    image_library: bool,
) -> Path:
    preview = _preview_html_path()
    active_root = (project_root or (REPO_ROOT / "examples")).expanduser().resolve()
    payload_json = json.dumps(
        _browser_preview_payload(
            active_root,
            include_artifacts=include_artifacts,
            image_library=image_library,
        ),
        separators=(",", ":"),
    ).replace("</", "<\\/")
    html = preview.read_text(encoding="utf-8")
    injection = f'<script>window.__MPLGALLERY_BROWSER_PAYLOAD__={payload_json};</script>\n'
    if '<script type="module"' in html:
        html = html.replace('<script type="module"', f"{injection}    <script type=\"module\"", 1)
    else:
        html = html.replace("</head>", f"    {injection}</head>", 1)
    target = FRONTEND_DIST_ROOT / "browser-preview.html"
    target.write_text(html, encoding="utf-8")
    return target


def _browser_preview_payload(
    project_root: Path,
    *,
    include_artifacts: bool,
    image_library: bool,
) -> dict[str, object]:
    from mplgallery.core.studio import build_csv_studio_index
    from mplgallery.core.user_settings import load_user_settings
    from mplgallery.ui.component import _plot_set_payloads, build_component_payload

    settings = load_user_settings()
    index = build_csv_studio_index(
        project_root,
        include_artifacts=include_artifacts,
        image_library_mode=image_library,
    )
    hydrated_plot_set_ids = {
        str(plot_set["plotSetId"])
        for plot_set in _plot_set_payloads(index.records, index.datasets)
        if "plotSetId" in plot_set
    }
    return build_component_payload(
        project_root=project_root,
        active_root=project_root,
        records=index.records,
        datasets=index.datasets,
        browse_mode=index.browse_mode,
        selected_plot_id=None,
        errors={},
        launch_root=project_root,
        recent_roots=settings.recent_roots if settings.remember_recent_projects else (),
        root_error=None,
        show_root_chooser=False,
        hydrated_plot_set_ids=hydrated_plot_set_ids,
        app_info=_desktop_update_payload(),
        user_settings=settings,
    )


def _start_browser_preview_server(preview_root: Path, preview_name: str) -> str:
    port = _find_open_port(preferred=51226)
    command = [
        sys.executable,
        "-m",
        "mplgallery.preview_server",
        "--directory",
        str(preview_root),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(
        command,
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    _wait_for_local_server("127.0.0.1", port)
    return f"http://127.0.0.1:{port}/{preview_name}"


def _find_open_port(*, preferred: int | None = None) -> int:
    if preferred is not None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", preferred))
            except OSError:
                pass
            else:
                return preferred
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_local_server(host: str, port: int, *, timeout_seconds: float = 5.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            if sock.connect_ex((host, port)) == 0:
                return
        time.sleep(0.1)
    raise RuntimeError(f"Browser preview server did not start on http://{host}:{port}/")


def _write_self_test(output_path: Path) -> None:
    command = _tauri_command()
    payload = {
        "ok": True,
        "version": APP_VERSION,
        "app_id": APP_USER_MODEL_ID,
        "launcher_command": command,
        "preview_html": str(_preview_html_path()) if (FRONTEND_DIST_ROOT / "index.html").exists() else None,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _desktop_update_payload() -> dict[str, object]:
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "appId": APP_USER_MODEL_ID,
        "canInstallUpdates": False,
        "update": {
            "checked": False,
            "available": False,
            "currentVersion": APP_VERSION,
            "latestVersion": APP_VERSION,
            "error": None,
        },
    }


if __name__ == "__main__":
    gui_main()
