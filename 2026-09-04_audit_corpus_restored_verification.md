# Audit — 2026-09-04 · corpus restored, readouts corrected
**Live build `2026-09-04T22:42:23Z` · every claim checked against that build**
*Facts and historical statistics only — not investment advice.*

*Note: the local clone sits at `00322fade` (Sep 2); live has rebuilt twice since. **Everything below is checked against the live site**, not the local tree.*

---

# 1. ✅ EVERY P0 AND EVERY RECOMMENDATION IS DONE

| Item | Status | Evidence |
|---|---|---|
| **229 deleted drug pages** | ✅ **RESTORED** | sitemap now **559 unique** `/drug/` URLs — above the 554 baseline |
| The 8 URLs I found 404 | ✅ **all 200** | adcetris · amvuttra · auvelity · benlysta · andembry · asceniv · bixlenvo · zusduri |
| Random spot-check | ✅ **12 / 12 → 200** | drawn from the live sitemap |
| **Guard 57 — corpus floor** | ✅ `test_corpus_floor.py` | high-water ratchet, fails below 95% |
| **Guard 58 — internal links** | ✅ `test_internal_links_resolve.py` | |
| **Guard 59 — guided readouts** | ✅ `test_guided_readouts_current.py` | **0** Guided readouts past date, live |
| Guard count | ✅ **59** (was 56) | + `test_drug_schema.py`, `test_decision_snippets.py` |

## The corpus floor guard is better than what I asked for

I asked for "±5% per page type." They built a **ratchet**:

> *"`_corpus_floor.json` records the high-water page count per page type. A build whose count falls below 95% of the floor FAILS. When a count grows, the floor rises… a deliberate retirement must lower the floor **by hand, in the same commit, with a reason**."*

The hand-lowering requirement is the part I didn't specify and should have. **A floor that any build can silently lower is not a floor.** Making the reduction a deliberate, attributed act is what turns this from a check into a record.

They also quoted the audit line back in the file header — *"a floor guard that only protects the thing someone complained about protects one thing."* Fair.

**And `test_drug_schema.py` is aimed squarely at my sampling error.** I certified `Drug` schema 554/554 from a 14/14 sample when it was 388/554. A guard that counts against an expected total is exactly the check my sample structurally could not perform.

---

# 2. ✅ ALL FOUR READOUTS CORRECTED — AND THE TRIAL-NAME BUG IS FIXED

| Ticker | Was | Now | ✓ |
|---|---|---|---|
| **TENX** | "LEVEL-2 readout", 2026-08-31 month, Guided | **"TNX-103 Phase 3 LEVEL topline", 2026-08-10 day, Reported** | ✅ right trial, right day |
| **MPLT** | "ML-007C readout", 2026-08-31 month, Guided | **"ML-007C-MA Phase 2 ZEPHYR topline", 2026-07-27 day, Reported** | ✅ |
| **TYRA** | 2026-08-31 month | **2027-12-31 year, Guided** | ✅ the ~1-year error is gone |
| **ALZN** | 2026-08-31 month | **2026-09-30 quarter** | ✅ |

**Both now cite the exact primary sources** — the GlobeNewswire releases, verbatim URLs. Provenance is clean.

The LEVEL / LEVEL-2 distinction being fixed matters more than it looks: **LEVEL-2 is still enrolling into 2027.** Had that name stayed attached to an August 2026 date, we'd have been publishing a completed result under an ongoing trial's name.

---

# 3. ✅ SLS — ALL THREE ITEMS DONE

**AACR Conference on Pancreatic Cancer added**, and the details match my verification exactly:

> *"Pancreatic Cancer · Sep 25 to 28, 2026 · in 21 days · San Diego, CA (Hilton San Diego Bayfront) · Oncology - Pancreatic · official site"*
> *"SLS — SLS009 (tambiciclib) — **PRECLINICAL**"*

**The `PRECLINICAL` label is there, in caps, on the listing itself.** That was the thing I most wanted and least expected to survive — the temptation with a conference row is to let it read like a data catalyst. It doesn't.

**REGAL's self-referential source is fixed** — it now cites the August 11 8-K rather than `pdufa.bio/sls`.

*Small open question, not a defect: we render it as "AACR **Special** Conference on Pancreatic Cancer"; the release says "AACR Conference on Pancreatic Cancer: New Frontiers in Biology and Therapeutic Development." AACR has used "Special Conference" branding historically, so this may be correct — worth one look at the official page rather than a change on my say-so.*

---

# 4. 🔴 ONE REAL DEFECT: `/readouts` attributes a stock move to a readout that hasn't happened

**TYRA's date was corrected in the data. The `/readouts` page didn't follow.**

I pulled the raw DOM rather than trusting a text match, because I have produced phantom page-vs-API discrepancies with regex before. This is a real element:

```html
<a class="row" href="https://ir.tyra.bio/.../tyra-biosciences-reports-second-quarter-2026-financial-results">
  <div class="t">TYRA &middot; Aug 2026</div>
  <div class="d">SURF303 Phase 2a/b initial results (LG-UTUC)</div>
  ... sparkline ...  -8%
```

| Source | SURF303 date |
|---|---|
| API (`/api/v1/events`) | **2027-12-31**, Guided ✅ |
| `/readouts` module | **Aug 2026**, with a **−8% move** ❌ |

**This is worse than a stale date. It shows a measured market reaction to an event that, by our own corrected data, has not occurred.** A reader sees a number that looks like evidence and is attached to nothing.

The linked source is TYRA's **Q2 2026 results** — which is where the *2027* guidance came from. So the module appears to be keying its date off the **source document's month** rather than the event's target date. If that's the mechanism, it will misdate every readout whose guidance was published in a different period from the event — which is most of them.

**Fix:** point that module at the event date, and add it to guard 58's family — *no readout row may render a date that disagrees with its dataset row.*

---

# 5. 🟠 WE NOW RECORD **THAT** A READOUT HAPPENED, BUT NEVER **WHAT IT SAID**

`outcome` is **null** on both TENX and MPLT. I checked three surfaces — `/readouts`, `/calendar`, `/ticker/TENX`:

```
"did not meet"      0 occurrences
"met its primary"   0
"primary endpoint"  0
```

`/ticker/TENX` names the LEVEL topline and dates it to Aug 10. **It never says what happened.** The only outcome signal anywhere is the sparkline: **TENX −88%**.

**That's market reaction standing in for fact, and it's backwards for us.** A reader sees −88% and infers a catastrophe. The actual, checkable facts are more useful *and* more nuanced:

- Primary endpoint **not met** — 6MWD difference **3.5 m, p=0.63**
- Prespecified subgroup below 333 m: **+26.3 m**, nominal p=0.0112
- NT-proBNP **−49% vs placebo**, nominal p<0.0001
- The company's own caveat: *"Nominal p-values are not adjusted for multiplicity and these analyses do not establish efficacy."*
- Tenax has requested a **Type C meeting** with FDA

MPLT is the mirror case — ZEPHYR **met** its primary endpoint on PANSS at Week 5, and the site says only **+39%**.

**We built the whole decision archive around stating the outcome in words** — *"received a Complete Response Letter,"* never "rejected." Readouts deserve the same treatment. Populating `outcome` and a one-sentence plain-language result would carry that discipline across, and it's the same work that made decision pages our best-converting page type.

---

# 6. STILL OPEN (long-standing, none from this batch)

| Item | Status |
|---|---|
| `/decisions/crl` hub — 0 `fda.gov` links; lede says 47, links 44 | ❌ |
| `/crl` hub · `/pdufa-date-changes` | ❌ 404 |
| 40 of 51 CRL pages carry no letter | ❌ name-matching, not corpus |
| `alternateName` — brand names (MIMRYLO, PASATRU) still absent | ❌ watcher already fetches `brand_name` |
| 51 `Estimated` readouts past mid-month placeholder dates | 🟠 re-estimate or age out |
| `/terms` `/privacy` `/refund-policy` `/contact` | ❌ 404 — block the email list and the paywall |
| `/api/v1/dataset.mjs` → 500 | 🟡 not advertised; 9 documented endpoints healthy |

---

# 7. ORDER

| # | Action | Why |
|---|---|---|
| **1** | **TYRA on `/readouts`** — render the event date, drop the −8% | a stock move attached to a non-event |
| **2** | Extend guard 58's family: readout row date must match its dataset row | closes the class |
| **3** | Populate `outcome` + a plain-language result for TENX and MPLT | we say *that* it happened, never *what* |
| 4 | Watcher `brand_name` → `alternateName` | citation breadth; zero new data sources |
| 5 | `/decisions/crl` links + lede reconciliation | long-standing |
| 6 | **Sept 8 console read** | first honest read on `/fda-decisions-today`, `/learn/what-is-a-pdufa-date`, and whether the 229 restored URLs re-index cleanly |

---

# BOTTOM LINE

**Yes — everything I raised is up to date, and the two guards are better than what I specified.** All 229 drug pages are back (559 unique, above the old baseline), 12 of 12 random URLs resolve, and the corpus floor is a **ratchet that must be lowered by hand with a reason** rather than a threshold any build can slide past. Guard 59 works: **zero** guided readouts sit past their date. All four readout corrections landed with the right trial names, the right dates, and the exact primary sources. The AACR Pancreatic listing carries `PRECLINICAL` on its face.

**Two things remain, and both are the same shape — the data got fixed and a rendering surface didn't follow.** `/readouts` still shows TYRA at "Aug 2026" with a **−8% move on a readout that won't happen until 2027**; I confirmed that in the raw DOM rather than by text match. And `outcome` is null on TENX and MPLT, so the only thing a reader learns about a Phase 3 that missed its primary endpoint is that the stock fell 88%.

**We spent months making decision pages say *"received a Complete Response Letter"* instead of *"rejected."* Right now the readouts surface says nothing at all and lets a sparkline do the talking.** That's the last gap worth closing before the Sept 8 console read.

---
*Verified against the 2026-09-04T22:42:23Z build. Not investment advice.*
