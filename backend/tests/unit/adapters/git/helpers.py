"""Repos git reales y temporales para probar adaptadores y hooks."""

from __future__ import annotations

import json
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )
    return result.stdout


def init_repo(path: Path, *, origin: str | None = None) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)
    if origin is not None:
        git(path, "remote", "add", "origin", origin)
    return path.resolve()


def commit_file(
    repo: Path, name: str = "a.txt", content: str = "hola\n", message: str = "feat: algo"
) -> str:
    """Hace un commit (ejecutando sus hooks) y devuelve su sha."""
    (repo / name).write_text(content, encoding="utf-8")
    git(repo, "add", name)
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD").strip()


class Recorder:
    """Servidor HTTP local que guarda lo que recibe (hace de API de Duelo en los tests)."""

    def __init__(self, *, delay: float = 0.0, status: int = 202) -> None:
        self.requests: list[tuple[str, dict[str, str], dict[str, object]]] = []
        recorder = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                time.sleep(delay)
                recorder.requests.append((self.path, dict(self.headers), body))
                self.send_response(status)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, *args: object) -> None:
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self._server.server_address[1]}"
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()

    def wait_for(self, count: int, seconds: float = 15.0) -> list[dict[str, object]]:
        deadline = time.monotonic() + seconds
        while len(self.requests) < count and time.monotonic() < deadline:
            time.sleep(0.05)
        assert len(self.requests) >= count, f"llegaron {len(self.requests)} de {count} peticiones"
        return [body for _path, _headers, body in self.requests]
