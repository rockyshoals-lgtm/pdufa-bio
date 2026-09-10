# Final audit: the sweep fixes verified live, and a correction to my own method
**2026-09-09. Live build `2026-09-09T22:53:26Z` commit `cff1c0ff3`. Every figure below re-read with a forced reload (`age: 0`, `x-vercel-cache: MISS`), for the reason in section 3.**
*Facts and build mechanics only. Not investment advice.*

---

# 1. THE SWEEP FIXES ARE LIVE AND CORRECT

| Item | Verified live |
|---|---|
| **TLX, our next decision (Friday)** | `to treat` **0 times**. Story now reads *"TLX101-Px is under FDA review for PET imaging to characterise recurrent or progressive glioma from treatment-related changes."* **Pixclara** present. Stamp **"Updated September 9, 2026"**, was August 15. All three defects closed. |
| **Manufactured day-15 dates** | Non-day-precision rows carrying a `date`: **0** (was 325). Rows ending in `-15`: **2** (was 263). |
| **Blank company names** | **2** (was 265). CORT's forward PDUFA, both AdComms and the KYTX readout all filled. The 2 remaining are CNTA, which the builder left blank and reported rather than guessed. |
| **MRK 2026-09-21** | **The date is right.** The builder found it by EDGAR full-text search: Merck's 8-K of 2026-02-03 (EX-99.1) and its Q2 2026 10-Q both state *"The FDA set a PDUFA date of September 21, 2026"* for the HYPERION-based sBLA. My flag was correct as filed (uncited, not wrong) and the row is now sourced twice to the sponsor's own filings. |

Two things worth naming beyond the checkmarks.

**The builder fixed the TLX generator and the published pages separately, and explained why.** A generator-only fix would have corrected future pages and left every existing one wrong, because the page builder never overwrites an existing page. That is the same class as the frozen-per-event-pages failure from early September, caught this time before it shipped.

**It also recorded two of its own errors inside that fix** — a lower-cased "pET imaging", and a sentence saying the product "is marketed under the brand name Pixclara" when it is under review and the name is proposed. Both are in the script's comments so they are not re-invented. That is the standard.

**And the EDGAR method is worth keeping.** `efts.sec.gov/LATEST/search-index?q="<drug>"+"<Month D, YYYY>"&forms=10-Q,10-K,8-K` returns JSON and finds a goal date inside a filing when the press-release trail has none. It settled MRK in one query after three web searches had failed. That should be the first move on any "no source" row, not the third.

---

# 2. THE ONE THING I GOT WRONG, AND IT IS A METHOD PROBLEM, NOT A ONE-OFF

**On my first read of the live API this session I measured 325 manufactured dates and 265 blank company names, and nearly filed it as "the builder's verified-live claim does not hold."** It does hold. My read was a cached body from before the fix.

Here is the instrumentation, because the detail matters:

```
build-info.json, three consecutive fetches, cache:'no-store' + Cache-Control: no-cache,
each with a DIFFERENT ?cb=<timestamp> query string:

  try 0   age: 14356   x-vercel-cache: HIT
  try 1   age: 14357   x-vercel-cache: HIT
  try 2   age: 14359   x-vercel-cache: HIT
```

Identical age across three different query strings, four hours stale, every one a HIT. Only `cache: 'reload'` produced `age: 0`, `MISS`.

**The query-string cache-buster does nothing.** Vercel's own cache-key documentation says query strings are ignored for static files, which I quoted in my 09-08e note without drawing the obvious conclusion about my own tooling. **Every `?v=<nanoseconds>` buster I have used in these audits has been a no-op**, and `Cache-Control: no-cache` as a *request* header does not force a revalidation at this CDN either.

Two consequences, and I would rather state both than the comfortable one:

1. **Some earlier "verified live" claims in this series were made against bodies of unknown age.** I do not know which. Where a check passed, a stale body would more likely have shown the *old* state and produced a false failure than a false pass, so the risk skews toward my having reported defects that were already fixed. The 09-08 "I reproduced the CDN stale-body issue" entry is the clearest example, and it now reads as method rather than discovery.
2. **The 09-07 CDN finding is no longer a candidate; it is reproduced with headers.** A four-hour-old body under a no-cache request, and, earlier in this same session, a `build-info.json` dated **2026-08-08** served to the browser while `web_fetch` returned September 9. That month-old body I saw once and could not reproduce in three follow-up fetches, so I record it as observed, not established.

**What this changes for the builder's verifier:** its passes are only meaningful if it forces a true MISS. If it is fetching the way I was, a PASS means "the cache agrees with itself." Worth confirming the verifier uses a real revalidation and not a query-string buster.

---

# 3. STILL OPEN, IN THE ORDER I WOULD TAKE THEM

| # | Item | Why it still matters |
|---|---|---|
| **1** | **`source_url` / `page_url` split (sweep item 5)** | MRK's source now exists in the dataset and **is not in the API response**: the row still returns `url: pdufa.bio/pdufa/MRK` and no source field. The work of sourcing it is done; a consumer still cannot see it. This is the single highest-value open item, because it converts "trust us" into "check us" across every forward row. |
| **2** | **Four day-precision PDUFAs dated December 31**: ABBV Tavapadon (TEMPO), AZN Ultomiris, BAYRY KERENDIA, NVO CagriSema | Same placeholder shape as the day-15 cluster we just removed, one field over. Four sponsors sharing a New Year's Eve goal date is implausible on its face. Each needs a source or a precision downgrade. **Unverified from this evidence** — I have not checked them against filings. |
| 3 | **The CORT row's three self-contradictions**, found by the builder while filling its company | A readout-shaped id carrying the retired 15th, `ta: "Infectious"` for Cushing's syndrome, and `source: "trial-estimate"` against its own review note citing Corcept's June 17 announcement. One row disagreeing with itself three ways. |
| 4 | Nine forward PDUFAs with no indication; per-event re-stamp (TLX now stamps correctly, so confirm it generalises) | sweep items 7 and 8 |
| 5 | **The false-GOLD regression** in `readout_gold_dates.py` | Not on pdufa.bio: it is the internal `latest/` feed. But nine GOLD rows claimed AAAAI, EULAR and ACTRIMS congresses on New Year's Eve, and the cause was a pdufa.bio fix from 09-07 that got swept onto `hypestock-wip` when four hypestock commits were moved. **That is the second time this class of loss has happened** (the `window_precision` work on 08-24). The patch and a `_gold_leak_check.py` guard are already written up. |

---

# 4. WHERE THE SITE STANDS

**Data.** Nine exhaustive structural checks across all 456 rows come back clean, and the two large integrity exposures I found this morning are closed the same day: no manufactured days in the API, two blank company fields instead of 265. The published "20 of 32 sourced decisions came early" reconciles exactly to the live data. The remaining known gaps are enumerated above rather than unknown.

**Guards.** 78, up from 55 a week ago, and the new ones assert the things that actually went wrong: no diagnostic described as a treatment, no blank company on a PDUFA or AdComm row, one company spelling per ticker, no listing boilerplate, no manufactured day in the API shaping code. Each proved 0 → planted 1 → healed 0.

**Channels**, as of the Sept 7 data: Bing 331 clicks and 11.1K impressions on 563 ranked keywords; AI citations 3.8K with grounding queries at 20, the first move off 19 in two weeks; `fda calendar 2026` up 90 citations to 291 and share to 30.83%; Google flat at 53 clicks for a fifth read. The snippet fixes from Sept 8 are still too recent to appear in either console.

**The infrastructure question that remains open** is the CDN, and it is now better instrumented than argued: a four-hour-old body under a no-cache request, a month-old one seen once, a Vercel token that will not authenticate because of a bug on their side, and a purge that Vercel's own cache-key documentation suggests may not be the remedy. The right next step is unchanged and costs nothing: the next time the verifier catches a stale body, purge by hand from the dashboard and see whether it clears.

---

# BOTTOM LINE

**Everything the sweep found this morning that could be fixed today, was.** The next decision on the site no longer calls a PET imaging agent a treatment, and it names Pixclara. The API no longer serves a day nobody announced, on 325 rows. Two company fields are blank instead of 265. And the one date I could not source, MRK's September 21, turned out to be right and is now cited twice to Merck's own SEC filings, found by a search method worth keeping.

**The correction is mine.** I read the API through a cache and nearly reported a false regression against work that had shipped correctly. The cause is that the query-string cache-buster I have been using throughout these audits does nothing at this CDN, which I had the documentation for in my own note yesterday and did not apply to my own tooling. The upside is that the CDN staleness we have been chasing since September 7 is now reproduced with response headers rather than inferred, and the verifier should be checked for the same flaw.

**Four December-31 PDUFA dates are the next thing I would look at**, and I have not verified them. They have the same shape as the placeholders we removed today.

---
*All figures re-read 2026-09-09 with forced revalidation. Build `cff1c0ff3`. MRK sourcing verified from Merck's 8-K of 2026-02-03 and Q2 2026 10-Q as quoted by the builder. Not investment advice.*
