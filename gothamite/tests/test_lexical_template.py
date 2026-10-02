"""A quoted wallet on pages that share a site template must not become an identity link.

The pages below use the same shell as the sandbox mock sites (header, tagline,
address, footer disclaimer), as a scraper would capture them. The warning post
appears more than 45 days after the vendor's last post, so the quoted wallet
(+0.25) is the only identity signal and must stay below the 0.30 threshold.
"""
import hashlib
import html
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db import Base
from backend.models.entities import Evidence, Persona, Relationship
from backend.services.correlation_service import CorrelationService
from backend.services.ingest_service import IngestService

VENDOR_WALLET = "1Fq8mT3kW9vR2nB6xL4pD7sJcY5hGzAe"


def page(site_name, tagline, address, title, handle, posted, body):
    """Same shell as darkweb-sandbox/mock_sites/site_server.py `_page` + `render_item`."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)} -- {html.escape(site_name)}</title>
</head>
<body>
<header>
<h1>{html.escape(site_name)}</h1>
<p class="tagline">{html.escape(tagline)}</p>
<p class="address">{html.escape(address)}</p>
</header>
<main>
<article>
<h2>{html.escape(title)}</h2>
<p class="byline">Posted by <a href="/user/{handle}">{handle}</a> on <time>{posted}</time></p>
<div class="body"><p>{html.escape(body)}</p></div>
</article>
<p><a href="/">Back to threads</a></p>
</main>
<footer>
<p>Synthetic sandbox content. Every handle, key and address on this site is
invented for a correlation demonstration and refers to no real person, service
or wallet.</p>
</footer>
</body>
</html>
"""


VENDOR_PAGES = [
    ("2026-01-05T10:00:00Z", "Bulk listing, January",
     f"Restocked for January. Payment to {VENDOR_WALLET} only, escrow accepted on orders above the usual size. "
     "Turnaround is three days from confirmation. Message before ordering if you need it split."),
    ("2026-02-20T16:30:00Z", "Pausing new orders",
     f"Pausing new orders for a few weeks while I clear the queue. Existing orders paid to {VENDOR_WALLET} "
     "will still go out. I will post here when I reopen."),
]
WARNING_PAGE = ("2026-05-02T08:15:00Z", "Warning about vendor_x",
                f"Warning for anyone still waiting on vendor_x. I paid {VENDOR_WALLET} in February and nothing ever "
                "arrived, and the account went silent after that. Do not send anything to that address. Report it "
                "if you were caught as well.")


def utc(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def ingest(db, source_id, source_type, site, handle, posted, title, body):
    raw = page(*site, title, handle, posted, body)
    IngestService.process_ingest(
        db, source_id=source_id, source_type=source_type,
        url=f"http://{site[2]}/thread/{abs(hash(title)) % 1000}", collected_at=utc(posted),
        relay_path=["relay-01", "relay-04", "relay-02"], raw_content=raw,
        content_hash="sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        persona_handle=handle, persona_observed_at=utc(posted),
        identifiers_data=[{"type": "wallet", "value": VENDOR_WALLET, "observed_at": utc(posted)}],
    )


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        yield session
    finally:
        session.close()


def test_quoted_wallet_on_shared_template_creates_no_edge(db):
    market = ("Beta Market", "Listings, escrow, and vendor feedback.", "beta4np8vz3wc.onion.mock")
    forum = ("Alpha Board", "General discussion and vendor threads.", "alpha7fq2mx9k.onion.mock")
    for posted, title, body in VENDOR_PAGES:
        ingest(db, "marketplace-beta", "marketplace", market, "vendor_x", posted, title, body)
    ingest(db, "forum-alpha", "forum", forum, "burned_buyer", *WARNING_PAGE)

    CorrelationService.run_correlation(db)

    handles = {p.persona_id: p.handle for p in db.query(Persona).all()}
    edges = [r for r in db.query(Relationship).filter_by(type="same_actor_suspected").all()
             if {handles[r.from_persona_id], handles[r.to_persona_id]} == {"vendor_x", "burned_buyer"}]
    detail = [(e.signal_type, e.weight) for r in edges for e in db.query(Evidence).filter_by(relationship_id=r.relationship_id)]
    assert not edges, f"false identity edge at score {edges[0].score}: {detail}"
