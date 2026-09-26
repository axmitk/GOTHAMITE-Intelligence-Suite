"""Demo viewer for the simulated onion-routed network.

This proxy acts as a visual browser for the presenter. It receives HTTP
requests on a local port, negotiates a fresh relay path via `OnionClient`,
fetches the mock site content through the relays, rewrites root-relative
links so navigation stays within the viewer, and serves the result.

It strictly enforces that only known `.onion.mock` addresses are visited.
It executes no JS and strips no content.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from client.onion_client import MOCK_ADDRESS_MAP, OnionClient, OnionClientError

log = logging.getLogger("demo-viewer")

# The root landing page for the presenter
LANDING_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Demo Viewer -- darkweb-sandbox</title>
<style>
  body { font-family: monospace; max-width: 800px; margin: 40px auto; line-height: 1.6; }
  h1 { border-bottom: 1px solid #ccc; padding-bottom: 10px; }
  li { margin-bottom: 10px; }
</style>
</head>
<body>
<h1>Simulated Onion Viewer</h1>
<p>This viewer acts as a gateway. Every link you click below will be fetched by requesting a fresh 3-hop path from the directory and pulling the data through the relays.</p>
<h2>Known Mock Sites:</h2>
<ul>
  <li><a href="/alpha7fq2mx9k.onion.mock/">alpha7fq2mx9k.onion.mock</a> (forum-alpha)</li>
  <li><a href="/beta4np8vz3wc.onion.mock/">beta4np8vz3wc.onion.mock</a> (marketplace-beta)</li>
  <li><a href="/gamma2xd6bt5hy.onion.mock/">gamma2xd6bt5hy.onion.mock</a> (forum-gamma)</li>
</ul>
</body>
</html>
"""

def rewrite_links(html: bytes, mock_host: str) -> bytes:
    """Rewrite root-relative links to prefix them with the mock host.
    
    e.g., href="/thread/12" -> href="/alpha7fq2mx9k.onion.mock/thread/12"
    """
    decoded = html.decode("utf-8", errors="replace")
    # Matches href="/something" or href="/"
    rewritten = re.sub(r'href="/([^"]*)"', rf'href="/{mock_host}/\1"', decoded)
    return rewritten.encode("utf-8")

class ViewerHandler(BaseHTTPRequestHandler):
    client: OnionClient  # set by build_server

    def do_GET(self) -> None:  # noqa: N802
        path = self.path
        
        if path == "/":
            self._send(200, LANDING_PAGE.encode("utf-8"), "text/html; charset=utf-8")
            return
            
        if path == "/health":
            self._send(200, b"ok", "text/plain")
            return

        # Path format: /<mock_host>/<resource>
        parts = path.strip("/").split("/", 1)
        mock_host = parts[0]
        resource = "/" + parts[1] if len(parts) > 1 else "/"

        if mock_host not in MOCK_ADDRESS_MAP:
            self._send(403, f"Host {mock_host} not in allowlist.".encode(), "text/plain")
            return

        try:
            relay_path = self.client.get_path(3)
            raw_body = self.client.get(relay_path, mock_host, resource)
        except OnionClientError as exc:
            log.error("Fetch failed: %s", exc)
            self._send(502, f"Gateway Error: {exc}".encode(), "text/plain")
            return

        # Rewrite links so clicking them stays within the viewer
        rewritten = rewrite_links(raw_body, mock_host)
        
        path_str = " -> ".join(node.relay_id for node in relay_path)
        self._send(200, rewritten, "text/html; charset=utf-8", headers={"X-Relay-Path": path_str})

    def _send(self, status: int, payload: bytes, content_type: str, headers: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'")
        if headers:
            for k, v in headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(payload)

def build_server(host: str, port: int, client: OnionClient) -> ThreadingHTTPServer:
    handler = type("BoundViewerHandler", (ViewerHandler,), {"client": client})
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server

def main() -> None:
    parser = argparse.ArgumentParser(description="Visual demo viewer proxy")
    parser.add_argument("--bind", default=os.environ.get("VIEWER_BIND", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("VIEWER_PORT", "8080")))
    parser.add_argument("--directory", default=os.environ.get("DIRECTORY_URL", "http://directory:8000"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="[viewer] %(message)s")
    
    client = OnionClient(args.directory)
    server = build_server(args.bind, args.port, client)
    
    log.info("Demo viewer listening on http://%s:%d", args.bind, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
