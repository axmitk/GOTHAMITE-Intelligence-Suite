"""Phase-1 demo: run the whole pool locally and carry two requests through it.

This is the Docker-free way to see Phase 1 work. It starts the same directory,
relay and endpoint code the containers run, on loopback ports, then makes two
requests and shows that they took different paths.

    python -m scripts.phase1_demo

Nothing here contacts the network. Every socket is loopback.
"""

from __future__ import annotations

import logging
import sys

from client.onion_client import build_raw_request, resolve_mock_address
from tests.harness import MOCK_HOST, SandboxHarness


def show_visibility(harness: SandboxHarness, client, path) -> None:
    """Print what each hop can actually decrypt.

    RELAY_PROTOCOL.md section 6 says its visibility table is the acceptance
    test for this phase, and that it should be verified by inspecting what each
    relay actually decrypts rather than assumed. This does that inspection live.
    """
    import base64
    import json

    raw = build_raw_request(MOCK_HOST, "/")
    dest_host, dest_port = resolve_mock_address(MOCK_HOST)
    wire, _ = client.build_layers(path, dest_host, dest_port, raw)

    print("\n  what each relay can decrypt")
    print("  " + "-" * 60)
    for index, hop in enumerate(path):
        layer, _ = harness.peel(wire, hop)
        role = "entry " if index == 0 else ("exit  " if index == len(path) - 1 else "middle")
        sees_destination = layer["next_hop"] == "DESTINATION"
        detail = (
            f"destination={layer['next_host']}:{layer['next_port']}"
            if sees_destination
            else f"next_hop={layer['next_hop']}"
        )
        print(
            f"  {hop.relay_id} ({role}) -> {detail}"
            f"   sees_destination={'YES' if sees_destination else 'no'}"
            f"   sees_body={'YES' if sees_destination else 'no'}"
        )
        if sees_destination:
            break
        wire = json.loads(base64.b64decode(layer["payload"]).decode("utf-8"))
    print(
        "  the exit relay sees the destination and the request body. That is a\n"
        "  documented property of onion routing, not a defect in this build."
    )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="  %(message)s")

    print("=" * 68)
    print("  darkweb-sandbox -- Phase 1")
    print("  simulated onion-routed network: directory + relay pool")
    print("=" * 68)

    harness = SandboxHarness(relay_count=7)
    print("\nstarting directory, 7 relays and the Phase-1 endpoint ...")
    harness.start()
    print(f"directory listening on {harness.directory_url}")

    try:
        client = harness.client()

        relays = client.get_relays()
        print(f"\nregistered relays: {len(relays)}")
        for entry in relays:
            print(f"  {entry['relay_id']:<10} {entry['status']}")

        print("\n" + "-" * 68)
        print("  run 1 -- 3 hops")
        print("-" * 68)
        path_one = client.get_path(3)
        print("  path: " + " -> ".join(hop.relay_id for hop in path_one))
        show_visibility(harness, client, path_one)
        print("\n  carrying the request ...")
        body_one = client.get(path_one, MOCK_HOST, "/")
        print(f"\n  {len(body_one)} bytes returned, decrypted through 3 layers")
        print(f"  marker present: {b'phase1-endpoint-ok' in body_one}")

        print("\n" + "-" * 68)
        print("  run 2 -- 3 hops, fresh path")
        print("-" * 68)
        path_two = client.get_path(3)
        print("  path: " + " -> ".join(hop.relay_id for hop in path_two))
        print("\n  carrying the request ...")
        body_two = client.get(path_two, MOCK_HOST, "/")
        print(f"\n  {len(body_two)} bytes returned, decrypted through 3 layers")

        route_one = tuple(h.relay_id for h in path_one)
        route_two = tuple(h.relay_id for h in path_two)

        # Compare the page, not the raw response: http.server stamps a Date
        # header, so the full byte stream differs between two runs a second
        # apart. The page itself is what must be identical.
        page_one = body_one.split(b"\r\n\r\n", 1)[-1]
        page_two = body_two.split(b"\r\n\r\n", 1)[-1]

        print("\n" + "=" * 68)
        print(f"  run 1 path:  {' -> '.join(route_one)}")
        print(f"  run 2 path:  {' -> '.join(route_two)}")
        print(f"  paths differ: {route_one != route_two}")
        print(f"  page identical across both paths: {page_one == page_two}")
        print("=" * 68)
        return 0
    finally:
        print("\nstopping ...")
        harness.stop()


if __name__ == "__main__":
    sys.exit(main())
