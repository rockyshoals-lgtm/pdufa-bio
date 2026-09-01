# Audit — post decisions-verification + new content opportunities
**2026-08-12 (later) · every line verified against live pages tonight**
*Facts and historical statistics only — not investment advice.*

---

# 1. WHAT THE BUILDER SHIPPED SINCE MY LAST PASS

Five commits, and the big one is a real change in what the site is:

| Commit | What |
|---|---|
| `281bf43` | **198 price-inferred outcomes replaced with primary sources** |
| `64d8395` | Second verification pass — **285 of 457 records now show a primary source** |
| `d190e64` | Killed the price-only resurrection loop; listing rows now name the drug |
| `14e48e5` | **CI source-checks new decisions daily** — nothing enters the archive as a price guess |
| `a3fb3e1` | Calendar rows reconciled against the dataset daily; window restored to the FAQ |

**This is the most valuable work done on the site in weeks.** The decision archive went from 150 sourced / 307 guessed to **285 sourced / 109 inferred / 63 unsourced**, and `14e48e5` means it can't silently regress. The new three-way split is also a *better* disclosure than the old binary — "asserted, no source" is a more honest label than lumping it into "inferred".

---

# 2. 🔴 TWO LIVE DEFECTS — both are page-vs-schema disagreements

## 2.1 The `/decisions` FAQ still publishes the OLD numbers

**This is new, and it undersells your own work.**

| Surface | Says |
|---|---|
| Page body (updated ✅) | "457 records · **Sourced 285** link a primary source · **Inferred 109** read from the price reaction · **Unsourced 63** asserted, no source" |
| **`FAQPage` schema (stale ❌)** | "457 records: **150 verified** against primary sources and **307 inferred** from the share-price reaction" |

The body was updated; the schema wasn't. **The schema is the sentence AI engines lift** — so we are actively telling engines we have 150 sourced decisions when we have 285. We're citing ourselves down.

## 2.2 The calendar count is half-fixed

✅ **Scope drop fixed.** FAQ now reads *"67 FDA decision dates are on this calendar, **covering June 2026 to December 2026**, and 52 are still ahead as of August 12, 2026."* That was my §2(b) — resolved cleanly.

❌ **The count still contradicts.** Same window, same moment:

```bash
curl -s "https://www.pdufa.bio/api/v1/pdufa?from=2026-06-01&to=2026-12-31&limit=500"
# meta.total = 64   ·   Upcoming = 46
# page says      67                52
```

`a3fb3e1` says rows are "reconciled against the dataset daily", so the reconciliation is running but the two surfaces still disagree by 3 and 6. Worth finding out *which* is right — the page may be counting something the API filters (or vice versa), and whichever way it resolves, one of them needs to change.

**Both defects are the same shape: the page learned something the schema didn't.** A CI guard asserting *page number == API number == schema number* would close this class permanently. It's mechanical; no judgement required.

---

# 3. STILL OPEN — verified 404/unchanged tonight

| Item | Status |
|---|---|
| `/patent-cliff` (+ `/2027`) | **404** — data has been ready since this afternoon |
| `/compare/` | 404 |
| `/pdufa/{TICKER}-{date}` per-event URLs | 404 |
| Nav regroup | **still 14 items** |
| Glossary in nav | **still absent**; drug pages still link `/learn/*` but **not** `/glossary` (0 links on rusfertide, zoryve, semaglutide) |
| Glossary clinical terms | not added — "control arm" still not on the site |
| `/pricing` free-trial FAQ | **still live, 2 mentions** |
| "not collecting emails" line | **still live**; no email input anywhere |
| Conferences | **still 14 live, 0 presenters, 0 events in 2027** |

Drug-page depth held: Q=3–6, 429–587 words. No regression.

---

# 4. ⚠️ A TRAP I ALMOST WALKED INTO — read this before publishing any base rate

You asked for new content. The obvious play is *"CRL rate by therapeutic area"* — a high-intent query nobody answers. I computed it from our own 2,203-event corpus:

> Oncology 46.3% · Pain 32.5% · Ophthalmology 31.8% · CNS 23.6% · Infectious disease 10.3%

**Do not publish this.** I checked the denominator before recommending it, and it doesn't hold:

```
events per year in the corpus
2015: 54   2016: 41   2017: 71   2018: 92   2019: 85
2020: 209  2021: 281  2022: 248  2023: 389  2024: 375  2025: 345
```

FDA activity did not increase seven-fold between 2015 and 2023. **That curve is our own coverage growing, not the world changing.** Early years are badly under-collected, so any rate computed across the window is contaminated by collection drift — and the under-collected years are exactly the ones most likely to be missing quiet approvals rather than newsworthy CRLs.

A 46% oncology CRL rate would also be read against FDA's published first-cycle figures (~80% approval for novel drugs) and look wrong, because it's a different denominator: our set includes sNDAs, BLAs and resubmissions at ~200–380 events/year against ~50 novel approvals.

**This is the same discipline `/decisions` already applies** by refusing to publish an overall approval rate over unverified records. The corpus is sound for modelling — walk-forward respects time — but it is **not a census**, and base rates need a census.

**If you want this content, the fix is a documented denominator:** pick a window where coverage is provably complete (2022 onward looks stable at 248–389), state the inclusion rule, publish n alongside every percentage, and say plainly what the set does and doesn't contain. That's publishable. The raw number above is not.

---

# 5. NEW OPPORTUNITIES, RANKED

## 5.1 Free quotability win — fix the `/decisions` FAQ today
Change `150 verified / 307 inferred` → `285 sourced / 109 inferred / 63 unsourced`. Minutes of work, and it makes the *strongest* claim on the site stronger:

> **"285 of 457 FDA decisions in this archive link to a primary source. 109 are inferred from the share-price reaction and 63 carry no source; all three are labelled on every row."**

Nobody else publishes their own sourcing rate. **That sentence is the most quotable thing you own** — it's a verifiable claim about your own rigour, and it invites comparison competitors can't survive.

## 5.2 Ship the patent cliff — the data has been sitting ready for hours
427 drugs, 97% with a therapeutic family, ~30 new indexable pages, an entirely new query family (*"when does SPRYCEL go generic"*), zero ranking risk. Full copy, FAQ set and disclosures are in `2026-08-12e`. **This is the single biggest reach lever available and it's blocked on nothing.**

## 5.3 Per-decision FAQ — 285 pages × one question
Every sourced decision page can carry:

> **Q: Was [drug] approved?**
> **A:** "The FDA approved [drug] on [date]. [Company] announced it in [source]."

That's ~285 exact-match answers for *"was X approved"* / *"did X get FDA approval"* — the highest-intent query in this category — each backed by a citation. **Same mechanism that already gives `/drug/rusfertide` 16.67% citation share, applied to the archive.**

## 5.4 Glossary clinical terms + nav placement
Still the cheapest unclaimed query family: *"what is a control arm"*, *"what does single-arm mean"*, *"what is a primary endpoint"*. Page exists, is good, and is unreachable. Add the 15 clinical terms, per-term anchors, `FAQPage`, and put it in the nav.

## 5.5 The differentiator nobody can copy
Competitors publish **dates**. You now publish **outcomes with citations, and an honest count of how many lack one.**

That's not a content advantage, it's a trust advantage, and it compounds: every AI engine that has to choose a source for "was drug X approved" will prefer the one that shows its work. Lean into it — put the sourcing ratio on the homepage, not buried on `/decisions`.

---

# 6. ORDER

| # | Item | Why | Effort |
|---|---|---|---|
| 1 | `/decisions` FAQ → 285/109/63 | we're citing ourselves down | minutes |
| 2 | Delete free-trial FAQ + rewrite email line | consumer misstatement, still live | minutes |
| 3 | Resolve calendar 67 vs 64 + guard page==API==schema | closes this defect class permanently | hours |
| 4 | **Ship `/patent-cliff`** | data ready, biggest reach lever | 2 days |
| 5 | Per-decision FAQ across 285 sourced pages | highest-intent query, generated | 1 day |
| 6 | Glossary clinical terms + nav | cheapest unclaimed queries | 1 day |
| 7 | Conference miner fix, then publish 41 + 9 | still >90% contaminated | 1 day |
| 8 | Email capture (needs privacy policy) | owned audience | 1 day |

---

# 7. BOTTOM LINE

The verification work is the most important thing shipped this week — 198 guesses replaced with primary sources, and CI that stops it regressing. That changes what the site *is*.

But **both live defects are the same failure**: the page learned something the schema didn't. On `/decisions` it's now costing you, because the stale schema tells engines you have 150 sourced decisions when you have 285. Fix that tonight; it's minutes and it strengthens your best claim.

On new content: **the patent cliff is ready and still 404** — that's the biggest reach lever and it's blocked on nothing. And I'd resist the tempting one. The CRL-rate-by-therapeutic-area page is a high-intent query we appear to have data for, and the data won't carry it. Our own event coverage grows 7× across the window; that's collection drift, not FDA behaviour. Publishing it would break the exact rule that makes the rest of the site citable.

---
*Verify every date and outcome against primary FDA / SEC / company filings. Not investment advice.*
