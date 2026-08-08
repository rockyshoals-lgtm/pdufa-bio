# 2026-07-21 — final two backlog items

## RHHBY Giredestrant on 11-30 and 12-18 — NOT a duplicate
The audit flagged it as "duplicate or two indications — needs distinguishing." Verified against
Roche IR: **two genuine, distinct NDAs.**
- **2026-11-30** — giredestrant monotherapy, **adjuvant early** ER+/HER2− breast cancer (lidERA
  Phase 3, −30% recurrence/death). Priority review.
- **2026-12-18** — giredestrant **+ everolimus**, ESR1-mutated **metastatic** ER+ breast cancer
  (evERA Phase 3, −44%/−62% progression/death).

Roche itself describes "a potential dual-approval scenario within a single calendar window." The
rows already carry different drug strings and indications on both surfaces, so they render
distinctly. **No change — correctly two events.**

## `/` vs `/calendar` canonical conflict — FIXED
Google flagged `/calendar` "Duplicate, Google chose different canonical than user." Root cause
found: the **homepage `<title>` started with the identical phrase** — "2026 FDA PDUFA Calendar" —
as `/calendar`'s title. Two near-identical PDUFA-calendar pages with the same leading title phrase;
Google consolidated them and picked the homepage as canonical for both.

Both pages already self-canonicalise correctly, so the fix is differentiation of intent:

| | before | after |
|---|---|---|
| `/` title | "2026 FDA PDUFA Calendar — Dates & Run-up History" | **"pdufa.bio — FDA Catalyst Tracker: PDUFA Dates, Trial Readouts & Run-up"** |
| `/` description | "Every upcoming FDA PDUFA decision on one screen…" | dashboard framing: PDUFAs + readouts + AdComms + conferences (165 chars) |
| `/calendar` | "2026 FDA PDUFA Calendar" | unchanged — it *is* the by-month index |

The homepage now targets the **tracker/dashboard** intent (brand + multi-catalyst) and `/calendar`
owns the **"2026 FDA PDUFA calendar"** head term. og:/twitter titles updated to match; all homepage
JSON-LD re-validated. Deployed and verified live: distinct titles, each self-canonical.

This is the on-page half of the canonical fix. The other half is the owner's: once Google
re-crawls (blocked today by the stale non-www sitemap — SEO-3), the distinct signals let it keep
`/calendar` canonical to itself.

## Guard suite: 7, all passing.

## Backlog status after this week
**All four AUDIT_2026-07-19 P0s closed and guarded** (fan-out dual-surface, API precision,
research figures, conferences). **All P1 #5–#7 done** (homepage Event schema, `/api` redirect,
null-drug rows 13→0 all verified, NVCR date, `/`↔`/calendar` canonical). Two more royalty-vs-
applicant errors (ANAB, IONS) caught and corrected in passing.

### Remaining — all owner or model work, none builder-actionable on-page
- **SEO-3** delete stale non-www `pdufa.bio/sitemap.xml` in Search Console (the real indexing lever)
- **SEO-1** stale ODIN titles evict on re-crawl; guard prevents regression
- **P0-4** CLAUDE.md ODIN block · **P0-5** ODIN retrain · **P1-4** BIFROST SI panel — model work
- **P2** CRL tracker copy, market-cap null publish, `/watchlist`, mobile QA, Stripe/Resend keys
- 🟡 past-dated readout estimates auto-flip to "Awaiting data" — nice-to-have; the page already
  labels them "(est.)" and the API now says `month`, so nothing false is published meanwhile
