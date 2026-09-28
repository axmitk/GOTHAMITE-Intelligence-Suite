"""Normalization, safety filtering and defensive entity extraction.

Used both by ``scripts/prepare_datasets.py`` (snapshot preparation) and by the
runtime importer (a second validation pass). Pure functions, no network I/O.

Safety rules (applied before anything becomes a GOTHAMITE observation):
- Redaction placeholders such as ``[EMAIL]`` are treated as markers, never as
  entities, and are never "recovered".
- Content with credentials, secrets, card numbers, contact details, key material,
  encoded blobs or executable content is suppressed. Only its SHA-256 is kept.
- URLs are stripped from excerpts so no access or download path is re-published.
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
from datetime import datetime

TRANSFORMATION_VERSION = "gothamite-ds-1.0"

REDACTION = re.compile(r"\[(?:[A-Z][A-Z_]{1,30})\]")
_URL = re.compile(r"(?:https?://|hxxps?://|www\.)\S+", re.I)
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE = re.compile(r"(?:\+?\d[\d\s().-]{8,}\d)")
_CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
_SECRET_WORD = re.compile(
    r"\b(pass(word|wd)?|pwd|api[_ -]?key|secret|token|bearer|auth(orization)?[:=]|"
    r"private key|ssh-rsa|cookie|session[_ ]?id|login:|combo ?list)\b", re.I)
_KEY_BLOCK = re.compile(r"-----BEGIN [A-Z ]*KEY-----")
_B64 = re.compile(r"\b[A-Za-z0-9+/]{80,}={0,2}")
_HEXBLOB = re.compile(r"\b[a-fA-F0-9]{40,}\b")
_EXEC = re.compile(r"(MZ\x90|\\x4d\\x5a|powershell\s+-e|<script|eval\(|base64 -d|curl .*\| *sh)", re.I)

# Hosts that name a service, not a victim organization.
_NON_ORG = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "live.com", "icloud.com",
    "mail.ru", "yandex.ru", "proton.me", "protonmail.com", "t.me", "telegram.org",
    "mega.nz", "gofile.io", "pixeldrain.com", "anonfiles.com", "pastebin.com",
    "github.com", "google.com", "youtube.com", "facebook.com", "twitter.com", "x.com",
    "instagram.com", "discord.gg", "discord.com", "bit.ly", "breachforums.st",
    "darkforums.st", "example.com",
}
_MULTI_SUFFIX = {"co.uk", "org.uk", "ac.uk", "gov.uk", "co.id", "ac.id", "go.id", "or.id",
                 "com.br", "gov.br", "co.za", "com.au", "co.in", "gov.in", "nic.in",
                 "co.jp", "com.mx", "com.tr", "com.ua", "gov.ua", "com.my", "com.ph"}
_DOMAIN = re.compile(r"\b((?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24})\b")
_VERSIONISH = re.compile(r"^\d+(\.\d+)+$")

COUNTRIES = [
    "Afghanistan", "Argentina", "Australia", "Bangladesh", "Brazil", "Canada", "Chile",
    "China", "Colombia", "Egypt", "France", "Germany", "India", "Indonesia", "Iran",
    "Israel", "Italy", "Japan", "Kenya", "Malaysia", "Mexico", "Morocco", "Nigeria",
    "Pakistan", "Peru", "Philippines", "Poland", "Russia", "Saudi Arabia", "Singapore",
    "South Africa", "South Korea", "Spain", "Sri Lanka", "Thailand", "Turkey", "Ukraine",
    "United Kingdom", "United States", "USA", "UK", "Vietnam",
]
_CANON = {c.lower(): c for c in COUNTRIES}
_COUNTRY = re.compile(r"\b(" + "|".join(re.escape(c) for c in COUNTRIES) + r")\b", re.I)
_CVE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.I)
_CWE = re.compile(r"\bCWE-\d{1,4}\b", re.I)
_ATTACK = re.compile(r"\bT1\d{3}(?:\.\d{3})?\b")


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _luhn(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d = d * 2 - 9 if d > 4 else d * 2
        total, alt = total + d, not alt
    return total % 10 == 0


def safety_reasons(text: str) -> list[str]:
    """Reasons a piece of content must not be displayed. Empty list = safe."""
    reasons = []
    if REDACTION.search(text):
        reasons.append("contains redacted personal data")
    if _SECRET_WORD.search(text) or _KEY_BLOCK.search(text):
        reasons.append("credential or secret reference")
    if _EMAIL.search(text):
        reasons.append("contact detail (email)")
    if _PHONE.search(_URL.sub(" ", text)):
        reasons.append("contact detail (phone-like number)")
    if _IBAN.search(text):
        reasons.append("financial account number")
    for m in _CARD.finditer(text):
        digits = re.sub(r"\D", "", m.group(0))
        if 13 <= len(digits) <= 19 and _luhn(digits):
            reasons.append("payment card number")
            break
    if _B64.search(text) or _HEXBLOB.search(text):
        reasons.append("encoded blob or key material")
    if _EXEC.search(text):
        reasons.append("executable or script content")
    return sorted(set(reasons))


def excerpt(text: str, limit: int = 180) -> tuple[str | None, list[str]]:
    """Safe display excerpt, or (None, reasons) when the content is suppressed.
    URLs are removed before the length cap so no access path is republished."""
    reasons = safety_reasons(text)
    if reasons:
        return None, reasons
    clean = re.sub(r"\s+", " ", _URL.sub("[link removed]", text)).strip()
    if not clean:
        return None, ["empty"]
    return (clean[:limit].rstrip() + ("…" if len(clean) > limit else "")), []


_SLD = {"gov", "gob", "go", "co", "com", "ac", "org", "edu", "net", "or", "mil", "nic", "ne", "sch"}


def is_public_suffix(value: str) -> bool:
    parts = value.split(".")
    return value in _MULTI_SUFFIX or (len(parts) == 2 and parts[0] in _SLD and len(parts[1]) == 2)


def registered_domain(host: str) -> str:
    parts = host.lower().strip(".").split(".")
    if parts[0] == "www" and len(parts) > 2:
        parts = parts[1:]
    if len(parts) >= 3 and is_public_suffix(".".join(parts[-2:])):
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def refang(value: str) -> str:
    return value.strip().replace("[.]", ".").replace("(.)", ".").replace("hxxp", "http")


def extract_entities(text: str) -> dict[str, list[str]]:
    """Defensive CTI entities only. Redaction markers are removed first, so a
    placeholder can never be mistaken for (or used to infer) a value."""
    clean = REDACTION.sub(" ", text)
    clean_nourl_emails = _EMAIL.sub(" ", clean)
    domains = set()
    for m in _DOMAIN.finditer(clean_nourl_emails.lower()):
        host = m.group(1)
        if _VERSIONISH.match(host) or host.split(".")[-1].isdigit():
            continue
        reg = registered_domain(host)
        if reg in _NON_ORG or is_public_suffix(reg) or len(reg) < 5:
            continue
        domains.add(reg)
    countries = set()
    for m in _COUNTRY.finditer(clean):
        c = m.group(1).lower()
        countries.add({"usa": "United States", "uk": "United Kingdom"}.get(c, _CANON[c]))
    return {
        "domain": sorted(domains),
        "country": sorted(countries),
        "cve": sorted({v.upper() for v in _CVE.findall(clean)}),
        "cwe": sorted({v.upper() for v in _CWE.findall(clean)}),
        "attack_technique": sorted(set(_ATTACK.findall(clean))),
    }


def parse_forum_date(value: str | None) -> tuple[str | None, str]:
    """Corpus dates look like ``04-08-23, 07:01 PM`` (DD-MM-YY). Relative values
    (``Less than 1 minute ago``) have no recoverable date and return None."""
    if not value:
        return None, "missing"
    try:
        dt = datetime.strptime(value.strip(), "%d-%m-%y, %I:%M %p")
        return dt.strftime("%Y-%m-%dT%H:%M:00Z"), "source"
    except ValueError:
        return None, "relative or unparseable in source"


def normalize_forum_thread(raw: dict) -> dict | None:
    """One corpus thread -> filtered snapshot record, or None if unusable."""
    if not isinstance(raw, dict) or not raw.get("thread_id") or not raw.get("title"):
        return None
    title = str(raw["title"])
    title_safe, title_reasons = excerpt(title, 160)
    if title_safe is None and "contains redacted personal data" not in title_reasons:
        return None  # a title carrying secrets/contact data is dropped entirely
    text = title + "\n" + "\n".join(str(p.get("content", "")) for p in raw.get("posts") or [] if isinstance(p, dict))
    date, basis = parse_forum_date(raw.get("date_posted"))
    posts = []
    for p in raw.get("posts") or []:
        if not isinstance(p, dict) or not p.get("post_id"):
            continue
        content = str(p.get("content", ""))
        shown, reasons = excerpt(content)
        pdate, pbasis = parse_forum_date(p.get("post_date"))
        posts.append({
            "post_id": str(p["post_id"]),
            "post_number": str(p.get("post_number", "")),
            "post_date": pdate, "post_date_basis": pbasis,
            "excerpt": shown, "suppressed": shown is None,
            "suppression_reasons": reasons,
            "content_sha256": sha256(content),
            "entities": extract_entities(content),
        })
    return {
        "thread_id": str(raw["thread_id"]),
        "title": title_safe or REDACTION.sub("[redacted]", title),
        "category": str(raw.get("category", "")),
        "forum_name": str(raw.get("forum_name", "")),
        "date_posted": date, "date_basis": basis,
        "posts": posts,
        "entities": extract_entities(text),
    }


_TYPE_MAP = {"ip": "ip", "ipv4": "ip", "domain": "domain", "url": "url",
             "sha256": "hash", "hash": "hash", "email": "email"}


def normalize_infoblox_rows(text: str, report: str) -> tuple[list[dict], int]:
    """Parse one Infoblox indicator CSV. Returns (records, rejected_count).
    Handles BOM headers, defanged values and a missing ``detected_date``."""
    records, rejected = [], 0
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    for row in reader:
        row = {(k or "").strip().lstrip("﻿").lower(): (v or "").strip() for k, v in row.items()}
        kind = _TYPE_MAP.get(row.get("type", "").lower())
        value = refang(row.get("indicator", "")).lower()
        if not kind or not value or " " in value:
            rejected += 1
            continue
        if kind == "email":  # personal contact data is out of scope for display
            rejected += 1
            continue
        records.append({
            "type": kind, "indicator": value,
            "classification": row.get("classification", "") or "unclassified",
            "detected_date": row.get("detected_date") or None,
            "report": report,
        })
    return records, rejected


def project_marketplace_record(raw: dict, market: str) -> dict | None:
    """DWData-schema projection: vendor/name/category/price/rating -> listing.
    Used only for data an operator supplies locally; never bundled."""
    name = str(raw.get("name") or raw.get("title") or "").strip()
    if not name:
        return None
    shown, reasons = excerpt(name, 120)
    return {
        "market": market,
        "vendor": str(raw.get("vendor") or "unknown").strip()[:80],
        "title": shown, "suppressed": shown is None, "suppression_reasons": reasons,
        "category": str(raw.get("category") or "uncategorized").strip()[:80],
        "price": str(raw.get("price") or "").strip()[:40] or None,
        "rating": str(raw.get("rating") or "").strip()[:20] or None,
    }


# ---------- Tor Project Onionoo relay metadata ----------

TOR_TRANSFORMATION_VERSION = "gothamite-tor-1.0"
_IPV4 = re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$")
_FPR = re.compile(r"^[A-F0-9]{40}$")


def normalize_ipv4(value: str) -> str | None:
    """Exact-match correlation key: dotted quad without port, leading zeros or spaces."""
    host = (value or "").strip()
    if host.startswith("["):
        return None  # IPv6 OR address; not used as a correlation key in this prototype
    host = host.rsplit(":", 1)[0] if host.count(":") == 1 else host
    m = _IPV4.match(host)
    if not m or any(int(p) > 255 for p in m.groups()):
        return None
    return ".".join(str(int(p)) for p in m.groups())


def _onionoo_time(value: str | None) -> str | None:
    """Onionoo uses 'YYYY-MM-DD hh:mm:ss' (UTC)."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def normalize_onionoo_relay(raw: dict) -> dict | None:
    """Keep only the relay fields GOTHAMITE uses. Returns None for malformed records.

    ``exit`` follows the directory's Exit flag. Exit addresses are the IPs the
    relay was observed exiting from; OR addresses are where it accepts relay
    connections. Both are IPv4-normalized for exact-match correlation."""
    fpr = str(raw.get("fingerprint", "")).upper()
    if not _FPR.match(fpr):
        return None
    flags = sorted(str(f) for f in raw.get("flags") or [])
    exit_ips = sorted({ip for ip in (normalize_ipv4(a) for a in raw.get("exit_addresses") or []) if ip})
    or_ips = sorted({ip for ip in (normalize_ipv4(a) for a in raw.get("or_addresses") or []) if ip})
    if not exit_ips and not or_ips:
        return None
    return {
        "fingerprint": fpr,
        "nickname": str(raw.get("nickname") or "Unnamed")[:32],
        "running": bool(raw.get("running")),
        "exit": "Exit" in flags,
        "flags": flags,
        "exit_addresses": exit_ips,
        "or_addresses": or_ips,
        "first_seen": _onionoo_time(raw.get("first_seen")),
        "last_seen": _onionoo_time(raw.get("last_seen")),
        "as": raw.get("as"),
        "as_name": raw.get("as_name"),
        "country": raw.get("country"),
        "observed_bandwidth": raw.get("observed_bandwidth"),
    }
