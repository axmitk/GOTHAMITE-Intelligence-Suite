"""Collection configuration. Everything live is opt-in and off by default.

The judge/demo environment must be deterministic, so no adapter performs network
I/O unless an operator explicitly enables it here (via environment variables) and
provides an approved target. Absent configuration, adapters report SYNTHETIC or
UNAVAILABLE and serve fixtures.
"""
from __future__ import annotations

import os


def _flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


class CollectionConfig:
    """Reads adapter enablement from the environment at call time.

    Live adapters require BOTH a global opt-in and a per-adapter opt-in, so a
    single flag can never silently turn on live dark-web or OSINT collection.
    """

    @property
    def live_enabled(self) -> bool:
        """Master switch. When false (default) every adapter is synthetic-only."""
        return _flag("GOTHAMITE_LIVE_COLLECTION")

    def adapter_enabled(self, adapter: str) -> bool:
        if not self.live_enabled:
            return False
        return _flag(f"GOTHAMITE_ADAPTER_{adapter.upper()}")

    def tool_command(self, adapter: str, default: str) -> str:
        """Path/command for a process-isolated tool, overridable per deployment."""
        return os.getenv(f"GOTHAMITE_{adapter.upper()}_CMD", default)

    @property
    def deepdarkcti_path(self) -> str | None:
        """Filesystem path to a local deepdarkCTI clone, if the operator supplies
        one. The catalogue is GPL-3.0 and is never vendored into this repo."""
        path = os.getenv("GOTHAMITE_DEEPDARKCTI_PATH", "").strip()
        return path or None

    @property
    def subprocess_timeout(self) -> float:
        try:
            return float(os.getenv("GOTHAMITE_COLLECTION_TIMEOUT", "20"))
        except ValueError:
            return 20.0


config = CollectionConfig()
