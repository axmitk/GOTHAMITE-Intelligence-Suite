# DIRECTORY_SPEC.md

**Repo:** `darkweb-sandbox`
**Prerequisites:** `MASTER_CONTEXT.md`, `RELAY_PROTOCOL.md`
**Phase:** 2

---

## 1. Purpose

A single in-memory registry of available relays, and a path-selection endpoint the client calls before every session.

This replaces Tor's directory authority + consensus system with the smallest thing that provides dynamic path selection. **No voting, no distributed trust, no persistence** — see `MASTER_CONTEXT.md` scope lock.

---

## 2. State

In-memory only. No database, no disk. Lost on restart, rebuilt as relays re-register.

```python
relays: dict[str, {
    "relay_id":   str,      # "relay-01" … "relay-07"
    "host":       str,
    "port":       int,
    "public_key": str,      # PEM, public only
    "status":     str,      # "up" | "down"
    "registered_at": datetime
}]
```

**The directory never receives, stores, or logs a private key.** If a registration payload contains one, reject it and log an error — that is a bug in the relay, not something to accept quietly.

---

## 3. Endpoints

### `POST /register`
Called by each relay at startup.

Request:
```json
{ "relay_id": "relay-03", "host": "relay-03", "port": 9003, "public_key": "-----BEGIN PUBLIC KEY-----\n..." }
```

Response `200`:
```json
{ "registered": true, "relay_id": "relay-03" }
```

Re-registration with the same `relay_id` overwrites the existing entry and sets `status: up`. This makes container restarts safe.

Reject with `400` if: `public_key` is not a valid PEM public key, contains `PRIVATE KEY`, or any required field is missing.

---

### `GET /path?hops=N`
The core endpoint. Returns an ordered route.

Default `hops=3`. Valid range `2–5`.

Response `200`:
```json
{
  "path_id": "p_8f3a2c",
  "hops": 3,
  "relays": [
    { "relay_id": "relay-05", "host": "relay-05", "port": 9005, "public_key": "..." },
    { "relay_id": "relay-02", "host": "relay-02", "port": 9002, "public_key": "..." },
    { "relay_id": "relay-07", "host": "relay-07", "port": 9007, "public_key": "..." }
  ]
}
```

Selection rules:
- Uniform random, **without replacement**, from relays with `status: up`
- Order in the array is the order of traversal: `relays[0]` is the entry relay
- **No** bandwidth, uptime, latency, geographic or reputation weighting
- No guard-node persistence — every call selects fresh

Errors:
- `400` if `hops` outside 2–5
- `503` if fewer than `hops` relays are `up`, with a message naming how many are available

`path_id` is for log correlation only. The directory does not track or store paths after returning them.

---

### `GET /relays`
Demo visibility. Returns all registered relays with status. **Public keys included, private keys never.**

```json
{ "count": 6, "relays": [ { "relay_id": "relay-01", "status": "up", ... } ] }
```

---

### `POST /relays/{relay_id}/status`
Manual up/down toggle. Exists so the demo can show a downed relay being excluded from selection.

```json
{ "status": "down" }
```

---

## 4. What the directory must not do

- Store or forward any traffic. It is consulted before a request, never during one
- Know which paths were actually used
- Log the composition of returned paths — logging every path defeats the isolation property the system is demonstrating. Log `path_id` and hop count only
- Persist anything across restarts

---

## 5. Acceptance criteria (Phase 2)

1. 5–7 relays start and successfully register
2. Ten consecutive `GET /path?hops=3` calls return visibly different orderings
3. No path contains a duplicate relay
4. A relay set to `down` never appears in a returned path
5. `hops=1` and `hops=6` both rejected with `400`
6. With only 2 relays up, `hops=3` returns `503` naming the shortfall
7. Directory logs contain no private keys and no full path compositions
