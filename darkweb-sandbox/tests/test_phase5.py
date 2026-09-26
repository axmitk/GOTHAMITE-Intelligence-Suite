"""Phase-5 verification: the scraper agent.

Coverage maps to `AgentsDocs/SCRAPER_AGENT_SPEC.md` section 8 and to
`AgentsDocs/API_CONTRACT.md` sections 3, 4 and 6.

The crawl in `setUpModule` is a real one: real relays, a real directory, the
real mock sites, and the real client, all on loopback.  Nothing is stubbed
except the far side of the ingestion seam, which does not exist yet -- and that
stub lives in `tests/ingest_receiver.py`, is never imported by `scraper/`, and
is not an implementation of GOTHAMITE.

Nothing here contacts the network.
"""

from __future__ import annotations

import ast
import hashlib
import pathlib
import re
import unittest
from urllib.parse import urlsplit

from scraper import contract, extract
from scraper.scraper_agent import SOURCES, Outcome, ScraperAgent
from tests import ingest_receiver
from tests.harness import SandboxHarness, free_port

# --- what the corpus should yield, written out by hand ----------------------
# Measured from the Phase-4 corpus and stated here as literals so a silent
# change to the corpus fails a test rather than moving the expectation with it.

EXPECTED_ARTIFACTS = 57
EXPECTED_BY_TYPE = {"index": 3, "item": 48, "profile": 6}
EXPECTED_PGP = 13
EXPECTED_WALLET = 16
EXPECTED_PERSONAS = 6
EXPECTED_SOURCES = 3
EXPECTED_PER_SOURCE = {"index": 1, "item": 16, "profile": 2}

TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

HARNESS: SandboxHarness | None = None
RECEIVER: ingest_receiver.IngestReceiver | None = None
SUMMARY = None
PAYLOADS: list[dict] = []


def setUpModule() -> None:  # noqa: N802
    """One clean run of the whole scraper, shared by every test below."""
    global HARNESS, RECEIVER, SUMMARY
    HARNESS = SandboxHarness(relay_count=7, with_sites=True)
    HARNESS.start()
    RECEIVER = ingest_receiver.IngestReceiver().start()

    agent = ScraperAgent(
        HARNESS.client(),
        ingest_url=RECEIVER.url,
        hops=3,
        timeout=10.0,
        pause=0.0,  # the 0.5s demo pause would add half a minute to the suite
    )
    SUMMARY = agent.run()
    PAYLOADS.extend(agent.payloads)


def tearDownModule() -> None:  # noqa: N802
    if RECEIVER is not None:
        RECEIVER.stop()
    if HARNESS is not None:
        HARNESS.stop()


def of_type(page_type: str) -> list[dict]:
    return [p for p in PAYLOADS if p["page_type"] == page_type]


# ---------------------------------------------------------------------------
# 1. Discovery and crawling
# ---------------------------------------------------------------------------


class TestCrawl(unittest.TestCase):
    def test_all_three_sources_were_crawled_through_the_relay_chain(self):
        self.assertEqual(EXPECTED_SOURCES, SUMMARY.sources_attempted)
        self.assertEqual(
            {source["source_id"] for source in SOURCES},
            {p["source_id"] for p in PAYLOADS},
        )
        for source_id, path in SUMMARY.relay_paths.items():
            with self.subTest(source=source_id):
                self.assertEqual(3, len(path), "every fetch used a full 3-hop path")
                self.assertEqual(3, len(set(path)), "a relay repeated within one path")

    def test_the_expected_corpus_was_discovered(self):
        self.assertEqual(EXPECTED_ARTIFACTS, SUMMARY.pages_fetched)
        self.assertEqual(EXPECTED_ARTIFACTS, len(PAYLOADS))
        self.assertEqual(EXPECTED_ARTIFACTS, SUMMARY.artifacts_sent)

    def test_page_types_are_classified_correctly(self):
        counts = {kind: len(of_type(kind)) for kind in EXPECTED_BY_TYPE}
        self.assertEqual(EXPECTED_BY_TYPE, counts)
        for payload in PAYLOADS:
            route = urlsplit(payload["url"]).path
            with self.subTest(url=payload["url"]):
                self.assertEqual(extract.classify(route), payload["page_type"])

    def test_every_source_yielded_the_same_shape(self):
        for source in SOURCES:
            counts = {
                kind: len(
                    [
                        p
                        for p in of_type(kind)
                        if p["source_id"] == source["source_id"]
                    ]
                )
                for kind in EXPECTED_BY_TYPE
            }
            with self.subTest(source=source["source_id"]):
                self.assertEqual(EXPECTED_PER_SOURCE, counts)

    def test_exactly_one_index_artifact_per_source(self):
        for source in SOURCES:
            matching = [
                p for p in of_type("index") if p["source_id"] == source["source_id"]
            ]
            with self.subTest(source=source["source_id"]):
                self.assertEqual(1, len(matching))
                self.assertEqual("/", urlsplit(matching[0]["url"]).path)

    def test_only_hardcoded_route_shapes_were_visited(self):
        for payload in PAYLOADS:
            route = urlsplit(payload["url"]).path
            with self.subTest(route=route):
                self.assertTrue(
                    route == "/"
                    or extract.ITEM_ROUTE.match(route)
                    or extract.PROFILE_ROUTE.match(route),
                    "a route outside the hardcoded structure was fetched",
                )


# ---------------------------------------------------------------------------
# 2. Extraction
# ---------------------------------------------------------------------------


class TestExtraction(unittest.TestCase):
    def test_identifier_totals_match_the_corpus(self):
        self.assertEqual(EXPECTED_PGP, SUMMARY.pgp)
        self.assertEqual(EXPECTED_WALLET, SUMMARY.wallet)
        emitted = [i for p in PAYLOADS for i in p["identifiers"]]
        self.assertEqual(EXPECTED_PGP + EXPECTED_WALLET, len(emitted))

    def test_fingerprints_are_uppercase_hex_with_no_whitespace(self):
        for payload in PAYLOADS:
            for entry in payload["identifiers"]:
                if entry["type"] != "pgp_fingerprint":
                    continue
                with self.subTest(url=payload["url"]):
                    self.assertRegex(entry["value"], r"^[0-9A-F]{40}$")
                    self.assertEqual(entry["value"], entry["value"].strip())

    def test_wallets_are_verbatim_and_pass_the_validation_rule(self):
        for payload in PAYLOADS:
            for entry in payload["identifiers"]:
                if entry["type"] != "wallet":
                    continue
                value = entry["value"]
                with self.subTest(value=value):
                    self.assertIn(value, payload["raw_content"], "wallet not verbatim")
                    self.assertTrue(26 <= len(value) <= 35)
                    self.assertFalse(set(value) & set("0OIl"))
                    self.assertRegex(value, r"^[13][a-km-zA-HJ-NP-Z1-9]+$")

    def test_no_handle_or_contact_identifier_is_ever_emitted(self):
        """SD-022: a handle travels in `persona.handle`, never as an identifier."""
        self.assertEqual(0, SUMMARY.handles)
        for payload in PAYLOADS:
            for entry in payload["identifiers"]:
                with self.subTest(url=payload["url"]):
                    self.assertIn(entry["type"], {"pgp_fingerprint", "wallet"})

    def test_every_identifier_carries_its_items_own_timestamp(self):
        for payload in of_type("item"):
            expected = payload["persona"]["observed_at"]
            for entry in payload["identifiers"]:
                with self.subTest(url=payload["url"]):
                    self.assertEqual(expected, entry["observed_at"])
                    self.assertRegex(entry["observed_at"], TIMESTAMP_RE)

    def test_index_and_profile_artifacts_carry_no_identifiers(self):
        for payload in of_type("index") + of_type("profile"):
            with self.subTest(url=payload["url"]):
                self.assertEqual([], payload["identifiers"])

    def test_persona_follows_the_page_type_matrix(self):
        for payload in of_type("index"):
            with self.subTest(url=payload["url"]):
                self.assertNotIn("persona", payload)
        for payload in of_type("item"):
            with self.subTest(url=payload["url"]):
                self.assertIn("handle", payload["persona"])
                self.assertIn("observed_at", payload["persona"])
        for payload in of_type("profile"):
            with self.subTest(url=payload["url"]):
                self.assertIn("handle", payload["persona"])
                self.assertNotIn(
                    "observed_at",
                    payload["persona"],
                    "a profile has no post timestamp and none may be substituted",
                )

    def test_six_personas_are_found_and_no_seventh_is_invented(self):
        personas = {
            (p["persona"]["handle"], p["source_id"])
            for p in PAYLOADS
            if "persona" in p
        }
        self.assertEqual(EXPECTED_PERSONAS, len(personas))

    def test_identifiers_are_attributed_to_the_page_they_came_from(self):
        """SD-028: attribution is page-local, and the page names its author."""
        for payload in of_type("item"):
            line = extract.byline(payload["raw_content"])
            with self.subTest(url=payload["url"]):
                self.assertIsNotNone(line)
                self.assertEqual(line.handle, payload["persona"]["handle"])
                for entry in payload["identifiers"]:
                    self.assertIn(
                        entry["value"].replace(" ", ""),
                        payload["raw_content"].replace(" ", ""),
                        "an identifier was attributed to a page it is not on",
                    )

    def test_a_profile_persona_comes_from_its_own_route(self):
        for payload in of_type("profile"):
            route = urlsplit(payload["url"]).path
            with self.subTest(url=payload["url"]):
                self.assertEqual(
                    extract.profile_handle(route), payload["persona"]["handle"]
                )


# ---------------------------------------------------------------------------
# 3. Payload construction
# ---------------------------------------------------------------------------


class TestPayload(unittest.TestCase):
    def test_every_payload_passes_local_contract_validation(self):
        for payload in PAYLOADS:
            with self.subTest(url=payload["url"]):
                self.assertEqual([], contract.validate(payload))

    def test_required_fields_are_present_on_every_artifact(self):
        required = {
            "source_id",
            "source_type",
            "page_type",
            "url",
            "collected_at",
            "relay_path",
            "raw_content",
            "content_hash",
            "identifiers",
        }
        for payload in PAYLOADS:
            with self.subTest(url=payload["url"]):
                self.assertTrue(required <= set(payload))

    def test_urls_are_canonical_absolute_mock_urls(self):
        for payload in PAYLOADS:
            url = payload["url"]
            parts = urlsplit(url)
            with self.subTest(url=url):
                self.assertEqual("http", parts.scheme)
                self.assertTrue(parts.netloc.endswith(".onion.mock"))
                self.assertTrue(parts.path.startswith("/"))
                self.assertEqual("", parts.query)
                self.assertEqual("", parts.fragment)

    def test_the_index_url_keeps_its_trailing_slash(self):
        for payload in of_type("index"):
            with self.subTest(url=payload["url"]):
                self.assertTrue(payload["url"].endswith(".onion.mock/"))

    def test_timestamps_are_utc_with_a_z_suffix(self):
        for payload in PAYLOADS:
            with self.subTest(url=payload["url"]):
                self.assertRegex(payload["collected_at"], TIMESTAMP_RE)

    def test_collected_at_differs_from_observed_at(self):
        """The distinction the rebrand signal depends on."""
        for payload in of_type("item"):
            with self.subTest(url=payload["url"]):
                self.assertNotEqual(
                    payload["collected_at"], payload["persona"]["observed_at"]
                )

    def test_content_hash_is_sha256_of_raw_content(self):
        for payload in PAYLOADS:
            expected = hashlib.sha256(
                payload["raw_content"].encode("utf-8")
            ).hexdigest()
            with self.subTest(url=payload["url"]):
                self.assertEqual(f"sha256:{expected}", payload["content_hash"])

    def test_raw_content_is_the_page_verbatim(self):
        for payload in PAYLOADS:
            raw = payload["raw_content"]
            with self.subTest(url=payload["url"]):
                self.assertTrue(raw.startswith("<!DOCTYPE html>"))
                self.assertTrue(raw.rstrip().endswith("</html>"))
                self.assertNotIn("HTTP/1.0", raw)
                self.assertNotIn("Content-Length:", raw)

    def test_relay_path_is_populated_with_real_relay_ids(self):
        known = {node.relay_id for node in HARNESS.nodes.values()}
        for payload in PAYLOADS:
            with self.subTest(url=payload["url"]):
                self.assertEqual(3, len(payload["relay_path"]))
                self.assertTrue(set(payload["relay_path"]) <= known)

    def test_source_identity_matches_the_hardcoded_source_list(self):
        by_host = {s["host"]: s for s in SOURCES}
        for payload in PAYLOADS:
            host = urlsplit(payload["url"]).netloc
            with self.subTest(url=payload["url"]):
                self.assertEqual(by_host[host]["source_id"], payload["source_id"])
                self.assertEqual(by_host[host]["source_type"], payload["source_type"])

    def test_one_payload_per_artifact_and_no_batching(self):
        urls = [p["url"] for p in PAYLOADS]
        self.assertEqual(len(urls), len(set(urls)), "a page was scraped twice")
        self.assertEqual(len(PAYLOADS), len(RECEIVER.received))

    def test_no_two_artifacts_from_one_source_share_a_content_hash(self):
        seen: set[tuple[str, str]] = set()
        for payload in PAYLOADS:
            key = (payload["source_id"], payload["content_hash"])
            with self.subTest(url=payload["url"]):
                self.assertNotIn(key, seen)
            seen.add(key)


# ---------------------------------------------------------------------------
# 4. Delivery -- the section 4 / section 6 failure matrix
# ---------------------------------------------------------------------------


class TestDelivery(unittest.TestCase):
    """Each branch exercised against the test receiver, one payload at a time."""

    def _agent(self, url: str) -> ScraperAgent:
        return ScraperAgent(
            HARNESS.client(), ingest_url=url, timeout=3.0, pause=0.0, backoff=0.01
        )

    def _payload(self) -> dict:
        return dict(PAYLOADS[0])

    def test_a_2xx_is_accepted(self):
        with ingest_receiver.IngestReceiver() as receiver:
            errors: list[str] = []
            outcome = self._agent(receiver.url).deliver(self._payload(), errors)
        self.assertEqual(Outcome.ACCEPTED, outcome)
        self.assertEqual([], errors)

    def test_a_duplicate_is_counted_as_duplicate_not_an_error(self):
        responder = ingest_receiver.duplicate_after_first(set())
        with ingest_receiver.IngestReceiver(responder) as receiver:
            agent = self._agent(receiver.url)
            errors: list[str] = []
            first = agent.deliver(self._payload(), errors)
            second = agent.deliver(self._payload(), errors)
        self.assertEqual(Outcome.ACCEPTED, first)
        self.assertEqual(Outcome.DUPLICATE, second)
        self.assertEqual([], errors, "a duplicate is expected, not an error")

    def test_a_400_is_logged_and_the_artifact_skipped(self):
        body = {"accepted": False, "errors": ["identifiers[0].value: invalid"]}
        with ingest_receiver.IngestReceiver(
            ingest_receiver.always(400, body)
        ) as receiver:
            errors: list[str] = []
            outcome = self._agent(receiver.url).deliver(self._payload(), errors)
            attempts = receiver.attempts
        self.assertEqual(Outcome.REJECTED, outcome)
        self.assertEqual(1, attempts, "a 400 must not be retried")
        self.assertEqual(1, len(errors))

    def test_a_5xx_is_retried_twice_and_then_succeeds(self):
        with ingest_receiver.IngestReceiver(
            ingest_receiver.fail_then_accept(2)
        ) as receiver:
            errors: list[str] = []
            outcome = self._agent(receiver.url).deliver(self._payload(), errors)
            attempts = receiver.attempts
        self.assertEqual(Outcome.ACCEPTED, outcome)
        self.assertEqual(3, attempts, "one attempt plus two retries")

    def test_a_persistent_5xx_gives_up_after_the_retries(self):
        with ingest_receiver.IngestReceiver(
            ingest_receiver.always(503, {"error": "unavailable"})
        ) as receiver:
            errors: list[str] = []
            outcome = self._agent(receiver.url).deliver(self._payload(), errors)
            attempts = receiver.attempts
        self.assertEqual(Outcome.UNDELIVERED, outcome)
        self.assertEqual(3, attempts)
        self.assertEqual(1, len(errors))

    def test_an_unreachable_ingest_endpoint_does_not_raise(self):
        dead = f"http://127.0.0.1:{free_port()}/api/v1/ingest"
        errors: list[str] = []
        outcome = self._agent(dead).deliver(self._payload(), errors)
        self.assertEqual(Outcome.UNDELIVERED, outcome)
        self.assertIn("ingest unreachable", errors)

    def test_the_crawl_continues_after_an_individual_artifact_is_rejected(self):
        """Section 6: one failure never kills a run.

        One source is crawled with a receiver that rejects the third request.
        Every later page must still be fetched and delivered.
        """
        state = {"n": 0}

        def reject_the_third(payload: dict, ordinal: int):
            state["n"] += 1
            if state["n"] == 3:
                return 400, {"accepted": False, "errors": ["synthetic"]}
            return ingest_receiver.accept_all(payload, ordinal)

        with ingest_receiver.IngestReceiver(reject_the_third) as receiver:
            agent = self._agent(receiver.url)
            counts = {
                key: 0
                for key in ("pages", "sent", Outcome.ACCEPTED, Outcome.DUPLICATE,
                            Outcome.REJECTED, Outcome.UNDELIVERED, Outcome.INVALID,
                            "pgp", "wallet")
            }
            errors: list[str] = []
            agent._crawl(SOURCES[0], counts, {}, errors)  # noqa: SLF001

        expected_pages = sum(EXPECTED_PER_SOURCE.values())
        self.assertEqual(expected_pages, counts["pages"])
        self.assertEqual(expected_pages, counts["sent"])
        self.assertEqual(1, counts[Outcome.REJECTED])
        self.assertEqual(expected_pages - 1, counts[Outcome.ACCEPTED])


# ---------------------------------------------------------------------------
# 5. Safety and scope
# ---------------------------------------------------------------------------


SCRAPER_DIR = pathlib.Path(__file__).resolve().parent.parent / "scraper"


def scraper_sources() -> list[tuple[str, str]]:
    return [
        (path.name, path.read_text(encoding="utf-8"))
        for path in sorted(SCRAPER_DIR.glob("*.py"))
    ]


class TestSafetyAndScope(unittest.TestCase):
    def test_scraped_content_is_never_executed(self):
        """`MASTER_CONTEXT.md` section 3 rule 3, checked structurally."""
        banned = {"eval", "exec", "compile", "__import__", "system", "popen"}
        for name, source in scraper_sources():
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    with self.subTest(module=name, call=node.func.id):
                        self.assertNotIn(node.func.id, banned)

    def test_the_scraper_imports_no_dangerous_module(self):
        banned = {"subprocess", "pickle", "marshal", "shelve", "ctypes"}
        for name, source in scraper_sources():
            for node in ast.walk(ast.parse(source)):
                if isinstance(node, ast.Import):
                    names = {alias.name.split(".")[0] for alias in node.names}
                elif isinstance(node, ast.ImportFrom):
                    names = {(node.module or "").split(".")[0]}
                else:
                    continue
                with self.subTest(module=name):
                    self.assertFalse(names & banned)

    def test_out_of_scope_links_are_not_followed(self):
        html = (
            '<a href="http://example.com/thread/1">off-host</a>'
            '<a href="//evil.test/thread/2">protocol-relative</a>'
            '<a href="/admin">unknown shape</a>'
            '<a href="/thread/9">wanted</a>'
            '<a href="/user/someone">wanted</a>'
            '<a href="../../etc/passwd">traversal</a>'
        )
        self.assertEqual(["/thread/9", "/user/someone"], extract.discover_routes(html))

    def test_the_scraper_emits_no_relationship_or_score(self):
        """Correlation is GOTHAMITE's, after ingest (contract section 5 rule 3)."""
        forbidden = {
            "relationship",
            "relationships",
            "score",
            "confidence",
            "edge",
            "edges",
            "actor",
            "same_actor_suspected",
            "evidence",
        }
        for payload in PAYLOADS:
            with self.subTest(url=payload["url"]):
                self.assertFalse(set(payload) & forbidden)

    def test_no_scoring_or_correlation_logic_exists_in_the_scraper(self):
        """Checked over code, not prose.

        A substring scan is the wrong instrument here: these modules *talk*
        about correlation in order to say they do not perform it, and a grep
        cannot tell a disclaimer from an implementation.  So this walks the AST
        and looks at the names the code actually defines and calls, plus any
        numeric literal that could be a scoring weight.
        """
        banned = ("levenshtein", "similarity", "correlat", "score", "confidence")
        weights = {0.70, 0.45, 0.30, 0.15, 0.05, 0.95, 0.60}

        for name, source in scraper_sources():
            tree = ast.parse(source)
            for node in ast.walk(tree):
                identifier = None
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    identifier = node.name
                elif isinstance(node, ast.Name):
                    identifier = node.id
                elif isinstance(node, ast.Attribute):
                    identifier = node.attr
                if identifier is not None:
                    lowered = identifier.lower()
                    for term in banned:
                        with self.subTest(module=name, name=identifier, term=term):
                            self.assertNotIn(term, lowered)
                if isinstance(node, ast.Constant) and isinstance(node.value, float):
                    with self.subTest(module=name, value=node.value):
                        self.assertNotIn(
                            round(node.value, 2),
                            weights,
                            "a DATA_MODEL.md section 3 scoring weight appears in the scraper",
                        )

    def test_only_the_three_hardcoded_sources_can_be_reached(self):
        self.assertEqual(3, len(SOURCES))
        for source in SOURCES:
            with self.subTest(source=source["source_id"]):
                self.assertTrue(source["host"].endswith(".onion.mock"))

    def test_no_real_network_host_appears_in_the_scraper(self):
        for name, source in scraper_sources():
            with self.subTest(module=name):
                self.assertNotIn(".onion\"", source.replace(".onion.mock", ""))
                self.assertNotIn("https://", source)


# ---------------------------------------------------------------------------
# 6. The run summary -- section 7
# ---------------------------------------------------------------------------


class TestRunSummary(unittest.TestCase):
    def test_the_summary_reports_the_corpus_it_actually_scraped(self):
        rendered = SUMMARY.render()
        self.assertIn("=== SCRAPE RUN COMPLETE ===", rendered)
        self.assertIn(f"Sources attempted:      {EXPECTED_SOURCES}", rendered)
        self.assertIn(f"Pages fetched:          {EXPECTED_ARTIFACTS}", rendered)
        self.assertIn(
            f"Identifiers extracted:  PGP {EXPECTED_PGP} | "
            f"wallet {EXPECTED_WALLET} | handles 0",
            rendered,
        )

    def test_the_summary_names_the_relay_path_used_per_source(self):
        rendered = SUMMARY.render()
        for source_id, path in SUMMARY.relay_paths.items():
            with self.subTest(source=source_id):
                self.assertIn(source_id, rendered)
                self.assertIn(" -> ".join(path), rendered)

    def test_a_clean_run_reports_no_errors(self):
        self.assertEqual([], SUMMARY.errors)
        self.assertEqual(EXPECTED_ARTIFACTS, SUMMARY.accepted)
        self.assertEqual(0, SUMMARY.duplicate)
        self.assertEqual(0, SUMMARY.rejected)
        self.assertEqual(0, SUMMARY.undelivered)
        self.assertEqual(0, SUMMARY.invalid)


# ---------------------------------------------------------------------------
# 7. The local contract validator itself
# ---------------------------------------------------------------------------


class TestContractValidator(unittest.TestCase):
    """The validator must reject what the contract forbids, not just accept."""

    def _valid(self) -> dict:
        return dict(next(p for p in PAYLOADS if p["page_type"] == "item"))

    def test_a_missing_page_type_is_rejected(self):
        payload = self._valid()
        del payload["page_type"]
        self.assertTrue(any("page_type" in e for e in contract.validate(payload)))

    def test_a_scheme_less_url_is_rejected(self):
        payload = self._valid()
        payload["url"] = "alpha7fq2mx9k.onion.mock/thread/14"
        self.assertTrue(any("scheme" in e for e in contract.validate(payload)))

    def test_a_mismatched_content_hash_is_rejected(self):
        payload = self._valid()
        payload["content_hash"] = "sha256:" + "0" * 64
        self.assertTrue(any("content_hash" in e for e in contract.validate(payload)))

    def test_a_handle_identifier_is_rejected(self):
        payload = self._valid()
        payload["identifiers"] = [
            {"type": "handle", "value": "nightjar", "observed_at": "2026-03-11T09:14:00Z"}
        ]
        self.assertTrue(any("not emitted" in e for e in contract.validate(payload)))

    def test_an_identifier_without_observed_at_is_rejected(self):
        payload = self._valid()
        payload["identifiers"] = [{"type": "wallet", "value": "1Hx4kQ9mVn2RtYbP7sLdF3wCgN8jZaEuT6"}]
        self.assertTrue(any("observed_at" in e for e in contract.validate(payload)))

    def test_a_persona_on_an_index_artifact_is_rejected(self):
        payload = dict(next(p for p in PAYLOADS if p["page_type"] == "index"))
        payload["persona"] = {"handle": "nightjar"}
        self.assertTrue(any("omitted" in e for e in contract.validate(payload)))

    def test_an_observed_at_on_a_profile_is_rejected(self):
        payload = dict(next(p for p in PAYLOADS if p["page_type"] == "profile"))
        payload["persona"] = dict(payload["persona"], observed_at="2026-03-11T09:14:00Z")
        self.assertTrue(any("profile" in e for e in contract.validate(payload)))

    def test_an_identifier_on_a_profile_is_rejected(self):
        payload = dict(next(p for p in PAYLOADS if p["page_type"] == "profile"))
        payload["identifiers"] = [
            {"type": "wallet", "value": "1Hx4kQ9mVn2RtYbP7sLdF3wCgN8jZaEuT6",
             "observed_at": "2026-03-11T09:14:00Z"}
        ]
        self.assertTrue(any("identifiers" in e for e in contract.validate(payload)))

    def test_an_empty_relay_path_is_rejected(self):
        payload = self._valid()
        payload["relay_path"] = []
        self.assertTrue(any("relay_path" in e for e in contract.validate(payload)))


if __name__ == "__main__":
    unittest.main()
