"""Process-isolated adapters for real, GPL-licensed tools.

These never import the third-party tools' code (GPL isolation) and never run
unless an operator has explicitly enabled live collection AND the specific
adapter. Absent that, ``state()`` is UNAVAILABLE and the call returns an
UNAVAILABLE result with no I/O. When enabled, the tool is invoked as a separate
process with a timeout, its stdout parsed into normalized observations, and any
failure captured as ``SourceState.ERROR`` — never raised into the core.

Only a minimal, defensive subset of each tool is exposed. No vendored source.
"""
from __future__ import annotations

import json
import shutil
import subprocess

from backend.collection.base import (
    AdapterResult,
    CollectionAdapter,
    EnrichmentAdapter,
    Observation,
    SourceState,
    infer_kind,
)
from backend.collection.config import config

_AT = "2026-09-28T09:00:00Z"


def _tool_present(command: str) -> bool:
    exe = command.split()[0] if command else ""
    return bool(exe) and (shutil.which(exe) is not None)


def _run(argv: list[str], timeout: float) -> tuple[int, str, str]:
    """Run an external tool in isolation. Returns (rc, stdout, stderr).

    stdin is closed and the environment is inherited but not extended with any
    secret. Callers treat a non-zero rc or timeout as ERROR.
    """
    proc = subprocess.run(  # noqa: S603 - argv is constructed, never shell=True
        argv, capture_output=True, text=True, timeout=timeout,
        stdin=subprocess.DEVNULL, check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


class _IsolatedBase:
    adapter_key: str = ""
    default_cmd: str = ""

    def _enabled(self) -> bool:
        return config.adapter_enabled(self.adapter_key)

    def _command(self) -> str:
        return config.tool_command(self.adapter_key, self.default_cmd)

    def _state(self) -> SourceState:
        if not self._enabled():
            return SourceState.UNAVAILABLE
        return SourceState.AVAILABLE if _tool_present(self._command()) else SourceState.UNAVAILABLE


class TorBotCollectionAdapter(_IsolatedBase, CollectionAdapter):
    """Dark-web collection via the isolated ``torbot`` CLI (GPL-3.0).

    Requires: live collection enabled, this adapter enabled, an installed
    ``torbot``, and an analyst-approved target. Never auto-crawls; one explicit
    target per call.
    """

    name = "torbot"
    kinds = ("url", "domain")
    adapter_key = "torbot"
    default_cmd = "torbot"

    def state(self) -> SourceState:
        return self._state()

    def collect(self, target: str, *, approved: bool = False) -> AdapterResult:
        if not self._enabled():
            return AdapterResult(self.name, SourceState.UNAVAILABLE, [],
                                 error="Live TorBot collection is disabled.")
        if not approved:
            return AdapterResult(self.name, SourceState.UNAVAILABLE, [],
                                 error="Collection target not analyst-approved.")
        if not _tool_present(self._command()):
            return AdapterResult(self.name, SourceState.UNAVAILABLE, [],
                                 error="torbot is not installed.")
        argv = self._command().split() + ["-u", target, "--info", "-q"]
        try:
            rc, out, err = _run(argv, config.subprocess_timeout)
        except subprocess.TimeoutExpired:
            return AdapterResult(self.name, SourceState.ERROR, [],
                                 error="torbot timed out.")
        except OSError as exc:
            return AdapterResult(self.name, SourceState.ERROR, [], error=str(exc))
        if rc != 0:
            return AdapterResult(self.name, SourceState.ERROR, [],
                                 error=(err or "torbot exited non-zero").strip()[:300])
        return AdapterResult(self.name, SourceState.CONNECTED,
                             self._parse(out, target))

    def _parse(self, out: str, target: str) -> list[Observation]:
        # TorBot JSON output shape varies by version; parse defensively and fall
        # back to a single reachable-page observation.
        links: list[str] = []
        title = ""
        try:
            data = json.loads(out)
            if isinstance(data, dict):
                title = str(data.get("title") or "")
                raw = data.get("links") or data.get("children") or []
                links = [str(x) for x in raw if isinstance(x, (str,))][:100]
        except (ValueError, TypeError):
            pass
        obs = [Observation(
            adapter=self.name, source="TorBot", source_type="dark-web", relationship="collected_from",
            collection_status="connected", entity_kind="url", value=target,
            observed_at=_AT, confidence=0.5, provenance="TorBot onion crawl (live)",
            synthetic=False,
            summary=f"Live page metadata; {len(links)} links extracted." if links
                    else "Live page reachable.",
            attributes={"title": title, "live": True, "link_count": len(links)},
        )]
        return obs


class HorusEnrichmentAdapter(_IsolatedBase, EnrichmentAdapter):
    """Passive OSINT metadata via the isolated ``horus`` CLI (GPL-3.0).

    Only passive lookups are invoked. Active scanning is never requested.
    """

    name = "horus"
    kinds = ("domain", "ip")
    adapter_key = "horus"
    default_cmd = "horus"

    def state(self) -> SourceState:
        return self._state()

    def enrich(self, value: str, kind: str | None = None) -> AdapterResult:
        kind = kind or infer_kind(value)
        if not self._enabled():
            return AdapterResult(self.name, SourceState.UNAVAILABLE, [],
                                 error="Live horus enrichment is disabled.")
        if kind not in self.kinds:
            return AdapterResult(self.name, SourceState.UNAVAILABLE, [])
        if not _tool_present(self._command()):
            return AdapterResult(self.name, SourceState.UNAVAILABLE, [],
                                 error="horus is not installed.")
        # Intentionally not implemented as a live call in this build: horus has no
        # stable machine-readable passive-only mode we can guarantee is scan-free,
        # so we do not shell out. Report AVAILABLE-but-unqueried instead of
        # risking an active operation.
        return AdapterResult(self.name, SourceState.AVAILABLE, [],
                             error="Live horus enrichment not wired (passive-only guard).")


class MailAccessEnrichmentAdapter(_IsolatedBase, EnrichmentAdapter):
    """Email OSINT via the isolated ``mailaccess`` CLI (MIT).

    Even though MailAccess is MIT (no copyleft isolation requirement), its active
    account-probing surface is out of scope for GOTHAMITE. This adapter is left
    disabled and unwired; the synthetic MailAccess adapter provides the findings
    shape for the demo. Enable and extend only under explicit authorization.
    """

    name = "mailaccess"
    kinds = ("email",)
    adapter_key = "mailaccess"
    default_cmd = "mailaccess"

    def state(self) -> SourceState:
        return self._state()

    def enrich(self, value: str, kind: str | None = None) -> AdapterResult:
        return AdapterResult(self.name, SourceState.UNAVAILABLE, [],
                             error="Live MailAccess enrichment not wired (active-probing out of scope).")
