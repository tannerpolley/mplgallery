from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def launch_desktop_app(
    project_root: Path,
    *,
    port: int | None = None,
    choose_root: bool = False,
    include_artifacts: bool = True,
    width: int = 1600,
    height: int = 1000,
    title: str = "MPLGallery",
) -> int:
    try:
        import webview
    except ImportError as exc:  # pragma: no cover - dependency guidance path
        raise RuntimeError(
            "Desktop mode requires the optional 'desktop' dependency. "
            "Install with: uv sync --extra desktop"
        ) from exc

    resolved_root = project_root.expanduser().resolve()
    server_port = port or _find_free_port()
    server_process = _start_streamlit_server(
        resolved_root,
        port=server_port,
        choose_root=choose_root,
        include_artifacts=include_artifacts,
    )
    url = f"http://127.0.0.1:{server_port}"
    try:
        _wait_for_server(url, server_process)
        window = webview.create_window(
            title=title,
            url=url,
            width=width,
            height=height,
            min_size=(1100, 720),
        )
        webview.start()
        return 0 if window is not None else 1
    finally:
        _stop_process(server_process)


def gui_main() -> None:
    parser = argparse.ArgumentParser(prog="mplgallery-desktop")
    parser.add_argument("project_root", nargs="?", default=".", help="Project directory to open.")
    parser.add_argument("--port", type=int, default=None, help="Preferred local port.")
    parser.add_argument("--choose-root", action="store_true", help="Start with the root chooser emphasized.")
    parser.add_argument(
        "--include-artifacts",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Show PNG/SVG artifacts alongside draftable CSV files.",
    )
    parser.add_argument("--width", type=int, default=1600, help="Initial window width.")
    parser.add_argument("--height", type=int, default=1000, help="Initial window height.")
    args = parser.parse_args()
    raise SystemExit(
        launch_desktop_app(
            Path(args.project_root),
            port=args.port,
            choose_root=args.choose_root,
            include_artifacts=args.include_artifacts,
            width=args.width,
            height=args.height,
        )
    )


def _start_streamlit_server(
    project_root: Path,
    *,
    port: int,
    choose_root: bool,
    include_artifacts: bool,
) -> subprocess.Popen[str]:
    app_path = Path(__file__).parent / "ui" / "app.py"
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.headless=true",
        "--server.address=127.0.0.1",
        f"--server.port={port}",
        "--browser.gatherUsageStats=false",
    ]
    command.extend(["--", "--project-root", str(project_root)])
    if choose_root:
        command.append("--choose-root")
    if include_artifacts:
        command.append("--include-artifacts")
    env = os.environ.copy()
    env.setdefault("BROWSER", "none")
    return subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        bufsize=1,
        env=env,
    )


def _wait_for_server(
    url: str,
    process: subprocess.Popen[str],
    *,
    timeout_seconds: float = 30.0,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = _read_output(process)
            raise RuntimeError(f"Desktop backend exited before launch.\n{output}")
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if response.status < 500:
                    return
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.2)
    output = _read_output(process)
    raise RuntimeError(f"Timed out waiting for desktop backend at {url}.\n{output}")


def _read_output(process: subprocess.Popen[str]) -> str:
    if process.stdout is None:
        return ""
    return process.stdout.read().strip()


def _stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])
