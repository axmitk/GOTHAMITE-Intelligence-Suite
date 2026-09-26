"""The mock-site HTTP server.

One module serves all three sites; which one it is comes from `SITE_ID`.  They
differ only in content, so three near-identical apps would be three chances to
let the content drift apart.

    SITE_ID=forum-alpha python -m mock_sites.site_server

Standard library only -- `MOCK_SITES_SPEC.md` section 3 says "Flask (or
equivalent)", and `SPEC_DECISIONS.md` SD-005 already fixed the equivalent for
this repository as `http.server`.  Adding a framework here would add a
dependency the rest of the system does not have.

These are observation sources and nothing more.  There is no scoring, no
correlation, no attribution and no profiling in this file, and none belongs
here: that is GOTHAMITE's work, downstream of the ingestion seam.

Nothing in this module opens an outbound connection.  It serves hardcoded bytes
from `mock_sites.seed_data` and never fetches, imports or resolves anything at
request time.
"""

from __future__ import annotations

import html
import logging
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from mock_sites import seed_data
from mock_sites.seed_data import Post, Site

LOG = logging.getLogger("mock-site")

# Deterministic output is an acceptance criterion (MOCK_SITES_SPEC.md section 7
# item 7: "identical bytes every time").  A stdlib HTTP server stamps a Date
# header, which would make the response bytes differ between two runs a second
# apart even when the page is identical.  See SPEC_DECISIONS.md SD-019.
SERVER_TOKEN = "mock-site"


def _page(site: Site, title: str, body: str) -> bytes:
    """Wrap page content in the shared shell.

    Deterministic: no timestamp, no counter, no request-derived value anywhere
    in the output.
    """
    document = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)} -- {html.escape(site.name)}</title>
</head>
<body>
<header>
<h1>{html.escape(site.name)}</h1>
<p class="tagline">{html.escape(site.tagline)}</p>
<p class="address">{html.escape(site.address)}</p>
</header>
<main>
{body}
</main>
<footer>
<p>Synthetic sandbox content. Every handle, key and address on this site is
invented for a correlation demonstration and refers to no real person, service
or wallet.</p>
</footer>
</body>
</html>
"""
    return document.encode("utf-8")


def _pgp_block(fingerprint: str) -> str:
    """A realistic-looking block carrying the fingerprint.

    No real key material -- `MOCK_SITES_SPEC.md` section 4 says placeholder text
    inside the block is correct and sufficient, and generating a real key would
    be both pointless and a liability.
    """
    spaced = seed_data.format_fingerprint(fingerprint)
    return (
        "<pre class=\"pgp\">-----BEGIN PGP PUBLIC KEY BLOCK-----\n"
        f"Fingerprint: {html.escape(spaced)}\n"
        "\n"
        "[synthetic key material -- not a real key, not usable for anything]\n"
        "-----END PGP PUBLIC KEY BLOCK-----</pre>"
    )


def render_index(site: Site) -> bytes:
    rows = []
    for post in seed_data.posts_for_site(site.site_id):
        href = f"/{site.item_path}/{post.post_id}"
        rows.append(
            f'<li><a href="{href}">{html.escape(post.title)}</a> '
            f"&mdash; {html.escape(post.handle)} "
            f"&mdash; {html.escape(post.observed_at)}</li>"
        )
    handles = [
        f'<li><a href="/user/{html.escape(p.handle)}">{html.escape(p.handle)}</a></li>'
        for p in seed_data.personas_for_site(site.site_id)
    ]
    body = (
        f"<h2>{html.escape(site.item_word)}</h2>\n<ul>\n"
        + "\n".join(rows)
        + "\n</ul>\n<h2>Users</h2>\n<ul>\n"
        + "\n".join(handles)
        + "\n</ul>"
    )
    return _page(site, site.item_word, body)


def render_item(site: Site, post: Post) -> bytes:
    """A thread or listing page.

    Identifiers go in the body text, never into attributes or metadata
    (`MOCK_SITES_SPEC.md` section 2 rule 4), so extraction has to parse prose.
    """
    parts = [
        f"<article>\n<h2>{html.escape(post.title)}</h2>",
        '<p class="byline">'
        f'Posted by <a href="/user/{html.escape(post.handle)}">{html.escape(post.handle)}</a>'
        f" on <time>{html.escape(post.observed_at)}</time></p>",
        f"<div class=\"body\"><p>{html.escape(post.body)}</p></div>",
    ]
    if post.pgp:
        parts.append(_pgp_block(post.pgp))
    parts.append("</article>")
    parts.append(f'<p><a href="/">Back to {html.escape(site.item_word.lower())}</a></p>')
    return _page(site, post.title, "\n".join(parts))


def render_profile(site: Site, handle: str) -> bytes:
    persona = seed_data.persona_by_handle(handle)
    posts = [p for p in seed_data.posts_for_handle(handle) if p.site_id == site.site_id]
    if persona is None or persona.site_id != site.site_id or not posts:
        return b""
    rows = "\n".join(
        f'<li><a href="/{site.item_path}/{p.post_id}">{html.escape(p.title)}</a> '
        f"&mdash; <time>{html.escape(p.observed_at)}</time></li>"
        for p in posts
    )
    body = (
        f"<h2>{html.escape(persona.handle)}</h2>\n"
        f'<p class="joined">Joined {html.escape(persona.active_from)}</p>\n'
        f'<p class="postcount">{len(posts)} posts</p>\n'
        f"<h3>Posts</h3>\n<ul>\n{rows}\n</ul>"
    )
    return _page(site, persona.handle, body)


class SiteHandler(BaseHTTPRequestHandler):
    """Serves the three page types from `MOCK_SITES_SPEC.md` section 4."""

    protocol_version = "HTTP/1.1"
    site: Site  # set by build_server

    # The stdlib logs every request line to stderr.  Relay logs are already
    # constrained by RELAY_PROTOCOL.md section 8; a mock site echoing full
    # request paths adds nothing and only creates somewhere for content to leak
    # into logs.
    def log_message(self, fmt: str, *args: object) -> None:  # noqa: A002
        return

    def send_response(self, code: int, message: str | None = None) -> None:
        """Respond without a Date header, so output is byte-identical.

        `MOCK_SITES_SPEC.md` section 7 item 7 requires identical bytes on every
        run.  The stdlib's Date header would break that for the full response
        even when the page is unchanged.  Everything these sites serve is
        hardcoded, so there is nothing for a caching header to be right about.
        """
        self.log_request(code)
        self.send_response_only(code, message)
        self.send_header("Server", SERVER_TOKEN)

    def _send(self, status: int, payload: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(payload)

    def _not_found(self) -> None:
        page = _page(self.site, "Not found", "<h2>Not found</h2>")
        self._send(404, page, "text/html; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802
        site = self.site
        path = self.path.split("?", 1)[0].rstrip("/") or "/"

        if path == "/":
            self._send(200, render_index(site), "text/html; charset=utf-8")
            return

        if path == "/health":
            self._send(200, b"ok", "text/plain; charset=utf-8")
            return

        segments = path.strip("/").split("/")
        if len(segments) == 2 and segments[0] == site.item_path:
            try:
                post_id = int(segments[1])
            except ValueError:
                self._not_found()
                return
            post = seed_data.find_post(site.site_id, post_id)
            if post is None:
                self._not_found()
                return
            self._send(200, render_item(site, post), "text/html; charset=utf-8")
            return

        if len(segments) == 2 and segments[0] == "user":
            page = render_profile(site, segments[1])
            if not page:
                self._not_found()
                return
            self._send(200, page, "text/html; charset=utf-8")
            return

        self._not_found()


def build_server(site_id: str, host: str, port: int) -> ThreadingHTTPServer:
    """A server for one site, bound but not yet serving.

    Port 0 asks the OS for a free port, which is how the tests run all three
    sites alongside the relay pool in one process.
    """
    if site_id not in seed_data.SITES:
        raise ValueError(f"unknown site_id {site_id!r}; expected one of {sorted(seed_data.SITES)}")
    site = seed_data.SITES[site_id]
    handler = type("BoundSiteHandler", (SiteHandler,), {"site": site})
    return ThreadingHTTPServer((host, port), handler)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
    site_id = os.environ.get("SITE_ID", "")
    if site_id not in seed_data.SITES:
        LOG.error("SITE_ID must be one of %s, got %r", sorted(seed_data.SITES), site_id)
        return 2
    host = os.environ.get("SITE_BIND", "0.0.0.0")  # noqa: S104 -- internal network only
    port = int(os.environ.get("SITE_PORT", "80"))
    server = build_server(site_id, host, port)
    site = seed_data.SITES[site_id]
    LOG.info(
        "%s (%s) serving %d posts on %s:%d as %s",
        site.site_id,
        site.kind,
        len(seed_data.posts_for_site(site_id)),
        host,
        port,
        site.address,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
