"""In-memory relay registry and path selection.

Implements ``AgentsDocs/DIRECTORY_SPEC.md`` in full.  This replaces a directory
authority and consensus system with the smallest thing that provides dynamic
path selection: one process, one dict, no voting, no distributed trust and no
persistence.

What this service must never do (DIRECTORY_SPEC.md section 4):

  * store or forward traffic -- it is consulted before a request, never during
  * know which paths were actually used
  * log the composition of a returned path
  * persist anything across a restart
"""

from __future__ import annotations

import argparse
import logging
import os
import random
import secrets
import threading
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from common.http_util import JsonRequestHandler
from common.onion_crypto import EnvelopeError, load_public_key

log = logging.getLogger("directory")

# RELAY_PROTOCOL.md section 4: default 3, and the pool of 5-7 relays makes
# 2-5 the usable range.
DEFAULT_HOPS = 3
MIN_HOPS = 2
MAX_HOPS = 5

STATUS_UP = "up"
STATUS_DOWN = "down"


class RelayRegistry:
    """The registry itself.  In-memory only, lost on restart, rebuilt as relays
    re-register (DIRECTORY_SPEC.md section 2)."""

    def __init__(self, rng: random.Random | None = None):
        self._relays: dict[str, dict] = {}
        self._lock = threading.Lock()
        # Injectable so tests can assert on selection behaviour deterministically.
        # Production uses SystemRandom: path selection must not be predictable.
        self._rng = rng or random.SystemRandom()

    def register(self, payload: dict) -> dict:
        """Record a relay, or raise ValueError describing why it was rejected.

        Re-registration under an existing ``relay_id`` overwrites the entry and
        sets it back up, which is what makes a container restart safe
        (DIRECTORY_SPEC.md section 3).
        """
        for field in ("relay_id", "host", "port", "public_key"):
            if field not in payload:
                raise ValueError(f"missing required field: {field}")

        relay_id = payload["relay_id"]
        host = payload["host"]
        public_key = payload["public_key"]

        if not isinstance(relay_id, str) or not relay_id:
            raise ValueError("relay_id must be a non-empty string")
        if not isinstance(host, str) or not host:
            raise ValueError("host must be a non-empty string")
        try:
            port = int(payload["port"])
        except (TypeError, ValueError):
            raise ValueError("port must be an integer") from None
        if not 1 <= port <= 65535:
            raise ValueError("port is out of range")
        if not isinstance(public_key, str):
            raise ValueError("public_key must be a string")

        # DIRECTORY_SPEC.md section 2: a registration carrying a private key is
        # a bug in the relay, not something to accept quietly.  The rejection
        # is logged; the key material itself never is.
        if "PRIVATE KEY" in public_key:
            log.error(
                "rejected registration relay_id=%s: payload contained a private key",
                relay_id,
            )
            raise ValueError("public_key contains a private key")

        try:
            load_public_key(public_key)
        except EnvelopeError as exc:
            raise ValueError(f"public_key is not a valid PEM public key: {exc}") from exc

        entry = {
            "relay_id": relay_id,
            "host": host,
            "port": port,
            "public_key": public_key,
            "status": STATUS_UP,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            self._relays[relay_id] = entry
        # The public key is deliberately absent from this line: it is bulky and
        # logging key material of any kind is a habit worth not forming.
        log.info("registered relay_id=%s status=up", relay_id)
        return entry

    def set_status(self, relay_id: str, status: str) -> bool:
        if status not in (STATUS_UP, STATUS_DOWN):
            raise ValueError("status must be 'up' or 'down'")
        with self._lock:
            entry = self._relays.get(relay_id)
            if entry is None:
                return False
            entry["status"] = status
        log.info("status change relay_id=%s status=%s", relay_id, status)
        return True

    def all_relays(self) -> list[dict]:
        with self._lock:
            return [dict(entry) for entry in self._relays.values()]

    def up_relays(self) -> list[dict]:
        with self._lock:
            return [
                dict(entry)
                for entry in self._relays.values()
                if entry["status"] == STATUS_UP
            ]

    def select_path(self, hops: int) -> dict:
        """Select ``hops`` distinct up relays, uniform random, without replacement.

        No bandwidth, uptime, latency, geographic or reputation weighting, and
        no guard persistence -- every call selects fresh (DIRECTORY_SPEC.md
        section 3, RELAY_PROTOCOL.md section 4).
        """
        if not MIN_HOPS <= hops <= MAX_HOPS:
            raise ValueError(
                f"hops must be between {MIN_HOPS} and {MAX_HOPS}, got {hops}"
            )

        available = self.up_relays()
        if len(available) < hops:
            raise LookupError(
                f"only {len(available)} relays are up, {hops} required"
            )

        chosen = self._rng.sample(available, hops)
        path_id = "p_" + secrets.token_hex(3)

        # DIRECTORY_SPEC.md section 4: log the path_id and the hop count, never
        # the composition.  Logging every path would defeat the isolation
        # property this system exists to demonstrate.
        log.info("path issued path_id=%s hops=%d", path_id, hops)

        return {
            "path_id": path_id,
            "hops": hops,
            "relays": [
                {
                    "relay_id": r["relay_id"],
                    "host": r["host"],
                    "port": r["port"],
                    "public_key": r["public_key"],
                }
                for r in chosen
            ],
        }


class DirectoryHandler(JsonRequestHandler):
    """HTTP surface: the four endpoints of DIRECTORY_SPEC.md section 3."""

    registry: RelayRegistry  # set on the server class at construction

    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        route = urlparse(self.path)

        if route.path == "/relays":
            # Public keys included, private keys never -- the directory holds none.
            self.send_json(
                200,
                {
                    "count": len(self.registry.all_relays()),
                    "relays": self.registry.all_relays(),
                },
            )
            return

        if route.path == "/path":
            params = parse_qs(route.query)
            raw_hops = params.get("hops", [str(DEFAULT_HOPS)])[0]
            try:
                hops = int(raw_hops)
            except ValueError:
                self.send_json(400, {"error": f"hops must be an integer, got {raw_hops!r}"})
                return
            try:
                self.send_json(200, self.registry.select_path(hops))
            except ValueError as exc:
                self.send_json(400, {"error": str(exc)})
            except LookupError as exc:
                # 503 naming the shortfall, per DIRECTORY_SPEC.md section 3.
                self.send_json(503, {"error": str(exc)})
            return

        if route.path == "/health":
            self.send_json(200, {"service": "directory", "status": "up"})
            return

        self.send_json(404, {"error": "no such endpoint"})

    def do_POST(self) -> None:  # noqa: N802 - stdlib naming
        route = urlparse(self.path)
        payload = self.read_json_body()

        if payload is None or not isinstance(payload, dict):
            self.send_json(400, {"error": "body must be a JSON object"})
            return

        if route.path == "/register":
            try:
                entry = self.registry.register(payload)
            except ValueError as exc:
                self.send_json(400, {"error": str(exc)})
                return
            self.send_json(200, {"registered": True, "relay_id": entry["relay_id"]})
            return

        # POST /relays/{relay_id}/status
        parts = [p for p in route.path.split("/") if p]
        if len(parts) == 3 and parts[0] == "relays" and parts[2] == "status":
            relay_id = parts[1]
            status = payload.get("status")
            try:
                found = self.registry.set_status(relay_id, status)
            except ValueError as exc:
                self.send_json(400, {"error": str(exc)})
                return
            if not found:
                self.send_json(404, {"error": f"unknown relay_id: {relay_id}"})
                return
            self.send_json(200, {"relay_id": relay_id, "status": status})
            return

        self.send_json(404, {"error": "no such endpoint"})


def build_server(host: str, port: int, registry: RelayRegistry | None = None) -> ThreadingHTTPServer:
    """Construct the directory server without starting it.

    Split out so tests can bind an ephemeral port and drive the same code the
    container runs.
    """
    registry = registry or RelayRegistry()
    handler = type("BoundDirectoryHandler", (DirectoryHandler,), {"registry": registry})
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    server.registry = registry  # type: ignore[attr-defined]
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Sandbox relay directory service")
    parser.add_argument("--host", default=os.environ.get("DIRECTORY_BIND", "0.0.0.0"))
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("DIRECTORY_PORT", "8000"))
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="[directory] %(message)s"
    )

    server = build_server(args.host, args.port)
    log.info("listening on %s:%d", args.host, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("shutting down")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
