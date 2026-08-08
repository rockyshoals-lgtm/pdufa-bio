# Static-page guard shipped — and it caught a live phantom on run #1

## The guard: `tests/test_static_pages_match_slate.py`
Closes the structural gap that let the ticker fan-out ship twice: **every prior guard read the
DATA layer (api/data.js, dataset.mjs, CSVs); none read the rendered HTML.** So the homepage,
screener and month calendars kept rendering phantom rows while every test passed, and the defect
was found by hand.

Rule: the authoritative truth is the **slate** (api/data.js forward catalysts) **+ the decisions
archive**. Every ticker a static listing page renders as a `/pdufa/{TICKER}` row must appear in
one of those. Scans the homepage, /calendar, /screener, all month calendars, and every
/condition/* page — 22 pages, 207 known tickers. Verified it fails on an injected `/pdufa/EVAX`.

## What it found immediately: a triple-corrupt GH (Guardant Health) row
On the very first run it flagged `condition/cancer` rendering `/pdufa/GH`. GH was in **neither**
the slate nor the archive — and inspection showed why it should never have been anywhere:

| surface | what it claimed |
|---|---|
| dataset.mjs | GH · 2027-05-15 · **FOLFIRI+cetuximab** |
| /pdufa/GH page | GH · **Dec 31 2026** · **Camizestrant** · Guardant Health |
| condition/cancer + readouts/2027/may | GH · May 2027 · FOLFIRI+cetuximab · **Metastatic NSCLC** |

Three different dates, three different drugs, none coherent: Camizestrant is **AstraZeneca's**
SERD, FOLFIRI+cetuximab is a **colorectal** chemo regimen (not NSCLC, not a Guardant product).
Verified against primary sources: **Guardant Health makes diagnostics** (Shield, Guardant360 CDx)
— it has **no drug PDUFA**. Pure garbage from a bad join, and it had been live.

## Purged everywhere, deployed, verified
Removed GH from `dataset.mjs` (385→384), stripped the rendered rows from `condition/cancer`,
`screener`, and `readouts/2027/may`, retired `/pdufa/GH` (301 → /calendar), removed it from the
sitemap. Live checks: 0 GH rows in the API, gone from condition/cancer, `/pdufa/GH` 301s clean.

## Guard suite now 8, all passing
static-pages-match-slate · no-ticker-fanout (dual-surface) · api-precision-honesty ·
research-figures-match-source · no-fabricated-conferences · crawler-no-regression ·
seo-invariants · si-display-cap

**These 8 now cover both halves of every "the page and the data disagree" defect this month:**
the data guards catch a bad row in api/data.js or dataset.mjs; the static guard catches a bad row
rendered into HTML even when the data layer is clean. That was the missing half.

## Sitemap question answered
Delete **`https://pdufa.bio/sitemap.xml`** (non-www) in Search Console → Sitemaps → that row → ⋮ →
Remove sitemap. Keep only `https://www.pdufa.bio/sitemap.xml`. Both URLs now serve the same live
523-URL file, but GSC still uses the non-www entry's stale Jun-25 read (170 Feb-era URLs) — that's
what feeds the dead-URL set. Removing the entry is the fix; nothing on the live site changes.

## Remaining — owner / model only
SEO-3 (delete non-www sitemap, above) · SEO-1 (stale ODIN titles evict on re-crawl; guarded) ·
P0-4 CLAUDE.md ODIN block · P0-5 ODIN retrain · P1-4 BIFROST SI panel · P2 polish.
No on-page builder P0/P1 items remain open.
