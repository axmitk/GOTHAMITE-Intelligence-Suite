"""The Phase-1 static endpoint (SD-012).

``AgentsDocs/IMPLEMENTATION_PLAN.md`` section 3 asks Phase 1 for "one trivial
mock endpoint (a static page is fine -- the real sites come in Phase 4)".  This
is that endpoint and nothing more.

It is **not a mock site.**  It carries no persona, no handle, no PGP block and
no wallet address.  The seed data in ``AgentsDocs/DATA_MODEL.md`` section 4 is
the demo's ground truth and ``MOCK_SITES_SPEC.md`` section 2 rule 5 requires it
character-exact in the Phase-4 sites; a throwaway second copy here is exactly
how a character-level drift would get introduced.

**Delete this package at Phase 4**, when ``forum-alpha``, ``marketplace-beta``
and ``forum-gamma`` replace it.

Addressed as ``phase1sandbox.onion.mock``.  Like every address in this
repository that is a mock address, not a real onion address, and it is not
reachable from the host -- only through the relay chain.
"""

from __future__ import annotations

import argparse
import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

log = logging.getLogger("phase1-endpoint")

# Byte-identical on every request and every restart.  Phase-1 verification
# compares the bytes that come back through the relay chain against this
# constant, so it must not contain a timestamp, a counter or anything else
# that varies.
PAGE = b"""<!DOCTYPE html>
<html>
<head><title>Phase 1 sandbox endpoint</title></head>
<body>
<h1>Phase 1 sandbox endpoint</h1>
<p>This page was served through the simulated onion-routed network.</p>
<p>It is a connectivity target for Phase 1 only. It carries no synthetic
persona content; the mock forums and marketplace arrive in Phase 4.</p>
<p id="marker">phase1-endpoint-ok</p>
</body>
</html>
"""


class StaticHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "phase1-endpoint"
    sys_version = ""

    def log_message(self, fmt, *args):  # noqa: A003, ANN001
        # One quiet line per request; the default writes the full request line
        # to stderr, which clutters the relay log panes during a demo.
        log.info("served %s", self.path)

    def do_GET(self):  # noqa: N802 - stdlib naming
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(PAGE)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(PAGE)
            return

        body = b"not found\n"
        self.send_response(404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)


def build_server(host: str, port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), StaticHandler)
    server.daemon_threads = True
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase-1 static endpoint")
    parser.add_argument("--host", default=os.environ.get("ENDPOINT_BIND", "0.0.0.0"))
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("ENDPOINT_PORT", "80"))
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="[phase1-endpoint] %(message)s")

    server = build_server(args.host, args.port)
    log.info("listening on %s:%d", args.host, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("shutting down")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
