# Conference crawler — coverage audit & upgrade
**2026-07-12** · answers: *"does the current one get them all?"*

## Verdict: no. It was searching 15 of 46 conferences.

The crawler queries SEC full-text with **named conference phrases**. It had **15**. The registry knew **46**; the study contains **50**. Everything else could only leak in through three generic phrases (`late-breaking abstract`, `oral presentation at`, `poster presentation at`) — and those were a *weak net*, not a workhorse:

- Named searches produced **214 of 229** rows (93%).
- The three generic phrases produced **15 rows** (7%) — spread across 7 conferences we never search for.
- Proof they under-sample: **EASL has 35 events in our history; the crawler found 3.** **ASCO-GI has 21; it found 0.**

Unsearched conferences accounted for **310 / 1,555 = 19.9% of the historical event mass.**

## What changed

| | before | after |
|---|---|---|
| Named EDGAR searches | **15** | **40** |
| ALIASES entries | 61 | **92** |
| Registry conferences | 46 (1 dup) | **51** |
| Historical coverage | 1,245/1,506 = **82.7%** | 1,483/1,506 = **98.5%** |
| Dead search phrases (find but can't label) | — | **0** (verified) |

### Conferences added as first-class searches
**Biggest gaps first:** EASL (n=35 — the single largest miss), ASCO-GI (21), AAAAI (17), **ASGCT (14 — cell & gene, core to our universe)**, ENDO (13), ASCO-GU (12), AAO / AAD / ATS / CTAD / EULAR (11 each), ARVO / AAIC / ACAAI (9), ECTRIMS (8), ADPD (7), ACNP / SNO (6), ISTH / ERS / ATTD (5).

**Not previously in the registry at all** — added with `doy` only, so they resolve as *month-precision, `date_basis=projected`* rather than inventing a day: **ASTRO, DDW, ObesityWeek, ESMO Breast, CROI, ACTRIMS**.
ESMO Breast matters immediately — it's on our own watchlist (ALXO, May 7) and the crawler could not have seen it.

## Bugs found and fixed

1. **`ANE` is not a conference.** 47 events in the study — the **7th-largest row in the published by-conference table**. Its registry "dates" jump between March, June and October across years; `conf_full` is empty; every row is an oncology asset (petosemtamab, ZL-1310, ZW191) with anchors that look like ASCO/ESMO/ASH. It is a **parse artifact that swept up real presentations under a meaningless code**. The events are genuine and stay in the headline sample; the **row is pulled from the table and the removal is disclosed on the page**.
2. **Duplicate registry key** — `IDWEEK` and `IDWeek` were two entries for one conference. Merged.
3. **ALIASES keys are lowercase.** My first patch added them in Title Case — all 28 would have been **silently dead** (found the filing, failed to label it). Caught on verification, redone lowercase, and I now assert `0 dead phrases` as a check.
4. **`AD/PD` vs `ADPD`** alias miss — both now map to ADPD.
5. **`PRE-RELEA`** — a truncated junk code (n=2), excluded alongside ANE.

## What adding search phrases will NOT fix

**Selection bias is the real ceiling.** The crawler finds companies that *filed* about a presentation (8-K / PR on EDGAR). A company that presents quietly is invisible, and no number of search phrases changes that. We do not currently know what fraction of actual presenters we catch.

The honest way to measure it: pull a published abstract list (ASCO and AACR both expose searchable abstract databases), intersect against US-listed tickers, and compute our recall. Until we do, "98.5% coverage" means *98.5% of the conferences we know about* — **not** 98.5% of presenters. Those are different claims and the page should not conflate them.

## Still unsearched (deliberately)
SGO (4), AES (3), ESCMID (3), ASRS (3), IDWeek (2), MDA (2), ASCRS (2) — **~19 events, 1.3%**. Each new phrase is another full-text EDGAR query on a crawl that is already slow. Poor ROI; left out on purpose.

## Next
- **Re-run the crawler.** The last output predates the ticker fix, the H2-2026 registry dates, *and* all of the above. Expect materially more rows, especially EASL / ASGCT / the CNS block.
- Then rebuild `/research/conference-runup` from the deepened set.
- **Measure recall against a real abstract list** before we make any coverage claim on the page.
