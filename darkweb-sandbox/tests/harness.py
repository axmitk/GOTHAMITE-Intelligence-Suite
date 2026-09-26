"""Test harness: a whole relay pool in one process, on ephemeral loopback ports.

The servers started here are the same classes the containers run -- nothing is
stubbed, mocked or reimplemented for testing.  Only the bind addresses differ.

Nothing in this harness, or in any test that uses it, contacts the network.
Every socket is on 127.0.0.1 / localhost.
"""

from __future__ import annotations

import base64
import json
import logging
import socket
import threading
from http.server import ThreadingHTTPServer

from client import onion_client
from client.onion_client import Hop, OnionClient
from common.onion_crypto import open_layer
from directory.directory_service import build_server as build_directory
from mock_sites import seed_data
from mock_sites.site_server import build_server as build_site
from phase1_endpoint.static_endpoint import build_server as build_endpoint
from relay.relay_node import RelayNode
from relay.relay_node import build_server as build_relay

# The Phase-1 endpoint is reached under this name during tests, while relays
# advertise 127.0.0.1.  Two distinct spellings of loopback let the visibility
# assertions tell "the destination" apart from "a relay" in decrypted bytes.
ENDPOINT_TEST_HOST = "localhost"
MOCK_HOST = "phase1sandbox.onion.mock"

# The Phase-4 sites, keyed by the .onion.mock address MOCK_SITES_SPEC.md
# section 6 assigns them.  Tests reach them the way the scraper will: through
# the relay chain, by mock address, never by host and port.
SITE_ADDRESSES = {site.site_id: site.address for site in seed_data.SITES.values()}


def free_port() -> int:
    """Reserve and release a port, returning a number nothing is listening on.

    Used to point a hop at a closed port for the failure tests.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class LogCapture:
    """Collect every log record emitted while the block is active."""

    def __init__(self) -> None:
        self.records: list[str] = []
        self._handler: logging.Handler | None = None

    def __enter__(self) -> LogCapture:
        capture = self

        class _Handler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                try:
                    capture.records.append(record.getMessage())
                except Exception:  # noqa: BLE001
                    capture.records.append("<unformattable record>")

        self._handler = _Handler()
        root = logging.getLogger()
        root.addHandler(self._handler)
        self._previous_level = root.level
        root.setLevel(logging.DEBUG)
        return self

    def __exit__(self, *exc: object) -> None:
        root = logging.getLogger()
        if self._handler is not None:
            root.removeHandler(self._handler)
        root.setLevel(self._previous_level)

    @property
    def text(self) -> str:
        return "\n".join(self.records)


class SandboxHarness:
    """Directory + N relays + the Phase-1 endpoint, all in-process."""

    def __init__(
        self,
        relay_count: int = 7,
        hop_timeout: float = 5.0,
        with_sites: bool = False,
    ):
        self.relay_count = relay_count
        self.hop_timeout = hop_timeout
        self.with_sites = with_sites
        self.nodes: dict[str, RelayNode] = {}
        self.site_ports: dict[str, int] = {}
        self._servers: list[ThreadingHTTPServer] = []
        self._threads: list[threading.Thread] = []
        self._saved_map_entry: tuple[str, int] | None = None
        self._saved_site_entries: dict[str, tuple[str, int]] = {}

    # -- lifecycle --------------------------------------------------------

    def start(self) -> None:
        self.directory_server = build_directory("127.0.0.1", 0)
        self.directory_port = self.directory_server.server_address[1]
        self._serve(self.directory_server)
        self.directory_url = f"http://127.0.0.1:{self.directory_port}"

        self.endpoint_server = build_endpoint("127.0.0.1", 0)
        self.endpoint_port = self.endpoint_server.server_address[1]
        self._serve(self.endpoint_server)

        # Point the client's resolution table at the ephemeral endpoint for the
        # duration of the tests, and remember what to put back.
        self._saved_map_entry = onion_client.MOCK_ADDRESS_MAP[MOCK_HOST]
        onion_client.MOCK_ADDRESS_MAP[MOCK_HOST] = (
            ENDPOINT_TEST_HOST,
            self.endpoint_port,
        )

        if self.with_sites:
            self._start_sites()

        for index in range(1, self.relay_count + 1):
            relay_id = f"relay-{index:02d}"
            node = RelayNode(
                relay_id=relay_id,
                host="127.0.0.1",
                port=0,  # replaced below, once the socket is bound
                hop_timeout=self.hop_timeout,
            )
            server = build_relay("127.0.0.1", 0, node)
            node.port = server.server_address[1]
            self._serve(server)
            self.nodes[relay_id] = node
            registered = node.register_with_directory(
                self.directory_url, attempts=10, backoff=0.05
            )
            if not registered:
                raise RuntimeError(f"{relay_id} failed to register with the directory")

    def _start_sites(self) -> None:
        """Start all three Phase-4 sites and point the client's map at them.

        Same server class the containers run; only the bind address differs.
        The sites are addressed as "localhost" while relays advertise
        "127.0.0.1", so the section 6 visibility assertions can still tell a
        destination apart from a relay in decrypted bytes.
        """
        for site_id, address in SITE_ADDRESSES.items():
            server = build_site(site_id, "127.0.0.1", 0)
            port = server.server_address[1]
            self._serve(server)
            self.site_ports[site_id] = port
            self._saved_site_entries[address] = onion_client.MOCK_ADDRESS_MAP[address]
            onion_client.MOCK_ADDRESS_MAP[address] = (ENDPOINT_TEST_HOST, port)

    def stop(self) -> None:
        for address, entry in self._saved_site_entries.items():
            onion_client.MOCK_ADDRESS_MAP[address] = entry
        self._saved_site_entries.clear()
        self.site_ports.clear()
        if self._saved_map_entry is not None:
            onion_client.MOCK_ADDRESS_MAP[MOCK_HOST] = self._saved_map_entry
            self._saved_map_entry = None
        for server in self._servers:
            server.shutdown()
            server.server_close()
        for thread in self._threads:
            thread.join(timeout=5)
        self._servers.clear()
        self._threads.clear()
        self.nodes.clear()

    def _serve(self, server: ThreadingHTTPServer) -> None:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self._servers.append(server)
        self._threads.append(thread)

    # -- convenience ------------------------------------------------------

    def client(self) -> OnionClient:
        return OnionClient(self.directory_url, timeout=self.hop_timeout)

    def private_key_for(self, relay_id: str):
        """The relay's private key, for verifying what that hop can decrypt.

        Reaching into a relay's private state is exactly what a test may do and
        a peer may not: it is how the section 6 visibility table gets checked
        against a real request rather than asserted.
        """
        return self.nodes[relay_id]._private_key  # noqa: SLF001

    def peel(self, wire: dict, hop: Hop) -> tuple[dict, bytes]:
        """Decrypt one layer as the named hop would."""
        return open_layer(wire, self.private_key_for(hop.relay_id))

    def request_layer_nonces(self, outer_layer: dict, path: list[Hop]) -> list[str]:
        """Every nonce used on the forward leg, outermost first."""
        nonces = [outer_layer["nonce"]]
        wire = outer_layer
        for index, hop in enumerate(path):
            layer, _ = self.peel(wire, hop)
            if layer["next_hop"] == "DESTINATION":
                break
            inner = json.loads(base64.b64decode(layer["payload"]).decode("utf-8"))
            nonces.append(inner["nonce"])
            wire = inner
            del index
        return nonces
