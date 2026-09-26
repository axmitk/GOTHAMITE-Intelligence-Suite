"""Seed content for the three mock sites.

Every value here is invented.  No real forum, marketplace, archive, dataset,
person, key or wallet is referenced.  Wallet strings are format-plausible so the
scraper's extraction regex is exercised; they are not real addresses and must
never be treated as operational targets.

**Authority.**  `AgentsDocs/DATA_MODEL.md` section 4 is the single source of truth
for the personas, fingerprints, wallets and active windows below
(`SPEC_DECISIONS.md` SD-014).  The canonical A1/A2 wallet is fixed by SD-015.
Values are copied character for character, as `MOCK_SITES_SPEC.md` section 2
rule 5 requires -- one wrong character silently breaks the headline link.

**Determinism.**  Everything is hardcoded.  No random generation, no faker, no
timestamp computed at import or request time (`MOCK_SITES_SPEC.md` section 2
rule 3).  The demo depends on knowing exactly what is here.

**Placement.**  Identifiers appear inline in post bodies, never in structured
metadata or HTML attributes (rule 4), so the scraper's extraction has to do real
work.  The `pgp` and `wallets` fields on each post declare what a correct
extractor should find in that body; they drive the tests, and the renderer never
emits them as markup.

This module holds no scoring, correlation, attribution or profiling logic.  The
sites are observation sources; the graph reasoning belongs to GOTHAMITE.
"""

from __future__ import annotations

from typing import NamedTuple

# --- identifiers, verbatim from DATA_MODEL.md section 4 --------------------

PGP_A = "9F2A4C81D3E5B7069A1C4F82D6E30B57A4C19E8D"  # A1 and A2 -- shared
PGP_B1 = "3B77E1A9C4D28F60B5E3A17C9D42F8E06B1A5C93"  # B1
PGP_B2 = "E4C08B21F7A6D93E5C1B84027FA36D9E1C05B872"  # B2 -- rotated, different
PGP_C1 = "7D19F4C8B302A6E5D91C7B48F0A2E63D5C81B94F"  # C1 -- shares nothing
PGP_D1 = "A50C3E97B14D6F82093C5A7E1BD48F620E93C7A1"  # D1

WALLET_A = "1Hx4kQ9mVn2RtYbP7sLdF3wCgN8jZaEuT6"  # A1 and A2 -- shared (SD-015)
WALLET_B = "1Kp7dR3zXw9QfM4vB2nHtL6sYcJ8gAeU5o"  # B1 and B2 -- shared
WALLET_C1 = "1Qs2fT8yWn5LpX3mK9vGdC7bJ4hRzAeN1u"  # C1 -- shares nothing
WALLET_D1 = "1Zr6bN4qJm8VhT2xD5cWfP9sLgY3kEuA7i"  # D1


class Persona(NamedTuple):
    """A seed persona as DATA_MODEL.md section 4 defines it."""

    persona_id: str  # A1, A2, B1, B2, C1, D1
    handle: str
    site_id: str
    active_from: str  # ISO 8601 date, inclusive
    active_to: str  # ISO 8601 date, inclusive
    pgp: str
    wallet: str


class Post(NamedTuple):
    """One thread or listing.

    `pgp` and `wallets` declare the identifiers planted in `body`.  They are the
    expectation the tests check the rendered page against; they are not rendered
    as metadata.
    """

    site_id: str
    post_id: int
    handle: str
    observed_at: str  # ISO 8601, UTC, Z suffix (SD-017)
    title: str
    body: str
    pgp: str | None = None
    wallets: tuple[str, ...] = ()


class Site(NamedTuple):
    site_id: str
    kind: str  # forum | marketplace -- DATA_MODEL.md Source.type
    name: str
    tagline: str
    address: str  # .onion.mock address, MOCK_SITES_SPEC.md section 6
    item_path: str  # "thread" or "listing"
    item_word: str


# --- the three sites, MOCK_SITES_SPEC.md sections 3 and 6 -------------------

SITES: dict[str, Site] = {
    "forum-alpha": Site(
        site_id="forum-alpha",
        kind="forum",
        name="Alpha Board",
        tagline="General discussion and vendor threads.",
        address="alpha7fq2mx9k.onion.mock",
        item_path="thread",
        item_word="Threads",
    ),
    "marketplace-beta": Site(
        site_id="marketplace-beta",
        kind="marketplace",
        name="Beta Market",
        tagline="Listings, escrow, and vendor feedback.",
        address="beta4np8vz3wc.onion.mock",
        item_path="listing",
        item_word="Listings",
    ),
            "marketplace-epsilon": Site(
        site_id="marketplace-epsilon",
        kind="marketplace",
        name="Epsilon Market",
        tagline="Next gen underground drugs & exploit market",
        address="epsilon8qkw4rx.onion.mock",
        item_path="listing",
        item_word="Listings",
    ),
    "forum-zeta": Site(
        site_id="forum-zeta",
        kind="forum",
        name="Zeta Board",
        tagline="Advanced Persistent Threat forum",
        address="zeta5vnp3ty2.onion.mock",
        item_path="thread",
        item_word="Threads",
    ),
    "marketplace-omega": Site(
        site_id="marketplace-omega",
        kind="marketplace",
        name="Omega Market",
        tagline="The end of all markets",
        address="omega9xrq2zv.onion.mock",
        item_path="listing",
        item_word="Listings",
    ),
    "forum-delta": Site(
        site_id="forum-delta",
        kind="forum",
        name="Delta Board",
        tagline="Underground carding and exploit discussion.",
        address="delta9pqr5st.onion.mock",
        item_path="thread",
        item_word="Threads",
    ),
    "forum-gamma": Site(
        site_id="forum-gamma",
        kind="forum",
        name="Gamma Board",
        tagline="Smaller board. Discussion and trade threads.",
        address="gamma2xd6bt5hy.onion.mock",
        item_path="thread",
        item_word="Threads",
    ),
}


# --- personas, DATA_MODEL.md section 4 --------------------------------------

PERSONAS: dict[str, Persona] = {
    "A1": Persona("A1", "nightjar", "forum-alpha", "2026-01-08", "2026-08-20", PGP_A, WALLET_A),
    "A2": Persona("A2", "n1ghtjar_", "marketplace-beta", "2026-02-14", "2026-08-22", PGP_A, WALLET_A),
    "B1": Persona("B1", "quillfeather", "forum-alpha", "2026-01-20", "2026-04-02", PGP_B1, WALLET_B),
    "B2": Persona("B2", "quill_v2", "forum-gamma", "2026-04-19", "2026-08-18", PGP_B2, WALLET_B),
            "F1": Persona("F1", "venom_strike", "marketplace-epsilon", "2026-01-01", "2026-09-01", PGP_A, WALLET_A),
    "F2": Persona("F2", "venomous", "forum-zeta", "2026-02-01", "2026-09-01", PGP_A, WALLET_A),
    "F3": Persona("F3", "ven0m", "marketplace-omega", "2026-03-01", "2026-09-01", PGP_A, WALLET_A),
    "E1": Persona("E1", "cipher_ghost", "forum-delta", "2026-03-01", "2026-08-20", PGP_C1, WALLET_A),
    "C1": Persona("C1", "nightjarr", "forum-gamma", "2026-03-01", "2026-08-21", PGP_C1, WALLET_C1),
    "D1": Persona("D1", "bellwether", "marketplace-beta", "2026-02-01", "2026-08-19", PGP_D1, WALLET_D1),
}


# --- posts ------------------------------------------------------------------
#
# 8 per persona, per DATA_MODEL.md section 5 (8-15) and MOCK_SITES_SPEC.md
# section 5.  Timestamps span each persona's stated active window, first and
# last post landing on its endpoints.
#
# Body text is deliberately mundane -- availability, payment terms, logistics,
# reputation.  No operational or instructional content of any kind, and no
# attempt to make any two personas read alike: stylometry is out of scope
# (MOCK_SITES_SPEC.md section 5), so writing-style hints would be wasted effort
# that invites claiming a capability this system does not have.

POSTS: list[Post] = [
    Post("marketplace-epsilon", 101, "venom_strike", "2026-05-10T12:00:00Z", "Selling access", "Initial access broker.", pgp=PGP_A, wallets=(WALLET_A,)),
    Post("forum-zeta", 202, "venomous", "2026-06-10T12:00:00Z", "Looking for partners", "Let's do some ransomware.", pgp=PGP_A, wallets=(WALLET_A,)),
    Post("marketplace-omega", 303, "ven0m", "2026-07-10T12:00:00Z", "RaaS Affiliate", "Looking for new RaaS.", pgp=PGP_A, wallets=(WALLET_A,)),

    # === forum-delta / E1 cipher_ghost =========================================
    Post(
        "forum-delta", 71, "cipher_ghost", "2026-03-15T12:00:00Z",
        "Selling 0days",
        "New 0days for sale. Using the same crypto wallet as the boss.",
        wallets=(WALLET_A,)
    ),
    Post(
        "forum-delta", 72, "cipher_ghost", "2026-04-10T12:00:00Z",
        "Another dump",
        "Here is my PGP key for verification.",
        pgp=PGP_C1
    ),

    # === forum-alpha / A1 nightjar =========================================
    # 2026-01-08 -> 2026-08-20.  PGP on 3 posts, wallet on 3 (spec asks >= 2).
    Post(
        "forum-alpha", 12, "nightjar", "2026-01-08T10:22:00Z",
        "Back after a quiet stretch",
        "Back after a quiet few weeks. Working through the backlog of requests "
        "from December -- if you messaged me and got nothing, send it again, I "
        "lost the queue when I rotated hosts. Turnaround on the standard "
        "dataset bundle is about four days at the moment, longer if you want it "
        "split into smaller parts. I am not taking rush jobs this month. Please "
        "read the pinned thread before asking about pricing.",
    ),
    Post(
        "forum-alpha", 13, "nightjar", "2026-02-03T14:05:00Z",
        "Key confirmation after the host move",
        "Several people have asked me to confirm my key after the host move, so "
        "here it is again. Verify anything that claims to be from me against "
        "this fingerprint before you send anything. I have seen at least two "
        "accounts using a similar handle this month. If the fingerprint does "
        "not match, it is not me, and I will not be replying to those threads.",
        pgp=PGP_A,
    ),
    # Thread 14 is the artifact quoted in API_CONTRACT.md section 3: same URL,
    # same handle, same observed_at, both identifiers on the page.
    Post(
        "forum-alpha", 14, "nightjar", "2026-03-11T09:14:00Z",
        "Terms, restated",
        "Restating my terms since the old thread fell off the index. Payment to "
        f"{WALLET_A} only -- I do not use any other address and I will not "
        "accept anything sent elsewhere. Key fingerprint below so you can check "
        "this post is mine. Delivery on the archive dump is three to five days "
        "from confirmation. Ask before sending if you are unsure.",
        pgp=PGP_A,
        wallets=(WALLET_A,),
    ),
    Post(
        "forum-alpha", 15, "nightjar", "2026-04-22T16:40:00Z",
        "Availability update",
        "Availability update. The archive dump is out of stock until the middle "
        "of next month while I rebuild the index. The access credentials pack "
        "is still available in the usual sizes. I am not adding anything new to "
        "the list this quarter -- several people have asked and the answer is "
        "the same. Reputation threads are on the board if you want to check "
        "before dealing.",
    ),
    Post(
        "forum-alpha", 16, "nightjar", "2026-05-30T11:07:00Z",
        "One address only",
        "Reminder for the new arrivals: payment to "
        f"{WALLET_A} only. Someone messaged me last week saying they had "
        "already paid a different address that was posted in a reply. That was "
        "not mine and I cannot help recover it. Check the fingerprint on my "
        "signed posts. I do not send payment details over private messages and "
        "never will.",
        wallets=(WALLET_A,),
    ),
    Post(
        "forum-alpha", 17, "nightjar", "2026-06-18T08:52:00Z",
        "Fingerprint, again",
        "Rotating nothing this cycle -- the key stays as it is. Posting the "
        "fingerprint again because the last thread was archived and people keep "
        "asking. If you are dealing with me for the first time, verify against "
        "this, and check the feedback thread. I have been on this board since "
        "January and the history is all there.",
        pgp=PGP_A,
    ),
    Post(
        "forum-alpha", 18, "nightjar", "2026-07-24T13:31:00Z",
        "Quarterly availability summary",
        "Quarterly summary for anyone tracking availability. Standard bundle: "
        "in stock. Archive dump: back in stock, four day turnaround. "
        "Credentials pack: limited. Payment to "
        f"{WALLET_A} only, as always. I will be slower to reply for the next "
        "two weeks -- travelling and on a bad connection. Anything urgent, say "
        "so in the subject line and I will get to it first.",
        wallets=(WALLET_A,),
    ),
    Post(
        "forum-alpha", 19, "nightjar", "2026-08-20T15:58:00Z",
        "Winding down for the season",
        "Winding down for the season. I will keep the listings up but expect "
        "slow replies until things settle. Thanks to the people who left "
        "feedback this year, it makes the vetting easier for everyone. The "
        "usual terms apply to anything already agreed. If you have an open "
        "order and have not heard from me in a week, bump the thread rather "
        "than starting a new one.",
    ),

    # === forum-alpha / B1 quillfeather =====================================
    # 2026-01-20 -> 2026-04-02.  Last post lands on the window's end date; see
    # SPEC_DECISIONS.md SD-018 for why that date and not an earlier one.
    Post(
        "forum-alpha", 20, "quillfeather", "2026-01-20T09:05:00Z",
        "New here",
        "New here, mostly reading for now. I have been doing small volume work "
        "on another board for a while and thought it was time to widen out. "
        "Happy to start with smaller trades until there is some history to "
        "point at. If anyone has a pinned guide for how vetting works here I "
        "would appreciate a link -- the search on this board is not great.",
    ),
    Post(
        "forum-alpha", 21, "quillfeather", "2026-01-29T12:44:00Z",
        "My key",
        "Posting my key so there is something to verify against. I would rather "
        "establish this early than have to prove it later when someone starts "
        "impersonating the handle. Everything I sign will match this "
        "fingerprint. If you get a message from this handle that is unsigned, "
        "treat it as suspect and say so publicly.",
        pgp=PGP_B1,
    ),
    Post(
        "forum-alpha", 22, "quillfeather", "2026-02-07T15:20:00Z",
        "First listing, small volume",
        "First proper listing. Small dataset bundles, nothing large, and I am "
        "keeping the volume low while I build up feedback. Payment to "
        f"{WALLET_B}. I will confirm receipt in thread rather than by message "
        "so there is a record. Turnaround is two days. Ask questions here "
        "rather than privately, it saves me repeating myself.",
        wallets=(WALLET_B,),
    ),
    Post(
        "forum-alpha", 23, "quillfeather", "2026-02-16T10:33:00Z",
        "Thanks for the notes",
        "Thanks to the two people who dealt with me this month and left notes. "
        "That is enough to move on to slightly larger batches. I am still not "
        "taking anything that needs a fast turnaround -- my setup is not built "
        "for it and I would rather say no than miss a deadline. Availability is "
        "roughly weekly at the moment.",
    ),
    Post(
        "forum-alpha", 24, "quillfeather", "2026-02-25T17:11:00Z",
        "This week",
        "Availability for this week. Two standard bundles, one credentials "
        f"pack. Payment to {WALLET_B} as before. I have had a couple of "
        "messages asking whether I take anything else -- I do not, and I am not "
        "going to start. Confirmations posted in thread within a day of receipt "
        "as usual.",
        wallets=(WALLET_B,),
    ),
    Post(
        "forum-alpha", 25, "quillfeather", "2026-03-06T08:47:00Z",
        "Fingerprint repost",
        "Reposting the fingerprint since the earlier thread has dropped off the "
        "front page. Nothing has changed and nothing is rotating. If that ever "
        "does change I will announce it in advance and sign the announcement "
        "with the old key first. Anyone claiming otherwise is not me.",
        pgp=PGP_B1,
    ),
    Post(
        "forum-alpha", 26, "quillfeather", "2026-03-19T14:02:00Z",
        "Slow month",
        "Slower month than I expected. Still available, still the same terms, "
        f"payment to {WALLET_B}. A couple of open threads are waiting on "
        "replies from buyers -- if that is you, bump it and I will pick it up. "
        "I am going to be reorganising how I handle the queue soon, will post "
        "details when it is settled.",
        wallets=(WALLET_B,),
    ),
    Post(
        "forum-alpha", 27, "quillfeather", "2026-04-02T11:26:00Z",
        "Stepping back",
        "This will be my last post under this handle for a while. Some changes "
        "on my side mean I am stepping back from this board. Open trades will "
        "be honoured -- message me in the existing threads and I will see them. "
        "Thanks to everyone who dealt with me here. I may be back in some form "
        "later; if so I will say so plainly rather than pretending to be new.",
    ),

    # === marketplace-beta / A2 n1ghtjar_ ===================================
    # 2026-02-14 -> 2026-08-22.  Same PGP and same wallet as A1: this is the
    # headline link.
    Post(
        "marketplace-beta", 31, "n1ghtjar_", "2026-02-14T09:30:00Z",
        "Listing here now",
        "Setting up here after being asked by a few regulars to list somewhere "
        "with escrow. Same terms as I use elsewhere. Starting with the standard "
        "dataset bundle and the archive dump; the credentials pack will follow "
        "once I see how the volume goes. Feedback from the other board does not "
        "carry over so I expect to be treated as new here, which is fair.",
    ),
    Post(
        "marketplace-beta", 32, "n1ghtjar_", "2026-03-05T13:15:00Z",
        "Key for verification",
        "Key fingerprint for verification. Anyone who has dealt with me on the "
        "forum side will recognise it -- it is the same key, I have not "
        "rotated. Verify before you send. There is at least one handle floating "
        "around that is close enough to mine to cause confusion, so check the "
        "fingerprint rather than the spelling.",
        pgp=PGP_A,
    ),
    Post(
        "marketplace-beta", 33, "n1ghtjar_", "2026-03-28T10:48:00Z",
        "Terms for new buyers",
        f"Terms for anyone new. Payment to {WALLET_A} only. Escrow is fine if "
        "you prefer it, I will not argue about it. Turnaround three to five "
        "days from confirmation. I do not do partial sends and I do not hold "
        "stock for people who have not confirmed. Ask in thread, not by "
        "message, unless it is genuinely private.",
        wallets=(WALLET_A,),
    ),
    Post(
        "marketplace-beta", 34, "n1ghtjar_", "2026-04-30T16:22:00Z",
        "Stock note",
        "Stock note. Archive dump limited this month, standard bundle fine. I "
        "have had a run of enquiries after being mentioned in someone else's "
        "feedback thread, which is appreciated but has stretched the queue. If "
        "you are waiting, you are still in it. I answer in order received and I "
        "do not skip people for paying more.",
    ),
    Post(
        "marketplace-beta", 35, "n1ghtjar_", "2026-05-27T11:39:00Z",
        "Impersonation, check the key",
        "Reposting the fingerprint. Two people have now told me they received "
        "messages from a handle one character different from mine offering the "
        "same items at a lower price. That is not me. I do not undercut my own "
        "listings and I do not open conversations by message. Check the key.",
        pgp=PGP_A,
    ),
    Post(
        "marketplace-beta", 36, "n1ghtjar_", "2026-06-25T08:14:00Z",
        "Mid-year terms restatement",
        f"Mid-year terms restatement. Payment to {WALLET_A} only, no "
        "exceptions, no alternate addresses, and I will never send you a "
        "different one in a message. If you see another address attached to "
        "this handle anywhere, report the thread. Turnaround unchanged. "
        "Feedback thread is pinned.",
        wallets=(WALLET_A,),
    ),
    Post(
        "marketplace-beta", 37, "n1ghtjar_", "2026-07-30T14:55:00Z",
        "Clearing the batch",
        "Wrapping up a batch of orders this week. Everything confirmed before "
        f"the weekend is out. Payment to {WALLET_A}. I have taken the "
        "credentials pack off the list for now -- not enough interest to "
        "justify keeping it stocked. Standard bundle and archive dump continue "
        "as normal.",
        wallets=(WALLET_A,),
    ),
    Post(
        "marketplace-beta", 38, "n1ghtjar_", "2026-08-22T12:03:00Z",
        "End of season",
        "End of season note. Availability drops from here until things pick up "
        "again. Existing agreements stand. Thanks to the buyers who used escrow "
        "without being asked -- it makes disputes much less likely and I would "
        "rather everyone did it. Anything unresolved, raise it in thread while "
        "I am still checking regularly.",
    ),

    # === marketplace-beta / D1 bellwether ==================================
    # 2026-02-01 -> 2026-08-19.  The co-location negative control: same site as
    # A2, overlapping active window, and no identifier shared with anyone.  Same
    # venue and same period must produce no edge (DATA_MODEL.md section 4,
    # Actor D, as revised by SD-027).
    Post(
        "marketplace-beta", 41, "bellwether", "2026-02-01T08:20:00Z",
        "Mostly buying",
        "New listing account. I mostly buy rather than sell, but I keep a small "
        "amount of stock moving to maintain standing. Anyone who has dealt with "
        "me elsewhere will know I am slow but reliable. I will use escrow by "
        "default on anything above a token amount and I would encourage "
        "everyone else to do the same.",
    ),
    Post(
        "marketplace-beta", 42, "bellwether", "2026-02-24T11:50:00Z",
        "Fingerprint on record",
        "Fingerprint for verification, posted early so there is a record. I "
        "sign anything that matters. If you receive an unsigned message from "
        "this handle asking you to send somewhere, it is not from me.",
        pgp=PGP_D1,
    ),
    Post(
        "marketplace-beta", 43, "bellwether", "2026-03-22T15:07:00Z",
        "The little I sell",
        f"For the few things I do sell, payment to {WALLET_D1}. Small volume "
        "only, generic archive material, nothing that needs discussion. I am "
        "not expanding this side of things. Most of my activity here is on the "
        "buying side and that is likely to stay true.",
        wallets=(WALLET_D1,),
    ),
    Post(
        # SD-027: this listing previously carried WALLET_A as a counterparty
        # reference. A rule-based extractor reads the address but not the
        # disclaimer around it, so it attributed A2's wallet to D1 and produced a
        # same_actor_suspected edge at 0.45 that DATA_MODEL.md section 4 forbids.
        # The reference is removed; the post keeps its feedback subject and
        # carries no identifier at all.
        "marketplace-beta", 44, "bellwether", "2026-04-27T09:41:00Z",
        "Feedback: purchase closed",
        "Closing out a purchase from earlier this month for the record. Terms "
        "were as agreed and everything arrived on time, no issues at all. "
        "Posting this because the seller asked for public feedback rather than "
        "a private note, which I think is the right way to do it. I am not "
        "putting payment details in a feedback post -- ask the seller directly.",
    ),
    Post(
        "marketplace-beta", 45, "bellwether", "2026-05-19T13:28:00Z",
        "Restocked a little",
        f"Restocked a little. Payment to {WALLET_D1} for anything from my "
        "listings. As before, small volume, and I will say no if the request is "
        "bigger than I can cover. I would rather turn something down than "
        "deliver late.",
        wallets=(WALLET_D1,),
    ),
    Post(
        "marketplace-beta", 46, "bellwether", "2026-06-30T10:16:00Z",
        "Verify signatures",
        "Reposting my fingerprint after a run of impersonation attempts across "
        "the board -- not aimed at me specifically, but worth everyone doing. "
        "Verify signatures, check addresses against signed posts, and do not "
        "accept payment details sent in a message.",
        pgp=PGP_D1,
    ),
    Post(
        "marketplace-beta", 47, "bellwether", "2026-07-28T16:44:00Z",
        "Quarterly feedback note",
        "Feedback note for a few sellers I have dealt with this quarter. All "
        "delivered as described, all within the stated window. I am not naming "
        "them here because a couple asked me not to; they know who they are and "
        "I have left notes in their threads. Escrow used throughout and no "
        "disputes.",
    ),
    Post(
        "marketplace-beta", 48, "bellwether", "2026-08-19T09:59:00Z",
        "Quiet period ahead",
        "Quiet period ahead. I will keep checking messages but expect delays. "
        "Nothing outstanding on my side that I am aware of -- if you think "
        "otherwise, say so in thread and I will look. Standing terms unchanged.",
    ),

    # === forum-gamma / B2 quill_v2 =========================================
    # 2026-04-19 -> 2026-08-18.  First post lands on the window's start date,
    # 17 days after B1's last (DATA_MODEL.md section 4; SD-018).  Rotated PGP,
    # same wallet as B1 -- wallet-only link, no key match.
    Post(
        "forum-gamma", 51, "quill_v2", "2026-04-19T10:12:00Z",
        "Starting again",
        "New handle, not a new person. I posted on another board under a "
        "different name until recently and stepped back for reasons that are "
        "not interesting. Starting again here rather than trying to carry "
        "anything over. I am not going to claim history I cannot prove on this "
        "board, so treat me as new and judge by what happens from here.",
    ),
    Post(
        "forum-gamma", 52, "quill_v2", "2026-05-02T14:38:00Z",
        "New key",
        "Key fingerprint. This is a new key -- the old one is gone and I am not "
        "going to pretend otherwise or try to link the two. If you dealt with "
        "me before under another handle you will notice it does not match. That "
        "is expected. Verify against this one from now on.",
        pgp=PGP_B2,
    ),
    Post(
        "forum-gamma", 53, "quill_v2", "2026-05-21T09:55:00Z",
        "First listing here",
        "First listing here. Small dataset bundles, same as I have always done. "
        f"Payment to {WALLET_B}. Turnaround two days. I confirm in thread "
        "rather than by message so there is a public record of it, which has "
        "saved me arguments before.",
        wallets=(WALLET_B,),
    ),
    Post(
        "forum-gamma", 54, "quill_v2", "2026-06-09T16:03:00Z",
        "Steady week",
        "Steady week. Two bundles out, both confirmed in thread. I am keeping "
        "volume low deliberately while I build up something to point at here. A "
        "couple of people have asked whether I take larger orders -- not yet, "
        "and I would rather say so than take one and handle it badly.",
    ),
    Post(
        "forum-gamma", 55, "quill_v2", "2026-06-27T11:21:00Z",
        "Availability",
        f"Availability. Standard bundles only for now. Payment to {WALLET_B} "
        "as in the previous thread. I have not changed the address and I do not "
        "intend to. Anything claiming a different one for this handle is wrong.",
        wallets=(WALLET_B,),
    ),
    Post(
        "forum-gamma", 56, "quill_v2", "2026-07-15T08:36:00Z",
        "Fingerprint repost",
        "Reposting the fingerprint since the first thread is well down the "
        "index now. Nothing rotated, nothing changed. If it ever does I will "
        "sign the announcement with the current key before switching.",
        pgp=PGP_B2,
    ),
    Post(
        "forum-gamma", 57, "quill_v2", "2026-08-01T13:49:00Z",
        "Feedback building up",
        "Feedback is starting to accumulate, which is the point of the "
        f"exercise. Same terms, payment to {WALLET_B}. I will look at slightly "
        "larger batches next month if this holds. Thanks to the people who left "
        "notes rather than just disappearing.",
        wallets=(WALLET_B,),
    ),
    Post(
        "forum-gamma", 58, "quill_v2", "2026-08-18T15:24:00Z",
        "Going quiet",
        "Short note before things go quiet for a bit. Open threads will be "
        "answered. I am reasonably happy with how the restart has gone -- "
        "slower than before but with less noise. Anything outstanding, bump the "
        "thread.",
    ),

    # === forum-gamma / C1 nightjarr ========================================
    # 2026-03-01 -> 2026-08-21, deliberately overlapping A1.  Handle is one
    # character from A1's.  Own PGP, own wallet, sharing nothing with anyone --
    # this is the false positive the system must refuse (DATA_MODEL.md
    # section 4, Actor C).
    Post(
        "forum-gamma", 61, "nightjarr", "2026-03-01T09:18:00Z",
        "Introduction",
        "Introduction post. I have been reading here for a while and finally "
        "got around to registering. I deal in generic archive material, small "
        "volumes, nothing that needs a long conversation. I am aware there is a "
        "similar handle on another board -- no relation, and I picked this name "
        "before I knew about it. Not changing it now.",
    ),
    Post(
        "forum-gamma", 62, "nightjarr", "2026-03-25T13:42:00Z",
        "My key, and the handle question",
        "My key fingerprint, posted for verification. Worth stating clearly "
        "since the handle question keeps coming up: this key is mine, it has "
        "never been used anywhere else, and it does not match anyone else's. If "
        "someone tells you my key is the same as another vendor's, they are "
        "wrong and you can check it yourself.",
        pgp=PGP_C1,
    ),
    Post(
        "forum-gamma", 63, "nightjarr", "2026-04-18T10:05:00Z",
        "Listing terms",
        f"Listing terms. Payment to {WALLET_C1}. This is my only address and it "
        "is not shared with anyone. Turnaround three days, small batches only. "
        "I am not looking to scale this up. Ask in thread and I will answer "
        "when I see it.",
        wallets=(WALLET_C1,),
    ),
    Post(
        "forum-gamma", 64, "nightjarr", "2026-05-16T15:33:00Z",
        "Not the other one",
        "Someone messaged me this week assuming I was a vendor from another "
        "board with a nearly identical name. I am not. I have never posted "
        "there, I do not know them, and we do not deal in the same things. I "
        "would rather clear that up now than have it turn into a dispute later. "
        "Check keys and addresses, not spelling.",
    ),
    Post(
        "forum-gamma", 65, "nightjarr", "2026-06-11T11:57:00Z",
        "Small batches, quick turnaround",
        f"Availability update, small batches as usual. Payment to {WALLET_C1}. "
        "I have had a slow couple of months and the queue is short, so "
        "turnaround is quick at the moment. Feedback thread is up if anyone "
        "wants to leave a note.",
        wallets=(WALLET_C1,),
    ),
    Post(
        "forum-gamma", 66, "nightjarr", "2026-07-08T08:29:00Z",
        "Fingerprint repost",
        "Reposting my fingerprint. Same key as the first thread, nothing "
        "rotated. Given the ongoing confusion about the handle I would "
        "encourage anyone dealing with me to verify this every time rather than "
        "assuming.",
        pgp=PGP_C1,
    ),
    Post(
        "forum-gamma", 67, "nightjarr", "2026-07-30T14:11:00Z",
        "Quiet stretch",
        "Quiet stretch. Still here, still available, nothing much to report. I "
        "have turned down two larger requests this month because they were "
        "outside what I can cover. If that is you, no hard feelings, and I "
        "would rather be honest about capacity than take it on and fail.",
    ),
    Post(
        "forum-gamma", 68, "nightjarr", "2026-08-21T16:47:00Z",
        "End of season",
        "End of season. I will keep an eye on threads but replies will be "
        "slower. Same terms whenever I am active. Thanks to the handful of "
        "regulars -- it has been an uneventful year, which in this context is "
        "the best kind.",
    ),
]


# --- lookups ----------------------------------------------------------------


def posts_for_site(site_id: str) -> list[Post]:
    """Every post on one site, oldest first."""
    return [p for p in POSTS if p.site_id == site_id]


def posts_for_handle(handle: str) -> list[Post]:
    """Every post by one persona, oldest first."""
    return [p for p in POSTS if p.handle == handle]


def personas_for_site(site_id: str) -> list[Persona]:
    return [p for p in PERSONAS.values() if p.site_id == site_id]


def find_post(site_id: str, post_id: int) -> Post | None:
    for post in POSTS:
        if post.site_id == site_id and post.post_id == post_id:
            return post
    return None


def persona_by_handle(handle: str) -> Persona | None:
    for persona in PERSONAS.values():
        if persona.handle == handle:
            return persona
    return None


def format_fingerprint(fingerprint: str) -> str:
    """Space-separated groups of four, as a PGP client would display it.

    `MOCK_SITES_SPEC.md` section 4 allows this for realism and says the scraper
    normalises back to uppercase with no spaces.  Rendering it this way means
    the extractor's normalisation step is actually exercised rather than handed
    an already-normalised string.
    """
    return " ".join(fingerprint[i : i + 4] for i in range(0, len(fingerprint), 4))
