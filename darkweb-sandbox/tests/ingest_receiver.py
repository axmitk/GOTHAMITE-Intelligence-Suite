"""A TEST DOUBLE for the ingest seam.  Not GOTHAMITE, and not a stand-in for it.

This exists so Phase-5 tests can observe what the **scraper** does when the
other side answers in each of the ways `API_CONTRACT.md` section 4 defines.  It
records requests and replies with whatever the test asked for.

It is deliberately not an implementation of the contract's server side:

* it stores nothing beyond a list in memory for the duration of one test,
* it does not deduplicate, correlate, score, or build any graph,
* it does not validate payloads -- `scraper.contract` does that, locally,
* it lives in `tests/` and nothing under `scraper/` imports it.

If GOTHAMITE is ever built, it is built in its own repository against
`API_CONTRACT.md`, and nothing here is reusable for that purpose.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

INGEST_PATH = "/api/v1/ingest"

# A responder sees (payload, ordinal) and returns (http_status, body).
Responder = Callable[[dict, int], "tuple[int, Any]"]


def accept_all(payload: dict, ordinal: int) -> tuple[int, Any]:
    """The happy path: 202 Accepted, as section 4 defines it."""
    return 202, {
        "accepted": True,
        "artifact_id": f"test-{ordinal:04d}",
        "identifiers_stored": len(payload.get("identifiers", [])),
    }


def duplicate_after_first(seen: set[str]) -> Responder:
    """202 the first time a (source_id, content_hash) arrives, 200 duplicate after.

    Mirrors section 4's rule closely enough to exercise the scraper's handling
    of a re-scrape.  It is not a deduplication implementation and is not
    persisted anywhere.
    """

    def responder(payload: dict, ordinal: int) -> tuple[int, Any]:
        key = f"{payload.get('source_id')}|{payload.get('content_hash')}"
        if key in seen:
            return 200, {
                "accepted": False,
                "reason": "duplicate_content_hash",
                "artifact_id": f"test-{ordinal:04d}",
            }
        seen.add(key)
        return accept_all(payload, ordinal)

    return responder


def always(status: int, body: Any) -> Responder:
    def responder(payload: dict, ordinal: int) -> tuple[int, Any]:
        return status, body

    return responder


def fail_then_accept(failures: int, status: int = 503) -> Responder:
    """Answer `status` for the first `failures` attempts, then accept."""
    state = {"seen": 0}

    def responder(payload: dict, ordinal: int) -> tuple[int, Any]:
        state["seen"] += 1
        if state["seen"] <= failures:
            return status, {"error": "unavailable"}
        return accept_all(payload, ordinal)

    return responder


class IngestReceiver:
    """A loopback HTTP server that records ingest requests."""

    def __init__(self, responder: Responder | None = None) -> None:
        self.responder: Responder = responder or accept_all
        self.received: list[dict] = []
        self.attempts = 0
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        assert self._server is not None, "receiver is not running"
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}{INGEST_PATH}"

    def start(self) -> IngestReceiver:
        receiver = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length else b"{}"
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except Exception:  # noqa: BLE001
                    payload = {}
                receiver.attempts += 1
                if self.path != INGEST_PATH:
                    self._reply(404, {"error": "no such endpoint"})
                    return
                status, body = receiver.responder(payload, receiver.attempts)
                if status < 400:
                    receiver.received.append(payload)
                self._reply(status, body)

            def _reply(self, status: int, body: object) -> None:
                encoded = json.dumps(body).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, *args: object) -> None:
                pass  # keep the test output readable

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def __enter__(self) -> IngestReceiver:
        return self.start()

    def __exit__(self, *exc: object) -> None:
        self.stop()
