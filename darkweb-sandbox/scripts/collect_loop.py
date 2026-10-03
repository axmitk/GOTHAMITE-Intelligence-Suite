"""Scheduled scrape-and-ingest loop over the simulated relay network.

Every ``--interval`` minutes, for ``--cycles`` cycles (0 runs until Ctrl+C):

1. crawl each source with ``ScraperAgent``, one source at a time, so a failure
   on one source is logged and the others still run;
2. the agent POSTs every page to GOTHAMITE's ``/api/v1/ingest``;
3. call the existing ``POST /api/v1/correlate``;
4. print a run summary with each source's status and last successful scan.

It targets a local ``backend.main`` and opens a workbench session first; the
session cookie and CSRF token travel on every request. It reaches only the
``.onion.mock`` sites, because that is all ``OnionClient`` can resolve.

``last_scan`` in the summary is the UTC time of this loop's last successful crawl
of that source. GOTHAMITE also records ``last_scan`` at ingest, but no API serves
it yet.
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import logging
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from client.onion_client import OnionClient, OnionClientError
from common.http_util import HttpError, post_json
from scraper.scraper_agent import (
    DEFAULT_PAUSE,
    SOURCES,
    Outcome,
    ScraperAgent,
)

log = logging.getLogger("collect_loop")

COUNT_KEYS = ("pages", "sent", Outcome.ACCEPTED, Outcome.DUPLICATE, Outcome.REJECTED,
              Outcome.UNDELIVERED, Outcome.INVALID, "pgp", "wallet")


@dataclass
class SourceResult:
    source_id: str
    status: str                    # ok | degraded | failed
    pages: int = 0
    accepted: int = 0
    duplicate: int = 0
    rejected: int = 0
    undelivered: int = 0
    error: str = ""
    last_scan: str | None = None   # last successful crawl in this loop


@dataclass
class CycleResult:
    number: int
    started_at: str
    sources: list[SourceResult] = field(default_factory=list)
    correlation: dict | None = None
    correlation_error: str = ""


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def crawl_source(agent: ScraperAgent, source: dict[str, str]) -> SourceResult:
    """Crawl one source through the agent; never raises."""
    counts = {key: 0 for key in COUNT_KEYS}
    relay_paths: dict[str, list[str]] = {}
    errors: list[str] = []
    try:
        agent._crawl(source, counts, relay_paths, errors)
    except OnionClientError as exc:
        return SourceResult(source["source_id"], "failed", error=f"relay path: {exc}")
    except Exception as exc:  # one source's bug must not stop the others
        log.exception("unexpected failure on %s", source["source_id"])
        return SourceResult(source["source_id"], "failed", error=f"{type(exc).__name__}: {exc}")

    result = SourceResult(
        source["source_id"], "ok", pages=counts["pages"],
        accepted=counts[Outcome.ACCEPTED], duplicate=counts[Outcome.DUPLICATE],
        rejected=counts[Outcome.REJECTED], undelivered=counts[Outcome.UNDELIVERED],
    )
    unavailable = [e for e in errors if "unavailable" in e or "unreachable" in e]
    if counts["pages"] == 0:
        result.status, result.error = "failed", "; ".join(errors) or "no pages fetched"
    elif unavailable or result.undelivered:
        result.status, result.error = "degraded", "; ".join(unavailable) or "pages not delivered"
    return result


class CollectLoop:
    def __init__(
        self,
        agent_factory: Callable[[], ScraperAgent],
        correlate: Callable[[], dict],
        sources=SOURCES,
        interval_s: float = 600.0,
        cycles: int = 0,
        monotonic: Callable[[], float] = time.monotonic,
        stamp: Callable[[], str] = utc_stamp,
        sleep: Callable[[float], None] = time.sleep,
        out: Callable[[str], None] = print,
    ) -> None:
        self.agent_factory = agent_factory
        self.correlate = correlate
        self.sources = sources
        self.interval_s = interval_s
        self.cycles = cycles
        self.monotonic = monotonic
        self.stamp = stamp
        self.sleep = sleep
        self.out = out
        self.last_scan: dict[str, str] = {}
        self.history: list[CycleResult] = []
        self.stopped_by_user = False

    def run_cycle(self, number: int) -> CycleResult:
        cycle = CycleResult(number, self.stamp())
        agent = self.agent_factory()
        for source in self.sources:
            result = crawl_source(agent, source)
            if result.status != "failed":
                self.last_scan[result.source_id] = self.stamp()
            else:
                log.warning("cycle %d: %s failed -- %s", number, result.source_id, result.error)
            result.last_scan = self.last_scan.get(result.source_id)
            cycle.sources.append(result)
        try:
            cycle.correlation = self.correlate()
        except (HttpError, OSError) as exc:
            cycle.correlation_error = str(exc)
            log.warning("cycle %d: correlation call failed -- %s", number, exc)
        self.history.append(cycle)
        return cycle

    def run(self) -> list[CycleResult]:
        number = 0
        try:
            while self.cycles == 0 or number < self.cycles:
                number += 1
                started = self.monotonic()
                self.out(render(self.run_cycle(number)))
                if self.cycles and number >= self.cycles:
                    break
                wait = max(0.0, self.interval_s - (self.monotonic() - started))
                self.out(f"next cycle in {wait:.0f}s")
                self.sleep(wait)
        except KeyboardInterrupt:
            self.stopped_by_user = True
            self.out(f"stopped by user after {len(self.history)} completed cycle(s)")
        return self.history


def render(cycle: CycleResult) -> str:
    lines = [f"=== CYCLE {cycle.number} started {cycle.started_at} ===",
             f"{'source':<18}{'status':<10}{'pages':>6}{'accepted':>10}{'duplicate':>11}"
             f"{'rejected':>10}{'undeliv.':>10}  last_scan"]
    for s in cycle.sources:
        lines.append(f"{s.source_id:<18}{s.status:<10}{s.pages:>6}{s.accepted:>10}{s.duplicate:>11}"
                     f"{s.rejected:>10}{s.undelivered:>10}  {s.last_scan or 'never'}")
        if s.error:
            lines.append(f"  {s.source_id} error: {s.error}")
    if cycle.correlation is not None:
        c = cycle.correlation
        lines.append(f"correlation: {c.get('evaluated_pairs')} pairs evaluated, "
                     f"{c.get('active_relationships')} active relationships")
        for edge in c.get("edges", []):
            lines.append(f"  {edge.get('from_handle')} -> {edge.get('to_handle')} "
                         f"{edge.get('type')} {edge.get('score')}")
    else:
        lines.append(f"correlation: not run ({cycle.correlation_error})")
    return "\n".join(lines)


def open_session(backend: str, timeout: float) -> str:
    """Get a workbench session; the cookie and CSRF header then go on every request."""
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    request = urllib.request.Request(
        f"{backend}/api/v1/workbench/session", data=b"", method="POST",
        headers={"x-gothamite-client": "workbench"},
    )
    with opener.open(request, timeout=timeout) as response:
        csrf = json.loads(response.read())["csrf"]
    if not any(cookie.name == "gothamite_demo" for cookie in jar):
        raise RuntimeError("session endpoint did not set the session cookie")
    opener.addheaders = [("X-CSRF-Token", csrf)]
    urllib.request.install_opener(opener)
    return csrf


def main() -> int:
    parser = argparse.ArgumentParser(description="Scheduled scrape, ingest and correlate loop (simulated network only)")
    parser.add_argument("--directory", default="http://directory:8000")
    parser.add_argument("--backend", default="http://127.0.0.1:8000", help="local backend.main base URL")
    parser.add_argument("--interval", type=float, default=10.0, help="minutes between cycle starts")
    parser.add_argument("--cycles", type=int, default=0, help="number of cycles; 0 runs until Ctrl+C")
    parser.add_argument("--hops", type=int, default=3)
    parser.add_argument("--pause", type=float, default=DEFAULT_PAUSE)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="[collect_loop] %(message)s")

    backend = args.backend.rstrip("/")
    open_session(backend, args.timeout)
    print(f"session opened on {backend}; interval {args.interval} min; "
          f"cycles {'until Ctrl+C' if args.cycles == 0 else args.cycles}")

    loop = CollectLoop(
        agent_factory=lambda: ScraperAgent(
            OnionClient(args.directory, timeout=args.timeout),
            ingest_url=f"{backend}/api/v1/ingest",
            hops=args.hops, timeout=args.timeout, pause=args.pause,
        ),
        correlate=lambda: post_json(f"{backend}/api/v1/correlate", {}, timeout=args.timeout * 6),
        interval_s=args.interval * 60,
        cycles=args.cycles,
    )
    loop.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
