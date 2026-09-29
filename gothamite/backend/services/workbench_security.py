"""Local demo seat, CSRF protection and bounded per-process request limiting.

This is deliberately not production identity/SSO. The launcher binds loopback.
A hosted demo sets GOTHAMITE_PUBLIC_URL (or runs on Render, which provides
RENDER_EXTERNAL_URL); that single https origin is then allowed and the session
cookie is marked Secure.
"""
import hashlib
import hmac
import os
import secrets
import time
from collections import defaultdict, deque
from threading import Lock
from fastapi import HTTPException, Request

SECRET = secrets.token_bytes(32)
COOKIE = "gothamite_demo"
ORIGINS = set(os.getenv("GOTHAMITE_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8042,http://127.0.0.1:8042,http://localhost:8000,http://127.0.0.1:8000,http://testserver").split(","))
PUBLIC_URL = (os.getenv("GOTHAMITE_PUBLIC_URL") or os.getenv("RENDER_EXTERNAL_URL") or "").rstrip("/")
if PUBLIC_URL:
    ORIGINS.add(PUBLIC_URL)
PUBLIC_HOST = PUBLIC_URL.split("://", 1)[-1].split("/", 1)[0] if PUBLIC_URL else ""
SECURE_COOKIE = PUBLIC_URL.startswith("https://")
_buckets = defaultdict(deque)
_lock = Lock()


def limit(request: Request):
    now = time.monotonic()
    key = request.client.host if request.client else "local"
    with _lock:
        if len(_buckets) > 1000:
            for k in list(_buckets):
                if not _buckets[k] or _buckets[k][-1] < now - 60:
                    del _buckets[k]
        bucket = _buckets[key]
        while bucket and bucket[0] < now - 60:
            bucket.popleft()
        if len(bucket) >= 240:
            raise HTTPException(429, "Too many requests. Retry in one minute.", headers={"Retry-After": "60"})
        bucket.append(now)


def origin_check(request: Request):
    origin = request.headers.get("origin")
    if origin and origin not in ORIGINS:
        raise HTTPException(403, "Origin is not allowed")


def sign(value):
    return hmac.new(SECRET, value.encode(), hashlib.sha256).hexdigest()


def valid_session(token):
    try:
        payload, signature = token.rsplit(".", 1)
        expires, nonce = payload.split(".", 1)
        return hmac.compare_digest(signature, sign(payload)) and int(expires) > time.time() and len(nonce) == 32
    except (ValueError, TypeError, AttributeError):
        return False


def create_session(existing=""):
    # Tabs share cookies: keep their CSRF token stable until the session expires.
    if valid_session(existing):
        return existing, sign(f"csrf:{existing}")
    payload = f"{int(time.time()) + 43200}.{secrets.token_hex(16)}"
    token = f"{payload}.{sign(payload)}"
    return token, sign(f"csrf:{token}")


def require_session(request: Request):
    limit(request)
    origin_check(request)
    token = request.cookies.get(COOKIE, "")
    if not valid_session(token):
        raise HTTPException(401, "Local demo session expired. Reload to start a new session.")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if not hmac.compare_digest(request.headers.get("x-csrf-token", ""), sign(f"csrf:{token}")):
            raise HTTPException(403, "CSRF token is missing or invalid")
        length = request.headers.get("content-length", "0")
        if not length.isdigit() or int(length) > 16384:
            raise HTTPException(413, "Request body exceeds 16 KB")
    return {"name": "Demo analyst", "role": "analyst", "mode": "synthetic"}
