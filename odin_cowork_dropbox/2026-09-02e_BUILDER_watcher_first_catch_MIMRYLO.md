# The early-approval watcher's first real catch — MIMRYLO (rusfertide), 33 days early
*2026-09-02 late evening (Pacific). Facts and build mechanics only — not investment advice.*

## What happened

On its second production day, `watch_fda_approvals.py` BLOCKED the CI run: FDA's
Drugs@FDA feed showed an ORIG-1 TYPE 1 AP dated 2026-08-28 for rusfertide, an armed
event with a September 30 goal date. Verified against Takeda's August 28 release and
FDA's own press announcement: **MIMRYLO (rusfertide) was approved August 28 for
erythrocytosis in polycythemia vera — 33 days before the goal date** (Phase 3 VERIFY,
NCT05210790, 76.9% response weeks 20-32, priority review; Protagonist discovered,
Takeda commercializes).

Our site — including /pdufa/PTGX, the 20%-CTR page your SEO audit called a conversion
champion — had shown it pending for five days. No crawl, feed, or human had caught it.
The watcher did, exactly as designed: exit 1, verify, publish.

## Published, all surfaces verified live

API `Decided / Approved / 2026-08-28` · decision page titled "MIMRYLO (rusfertide)
Approved Aug 28, 2026, 33 Days Early" with the Takeda source and a +54.7% measured
120-day run-up · event-page banners on /pdufa/PTGX and /pdufa/PTGX-rusfertide ·
timing sample **n=29 (17 early / 9 on / 3 after)** — the early-decision evidence keeps
strengthening · calendar row marked · listing, slate, hubs, lede, today page all synced.

The wide evidence-gated matcher flipped the dataset row automatically at −33 days
(lead-token "rusfertide" across MIMRYLO's brand name) — the exact gap class that
required manual work for AZN's −18 last time.

## Two collisions found and fixed during the publish

1. `build_decision_page.py` clones the VERA template and literal-replaced VERA's
   ORIGINAL title — which the snippet rewriter had since rewritten, so the new PTGX
   page briefly shipped titled "Trutakna (atacicept)". Now a regex replace; the same
   one-owner-per-field class the 09-02c audit flagged.
2. The GILD hits alongside were the lenacapavir cross-product trap in watcher form
   (Bixlenvo's Aug 27 approval matching the separate once-weekly Yeztugo application,
   goal Feb 2027, still pending) — acked in `_fda_watch_ack.json` with the reason.

Also for the record: a swallowed `checkout --ours` failure during a rebase earlier
tonight briefly shipped conflict markers across the site tree; caught by
`test_no_conflict_markers`, repaired by resetting to CI's tree + full deterministic
regen. 56 guards green, CI green, all surfaces live-verified.
