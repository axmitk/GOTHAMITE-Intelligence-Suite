#!/usr/bin/env python3
"""
Seed script for GOTHAMITE test benchmark vectors (DATA_MODEL.md §4).
Loads synthetic personas, raw source artifacts, and identifiers directly into SQLite.
Idempotent and safe for repeat executions.
"""

import hashlib
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.db import init_db, SessionLocal, engine
from backend.models.entities import Source, Artifact, Persona, Identifier


def parse_iso(dt_str: str) -> datetime:
    """Parses an ISO 8601 UTC string into a timezone-aware datetime."""
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))


def ensure_utc(dt: datetime) -> datetime:
    """Ensures datetime is timezone-aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def compute_hash(content: str) -> str:
    """Computes sha256:hex digest for raw content bytes."""
    return f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}"


def normalize_pgp(pgp: str) -> str:
    """Normalizes PGP fingerprint: uppercase, stripped whitespace."""
    clean = "".join(pgp.split()).upper()
    if len(clean) != 40 or not all(c in "0123456789ABCDEF" for c in clean):
        raise ValueError(f"Invalid PGP fingerprint format: {pgp}")
    return clean


# Canonical sources per DATA_MODEL.md §2 & §4
SOURCES_DATA = [
    {
        "source_id": "forum-alpha",
        "type": "forum",
        "reliability": "high",
        "status": "up",
        "last_scan": parse_iso("2026-08-25T12:00:00Z"),
    },
    {
        "source_id": "marketplace-beta",
        "type": "marketplace",
        "reliability": "high",
        "status": "up",
        "last_scan": parse_iso("2026-08-25T14:30:00Z"),
    },
    {
        "source_id": "forum-gamma",
        "type": "forum",
        "reliability": "medium",
        "status": "up",
        "last_scan": parse_iso("2026-08-25T16:45:00Z"),
    },
]

# Benchmark persona definitions per DATA_MODEL.md §4
PERSONAS_DATA = [
    # Actor A: Strong PGP + Wallet Link (Headline result)
    {
        "actor_group": "A1",
        "handle": "nightjar",
        "source_id": "forum-alpha",
        "first_seen": "2026-01-08T10:00:00Z",
        "last_seen": "2026-08-20T18:30:00Z",
        "post_count": 12,
        "pgp": "9F2A4C81D3E5B7069A1C4F82D6E30B57A4C19E8D",
        "wallet": "1Hx4kQ9mVn2RtYbP7sLdF3wCgN8jZaEuT6",
        "url": "alpha7fq2mx9k.onion.mock/thread/14",
        "raw_content": (
            "<html><body>\n"
            "<div class='post' id='p-1042'>\n"
            "  <h3>Post by nightjar (2026-03-11 09:14:00 UTC)</h3>\n"
            "  <p>Public verification key for all direct escrow disputes:</p>\n"
            "  <pre>-----BEGIN PGP PUBLIC KEY BLOCK-----\n"
            "Fingerprint: 9F2A 4C81 D3E5 B706 9A1C  4F82 D6E3 0B57 A4C1 9E8D\n"
            "-----END PGP PUBLIC KEY BLOCK-----</pre>\n"
            "  <p>Deposit BTC payments to: 1Hx4kQ9mVn2RtYbP7sLdF3wCgN8jZaEuT6</p>\n"
            "</div>\n"
            "</body></html>"
        ),
        "relay_path": ["relay-05", "relay-02", "relay-07"],
        "observed_at": "2026-03-11T09:14:00Z",
    },
    {
        "actor_group": "A2",
        "handle": "n1ghtjar_",
        "source_id": "marketplace-beta",
        "first_seen": "2026-02-14T11:00:00Z",
        "last_seen": "2026-08-22T20:15:00Z",
        "post_count": 15,
        "pgp": "9F2A4C81D3E5B7069A1C4F82D6E30B57A4C19E8D",
        "wallet": "1Hx4kQ9mVn2RtYbP7sLdF3wCgN8jZaEuT6",
        "url": "beta3kx8pm2v.onion.mock/vendor/n1ghtjar_",
        "raw_content": (
            "<html><body>\n"
            "<div class='vendor-profile'>\n"
            "  <h2>Vendor: n1ghtjar_</h2>\n"
            "  <p>Trusted supplier. Verify signatures using my canonical PGP fingerprint:</p>\n"
            "  <code>9F2A 4C81 D3E5 B706 9A1C 4F82 D6E3 0B57 A4C1 9E8D</code>\n"
            "  <p>Default settlement wallet: 1Hx4kQ9mVn2RtYbP7sLdF3wCgN8jZaEuT6</p>\n"
            "</div>\n"
            "</body></html>"
        ),
        "relay_path": ["relay-01", "relay-04", "relay-02"],
        "observed_at": "2026-02-14T11:00:00Z",
    },

    # Actor B: Rebrand / Migration (Shared Wallet + Temporal Succession, Rotated PGP)
    {
        "actor_group": "B1",
        "handle": "quillfeather",
        "source_id": "forum-alpha",
        "first_seen": "2026-01-20T08:00:00Z",
        "last_seen": "2026-04-02T19:00:00Z",
        "post_count": 9,
        "pgp": "3B77E1A9C4D28F60B5E3A17C9D42F8E06B1A5C93",
        "wallet": "1Kp7dR3zXw9QfM4vB2nHtL6sYcJ8gAeU5o",
        "url": "alpha7fq2mx9k.onion.mock/thread/88",
        "raw_content": (
            "<html><body>\n"
            "<div class='post' id='p-3091'>\n"
            "  <h3>Post by quillfeather (2026-04-02 19:00:00 UTC)</h3>\n"
            "  <p>Final dispatch notice. Forum-alpha operations closing today.</p>\n"
            "  <p>PGP: 3B77E1A9C4D28F60B5E3A17C9D42F8E06B1A5C93</p>\n"
            "  <p>Treasury wallet: 1Kp7dR3zXw9QfM4vB2nHtL6sYcJ8gAeU5o</p>\n"
            "</div>\n"
            "</body></html>"
        ),
        "relay_path": ["relay-03", "relay-06", "relay-08"],
        "observed_at": "2026-04-02T19:00:00Z",
    },
    {
        "actor_group": "B2",
        "handle": "quill_v2",
        "source_id": "forum-gamma",
        "first_seen": "2026-04-19T14:00:00Z",
        "last_seen": "2026-08-18T17:00:00Z",
        "post_count": 11,
        "pgp": "E4C08B21F7A6D93E5C1B84027FA36D9E1C05B872",
        "wallet": "1Kp7dR3zXw9QfM4vB2nHtL6sYcJ8gAeU5o",
        "url": "gamma9zl4qw1c.onion.mock/thread/05",
        "raw_content": (
            "<html><body>\n"
            "<div class='post' id='p-5012'>\n"
            "  <h3>Post by quill_v2 (2026-04-19 14:00:00 UTC)</h3>\n"
            "  <p>New presence established on forum-gamma. Old PGP retired, key rotated.</p>\n"
            "  <p>New PGP: E4C08B21F7A6D93E5C1B84027FA36D9E1C05B872</p>\n"
            "  <p>Same Bitcoin settlement address: 1Kp7dR3zXw9QfM4vB2nHtL6sYcJ8gAeU5o</p>\n"
            "</div>\n"
            "</body></html>"
        ),
        "relay_path": ["relay-02", "relay-07", "relay-01"],
        "observed_at": "2026-04-19T14:00:00Z",
    },

    # Actor C: Decoy (Must NOT link — handle similarity + activity overlap conflict)
    {
        "actor_group": "C1",
        "handle": "nightjarr",
        "source_id": "forum-gamma",
        "first_seen": "2026-03-01T09:00:00Z",
        "last_seen": "2026-08-21T18:00:00Z",
        "post_count": 8,
        "pgp": "7D19F4C8B302A6E5D91C7B48F0A2E63D5C81B94F",
        "wallet": "1Qs2fT8yWn5LpX3mK9vGdC7bJ4hRzAeN1u",
        "url": "gamma9zl4qw1c.onion.mock/thread/77",
        "raw_content": (
            "<html><body>\n"
            "<div class='post' id='p-7701'>\n"
            "  <h3>Post by nightjarr (2026-03-01 09:00:00 UTC)</h3>\n"
            "  <p>Independent security consultant. Not affiliated with anyone on forum-alpha.</p>\n"
            "  <p>PGP: 7D19F4C8B302A6E5D91C7B48F0A2E63D5C81B94F</p>\n"
            "  <p>Wallet: 1Qs2fT8yWn5LpX3mK9vGdC7bJ4hRzAeN1u</p>\n"
            "</div>\n"
            "</body></html>"
        ),
        "relay_path": ["relay-04", "relay-03", "relay-05"],
        "observed_at": "2026-03-01T09:00:00Z",
    },

    # Actor D: Transaction Edge Only (transacted_with, not same_actor_suspected)
    {
        "actor_group": "D1",
        "handle": "bellwether",
        "source_id": "marketplace-beta",
        "first_seen": "2026-02-01T12:00:00Z",
        "last_seen": "2026-08-19T16:00:00Z",
        "post_count": 10,
        "pgp": "A50C3E97B14D6F82093C5A7E1BD48F620E93C7A1",
        "wallet": "1Zr6bN4qJm8VhT2xD5cWfP9sLgY3kEuA7i",
        "url": "beta3kx8pm2v.onion.mock/feedback/thread/42",
        "raw_content": (
            "<html><body>\n"
            "<div class='review'>\n"
            "  <h3>Review by bellwether (2026-05-10 15:30:00 UTC)</h3>\n"
            "  <p>Payment escrow cleared. Transferred 0.85 BTC to n1ghtjar_ at 1Hx4kQ9mVn2RtYbP7sLdF3wCgN8jZaEuT6.</p>\n"
            "  <p>My escrow release wallet: 1Zr6bN4qJm8VhT2xD5cWfP9sLgY3kEuA7i</p>\n"
            "  <p>Buyer PGP: A50C3E97B14D6F82093C5A7E1BD48F620E93C7A1</p>\n"
            "</div>\n"
            "</body></html>"
        ),
        "relay_path": ["relay-08", "relay-01", "relay-06"],
        "observed_at": "2026-05-10T15:30:00Z",
        "transacted_target_wallet": "1Hx4kQ9mVn2RtYbP7sLdF3wCgN8jZaEuT6",
    },
]


def seed_database(session):
    """Inserts or updates sources, artifacts, personas, and identifiers idempotently."""
    print("[*] Initializing sources...")
    for s_data in SOURCES_DATA:
        source = session.query(Source).filter_by(source_id=s_data["source_id"]).first()
        if not source:
            source = Source(**s_data)
            session.add(source)
        else:
            source.type = s_data["type"]
            source.reliability = s_data["reliability"]
            source.status = s_data["status"]
            source.last_scan = s_data["last_scan"]
    session.flush()

    print("[*] Seeding benchmark personas, artifacts, and identifiers...")
    personas_created = 0
    artifacts_created = 0
    identifiers_created = 0

    for p_def in PERSONAS_DATA:
        # 1. Artifact (Immutable Evidence Locker)
        c_hash = compute_hash(p_def["raw_content"])
        artifact = (
            session.query(Artifact)
            .filter_by(source_id=p_def["source_id"], content_hash=c_hash)
            .first()
        )
        if not artifact:
            artifact = Artifact(
                artifact_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{p_def['source_id']}:{p_def['url']}")),
                source_id=p_def["source_id"],
                url=p_def["url"],
                raw_content=p_def["raw_content"],
                content_hash=c_hash,
                collected_at=parse_iso(p_def["observed_at"]),
                relay_path=p_def["relay_path"],
            )
            session.add(artifact)
            session.flush()
            artifacts_created += 1

        # 2. Persona
        persona = (
            session.query(Persona)
            .filter_by(handle=p_def["handle"], source_id=p_def["source_id"])
            .first()
        )
        if not persona:
            persona = Persona(
                persona_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{p_def['handle']}@{p_def['source_id']}")),
                handle=p_def["handle"],
                source_id=p_def["source_id"],
                first_seen=parse_iso(p_def["first_seen"]),
                last_seen=parse_iso(p_def["last_seen"]),
                post_count=p_def["post_count"],
            )
            session.add(persona)
            session.flush()
            personas_created += 1
        else:
            # Widen observation window if needed
            new_first = parse_iso(p_def["first_seen"])
            new_last = parse_iso(p_def["last_seen"])
            curr_first = ensure_utc(persona.first_seen)
            curr_last = ensure_utc(persona.last_seen)
            if new_first < curr_first:
                persona.first_seen = new_first
            if new_last > curr_last:
                persona.last_seen = new_last
            persona.post_count = p_def["post_count"]
            session.flush()

        # 3. Identifiers (PGP & Wallet)
        clean_pgp = normalize_pgp(p_def["pgp"])
        pgp_ident = (
            session.query(Identifier)
            .filter_by(
                persona_id=persona.persona_id,
                type="pgp_fingerprint",
                value=clean_pgp,
            )
            .first()
        )
        if not pgp_ident:
            pgp_ident = Identifier(
                identifier_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{persona.persona_id}:pgp:{clean_pgp}")),
                type="pgp_fingerprint",
                value=clean_pgp,
                persona_id=persona.persona_id,
                artifact_id=artifact.artifact_id,
                observed_at=parse_iso(p_def["observed_at"]),
            )
            session.add(pgp_ident)
            identifiers_created += 1

        raw_wallet = p_def["wallet"].strip()
        wallet_ident = (
            session.query(Identifier)
            .filter_by(
                persona_id=persona.persona_id,
                type="wallet",
                value=raw_wallet,
            )
            .first()
        )
        if not wallet_ident:
            wallet_ident = Identifier(
                identifier_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{persona.persona_id}:wallet:{raw_wallet}")),
                type="wallet",
                value=raw_wallet,
                persona_id=persona.persona_id,
                artifact_id=artifact.artifact_id,
                observed_at=parse_iso(p_def["observed_at"]),
            )
            session.add(wallet_ident)
            identifiers_created += 1

        # Optional transaction reference identifier for Actor D
        if "transacted_target_wallet" in p_def:
            tx_wallet = p_def["transacted_target_wallet"].strip()
            tx_ident = (
                session.query(Identifier)
                .filter_by(
                    persona_id=persona.persona_id,
                    type="contact",
                    value=f"transacted_with_wallet:{tx_wallet}",
                )
                .first()
            )
            if not tx_ident:
                tx_ident = Identifier(
                    identifier_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{persona.persona_id}:contact:{tx_wallet}")),
                    type="contact",
                    value=f"transacted_with_wallet:{tx_wallet}",
                    persona_id=persona.persona_id,
                    artifact_id=artifact.artifact_id,
                    observed_at=parse_iso(p_def["observed_at"]),
                )
                session.add(tx_ident)
                identifiers_created += 1

    session.commit()
    print(f"[✓] Seeding complete: {personas_created} new personas, {artifacts_created} new artifacts, {identifiers_created} new identifiers.")


def verify_seed_invariants(session):
    """Verifies that the database state strictly satisfies Phase 1 acceptance criteria."""
    print("\n--- Running Phase 1 Acceptance Checks ---")

    # 1. Total Personas Count == 6
    personas = session.query(Persona).all()
    assert len(personas) == 6, f"Expected 6 personas, found {len(personas)}"
    print(f"[✓] Criterion 1 & 3: Exactly 6 personas present: {[p.handle for p in personas]}")

    # Map handles to personas
    by_handle = {p.handle: p for p in personas}

    # 2. Check PGP Normalization (Criterion 4)
    identifiers = session.query(Identifier).all()
    for ident in identifiers:
        if ident.type == "pgp_fingerprint":
            assert len(ident.value) == 40, f"PGP fingerprint not 40 chars: {ident.value}"
            assert ident.value.isupper(), f"PGP fingerprint not uppercase: {ident.value}"
            assert " " not in ident.value, f"PGP fingerprint has whitespace: {ident.value}"
        # Foreign Key requirement check (Criterion 2)
        assert ident.persona_id is not None, "Identifier missing persona_id"
        assert ident.artifact_id is not None, "Identifier missing artifact_id"
    print(f"[✓] Criterion 2 & 4: Identifiers correctly linked to persona and artifact; PGP uppercase 40 hex chars.")

    # 3. Check A1/A2 share PGP and wallet (Criterion 6)
    a1 = by_handle["nightjar"]
    a2 = by_handle["n1ghtjar_"]
    a1_pgp = {i.value for i in a1.identifiers if i.type == "pgp_fingerprint"}
    a2_pgp = {i.value for i in a2.identifiers if i.type == "pgp_fingerprint"}
    a1_wallet = {i.value for i in a1.identifiers if i.type == "wallet"}
    a2_wallet = {i.value for i in a2.identifiers if i.type == "wallet"}

    assert a1_pgp == a2_pgp and len(a1_pgp) == 1, f"A1 and A2 must share identical PGP: {a1_pgp} vs {a2_pgp}"
    assert a1_wallet == a2_wallet and len(a1_wallet) == 1, f"A1 and A2 must share identical wallet: {a1_wallet} vs {a2_wallet}"
    print(f"[✓] Criterion 6a: A1 (nightjar) and A2 (n1ghtjar_) share PGP and wallet.")

    # 4. Check B1/B2 share wallet only; PGP rotated (Criterion 6)
    b1 = by_handle["quillfeather"]
    b2 = by_handle["quill_v2"]
    b1_pgp = {i.value for i in b1.identifiers if i.type == "pgp_fingerprint"}
    b2_pgp = {i.value for i in b2.identifiers if i.type == "pgp_fingerprint"}
    b1_wallet = {i.value for i in b1.identifiers if i.type == "wallet"}
    b2_wallet = {i.value for i in b2.identifiers if i.type == "wallet"}

    assert b1_wallet == b2_wallet and len(b1_wallet) == 1, f"B1 and B2 must share wallet: {b1_wallet} vs {b2_wallet}"
    assert b1_pgp != b2_pgp, f"B1 and B2 must have rotated PGP keys (different): {b1_pgp} vs {b2_pgp}"
    print(f"[✓] Criterion 6b: B1 (quillfeather) and B2 (quill_v2) share wallet only (PGP is rotated/different).")

    # 5. Check C1 shares nothing with A1 or B1 (Criterion 6)
    c1 = by_handle["nightjarr"]
    c1_pgp = {i.value for i in c1.identifiers if i.type == "pgp_fingerprint"}
    c1_wallet = {i.value for i in c1.identifiers if i.type == "wallet"}

    assert not (c1_pgp & a1_pgp), "C1 must not share PGP with A1"
    assert not (c1_wallet & a1_wallet), "C1 must not share wallet with A1"
    assert not (c1_pgp & b1_pgp), "C1 must not share PGP with B1"
    assert not (c1_wallet & b1_wallet), "C1 must not share wallet with B1"
    print(f"[✓] Criterion 6c: C1 (nightjarr) shares no PGP or wallet with A1 or B1.")

    print("\n[✓✓✓] ALL PHASE 1 ACCEPTANCE CHECKS PASSED SUCCESSFULLY!\n")


def main():
    print("[*] Initializing database schema...")
    init_db()
    session = SessionLocal()
    try:
        seed_database(session)
        verify_seed_invariants(session)
    finally:
        session.close()


if __name__ == "__main__":
    main()
