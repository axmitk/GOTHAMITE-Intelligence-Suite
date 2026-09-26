"""Extraction and page classification -- `SCRAPER_AGENT_SPEC.md` sections 3 and 4.

Rule-based only.  No ML, no NLP, no LLM, and nothing here evaluates or executes
scraped text: every function below takes page content as an opaque string and
returns data.  That is the scope lock in `MASTER_CONTEXT.md` section 3 rule 3,
and it is the property that makes a crawler over attacker-controlled pages safe
to run at all.
"""

from __future__ import annotations

import re
from typing import NamedTuple

# --- page structure (section 3) ---------------------------------------------

# The hardcoded route shapes.  A URL is visited only if it matches one of these
# *and* is same-host: "any URL that did not come from the hardcoded structure is
# not visited".  Discovery reads the index page's own links, but a link is a
# candidate route, never a destination in itself -- anything that does not match
# a pattern here is dropped without being fetched.
ITEM_ROUTE = re.compile(r"^/(?:thread|listing)/[0-9]+$")
PROFILE_ROUTE = re.compile(r"^/user/[A-Za-z0-9_]+$")
INDEX_ROUTE = "/"

HREF_RE = re.compile(r'href="([^"]*)"')

# --- markup the mock sites emit (MOCK_SITES_SPEC.md section 4) ---------------

BYLINE_RE = re.compile(
    r'<p class="byline">Posted by <a href="/user/([^"]+)">[^<]*</a>'
    r" on <time>([^<]+)</time></p>"
)

# --- identifiers (section 4) ------------------------------------------------

PGP_BLOCK_RE = re.compile(
    r"-----BEGIN PGP PUBLIC KEY BLOCK-----(.*?)-----END PGP PUBLIC KEY BLOCK-----",
    re.DOTALL,
)
FINGERPRINT_RE = re.compile(r"Fingerprint:\s*([0-9A-Fa-f][0-9A-Fa-f\s]*)")
HEX40_RE = re.compile(r"^[0-9A-F]{40}$")

# Base58 as the seed data uses it.  The lookarounds are the "not a substring of
# a longer alphanumeric run" half of section 4's validation rule; the character
# class is the "no 0/O/I/l" half.
WALLET_RE = re.compile(
    r"(?<![0-9A-Za-z])[13][a-km-zA-HJ-NP-Z1-9]{25,34}(?![0-9A-Za-z])"
)
WALLET_FORBIDDEN = set("0OIl")
WALLET_MIN, WALLET_MAX = 26, 35


class PageType:
    """The three values `page_type` may take (SD-021, closed enum, no default)."""

    INDEX = "index"
    ITEM = "item"
    PROFILE = "profile"


class Byline(NamedTuple):
    handle: str
    observed_at: str


def classify(route: str) -> str:
    """Map a route to its `page_type`.

    Structural, from the crawl step that produced the page -- never from
    inspecting content.  The scraper therefore knows `page_type` before it
    parses anything, which is what lets the field be required with no default.
    """
    if route == INDEX_ROUTE:
        return PageType.INDEX
    if PROFILE_ROUTE.match(route):
        return PageType.PROFILE
    if ITEM_ROUTE.match(route):
        return PageType.ITEM
    raise ValueError(f"route {route!r} is not part of the hardcoded structure")


def http_body(response: bytes) -> str:
    """The page itself, without the HTTP status line and headers.

    `onion_client` returns the destination's whole raw HTTP response.
    `API_CONTRACT.md` section 3 calls `raw_content` *"verbatim page content"* and
    both worked examples show the document alone, so the page is what is
    carried.  Nothing inside the document is cleaned, stripped or truncated.
    """
    text = response.decode("utf-8", errors="replace")
    marker = "\r\n\r\n"
    if marker in text:
        return text.split(marker, 1)[1]
    if "\n\n" in text:
        return text.split("\n\n", 1)[1]
    return text


def discover_routes(index_html: str) -> list[str]:
    """Routes to visit, read from the index page's own links.

    Only same-host relative links matching a hardcoded route pattern survive.
    A link pointing at another host is ignored silently, and so is a same-host
    link whose shape is not one the crawl knows -- neither is ever fetched.

    Returns items before profiles, each in sorted order, so a run over an
    unchanged corpus visits pages in an unchanged sequence.
    """
    items: set[str] = set()
    profiles: set[str] = set()
    for href in HREF_RE.findall(index_html):
        if not href.startswith("/") or href.startswith("//"):
            continue  # absolute, protocol-relative or fragment: not ours
        if ITEM_ROUTE.match(href):
            items.add(href)
        elif PROFILE_ROUTE.match(href):
            profiles.add(href)
    return sorted(items, key=_route_sort_key) + sorted(profiles)


def _route_sort_key(route: str) -> tuple[str, int]:
    head, _, tail = route.rpartition("/")
    return head, int(tail)


def byline(page: str) -> Byline | None:
    """The author and post timestamp an item page displays."""
    match = BYLINE_RE.search(page)
    if match is None:
        return None
    return Byline(handle=match.group(1), observed_at=match.group(2))


def profile_handle(route: str) -> str:
    """The persona a profile page belongs to, from its own route."""
    return route[len("/user/") :]


def pgp_fingerprints(page: str) -> list[str]:
    """Every fingerprint on the page, normalised.

    Uppercased with all whitespace removed, per section 4.  Anything that is not
    40 hex characters after normalisation is not a fingerprint and is dropped --
    the caller logs it and moves on.
    """
    found: list[str] = []
    for block in PGP_BLOCK_RE.findall(page):
        match = FINGERPRINT_RE.search(block)
        if match is None:
            continue
        normalised = re.sub(r"\s+", "", match.group(1)).upper()
        if HEX40_RE.match(normalised) and normalised not in found:
            found.append(normalised)
    return found


def wallets(page: str) -> list[str]:
    """Every wallet address on the page, verbatim and validated.

    Section 4 is explicit that a false positive is worse than a miss: an
    invented address creates a link in the graph that nothing in the world
    supports.  So the regex match is a candidate, and the checks below decide.
    """
    found: list[str] = []
    for candidate in WALLET_RE.findall(page):
        if not WALLET_MIN <= len(candidate) <= WALLET_MAX:
            continue
        if set(candidate) & WALLET_FORBIDDEN:
            continue
        if candidate not in found:
            found.append(candidate)
    return found
