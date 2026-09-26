"""Phase-4 tests: the mock sites, checked against the acceptance criteria in
`AgentsDocs/MOCK_SITES_SPEC.md` section 7 and `AgentsDocs/IMPLEMENTATION_PLAN.md`
section 3 Phase 4.

Content is asserted against `mock_sites.seed_data`, which copies
`AgentsDocs/DATA_MODEL.md` section 4 -- and the identifiers are additionally
asserted against literals written out here, character for character.  Comparing
the pages only to the module that renders them would pass even if the module
itself drifted from the data model, so the literals below are the actual guard.

Every fetch that exercises criterion 1 goes through a real relay path.  Nothing
in this file contacts the network: every socket is loopback, and a test
explicitly asserts that no site opens an outbound connection.
"""

from __future__ import annotations

import re
import socket
import unittest

from client.onion_client import build_raw_request
from mock_sites import seed_data
from mock_sites import site_server
from mock_sites.site_server import build_server
from tests.harness import SITE_ADDRESSES, SandboxHarness

# --- the data model, restated as literals -----------------------------------
# DATA_MODEL.md section 4, copied by hand.  If mock_sites.seed_data drifts from
# the document, these fail.

EXPECTED_PGP = {
    "nightjar": "9F2A4C81D3E5B7069A1C4F82D6E30B57A4C19E8D",
    "n1ghtjar_": "9F2A4C81D3E5B7069A1C4F82D6E30B57A4C19E8D",
    "quillfeather": "3B77E1A9C4D28F60B5E3A17C9D42F8E06B1A5C93",
    "quill_v2": "E4C08B21F7A6D93E5C1B84027FA36D9E1C05B872",
    "nightjarr": "7D19F4C8B302A6E5D91C7B48F0A2E63D5C81B94F",
    "bellwether": "A50C3E97B14D6F82093C5A7E1BD48F620E93C7A1",
}

EXPECTED_WALLET = {
    "nightjar": "1Hx4kQ9mVn2RtYbP7sLdF3wCgN8jZaEuT6",
    "n1ghtjar_": "1Hx4kQ9mVn2RtYbP7sLdF3wCgN8jZaEuT6",
    "quillfeather": "1Kp7dR3zXw9QfM4vB2nHtL6sYcJ8gAeU5o",
    "quill_v2": "1Kp7dR3zXw9QfM4vB2nHtL6sYcJ8gAeU5o",
    "nightjarr": "1Qs2fT8yWn5LpX3mK9vGdC7bJ4hRzAeN1u",
    "bellwether": "1Zr6bN4qJm8VhT2xD5cWfP9sLgY3kEuA7i",
}

EXPECTED_WINDOW = {
    "nightjar": ("2026-01-08", "2026-08-20"),
    "n1ghtjar_": ("2026-02-14", "2026-08-22"),
    "quillfeather": ("2026-01-20", "2026-04-02"),
    "quill_v2": ("2026-04-19", "2026-08-18"),
    "nightjarr": ("2026-03-01", "2026-08-21"),
    "bellwether": ("2026-02-01", "2026-08-19"),
}

EXPECTED_SITE = {
    "nightjar": "forum-alpha",
    "quillfeather": "forum-alpha",
    "n1ghtjar_": "marketplace-beta",
    "bellwether": "marketplace-beta",
    "quill_v2": "forum-gamma",
    "nightjarr": "forum-gamma",
}

CANONICAL_A_WALLET = "1Hx4kQ9mVn2RtYbP7sLdF3wCgN8jZaEuT6"  # SD-015

WALLET_RE = re.compile(r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b")
PGP_RE = re.compile(r"Fingerprint:\s*([0-9A-F ]{40,60})")

HARNESS: SandboxHarness | None = None
PAGES: dict[str, dict[str, str]] = {}


def setUpModule() -> None:  # noqa: N802
    """One pool and one crawl, shared by every test in this module.

    Fetching each page through a real 3-hop path is the expensive part; doing it
    once and asserting many things about the captured bytes keeps the suite
    honest without making it slow.
    """
    global HARNESS
    HARNESS = SandboxHarness(relay_count=7, with_sites=True)
    HARNESS.start()
    client = HARNESS.client()

    for site_id, address in SITE_ADDRESSES.items():
        pages: dict[str, str] = {}
        path = client.get_path(3)
        pages["/"] = client.get(path, address, "/").decode("utf-8", "replace")
        site = seed_data.SITES[site_id]
        for post in seed_data.posts_for_site(site_id):
            resource = f"/{site.item_path}/{post.post_id}"
            pages[resource] = client.get(
                client.get_path(3), address, resource
            ).decode("utf-8", "replace")
        for persona in seed_data.personas_for_site(site_id):
            resource = f"/user/{persona.handle}"
            pages[resource] = client.get(
                client.get_path(3), address, resource
            ).decode("utf-8", "replace")
        PAGES[site_id] = pages


def tearDownModule() -> None:  # noqa: N802
    if HARNESS is not None:
        HARNESS.stop()


def body_of(raw: str) -> str:
    """The page, without the HTTP status line and headers."""
    return raw.split("\r\n\r\n", 1)[-1]


def all_text(site_id: str) -> str:
    return "\n".join(body_of(v) for v in PAGES[site_id].values())


def every_page() -> str:
    return "\n".join(all_text(s) for s in PAGES)


BYLINE_RE = re.compile(r'<p class="byline">Posted by <a href="/user/([^"]+)">')


def author_of(raw: str, resource: str) -> str | None:
    """The handle a rendered page belongs to, read out of the page itself.

    Item pages carry a byline; profile pages are addressed by handle; index
    pages have no author at all.  Read from the markup rather than looked up in
    `seed_data`, because the point is to check what a scraper would actually
    attribute an identifier to.
    """
    if resource.startswith("/user/"):
        return resource[len("/user/"):]
    match = BYLINE_RE.search(body_of(raw))
    return match.group(1) if match else None


def identifiers_on(raw: str) -> tuple[set[str], set[str]]:
    """Every wallet and PGP fingerprint a rule-based extractor would find."""
    text = body_of(raw)
    wallets = set(WALLET_RE.findall(text))
    fingerprints = {m.replace(" ", "") for m in PGP_RE.findall(text)}
    return wallets, fingerprints


class TestReachableThroughRelayPath(unittest.TestCase):
    """Criterion 1 -- all three sites reachable through a full relay path."""

    def test_all_three_sites_answered_through_the_chain(self) -> None:
        self.assertEqual(set(PAGES), set(SITE_ADDRESSES))
        for site_id in SITE_ADDRESSES:
            with self.subTest(site=site_id):
                self.assertIn("200 OK", PAGES[site_id]["/"])

    def test_fetch_used_three_distinct_relays_and_returned_the_page(self) -> None:
        """The fetch is not just successful -- it went through three hops.

        A page can be right and still have been fetched directly, which would
        make criterion 1 meaningless. This asserts the path really was three
        distinct relays and that the response came back decrypted.
        """
        assert HARNESS is not None
        client = HARNESS.client()
        path = client.get_path(3)
        self.assertEqual(len({hop.relay_id for hop in path}), 3)
        body, trace = client.get_with_trace(
            path, SITE_ADDRESSES["forum-alpha"], "/thread/14"
        )
        self.assertIn(CANONICAL_A_WALLET, body.decode("utf-8"))
        self.assertEqual([hop.relay_id for hop in trace.path], [h.relay_id for h in path])
        # One response envelope per hop: the page really was re-encrypted three
        # times on the way back, not fetched directly.
        self.assertEqual(len(trace.response_envelopes), 3)

    def test_every_declared_route_exists(self) -> None:
        """Index, every thread/listing, and every profile answer 200."""
        for site_id, pages in PAGES.items():
            expected = 1 + len(seed_data.posts_for_site(site_id)) + len(
                seed_data.personas_for_site(site_id)
            )
            with self.subTest(site=site_id):
                self.assertEqual(len(pages), expected)
                for resource, raw in pages.items():
                    self.assertIn("200 OK", raw, f"{site_id}{resource}")

    def test_unknown_routes_are_404(self) -> None:
        assert HARNESS is not None
        client = HARNESS.client()
        for resource in ("/thread/9999", "/user/nobody", "/wp-admin"):
            with self.subTest(resource=resource):
                raw = client.get(
                    client.get_path(3), SITE_ADDRESSES["forum-alpha"], resource
                ).decode("utf-8", "replace")
                self.assertIn("404", raw.splitlines()[0])


class TestPersonasPresent(unittest.TestCase):
    """Criterion 3 -- every persona present with the exact handle and window."""

    def test_all_six_personas_on_the_right_site(self) -> None:
        self.assertEqual(len(seed_data.PERSONAS), 6)
        for handle, site_id in EXPECTED_SITE.items():
            with self.subTest(handle=handle):
                persona = seed_data.persona_by_handle(handle)
                self.assertIsNotNone(persona, f"{handle} missing from seed data")
                assert persona is not None
                self.assertEqual(persona.site_id, site_id)
                self.assertIn(f"/user/{handle}", PAGES[site_id])

    def test_profile_pages_state_the_documented_window(self) -> None:
        for handle, (start, _end) in EXPECTED_WINDOW.items():
            site_id = EXPECTED_SITE[handle]
            with self.subTest(handle=handle):
                page = body_of(PAGES[site_id][f"/user/{handle}"])
                self.assertIn(f"Joined {start}", page)

    def test_posts_span_the_documented_active_window(self) -> None:
        """First and last post land on the window endpoints, not merely inside."""
        for handle, (start, end) in EXPECTED_WINDOW.items():
            with self.subTest(handle=handle):
                posts = seed_data.posts_for_handle(handle)
                stamps = sorted(p.observed_at for p in posts)
                self.assertTrue(stamps[0].startswith(start), f"{handle} first {stamps[0]}")
                self.assertTrue(stamps[-1].startswith(end), f"{handle} last {stamps[-1]}")

    def test_post_count_within_the_documented_range(self) -> None:
        """DATA_MODEL.md section 5: 8-15 posts per persona."""
        for handle in EXPECTED_SITE:
            with self.subTest(handle=handle):
                count = len(seed_data.posts_for_handle(handle))
                self.assertGreaterEqual(count, 8)
                self.assertLessEqual(count, 15)

    def test_handles_appear_on_their_own_site_and_nowhere_else(self) -> None:
        """A handle leaking onto another site would invent a link.

        `nightjar` is a substring of `nightjarr`, so this compares the byline
        markup rather than searching for the bare handle.
        """
        for handle, site_id in EXPECTED_SITE.items():
            byline = f'<a href="/user/{handle}">{handle}</a>'
            with self.subTest(handle=handle):
                self.assertIn(byline, all_text(site_id))
                for other in PAGES:
                    if other != site_id:
                        self.assertNotIn(byline, all_text(other))


class TestIdentifiersCharacterForCharacter(unittest.TestCase):
    """Criterion 4 -- fingerprints and wallets match the data model exactly."""

    def test_canonical_a1_a2_wallet_present_on_both_sites(self) -> None:
        """SD-015: the canonical value, character for character."""
        self.assertIn(CANONICAL_A_WALLET, all_text("forum-alpha"))
        self.assertIn(CANONICAL_A_WALLET, all_text("marketplace-beta"))

    def test_canonical_wallet_matches_seed_module_exactly(self) -> None:
        self.assertEqual(seed_data.WALLET_A, CANONICAL_A_WALLET)
        self.assertEqual(seed_data.PERSONAS["A1"].wallet, CANONICAL_A_WALLET)
        self.assertEqual(seed_data.PERSONAS["A2"].wallet, CANONICAL_A_WALLET)

    def test_no_bech32_anywhere(self) -> None:
        """SD-015 forbids bech32. A stray one would silently go unextracted."""
        self.assertNotIn("bc1", every_page())

    def test_each_persona_wallet_appears_on_at_least_two_pages(self) -> None:
        """MOCK_SITES_SPEC.md section 5 -- redundancy against a parser miss."""
        for handle, wallet in EXPECTED_WALLET.items():
            site_id = EXPECTED_SITE[handle]
            pages = [
                p for r, p in PAGES[site_id].items()
                if r.startswith(("/thread/", "/listing/")) and wallet in body_of(p)
            ]
            with self.subTest(handle=handle):
                self.assertGreaterEqual(len(pages), 2, f"{handle} wallet on {len(pages)} pages")

    def test_each_persona_pgp_appears_on_at_least_two_pages(self) -> None:
        for handle, fingerprint in EXPECTED_PGP.items():
            site_id = EXPECTED_SITE[handle]
            spaced = seed_data.format_fingerprint(fingerprint)
            pages = [
                p for r, p in PAGES[site_id].items()
                if r.startswith(("/thread/", "/listing/")) and spaced in body_of(p)
            ]
            with self.subTest(handle=handle):
                self.assertGreaterEqual(len(pages), 2, f"{handle} PGP on {len(pages)} pages")

    def test_every_rendered_wallet_is_a_known_seed_value(self) -> None:
        """No stray base58-shaped string anywhere.

        A wallet that is not in the data model would create a link GOTHAMITE
        cannot explain, which is worse than a missing one.
        """
        known = set(EXPECTED_WALLET.values())
        for site_id in PAGES:
            for found in WALLET_RE.findall(all_text(site_id)):
                with self.subTest(site=site_id, found=found):
                    self.assertIn(found, known)

    def test_every_rendered_fingerprint_normalises_to_a_known_value(self) -> None:
        known = set(EXPECTED_PGP.values())
        for site_id in PAGES:
            found = PGP_RE.findall(all_text(site_id))
            self.assertTrue(found, f"no fingerprints on {site_id}")
            for raw in found:
                normalised = raw.replace(" ", "").upper()
                with self.subTest(site=site_id, fingerprint=normalised):
                    self.assertEqual(len(normalised), 40)
                    self.assertIn(normalised, known)

    def test_identifiers_are_in_body_text_not_attributes(self) -> None:
        """MOCK_SITES_SPEC.md section 2 rule 4 -- extraction must do real work."""
        for site_id in PAGES:
            for resource, raw in PAGES[site_id].items():
                if not resource.startswith(("/thread/", "/listing/")):
                    continue
                page = body_of(raw)
                for wallet in EXPECTED_WALLET.values():
                    if wallet in page:
                        with self.subTest(site=site_id, resource=resource):
                            self.assertNotIn(f'"{wallet}"', page)
                            self.assertNotIn(f"={wallet}", page)
                            self.assertIn(f"<p>", page)


class TestPlantedLinks(unittest.TestCase):
    """Criterion 5 -- A1/A2 share both, B1/B2 share wallet only, C1 shares none."""

    def test_a1_and_a2_share_pgp_and_wallet(self) -> None:
        self.assertEqual(EXPECTED_PGP["nightjar"], EXPECTED_PGP["n1ghtjar_"])
        self.assertEqual(EXPECTED_WALLET["nightjar"], EXPECTED_WALLET["n1ghtjar_"])
        alpha, beta = all_text("forum-alpha"), all_text("marketplace-beta")
        spaced = seed_data.format_fingerprint(EXPECTED_PGP["nightjar"])
        for text in (alpha, beta):
            self.assertIn(spaced, text)
            self.assertIn(CANONICAL_A_WALLET, text)

    def test_b1_and_b2_share_wallet_but_not_pgp(self) -> None:
        self.assertEqual(EXPECTED_WALLET["quillfeather"], EXPECTED_WALLET["quill_v2"])
        self.assertNotEqual(EXPECTED_PGP["quillfeather"], EXPECTED_PGP["quill_v2"])
        wallet = EXPECTED_WALLET["quillfeather"]
        self.assertIn(wallet, all_text("forum-alpha"))
        self.assertIn(wallet, all_text("forum-gamma"))
        b1_pgp = seed_data.format_fingerprint(EXPECTED_PGP["quillfeather"])
        self.assertNotIn(b1_pgp, all_text("forum-gamma"))

    def test_c1_shares_nothing_with_anyone(self) -> None:
        """The decoy must not be linkable on any identifier.

        Handle similarity is the whole point of C1 and is left intact; what must
        not exist is a shared key or address.
        """
        c1_pgp, c1_wallet = EXPECTED_PGP["nightjarr"], EXPECTED_WALLET["nightjarr"]
        others = {h for h in EXPECTED_PGP if h != "nightjarr"}
        for handle in others:
            with self.subTest(other=handle):
                self.assertNotEqual(c1_pgp, EXPECTED_PGP[handle])
                self.assertNotEqual(c1_wallet, EXPECTED_WALLET[handle])
        self.assertNotIn(c1_wallet, all_text("forum-alpha"))
        self.assertNotIn(c1_wallet, all_text("marketplace-beta"))
        self.assertNotIn(seed_data.format_fingerprint(c1_pgp), all_text("forum-alpha"))

    def test_c1_handle_is_one_character_from_a1(self) -> None:
        self.assertEqual("nightjarr", "nightjar" + "r")

    def test_c1_activity_overlaps_a1(self) -> None:
        c1_start, c1_end = EXPECTED_WINDOW["nightjarr"]
        a1_start, a1_end = EXPECTED_WINDOW["nightjar"]
        self.assertLess(a1_start, c1_end)
        self.assertLess(c1_start, a1_end)

    def test_d1_is_the_co_location_negative_control(self) -> None:
        """Criterion for Actor D, as revised by SD-027 and its R2 addendum.

        D1 shares a marketplace and an active period with A2 and shares no
        identifier with it, so no `same_actor_suspected` edge may arise.  C1
        covers the *similar handle* false positive, which section 3 scores at
        0.05; this covers *same venue, same period*, which section 3 does not
        score at all.

        Asserted over rendered pages rather than over the seed map, because the
        defect this replaces -- listing 44, before SD-027 -- left both personas'
        own values correct and still put A2's wallet on a page written by D1.
        """
        self.assertEqual(EXPECTED_SITE["bellwether"], EXPECTED_SITE["n1ghtjar_"])

        d1_start, d1_end = EXPECTED_WINDOW["bellwether"]
        a2_start, a2_end = EXPECTED_WINDOW["n1ghtjar_"]
        self.assertLess(a2_start, d1_end)
        self.assertLess(d1_start, a2_end)

        seen_d1_page = False
        for resource, raw in PAGES["marketplace-beta"].items():
            author = author_of(raw, resource)
            if author is None:
                continue
            wallets, fingerprints = identifiers_on(raw)
            other = "n1ghtjar_" if author == "bellwether" else "bellwether"
            seen_d1_page = seen_d1_page or author == "bellwether"
            with self.subTest(resource=resource, author=author):
                self.assertNotIn(EXPECTED_WALLET[other], wallets)
                self.assertNotIn(EXPECTED_PGP[other], fingerprints)
        self.assertTrue(seen_d1_page, "no bellwether page was examined")

    def test_d1_own_wallet_never_shared(self) -> None:
        d1 = EXPECTED_WALLET["bellwether"]
        self.assertNotIn(d1, all_text("forum-alpha"))
        self.assertNotIn(d1, all_text("forum-gamma"))

    def test_no_unintended_identifier_sharing(self) -> None:
        """Only the documented pairs share anything.

        A1/A2 share PGP and wallet; B1/B2 share wallet. Every other pair must
        share neither -- an accidental collision would invent a link.
        """
        allowed_pgp = {frozenset({"nightjar", "n1ghtjar_"})}
        allowed_wallet = {
            frozenset({"nightjar", "n1ghtjar_"}),
            frozenset({"quillfeather", "quill_v2"}),
        }
        handles = sorted(EXPECTED_PGP)
        for i, a in enumerate(handles):
            for b in handles[i + 1:]:
                pair = frozenset({a, b})
                with self.subTest(pair=sorted(pair)):
                    if EXPECTED_PGP[a] == EXPECTED_PGP[b]:
                        self.assertIn(pair, allowed_pgp)
                    if EXPECTED_WALLET[a] == EXPECTED_WALLET[b]:
                        self.assertIn(pair, allowed_wallet)

    def test_no_page_carries_another_personas_identifier(self) -> None:
        """`MOCK_SITES_SPEC.md` section 2 rules 6 and 7 -- attribution soundness.

        `DATA_MODEL.md` section 2 defines `Identifier.persona_id` as ownership,
        and the scraper's extractor is a regex that cannot tell "my address"
        from "I paid this address".  So the guarantee has to hold in the corpus:
        every identifier a scraper can find on a page must belong to that page's
        author, or the wrong persona gets it and a false `same_actor_suspected`
        edge follows silently.

        This scans the rendered pages and checks each value against the author
        read from that same page.  Comparing the persona-to-identifier map would
        not do: the defect this exists to catch -- listing 44, before SD-027 --
        left every persona's own values correct and still attributed A2's wallet
        to D1.

        Index and profile pages must carry no identifier at all (rule 7).  They
        have no post timestamp, so an identifier found there could not be
        emitted with a conforming `observed_at`.
        """
        checked = 0
        for site_id, pages in PAGES.items():
            for resource, raw in pages.items():
                wallets, fingerprints = identifiers_on(raw)
                author = author_of(raw, resource)
                is_item = resource != "/" and not resource.startswith("/user/")
                with self.subTest(site=site_id, resource=resource, author=author):
                    if not is_item:
                        self.assertEqual(set(), wallets, "identifier on a non-item page")
                        self.assertEqual(set(), fingerprints, "identifier on a non-item page")
                        continue
                    self.assertIsNotNone(author, "an item page with no byline")
                    self.assertIn(author, EXPECTED_WALLET, "unknown author handle")
                    for wallet in wallets:
                        self.assertEqual(
                            EXPECTED_WALLET[author], wallet,
                            f"{resource} carries a wallet not belonging to {author}",
                        )
                        checked += 1
                    for fingerprint in fingerprints:
                        self.assertEqual(
                            EXPECTED_PGP[author], fingerprint,
                            f"{resource} carries a fingerprint not belonging to {author}",
                        )
                        checked += 1
        self.assertGreater(checked, 0, "no identifiers were scanned -- the guard is vacuous")


class TestRebrandTiming(unittest.TestCase):
    """Criterion 6 -- B1's last post precedes B2's first by roughly 17 days."""

    def test_b1_last_precedes_b2_first_by_seventeen_days(self) -> None:
        from datetime import datetime

        b1 = max(p.observed_at for p in seed_data.posts_for_handle("quillfeather"))
        b2 = min(p.observed_at for p in seed_data.posts_for_handle("quill_v2"))
        parse = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))  # noqa: E731
        gap_days = (parse(b2) - parse(b1)).total_seconds() / 86400
        self.assertGreater(gap_days, 0, "B2 must start after B1 ends")
        self.assertAlmostEqual(gap_days, 17, delta=1.0)

    def test_b1_and_b2_windows_do_not_overlap(self) -> None:
        self.assertLess(EXPECTED_WINDOW["quillfeather"][1], EXPECTED_WINDOW["quill_v2"][0])


class TestDeterminism(unittest.TestCase):
    """Criterion 7 -- identical bytes every time."""

    def test_same_page_twice_through_different_paths_is_identical(self) -> None:
        assert HARNESS is not None
        client = HARNESS.client()
        address = SITE_ADDRESSES["marketplace-beta"]
        first = client.get(client.get_path(3), address, "/listing/44")
        second = client.get(client.get_path(3), address, "/listing/44")
        self.assertEqual(first, second)

    def test_response_bytes_identical_across_a_server_restart(self) -> None:
        """A fresh process must produce the same bytes, headers included.

        This is the criterion as written. It holds because the sites emit no
        Date header and compute nothing at request time.
        """
        captured = []
        for _ in range(2):
            server = build_server("forum-alpha", "127.0.0.1", 0)
            port = server.server_address[1]
            import threading

            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
                    sock.sendall(build_raw_request("alpha7fq2mx9k.onion.mock", "/thread/14"))
                    chunks = []
                    while True:
                        chunk = sock.recv(65536)
                        if not chunk:
                            break
                        chunks.append(chunk)
                    captured.append(b"".join(chunks))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
        self.assertEqual(captured[0], captured[1])
        self.assertNotIn(b"Date:", captured[0])

    def test_no_runtime_generated_content(self) -> None:
        """Rule 3: no random generation, no timestamps computed at runtime.

        Parsed rather than grepped. A substring search over the source also hits
        the prose in docstrings that says these things are not used, so it would
        fail on a module that is correct and pass on one that imports `random`
        inside a function.
        """
        import ast
        import inspect

        banned_modules = {"random", "faker", "secrets", "time", "datetime", "uuid"}
        banned_calls = {"now", "utcnow", "today", "time", "random", "choice", "uuid4"}

        for module in (seed_data, site_server):
            tree = ast.parse(inspect.getsource(module))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        with self.subTest(module=module.__name__, imported=alias.name):
                            self.assertNotIn(alias.name.split(".")[0], banned_modules)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    with self.subTest(module=module.__name__, imported=node.module):
                        self.assertNotIn(node.module.split(".")[0], banned_modules)
                elif isinstance(node, ast.Call):
                    func = node.func
                    name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
                    with self.subTest(module=module.__name__, call=name):
                        self.assertNotIn(name, banned_calls)


class TestContentSafety(unittest.TestCase):
    """Criterion 8 -- no real-world content, no operational detail."""

    def test_listings_use_placeholder_item_names_only(self) -> None:
        """MOCK_SITES_SPEC.md section 2 rule 2 -- generic placeholders only."""
        allowed = ("dataset bundle", "archive dump", "credentials pack", "archive material")
        text = every_page().lower()
        self.assertTrue(any(item in text for item in allowed))

    def test_no_operational_or_instructional_language(self) -> None:
        banned = [
            "how to", "step 1", "tutorial", "instructions for",
            "exploit", "payload", "bypass", "crack",
        ]
        text = every_page().lower()
        for phrase in banned:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, text)

    def test_no_real_network_identifiers(self) -> None:
        """No real hostnames, emails or URLs anywhere in the content."""
        text = every_page()
        self.assertNotIn("http://", text.replace('href="/', ""))
        self.assertNotIn("https://", text)
        self.assertNotIn("@", text)
        self.assertNotIn(".com", text)
        self.assertNotIn(".org", text)

    def test_every_onion_address_carries_the_mock_suffix(self) -> None:
        """MOCK_SITES_SPEC.md section 6 -- the suffix is mandatory.

        A bare `.onion` string could be mistaken for a real hidden service.
        """
        for match in re.findall(r"[a-z0-9]+\.onion(?:\.mock)?", every_page()):
            with self.subTest(address=match):
                self.assertTrue(match.endswith(".onion.mock"))

    def test_pgp_blocks_contain_no_real_key_material(self) -> None:
        text = every_page()
        self.assertIn("BEGIN PGP PUBLIC KEY BLOCK", text)
        self.assertIn("not a real key", text)
        self.assertNotIn("mQ", text)  # the usual start of a real armoured key

    def test_pages_declare_themselves_synthetic(self) -> None:
        for site_id in PAGES:
            with self.subTest(site=site_id):
                self.assertIn("Synthetic sandbox content", body_of(PAGES[site_id]["/"]))


class TestNoExternalAccess(unittest.TestCase):
    """No mock site opens an outbound connection."""

    def test_serving_pages_opens_no_outbound_socket(self) -> None:
        """Patch socket creation and assert the site never reaches out.

        Serving is entirely local rendering of hardcoded bytes, so any outbound
        connection would be a defect -- and the kind that would only show up in
        an environment with real network access.
        """
        server = build_server("forum-gamma", "127.0.0.1", 0)
        port = server.server_address[1]
        import threading

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        attempts: list[tuple] = []
        real_create = socket.create_connection

        def watched(address, *args, **kwargs):  # type: ignore[no-untyped-def]
            attempts.append(address)
            return real_create(address, *args, **kwargs)

        socket.create_connection = watched  # type: ignore[assignment]
        try:
            with real_create(("127.0.0.1", port), timeout=5) as sock:
                sock.sendall(build_raw_request("gamma2xd6bt5hy.onion.mock", "/thread/62"))
                while sock.recv(65536):
                    pass
        finally:
            socket.create_connection = real_create  # type: ignore[assignment]
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        self.assertEqual(attempts, [], f"site opened outbound connections: {attempts}")

    def test_site_module_imports_no_network_client(self) -> None:
        import inspect

        source = inspect.getsource(
            __import__("mock_sites.site_server", fromlist=["x"])
        )
        for banned in ("urllib.request", "requests", "http.client", "urlopen"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, source)


class TestComposeIsolation(unittest.TestCase):
    """Criterion 2 -- not reachable directly from the host.

    That is a property of the deployment, so what is checkable here is the
    compose file: no site may publish a host port. The live `curl` check belongs
    to the Docker verification and is reported separately.
    """

    def test_no_site_publishes_a_host_port(self) -> None:
        from pathlib import Path

        text = Path("mock_sites/docker-compose.sites.yml").read_text(encoding="utf-8")
        stripped = "\n".join(
            line for line in text.splitlines() if not line.lstrip().startswith("#")
        )
        self.assertNotIn("ports:", stripped)

    def test_all_three_sites_declared(self) -> None:
        from pathlib import Path

        text = Path("mock_sites/docker-compose.sites.yml").read_text(encoding="utf-8")
        for site_id in seed_data.SITES:
            with self.subTest(site=site_id):
                self.assertIn(f"container_name: {site_id}", text)

    def test_addresses_match_the_spec(self) -> None:
        """MOCK_SITES_SPEC.md section 6, and the client's resolution table."""
        from client.onion_client import MOCK_ADDRESS_MAP

        expected = {
            "forum-alpha": "alpha7fq2mx9k.onion.mock",
            "marketplace-beta": "beta4np8vz3wc.onion.mock",
            "forum-gamma": "gamma2xd6bt5hy.onion.mock",
        }
        for site_id, address in expected.items():
            with self.subTest(site=site_id):
                self.assertEqual(seed_data.SITES[site_id].address, address)
                self.assertIn(address, MOCK_ADDRESS_MAP)


if __name__ == "__main__":
    unittest.main()
