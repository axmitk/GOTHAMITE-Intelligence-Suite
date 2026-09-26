"""A single relay in the simulated onion-routed network.

Implements ``AgentsDocs/RELAY_PROTOCOL.md`` sections 3, 6, 7, 8 and 9.

Every relay runs identical logic.  A relay does not know whether it is the
entry, a middle hop or the exit until it decrypts its own layer, and it never
learns more than that layer contains:

    entry   sees the client, sees the next hop, sees neither the destination
            nor the request body
    middle  sees its predecessor, sees the next hop, sees neither the
            destination nor the request body
    exit    sees its predecessor, sees the destination and the request body

That table (section 6) is the property this whole system exists to
demonstrate.  Any change here that widens what a hop can see is a bug, however
convenient it is.
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import secrets
import socket
import time
from http.server import ThreadingHTTPServer

from common.http_util import HttpError, JsonRequestHandler, post_json
from common.onion_crypto import (
    DESTINATION,
    EnvelopeError,
    generate_relay_keypair,
    layer_payload,
    open_layer,
    seal_response,
)

log = logging.getLogger("relay")

# Bound on the raw response an exit relay will read back from a destination.
# The Phase-1 endpoint and the Phase-4 mock sites are all far below this; the
# cap exists so a misbehaving destination cannot exhaust the relay.
MAX_DESTINATION_RESPONSE = 4 * 1024 * 1024

# Section 7: the three sealed content types.  A relay never parses the response
# it is forwarding -- `relay` carries base64 bytes, not a nested object, exactly
# so that no hop needs to look inside to decide what to do with it.
TYPE_RELAY = "relay"
TYPE_SUCCESS = "success"
TYPE_ERROR = "error"

# Section 9.1: the closed set of four.  Nothing else may appear as a `code`.
ERR_NEXT_HOP_UNREACHABLE = "next_hop_unreachable"
ERR_DECRYPTION_FAILURE = "decryption_failure"
ERR_DESTINATION_UNREACHABLE = "destination_unreachable"
ERR_UNUSABLE_LAYER = "unusable_layer"


def _usable_port(value: object) -> int:
    """Section 9.1: `next_port` must be an integer port value.

    ``int()`` would accept a good deal this must not: ``int(8080.9)`` truncates
    to 8080 and ``int(True)`` is 1, so a layer carrying either would be
    silently acted on rather than reported.  ``bool`` is checked first because
    it is a subclass of ``int``.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise _UnusableLayer("next_port is not an integer port value")
    return value


class RelayNode:
    """Relay identity, keys, and the per-hop processing of section 6."""

    def __init__(self, relay_id: str, host: str, port: int, hop_timeout: float = 10.0):
        self.relay_id = relay_id
        self.host = host
        self.port = port
        self.hop_timeout = hop_timeout
        # Section 3: generated in memory at startup, held for the lifetime of
        # the process, never written to disk and never sent anywhere.  Only
        # the public half leaves this object.
        self._private_key, self.public_pem = generate_relay_keypair()

    # -- registration (section 3) -----------------------------------------

    def register_with_directory(
        self, directory_url: str, attempts: int = 30, backoff: float = 1.0
    ) -> bool:
        """Publish this relay's public key to the directory.

        Retries, because under ``docker compose up`` a relay can be ready
        before the directory is.  Only the public key is ever sent.
        """
        payload = {
            "relay_id": self.relay_id,
            "host": self.host,
            "port": self.port,
            "public_key": self.public_pem,
        }
        url = directory_url.rstrip("/") + "/register"
        for attempt in range(1, attempts + 1):
            try:
                post_json(url, payload, timeout=self.hop_timeout)
            except HttpError as exc:
                if attempt == attempts:
                    log.error(
                        "[%s] registration failed after %d attempts: %s",
                        self.relay_id,
                        attempts,
                        exc,
                    )
                    return False
                time.sleep(backoff)
                continue
            log.info("[%s] registered with directory", self.relay_id)
            return True
        return False

    # -- per-hop processing (sections 6 and 7) ----------------------------

    def handle_layer(self, wire: object, peer: str) -> tuple[int, dict]:
        """Process one inbound wire layer and return ``(http_status, body)``.

        This is the whole of section 6.  ``K`` lives in a local variable for
        exactly the duration of the request and is deleted before returning,
        which satisfies section 7's "per-request keys are discarded once the
        response is returned" more strictly than a keyed map would.

        ``request_id`` is generated here and is local to this relay -- it is
        not on the wire and is not shared with any other hop (SD-003).
        """
        request_id = secrets.token_hex(2)
        log.info("[%s] recv request_id=%s from %s", self.relay_id, request_id, peer)

        try:
            layer, session_key = open_layer(wire, self._private_key)
        except EnvelopeError as exc:
            # Section 9.3, the plaintext fallback: this relay holds no usable
            # key, so it cannot seal anything for its predecessor.  It is the
            # only branch here that answers in plaintext, and the only place
            # `decryption_failure` appears unsealed.
            #
            # The reason is logged locally and never returned -- a decryption
            # oracle is not something to offer.  Two fields, nothing else.
            log.warning(
                "[%s] request_id=%s layer failed to decrypt: %s",
                self.relay_id,
                request_id,
                exc,
            )
            return 400, {
                "error": ERR_DECRYPTION_FAILURE,
                "reported_by": self.relay_id,
            }

        # From here on `K` is held, so every failure below is SEALED (section
        # 9.1).  There is exactly one seal point, at the end.
        content: dict | None = None
        try:
            next_hop = str(layer["next_hop"])
            next_host = str(layer["next_host"])
            next_port = _usable_port(layer["next_port"])
            payload = layer_payload(layer)
        except (_UnusableLayer, EnvelopeError) as exc:
            # Section 9.1 `unusable_layer`.  The layer decrypted and passed the
            # AES-GCM tag check, so it came from whoever holds K -- this is a
            # construction fault, not tampering.  The offending field and its
            # value stay in this log line and never reach the wire.
            log.warning(
                "[%s] request_id=%s layer is unusable: %s",
                self.relay_id,
                request_id,
                exc,
            )
            content = self._error(ERR_UNUSABLE_LAYER)

        if content is None:
            # Section 8: log the next hop only.  next_host is deliberately
            # absent from this line -- for the exit hop it would name the
            # destination, which section 8 forbids and which would make the
            # isolation claim false for anyone reading the logs.
            log.info("[%s] decrypted layer -> next_hop=%s", self.relay_id, next_hop)
            log.info("[%s] forwarding %d bytes (opaque)", self.relay_id, len(payload))

            try:
                if next_hop == DESTINATION:
                    raw = self._fetch_destination(next_host, next_port, payload)
                    content = {"type": TYPE_SUCCESS, "body": _b64(raw)}
                else:
                    raw = self._forward_to_relay(next_host, next_port, payload)
                    content = {"type": TYPE_RELAY, "inner": _b64(raw)}
            except _SuccessorCannotSeal:
                # Section 9.3: the successor answered with the plaintext
                # fallback because it could not decrypt.  That response travels
                # exactly one hop and is never forwarded -- this relay emits its
                # own sealed error naming itself, and never its successor.
                log.warning(
                    "[%s] request_id=%s next_hop=%s could not decrypt its layer",
                    self.relay_id,
                    request_id,
                    next_hop,
                )
                content = self._error(ERR_DECRYPTION_FAILURE)
            except _HopFailure as exc:
                # SD-011: the failed link is named here, in this relay's own
                # log, where section 8 permits naming the next hop.  What goes
                # back upstream names only this relay, so a predecessor never
                # learns the identity of a hop further down the path.
                log.warning(
                    "[%s] request_id=%s next_hop=%s unreachable: %s",
                    self.relay_id,
                    request_id,
                    next_hop,
                    exc,
                )
                content = self._error(
                    ERR_DESTINATION_UNREACHABLE
                    if next_hop == DESTINATION
                    else ERR_NEXT_HOP_UNREACHABLE
                )

        # Section 7: seal with the retained K and a *fresh* nonce.  seal_response
        # generates the nonce itself; no call site here ever supplies one.
        # Section 9.3: HTTP 200 whenever an envelope is returned, whether what
        # it carries is a success or an error.
        envelope = seal_response(
            json.dumps(content, separators=(",", ":")).encode("utf-8"), session_key
        )
        del session_key

        log.info(
            "[%s] recv response, re-encrypting, returning to %s", self.relay_id, peer
        )
        return 200, envelope

    def _error(self, code: str) -> dict:
        """A sealed protocol error naming this relay and nothing else.

        Section 9.1: no diagnostic, no offending value, no downstream identity.
        """
        return {"type": TYPE_ERROR, "code": code, "reported_by": self.relay_id}

    def _forward_to_relay(self, host: str, port: int, payload: bytes) -> bytes:
        """Hand the opaque inner layer to the next relay and return its envelope.

        ``payload`` is the next relay's wire layer.  This relay cannot read it
        and does not try: it is decoded from base64 as JSON only because that is
        what the next hop's HTTP endpoint expects as a body.
        """
        try:
            wire = json.loads(payload.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise _HopFailure(f"inner payload is not a wire layer: {exc}") from exc

        url = f"http://{host}:{port}/relay"
        try:
            response = post_json(url, wire, timeout=self.hop_timeout)
        except HttpError as exc:
            if _is_plaintext_fallback(exc):
                raise _SuccessorCannotSeal from exc
            raise _HopFailure(str(exc)) from exc
        if not isinstance(response, dict):
            raise _HopFailure("next hop returned a body that is not an envelope")
        return json.dumps(response, separators=(",", ":")).encode("utf-8")

    def _fetch_destination(self, host: str, port: int, payload: bytes) -> bytes:
        """Send the raw HTTP request to the destination and read the raw response.

        Only the exit relay reaches this.  ``payload`` is the verbatim request
        the client built (RELAY_PROTOCOL.md section 5.1), written to the socket
        unmodified -- this relay does not parse, rewrite or re-issue it.

        The client sets ``Connection: close``, so reading to EOF is the whole
        response.
        """
        try:
            with socket.create_connection((host, port), timeout=self.hop_timeout) as sock:
                sock.settimeout(self.hop_timeout)
                sock.sendall(payload)
                chunks: list[bytes] = []
                total = 0
                while True:
                    chunk = sock.recv(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    total += len(chunk)
                    if total > MAX_DESTINATION_RESPONSE:
                        raise _HopFailure("destination response exceeded the size cap")
        except _HopFailure:
            raise
        except (OSError, TimeoutError) as exc:
            raise _HopFailure(f"destination unreachable: {exc}") from exc

        if not chunks:
            raise _HopFailure("destination closed the connection without responding")
        return b"".join(chunks)


class _HopFailure(Exception):
    """The next hop or the destination could not be reached."""


class _UnusableLayer(Exception):
    """The layer decrypted and authenticated, but cannot be acted on."""


class _SuccessorCannotSeal(Exception):
    """The next hop answered with section 9.3's plaintext fallback.

    It could not decrypt its own layer, so it held no key to seal with.  The
    predecessor converts this into its own sealed error; the plaintext never
    travels a second hop.
    """


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _is_plaintext_fallback(exc: HttpError) -> bool:
    """Is this the section 9.3 fallback, rather than an unreachable hop?

    Recognised by exactly what section 9.3 defines: HTTP 400 and a JSON object
    whose ``error`` is ``decryption_failure``.  Anything else -- including any
    other status, or a body of another shape -- is a hop failure.
    """
    return (
        exc.status == 400
        and isinstance(exc.body, dict)
        and exc.body.get("error") == ERR_DECRYPTION_FAILURE
    )


class RelayHandler(JsonRequestHandler):
    """HTTP surface of a relay: ``POST /relay`` plus a health probe."""

    node: RelayNode  # set on the server class at construction

    def do_POST(self) -> None:  # noqa: N802 - stdlib naming
        if self.path != "/relay":
            self.send_json(404, {"error": "no such endpoint"})
            return

        wire = self.read_json_body()
        if wire is None:
            self.send_json(
                400, {"error": "body must be a JSON object", "reported_by": self.node.relay_id}
            )
            return

        peer = self.client_address[0]
        status, body = self.node.handle_layer(wire, peer)
        self.send_json(status, body)

    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        if self.path == "/health":
            self.send_json(
                200, {"relay_id": self.node.relay_id, "status": "up"}
            )
            return
        self.send_json(404, {"error": "no such endpoint"})


def build_server(bind_host: str, bind_port: int, node: RelayNode) -> ThreadingHTTPServer:
    """Construct a relay server without starting it."""
    handler = type("BoundRelayHandler", (RelayHandler,), {"node": node})
    server = ThreadingHTTPServer((bind_host, bind_port), handler)
    server.daemon_threads = True
    server.node = node  # type: ignore[attr-defined]
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Sandbox relay node")
    parser.add_argument("--relay-id", default=os.environ.get("RELAY_ID"))
    parser.add_argument("--bind", default=os.environ.get("RELAY_BIND", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("RELAY_PORT", "9001")))
    parser.add_argument(
        "--advertise-host",
        default=os.environ.get("RELAY_HOST"),
        help="host other nodes use to reach this relay (defaults to relay-id)",
    )
    parser.add_argument(
        "--directory",
        default=os.environ.get("DIRECTORY_URL", "http://directory:8000"),
    )
    parser.add_argument(
        "--hop-timeout", type=float, default=float(os.environ.get("HOP_TIMEOUT", "10"))
    )
    args = parser.parse_args()

    if not args.relay_id:
        parser.error("--relay-id (or RELAY_ID) is required")

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    node = RelayNode(
        relay_id=args.relay_id,
        host=args.advertise_host or args.relay_id,
        port=args.port,
        hop_timeout=args.hop_timeout,
    )

    if not node.register_with_directory(args.directory):
        raise SystemExit(f"[{node.relay_id}] could not register with the directory")

    server = build_server(args.bind, args.port, node)
    log.info("[%s] listening on %s:%d", node.relay_id, args.bind, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("[%s] shutting down", node.relay_id)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
