"""Small JSON-over-HTTP helpers shared by the directory, the relays and the client.

Standard library only -- see SD-005.  These helpers exist so the three servers
in this repository answer in a consistent shape; they carry no protocol
knowledge of their own.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler
from typing import Any

# A request body larger than this is refused before it is read into memory.
# Nothing this system sends legitimately approaches it; the cap is here so a
# malformed or hostile Content-Length fails fast instead of exhausting a relay.
MAX_BODY_BYTES = 8 * 1024 * 1024


class HttpError(Exception):
    """A JSON-over-HTTP call failed.

    ``status`` is the HTTP status when the peer answered at all, and ``None``
    when the peer could not be reached.  ``body`` is the decoded JSON error
    body when the peer supplied one.
    """

    def __init__(self, message: str, status: int | None = None, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


def post_json(url: str, payload: Any, timeout: float) -> Any:
    """POST a JSON document and return the decoded JSON response."""
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    return _send(request, timeout)


def get_json(url: str, timeout: float) -> Any:
    """GET a JSON document and return the decoded response."""
    request = urllib.request.Request(
        url, method="GET", headers={"Accept": "application/json"}
    )
    return _send(request, timeout)


def _send(request: urllib.request.Request, timeout: float) -> Any:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_BODY_BYTES)
    except urllib.error.HTTPError as exc:
        raw = exc.read(MAX_BODY_BYTES)
        try:
            body = json.loads(raw.decode("utf-8"))
        except Exception:  # noqa: BLE001 - a non-JSON error body is still an error
            body = None
        raise HttpError(
            f"peer returned HTTP {exc.code}", status=exc.code, body=body
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise HttpError(f"peer unreachable: {exc}") from exc

    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise HttpError("peer returned a body that is not JSON") from exc


class JsonRequestHandler(BaseHTTPRequestHandler):
    """Base handler that speaks JSON and keeps the stdlib's noise out of the logs.

    Subclasses implement ``do_GET`` / ``do_POST`` and use ``send_json`` and
    ``read_json_body``.
    """

    protocol_version = "HTTP/1.1"
    server_version = "sandbox-node"
    sys_version = ""

    # The default BaseHTTPRequestHandler implementation writes a line per
    # request straight to stderr, including the full request path.  The
    # directory must not log path composition (DIRECTORY_SPEC.md section 4) and
    # relays must not log more than their own hop (RELAY_PROTOCOL.md section
    # 8), so the automatic line is suppressed and each server logs what it is
    # permitted to log, deliberately.
    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
        return

    def send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self) -> Any:
        """Read and decode the request body, or return ``None`` if unusable."""
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None
        if length <= 0 or length > MAX_BODY_BYTES:
            return None
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:  # noqa: BLE001
            return None
