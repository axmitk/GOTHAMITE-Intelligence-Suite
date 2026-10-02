# Persona scoring: how the weights were set, and what they do not prove

This note covers the `same_actor_suspected` score in
`gothamite/backend/services/correlation_service.py`. It records where each number came
from, how the scenario set relates to those numbers, the known failure cases, and the
plan for calibration.

## 1. The weights are hand-set priors

| Signal | Weight | Condition |
|---|---|---|
| Shared PGP fingerprint | +0.70 | identical normalised 40-hex fingerprint |
| Shared wallet | +0.25 | identical address string (was +0.45 until 2026-10-02; see §4) |
| Lexical similarity | 0 (off; was +0.25 until 2026-10-03, see §5) | term-frequency cosine ≥ 0.85 between the first stored artifact of each persona |
| Temporal succession | +0.15 | one persona's last post precedes the other's first post by fewer than 45 days |
| Handle similarity | +0.05 | Levenshtein distance ≤ 1, or ≤ 2 when no PGP key is shared |
| Concurrent activity | −0.30 | activity windows overlap and no PGP key is shared |

The score is the sum of the weights, clamped to [0.00, 0.95]. An edge is proposed at
0.30 or above. Only persona pairs from different sources are compared.

**No data was used to choose these numbers.** The five exact-match weights, the 0.30
threshold and the 0.95 cap were written into the data-model specification
(`gothamite/Docs/DATA_MODEL.md` §3) in the project's first documentation commit, on
2026-09-06. That was before any code or scenario data existed. They were set by
judgement, by ranking the signals on how hard each one is for an unrelated person to
produce by accident:

- **PGP fingerprint, the strongest signal.** Controlling the matching private key is
  needed to sign with it. The weight alone clears the threshold.
- **Wallet, next.** Reusing an address is costly for an actor who wants separation.
  However, addresses are also shared, quoted and reused by services, so the weight now
  sits below the threshold.
- **Lexical similarity, now switched off.** Short posts make writing-style evidence
  weak. This signal was added later and was first labelled "AI stylometric match" in
  the code. It is a bag-of-words cosine, not a trained model, and was renamed on that
  basis. Since 2026-10-03 its weight is 0 (see §5).
- **Timing and handle shape, weak.** These are circumstantial and easy to imitate.
  They can only tip a score that other evidence has already built.
- **Concurrent activity, a penalty.** One person running two personas at the same time
  is possible but less likely than two people. The penalty is large enough to cancel a
  wallet match or a handle match, but not a shared key.

## 2. Why the scenario results are not validation

The persona scenario set is small and was written by the team to exercise these rules:

- 6 personas on 3 sources, with 6 stored artifacts and 13 identifiers.
- 15 persona pairs. Of these, 3 are same-source and skipped, and **12 cross-source pairs
  are scored**.
- 2 ground-truth same-actor pairs: `nightjar` ↔ `n1ghtjar_` (shared key and wallet) and
  `quillfeather` → `quill_v2` (rebrand, key rotated).
- 10 ground-truth negatives, including 1 deliberate look-alike decoy (`nightjarr`).
- 1 `transacted_with` interaction, which is never promoted to identity.

Result: 2 of 2 links found, and 0 of 10 negatives linked.

**This is circular, and the project records show it.** The expected score for each
scenario was computed from the weights when the scenario was written. When the
scenario data and the weights disagreed, **the data was changed, not the weights**:

- **SD-018** (`darkweb-sandbox/AgentsDocs/SPEC_DECISIONS.md`). The rebrand's boundary
  dates were corrected so that the gap matched the 17 days that the expected 0.60 score
  had assumed.
- **SD-027**. A marketplace post that quoted another persona's wallet as a counterparty
  produced a false `same_actor_suspected` edge at 0.45. The post was removed from the
  corpus. The rule was not changed. SD-028 then added a corpus rule, "no page carries
  another persona's identifier", to keep such posts out.

So the scenario set shows that the code does what the rules say on the cases the rules
were designed for. It says nothing about precision or recall on real data, and it
should not be called a benchmark.

## 3. Known failure cases

The scraper attributes every PGP fingerprint and wallet on a page to the page's author.
It records mentions, not ownership. `gothamite/tests/test_identifier_mentions.py` pins
down what happens when someone quotes another person's identifier, for example in a
scam-warning post:

| Case | Score | Result | Test status |
|---|---|---|---|
| Quoted wallet; poster active > 45 days after the owner went quiet | 0.25 | no edge | pass |
| Quoted wallet; poster active at the same time as the owner | 0.00 | no edge | pass |
| Quoted wallet; poster first appears < 45 days after the owner's last post | 0.40 | **edge (false)** | xfail, strict |
| Quoted PGP public-key block | 0.70 | **edge (false)**. A shared key also switches off the overlap penalty. | xfail, strict |
| Quoted wallet on pages sharing a site template (`tests/test_lexical_template.py`) | 0.25 (was 0.50 with lexical on) | no edge | pass |

Other limits of the current rules:

- **Shared service addresses.** Escrow, exchange-deposit and mixer addresses are not
  excluded. Two customers of one escrow address get +0.25 each time.
- **Same-source sock puppets are never compared.** Two handles on one forum are never
  scored against each other.
- **All pairs are compared.** The cost grows with the square of the number of personas,
  and there is a database query per pair. There is no blocking on shared identifiers
  yet.

## 4. Change on 2026-10-02: wallet weight 0.45 → 0.25

At 0.45, one shared wallet string cleared the 0.30 threshold on its own. That is the
same false edge SD-027 hit, and SD-027 avoided it by editing the data. At 0.25 a wallet
needs at least one other supporting signal.

Effect on the scenario set:

- `nightjar` ↔ `n1ghtjar_` stays at 0.95, because 0.70 + 0.25 is still capped.
- `quillfeather` → `quill_v2` moves from 0.60 to 0.40 (wallet 0.25 + succession 0.15).
  The link still forms. Its display band changes from strong to moderate.
- No negative pair changes outcome.

## 5. Change on 2026-10-03: lexical weight 0.25 → 0

The lexical signal compares the raw HTML of each persona's first stored page. In an
end-to-end run over pages scraped through the sandbox, it fired on 8 of the 12 pairs,
6 of them negatives, because the shared page template dominated the vocabulary. With
it on, a quoted wallet on two templated pages scored 0.50 and formed a false edge
(`tests/test_lexical_template.py`), and the rebrand pair scored 0.65.

Comparing visible text only stopped the firing but did not separate the pairs. On
the same 12 scraped pairs, the two true pairs scored 0.796 and 0.798, while the 10 negatives scored 0.706 to 0.808, and one negative (nightjar and quill_v2, 0.808) scored above both true pairs. A signal
that cannot tell true pairs from negatives should not add to an attribution score,
so its weight is 0 until real stylometry exists. The code skips the comparison
entirely while the weight is 0 (`LEXICAL_WEIGHT = 0.0` in `correlation_service.py`).

Effect: seed set unchanged (0.95 and 0.40; it never fired there). Scraped set:
nightjar ↔ n1ghtjar_ 0.95, quillfeather → quill_v2 0.40 (was 0.65), no false edge.

## 6. Calibration plan

1. **Build a labelled pair set from public sources**, with each label's source recorded:
   - aliases confirmed in court records or takedown announcements;
   - vendor migrations announced with a signed message from the same key;
   - pairs known to be different actors.
2. **Separate identifier ownership from mention at extraction.** Treat a key block or
   wallet posted on the persona's own profile or signature as owned, and one inside
   quoted or warning text as mentioned. Only owned identifiers score as identity.
3. **Fit one weight per signal** (logistic regression, or per-signal likelihood ratios)
   on a training split. Report precision and recall on a held-out split, and choose the
   threshold from the precision analysts will accept.
4. **Keep the hand-set values as the documented prior.** Publish any change with the
   data and the evaluation behind it.
