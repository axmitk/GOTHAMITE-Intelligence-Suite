"""The scraper agent -- `AgentsDocs/SCRAPER_AGENT_SPEC.md`.

Crawls the three mock sites **through `onion_client`**, extracts the fields the
contract defines, and POSTs one artifact per page to the GOTHAMITE ingestion
seam.  Nothing here talks to a mock site directly: every fetch goes through a
relay path, which is the property the whole demo exists to show.

Scraped content is data.  It is never executed, evaluated, or passed anywhere
that treats text as an instruction (`MASTER_CONTEXT.md` section 3 rule 3).
"""

from __future__ import annotations

import argparse
import logging
import os
import time
from datetime import datetime, timezone
from typing import NamedTuple

from client.onion_client import OnionClient, OnionClientError
from common.http_util import HttpError, post_json
from scraper import contract, extract

log = logging.getLogger("scraper")

# Section 2 of the contract.  One request per artifact, never batched.
DEFAULT_INGEST_URL = "http://gothamite-backend:8000/api/v1/ingest"

# Section 3: hardcoded.  The scraper visits these three hosts and nothing else,
# ever.  There is no configuration path that adds a fourth.
SOURCES: tuple[dict[str, str], ...] = (
    {"source_id": "forum-alpha", "source_type": "forum",
     "host": "alpha7fq2mx9k.onion.mock"},
    {"source_id": "marketplace-beta", "source_type": "marketplace",
     "host": "beta4np8vz3wc.onion.mock"},
    {"source_id": "forum-gamma", "source_type": "forum",
     "host": "gamma2xd6bt5hy.onion.mock"},
)

# Section 3: about half a second between requests.  Not politeness -- it makes
# the relay logs readable while the demo is running.
DEFAULT_PAUSE = 0.5

# Section 6 says "retry twice with backoff" and does not fix the duration.
# This is an implementation default, not a specification value.
DEFAULT_BACKOFF = 0.5


class Outcome:
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"      # GOTHAMITE returned 400
    UNDELIVERED = "undelivered"  # 5xx after retries, or unreachable
    INVALID = "invalid"        # failed local validation, never sent


class RunSummary(NamedTuple):
    """Counters behind the section 7 run summary."""

    sources_attempted: int
    pages_fetched: int
    artifacts_sent: int
    accepted: int
    duplicate: int
    rejected: int
    undelivered: int
    invalid: int
    pgp: int
    wallet: int
    handles: int
    relay_paths: dict[str, list[str]]
    errors: list[str]

    def render(self) -> str:
        lines = [
            "=== SCRAPE RUN COMPLETE ===",
            f"Sources attempted:      {self.sources_attempted}",
            f"Pages fetched:          {self.pages_fetched}",
            f"Artifacts sent:         {self.artifacts_sent}   "
            f"(accepted {self.accepted}, duplicate {self.duplicate}, "
            f"failed {self.rejected + self.undelivered})",
            f"Identifiers extracted:  PGP {self.pgp} | wallet {self.wallet} "
            f"| handles {self.handles}",
            "Relay paths used:",
        ]
        for source_id, path in self.relay_paths.items():
            lines.append(f"  {source_id:<18}{' -> '.join(path)}")
        lines.append("Errors: " + ("none" if not self.errors else ""))
        lines.extend(f"  {error}" for error in self.errors)
        return "\n".join(lines)


def utc_now() -> str:
    """`collected_at`: when we saw it.  ISO 8601, UTC, `Z` suffix (SD-017)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ScraperAgent:
    """One crawl of the three sources, and one POST per page."""

    def __init__(
        self,
        client: OnionClient,
        ingest_url: str = DEFAULT_INGEST_URL,
        hops: int = 3,
        timeout: float = 10.0,
        pause: float = DEFAULT_PAUSE,
        backoff: float = DEFAULT_BACKOFF,
    ) -> None:
        self.client = client
        self.ingest_url = ingest_url
        self.hops = hops
        self.timeout = timeout
        self.pause = pause
        self.backoff = backoff
        self.payloads: list[dict] = []

    # -- the run ----------------------------------------------------------

    def run(self) -> RunSummary:
        """Crawl every source.  One source failing never stops the others."""
        counts = {
            key: 0
            for key in ("pages", "sent", Outcome.ACCEPTED, Outcome.DUPLICATE,
                        Outcome.REJECTED, Outcome.UNDELIVERED, Outcome.INVALID,
                        "pgp", "wallet")
        }
        relay_paths: dict[str, list[str]] = {}
        errors: list[str] = []

        for source in SOURCES:
            try:
                self._crawl(source, counts, relay_paths, errors)
            except OnionClientError as exc:
                # Section 6: a path request failing for one site skips that
                # site.  The next source still gets its turn.
                message = f"{source['source_id']}: {exc}"
                log.warning("skipping source -- %s", message)
                errors.append(message)

        return RunSummary(
            sources_attempted=len(SOURCES),
            pages_fetched=counts["pages"],
            artifacts_sent=counts["sent"],
            accepted=counts[Outcome.ACCEPTED],
            duplicate=counts[Outcome.DUPLICATE],
            rejected=counts[Outcome.REJECTED],
            undelivered=counts[Outcome.UNDELIVERED],
            invalid=counts[Outcome.INVALID],
            pgp=counts["pgp"],
            wallet=counts["wallet"],
            # Handles are never emitted as identifiers (SD-022).  The counter is
            # kept so a run that ever reported otherwise would be visibly wrong.
            handles=0,
            relay_paths=relay_paths,
            errors=errors,
        )

    def _crawl(
        self,
        source: dict[str, str],
        counts: dict[str, int],
        relay_paths: dict[str, list[str]],
        errors: list[str],
    ) -> None:
        """One source: index, then the routes the index names."""
        host = source["host"]
        path = self.client.get_path(self.hops)
        relay_paths[source["source_id"]] = [hop.relay_id for hop in path]

        index = self._fetch(path, host, extract.INDEX_ROUTE)
        if index is None:
            errors.append(f"{source['source_id']}: index page unavailable")
            return
        self._handle_page(source, extract.INDEX_ROUTE, index, counts, errors)

        for route in extract.discover_routes(index[0]):
            page = self._fetch(path, host, route)
            if page is None:
                errors.append(f"{source['source_id']}{route}: page unavailable")
                continue
            self._handle_page(source, route, page, counts, errors)

    def _fetch(
        self, path: list, host: str, route: str
    ) -> tuple[str, list[str]] | None:
        """Fetch one page through the relay chain.

        Returns ``(page, relay_path)``, or ``None`` when the page could not be
        carried -- section 6: log the hop, skip the page, keep going.
        """
        if self.pause:
            time.sleep(self.pause)
        try:
            response, trace = self.client.get_with_trace(path, host, route)
        except OnionClientError as exc:
            log.warning("%s%s could not be fetched: %s", host, route, exc)
            return None
        return extract.http_body(response), [hop.relay_id for hop in trace.path]

    def _handle_page(
        self,
        source: dict[str, str],
        route: str,
        fetched: tuple[str, list[str]],
        counts: dict[str, int],
        errors: list[str],
    ) -> None:
        page, relay_path = fetched
        counts["pages"] += 1

        payload = self.build_payload(source, route, page, relay_path)
        for entry in payload["identifiers"]:
            counts["pgp" if entry["type"] == "pgp_fingerprint" else "wallet"] += 1

        problems = contract.validate(payload)
        if problems:
            # A payload that does not conform is a bug in this scraper, not in
            # the corpus.  It is logged loudly and skipped, the same way a 400
            # is: one bad page never kills a run.
            for problem in problems:
                log.error("%s%s payload invalid -- %s", source["source_id"], route, problem)
            errors.append(f"{source['source_id']}{route}: payload failed validation")
            counts[Outcome.INVALID] += 1
            return

        self.payloads.append(payload)
        counts["sent"] += 1
        counts[self.deliver(payload, errors)] += 1

    # -- payload construction (contract section 3) ------------------------

    def build_payload(
        self,
        source: dict[str, str],
        route: str,
        page: str,
        relay_path: list[str],
    ) -> dict:
        """One artifact, exactly as `API_CONTRACT.md` section 3 defines it."""
        page_type = extract.classify(route)
        payload: dict = {
            "source_id": source["source_id"],
            "source_type": source["source_type"],
            "page_type": page_type,
            "url": f"http://{source['host']}{route}",
            "collected_at": utc_now(),
            "relay_path": list(relay_path),
            "raw_content": page,
            "content_hash": contract.content_hash(page),
            "identifiers": [],
        }

        if page_type == extract.PageType.ITEM:
            line = extract.byline(page)
            if line is not None:
                payload["persona"] = {
                    "handle": line.handle,
                    "observed_at": line.observed_at,
                }
                payload["identifiers"] = self._identifiers(page, line.observed_at)
        elif page_type == extract.PageType.PROFILE:
            # No post timestamp exists here, and none may be invented from a
            # join date or a latest post (SD-021.2).  So: persona, no
            # `observed_at`, and no identifiers.
            payload["persona"] = {"handle": extract.profile_handle(route)}

        return payload

    @staticmethod
    def _identifiers(page: str, observed_at: str) -> list[dict]:
        """Identifiers on an item page, each stamped with that item's timestamp.

        Only `pgp_fingerprint` and `wallet`.  A handle is not emitted here: it
        travels in `persona.handle`, and emitting it again would be tautological
        with the persona it hangs off (SD-022).

        Every value found is attributed to this page's author, which is sound
        because `MOCK_SITES_SPEC.md` section 2 rule 6 guarantees no page carries
        another persona's identifier.  A regex cannot tell "my address" from "I
        paid this address", so the guarantee has to live in the corpus.
        """
        entries = [
            {"type": "pgp_fingerprint", "value": value, "observed_at": observed_at}
            for value in extract.pgp_fingerprints(page)
        ]
        entries += [
            {"type": "wallet", "value": value, "observed_at": observed_at}
            for value in extract.wallets(page)
        ]
        return entries

    # -- delivery (contract section 4, spec section 6) --------------------

    def deliver(self, payload: dict, errors: list[str]) -> str:
        """POST one artifact and classify what came back.

        GOTHAMITE being absent, slow or broken never aborts the crawl.
        """
        attempts = 3  # the first try, then "retry twice with backoff"
        for attempt in range(1, attempts + 1):
            try:
                body = post_json(self.ingest_url, payload, timeout=self.timeout)
            except HttpError as exc:
                if exc.status is None:
                    log.warning("ingest unreachable, continuing: %s", exc)
                    errors.append("ingest unreachable")
                    return Outcome.UNDELIVERED
                if exc.status == 400:
                    log.error("ingest rejected %s: %s", payload["url"], exc.body)
                    errors.append(f"{payload['url']}: rejected 400")
                    return Outcome.REJECTED
                if 500 <= exc.status < 600:
                    if attempt < attempts:
                        time.sleep(self.backoff * attempt)
                        continue
                    log.error("ingest 5xx after %d attempts: %s", attempts, exc)
                    errors.append(f"{payload['url']}: 5xx after retries")
                    return Outcome.UNDELIVERED
                log.error("ingest returned unexpected HTTP %s", exc.status)
                errors.append(f"{payload['url']}: HTTP {exc.status}")
                return Outcome.UNDELIVERED

            if isinstance(body, dict) and body.get("reason") == "duplicate_content_hash":
                # Expected on a re-scrape, and not an error.
                return Outcome.DUPLICATE
            return Outcome.ACCEPTED

        return Outcome.UNDELIVERED  # unreachable, kept for exhaustiveness


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Crawl the mock sites through the relay chain and POST artifacts"
    )
    parser.add_argument(
        "--directory", default=os.environ.get("DIRECTORY_URL", "http://localhost:8000")
    )
    parser.add_argument("--ingest", default=os.environ.get("INGEST_URL", DEFAULT_INGEST_URL))
    parser.add_argument("--hops", type=int, default=3)
    parser.add_argument("--pause", type=float, default=DEFAULT_PAUSE)
    parser.add_argument(
        "--timeout", type=float, default=float(os.environ.get("HOP_TIMEOUT", "10"))
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="[scraper] %(message)s")

    agent = ScraperAgent(
        OnionClient(args.directory, timeout=args.timeout),
        ingest_url=args.ingest,
        hops=args.hops,
        timeout=args.timeout,
        pause=args.pause,
    )
    summary = agent.run()
    print(summary.render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
