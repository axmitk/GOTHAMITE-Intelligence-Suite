"""Phase-1 verification.

Every test here runs the real directory, the real relays and the real client
against loopback sockets.  Nothing contacts the network, and nothing is
stubbed.

Coverage maps to:
  * RELAY_PROTOCOL.md section 11  -- Phase 1 acceptance, all six
  * DIRECTORY_SPEC.md section 5   -- Phase 2 acceptance, all seven
  * IMPLEMENTATION_PLAN.md Phase 3 acceptance, all six
"""

from __future__ import annotations

import base64
import json
import unittest

from client.onion_client import (
    AddressError,
    DirectoryError,
    Hop,
    OnionPathError,
    OnionProtocolError,
    OnionRelayError,
    build_raw_request,
    resolve_mock_address,
)
from common.http_util import HttpError, get_json, post_json
from common.onion_crypto import (
    NONCE_BYTES,
    EnvelopeError,
    generate_relay_keypair,
    load_public_key,
    open_layer,
    open_response,
    seal_layer,
)
from phase1_endpoint.static_endpoint import PAGE
from tests.harness import (
    ENDPOINT_TEST_HOST,
    MOCK_HOST,
    LogCapture,
    SandboxHarness,
    free_port,
)


_HARNESS: SandboxHarness | None = None


def setUpModule() -> None:  # noqa: N802 - unittest naming
    """Start one pool for the whole module.

    Seven RSA-2048 keypairs is the expensive part of setup, so the suite pays
    for it once rather than once per test class.
    """
    global _HARNESS
    _HARNESS = SandboxHarness(relay_count=7)
    _HARNESS.start()


def tearDownModule() -> None:  # noqa: N802 - unittest naming
    if _HARNESS is not None:
        _HARNESS.stop()


class Phase1TestCase(unittest.TestCase):
    """One pool shared by the whole suite; each test asks for its own path."""

    @classmethod
    def setUpClass(cls) -> None:
        assert _HARNESS is not None, "harness was not started"
        cls.harness = _HARNESS

    def setUp(self) -> None:
        self.client = self.harness.client()
        # Leave the pool as the suite found it: everything up.
        for relay_id in self.harness.nodes:
            post_json(
                f"{self.harness.directory_url}/relays/{relay_id}/status",
                {"status": "up"},
                timeout=5,
            )


# ---------------------------------------------------------------------------
# 1. Relay starts successfully
# ---------------------------------------------------------------------------


class TestRelayStartup(Phase1TestCase):
    def test_every_relay_answers_its_health_probe(self):
        for relay_id, node in self.harness.nodes.items():
            body = get_json(f"http://{node.host}:{node.port}/health", timeout=5)
            self.assertEqual(body["relay_id"], relay_id)
            self.assertEqual(body["status"], "up")

    def test_relay_generates_an_rsa_2048_keypair_in_memory(self):
        node = self.harness.nodes["relay-01"]
        self.assertEqual(node._private_key.key_size, 2048)  # noqa: SLF001
        self.assertIn("BEGIN PUBLIC KEY", node.public_pem)
        # The public PEM is the only key material that ever leaves the relay.
        self.assertNotIn("PRIVATE KEY", node.public_pem)

    def test_every_relay_has_a_distinct_keypair(self):
        pems = {node.public_pem for node in self.harness.nodes.values()}
        self.assertEqual(len(pems), len(self.harness.nodes))


# ---------------------------------------------------------------------------
# 2. Relay registers with the directory
# ---------------------------------------------------------------------------


class TestRegistration(Phase1TestCase):
    def test_all_seven_relays_are_registered_and_up(self):
        body = get_json(f"{self.harness.directory_url}/relays", timeout=5)
        self.assertEqual(body["count"], 7)
        self.assertEqual({r["status"] for r in body["relays"]}, {"up"})

    def test_directory_holds_public_keys_and_no_private_keys(self):
        body = get_json(f"{self.harness.directory_url}/relays", timeout=5)
        for entry in body["relays"]:
            self.assertIn("BEGIN PUBLIC KEY", entry["public_key"])
            self.assertNotIn("PRIVATE KEY", entry["public_key"])

    def test_registration_carrying_a_private_key_is_rejected(self):
        private_key, _ = generate_relay_keypair()
        from cryptography.hazmat.primitives import serialization

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("ascii")

        with self.assertRaises(HttpError) as caught:
            post_json(
                f"{self.harness.directory_url}/register",
                {
                    "relay_id": "relay-99",
                    "host": "relay-99",
                    "port": 9099,
                    "public_key": private_pem,
                },
                timeout=5,
            )
        self.assertEqual(caught.exception.status, 400)

    def test_registration_with_a_bad_pem_is_rejected(self):
        with self.assertRaises(HttpError) as caught:
            post_json(
                f"{self.harness.directory_url}/register",
                {
                    "relay_id": "relay-98",
                    "host": "relay-98",
                    "port": 9098,
                    "public_key": "not a pem at all",
                },
                timeout=5,
            )
        self.assertEqual(caught.exception.status, 400)

    def test_registration_missing_a_field_is_rejected(self):
        with self.assertRaises(HttpError) as caught:
            post_json(
                f"{self.harness.directory_url}/register",
                {"relay_id": "relay-97", "host": "relay-97"},
                timeout=5,
            )
        self.assertEqual(caught.exception.status, 400)

    def test_re_registration_overwrites_and_sets_up(self):
        """Container restarts must be safe (DIRECTORY_SPEC.md section 3)."""
        node = self.harness.nodes["relay-03"]
        post_json(
            f"{self.harness.directory_url}/relays/relay-03/status",
            {"status": "down"},
            timeout=5,
        )
        self.assertTrue(node.register_with_directory(self.harness.directory_url, attempts=3))
        body = get_json(f"{self.harness.directory_url}/relays", timeout=5)
        entry = next(r for r in body["relays"] if r["relay_id"] == "relay-03")
        self.assertEqual(entry["status"], "up")


# ---------------------------------------------------------------------------
# 3. Client can obtain relay information
# 4. A multi-hop path can be constructed
# ---------------------------------------------------------------------------


class TestPathSelection(Phase1TestCase):
    def test_client_lists_relays(self):
        relays = self.client.get_relays()
        self.assertEqual(len(relays), 7)

    def test_path_has_the_requested_length_and_no_duplicates(self):
        for hops in (2, 3, 4, 5):
            path = self.client.get_path(hops)
            self.assertEqual(len(path), hops)
            self.assertEqual(len({hop.relay_id for hop in path}), hops)

    def test_ten_consecutive_paths_are_not_all_identical(self):
        """DIRECTORY_SPEC.md section 5 criterion 2."""
        seen = {
            tuple(hop.relay_id for hop in self.client.get_path(3)) for _ in range(10)
        }
        self.assertGreater(len(seen), 1, "path selection is not varying")

    def test_hops_below_and_above_the_range_are_rejected(self):
        """DIRECTORY_SPEC.md section 5 criterion 5."""
        for hops in (1, 6):
            with self.assertRaises(DirectoryError):
                self.client.get_path(hops)

    def test_a_downed_relay_is_never_selected(self):
        """DIRECTORY_SPEC.md section 5 criterion 4."""
        post_json(
            f"{self.harness.directory_url}/relays/relay-05/status",
            {"status": "down"},
            timeout=5,
        )
        for _ in range(25):
            path = self.client.get_path(5)
            self.assertNotIn("relay-05", [hop.relay_id for hop in path])

    def test_insufficient_relays_returns_503_naming_the_shortfall(self):
        """DIRECTORY_SPEC.md section 5 criterion 6."""
        for relay_id in ("relay-03", "relay-04", "relay-05", "relay-06", "relay-07"):
            post_json(
                f"{self.harness.directory_url}/relays/{relay_id}/status",
                {"status": "down"},
                timeout=5,
            )
        with self.assertRaises(HttpError) as caught:
            get_json(f"{self.harness.directory_url}/path?hops=3", timeout=5)
        self.assertEqual(caught.exception.status, 503)
        self.assertIn("2", caught.exception.body["error"])

    def test_directory_logs_no_path_composition(self):
        """DIRECTORY_SPEC.md section 4 and section 5 criterion 7."""
        with LogCapture() as capture:
            path = self.client.get_path(3)
        for hop in path:
            self.assertNotIn(
                hop.relay_id,
                capture.text.replace("entry=" + path[0].relay_id, ""),
                f"directory or client log leaked path member {hop.relay_id}",
            )


# ---------------------------------------------------------------------------
# 5. Request layers are constructed correctly
# 6. Each relay removes exactly one layer
# ---------------------------------------------------------------------------


class TestLayerConstruction(Phase1TestCase):
    def test_layers_nest_innermost_first_and_name_the_right_next_hop(self):
        """RELAY_PROTOCOL.md section 5.3."""
        path = self.client.get_path(3)
        raw = build_raw_request(MOCK_HOST, "/")
        dest_host, dest_port = resolve_mock_address(MOCK_HOST)
        outer, keys = self.client.build_layers(path, dest_host, dest_port, raw)

        self.assertEqual(len(keys), 3)
        self.assertEqual(set(outer), {"enc_key", "nonce", "ciphertext"})

        # Hop A: names B, carries an opaque inner layer.
        layer_a, _ = self.harness.peel(outer, path[0])
        self.assertEqual(layer_a["next_hop"], path[1].relay_id)
        self.assertEqual(layer_a["next_host"], path[1].host)
        self.assertEqual(layer_a["next_port"], path[1].port)

        wire_b = json.loads(base64.b64decode(layer_a["payload"]).decode("utf-8"))
        self.assertEqual(set(wire_b), {"enc_key", "nonce", "ciphertext"})

        # Hop B: names C.
        layer_b, _ = self.harness.peel(wire_b, path[1])
        self.assertEqual(layer_b["next_hop"], path[2].relay_id)

        # Hop C: the exit. Only here do the destination and the request appear.
        wire_c = json.loads(base64.b64decode(layer_b["payload"]).decode("utf-8"))
        layer_c, _ = self.harness.peel(wire_c, path[2])
        self.assertEqual(layer_c["next_hop"], "DESTINATION")
        self.assertEqual(layer_c["next_host"], ENDPOINT_TEST_HOST)
        self.assertEqual(base64.b64decode(layer_c["payload"]), raw)

    def test_a_relay_cannot_open_a_layer_addressed_to_another_relay(self):
        """Each relay decrypts exactly one layer, and only its own."""
        path = self.client.get_path(3)
        raw = build_raw_request(MOCK_HOST, "/")
        dest_host, dest_port = resolve_mock_address(MOCK_HOST)
        outer, _ = self.client.build_layers(path, dest_host, dest_port, raw)

        for other in (path[1], path[2]):
            with self.assertRaises(EnvelopeError):
                open_layer(outer, self.harness.private_key_for(other.relay_id))

    def test_the_visibility_table_holds(self):
        """RELAY_PROTOCOL.md section 6 -- the acceptance test for Phase 1 and 3.

        The middle relay must not be able to see the destination, and neither
        the entry nor the middle relay may see the request body.
        """
        path = self.client.get_path(3)
        raw = build_raw_request(MOCK_HOST, "/")
        dest_host, dest_port = resolve_mock_address(MOCK_HOST)
        outer, _ = self.client.build_layers(path, dest_host, dest_port, raw)

        destination = ENDPOINT_TEST_HOST.encode()
        body_marker = b"User-Agent: sandbox-onion-client"

        # Entry: everything it can decrypt, in full.
        layer_a, _ = self.harness.peel(outer, path[0])
        visible_a = json.dumps(layer_a).encode()
        self.assertNotIn(destination, visible_a, "entry relay can see the destination")
        self.assertNotIn(body_marker, base64.b64decode(layer_a["payload"]))

        # Middle: same check, one layer in.
        wire_b = json.loads(base64.b64decode(layer_a["payload"]).decode("utf-8"))
        layer_b, _ = self.harness.peel(wire_b, path[1])
        visible_b = json.dumps(layer_b).encode()
        self.assertNotIn(destination, visible_b, "middle relay can see the destination")
        self.assertNotIn(body_marker, base64.b64decode(layer_b["payload"]))

        # Exit: sees both. This is a documented property of onion routing, not
        # a defect -- RELAY_PROTOCOL.md section 6 says to state it openly.
        wire_c = json.loads(base64.b64decode(layer_b["payload"]).decode("utf-8"))
        layer_c, _ = self.harness.peel(wire_c, path[2])
        self.assertEqual(layer_c["next_host"], ENDPOINT_TEST_HOST)
        self.assertIn(body_marker, base64.b64decode(layer_c["payload"]))


# ---------------------------------------------------------------------------
# 7. The correct next hop is reached
# 8. Response returns successfully
# ---------------------------------------------------------------------------


class TestEndToEnd(Phase1TestCase):
    def test_three_hop_request_completes_and_returns_the_page(self):
        path = self.client.get_path(3)
        body = self.client.get(path, MOCK_HOST, "/")
        self.assertIn(b"200 OK", body)
        self.assertIn(b"phase1-endpoint-ok", body)
        self.assertIn(PAGE.strip(), body)

    def test_works_at_two_and_five_hops(self):
        """IMPLEMENTATION_PLAN.md Phase 3 criterion 5."""
        for hops in (2, 3, 4, 5):
            path = self.client.get_path(hops)
            body = self.client.get(path, MOCK_HOST, "/")
            self.assertIn(b"phase1-endpoint-ok", body, f"failed at hops={hops}")

    def test_two_consecutive_runs_use_different_paths(self):
        """IMPLEMENTATION_PLAN.md Phase 3 criterion 4."""
        seen = set()
        for _ in range(10):
            path = self.client.get_path(3)
            body = self.client.get(path, MOCK_HOST, "/")
            self.assertIn(b"phase1-endpoint-ok", body)
            seen.add(tuple(hop.relay_id for hop in path))
        self.assertGreater(len(seen), 1)

    def test_a_404_at_the_destination_is_returned_intact(self):
        path = self.client.get_path(3)
        body = self.client.get(path, MOCK_HOST, "/nope")
        self.assertIn(b"404", body)

    def test_unknown_mock_address_is_named_clearly(self):
        path = self.client.get_path(2)
        with self.assertRaises(AddressError):
            self.client.get(path, "doesnotexist.onion.mock", "/")


# ---------------------------------------------------------------------------
# 9. Fresh nonces are used where required
# ---------------------------------------------------------------------------


class TestNonceDiscipline(Phase1TestCase):
    def test_every_forward_layer_uses_a_distinct_nonce(self):
        path = self.client.get_path(5)
        raw = build_raw_request(MOCK_HOST, "/")
        dest_host, dest_port = resolve_mock_address(MOCK_HOST)
        outer, keys = self.client.build_layers(path, dest_host, dest_port, raw)

        nonces = self.harness.request_layer_nonces(outer, path)
        self.assertEqual(len(nonces), 5)
        self.assertEqual(len(set(nonces)), 5, "a nonce was reused across layers")
        self.assertEqual(len(set(keys)), 5, "a session key was reused across layers")

    def test_response_nonces_are_fresh_and_differ_from_request_nonces(self):
        """RELAY_PROTOCOL.md section 7: a fresh nonce for every encryption,
        forward and return.  The return leg reuses K, so the nonce is the only
        thing standing between this and catastrophic AES-GCM misuse."""
        path = self.client.get_path(3)
        _, trace = self.client.get_with_trace(path, MOCK_HOST, "/")

        request_nonces = set(self.harness.request_layer_nonces(trace.outer_layer, path))
        response_nonces = [env["nonce"] for env in trace.response_envelopes]

        self.assertEqual(len(response_nonces), 3)
        self.assertEqual(
            len(set(response_nonces)), 3, "a nonce was reused across response layers"
        )
        self.assertFalse(
            request_nonces & set(response_nonces),
            "a nonce was reused between the forward and return legs",
        )

    def test_nonces_do_not_repeat_across_runs(self):
        seen: set[str] = set()
        for _ in range(5):
            path = self.client.get_path(3)
            _, trace = self.client.get_with_trace(path, MOCK_HOST, "/")
            nonces = set(self.harness.request_layer_nonces(trace.outer_layer, path))
            nonces |= {env["nonce"] for env in trace.response_envelopes}
            self.assertFalse(seen & nonces, "a nonce repeated across runs")
            seen |= nonces


# ---------------------------------------------------------------------------
# 10. Private keys and sensitive payload data are not emitted into logs
# ---------------------------------------------------------------------------


class TestLogHygiene(Phase1TestCase):
    def test_logs_carry_no_keys_no_nonces_no_ciphertext_no_destination(self):
        """RELAY_PROTOCOL.md section 8."""
        path = self.client.get_path(3)
        with LogCapture() as capture:
            body, trace = self.client.get_with_trace(path, MOCK_HOST, "/")
        logs = capture.text

        self.assertIn(b"phase1-endpoint-ok", body)  # the run really happened
        self.assertIn("recv request_id=", logs)  # and really logged

        self.assertNotIn("PRIVATE KEY", logs)
        for node in self.harness.nodes.values():
            self.assertNotIn(node.public_pem.strip(), logs)

        for key in trace.session_keys:
            self.assertNotIn(base64.b64encode(key).decode(), logs)

        for nonce in self.harness.request_layer_nonces(trace.outer_layer, path):
            self.assertNotIn(nonce, logs)
        for envelope in trace.response_envelopes:
            self.assertNotIn(envelope["nonce"], logs)
            self.assertNotIn(envelope["ciphertext"], logs)

        self.assertNotIn(trace.outer_layer["ciphertext"], logs)
        # The destination and the page contents never appear in any relay log.
        self.assertNotIn(ENDPOINT_TEST_HOST, logs)
        self.assertNotIn("phase1-endpoint-ok", logs)

    def test_each_relay_logs_exactly_one_hop(self):
        """IMPLEMENTATION_PLAN.md Phase 3 criterion 3."""
        path = self.client.get_path(3)
        with LogCapture() as capture:
            self.client.get(path, MOCK_HOST, "/")

        for index, hop in enumerate(path):
            mine = [
                line for line in capture.records if line.startswith(f"[{hop.relay_id}]")
            ]
            decrypted = [line for line in mine if "decrypted layer ->" in line]
            self.assertEqual(
                len(decrypted), 1, f"{hop.relay_id} logged {len(decrypted)} hops"
            )
            expected = "DESTINATION" if index == len(path) - 1 else path[index + 1].relay_id
            self.assertIn(f"next_hop={expected}", decrypted[0])

            # No relay names a hop other than its own successor.
            others = {h.relay_id for h in path} - {hop.relay_id}
            if index + 1 < len(path):
                others.discard(path[index + 1].relay_id)
            for other in others:
                self.assertNotIn(other, "\n".join(mine))


# ---------------------------------------------------------------------------
# 11. Invalid messages fail safely
# ---------------------------------------------------------------------------


class TestInvalidInput(Phase1TestCase):
    def _entry(self) -> Hop:
        return self.client.get_path(2)[0]

    def test_garbage_envelope_is_refused_with_400(self):
        entry = self._entry()
        with self.assertRaises(HttpError) as caught:
            post_json(
                f"http://{entry.host}:{entry.port}/relay",
                {"enc_key": "!!!", "nonce": "!!!", "ciphertext": "!!!"},
                timeout=5,
            )
        self.assertEqual(caught.exception.status, 400)
        self.assertEqual(caught.exception.body["reported_by"], entry.relay_id)

    def test_layer_sealed_to_the_wrong_relay_is_refused(self):
        path = self.client.get_path(2)
        raw = build_raw_request(MOCK_HOST, "/")
        dest_host, dest_port = resolve_mock_address(MOCK_HOST)
        outer, _ = self.client.build_layers(path, dest_host, dest_port, raw)

        wrong = path[1]  # sealed for path[0], sent to path[1]
        with self.assertRaises(HttpError) as caught:
            post_json(f"http://{wrong.host}:{wrong.port}/relay", outer, timeout=5)
        self.assertEqual(caught.exception.status, 400)

    def test_empty_and_non_object_bodies_are_refused(self):
        entry = self._entry()
        for body in ({}, [], "string"):
            with self.assertRaises(HttpError) as caught:
                post_json(f"http://{entry.host}:{entry.port}/relay", body, timeout=5)
            self.assertEqual(caught.exception.status, 400)

    def test_unknown_endpoints_return_404(self):
        entry = self._entry()
        with self.assertRaises(HttpError) as caught:
            get_json(f"http://{entry.host}:{entry.port}/admin", timeout=5)
        self.assertEqual(caught.exception.status, 404)

    def test_the_relay_still_works_after_being_fed_garbage(self):
        """A malformed message must not take a relay down."""
        entry = self._entry()
        try:
            post_json(
                f"http://{entry.host}:{entry.port}/relay", {"junk": True}, timeout=5
            )
        except HttpError:
            pass
        path = self.client.get_path(3)
        body = self.client.get(path, MOCK_HOST, "/")
        self.assertIn(b"phase1-endpoint-ok", body)


# ---------------------------------------------------------------------------
# 12. Relay failure produces a controlled error
# ---------------------------------------------------------------------------


class TestFailureHandling(Phase1TestCase):
    def test_unreachable_entry_relay_raises_a_named_error(self):
        path = self.client.get_path(3)
        broken = [Hop("relay-dead", "127.0.0.1", free_port(), path[0].public_key)] + path[1:]
        with self.assertRaises(OnionPathError) as caught:
            self.client.get(broken, MOCK_HOST, "/")
        self.assertIn("relay-dead", str(caught.exception))
        self.assertIn("unreachable", str(caught.exception))

    def test_unreachable_middle_relay_raises_a_controlled_error(self):
        """IMPLEMENTATION_PLAN.md Phase 3 criterion 6: a clear named error, no hang."""
        path = self.client.get_path(3)
        broken = list(path)
        broken[1] = Hop(
            path[1].relay_id, "127.0.0.1", free_port(), path[1].public_key
        )
        with self.assertRaises(OnionPathError) as caught:
            self.client.get(broken, MOCK_HOST, "/")
        message = str(caught.exception)
        self.assertIn("next_hop_unreachable", message)
        # SD-011: the entry relay reports itself, never a hop further down.
        self.assertIn(f"reported_by={path[0].relay_id}", message)
        self.assertNotIn(path[2].relay_id, message)

    def test_unreachable_destination_raises_a_controlled_error(self):
        path = self.client.get_path(2)
        raw = build_raw_request(MOCK_HOST, "/")
        outer, keys = self.client.build_layers(path, "127.0.0.1", free_port(), raw)
        with self.assertRaises(OnionPathError):
            envelope = self.client.send(path, outer)
            self.client.unwrap(envelope, keys)

    def test_directory_unreachable_fails_with_a_clear_error(self):
        """RELAY_PROTOCOL.md section 9: no cached fallback path."""
        from client.onion_client import OnionClient

        stranded = OnionClient(f"http://127.0.0.1:{free_port()}", timeout=2)
        with self.assertRaises(DirectoryError):
            stranded.get_path(3)


# ---------------------------------------------------------------------------
# 13. The sealed error protocol -- SD-024 as amended by SD-029 and SD-030
# ---------------------------------------------------------------------------


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _post_raw(url: str, payload: dict) -> tuple[int, str, dict]:
    """POST and return ``(status, content_type, body)`` without raising.

    ``post_json`` raises on a non-2xx, which hides the status and headers that
    RELAY_PROTOCOL.md section 9.3 pins down.  These tests need both.
    """
    import urllib.error
    import urllib.request

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, method="POST", headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.headers.get("Content-Type", ""), json.loads(
                response.read()
            )
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type", ""), json.loads(exc.read())


class SealedProtocolTestCase(Phase1TestCase):
    """Helpers for hand-building layers the client would never build."""

    def _relay_url(self, hop: Hop) -> str:
        return f"http://{hop.host}:{hop.port}/relay"

    def _seal_to(self, hop: Hop, layer: dict) -> tuple[dict, bytes]:
        return seal_layer(layer, load_public_key(hop.public_key))

    def _layer(self, **overrides) -> dict:
        """A structurally complete layer, with fields overridable.

        Built by hand rather than with ``build_layer`` because that helper
        coerces ``next_port`` with ``int()``, which is precisely what SD-030
        exists to stop a relay from doing.
        """
        layer = {
            "next_hop": "DESTINATION",
            "next_host": "127.0.0.1",
            "next_port": 9,
            "payload": _b64(b"unused"),
        }
        layer.update(overrides)
        return layer

    def _sealed_reply(self, hop: Hop, layer: dict) -> dict:
        """Send ``layer`` to ``hop`` and return its decrypted typed content."""
        wire, key = self._seal_to(hop, layer)
        status, content_type, envelope = _post_raw(self._relay_url(hop), wire)
        self.assertEqual(200, status, "a sealed reply must travel with HTTP 200")
        self.assertIn("application/json", content_type)
        return json.loads(open_response(envelope, key).decode("utf-8"))


class TestPlaintextFallback(SealedProtocolTestCase):
    """SD-029 / section 9.3 -- the one case a relay answers in plaintext."""

    def _fallback(self, hop: Hop, wire: dict) -> tuple[int, str, dict]:
        return _post_raw(self._relay_url(hop), wire)

    def test_undecryptable_layer_gives_400_json_with_exactly_two_fields(self):
        entry = self.client.get_path(2)[0]
        status, content_type, body = self._fallback(
            entry, {"enc_key": "!!!", "nonce": "!!!", "ciphertext": "!!!"}
        )
        self.assertEqual(400, status)
        self.assertIn("application/json", content_type)
        self.assertEqual({"error", "reported_by"}, set(body))
        self.assertEqual("decryption_failure", body["error"])
        self.assertEqual(entry.relay_id, body["reported_by"])
        self.assertIsInstance(body["error"], str)
        self.assertIsInstance(body["reported_by"], str)

    def test_a_tampered_layer_is_a_decryption_failure_not_an_unusable_layer(self):
        """SD-030 must not swallow SD-029's case.

        A flipped ciphertext byte fails the AES-GCM tag, so the relay never
        holds a usable key and cannot seal.  It must take the plaintext path.
        """
        entry = self.client.get_path(2)[0]
        wire, _ = self._seal_to(entry, self._layer())
        raw = bytearray(base64.b64decode(wire["ciphertext"]))
        raw[0] ^= 0x01
        wire["ciphertext"] = _b64(bytes(raw))

        status, _, body = self._fallback(entry, wire)
        self.assertEqual(400, status)
        self.assertEqual("decryption_failure", body["error"])

    def test_the_fallback_body_carries_no_diagnostics(self):
        entry = self.client.get_path(2)[0]
        _, _, body = self._fallback(
            entry, {"enc_key": "!!!", "nonce": "!!!", "ciphertext": "!!!"}
        )
        text = json.dumps(body)
        for leak in (
            "base64",
            "Traceback",
            "InvalidTag",
            "authentication",
            "session key",
            "nonce",
            "ciphertext",
            "enc_key",
            "request_id",
        ):
            self.assertNotIn(leak, text, f"the fallback body leaked {leak!r}")

    def test_the_fallback_names_no_relay_but_the_one_answering(self):
        path = self.client.get_path(3)
        _, _, body = self._fallback(
            path[0], {"enc_key": "!!!", "nonce": "!!!", "ciphertext": "!!!"}
        )
        text = json.dumps(body)
        for other in path[1:]:
            self.assertNotIn(other.relay_id, text)

    def test_a_predecessor_converts_the_fallback_into_its_own_sealed_error(self):
        """Section 9.3: the plaintext travels exactly one hop.

        B is handed a layer sealed to the wrong key, so B answers A in
        plaintext.  A must not forward that: it emits its own sealed error, and
        must not name B.
        """
        path = self.client.get_path(2)
        entry, second = path[0], path[1]

        # Sealed to the entry relay's key but addressed to the second, so the
        # second relay cannot open it.
        undecryptable, _ = self._seal_to(entry, self._layer())
        outer = self._layer(
            next_hop=second.relay_id,
            next_host=second.host,
            next_port=second.port,
            payload=_b64(json.dumps(undecryptable).encode("utf-8")),
        )
        content = self._sealed_reply(entry, outer)

        self.assertEqual("error", content["type"])
        self.assertEqual("decryption_failure", content["code"])
        self.assertEqual(entry.relay_id, content["reported_by"])
        self.assertNotIn(second.relay_id, json.dumps(content))

    def test_entry_relay_fallback_reaches_the_client_as_a_protocol_error(self):
        path = self.client.get_path(2)
        # Sealed for the second relay, sent to the first: the entry cannot open it.
        wire, _ = self._seal_to(path[1], self._layer())
        with self.assertRaises(OnionRelayError) as caught:
            self.client.send(path, wire)
        error = caught.exception
        self.assertEqual("decryption_failure", error.code)
        self.assertEqual(path[0].relay_id, error.reported_by)
        self.assertFalse(error.sealed)
        self.assertNotIn(path[1].relay_id, str(error))


class TestUnusableLayer(SealedProtocolTestCase):
    """SD-030 / section 9.1 -- decrypted, authenticated, and unusable."""

    def test_non_integer_next_port_produces_a_sealed_unusable_layer(self):
        entry = self.client.get_path(2)[0]
        content = self._sealed_reply(entry, self._layer(next_port="eighty"))
        self.assertEqual(
            {"type": "error", "code": "unusable_layer", "reported_by": entry.relay_id},
            content,
        )

    def test_a_float_port_is_not_silently_truncated(self):
        """``int(8080.9)`` is 8080.  A relay must not act on that."""
        entry = self.client.get_path(2)[0]
        content = self._sealed_reply(entry, self._layer(next_port=8080.9))
        self.assertEqual("unusable_layer", content["code"])

    def test_a_boolean_port_is_not_silently_coerced(self):
        """``int(True)`` is 1, and ``bool`` is a subclass of ``int``."""
        entry = self.client.get_path(2)[0]
        content = self._sealed_reply(entry, self._layer(next_port=True))
        self.assertEqual("unusable_layer", content["code"])

    def test_undecodable_payload_produces_a_sealed_unusable_layer(self):
        entry = self.client.get_path(2)[0]
        content = self._sealed_reply(entry, self._layer(payload="!!! not base64 !!!"))
        self.assertEqual("unusable_layer", content["code"])
        self.assertEqual(entry.relay_id, content["reported_by"])

    def test_the_sealed_error_carries_exactly_three_fields_and_no_diagnostics(self):
        entry = self.client.get_path(2)[0]
        content = self._sealed_reply(entry, self._layer(next_port="eighty"))
        self.assertEqual({"type", "code", "reported_by"}, set(content))
        text = json.dumps(content)
        for leak in ("next_port", "eighty", "Traceback", "payload", "request_id"):
            self.assertNotIn(leak, text)

    def test_an_intermediate_relay_cannot_read_the_sealed_error(self):
        """Section 9.1 / E2: the error is opaque to every hop above it."""
        path = self.client.get_path(2)
        entry, second = path[0], path[1]

        inner_wire, inner_key = self._seal_to(second, self._layer(next_port="eighty"))
        outer = self._layer(
            next_hop=second.relay_id,
            next_host=second.host,
            next_port=second.port,
            payload=_b64(json.dumps(inner_wire).encode("utf-8")),
        )
        outer_wire, outer_key = self._seal_to(entry, outer)
        status, _, envelope = _post_raw(self._relay_url(entry), outer_wire)
        self.assertEqual(200, status)

        # What the entry relay sealed is an opaque relay wrapper.  The error is
        # not in it, and no amount of reading the entry's own layer reveals it.
        outer_content = json.loads(open_response(envelope, outer_key).decode("utf-8"))
        self.assertEqual("relay", outer_content["type"])
        self.assertNotIn("unusable_layer", json.dumps(outer_content))
        self.assertNotIn(second.relay_id, json.dumps(outer_content))

        # Only the key the entry relay never had opens it.
        nested = json.loads(base64.b64decode(outer_content["inner"]).decode("utf-8"))
        inner_content = json.loads(open_response(nested, inner_key).decode("utf-8"))
        self.assertEqual("unusable_layer", inner_content["code"])
        self.assertEqual(second.relay_id, inner_content["reported_by"])


class TestTypedResponses(SealedProtocolTestCase):
    """Section 7: success and error travel under identical layers."""

    def test_a_normal_request_still_returns_the_page_unchanged(self):
        """SD-029 and SD-030 must not disturb the successful path."""
        path = self.client.get_path(3)
        body, trace = self.client.get_with_trace(path, MOCK_HOST, "/")
        self.assertIn(b"phase1-endpoint-ok", body)
        self.assertIn(PAGE.strip(), body)
        self.assertEqual(3, len(trace.response_envelopes))
        for envelope in trace.response_envelopes:
            self.assertEqual({"nonce", "ciphertext"}, set(envelope))

    def test_a_relay_error_is_sealed_under_the_same_layers_as_a_success(self):
        path = self.client.get_path(3)
        broken = list(path)
        broken[1] = Hop(path[1].relay_id, "127.0.0.1", free_port(), path[1].public_key)
        raw = build_raw_request(MOCK_HOST, "/")
        dest_host, dest_port = resolve_mock_address(MOCK_HOST)
        outer, keys = self.client.build_layers(broken, dest_host, dest_port, raw)

        envelope = self.client.send(broken, outer)
        self.assertEqual({"nonce", "ciphertext"}, set(envelope))
        with self.assertRaises(OnionRelayError) as caught:
            self.client.unwrap(envelope, keys)
        self.assertEqual("next_hop_unreachable", caught.exception.code)
        self.assertTrue(caught.exception.sealed)

    def test_an_unreachable_destination_is_reported_as_such(self):
        """Section 9.1: the exit hop's failure is not `next_hop_unreachable`."""
        path = self.client.get_path(2)
        raw = build_raw_request(MOCK_HOST, "/")
        outer, keys = self.client.build_layers(path, "127.0.0.1", free_port(), raw)
        envelope = self.client.send(path, outer)
        with self.assertRaises(OnionRelayError) as caught:
            self.client.unwrap(envelope, keys)
        self.assertEqual("destination_unreachable", caught.exception.code)

    def test_a_malformed_response_is_a_client_side_condition(self):
        """Section 9.2 row 3: not a relay-reported protocol error."""
        path = self.client.get_path(2)
        _, keys = self.client.build_layers(
            path, "127.0.0.1", 9, build_raw_request(MOCK_HOST, "/")
        )
        with self.assertRaises(OnionProtocolError):
            self.client.unwrap({"nonce": "!!!", "ciphertext": "!!!"}, keys)


# ---------------------------------------------------------------------------
# 14. OPEN-9 closure evidence -- CONSOLIDATED_FREEZE_REVIEW.md section 11
# ---------------------------------------------------------------------------


class ErrorPathTestCase(Phase1TestCase):
    """A deliberately broken path, and the sealed error that comes back.

    Breaking the *last* hop's address rather than a middle one means the error
    is sealed by the second-to-last relay and the client has to unwrap every
    relay layer above it before reaching a terminal type.  That is what makes
    these tests say something at 4 and 5 hops that they do not say at 2.
    """

    def _broken_at_the_exit(self, hops: int):
        """Return ``(path, outer_layer, session_keys, detector, broken)``."""
        path = self.client.get_path(hops)
        broken = path[-1]
        path = list(path[:-1]) + [
            Hop(broken.relay_id, "127.0.0.1", free_port(), broken.public_key)
        ]
        dest_host, dest_port = resolve_mock_address(MOCK_HOST)
        outer, keys = self.client.build_layers(
            path, dest_host, dest_port, build_raw_request(MOCK_HOST, "/")
        )
        return path, outer, keys, path[-2], path[-1]

    def _peel_error(self, envelope: dict, keys: list[bytes]) -> tuple[dict, list[dict]]:
        """Unwrap by hand, returning ``(terminal_content, envelopes_seen)``.

        ``unwrap`` raises on a terminal error, which discards the envelopes --
        and the envelopes are exactly what the nonce test needs to inspect.
        """
        envelopes: list[dict] = []
        current = envelope
        for key in keys:
            envelopes.append(current)
            content = json.loads(open_response(current, key).decode("utf-8"))
            if content["type"] != "relay":
                return content, envelopes
            current = json.loads(
                base64.b64decode(content["inner"]).decode("utf-8")
            )
        raise AssertionError("the response never reached a terminal type")


class TestSealedErrorAtEveryPathLength(ErrorPathTestCase):
    """Review section 11 test 1 -- a sealed error opened at hops=2..5.

    Two and three hops are already covered by
    `TestTypedResponses.test_an_unreachable_destination_is_reported_as_such`
    and `test_a_relay_error_is_sealed_under_the_same_layers_as_a_success`;
    this adds the two lengths those do not reach, and re-asserts 2 and 3 here
    so the full range lives in one place.
    """

    def test_the_client_opens_a_sealed_error_at_two_through_five_hops(self):
        for hops in (2, 3, 4, 5):
            with self.subTest(hops=hops):
                path, outer, keys, detector, broken = self._broken_at_the_exit(hops)
                self.assertEqual(hops, len(keys))

                envelope = self.client.send(path, outer)
                self.assertEqual({"nonce", "ciphertext"}, set(envelope))

                with self.assertRaises(OnionRelayError) as caught:
                    self.client.unwrap(envelope, keys)
                error = caught.exception

                # Correctly typed, and from the closed set of four.
                self.assertEqual("next_hop_unreachable", error.code)
                self.assertTrue(error.sealed)

                # Attributed to the relay that actually detected the failure --
                # the hop before the broken one, not the entry relay and not
                # the broken relay itself (SD-011, section 9.4).
                self.assertEqual(detector.relay_id, error.reported_by)
                self.assertNotIn(broken.relay_id, str(error))

    def test_the_error_survives_the_full_depth_of_relay_layers(self):
        """The terminal error is reached by unwrapping, not by counting."""
        path, outer, keys, detector, broken = self._broken_at_the_exit(5)
        envelope = self.client.send(path, outer)
        content, envelopes = self._peel_error(envelope, keys)

        # Four relays sealed something: three `relay` wrappers above the error.
        self.assertEqual(4, len(envelopes))
        self.assertEqual(
            {"type": "error", "code": "next_hop_unreachable",
             "reported_by": detector.relay_id},
            content,
        )
        self.assertNotIn(broken.relay_id, json.dumps(content))


class TestNonceDisciplineOnTheErrorPath(ErrorPathTestCase):
    """Review section 11 test 6 -- fresh nonces on error layers too.

    Section 7's rule has no exception for errors, and the error return path is
    newly written code, so a nonce mistake here would be novel rather than
    inherited from the success path.
    """

    def test_every_error_layer_uses_a_fresh_unique_nonce(self):
        path, outer, keys, _, _ = self._broken_at_the_exit(5)
        envelope = self.client.send(path, outer)
        _, envelopes = self._peel_error(envelope, keys)

        nonces = [env["nonce"] for env in envelopes]
        self.assertEqual(4, len(nonces))
        self.assertEqual(
            len(nonces), len(set(nonces)), "a nonce was reused across error layers"
        )
        for nonce in nonces:
            self.assertEqual(
                NONCE_BYTES,
                len(base64.b64decode(nonce)),
                "an error layer used a nonce that is not 96 bits",
            )

    def test_error_layer_nonces_never_reuse_a_forward_nonce(self):
        """The return leg reuses K, so the nonce is the whole defence."""
        path, outer, keys, _, _ = self._broken_at_the_exit(4)
        forward = set(self.harness.request_layer_nonces(outer, path))
        envelope = self.client.send(path, outer)
        _, envelopes = self._peel_error(envelope, keys)

        returned = {env["nonce"] for env in envelopes}
        self.assertTrue(forward, "no forward nonces were captured")
        self.assertFalse(
            forward & returned,
            "a nonce was reused between the forward leg and an error layer",
        )

    def test_error_layer_nonces_do_not_repeat_across_runs(self):
        seen: set[str] = set()
        for _ in range(3):
            path, outer, keys, _, _ = self._broken_at_the_exit(3)
            envelope = self.client.send(path, outer)
            _, envelopes = self._peel_error(envelope, keys)
            nonces = {env["nonce"] for env in envelopes}
            self.assertFalse(seen & nonces, "an error-layer nonce repeated")
            seen |= nonces


class TestLogHygieneOnTheErrorPath(ErrorPathTestCase):
    """Review section 11 test 7 -- section 8's rules hold when things break.

    The error path is the branch that actually has diagnostics to leak: it is
    the only place a relay holds an exception describing what went wrong.
    """

    def test_the_error_path_leaks_no_keys_nonces_ciphertext_or_payload(self):
        path, outer, keys, _, _ = self._broken_at_the_exit(4)
        with LogCapture() as capture:
            envelope = self.client.send(path, outer)
            _, envelopes = self._peel_error(envelope, keys)
        logs = capture.text

        self.assertIn("unreachable", logs, "the failure was not logged at all")

        self.assertNotIn("PRIVATE KEY", logs)
        for node in self.harness.nodes.values():
            self.assertNotIn(node.public_pem.strip(), logs)
        for key in keys:
            self.assertNotIn(base64.b64encode(key).decode(), logs)
        for nonce in self.harness.request_layer_nonces(outer, path):
            self.assertNotIn(nonce, logs)
        for env in envelopes:
            self.assertNotIn(env["nonce"], logs)
            self.assertNotIn(env["ciphertext"], logs)
        self.assertNotIn(outer["ciphertext"], logs)
        self.assertNotIn(PAGE.strip().decode(), logs)

    def test_the_error_path_leaks_neither_the_destination_nor_the_full_path(self):
        """Section 8: log the next hop only.

        Checked structurally rather than by keyword: every relay id appearing
        on a log line must be either the relay writing it or that relay's own
        successor.  A relay naming any other hop would mean the path leaked
        into a log, which is what section 6's isolation claim rests on.
        """
        path, outer, keys, _, broken = self._broken_at_the_exit(4)
        dest_host, dest_port = resolve_mock_address(MOCK_HOST)
        with LogCapture() as capture:
            envelope = self.client.send(path, outer)
            self._peel_error(envelope, keys)
        logs = capture.text

        # The destination never appears, in any form.
        self.assertNotIn(dest_host, logs)
        self.assertNotIn(f":{dest_port}", logs)
        self.assertNotIn(str(broken.port), logs)
        self.assertNotIn(MOCK_HOST, logs)

        successor = {
            path[i].relay_id: path[i + 1].relay_id for i in range(len(path) - 1)
        }
        known = {hop.relay_id for hop in path}
        for line in logs.splitlines():
            if not line.startswith("[") or "]" not in line:
                continue
            speaker = line[1 : line.index("]")]
            if speaker not in known:
                continue
            allowed = {speaker, successor.get(speaker)}
            for other in known:
                if other in allowed:
                    continue
                with self.subTest(speaker=speaker, other=other):
                    self.assertNotIn(
                        other, line, f"{speaker} logged a hop that is not its own"
                    )


if __name__ == "__main__":
    unittest.main()
