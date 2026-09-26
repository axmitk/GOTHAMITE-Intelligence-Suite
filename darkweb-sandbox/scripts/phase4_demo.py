"""Phase-4 demo: fetch the three mock sites through the relay chain.

Docker-free. Starts the directory, seven relays and all three mock sites on
loopback ports, then crawls each site by its `.onion.mock` address through a
fresh 3-hop path and shows what a scraper would find.

    python -m scripts.phase4_demo

Nothing here contacts the network. Every socket is loopback.

**On the ground truth printed at the end.** The planted-link summary is read
straight out of `mock_sites.seed_data` -- it is the sandbox operator's view, and
it is what makes the demo checkable: you can see what GOTHAMITE *should* find
before it finds it. It is deliberately not available through the ingestion seam;
GOTHAMITE receives only scraped artifacts and must derive the links itself. No
scoring, correlation or attribution happens in this file or anywhere else in this
repository.
"""

from __future__ import annotations

import sys

from mock_sites import seed_data
from tests.harness import SITE_ADDRESSES, SandboxHarness

WALLET_LABEL = {
    seed_data.WALLET_A: "wallet-A  (A1 + A2, shared)",
    seed_data.WALLET_B: "wallet-B  (B1 + B2, shared)",
    seed_data.WALLET_C1: "wallet-C1 (decoy, shared with nobody)",
    seed_data.WALLET_D1: "wallet-D1 (D1's own)",
}


def crawl_site(client, site_id: str) -> dict[str, object]:
    """Fetch every page of one site through a fresh path per request."""
    site = seed_data.SITES[site_id]
    address = site.address
    pages: list[tuple[str, bytes]] = []
    paths: set[tuple[str, ...]] = set()

    path = client.get_path(3)
    paths.add(tuple(h.relay_id for h in path))
    pages.append(("/", client.get(path, address, "/")))

    for post in seed_data.posts_for_site(site_id):
        resource = f"/{site.item_path}/{post.post_id}"
        path = client.get_path(3)
        paths.add(tuple(h.relay_id for h in path))
        pages.append((resource, client.get(path, address, resource)))

    for persona in seed_data.personas_for_site(site_id):
        resource = f"/user/{persona.handle}"
        path = client.get_path(3)
        paths.add(tuple(h.relay_id for h in path))
        pages.append((resource, client.get(path, address, resource)))

    text = "\n".join(body.decode("utf-8", "replace") for _, body in pages)
    return {"pages": pages, "paths": paths, "text": text}


def main() -> int:
    print("=" * 72)
    print("  darkweb-sandbox -- Phase 4")
    print("  three synthetic mock sites, reached through the relay pool")
    print("=" * 72)

    harness = SandboxHarness(relay_count=7, with_sites=True)
    print("\nstarting directory, 7 relays and 3 mock sites ...")
    harness.start()

    try:
        client = harness.client()
        results: dict[str, dict[str, object]] = {}

        for site_id in seed_data.SITES:
            site = seed_data.SITES[site_id]
            print("\n" + "-" * 72)
            print(f"  {site.site_id}  ({site.kind})   {site.address}")
            print("-" * 72)

            result = crawl_site(client, site_id)
            results[site_id] = result
            pages = result["pages"]  # type: ignore[index]
            paths = result["paths"]  # type: ignore[index]
            text = result["text"]  # type: ignore[index]

            print(f"  {len(pages)} pages fetched through {len(paths)} distinct relay paths")
            print("  example path: " + " -> ".join(sorted(paths)[0]))

            for persona in seed_data.personas_for_site(site_id):
                posts = seed_data.posts_for_handle(persona.handle)
                pgp_pages = sum(1 for p in posts if p.pgp)
                wallet_pages = sum(1 for p in posts if p.wallets)
                print(
                    f"    {persona.handle:<14} {len(posts)} posts   "
                    f"{persona.active_from} -> {persona.active_to}   "
                    f"PGP on {pgp_pages}, wallet on {wallet_pages}"
                )

            found = sorted({w for w in WALLET_LABEL if w in text})
            for wallet in found:
                print(f"    carries {WALLET_LABEL[wallet]}")

        print("\n" + "=" * 72)
        print("  planted ground truth -- what GOTHAMITE should derive")
        print("=" * 72)
        print("  A1 nightjar   <-> A2 n1ghtjar_    same PGP AND same wallet")
        print("  B1 quillfeather -> B2 quill_v2    same wallet, DIFFERENT PGP (rotated)")
        b1_last = max(p.observed_at for p in seed_data.posts_for_handle("quillfeather"))
        b2_first = min(p.observed_at for p in seed_data.posts_for_handle("quill_v2"))
        print(f"                                    B1 last {b1_last}")
        print(f"                                    B2 first {b2_first}  (17 days)")
        print("  C1 nightjarr  vs  A1 nightjar     handle differs by one character,")
        print("                                    activity overlaps, shares NOTHING.")
        print("                                    This one must NOT link.")
        print("  D1 bellwether  vs  A2 n1ghtjar_   same marketplace, overlapping")
        print("                                    activity, shares NOTHING.")
        print("                                    This one must NOT link either.")
        print("=" * 72)
        print("  The sites are observation sources. Deriving these links from the")
        print("  scraped artifacts is GOTHAMITE's job, and nothing above is")
        print("  reachable through the ingestion seam.")
        print("=" * 72)
        return 0
    finally:
        print("\nstopping ...")
        harness.stop()


if __name__ == "__main__":
    sys.exit(main())
