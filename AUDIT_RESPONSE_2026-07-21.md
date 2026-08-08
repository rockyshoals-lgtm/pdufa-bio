# 2026-07-21 — MASTER_BACKLOG action pass

## 🔴 P0-A — now ACTUALLY closed on the API surface

The backlog's top open item: *"`/api/v1/events` still returns all three [BNTX/CTMX/EVAX] … The
page is clean and the API is not."* Correct. The v1 API is served by **`dataset.mjs`**, a separate
file from the `api/data.js` SLATE I had cleaned. Fixed:

- Removed from `dataset.mjs`: BNTX, CTMX, EVAX (2026-08-17), MIRM (09-26), ONC (08-25),
  RPRX (08-25 + 09-18), and the decided MRK/PFE/ALPMY (08-17, approved 2026-07-10). 398 → 385.
- Live `/api/v1/events` verified: 08-17 now shows only BMY; 08-25 shows JAZZ + ZYME; all seven
  bad tickers return 0 PDUFA rows.

**The guard now reads BOTH surfaces.** `test_no_ticker_fanout.py` was checking only `api/data.js`
— which is *exactly why P0-A looked closed while the API was wrong*. It now loads `dataset.mjs`
too and fails if either surface has a join artifact. Verified by re-injecting the original defect
into the dataset surface: it fails. This is the structural gap from yesterday's writeup, closed.

Also flipped 1 stale `Upcoming` past-dated row (CELC) to `Decided` in dataset.mjs; the guard's
past-dated check now only fires on rows still claiming `Upcoming`, so a correctly-decided event
no longer trips it.

## 🟢 13 null-drug rows → 0, all verified against primary sources

The audit flagged "a decision with no drug." Rather than guess, I verified each of the 13 (NVCR
was the 13th, fixed earlier) against company IR / FDA. **9 filled, 3 removed/suppressed, 1 already
done:**

| ticker | date | filled with | source |
|---|---|---|---|
| CYTK | 2026-11-14 | Aficamten — MAPLE-HCM (non-obstructive HCM) | Cytokinetics 8-K |
| COGT | 2026-11-30 | Bezuclastinib + sunitinib (GIST) | Cogent IR |
| GILD | 2026-12-23 | Anito-cel (4L+ multiple myeloma) | Gilead Q1 8-K |
| GILD | 2027-02-02 | Yeztugo (lenacapavir) once-weekly oral PrEP | Gilead IR |
| GSK | 2026-10-26 | Bepirovirsen (chronic hep B) | GSK 6-K |
| NUVB | 2027-01-04 | IBTROZI (taletrectinib) sNDA (ROS1 NSCLC) | Nuvation IR |
| IBRX | 2027-01-06 | ANKTIVA + BCG (papillary NMIBC) | ImmunityBio IR |
| ARQT | 2027-02-23 | ZORYVE cream 0.05% (infant atopic dermatitis) | Arcutis IR |
| PHVS | 2027-04-23 | Deucrictibant IR (HAE on-demand) | Pharvaris IR |
| NVCR | 2026-Q4→11-15 | TTFields NSCLC brain-mets PMA (quarter precision) | NovoCure 8-K |

**Two more royalty-vs-applicant errors found and removed** — the same class as ONC/RPRX:
- **ANAB 2026-12-12** — imsidolimab GPP is **Vanda's** BLA (VNDA is applicant); ANAB holds a royalty.
- **IONS 2026-10-26** — bepirovirsen is **GSK's** application; IONS holds a royalty. Also a
  duplicate of the correct GSK 10-26 row.

Both posted to `/corrections`. **1 suppressed:** MRK 2026-09-21 — I could not verify any catalyst
on that date (WINREVAIR/ZENITH was Oct-2025, already decided; enlicitide still Phase 3). Suppressed
rather than invent one. Live API confirms **0 null-drug PDUFA rows**.

Also fixed the audit's `NVCR 2026-Q4` non-ISO date → `2026-11-15` with `date_precision: quarter`
and a real drug (verified: TTFields for NSCLC brain metastases, PMA expected Q4 2026).

## Freshness sweep (2026-07-21)
- `check_pdufa_decided.py` → clean, no forward PDUFA already decided
- Price cache current to 07-20 (1 day); slate `as_of` 07-17, 0 past-dated rows
- Removed a stale BIIB 2026-08-24 (LEQEMBI IQLIK, approved 2026-07-13) still in dataset.mjs

## Not actioned — owner / SEO (correctly diagnosed in the backlog)
- **SEO-3** delete the stale non-www `pdufa.bio/sitemap.xml` from Search Console — **owner action**.
- **SEO-4** `/pdufa-calendar` redirect error freezing Google's link graph — I re-verified the live
  redirect is a single clean 308 → 200 with no chain/loop for a normal UA; the "redirect error" is
  in Google's cache, and clears once it re-fetches (the non-www sitemap deletion is the real lever).
- **SEO-1** stale ODIN titles in Google's index — live site clean; `test_seo_invariants` prevents
  regression; eviction needs Google to re-crawl.
- P0-4 (CLAUDE.md ODIN block), P0-5 (ODIN retrain), P1-4 (BIFROST SI) — model/owner work.

## Guard suite: 7, all passing (fan-out now dual-surface)
no-ticker-fanout · api-precision-honesty · research-figures-match-source ·
no-fabricated-conferences · crawler-no-regression · seo-invariants · si-display-cap

## Still open (🟠)
- `/` vs `/calendar` canonical differentiation
- RHHBY Giredestrant appears on both 2026-11-30 and 2026-12-18 (dup or two indications — needs a look)
- Past-dated readout estimates auto-flip to "Awaiting data"
