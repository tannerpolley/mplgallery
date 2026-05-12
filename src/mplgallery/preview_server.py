from __future__ import annotations

import argparse
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class IdlePreviewServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], handler_cls, idle_seconds: float) -> None:
        super().__init__(server_address, handler_cls)
        self.idle_seconds = idle_seconds
        self.last_request_at = time.monotonic()
        self.timeout = 0.5

    def finish_request(self, request, client_address) -> None:  # type: ignore[override]
        self.last_request_at = time.monotonic()
        super().finish_request(request, client_address)

    def serve_until_idle(self) -> None:
        while time.monotonic() - self.last_request_at < self.idle_seconds:
            self.handle_request()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m mplgallery.preview_server")
    parser.add_argument("--directory", type=Path, required=True, help="Directory to serve.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument("--port", type=int, required=True, help="Port to bind.")
    parser.add_argument("--idle-seconds", type=float, default=600.0, help="Stop after this much idle time.")
    args = parser.parse_args()

    handler = partial(SimpleHTTPRequestHandler, directory=str(args.directory))
    with IdlePreviewServer((args.host, args.port), handler, idle_seconds=args.idle_seconds) as server:
        server.serve_until_idle()


if __name__ == "__main__":
    main()
