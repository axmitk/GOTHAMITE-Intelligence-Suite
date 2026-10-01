"""Check the hosted GOTHAMITE prototype and keep the free Render instance awake.

Usage:  python scripts/check_live.py [base_url]
Default URL: https://gothamite.onrender.com (or GOTHAMITE_URL).
Exit code 0 = healthy, 1 = a check failed. Standard library only.

Read-only: it opens a demo session and reads data; it never approves,
simulates or edits anything, so the demo state is untouched.
"""
import http.cookiejar
import json
import os
import sys
import time
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else os.getenv("GOTHAMITE_URL", "https://gothamite.onrender.com")).rstrip("/")
API = BASE + "/api/v1/workbench"
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
failures = []


def request(path, method="GET", headers=None, timeout=90):
    req = urllib.request.Request(BASE + path if path.startswith("/") else path, method=method,
                                 headers={"User-Agent": "gothamite-check", **(headers or {})})
    with opener.open(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "replace")


def check(name, fn):
    started = time.time()
    try:
        detail = fn()
        print(f"PASS  {name} ({time.time() - started:.1f}s){' - ' + detail if detail else ''}")
    except Exception as e:  # noqa: BLE001 - report every failure, keep checking
        failures.append(name)
        print(f"FAIL  {name}: {e}")


def wake():
    # A sleeping free instance can take ~30-60 s to start; retry for up to ~3 min.
    for attempt in range(1, 7):
        try:
            status, body = request("/health", timeout=60)
            assert status == 200 and json.loads(body)["status"] == "ok", body[:120]
            return f"attempt {attempt}"
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(15)
    raise RuntimeError(f"not healthy after 6 attempts: {last}")


def session():
    status, body = request("/api/v1/workbench/session", "POST",
                           {"X-Gothamite-Client": "workbench", "Origin": BASE})
    assert status == 200 and json.loads(body).get("csrf"), body[:120]


def dashboard():
    _, body = request("/api/v1/workbench/dashboard")
    d = json.loads(body)
    assert len(d["cases"]) == 11, f"expected 11 cases, got {len(d['cases'])}"
    assert d["indicators"] > 500, f"only {d['indicators']} indicators"
    return f"{len(d['cases'])} cases, {d['indicators']} indicators"


def canonical_case():
    _, body = request("/api/v1/workbench/search?q=203.0.113.42")
    hits = json.loads(body)["results"]
    assert hits and hits[0]["provenance"] == "synthetic", hits[:1]
    _, body = request("/api/v1/workbench/cases/INC-1042")
    case = json.loads(body)
    assert case["risk"]["score"] == 100 and len(case["evidence"]) == 6
    reviewed = [a["title"] for a in case["actions"] if a["status"] != "pending"]
    return "pristine" if not reviewed else f"WARNING: already reviewed {reviewed}; restart Render to reset"


def tor_context():
    _, body = request("/api/v1/workbench/entities/IP-L47")
    ev = json.loads(body)["evidence"]
    assert any((e.get("dataset_record") or {}).get("dataset") == "tor_project_onionoo" for e in ev)


def frontend():
    for path in ("/", "/investigations/INC-1042"):
        status, body = request(path)
        assert status == 200 and '<div id="root">' in body, f"{path} -> {status}"


print(f"Checking {BASE}")
check("server awake and healthy", wake)
check("demo session", session)
check("command center data", dashboard)
check("canonical case INC-1042", canonical_case)
check("Tor exit-node context", tor_context)
check("frontend pages", frontend)
print("RESULT:", "FAILED " + ", ".join(failures) if failures else "all checks passed")
sys.exit(1 if failures else 0)
