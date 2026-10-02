import sys
import os
import re
import hashlib
import json
import requests
import subprocess
from datetime import datetime, timezone

GOTHAMITE_API = "http://localhost:8000/api/v1"

TARGETS = [
    # A1 nightjar
    {"source_id": "forum-alpha", "source_type": "forum", "host": "alpha7fq2mx9k.onion.mock", "resource": "/thread/14"},
    # A2 n1ghtjar_ (shares PGP_A)
    {"source_id": "marketplace-beta", "source_type": "marketplace", "host": "beta4np8vz3wc.onion.mock", "resource": "/listing/32"},
    # A2 n1ghtjar_ (shares WALLET_A)
    {"source_id": "marketplace-beta", "source_type": "marketplace", "host": "beta4np8vz3wc.onion.mock", "resource": "/listing/33"},
    # C1 nightjarr (decoy, overlaps time, similar handle, different PGP)
    {"source_id": "forum-gamma", "source_type": "forum", "host": "gamma2xd6bt5hy.onion.mock", "resource": "/thread/62"},
    # C1 nightjarr (wallet)
    {"source_id": "forum-gamma", "source_type": "forum", "host": "gamma2xd6bt5hy.onion.mock", "resource": "/thread/63"},
    # B1 quillfeather (WALLET_B)
    {"source_id": "forum-alpha", "source_type": "forum", "host": "alpha7fq2mx9k.onion.mock", "resource": "/thread/24"},
    # B2 quill_v2 (WALLET_B, rotated PGP)
    {"source_id": "forum-gamma", "source_type": "forum", "host": "gamma2xd6bt5hy.onion.mock", "resource": "/thread/53"},
    # D1 bellwether (negative control)
    {"source_id": "marketplace-beta", "source_type": "marketplace", "host": "beta4np8vz3wc.onion.mock", "resource": "/listing/42"},
]

def collect(target):
    mock_host = target["host"]
    resource = target["resource"]
    print(f"\n[1] Collecting from {mock_host}{resource}")
    
    cmd = [
        "docker", "compose", "-f", "docker-compose.yml", "-f", "mock_sites/docker-compose.sites.yml", 
        "run", "--rm", "--entrypoint", "python", "directory", "-m", "client.onion_client",
        "--directory", "http://directory:8000", "--hops", "3", "--host", mock_host, "--resource", resource
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Docker command failed: {result.stderr}")
        
    output = result.stdout
    path_match = re.search(r'path:\s*(.+)', output)
    relay_path_ids = []
    if path_match:
        relay_path_ids = [r.strip() for r in path_match.group(1).split('->')]
        
    parts = output.split("\n\n", 1)
    if len(parts) > 1:
        raw_html = parts[1]
    else:
        raw_html = output
        
    return raw_html, relay_path_ids

def extract_entities(html: str):
    persona = None
    handle_match = re.search(r'Posted by <a href="/user/([^"]+)">', html)
    if handle_match:
        persona = handle_match.group(1)
        
    pgp = None
    pgp_match = re.search(r'Fingerprint:\s*([0-9A-F\s]+)', html, re.IGNORECASE)
    if pgp_match:
        pgp = pgp_match.group(1).replace(' ', '').strip()
        
    btc = None
    btc_match = re.search(r'\b(1[1-9A-HJ-NP-Za-km-z]{25,34})\b', html)
    if btc_match:
        btc = btc_match.group(1)
        
    return persona, pgp, btc

def normalize_payload(target, html, relay_path_ids, persona, pgp, btc):
    raw_hash = hashlib.sha256(html.encode('utf-8')).hexdigest()
    print(f"    [+] SHA-256: {raw_hash}")
    print(f"    [+] Extracted persona: {persona}")
    print(f"    [+] Extracted PGP: {pgp}")
    print(f"    [+] Extracted BTC: {btc}")
    
    now = datetime.now(timezone.utc).isoformat()
    
    identifiers = []
    if pgp:
        identifiers.append({
            "type": "pgp_fingerprint",
            "value": pgp,
            "observed_at": now
        })
    if btc:
        identifiers.append({
            "type": "wallet",
            "value": btc,
            "observed_at": now
        })
        
    content_hash = f"sha256:{raw_hash}"
    
    payload = {
        "source_id": target["source_id"],
        "source_type": target["source_type"],
        "url": f"http://{target['host']}{target['resource']}",
        "collected_at": now,
        "relay_path": relay_path_ids if relay_path_ids else ["unknown"],
        "raw_content": html,
        "content_hash": content_hash,
        "persona": {
            "handle": persona or "unknown",
            "observed_at": now
        },
        "identifiers": identifiers
    }
    return payload

def ingest_to_gothamite(payload):
    res = requests.post(f"{GOTHAMITE_API}/ingest", json=payload)
    if res.status_code == 202:
        print(f"    [+] Ingested -> Artifact ID: {res.json().get('artifact_id')}")
    elif res.status_code == 200 and not res.json().get('accepted'):
        print(f"    [=] Duplicate -> Artifact ID: {res.json().get('artifact_id')}")
    else:
        print(f"    [!] Ingestion failed: {res.status_code} {res.text}")

def trigger_correlation():
    print("\n[*] Triggering GOTHAMITE Correlation Engine...")
    res = requests.post(f"{GOTHAMITE_API}/correlate")
    if res.status_code in (200, 202):
        print(f"    [+] Correlation completed. Added {res.json().get('edges_added', 0)} new edges.")
    else:
        print(f"    [!] Correlation failed: {res.status_code} {res.text}")

def main():
    try:
        for t in TARGETS:
            html, relay_path_ids = collect(t)
            persona, pgp, btc = extract_entities(html)
            payload = normalize_payload(t, html, relay_path_ids, persona, pgp, btc)
            ingest_to_gothamite(payload)
        
        trigger_correlation()
    except Exception as e:
        print(f"[!] Error during bridge collection: {e}")

if __name__ == "__main__":
    main()
