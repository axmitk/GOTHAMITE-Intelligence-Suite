"""Deterministic synthetic adapters.

These produce reproducible normalized observations for the judge/demo without any
network I/O, key, or external tool. Each mirrors the *shape* of what its real
counterpart would return (MailAccess email OSINT, TorBot dark-web collection,
horus OSINT metadata) so the investigation workflow is exercised end to end while
every record is clearly marked synthetic.
"""
from __future__ import annotations

import hashlib

from backend.collection.base import (
    AdapterResult,
    CollectionAdapter,
    EnrichmentAdapter,
    Observation,
    SourceState,
    infer_kind,
)

# Fixed timestamp so demo output and screenshots are stable.
_AT = "2026-09-28T09:00:00Z"


def _seeded(value: str, mod: int) -> int:
    return int(hashlib.sha256(value.encode()).hexdigest(), 16) % mod


class SyntheticMailAccessAdapter(EnrichmentAdapter):
    """Email OSINT enrichment (models MailAccess, MIT). Synthetic findings only.

    Real MailAccess active-probing (account existence, SMTP/reset probing, proxy
    egress) is intentionally NOT modelled or invoked: out of scope for a
    defensive, authorization-gated platform.
    """

    name = "mailaccess"
    kinds = ("email",)

    def state(self) -> SourceState:
        return SourceState.SYNTHETIC

    def enrich(self, value: str, kind: str | None = None) -> AdapterResult:
        kind = kind or infer_kind(value)
        if kind != "email":
            return AdapterResult(self.name, SourceState.SYNTHETIC, [])
        local, _, domain = value.partition("@")
        breaches = _seeded(value, 4)
        obs = [
            Observation(
                adapter=self.name, source="MailAccess (synthetic)", source_type="email-osint",
                entity_kind="identity", value=local, relationship="identity_of", observed_at=_AT,
                confidence=0.6, provenance="Synthetic identity graph",
                synthetic=True,
                summary=f"Candidate identity handle derived from {value}.",
                attributes={"basis": "local-part", "email": value},
            ),
            Observation(
                adapter=self.name, source="MailAccess (synthetic)", source_type="email-osint",
                entity_kind="organization", value=domain, relationship="member_of", observed_at=_AT,
                confidence=0.5, provenance="Synthetic domain association",
                synthetic=True,
                summary=f"Email domain {domain} associated with the identity.",
                attributes={"domain": domain},
            ),
            Observation(
                adapter=self.name, source="MailAccess (synthetic)", source_type="email-osint",
                entity_kind="exposure", value=f"{value}#exposure", relationship="exposed_in", observed_at=_AT,
                confidence=0.55, provenance="Synthetic breach-exposure finding",
                synthetic=True,
                summary=(f"{breaches} synthetic breach exposure(s) reference this "
                         "address. Unverified; corroboration required."),
                attributes={"exposure_count": breaches, "verified": False,
                            "email": value},
            ),
        ]
        return AdapterResult(self.name, SourceState.SYNTHETIC, obs)


class SyntheticTorBotAdapter(CollectionAdapter):
    """Dark-web collection (models TorBot, GPL-3.0). Synthetic pages only.

    Real collection requires the process-isolated adapter, an explicit
    analyst-approved onion target, and live collection enabled. This synthetic
    adapter never contacts Tor.
    """

    name = "torbot"
    kinds = ("url", "domain")

    def state(self) -> SourceState:
        return SourceState.SYNTHETIC

    def collect(self, target: str, *, approved: bool = False) -> AdapterResult:
        if not approved:
            return AdapterResult(
                self.name, SourceState.UNAVAILABLE, [],
                error="Collection target not analyst-approved.")
        links = 2 + _seeded(target, 4)
        obs = [
            Observation(
                adapter=self.name, source="TorBot (synthetic)", source_type="dark-web", relationship="collected_from",
                entity_kind="url", value=target, observed_at=_AT,
                confidence=0.5, provenance="Synthetic onion crawl",
                synthetic=True,
                summary=f"Synthetic page metadata for approved target; {links} links extracted.",
                attributes={"title": "Synthetic hidden service", "live": False,
                            "link_count": links, "status": "reachable (synthetic)"},
            ),
        ]
        return AdapterResult(self.name, SourceState.SYNTHETIC, obs)


class SyntheticHorusAdapter(EnrichmentAdapter):
    """OSINT metadata enrichment (models horus, GPL-3.0). Passive subset only.

    Only passive metadata (domain/whois-style context) is modelled. Active
    scanning surfaces (nmap, packet capture) are intentionally excluded.
    """

    name = "horus"
    kinds = ("domain", "ip")

    def state(self) -> SourceState:
        return SourceState.SYNTHETIC

    def enrich(self, value: str, kind: str | None = None) -> AdapterResult:
        kind = kind or infer_kind(value)
        if kind not in self.kinds:
            return AdapterResult(self.name, SourceState.SYNTHETIC, [])
        obs = [
            Observation(
                adapter=self.name, source="horus (synthetic)", source_type="osint-metadata", relationship="registered_as",
                entity_kind=kind, value=value, observed_at=_AT,
                confidence=0.5, provenance="Synthetic passive metadata",
                synthetic=True,
                summary=f"Synthetic registration/hosting context for {value}.",
                attributes={"registrar": "Synthetic Registrar", "first_seen": _AT,
                            "passive_only": True},
            ),
        ]
        return AdapterResult(self.name, SourceState.SYNTHETIC, obs)
