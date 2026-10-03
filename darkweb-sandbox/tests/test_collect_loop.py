"""scripts/collect_loop.py with a fake agent and a fake clock. No network, no Docker."""

from __future__ import annotations

import unittest
import urllib.request

from client.onion_client import OnionClientError
from scraper.scraper_agent import SOURCES, Outcome
from scripts.collect_loop import BackendCsrfHeader, CollectLoop

PAGES_PER_SOURCE = 4
CYCLE_SECONDS = 5.0


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []
        self.stop_after_sleeps: int | None = None

    def monotonic(self) -> float:
        return self.now

    def stamp(self) -> str:
        return f"t+{self.now:06.1f}s"

    def sleep(self, seconds: float) -> None:
        if self.stop_after_sleeps is not None and len(self.sleeps) >= self.stop_after_sleeps:
            raise KeyboardInterrupt
        self.sleeps.append(seconds)
        self.now += seconds


class FakeAgent:
    """Stands in for ScraperAgent._crawl: pages are accepted once, duplicates after."""

    def __init__(self, world: "FakeWorld") -> None:
        self.world = world

    def _crawl(self, source, counts, relay_paths, errors) -> None:
        source_id = source["source_id"]
        self.world.events.append(("crawl", source_id))
        self.world.clock.now += CYCLE_SECONDS / len(SOURCES)
        if (self.world.cycle, source_id) in self.world.failures:
            raise OnionClientError("directory returned no path")
        for page in range(PAGES_PER_SOURCE):
            key = (source_id, page)
            counts["pages"] += 1
            counts["sent"] += 1
            if key in self.world.ingested:
                counts[Outcome.DUPLICATE] += 1
            else:
                self.world.ingested.add(key)
                counts[Outcome.ACCEPTED] += 1
            self.world.events.append(("ingest", source_id))


class FakeWorld:
    def __init__(self, failures=()) -> None:
        self.clock = FakeClock()
        self.events: list[tuple[str, str]] = []
        self.ingested: set = set()
        self.failures = set(failures)
        self.cycle = 0
        self.output: list[str] = []

    def agent_factory(self) -> FakeAgent:
        self.cycle += 1
        return FakeAgent(self)

    def correlate(self) -> dict:
        self.events.append(("correlate", ""))
        return {"evaluated_pairs": 12, "active_relationships": 2, "edges": []}

    def loop(self, cycles: int, interval_s: float = 60.0) -> CollectLoop:
        return CollectLoop(
            agent_factory=self.agent_factory, correlate=self.correlate,
            interval_s=interval_s, cycles=cycles, monotonic=self.clock.monotonic,
            stamp=self.clock.stamp, sleep=self.clock.sleep, out=self.output.append,
        )


class CollectLoopTests(unittest.TestCase):
    def test_interval_is_respected(self) -> None:
        world = FakeWorld()
        history = world.loop(cycles=3, interval_s=60.0).run()
        self.assertEqual(3, len(history))
        # Each cycle takes 5 s of fake time, so the loop waits the remaining 55 s,
        # and no wait follows the last cycle.
        self.assertEqual([55.0, 55.0], world.clock.sleeps)
        self.assertEqual(["t+0000.0s", "t+0060.0s", "t+0120.0s"], [c.started_at for c in history])

    def test_correlate_runs_after_ingest_each_cycle(self) -> None:
        world = FakeWorld()
        world.loop(cycles=2).run()
        correlate_at = [i for i, (kind, _) in enumerate(world.events) if kind == "correlate"]
        self.assertEqual(2, len(correlate_at))
        first_cycle = world.events[: correlate_at[0]]
        self.assertEqual(len(SOURCES) * PAGES_PER_SOURCE, sum(1 for kind, _ in first_cycle if kind == "ingest"))
        self.assertEqual(("correlate", ""), world.events[-1])

    def test_rerun_counts_duplicates(self) -> None:
        world = FakeWorld()
        first, second = world.loop(cycles=2).run()
        self.assertEqual([PAGES_PER_SOURCE] * len(SOURCES), [s.accepted for s in first.sources])
        self.assertEqual([0] * len(SOURCES), [s.duplicate for s in first.sources])
        self.assertEqual([0] * len(SOURCES), [s.accepted for s in second.sources])
        self.assertEqual([PAGES_PER_SOURCE] * len(SOURCES), [s.duplicate for s in second.sources])

    def test_one_failing_source_does_not_stop_the_others(self) -> None:
        failing = SOURCES[1]["source_id"]
        world = FakeWorld(failures={(2, failing)})
        first, second = world.loop(cycles=2).run()
        statuses = {s.source_id: s.status for s in second.sources}
        self.assertEqual("failed", statuses[failing])
        self.assertTrue(all(v == "ok" for k, v in statuses.items() if k != failing))
        # The source after the failing one was still crawled, and correlation still ran.
        self.assertIn(("crawl", SOURCES[2]["source_id"]), world.events[-(PAGES_PER_SOURCE + 2):])
        self.assertIsNotNone(second.correlation)
        # last_scan for the failed source keeps its previous successful value.
        failed = next(s for s in second.sources if s.source_id == failing)
        before = next(s for s in first.sources if s.source_id == failing)
        self.assertEqual(before.last_scan, failed.last_scan)
        self.assertIn("relay path", failed.error)

    def test_ctrl_c_stops_cleanly(self) -> None:
        world = FakeWorld()
        world.clock.stop_after_sleeps = 1  # Ctrl+C arrives during the second wait
        loop = world.loop(cycles=0)
        history = loop.run()
        self.assertTrue(loop.stopped_by_user)
        self.assertEqual(2, len(history))
        self.assertTrue(world.output[-1].startswith("stopped by user after 2 completed cycle(s)"))

    def test_csrf_header_goes_only_to_the_backend(self) -> None:
        handler = BackendCsrfHeader("http://host.docker.internal:8044", "token-123")
        backend = handler.http_request(urllib.request.Request("http://host.docker.internal:8044/api/v1/ingest"))
        directory = handler.http_request(urllib.request.Request("http://directory:8000/path?hops=3"))
        relay = handler.http_request(urllib.request.Request("http://relay-01:9001/"))
        self.assertEqual("token-123", backend.get_header("X-csrf-token"))
        self.assertIsNone(directory.get_header("X-csrf-token"))
        self.assertIsNone(relay.get_header("X-csrf-token"))

    def test_correlation_failure_is_reported_not_raised(self) -> None:
        world = FakeWorld()

        def broken() -> dict:
            raise OSError("backend unreachable")

        loop = world.loop(cycles=1)
        loop.correlate = broken
        (cycle,) = loop.run()
        self.assertIsNone(cycle.correlation)
        self.assertIn("backend unreachable", cycle.correlation_error)


if __name__ == "__main__":
    unittest.main()
