"""Negative tests: an identifier quoted by someone else is not an identity link.

The scraper attributes every wallet and PGP fingerprint on a page to the page's
author. It records mentions, not ownership. A scam-warning post that quotes the
scammer's wallet or key therefore attaches that identifier to the person warning
about them. These tests pin down what the correlation pass does with that.

Two cases are known limitations and are marked xfail(strict=True): if a future
change fixes them, the suite fails until the marker is removed.
"""
import hashlib
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db import Base
from backend.models.entities import Persona, Relationship
from backend.services.correlation_service import CorrelationService
from backend.services.ingest_service import IngestService

SCAM_WALLET = "1Fq8mT3kW9vR2nB6xL4pD7sJcY5hGzAe"
SCAM_PGP = "C0FFEE00112233445566778899AABBCCDDEEFF00"
SCAM_PGP_BLOCK = (
    "-----BEGIN PGP PUBLIC KEY BLOCK-----\n"
    "Fingerprint: C0FF EE00 1122 3344 5566 7788 99AA BBCC DDEE FF00\n"
    "-----END PGP PUBLIC KEY BLOCK-----"
)


def utc(day: str) -> datetime:
    return datetime.fromisoformat(day).replace(tzinfo=timezone.utc)


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        yield session
    finally:
        session.close()


def post(db, source_id, source_type, handle, day, body, identifiers):
    IngestService.process_ingest(
        db,
        source_id=source_id,
        source_type=source_type,
        url=f"{source_id}.onion.mock/{handle}/{day}",
        collected_at=utc(day),
        relay_path=["relay-1", "relay-2", "relay-3"],
        raw_content=body,
        content_hash="sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest(),
        persona_handle=handle,
        persona_observed_at=utc(day),
        identifiers_data=[{"type": t, "value": v, "observed_at": utc(day)} for t, v in identifiers],
    )


def seed_scammer(db):
    """A vendor active 1 Jan to 1 Mar 2026 on a marketplace, with its own key and wallet."""
    for day in ("2026-01-01", "2026-03-01"):
        post(db, "market-a", "marketplace", "vendor_x", day,
             f"<p>vendor_x listing {day}. pay to {SCAM_WALLET}</p>\n{SCAM_PGP_BLOCK}",
             [("wallet", SCAM_WALLET), ("pgp_fingerprint", SCAM_PGP)])


def warning_post(db, day, quoted):
    body = f"<p>warning: vendor_x took my money and vanished. do not pay {quoted}</p>"
    ident_type = "pgp_fingerprint" if quoted == SCAM_PGP_BLOCK else "wallet"
    value = SCAM_PGP if ident_type == "pgp_fingerprint" else quoted
    post(db, "forum-b", "forum", "burned_buyer", day, body, [(ident_type, value)])


def identity_edge(db):
    handles = {p.persona_id: p.handle for p in db.query(Persona).all()}
    for rel in db.query(Relationship).filter_by(type="same_actor_suspected").all():
        if {handles[rel.from_persona_id], handles[rel.to_persona_id]} == {"vendor_x", "burned_buyer"}:
            return rel
    return None


def test_quoted_wallet_alone_creates_no_edge(db):
    """Warning posted 61 days after the vendor went quiet: the wallet is the only shared signal.

    Under the old wallet weight (0.45) this produced a same_actor_suspected edge.
    At 0.25 it stays below the 0.30 threshold.
    """
    seed_scammer(db)
    warning_post(db, "2026-05-01", SCAM_WALLET)
    CorrelationService.run_correlation(db)
    assert identity_edge(db) is None


def test_quoted_wallet_during_vendor_activity_creates_no_edge(db):
    """Warning posted while the vendor is still active: the overlap penalty also applies."""
    seed_scammer(db)
    warning_post(db, "2026-02-01", SCAM_WALLET)
    CorrelationService.run_correlation(db)
    assert identity_edge(db) is None


@pytest.mark.xfail(strict=True, reason=(
    "Known limitation: a warning posted within 45 days after the vendor's last post scores "
    "wallet 0.25 + succession 0.15 = 0.40 and links. Fix needs mention-vs-ownership extraction."))
def test_quoted_wallet_soon_after_vendor_exit_creates_no_edge(db):
    seed_scammer(db)
    warning_post(db, "2026-03-20", SCAM_WALLET)
    CorrelationService.run_correlation(db)
    assert identity_edge(db) is None


@pytest.mark.xfail(strict=True, reason=(
    "Known limitation: a quoted PGP key block scores 0.70 on its own, and a shared key also "
    "suppresses the overlap penalty. Fix needs mention-vs-ownership extraction."))
def test_quoted_pgp_key_creates_no_edge(db):
    seed_scammer(db)
    warning_post(db, "2026-02-01", SCAM_PGP_BLOCK)
    CorrelationService.run_correlation(db)
    assert identity_edge(db) is None
