"""Local validation of an ingest payload against `AgentsDocs/API_CONTRACT.md` section 3.

**This is not GOTHAMITE, and it is not an ingestion endpoint.**  It reads a
payload the scraper has just built and reports whether that payload conforms to
the contract, so a construction bug is caught here rather than being posted at a
service that does not exist yet to reject it.

It validates the *request*, and stops there.  Storage, deduplication,
correlation, scoring and every relationship decision belong to GOTHAMITE
(`API_CONTRACT.md` section 5), and nothing in this module implements or
approximates any of them.
"""

from __future__ import annotations

import hashlib
import re
from urllib.parse import urlsplit

SOURCE_IDS = {"forum-alpha", "marketplace-beta", "forum-gamma"}
SOURCE_TYPES = {"forum", "marketplace"}
PAGE_TYPES = {"index", "item", "profile"}

# Section 3: Phase 5 emits these two only.  `handle` and `contact` stay reserved
# in the data model and are never sent (SD-022).
EMITTED_IDENTIFIER_TYPES = {"pgp_fingerprint", "wallet"}

TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
CONTENT_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
PGP_RE = re.compile(r"^[0-9A-F]{40}$")
MOCK_HOST_SUFFIX = ".onion.mock"


def content_hash(raw_content: str) -> str:
    """`sha256:` + hex digest of `raw_content` as UTF-8 bytes (section 3)."""
    digest = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def validate(payload: dict) -> list[str]:
    """Every way this payload fails the contract, or an empty list.

    Returns all problems rather than the first, so a malformed payload is
    reported once and completely.
    """
    errors: list[str] = []
    _check_required(payload, errors)
    _check_url(payload, errors)
    _check_content(payload, errors)
    _check_persona(payload, errors)
    _check_identifiers(payload, errors)
    _check_relay_path(payload, errors)
    return errors


def _check_required(payload: dict, errors: list[str]) -> None:
    for field in (
        "source_id",
        "source_type",
        "page_type",
        "url",
        "collected_at",
        "relay_path",
        "raw_content",
        "content_hash",
        "identifiers",
    ):
        if field not in payload:
            errors.append(f"{field}: required field is missing")

    if payload.get("source_id") not in SOURCE_IDS:
        errors.append(f"source_id: {payload.get('source_id')!r} is not a known source")
    if payload.get("source_type") not in SOURCE_TYPES:
        errors.append(f"source_type: {payload.get('source_type')!r} is not a valid type")
    if payload.get("page_type") not in PAGE_TYPES:
        errors.append(
            f"page_type: {payload.get('page_type')!r} is not one of "
            "index | item | profile (required, no default)"
        )
    if not TIMESTAMP_RE.match(str(payload.get("collected_at", ""))):
        errors.append("collected_at: not ISO 8601 UTC with a Z suffix")


def _check_url(payload: dict, errors: list[str]) -> None:
    url = payload.get("url")
    if not isinstance(url, str):
        errors.append("url: must be a string")
        return
    parts = urlsplit(url)
    if parts.scheme != "http":
        errors.append("url: scheme must be http (SD-023 rules 1 and 2)")
    if not parts.netloc.endswith(MOCK_HOST_SUFFIX):
        errors.append("url: host must be a .onion.mock address")
    if not parts.path.startswith("/"):
        errors.append("url: a route path is required, including the index's slash")
    if parts.query or parts.fragment:
        errors.append("url: no query string or fragment semantics are defined")


def _check_content(payload: dict, errors: list[str]) -> None:
    raw = payload.get("raw_content")
    if not isinstance(raw, str) or not raw:
        errors.append("raw_content: must be a non-empty string")
        return
    expected = content_hash(raw)
    if payload.get("content_hash") != expected:
        errors.append("content_hash: does not match sha256 of raw_content")
    if not CONTENT_HASH_RE.match(str(payload.get("content_hash", ""))):
        errors.append("content_hash: must be 'sha256:' followed by a hex digest")


def _check_persona(payload: dict, errors: list[str]) -> None:
    """The section 3 page_type matrix, which is the whole of SD-021."""
    page_type = payload.get("page_type")
    persona = payload.get("persona")

    if page_type == "index":
        if persona is not None:
            errors.append("persona: must be omitted entirely for an index page")
        return

    if not isinstance(persona, dict):
        errors.append(f"persona: required for page_type {page_type!r}")
        return
    if not isinstance(persona.get("handle"), str) or not persona["handle"]:
        errors.append("persona.handle: required and must be a non-empty string")

    if page_type == "item":
        observed = persona.get("observed_at")
        if observed is None:
            errors.append("persona.observed_at: required on an item page")
        elif not TIMESTAMP_RE.match(str(observed)):
            errors.append("persona.observed_at: not ISO 8601 UTC with a Z suffix")
    elif "observed_at" in persona:
        errors.append(
            "persona.observed_at: must be omitted on a profile page -- no join "
            "date or latest-post date may be substituted (SD-021.2)"
        )


def _check_identifiers(payload: dict, errors: list[str]) -> None:
    identifiers = payload.get("identifiers")
    if not isinstance(identifiers, list):
        errors.append("identifiers: must be a list (may be empty)")
        return

    if identifiers and payload.get("page_type") in {"index", "profile"}:
        errors.append(
            "identifiers: an index or profile page carries no extractable "
            "identifier -- it has no timestamp one could be emitted with"
        )

    for index, entry in enumerate(identifiers):
        where = f"identifiers[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{where}: must be an object")
            continue
        kind = entry.get("type")
        if kind not in EMITTED_IDENTIFIER_TYPES:
            errors.append(
                f"{where}.type: {kind!r} is not emitted by Phase 5 -- "
                "only pgp_fingerprint and wallet are"
            )
        value = entry.get("value")
        if not isinstance(value, str) or not value:
            errors.append(f"{where}.value: required and must be a non-empty string")
        elif kind == "pgp_fingerprint" and not PGP_RE.match(value):
            errors.append(
                f"{where}.value: a fingerprint must be 40 uppercase hex "
                "characters with no whitespace"
            )
        observed = entry.get("observed_at")
        if observed is None:
            errors.append(f"{where}.observed_at: required for every identifier")
        elif not TIMESTAMP_RE.match(str(observed)):
            errors.append(f"{where}.observed_at: not ISO 8601 UTC with a Z suffix")


def _check_relay_path(payload: dict, errors: list[str]) -> None:
    relay_path = payload.get("relay_path")
    if not isinstance(relay_path, list) or not relay_path:
        errors.append("relay_path: required, and must name the relays used")
        return
    if not all(isinstance(relay, str) and relay for relay in relay_path):
        errors.append("relay_path: every entry must be a relay id")
