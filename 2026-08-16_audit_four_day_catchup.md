# Audit — four-day catch-up
**2026-08-16 22:20 UTC · every line verified against live pages tonight**
*Facts and historical statistics only — not investment advice.*

---

# 1. THE BUILDER SHIPPED THE ENTIRE BACKLOG

Eleven commits since my last pass. Verified live, not taken on trust:

| Item | Status | Evidence |
|---|---|---|
| **`/patent-cliff` — 40 pages** | ✅ **LIVE** | hub 738w · `/2027` 1,182w · `/company/abbvie` · `/cancer` all 200 |
| Cliff disclosures | ✅ | "earliest date… could enter" ×2, settlements ×1, "not a guarantee" ×1–2 per page |
| Cliff never-say sweep | ✅ **clean** | no "goes generic on", "guaranteed", "rejection" |
| **My BALCOLTRA fix carried through** | ✅ | `/patent-cliff/cancer` → **0** BALCOLTRA hits, SPRYCEL present |
| **Glossary clinical terms** | ✅ **DONE** | 1,525w → **2,442w**, 14 → **32 `DefinedTerm`s**, 32 anchors, `FAQPage` added |
| — control arm / single-arm / primary endpoint / hazard ratio / PFS / OS / CI / non-inferiority | ✅ all present | 4 / 4 / 9 / 7 / 3 / 5 / 1 / 1 |
| **Nav regrouped** | ✅ | Calendar · Decisions · Readouts · **Patents** · [Explore ▾] · [Research ▾] · API — the 3 orphans surfaced |
| **`/decisions` FAQ ↔ body** | ✅ **FIXED** | both now say **286 of 458 sourced · 109 inferred · 63 unsourced** |
| Decision-page FAQ | ✅ | `/fda-decision/VTRS-2026-07-29` carries `FAQPage` |
| **`/pricing` free-trial claim** | ✅ **GONE** | 0 mentions |
| "not collecting emails" line | ✅ **GONE** | 0 mentions |
| Conferences page | ✅ | 41 meetings, 2027 events live, presenters shown |
| Conference provenance disclosure | ✅ **excellent** | "we can source to a filing or company release. **This is not the full programme**" ×12 |
| LNTH TAUKLARIFY approval | ✅ published Aug 13 |

**The quotable sentence I recommended is live almost verbatim:**

> *"286 of 458 FDA decisions in this archive link to a primary source. 109 are inferred from the share-price reaction and 63 carry no source; all three states are labelled on every row."*

That is the strongest claim on the site and no competitor can match it.

---

# 2. 🔴 THE ONE RECURRING DEFECT: page ↔ API divergence

Three audits running, same structural failure — **a surface learns something and another surface doesn't.**

## 2.1 Calendar counts still disagree, and the gap has grown

| | Page | API, same window |
|---|---:|---:|
| 08-12 | 67 / 52 | 64 / 46 |
| **08-16** | **73 / 57** | **68 / 49** |

```bash
curl -s "https://www.pdufa.bio/api/v1/pdufa?from=2026-06-01&to=2026-12-31&limit=500"
# meta.total = 68 · Upcoming = 49    page says 73 / 57
```

Gap went from 3/6 to **5/8**. `a3fb3e1` reconciles rows daily, but the reconciliation clearly isn't comparing against the API's own count. The page also stamps *"as of August 15"* while today is the 16th.

**This is in `FAQPage` schema.** We are feeding engines a number our own API contradicts, and it's drifting wider.

## 2.2 `/api/v1/conferences` never got the update

| Surface | Conferences | Presenters | 2027 events |
|---|---:|---:|---:|
| `/conferences` page | **41** | **9+** | ✅ yes |
| **`/api/v1/conferences`** | **14** | **0** | **0** |

The page shipped; the API didn't. And `/llms.txt` advertises `/api/v1/conferences` to AI crawlers — so the machine-readable surface we deliberately point AI at is serving four-month-old data with no presenters.

**One guard closes both:** assert page count == API count == schema count for every hub, in CI. Mechanical, no judgement.

---

# 3. 🟠 TWO WRONG-EDITION PRESENTER ROWS ARE LIVE

The mined-file gate **held** — `build_conferences.py` correctly requires `confidence == 'high'`, and legacy rows lack that column so they're excluded by construction. That was well done.

But there's a **third source read with `gate=False`**: `catalysts_out/conference_presentations_history.csv` (754 rows). Ten of its rows publish. **Eight are genuinely good.** Two are not:

| Row | Published as | The sentence | Problem |
|---|---|---|---|
| **BOLT → SITC 2026** | Nov 4, 2026 | *"In November at the **40th Annual Meeting** of the Society for Immunotherapy of Cancer"* | SITC 2026 is the **41st**. The 40th was 2025 — and the filing accession is a **2025** filing. |
| **IMNM → ENA 2026** | Nov 18, 2026 | *"In October, **Immunome presented** a poster entitled HC74"* | Past tense, already-delivered poster, **2025** filing. |

Both are the edition-mismatch bug — the same one the miner was fixed for, in a file the fix doesn't cover.

**Fix:** run the history file through the miner's own `PAST_GOV` and `edition_ok()` before publishing. `PAST_GOV` catches IMNM ("Immunome presented"); edition-anchoring catches BOLT ("40th" against a 2026 conference). Note `confidence` does **not** separate them — BOLT is 0.75 and good rows are 0.55 — so gate on the rules, not the score.

---

# 4. ⚠️ I OWE THE BUILDER A CORRECTION — MOLN/ESMO

On 08-12 I **rejected** MOLN/ESMO from my verified set: *"the captured sentence never establishes an ESMO 2026 presentation."* The builder published it anyway.

**The builder was right.** A Molecular Partners press release filed July 16, 2026 states plainly:

> *"Trial-in-progress poster **to be presented at ESMO 2026 in October**."*

My rejection was correct **about the evidence I had** — the miner had captured a weaker sentence from the same document. But better evidence existed in the history file, and the row is true. Publishing it was the right call.

Also worth noting: EVAX and MGNX, which I flagged as unverified-by-me, both hold up — *"Evaxion **to present** … at the **ESMO Congress 2026**"* and *"Interim Phase 1 results **accepted for poster presentation** at **ESMO Congress 2026**."*

**Lesson for me:** rejecting on one weak sentence when a second source exists is a false negative. When I reject a row, I should say "unverified from this evidence" rather than implying the claim is false.

---

# 5. STILL OPEN

| Item | Status |
|---|---|
| `/compare/` pages | 404 — the last unbuilt content surface |
| Per-event PDUFA URLs `/pdufa/{T}-{date}` | 404 |
| Email capture form | not built — but **both blocking false claims are now gone**, so this is unblocked |
| Privacy policy / terms / refund / contact | still absent — blocks both email capture and payments |

---

# 6. ORDER

| # | Item | Why | Effort |
|---|---|---|---|
| 1 | **Guard: page == API == schema counts** | third audit on the same defect; it's widening | hours |
| 2 | **Rebuild `/api/v1/conferences`** | AI crawlers are pointed at stale data | hours |
| 3 | Gate the history file through `PAST_GOV` + `edition_ok()` | 2 false statements live | hours |
| 4 | Privacy policy + terms + refund + contact | blocks email *and* payments | 1 day |
| 5 | Email capture form | audience compounding | 1 day |
| 6 | `/compare/` pilot (5 pages) | last content surface | 2 days |
| 7 | Per-event PDUFA URLs | AI cites specific URLs | 1 day |

---

# 7. BOTTOM LINE

Four days, eleven commits, and essentially the entire backlog is now live and **verified** — patent cliff with correct disclosures, a real clinical glossary, a regrouped nav that finally surfaces three orphaned pages, and a `/decisions` archive that states its own sourcing rate in a sentence engines can lift. The conference provenance line — *"this is not the full programme"* — is exactly the right instinct.

Two things to fix, and one is stubborn:

**The calendar page and the API have now disagreed for three audits, and the gap grew from 3 to 5.** Whatever the daily reconciliation compares, it isn't the API's own count. That number sits in FAQ schema, so it's the one being quoted.

**`/api/v1/conferences` is four months stale** while the page is current — and that API is what `/llms.txt` hands to AI crawlers.

And I got one wrong: MOLN/ESMO was a true row that I rejected on weak evidence. The builder's publish call beat my reject call.

---
*Verify every date and outcome against primary FDA / SEC / company filings. Not investment advice.*
