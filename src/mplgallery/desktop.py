from __future__ import annotations

import argparse
import json
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
    _trace("gui_main:start")
    parser = argparse.ArgumentParser(prog="mplgallery-desktop")
    parser.add_argument("--internal-streamlit", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--self-test-out", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--smoke-browser-launch", action="store_true", help=argparse.SUPPRESS)
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
    if args.self_test_out is None:
        env_self_test_out = os.getenv("MPLGALLERY_DESKTOP_SELF_TEST_OUT")
        if env_self_test_out:
            args.self_test_out = Path(env_self_test_out)
    if not args.smoke_browser_launch and os.getenv("MPLGALLERY_DESKTOP_SMOKE") == "1":
        args.smoke_browser_launch = True
    _trace(
        "gui_main:parsed",
        {
            "internal_streamlit": args.internal_streamlit,
            "self_test_out": str(args.self_test_out) if args.self_test_out else None,
            "smoke_browser_launch": args.smoke_browser_launch,
            "project_root": args.project_root,
        },
    )
    if args.internal_streamlit:
        _trace("gui_main:internal_streamlit")
        raise SystemExit(
            _run_internal_streamlit(
                Path(args.project_root),
                port=args.port or 8501,
                choose_root=args.choose_root,
                include_artifacts=args.include_artifacts,
            )
        )
    if args.smoke_browser_launch:
        _trace("gui_main:smoke")
        raise SystemExit(
            _smoke_browser_launch(
                Path(args.project_root),
                port=args.port,
                choose_root=args.choose_root,
                include_artifacts=args.include_artifacts,
                output_path=args.self_test_out,
            )
        )
    if args.self_test_out is not None:
        _trace("gui_main:self_test")
        _write_self_test(args.self_test_out)
        raise SystemExit(0)
    _trace("gui_main:launch")
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
    _trace("start_streamlit_server", {"project_root": str(project_root), "port": port, "frozen": bool(getattr(sys, "frozen", False))})
    command = _streamlit_command(
        project_root=project_root,
        port=port,
        choose_root=choose_root,
        include_artifacts=include_artifacts,
    )
    env = _streamlit_env()
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


def _streamlit_command(
    *,
    project_root: Path,
    port: int,
    choose_root: bool,
    include_artifacts: bool,
) -> list[str]:
    if getattr(sys, "frozen", False):
        command = [sys.executable, "--internal-streamlit", str(project_root)]
        command.append(f"--port={port}")
        if choose_root:
            command.append("--choose-root")
        if include_artifacts:
            command.append("--include-artifacts")
        return command

    app_path = _streamlit_app_path()
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
        "--",
        "--project-root",
        str(project_root),
    ]
    if choose_root:
        command.append("--choose-root")
    if include_artifacts:
        command.append("--include-artifacts")
    return command


def _wait_for_server(
    url: str,
    process: subprocess.Popen[str],
    *,
    timeout_seconds: float = 120.0,
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
    _stop_process(process)
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


def _streamlit_app_path() -> Path:
    if getattr(sys, "frozen", False):
        bundle_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        return bundle_root / "mplgallery" / "ui" / "app.py"
    return Path(__file__).parent / "ui" / "app.py"


def _run_internal_streamlit(
    project_root: Path,
    *,
    port: int,
    choose_root: bool,
    include_artifacts: bool,
) -> int:
    from streamlit.web import cli as stcli

    app_path = _streamlit_app_path()
    _trace("run_internal_streamlit", {"app_path": str(app_path), "port": port})
    argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.headless=true",
        "--server.address=127.0.0.1",
        f"--server.port={port}",
        "--browser.gatherUsageStats=false",
        "--",
        "--project-root",
        str(project_root.expanduser().resolve()),
    ]
    if choose_root:
        argv.append("--choose-root")
    if include_artifacts:
        argv.append("--include-artifacts")
    previous_argv = sys.argv[:]
    streamlit_env = _streamlit_env()
    previous_env = {key: os.environ.get(key) for key in streamlit_env}
    try:
        os.environ.update(streamlit_env)
        sys.argv = argv
        try:
            result = stcli.main()
        except SystemExit as exc:
            return int(exc.code or 0)
        return int(result or 0)
    finally:
        sys.argv = previous_argv
        for key, value in previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _streamlit_env() -> dict[str, str]:
    env = os.environ.copy()
    env["BROWSER"] = os.environ.get("BROWSER", "none")
    # Frozen Streamlit runs from a PyInstaller temp bundle instead of site-packages,
    # which makes Streamlit auto-enable developmentMode unless we override it.
    env["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = os.environ.get(
        "STREAMLIT_GLOBAL_DEVELOPMENT_MODE", "false"
    )
    return env


def _write_self_test(output_path: Path) -> None:
    payload = {
        "ok": True,
        "frozen": bool(getattr(sys, "frozen", False)),
        "executable": sys.executable,
        "app_path": str(_streamlit_app_path()),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _trace("write_self_test", payload)


def _smoke_browser_launch(
    project_root: Path,
    *,
    port: int | None,
    choose_root: bool,
    include_artifacts: bool,
    output_path: Path | None,
) -> int:
    resolved_root = project_root.expanduser().resolve()
    server_port = port or _find_free_port()
    _trace("smoke_browser_launch:start", {"project_root": str(resolved_root), "port": server_port})
    server_process = _start_streamlit_server(
        resolved_root,
        port=server_port,
        choose_root=choose_root,
        include_artifacts=include_artifacts,
    )
    url = f"http://127.0.0.1:{server_port}"
    try:
        _wait_for_server(url, server_process)
        payload = {
            "ok": True,
            "frozen": bool(getattr(sys, "frozen", False)),
            "url": url,
            "project_root": str(resolved_root),
            "app_path": str(_streamlit_app_path()),
        }
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        _trace("smoke_browser_launch:ok", payload)
        return 0
    finally:
        _stop_process(server_process)


def _trace(event: str, payload: dict[str, object] | None = None) -> None:
    trace_path = os.getenv("MPLGALLERY_DESKTOP_TRACE")
    if not trace_path:
        return
    record = {"event": event, "payload": payload or {}}
    path = Path(trace_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


if __name__ == "__main__":
    gui_main()
