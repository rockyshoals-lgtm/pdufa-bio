# Audit — 2026-09-02 (final) · the watcher's first catch, and a P0 the guards missed
**Live build `2026-09-03T01:12:12Z` · every claim cache-busted against that build**
*Facts and historical statistics only — not investment advice.*

---

# 0. HEADLINE

**The early-approval watcher made its first real catch, and I verified it against FDA's own record — it is exactly right.**

**But the daily refresh that ran 3 hours later silently deleted 229 drug pages. They are 404 on the live site right now, and 63 internal links point at them.**

Both things are true tonight. The safety net you asked for last week worked. A different layer, with no safety net, broke.

---

# 1. ✅ MIMRYLO — THE WATCHER'S FIRST CATCH, VERIFIED AGAINST FDA

I did not take the builder's word for this. I queried **FDA's Drugs@FDA record directly**:

```
app:      NDA220605
sponsor:  TAKEDA PHARMACEUTICALS U.S.A., INC.
brand:    MIMRYLO      active: RUSFERTIDE ACETATE
ORIG-1    submission_status: AP        status_date: 20260828
```

| Claim | Site | FDA | ✓ |
|---|---|---|---|
| Approval date | 2026-08-28 | **20260828** | ✅ exact |
| Goal date | 2026-09-30 | — | ✅ |
| Days early | 33 | 30 Sep − 28 Aug = **33** | ✅ arithmetic holds |

The live page reads:

> *"✓ Approved · the FDA decided this application on **August 28, 2026, 33 days before** its September 30, 2026 goal date."*

**This is the case the watcher was built for.** A 33-day-early approval on a September goal date is precisely the failure mode that let REGN sit at "Awaiting" for 13 days — an event nobody would have re-checked, because its goal date hadn't arrived. The crawl didn't find it. **FDA's own feed did, because we now ask.**

**The duplicate was resolved the right way, and it was not obvious.** Rusfertide is Protagonist's molecule but **Takeda holds NDA 220605** — so a `TAK` record and a `PTGX` record both had a claim to being real. The builder retired the TAK artifact and kept PTGX. I checked the result: **exactly one rusfertide row in the API, ticker PTGX.** For a catalyst tracker that is the correct call — PTGX is the listed name a reader is tracking.

---

# 2. ✅ THE CONFLICT-MARKER INCIDENT — REPAIRED PROPERLY

Commit `1aa8c856a` shipped **980 files containing git conflict markers**. It was caught and repaired in `1e247c6b1`.

**Exposure was two minutes.** `1aa8c856a` at 17:58 Pacific → `1e247c6b1` at 18:00 Pacific. *(RULE 1: both are Pacific author timestamps; the live build stamp is UTC.)*

**Live is clean** — 0 markers across `/calendar`, `/decisions`, `/decisions/crl`, `/conferences`, `/adcomm`, `/developers`.

**And the repair itself was clean, which I checked rather than assumed.** The poisoned sitemap listed **879 drug URLs** — but only **554 unique**. The extra 325 were the conflict duplicating both sides of every hunk. The repair commit restored it to exactly **554 unique**. No data was lost in the repair.

That matters for §3, because it establishes the true baseline: **554 is the real number.**

---

# 3. 🔴 P0 — 229 DRUG PAGES DELETED BY THE ROUTINE DAILY REFRESH

The repair was fine. **The next commit — the ordinary `chore: daily data refresh 2026-09-03` — is what broke things.**

```
afb99d0bd  (audit 09-02c actioned)     554 unique /drug/ URLs
1e247c6b1  (REPAIR)                    554 unique /drug/ URLs   <- clean
6a2e3c28f  (daily data refresh 09-03)  325 unique /drug/ URLs   <- -229
```

**Lost: 229. Gained: 0.** Pure deletion. It is live now:

```
/drug/bixlenvo   404      /drug/arexvy   404
/drug/zusduri    404      /drug/ajovy    404
```

**And 63 internal links across the built site point at deleted pages.**

## The deleted set is disproportionately brand names

Spread evenly across A–Z, so this is a content-based cull, not a truncation. But look at what went:

> adcetris · afrezza · ajovy · akeega · amvuttra · arexvy · auvelity · awiqli · **bixlenvo** · zepzelca · **zusduri** · zynyz

**These are approved brand names — the highest-intent queries on the site.** `/drug/bixlenvo` is GILD's drug approved six days ago. `/drug/zusduri` is the drug I quoted from URGN's snippet in last night's audit as a model of the new format. Both are 404 tonight.

## Why nothing caught it

There is **no floor guard on the page corpus.** I checked all 56.

The bitter irony: **the builder invented exactly the right pattern in this same batch** — for the CRL letters —

```python
assert n >= 10, (f"only {n} decision pages carry an FDA letter card (floor 10) -- ")
```

**That guard exists because I asked for CRL letters. Nobody asked for a floor on drug pages, so there isn't one.** The pattern was already in their hands; it just wasn't pointed at the biggest corpus on the site.

## The fix

1. **Restore the 229 pages** and re-run the sitemap.
2. **Guard 57 — corpus floor:** *no build may reduce any page-type count by more than 5% versus the previous build.* Same shape as the CRL floor guard, applied to `/drug/`, `/pdufa/`, `/fda-decision/`, `/conference/`.
3. **Guard 58 — no internal link may point at a path that does not exist in this build.** That catches the 63 broken links as a class, permanently.

*A floor guard that only protects the thing someone complained about protects one thing. Make it protect the corpus.*

---

# 4. ⚠️ WE HOLD MIMRYLO'S BRAND NAME AND THROW IT AWAY

`alternateName` **did ship** — the rusfertide page carries `["PTG-300","PTG-300FB"]` from the ChEMBL synonyms pass. That is real, and it is the work I asked for.

**But it delivers code names, not brands.** `MIMRYLO` appears **zero times** anywhere on `/drug/rusfertide` or `/pdufa/PTGX`.

Across all 554 drug pages: MIMRYLO 0 · PASATRU 0 · LYTENAVA 0 · ZUSDURI 0.

**Here is the part worth acting on: we already fetch the brand name and discard it.** The watcher's own openFDA call returns it in the same payload as the approval date it acts on:

```
brand: MIMRYLO      active: RUSFERTIDE ACETATE      AP 20260828
```

**Zero new data sources. Zero new API budget.** When the watcher confirms an approval, write `openfda.brand_name` into `alternateName` alongside the decision date it is already writing. Every future approval self-populates its own brand.

That matters because **grounding queries have been stuck at 18 for two weeks** while citation depth climbs. Breadth comes from entities, and *"what is MIMRYLO"* is a query we cannot currently be cited for on a drug we correctly called 33 days early.

---

# 5. ✅ THE REST OF THE 09-02c BATCH — VERIFIED

| Item | Claimed | Verified |
|---|---|---|
| `"X (X):"` snippet fix | 187 pages | ✅ **0 remaining** — now *"LLY: Inluriyo was approved on September 25, 2025."* |
| CRL pages citing FDA's letters | 11 | ✅ **11 of 51** CRL pages — floor-guarded |
| ChEMBL synonyms → `alternateName` | 259 drugs | ✅ deployed (see §4 on what it does and doesn't cover) |
| Guards | 56 | ✅ 56 |
| Advertised API endpoints | — | ✅ 6× 200, 3× 403 (pro-gated, correct) |

**On the CRL letters — the claim was honest and I want to say so.** "11 pages" is 11 of 51 CRL pages, not 11 of 458 letters. The builder stated the number they achieved rather than the corpus they hold. **40 CRL pages still have no letter; the constraint is name-matching, not the corpus.**

---

# 6. 🟡 MINOR — `/api/v1/dataset.mjs` returns HTTP 500

Reproducible across four attempts, no query parameters.

**I am flagging this at low severity and stating why**, because I have twice reported this API broken when it wasn't. `dataset.mjs` is **not advertised on `/developers`**. The nine documented endpoints are all healthy. This is an internal module path, not a customer-facing contract — but a hard 500 on any route is worth a look.

---

# 7. ✋ A CORRECTION TO LAST NIGHT'S AUDIT

I wrote: **"`Drug` schema on 554 drug pages — DEPLOYED, 14/14 in a random sample."**

**That was wrong, and my method is why.** My sample drew from pages that existed. **166 of the directories were empty** — the sample could not draw from them because there was nothing to draw. I measured the pages that were there and reported it as coverage of the corpus.

Actual at that commit: **388 of 554 had `Drug` schema.** I reported 100% from a sample that structurally could not find the gap.

**The lesson is the same one from the Bing incident:** a check that can only observe successes is not a check. Sampling live pages cannot detect missing pages — that needs a count against an expected total, which is precisely what guard 57 above would do.

---

# 8. ORDER

| # | Action | Why |
|---|---|---|
| **1** | **Restore the 229 drug pages** | live 404s on brand-name URLs, 63 broken internal links |
| **2** | **Guard 57 — corpus floor (±5% per page type)** | the pattern already exists for CRL letters; point it at the corpus |
| **3** | **Guard 58 — no internal link to a non-existent path** | catches the 63 as a class |
| 4 | Wire watcher `openfda.brand_name` → `alternateName` | brand entities, zero new data sources |
| 5 | `/decisions/crl` hub: 0 `fda.gov` links; lede says 47, links 44 | long-standing |
| 6 | `/crl` hub · `/pdufa-date-changes` | still 404 |
| 7 | **Sept 8 console read** | first honest read on `/fda-decisions-today`, `/learn/what-is-a-pdufa-date` — **and on whether the 229 URLs were indexed before they went** |

---

# BOTTOM LINE

**The watcher works.** MIMRYLO was approved 33 days early on a goal date that hadn't arrived, our own crawl didn't see it, and **FDA's feed told us because we now ask**. I verified the date against NDA 220605 directly — it matches to the day. The TAK/PTGX duplicate was resolved correctly on a genuinely ambiguous case. That is the safety net doing exactly what it was built for, on its first real test.

**And three hours later, a routine daily refresh deleted 229 drug pages.** Brand names — bixlenvo, zusduri, arexvy, adcetris — 404 on the live site, with 63 internal links pointing at them. **Nothing caught it, because all 56 guards check the correctness of what exists and none checks that things still exist.** The builder wrote the perfect countermeasure in this same batch — a floor guard — and aimed it at the CRL letters, because that is what I asked about.

**The pattern across both halves of tonight is one thing:** the layers we deliberately instrumented held, and the layer nobody thought to instrument failed silently. The early-approval gap got a watcher after REGN. The page corpus needs the same, and it needs it before the next daily refresh.

**And I owe a correction:** I certified `Drug` schema on 554 pages from a 14/14 sample. It was 388, and my sample couldn't have found that out — it drew only from pages that existed, and the gap was pages that didn't.

---
*Verified against the 2026-09-03T01:12:12Z build. Approval verified against FDA Drugs@FDA NDA 220605. Not investment advice.*
