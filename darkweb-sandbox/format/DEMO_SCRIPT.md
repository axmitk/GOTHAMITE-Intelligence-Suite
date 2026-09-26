# DEMO_SCRIPT.md

**Repos:** `darkweb-sandbox` + `GOTHAMITE`
**Audience:** internal college hackathon judges — assume no dark web or Tor background
**Length:** 6–7 minutes
**Phase:** 6

---

## 1. Rules

1. **Rehearse the exact sequence below at least twice, cold start, before presenting.**
2. **Have the recording ready and cued.** Four chained subsystems on an unfamiliar network is exactly where live demos die. If anything hangs past ~10 seconds, cut to video and keep talking. Nobody deducts marks for a video; a silent frozen terminal costs the round.
3. **Never say "Tor", "our Tor browser", or "we access the dark web."** Say *simulated onion-routed network*, *relay pool*, *layered encryption*, *synthetic corpus*. Every claim below is literally true — keep it that way.

---

## 2. Screen setup — arrange before you start

| Window | Content |
|---|---|
| 1 | Terminal — `docker compose` output |
| 2 | Terminal — split panes tailing 3 relay logs |
| 3 | Browser — a mock site page |
| 4 | Browser — GOTHAMITE dashboard |

Everything already running except the scrape. Do not `docker compose up` live — start it before you walk on.

---

## 3. The script

### 0:00 — Problem (45s)
*No screen. Talk to the room.*

> An analyst investigating dark web threat actors has one thing to work with: a username. The same person operates under different names on different marketplaces. Today, linking them is manual — reading forums, keeping notes in spreadsheets, holding it all in your head. It doesn't scale and it isn't repeatable.
>
> GOTHAMITE automates that correlation. And because we can't legally or ethically touch real dark web infrastructure, we built the environment too — a working simulation of onion routing, with synthetic marketplaces, so every part of this is ours end to end.

**Say the synthetic part yourself, first, unprompted.** It is a strength, and volunteering it prevents it becoming a challenge later.

---

### 0:45 — The network (90s)
*Window 1.*

> Real onion routing works by encrypting a request in layers, once per relay. Each relay peels exactly one layer — it learns who handed it the request and where to pass it next, and nothing else. No single relay knows both the origin and the destination.
>
> We built that. Seven relay nodes, each an isolated container with its own keypair, and a directory service the client queries for a route.

Show `GET /relays` — seven nodes, all up.
Show `GET /path?hops=3` — call it **twice**. Different route each time.

> Path is selected fresh each session. Standard AES and RSA, from the `cryptography` library — we didn't write our own crypto.

---

### 2:15 — The synthetic dark web (45s)
*Window 3.*

> Three sites: two forums and a marketplace. Entirely invented content — invented handles, invented PGP keys, invented wallets. Nothing scraped from anywhere real.

Show a thread. Point at an inline PGP fingerprint and a wallet address.

> These sites have no port mapping to the host. The only way to reach them is through the relay chain.

*(Optional, if rehearsed: `curl` from the host and let it fail. Strong beat — but only if it fails fast.)*

---

### 3:00 — Collection (75s)
*Window 1 to run, Window 2 to watch.*

Run the scraper.

> Our agent is requesting a route, then crawling through it.

Point at the relay logs as they scroll.

> Each relay logs one hop — its own next hop, nothing more. Relay two there has no idea which site this request ends at. That's the property that makes it onion routing rather than a proxy chain.

Let the run summary print.

> Forty-odd pages, through three different routes, and the identifiers are extracted and handed to the analysis platform.

---

### 4:15 — The result (2 min) — **the important part**
*Window 4. Slow down here.*

Graph view.

> Two personas on two different sites. `nightjar` on the forum, `n1ghtjar_` on the marketplace. Different names. Same PGP fingerprint, same wallet.

Click the edge → evidence panel.

> Confidence 0.95. And it shows *why* — every signal, its weight, and the source artifact it came from. Not a black box. An analyst can click through to the exact page this came from.

Then the rebrand:

> This one is more interesting. `quillfeather` stops posting in April. Seventeen days later `quill_v2` appears on a different forum. Different PGP key — they rotated it. But the same wallet, and the timing lines up. 0.60. That's a rebrand caught without a key match.

Then — **do not skip this** — the decoy:

> And this is the one we're most pleased with. `nightjarr`, two Rs. One character from `nightjar`. Overlapping activity. Every naive system links these two.
>
> Ours doesn't. Nothing shared but a similar name, and the activity windows actually conflict, which counts *against* the link. Below threshold, no edge. The system reports what it could not link, and why.

> False positives are how an analyst stops trusting a tool. We'd rather show a rejection than a guess.

Export → CSV/JSON. Two seconds, no commentary needed.

---

### 6:15 — Close (30s)

> To be exact about what's real: the encryption and relay isolation are real. The correlation engine is real. The data is synthetic, by design — the alternative is illegal, and we're not going to pretend otherwise.
>
> Point it at an authorised source and nothing in the engine changes.

---

## 4. Expected questions

| Question | Answer |
|---|---|
| Is this real Tor? | No, and we don't claim it is. Real layered encryption, real relay isolation, on a fixed pool of seven nodes we operate. It demonstrates the mechanism, not real-world anonymity. |
| Why not use real dark web data? | It's legally and ethically off-limits for a student team, and our project document rules it out. Synthetic also means we have labelled ground truth, so we can actually measure whether the correlation is right. |
| Could someone use this to deanonymise real people? | It finds operator mistakes — reused keys, reused wallets — in sources it's pointed at. It doesn't break Tor. Built for authorised investigators under lawful process. |
| Isn't the exit relay a weakness? | The exit sees the request body. That's true of real onion routing too and it's well documented — not a flaw in our implementation. |
| Where's the AI? | Deliberately absent from attribution. Correlation is deterministic and reproducible, which is what makes the audit trail meaningful. Stylometry was scoped out rather than claimed and faked. |
| What if a forum post tries to manipulate your scraper? | Scraped content is treated as inert data — never executed, never put in a query, never fed to a model. That's a real attack against systems like this and we designed against it. |
| How do you know the confidence scores are right? | We don't call them probabilities. They're weighted scores against documented weights, capped at 0.95. Calibration would need real ground truth we don't have. |
| What's left to build? | Stylometric persona linkage, hidden-service infrastructure correlation against Certificate Transparency logs, and a live collection scheduler. Scoped out for this deadline, not hand-waved. |

---

## 5. Failure playbook

| Fails | Do |
|---|---|
| Relay hangs mid-scrape | 10 seconds, then cut to video, keep narrating |
| Site unreachable | Scraper continues by design — say so, it demonstrates fault isolation |
| Dashboard won't load | Video |
| A link is missing from the graph | Don't improvise. Show the two that are there and move on |
| Docker won't come up | Open with the video, treat it as a walkthrough |
| Asked something you can't answer | "I don't know — that's outside what we scoped." Then stop. Guessing in front of judges is how a good demo unravels. |
