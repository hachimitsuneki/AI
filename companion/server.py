from __future__ import annotations

import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from typing import Any

from .config import RuntimeConfig, load_config
from .context_builder import ContextBuilder
from .database import Database
from .gateway import OllamaClient
from .orchestrator import ConversationRuntime
from .repositories import RuntimeRepository
from .retrieval import Retriever

MAX_BODY_BYTES = 128_000
STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_runtime(config: RuntimeConfig | None = None) -> tuple[RuntimeConfig, Database, RuntimeRepository, OllamaClient, ConversationRuntime]:
    config = config or load_config()
    db = Database(config.database_path)
    db.initialize(config)
    repository = RuntimeRepository(db)
    provider = OllamaClient(config)
    retriever = Retriever(db, repository, provider, config)
    context_builder = ContextBuilder(repository, config)
    runtime = ConversationRuntime(db, repository, provider, retriever, context_builder, config)
    return config, db, repository, provider, runtime


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
        config: RuntimeConfig,
        repository: RuntimeRepository,
        provider: OllamaClient,
        runtime: ConversationRuntime,
    ):
        super().__init__(address, LocalRequestHandler)
        self.config = config
        self.repository = repository
        self.provider = provider
        self.runtime = runtime


class LocalRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "TextV01Local/0.1"
    sys_version = ""

    @property
    def app(self) -> LocalServer:
        return self.server  # type: ignore[return-value]

    def log_message(self, format: str, *args: Any) -> None:
        # Keep the local development log useful without writing conversation content.
        super().log_message(format, *args)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json_body(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc
        if length < 1 or length > MAX_BODY_BYTES:
            raise ValueError("request body is empty or too large")
        if self.headers.get_content_type() != "application/json":
            raise ValueError("Content-Type must be application/json")
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("request body must be valid UTF-8 JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    def _check_origin(self) -> bool:
        origin = self.headers.get("Origin")
        if not origin:
            return True
        parsed = urlsplit(origin)
        host = self.headers.get("Host", "")
        return parsed.scheme in {"http", "https"} and parsed.netloc.lower() == host.lower()

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        if parsed.path == "/":
            self._send_static("index.html")
            return
        if parsed.path in {"/app.js", "/styles.css"}:
            self._send_static(parsed.path.lstrip("/"))
            return
        if parsed.path == "/api/bootstrap":
            try:
                identity = self.app.repository.default_scope()
                health = self.app.provider.health()
                self._send_json(
                    200,
                    {
                        "identity": {
                            "id": identity["ai_identity_id"],
                            "name": identity["name"],
                            "role": identity["role"],
                        },
                        "conversation_id": identity["conversation_id"],
                        "history": self.app.repository.history(),
                        "runtime_profile": {
                            "profile_id": self.app.config.profile_id,
                            "main_model": self.app.config.main_model,
                            "embedding_model": self.app.config.embedding_model,
                            "context_budget_tokens": self.app.config.context_budget_tokens,
                        },
                        "provider": health,
                    },
                )
            except Exception as exc:
                self._send_json(500, {"error": "bootstrap_failed", "message": str(exc)})
            return
        if parsed.path == "/api/health":
            provider = self.app.provider.health()
            self._send_json(
                200 if provider["main_model_available"] else 503,
                {
                    "status": "ok" if provider["main_model_available"] else "model_unavailable",
                    "database": "ok",
                    "provider": provider,
                },
            )
            return
        if parsed.path.startswith("/api/turns/") and parsed.path.endswith("/trace"):
            turn_id = parsed.path[len("/api/turns/") : -len("/trace")].strip("/")
            try:
                self._send_json(200, self.app.runtime.trace(turn_id))
            except KeyError as exc:
                self._send_json(404, {"error": "turn_not_found", "message": str(exc)})
            except Exception as exc:
                self._send_json(500, {"error": "trace_failed", "message": str(exc)})
            return
        self._send_json(404, {"error": "not_found"})

    def _send_static(self, name: str) -> None:
        target = (STATIC_DIR / name).resolve()
        if STATIC_DIR.resolve() not in target.parents or not target.is_file():
            self._send_json(404, {"error": "not_found"})
            return
        body = target.read_bytes()
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if content_type in ("text/html", "text/javascript", "text/css"):
            content_type += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if not self._check_origin():
            self._send_json(403, {"error": "origin_rejected"})
            return
        try:
            if self.path == "/api/turns":
                self._post_turn()
                return
            if self.path.startswith("/api/turns/"):
                rest = self.path[len("/api/turns/") :]
                parts = rest.split("/")
                if len(parts) == 2 and parts[1] == "delivery":
                    self._post_delivery(parts[0])
                    return
                if len(parts) == 2 and parts[1] == "finalize":
                    self._post_finalize(parts[0])
                    return
                if len(parts) == 2 and parts[1] == "cancel":
                    self._post_cancel(parts[0])
                    return
        except ValueError as exc:
            self._send_json(400, {"error": "invalid_request", "message": str(exc)})
            return
        except KeyError as exc:
            self._send_json(404, {"error": "turn_not_found", "message": str(exc)})
            return
        except RuntimeError as exc:
            self._send_json(409, {"error": "request_conflict", "message": str(exc)})
            return
        self._send_json(404, {"error": "not_found"})

    def _post_turn(self) -> None:
        payload = self._json_body()
        text = payload.get("text")
        if not isinstance(text, str):
            raise ValueError("text must be a string")
        session = self.app.runtime.begin(text)
        stream = self.app.runtime.stream(session)
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Cache-Control", "no-store, no-transform")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        try:
            for event in stream:
                encoded = json.dumps(event, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
                self.wfile.write(f"{len(encoded):X}\r\n".encode("ascii"))
                self.wfile.write(encoded)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            self.app.runtime.disconnect(session)
            try:
                stream.close()
            except Exception:
                pass

    def _post_delivery(self, turn_id: str) -> None:
        payload = self._json_body()
        result = self.app.runtime.acknowledge_delivery(
            turn_id, payload.get("offset"), payload.get("text")
        )
        self._send_json(200, result)

    def _post_finalize(self, turn_id: str) -> None:
        self._json_body() if self.headers.get("Content-Length") else None
        result = self.app.runtime.finalize_from_client(turn_id)
        self._send_json(200, result)

    def _post_cancel(self, turn_id: str) -> None:
        payload = self._json_body() if self.headers.get("Content-Length") else {}
        reason = payload.get("reason", "user_cancelled")
        if not isinstance(reason, str):
            raise ValueError("reason must be a string")
        self._send_json(200, self.app.runtime.cancel(turn_id, reason[:120]))


def serve() -> None:
    config, _db, repository, provider, runtime = create_runtime()
    server = LocalServer((config.host, config.port), config, repository, provider, runtime)
    print(f"Text v0.1 local runtime: http://{config.host}:{config.port}")
    print(f"Runtime profile: {config.profile_id}; Main model: {config.main_model}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()


def start_background_server(server: LocalServer) -> threading.Thread:
    thread = threading.Thread(target=server.serve_forever, name="text-v01-http", daemon=True)
    thread.start()
    return thread
