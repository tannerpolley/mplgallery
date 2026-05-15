from __future__ import annotations

import argparse
import json
import os
import socket
import time
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from mplgallery.core.user_settings import (
    clear_recent_roots,
    forget_recent_root,
    load_user_settings,
    save_user_settings,
    update_project_memory_setting,
)
from mplgallery.desktop import build_browser_preview_payload_for_root
from mplgallery.ui.root_state import change_active_root, reset_active_root

API_EVENT_PATH = "/__mplgallery__/event"


class IdlePreviewServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(
        self,
        server_address: tuple[str, int],
        handler_cls,
        *,
        idle_seconds: float,
        launch_root: Path,
        include_artifacts: bool,
        image_library: bool,
    ) -> None:
        super().__init__(server_address, handler_cls)
        self.idle_seconds = idle_seconds
        self.last_request_at = time.monotonic()
        self.timeout = 0.5
        self.launch_root = launch_root
        self.active_root = launch_root
        self.include_artifacts = include_artifacts
        self.image_library = image_library

    def server_bind(self) -> None:
        exclusive_addr_use = getattr(socket, "SO_EXCLUSIVEADDRUSE", None)
        if exclusive_addr_use is not None:
            try:
                self.socket.setsockopt(socket.SOL_SOCKET, exclusive_addr_use, 1)
            except OSError:
                pass
        super().server_bind()

    def finish_request(self, request, client_address) -> None:  # type: ignore[override]
        self.last_request_at = time.monotonic()
        super().finish_request(request, client_address)

    def serve_until_idle(self) -> None:
        while time.monotonic() - self.last_request_at < self.idle_seconds:
            self.handle_request()


class PreviewRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/__mplgallery__/asset":
            self._serve_asset(parsed.query)
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if self.path != API_EVENT_PATH:
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown API endpoint")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._json_response({"error": "invalid_json"}, status=HTTPStatus.BAD_REQUEST)
            return

        response_payload = self._handle_event(payload)
        self._json_response(response_payload)

    def _serve_asset(self, query: str) -> None:
        params = parse_qs(query)
        root_value = params.get("root", [""])[0]
        path_value = params.get("path", [""])[0]
        if not root_value or not path_value:
            self.send_error(HTTPStatus.BAD_REQUEST, "Missing asset path")
            return
        root = Path(unquote(root_value)).expanduser().resolve(strict=False)
        relative = Path(unquote(path_value))
        if relative.is_absolute():
            self.send_error(HTTPStatus.BAD_REQUEST, "Asset path must be relative")
            return
        target = (root / relative).resolve(strict=False)
        try:
            if os.path.commonpath([str(root), str(target)]) != str(root):
                raise ValueError
        except ValueError:
            self.send_error(HTTPStatus.FORBIDDEN, "Asset path is outside project root")
            return
        if not target.is_file() or target.suffix.lower() not in {".png", ".svg"}:
            self.send_error(HTTPStatus.NOT_FOUND, "Asset not found")
            return
        body = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "image/svg+xml" if target.suffix.lower() == ".svg" else "image/png")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "private, max-age=60")
        self.end_headers()
        self.wfile.write(body)

    def _handle_event(self, payload: dict[str, object]) -> dict[str, object]:
        event_type = str(payload.get("type") or "")
        current_root = _coerce_path(payload.get("currentRoot"))
        launch_root = self.server.launch_root  # type: ignore[attr-defined]
        remembered_root = self.server.active_root  # type: ignore[attr-defined]
        include_artifacts = self.server.include_artifacts  # type: ignore[attr-defined]
        image_library = self.server.image_library  # type: ignore[attr-defined]
        settings = load_user_settings()
        active_root = remembered_root or current_root or launch_root
        root_error: str | None = None

        if event_type == "refresh_index":
            active_root = _coerce_path(payload.get("rootPath")) or remembered_root or current_root or launch_root
        elif event_type == "change_project_root":
            result = change_active_root(str(payload.get("rootPath") or ""), settings)
            root_error = result.error
            settings = result.settings
            if result.active_root is not None:
                active_root = result.active_root
                save_user_settings(settings)
        elif event_type == "browse_project_root":
            root_error = "Use the Project path field and Open root in browser preview."
        elif event_type == "reset_project_root":
            result = reset_active_root(launch_root, settings)
            root_error = result.error
            settings = result.settings
            if result.active_root is not None:
                active_root = result.active_root
                save_user_settings(settings)
        elif event_type == "forget_recent_root":
            root_path = _coerce_path(payload.get("rootPath"))
            if root_path is not None:
                settings = forget_recent_root(settings, root_path)
                save_user_settings(settings)
                if active_root is not None and _same_root(active_root, root_path):
                    active_root = None
        elif event_type == "clear_recent_roots":
            settings = clear_recent_roots(settings)
            save_user_settings(settings)
        elif event_type == "set_user_setting":
            setting_key = str(payload.get("settingKey") or "")
            setting_value = bool(payload.get("settingValue"))
            settings = update_project_memory_setting(settings, setting_key, setting_value)
            save_user_settings(settings)
        else:
            return {"error": f"unsupported_event:{event_type}"}

        self.server.active_root = active_root or launch_root  # type: ignore[attr-defined]

        return build_browser_preview_payload_for_root(
            active_root,
            launch_root=launch_root,
            include_artifacts=include_artifacts,
            image_library=image_library,
            settings=settings,
            root_error=root_error,
            show_root_chooser=False,
        )

    def _json_response(self, payload: dict[str, object], *, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def _coerce_path(value: object) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return Path(value).expanduser().resolve(strict=False)


def _same_root(left: Path, right: Path) -> bool:
    return str(left.expanduser().resolve(strict=False)).lower() == str(right.expanduser().resolve(strict=False)).lower()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m mplgallery.preview_server")
    parser.add_argument("--directory", type=Path, required=True, help="Directory to serve.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument("--port", type=int, required=True, help="Port to bind.")
    parser.add_argument("--project-root", type=Path, required=True, help="Launch project root.")
    parser.add_argument("--include-artifacts", action="store_true", help="Serve PNG/SVG artifact records.")
    parser.add_argument("--image-library", action="store_true", help="Serve in loose image library mode.")
    parser.add_argument("--idle-seconds", type=float, default=600.0, help="Stop after this much idle time.")
    args = parser.parse_args()

    handler = partial(PreviewRequestHandler, directory=str(args.directory))
    with IdlePreviewServer(
        (args.host, args.port),
        handler,
        idle_seconds=args.idle_seconds,
        launch_root=args.project_root.expanduser().resolve(strict=False),
        include_artifacts=args.include_artifacts,
        image_library=args.image_library,
    ) as server:
        server.serve_until_idle()


if __name__ == "__main__":
    main()
