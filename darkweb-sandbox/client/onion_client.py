"""Client for the simulated onion-routed network.

Implements ``AgentsDocs/RELAY_PROTOCOL.md`` sections 4, 5 and 7: request a path
from the directory, build nested layers innermost-first, send only the outermost
layer to the entry relay, and unwrap the returned envelopes in path order.

The client is the only component that knows the whole path.  That is by design:
it is the party the path is being hidden *from* everyone else on behalf of.
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
from typing import Any, NamedTuple

from common.http_util import HttpError, get_json, post_json
from common.onion_crypto import (
    DESTINATION,
    EnvelopeError,
    build_layer,
    load_public_key,
    open_response,
    seal_layer,
)

log = logging.getLogger("client")

# MOCK_SITES_SPEC.md section 6, plus the Phase-1 endpoint (SD-012).
#
# The client resolves these before building the innermost layer, so a
# `.onion.mock` name never reaches a relay (SD-007).  There is no descriptor
# lookup and no DHT here, and there is not meant to be -- see the scope lock in
# MASTER_CONTEXT.md section 3.
#
# These are mock addresses.  The `.onion.mock` suffix is mandatory and none of
# them is, or resolves to, a real onion address.
MOCK_ADDRESS_MAP: dict[str, tuple[str, int]] = {
    # Phase 1 only. Delete this entry when the Phase-4 sites land (SD-012).
    "phase1sandbox.onion.mock": ("phase1-endpoint", 80),
    # Phase 4. Inert until those containers exist.
    "alpha7fq2mx9k.onion.mock": ("forum-alpha", 80),
    "beta4np8vz3wc.onion.mock": ("marketplace-beta", 80),
    "gamma2xd6bt5hy.onion.mock": ("forum-gamma", 80),
    "delta9pqr5st.onion.mock": ("forum-delta", 80),
    "epsilon8qkw4rx.onion.mock": ("marketplace-epsilon", 80),
    "zeta5vnp3ty2.onion.mock": ("forum-zeta", 80),
    "omega9xrq2zv.onion.mock": ("marketplace-omega", 80),
}


class OnionClientError(Exception):
    """Base class for every failure this client reports."""


class DirectoryError(OnionClientError):
    """The directory could not be reached, or refused the request.

    Section 9: the client fails with a clear error and does not fall back to a
    cached path.  There is no cache.
    """


class OnionPathError(OnionClientError):
    """The request could not be carried along the path."""


class OnionRelayError(OnionPathError):
    """A relay reported a protocol error.

    RELAY_PROTOCOL.md section 9.2 row 2.  ``code`` is one of the closed set of
    four and ``reported_by`` is the relay that detected the failure -- never a
    hop further down the path (SD-011, section 9.4).
    """

    def __init__(self, code: str, reported_by: str, sealed: bool = True):
        how = "sealed" if sealed else "plaintext"
        super().__init__(
            f"path failed: {code} (reported_by={reported_by}); {how} protocol error"
            f" -- see that relay's log for its own next hop"
        )
        self.code = code
        self.reported_by = reported_by
        self.sealed = sealed


class OnionProtocolError(OnionPathError):
    """The response could not be parsed as a protocol response.

    RELAY_PROTOCOL.md section 9.2 rows 3 and 4: a **client-side** condition,
    deliberately distinct from a relay-reported error.  No relay parses relayed
    content, so no relay is in a position to report this.
    """


class AddressError(OnionClientError):
    """A `.onion.mock` address is not in the resolution table."""


class Hop(NamedTuple):
    """One relay on a path, as the directory described it."""

    relay_id: str
    host: str
    port: int
    public_key: str


class Trace(NamedTuple):
    """What actually went on the wire, for verification and demonstration.

    This exists so the visibility table in RELAY_PROTOCOL.md section 6 can be
    checked against a real request rather than asserted -- Phase 3's acceptance
    criterion 2 requires verifying "by inspecting what each relay actually
    decrypts".  It holds only what the client already knows.
    """

    path: list[Hop]
    outer_layer: dict
    session_keys: list[bytes]
    response_envelopes: list[dict]


def resolve_mock_address(mock_host: str) -> tuple[str, int]:
    """Map a `.onion.mock` address to its container and port (SD-007)."""
    try:
        return MOCK_ADDRESS_MAP[mock_host]
    except KeyError:
        raise AddressError(
            f"unknown mock address {mock_host!r}; "
            f"known addresses: {', '.join(sorted(MOCK_ADDRESS_MAP))}"
        ) from None


def build_raw_request(mock_host: str, resource: str) -> bytes:
    """Build the verbatim HTTP request the exit relay will write to the socket.

    The `Host:` header carries the `.onion.mock` name, so the destination is
    addressed as the mock address even though the TCP connection is made to a
    container name.

    `Connection: close` is set so the exit relay can read the whole response to
    EOF without parsing it.
    """
    if not resource.startswith("/"):
        resource = "/" + resource
    lines = [
        f"GET {resource} HTTP/1.1",
        f"Host: {mock_host}",
        "User-Agent: sandbox-onion-client/1.0",
        "Accept: */*",
        "Connection: close",
        "",
        "",
    ]
    return "\r\n".join(lines).encode("utf-8")


class OnionClient:
    """Builds circuits and carries requests along them."""

    def __init__(self, directory_url: str, timeout: float = 10.0):
        self.directory_url = directory_url.rstrip("/")
        self.timeout = timeout

    # -- directory (section 4) --------------------------------------------

    def get_relays(self) -> list[dict]:
        """List every registered relay and its status -- demo visibility."""
        try:
            body = get_json(f"{self.directory_url}/relays", timeout=self.timeout)
        except HttpError as exc:
            raise DirectoryError(f"could not list relays: {exc}") from exc
        return body.get("relays", []) if isinstance(body, dict) else []

    def get_path(self, hops: int = 3) -> list[Hop]:
        """Request a fresh path of ``hops`` relays.

        A new path is selected per session, so consecutive runs visibly differ.
        Section 4 calls that a demo requirement rather than an optimisation.
        """
        try:
            body = get_json(
                f"{self.directory_url}/path?hops={hops}", timeout=self.timeout
            )
        except HttpError as exc:
            detail = ""
            if isinstance(exc.body, dict) and "error" in exc.body:
                detail = f": {exc.body['error']}"
            raise DirectoryError(f"could not obtain a path{detail}") from exc

        if not isinstance(body, dict) or "relays" not in body:
            raise DirectoryError("directory returned a malformed path")

        path = [
            Hop(
                relay_id=r["relay_id"],
                host=r["host"],
                port=int(r["port"]),
                public_key=r["public_key"],
            )
            for r in body["relays"]
        ]
        log.info(
            "path_id=%s hops=%d entry=%s",
            body.get("path_id", "?"),
            len(path),
            path[0].relay_id if path else "-",
        )
        return path

    # -- layer construction (section 5) -----------------------------------

    def build_layers(
        self, path: list[Hop], dest_host: str, dest_port: int, raw_request: bytes
    ) -> tuple[dict, list[bytes]]:
        """Build the nested layers for ``path``, innermost first.

        For path [A, B, C] this produces exactly the construction in section
        5.3: the innermost layer names DESTINATION, each outer layer names the
        relay that follows it, and only the outermost layer is ever sent.

        Returns ``(outermost_wire_layer, session_keys_in_path_order)``.
        """
        if not path:
            raise OnionPathError("cannot build layers for an empty path")

        # Innermost: the exit relay is told the destination and carries the
        # raw request as its opaque payload.
        layer = build_layer(DESTINATION, dest_host, dest_port, raw_request)

        keys_reversed: list[bytes] = []
        wire: dict = {}

        # Work outward.  At each step the layer just sealed becomes the payload
        # of the next one out, and the hop that will open it is named by the
        # hop before it.
        for index in range(len(path) - 1, -1, -1):
            hop = path[index]
            try:
                public_key = load_public_key(hop.public_key)
            except EnvelopeError as exc:
                raise OnionPathError(
                    f"relay {hop.relay_id} published an unusable public key: {exc}"
                ) from exc

            wire, session_key = seal_layer(layer, public_key)
            keys_reversed.append(session_key)

            if index > 0:
                previous = path[index - 1]
                payload = json.dumps(wire, separators=(",", ":")).encode("utf-8")
                layer = build_layer(hop.relay_id, hop.host, hop.port, payload)
                del previous  # named only to make the direction of travel obvious

        session_keys = list(reversed(keys_reversed))
        return wire, session_keys

    # -- send and unwrap (sections 6 and 7) -------------------------------

    def send(self, path: list[Hop], outer_layer: dict) -> dict:
        """Send the outermost layer to the entry relay and return its envelope.

        Only the entry relay is contacted.  Nothing is sent to B or C directly
        (section 5.3).
        """
        entry = path[0]
        url = f"http://{entry.host}:{entry.port}/relay"
        try:
            envelope = post_json(url, outer_layer, timeout=self.timeout)
        except HttpError as exc:
            raise self._hop_failure(entry, exc) from exc
        if not isinstance(envelope, dict):
            raise OnionProtocolError(
                f"entry relay {entry.relay_id} returned a body that is not an envelope"
            )
        return envelope

    @staticmethod
    def _hop_failure(entry: Hop, exc: HttpError) -> OnionPathError:
        """Classify a non-envelope answer from the entry relay (section 9.2).

        Only one non-2xx response is part of the protocol: section 9.3's
        plaintext fallback, which the client sees when the **entry** relay is
        itself unable to decrypt.  That is a protocol error.  A relay that could
        not be reached at all, or that answered with anything else, is a
        client-side transport condition.
        """
        if exc.status is None:
            return OnionPathError(
                f"entry relay {entry.relay_id} ({entry.host}:{entry.port}) "
                f"is unreachable: {exc}"
            )
        if (
            exc.status == 400
            and isinstance(exc.body, dict)
            and exc.body.get("error") == "decryption_failure"
        ):
            return OnionRelayError(
                "decryption_failure",
                str(exc.body.get("reported_by", entry.relay_id)),
                sealed=False,
            )
        return OnionProtocolError(
            f"entry relay {entry.relay_id} returned HTTP {exc.status}"
        )

    def unwrap(self, envelope: dict, session_keys: list[bytes]) -> tuple[bytes, list[dict]]:
        """Peel the response envelopes in path order A -> B -> C (section 7).

        Each relay added a layer on the way back, so the client removes them in
        the order the path was built.  What falls out of each decryption is a
        **typed object**, and unwrapping stops at the first terminal type:
        `success` carries the destination's raw response, `error` is a relay's
        protocol error.

        Section 9.3 and section F: the type is authoritative.  Success is never
        inferred from how many layers were peeled, and never from an HTTP
        status.
        """
        envelopes: list[dict] = []
        current: Any = envelope
        for index, key in enumerate(session_keys):
            if not isinstance(current, dict):
                raise OnionProtocolError(f"response layer {index} is not an envelope")
            envelopes.append(current)
            try:
                inner = open_response(current, key)
            except EnvelopeError as exc:
                raise OnionProtocolError(
                    f"could not open response layer {index}: {exc}"
                ) from exc

            content = self._typed_content(index, inner)
            kind = content["type"]

            if kind == "success":
                return self._terminal_bytes(index, content, "body"), envelopes
            if kind == "error":
                raise OnionRelayError(
                    str(content.get("code", "unknown_error")),
                    str(content.get("reported_by", "unknown")),
                )
            if kind != "relay":
                raise OnionProtocolError(
                    f"response layer {index} carries an unknown type"
                )

            nested = self._terminal_bytes(index, content, "inner")
            try:
                current = json.loads(nested.decode("utf-8"))
            except Exception as exc:  # noqa: BLE001
                raise OnionProtocolError(
                    f"response layer {index} did not contain a nested envelope"
                ) from exc

        raise OnionProtocolError(
            "the response ran out of layers before reaching a terminal type"
        )

    @staticmethod
    def _typed_content(index: int, inner: bytes) -> dict:
        try:
            content = json.loads(inner.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise OnionProtocolError(
                f"response layer {index} is not a typed protocol object"
            ) from exc
        if not isinstance(content, dict) or not isinstance(content.get("type"), str):
            raise OnionProtocolError(f"response layer {index} carries no type")
        return content

    @staticmethod
    def _terminal_bytes(index: int, content: dict, field: str) -> bytes:
        value = content.get(field)
        if not isinstance(value, str):
            raise OnionProtocolError(
                f"response layer {index} is missing its {field!r} field"
            )
        try:
            return base64.b64decode(value, validate=True)
        except Exception as exc:  # noqa: BLE001
            raise OnionProtocolError(
                f"response layer {index} has a {field!r} that is not base64"
            ) from exc

    # -- the public call --------------------------------------------------

    def get(self, path: list[Hop], mock_host: str, resource: str) -> bytes:
        """Fetch ``resource`` from ``mock_host`` through ``path``.

        This is the call signature SCRAPER_AGENT_SPEC.md section 2 already
        specifies, so the Phase-5 scraper needs no change here.
        """
        body, _ = self.get_with_trace(path, mock_host, resource)
        return body

    def get_with_trace(
        self, path: list[Hop], mock_host: str, resource: str
    ) -> tuple[bytes, Trace]:
        """As ``get``, and also return what went on the wire.

        Used by the Phase-1 verification to check the section 6 visibility
        table against a real request instead of taking it on trust.
        """
        dest_host, dest_port = resolve_mock_address(mock_host)
        raw_request = build_raw_request(mock_host, resource)

        outer_layer, session_keys = self.build_layers(
            path, dest_host, dest_port, raw_request
        )
        envelope = self.send(path, outer_layer)
        body, envelopes = self.unwrap(envelope, session_keys)

        trace = Trace(
            path=list(path),
            outer_layer=outer_layer,
            session_keys=session_keys,
            response_envelopes=envelopes,
        )
        return body, trace


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch a page through the simulated onion-routed network"
    )
    parser.add_argument(
        "--directory", default=os.environ.get("DIRECTORY_URL", "http://localhost:8000")
    )
    parser.add_argument("--hops", type=int, default=3)
    parser.add_argument("--host", default="phase1sandbox.onion.mock")
    parser.add_argument("--resource", default="/")
    parser.add_argument(
        "--timeout", type=float, default=float(os.environ.get("HOP_TIMEOUT", "10"))
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="[client] %(message)s")

    client = OnionClient(args.directory, timeout=args.timeout)
    path = client.get_path(args.hops)

    print(f"path: {' -> '.join(hop.relay_id for hop in path)}")
    body = client.get(path, args.host, args.resource)
    print(f"--- {len(body)} bytes from {args.host}{args.resource} ---")
    print(body.decode("utf-8", errors="replace"))


if __name__ == "__main__":
    main()
