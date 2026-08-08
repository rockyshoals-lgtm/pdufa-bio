# 🎯 pdufa.bio — MASTER BACKLOG
**Updated: 2026-07-18 (AM re-audit, parallel to builder)** · Everything below **verified live**.
**Builder: start at the top open item and work down.**

---

## 📊 SEO STATUS — 2026-07-18

### ✅ BIG WINS since last audit
- **`/ticker/{TICKER}` hubs SHIPPED — 210 pages in the sitemap.** P1-3, the item I'd called "the only winnable SEO path," is live. Verified: `/ticker/CELC|MNKD|OTLK|CORT` all 200, ~6.5–7.6KB each, `BreadcrumbList + ItemList` schema, aggregate PDUFA + Readout + Conference + AdComm + past decisions, and cross-link to 6 other pages. **The MNKD hub correctly captures BOTH its catalysts** (Afrezza pediatric + FUROSCIX) — real aggregation, not a stub.
- **Sitemap 338 → 546 URLs, still 100% www.** `/ticker` 210 · `/fda-decision` 144 · `/pdufa` 100 · `/conference` 14. `lastmod` runs to **2026-07-18** — fresh.
- **`/glossary`, `/about`, `/corrections`, `/changelog` all in the sitemap now.**
- `robots.txt` clean: allows all, `Disallow: /api/`, declares the www sitemap.

### 🟢🟢 INDEXING ROUND 5 (2026-08-07) — SITEMAP P0 CONFIRMED FIXED + FIRST REAL INDEX MOVEMENT
**🎯 THE P0 WORKED. GSC Sitemaps now: submitted Aug 7 · LAST READ Aug 7 · 473 discovered** (was: submitted Jul 21, last read **Jul 27**, 520 discovered). Google is re-reading the sitemap again — the sitemap-ping fix from the 08-03 brief is live and working.
**📈 INDEX COUNTS MOVED (vs 2026-08-02):** Indexed **36 → 51** (+15, +42%) · Not indexed **522 → 456** (−66) · **"Discovered – currently not indexed" 478 → 421 (−57)** · "Crawled – not indexed" 13 → 3. Exactly the metric predicted in the playbook. *(GSC report "Last update: 8/4/26" — still lags, so more movement likely already banked.)*
**Submitted this round (all confirmed "Indexing requested"):** `/tickers` (new A–Z hub, Discovered-not-crawled) · `/sls` (flagship, **"URL unknown to Google"**) · `/screener` (indexed → recrawl to pick up its 192 new outbound links) · `/vktx` (unknown to Google) · `/fda-decision/MRNA-2026-08-05` (fresh mFLUSIVA approval).
**Not submitted:** `/ticker/BMY` — held until the Bevacizumab title bug is fixed. `/fda-decision/REPL-2026-08-02` — **404, page doesn't exist** despite the API carrying the Decided/Approved record (NEW GAP: decision detail page not generated for REPL).
**Still open from the 08-07 audit (unchanged on live site):** BMY title still "…FDA Catalysts: Bevacizumab"; `readout_bmy_2026-09-15` still name="Bevacizumab"; MRNA still "mRNA-1010 - (P304)" (no **mFLUSIVA**) with **self-referential** url `pdufa.bio/pdufa/MRNA`; REPL still "RP1 (vusolimogene oderparepvec)" (no **TUDRIQEV**) with url pointing at the Jul 30 AdComm 8-K not the Aug 6 approval; `/sls` still emits **zero JSON-LD**; `/calendar`+`/decisions` still 0 ticker links; `/surges` still 404 in sitemap; sitemap still flat.

### 🔎 INDEXING ROUND 4 (2026-08-02, later) — hot names submitted + ROOT CAUSE FOUND
**Submitted (all confirmed "Indexing requested"):** `/pdufa/MRNA` (PDUFA Aug 5) · `/pdufa/BMY` (Aug 17 + AZ merger news) · `/ticker/AZN` · `/pdufa/CAPR` (Aug 22) · `/pdufa/REGN`. **Also RESUBMITTED sitemap.xml to force a re-read.**
**🔴 ROOT CAUSE of the 478 "Discovered–not indexed": Google last read sitemap.xml on Jul 27, 2026 (6 days stale), seeing 520 pages.** GSC Sitemaps page: Submitted Jul 21 · **Last read Jul 27** · 520 discovered. Every sitemap improvement since (VTRS added, lastmod refresh, restructure) is invisible to Google. That's why `/pdufa/BMY` and `/pdufa/REGN` both report **"URL is unknown to Google" + "No referring sitemaps detected"** even though both ARE in the current sitemap. **Not a sitemap-content bug — a sitemap-refresh/ping bug.**
**→ ACTION for builder: ping Google on every deploy** — either `GET https://www.google.com/ping?sitemap=https://www.pdufa.bio/sitemap.xml` (deprecated but harmless), or better, the **Search Console API `sitemaps.submit`**, or IndexNow for Bing. Without a ping, a static sitemap can go a week+ between reads at this authority level.
**Also found:** every inspected page shows **"Referring page: None detected"** (MRNA, BMY, AZN, CAPR, REGN) despite real internal links from `/calendar` (23 pdufa links) and homepage — consistent with Google not having recrawled the linking hubs recently. Reinforces the internal-linking + crawl-budget thesis.
**Sitemap changed mid-session: 520 → 429 URLs**, newest `<lastmod>` now includes **2026-08-03 (future-dated again)** — the as_of/UTC-rollover bug has resurfaced in the sitemap generator. `/pdufa/LNTH` and `/pdufa/IONS` now 308-redirect and are correctly absent.

### 🔴🔴 P0 SLS + HOT-NAME SEO 2026-08-02 — see `AUDIT_2026-08-02_SLS_AND_HOT_NAMES.md`
**FALSE FDA CRL PUBLISHED:** `/fda-decision/SLS-2025-02-20` renders "✗ CRL" for SELLAS — **impossible**, SELLAS has never filed an NDA/BLA (GPS Phase 3, SLS009 Phase 2). Page self-labels "~ price-only (validating)" = inferred from a price move. SLS is the #1 retail-voted biotech right now. DELETE/noindex + retract + log on /corrections.
**SYSTEMIC: 308 of 450 decision pages (68%) are "price-only" inferences rendered as definitive ✓/✗ fact** (142 sourced, and those are good — VTRS/OTLK/MRK/CELC/BIIB all have real primary-source links). They also feed the "221 appr · 96 CRL · 70%" headline stat. Fix: noindex the inferred tier (sitemap ALREADY excludes all 308 — good instinct, extend it to robots meta) or relabel visibly as unverified + split the stats.
**SLS coverage gap:** ticker page says "no upcoming catalyst on file" but REGAL Ph3 (GPS, AML CR2, NCT04229979) is event-driven at 80th event — 78 as of 2026-05-11, topline guided Q4 2026; plus SLS009 Ph2. Add as month/quarter-precision readout w/ event-driven flag.
**SEO:** `/ticker/SLS` NOT indexed (`site:` confirms); Google's "people also search" for SLS = mortgage/Dubai/toothpaste — **bare-ticker titles can't bind to the biotech entity**. Fix all 208 ticker titles/H1 → "SELLAS Life Sciences (SLS)" + drug + trial + NCT + Organization/Dataset JSON-LD w/ sameAs.
**OPPORTUNITY:** SERP for "SELLAS REGAL readout date" = IR + **Reddit** + Yahoo + LARVOL; pdufa.bio nowhere. PAA asks "When is the SLS Phase 3 readout?" — our exact product. Add FAQPage blocks per ticker (like /condition/cancer, our best performer). Hot names: SLS, BMY/AZN ($400B merger talks Aug 2), MRNA (PDUFA Aug 5), REPL (PDUFA Aug 2 STILL MISSING), CAPR (Aug 22), REGN, VKTX (**no page — 404**), IBRX.
**✅ Confirmed fixed:** Events schema now 14 valid/2 invalid (was 94% ineligible); sitemap lastmod 2026-08-02 + recent decisions included.
**Self-correction:** my 08-01 "303 decision pages missing from sitemap" was mostly BY DESIGN (price-only exclusion); real gap was ~10 sourced pages, now added.
**⚠️ Indexing BLOCKED this session** — GSC omnibox rejected all input, screenshots CDP-erroring. Queue: /ticker/SLS (only AFTER CRL fix), /pdufa/BMY, /ticker/BMY, /ticker/AZN, /pdufa/MRNA, /pdufa/REGN, /ticker/CAPR, /ticker/IBRX.
**Note:** Core Web Vitals = "No data" both mobile+desktop (insufficient CrUX traffic).

### ✅ VERIFICATION AUDIT 2026-08-02 — see `AUDIT_2026-08-02_VERIFICATION.md` (origin-verified, x-vercel-cache MISS)
**ALL 6 prior items CONFIRMED FIXED:** robots `Allow: /api/v1/` ✓ · API mirror VTRS+OTLK Decided/Approved, CAPR Held 3-9 against ✓ · as_of now 2026-08-01 (ET) ✓ · /decisions date-descending + counter 131 ✓ · Event startDate time+TZ on calendar 40/40, readouts 81/81, adcomm 2/2 (readouts 150→81 = undatable demoted to WebPage) ✓ · VTRS page/board correct ✓.
**Accuracy verified vs primary sources:** CAPR 3-9 against ✓ (my 07-30 note saying "9-3" was MY error, site was right); REPL 10-3 favorable ✓.
**🔴 NEW #1 — REPL PDUFA 2026-08-02 MISSING ENTIRELY** (decides tomorrow; FDA goal date per Replimune 8-K). Site has REPL AdComm but no PDUFA row; homepage "next decision" wrongly opens at MRNA Aug 5. Fix + fix AdComm→PDUFA linkage so it can't recur.
**🔴 NEW #2 — 303 of 448 live decision pages MISSING from sitemap** (only 145 present; newest is 2026-06-26). All July decisions absent incl. VTRS/OTLK/OTSKY/MRK. Regenerate sitemap from live decisions archive w/ real lastmod.
**Still open (not started, multi-day):** B2 ticker orphans (/tickers = 404, links still home 1 / calendar 0 / decisions 0 / screener 0) · B3 /screener still 0 `<tr>` · B4 ticker ~179-209 words · B6 /research 2 + /developers 1 homepage anchors (no nofollow — crawlable, just thin equity) · B7 sitemap flat, lastmod still Jul 24.
**GSC unchanged (36 indexed / 522 not / 478 discovered)** — expected; report lags and the demand-side fixes (B2/B3/B4/B7) haven't shipped.
**Self-correction:** playbook claim "ticker pages emit no JSON-LD" was unverified and WRONG — they emit BreadcrumbList+ItemList+ListItem. B4 stands on word count only.

### 🚀 SEO PLAYBOOK 2026-08-01 — see `SEO_PLAYBOOK_2026-08-01_FOR_BUILDER.md`
**VTRS SHIPPED** ✓ (detail page 200, homepage decided leads VTRS, removed from upcoming). Two follow-ups: (A1) /decisions sorts VTRS *below* MNKD 07-24 + counter still 128 not 129; (A2) **API mirror still NOT shipped** — VTRS/OTLK "Awaiting", CAPR "Scheduled" (3rd recurrence); (A3) as_of future-dated 2026-08-02.
**THE NUMBER: 36 indexed vs 522 not indexed — 478 = "Discovered, currently not indexed" (never crawled).** Technical base is clean (robots OK, 520/520 sitemap URLs → 200, canonicals/308s correct, 1×h1, unique titles). Problem is **crawl demand, not discovery** — manual index requests can't fix 478.
Root causes found: (B1) **robots.txt `Disallow: /api/` blocks the very endpoints /llms.txt advertises to AI crawlers** → `Allow: /api/v1/` (5-min, highest leverage); (B2) **208 ticker pages = 40% of sitemap, ~0 internal links** (home 1, calendar/decisions/screener/condition 0) = orphaned, sitemap-only; (B3) **/screener JS-only — 0 `<tr>`, 0 links** in HTML, passes no equity; (B4) ticker pages ~190 words (vs decision 314, pdufa 504) = thin at scale; (B5) GSC "Events: 94% not eligible" (54+150+2 invalid, conferences 14 valid) = startDate time+TZ; (B6) /research "crawled not indexed" (last crawl Mar 30), /developers "discovered, never crawled, NO referring page"; (B7) sitemap lastmod stale Jul 24 + flat 520 → split into sitemap index for per-section measurement; (B8) authority program (Zenodo DOI, Wikipedia, dev repo, journalist pitch).
Measure weekly: "Discovered – not indexed" falling from 478, Indexed rising from 36.

### 🔴 Builder audit 2026-08-01 — see `AUDIT_2026-08-01_FOR_BUILDER.md`
- **P0: VTRS/Gwyn Lo STILL not deployed** 3 days post-approval — detail page 404, still in upcoming, /decisions counter still 128, API "Awaiting". Six prepared files pass 14/14 guards; just needs commit+push (clear stale .git/*.lock first). Don't regenerate board on clean checkout before committing or homepage dupes VTRS.
- **P0: API mirror** — back-fill OTLK + CAPR AdComm in dataset.mjs; make manual/AdComm publish write the API record in the same commit.
- **NEW SEO: /research = "crawled, not indexed"; /developers = "discovered, not indexed", never crawled, no referring page (orphaned)** — nav "API" link not counted; add server-rendered footer anchors + sitemap lastmod. Requested indexing for both today.
- **Schema: GSC says "Events: 94% not eligible"** — /calendar 54, /readouts 150 invalid → startDate time+TZ.
- **as_of anomaly:** API meta.as_of=2026-08-02 while today=Aug 1 (badge correct "Aug 1") — daily job stamping UTC-tomorrow; stamp from ET.
- **Sitemap lastmod** newest 2026-07-24 (stale).
- **Indexed round 3:** /research, /developers, /condition/cancer, /pricing, /methodology.

### 🟠 Audit 2026-07-31 — see `AUDIT_2026-07-31.md` (cache-busted live pages + live API)
- **VTRS/Gwyn Lo (approved 2026-07-29, primary-source verified):** publish prepared (data.js/dataset.mjs/decisions/detail page/calendar), 14/14 CI guards pass, builder deploying. At audit time NOT yet live (homepage still lists VTRS upcoming; /fda-decision/VTRS-2026-07-29 → 404). Land the deploy.
- **API lag now has 3 live examples:** `/api/v1/events` shows OTLK "Awaiting", CAPR AdComm "Scheduled", VTRS "Awaiting" — all wrong vs rendered site; MNKD/OTSKY/MRK correct. Manual/AdComm publishes update pages+decisions archive but NOT the API dataset. Fix = back-fill status/outcome/decision_date for OTLK + CAPR in the API dataset; make VTRS deploy carry its dataset.mjs change.
- **Schema still open:** /calendar 54 invalid, /readouts 150 invalid, /conferences 14 valid → PDUFA/readout startDate needs time+TZ (~204 items).
- **Sitemap** newest `<lastmod>` = 2026-07-24 (stale) — confirm daily sitemap regen runs.
- **Indexing this session (recrawl-requested, all indexed):** /decisions, /calendar, /conferences, /readouts, /screener.
- **Freshness badge now "Data through Jul 31" — current/correct** (07-30 concern resolved).

### 🟢 Indexing 2026-07-30 — 5 primary pages recrawl-requested (all indexed, confirmed queued)
`/` · `/research/conference-runup` · `/research/readout-reaction` · `/adcomm` · `/runup-by-year`. All returned "URL is on Google / indexed"; research pages have valid Breadcrumbs+Datasets. Recrawls pick up last week's decisions + CAPR AdComm.
**Event-schema invalidity spans PDUFA/readout/AdComm objects:** /calendar 55 · /readouts 150 · /adcomm 2 invalid; /conferences 14 VALID. Root = date-only `startDate` + VirtualLocation on the PDUFA/readout/AdComm emitter. Fix startDate time+TZ on that emitter → clears all. Conferences already pass.

## ⚠️✅ 2026-07-30 CORRECTED — the SITE is current & correct; the API FEED lags — see `AUDIT_2026-07-30.md`
**Owner correctly flagged my error.** I measured the site via `/api/v1/events` instead of the rendered pages. **The rendered site is CORRECT:** homepage + `/decisions` show **OTLK Approved 2026-07-24** (LYTENAVA) and `/decisions`+`/adcomm` reflect the **CAPR 9-3 AdComm against**. My "3 live errors" claim was FALSE — withdrawn.
**REAL bug (narrower) = API/page divergence** (same class as MNKD 07-25, still open):
- API returns OTLK `Awaiting/null` while page shows Approved 7/24.
- API returns CAPR AdComm `Scheduled` while page reflects the 9-3 vote.
- API `updated_at` mode = Jul 11 → the **"Data through" badge understates the site's real currency** (badge reads the stale API timestamps).
**Consequences:** `/llms.txt` points crawlers at the stale API; the freshness badge undersells the site. **Fix:** make `/api/v1/events` a faithful mirror — propagate outcome/decision_date/AdComm result + bump `updated_at` on change.
**⚠️ Also corrects my 07-21→07-27 audits:** the "day N / 84% frozen at Jul 11" numbers measured the API feed, NOT proof the rendered site is stale. The site's decision data is demonstrably current. I over-stated site staleness; the demonstrable problem is the API feed + badge.
**✅ Holding:** Lipfendra, MNKD, OTSKY, MRK, OTLK, CAPR all correct on the rendered site; fan-out 0, null names 0, sitemap 520 www-only.

## 2026-07-27 — Lipfendra ADDED ✅ / rebuild still not run 🔴 / SEO turning ✅ — see `AUDIT_2026-07-27.md`
- ✅ **Lipfendra fixed** (builder-prompt item #1): MRK, 2026-07-16, Approved, decision_date + FDA source all correct.
- 🔴 **Full rebuild NOT run** (items #2/#3): 326 rows still Jul 11 (day 16); badge still "Data through Jul 11". Automated daily rebuild + backfill + FDA reconciliation guard + CI freshness check remain the #1 asks. (Also: `Data through` badge is client-side only — server-render it.)
- ✅ **SEO turning the corner:** `/calendar` **now indexed** (canonical dup RESOLVED — the weeks-long blocker) · `/conferences` **now indexed** (was "unknown to Google") · `/decisions`,`/readouts`,`/screener` indexed · `/condition/cancer` gaining impressions. Recrawl requested this session on all 5 primary pages (they carry the new decisions).
- 🟠 **Event schema invalidity QUANTIFIED:** `/calendar` 55 invalid + `/readouts` 150 invalid Events; `/conferences` 14 VALID. → the **PDUFA/readout event objects** are the invalid ones (date-only startDate + VirtualLocation); conferences pass. Fix startDate time+TZ on the PDUFA/readout emitter → clears ~205 invalid items on the 2 top index pages. Real SERP cost (no date-chip rich results).
- ✅ No regressions (fan-out 0, null names 0, all Decided have outcome, sitemap 520 www-only).

## ~~🔴🔴 2026-07-26 — COVERAGE MISS: Lipfendra~~ (ADDED ✅) — see `AUDIT_2026-07-26b_LIPFENDRA_MISS.md`
**Owner-flagged. The site completely missed the first oral PCSK9 inhibitor** — Merck **Lipfendra (enlicitide decanoate, MK-0616)**, approved **2026-07-16**, biggest cardiology approval of the year. API search for pcsk9/cholesterol/ldl/enlicitide/mk-0616/lipfendra = **0 hits**. Not a wrong date — the event was NEVER ingested (no upcoming PDUFA, no decision). Proof that the frozen bulk refresh (326 rows @ Jul 11) is dropping real post-Jul-11 catalysts.
**Actions:** (1) manually add the record NOW (full verified data in the audit doc: MRK, Lipfendra, Approved 2026-07-16, Priority Review + CNPV, hypercholesterolemia/HeFH, NCT05952856). (2) **Backfill ALL decisions since Jul 11** — Lipfendra may not be the only miss. (3) Add `test_fda_reconcile.py` — cross-check decided archive vs FDA press-announcements RSS (30d), alert on any absent approval. **This is exhibit A for the bulk-refresh P0.**

## ✅ 2026-07-26 — API decision-capture P0s FIXED & VERIFIED — see `AUDIT_2026-07-26.md`
Both 07-25 P0s closed: MNKD now `outcome:Approved` + `decision_date:2026-07-24` + `days_to_decision:null`. OTSKY flipped stale-Upcoming → `Decided/Approved`. **0** Decided-without-outcome, **0** Decided-with-positive-days, **0** past-dated Upcoming. Both approvals independently verified (MNKD FUROSCIX + OTSKY SIMTRIYO/centanafadine both real FDA approvals). API now agrees with rendered pages.
**🔴 ONLY substantive item left: bulk refresh (day 15).** 326/387 rows still Jul 11 — daily job refreshes near-term+decided only, not the future-readout/late-2026 bulk. Badge honestly "Data through Jul 11." Point the working job at the full dataset (Polygon).
**🟡 Minors:** (1) Event `startDate` still date-only (no time+TZ) → likely the GSC "94% Events not eligible" driver; add TZ, recrawl. (2) Decided archive sorts by scheduled `date` not new `decision_date` — MNKD shows as "decided 7/26" (scheduled) vs actual 7/24; re-sort by decision_date.
**✅ No regressions:** fan-out 0, null names 0, sitemap 520 www-only.

## ~~🔴 API/PAGE DIVERGENCE 2026-07-25~~ (RESOLVED — see above) — `AUDIT_2026-07-25.md`
**Refresh partially ran** (60 rows fresh today, 326 still Jul 11 → badge still honestly "Data through Jul 11"). MannKind FUROSCIX **approved 7/24** (verified) and the **rendered site shows it correctly** ("MNKD 2026-07-24 ✓ Approved"). **But the API record is self-contradictory:**
- `status:"Decided"` yet **NO `outcome` field** — API can't tell Approved from CRL (site has it, serializer doesn't expose it). **Highest-value missing API field.**
- `date:"2026-07-26"` = scheduled PDUFA date, not the 7/24 decision date.
- `days_to_decision: 1` on a Decided event → "decided but +1 day to go" contradiction.
- **`/llms.txt` sends AI crawlers to this API** → they'd quote a future-dated, outcome-less record for an approved drug. Same class as the 07-19 readout-precision split.
- **Fix:** expose `outcome`+`decision_date`, recompute `days_to_decision`≤0 on Decided. Ship `test_decided_consistency.py` (in audit).

**🔴 Same root cause: OTSKY centanafadine** PDUFA 7/24 (past), refreshed today but still `status:Upcoming` — decision-capture step missed it. Only past-dated "Upcoming" PDUFA. Flip to Decided/Awaiting.

**🟠 Refresh still incomplete:** 326/387 rows Jul 11. Partial = progress; badge won't go green until full rebuild.

### ✅ Indexing batch 2026-07-25 — 8 submitted (confirmed queued)
`/ticker/ABBV`,`/AMGN`,`/REGN`,`/SRPT`,`/BNTX` · `/calendar/2026/december` · `/condition/cancer` · `/condition/rare-disease`.
**Skipped:** `/ticker/NVO` (GSC threw intermittent "Something went wrong / try again in a few hours" — daily inspection throttle after ~6 rapid requests). `/learn/what-is-a-pdufa-date` was **already indexed** (learn pages converting, valid Breadcrumbs).
**New indexed observed:** `/learn/what-is-a-pdufa-date` (indexed). GSC insight: `/decisions` now getting **MORE** impressions than usual (was −93% on /calendar last week — recovering). Clicks 42→**44**. Throttle note: cap indexing at ~5–6/session to avoid the "try again" wall.

## ✅/🔴 CURRENCY UPDATE 2026-07-23 PM (post-builder) — see `AUDIT_2026-07-23b.md`
**Honesty layer FIXED (well-built):** dropped false "~5×/day" claim → honest "snapshot, data-through date stated" · homepage prints **"Data through {date}"** using **MODE of updated_at (=Jul 11), not MAX** — so the 1 hand-added row can't inflate it (genuinely clever) · **live-dot goes amber >7d** ("badge can never overstate currency") · **centanafadine (OTSKY 7/24) hand-added** — tomorrow no longer a visible miss.
**🔴 STILL OPEN — the actual pipe:** 384/385 rows still `updated_at=2026-07-11`, latest Decided still 7/17. Badge honestly reads "Data through Jul 11" but that's **12-day-old data**. Honest-stale ≠ fresh. **#1 action on the whole board: make the snapshot rebuild run on a daily+ schedule (Polygon feed).** Everything else structural is done.
**🟡 CORRECTION (my error):** I overstated the Event-schema "94% invalid." Actual markup is coherent — `VirtualLocation`+`OnlineEventAttendanceMode` match, eventStatus/organizer/etc present. Only real gap: `startDate` date-only (no time+TZ). Run Rich Results Test, add time+TZ if flagged, let GSC recrawl. Lower priority than stated.
**✅ No regressions:** fan-out 0, null names 0, sitemap 520 www-only.

## ~~🔴🔴🔴 P0-CURRENCY — STILL DEAD 2026-07-23 (now 12 days)~~ (superseded by PM update above)
**Unaddressed since 07-19. `as_of=2026-07-23` but all 384 rows still `updated_at=2026-07-11`.** `/coverage` still claims "~5×/day." **Centanafadine PDUFA is TOMORROW (7/24) and absent** — the site is about to visibly miss a real FDA decision. This is now the ONLY thing between the site and its "most current" positioning; every other P0 is fixed. Min fix: manually backfill centanafadine + post-7/11 events, flip "Live"→"Updated Jul 11", ship `test_data_freshness.py`. Ideally revive cron off new Polygon feed.

## 🟠 NEW 2026-07-23 — Event schema is 94% INVALID (GSC flags it)
Homepage now emits `Event` schema (the 07-19 fix) BUT **GSC Recommendations: "Events: 94% of your items aren't eligible for rich results."** Likely `VirtualLocation` used for physical FDA decisions, or incomplete `startDate`/location/`eventStatus`. **Builder: GSC → Enhancements → Events → read exact error → fix required fields.** Rich-result eligibility = the only no-backlink SERP edge.

## ✅ SEO WORKING 2026-07-23 — sitemap fix is landing
`/ticker/MRNA` + `/ticker/VRTX` now **"URL is on Google" (indexed)** — were unindexed a week ago. Ticker hubs converting from www sitemap. Indexed 10 / not 350 (315 = Discovered-not-crawled). `/calendar` impressions −93% (canonical churn, should recover). Clicks 42→44.
**Requested this session (10, confirmed queued, skipped already-indexed MRNA/VRTX):** `/ticker/LLY`,`/PFE`,`/MRK`,`/GILD`,`/BMY` · `/calendar/2026/august`,`/september`,`/october`,`/november` · `/adcomm`.

## 🔴🔴🔴 P0-CURRENCY — data frozen 10 days, site claims "~5×/day" (2026-07-21) — see `AUDIT_2026-07-21.md`

**THE priority. Attacks the exact "most up-to-date source" positioning.**
- 100% of 384 API rows: `updated_at = 2026-07-11T15:23:27Z`. `as_of` says today. **The refresh cron is dead, silently** (waitlist-KV pattern again).
- `/coverage` claims *"refreshes ~5×/day via cron"* — **falsifiable in one API call.** Homepage says "Live" ×3.
- **Concrete miss:** Otsuka **centanafadine PDUFA Jul 24** (ADHD) — 3 days out, absent. Snapshot froze before it landed.
- **Fixes:** (1) find why cron died; (2) make "Live" badge a FUNCTION of `max(updated_at)` — flips to "Last updated Jul 11" if >48h, never a hardcoded string; (3) staleness alert >24h; (4) `tests/test_data_freshness.py` in `AUDIT_2026-07-21.md`; (5) backfill centanafadine.
- **This is the same fix as the Polygon migration** — point the refreshed price/mcap cron at Polygon Ultimate.

## 🟠 UW → POLYGON migration (UW key dies 2026-07-22)
- **Dies, no user-facing impact:** all `uw_*` MCP tools (flow_alerts, darkpool, congress, greek_exposure, net_prem_ticks, oi_change, options_volume, institutions). UW-proprietary, no Polygon equivalent. **Retire/stub them so they error loud, not silent.** Rotate dead key out of secrets.
- **Survives:** UOA overlay (runs on ORATS, not UW), ODIN/GUNGNIR/BIFROST (no live dep), public calendar.
- **Opportunity:** Polygon Ultimate = real-time stocks+options → (a) drives the dead price/mcap refresh, (b) likely replaces ORATS for UOA (drop $99/mo) — **A/B ORATS vs Polygon on 5 microcaps first**, Polygon may be thin on nano/micro chains. (c) can't replace GEX/congress/darkpool — none are in public product.
- **⚠️ Verify before cutover:** what "Massive" covers vs raw Polygon; **redistribution rights** if displaying Polygon prices publicly (same open Q as FMP/ORATS).

## ✅ ALL prior P0s CLEARED (verified 2026-07-21)
P0-A fan-out **GONE** (0 join artifacts, PDUFA 83→70) · null drug names **0** (268 filtered per `/coverage`) · P0-B precision fixed · P0-C prose fixed · P0-D 1,425 fixed · homepage schema shipped · `/api`→`/developers` · **non-www sitemap DELETED**, live sitemap 520 www-only.

## 🟡 Currency-adjacent still open
39 readouts in past est. windows not flipped to Overdue · ~80% API rows null mcap (Polygon fixes) · SEO now a waiting game — don't burn more indexing quota, let 7/21 batch land.

---

## 🔎 SEO ROOT CAUSE FOUND — 2026-07-21 (Search Console deep dive)

**The 350 not-indexed pages are ONE problem, not seven.** Breakdown from the Pages report:

| Reason | Pages | Read |
|---|---|---|
| **Discovered – currently not indexed** | **315 (90%)** | Google knows the URL, has **never crawled it**. |
| Redirect error | 17 | **16 are non-www Feb-2026 ghosts** (`/vnda-pdufa`, `/tools`, `/leaderboard`, `/q1-2026-oncology-pdufa-dates`…). Only 1 is current. |
| Crawled – not indexed | 6 | Quality signal. |
| Not found (404) | 5 | |
| Page with redirect | 4 | Expected (legacy → `/calendar`). |
| Alternate page w/ canonical | 2 | Expected. |
| Duplicate, Google chose different canonical | 1 | `/calendar` — see below. |

### 🔴 SEO-3 — A stale DUPLICATE non-www sitemap is still submitted
Search Console has **two** sitemaps:

| Sitemap | Submitted | Last read | Pages Google saw |
|---|---|---|---|
| `https://www.pdufa.bio/sitemap.xml` | Jul 18 2026 | Jul 18 2026 | **336** |
| **`https://pdufa.bio/sitemap.xml`** (non-www) | **Jun 25 2026** | **Jun 25 2026** | **170** |

The non-www sitemap is **feeding Google the Feb-era non-www URL set** — that is where the 16 non-www "Redirect error" ghosts come from. **🔧 OWNER ACTION: delete `https://pdufa.bio/sitemap.xml` from Search Console** (Sitemaps → ⋮ → Remove sitemap). Keep only the www one.

Also: Google's last read of the www sitemap found **336 URLs; the live file has 518.** Newer pages (`/methodology`, `/clinical-trial-success-rates`) inspect as **"No referring sitemaps detected"** — they're in the live file but not in Google's copy. ✅ Resubmitted 2026-07-21 to force a re-read.

### 🔴 SEO-4 — Google's internal link graph is anchored on a URL it can't fetch
Inspected 10 pages. **Nine show `Referring page: None detected`.** The one exception:

> `/screener` → **`Referring page: https://www.pdufa.bio/pdufa-calendar`**

`/pdufa-calendar` is the URL Google reports **"Page fetch: Failed — Redirect error"** on. **Google's map of this site's internal links is frozen at the pre-redirect structure, and the hub it thinks links to everything is a URL it can no longer fetch.** That is the mechanism behind all 315 "Discovered – not indexed": Google is discovering URLs from the sitemap only, with **zero internal-link signal and zero external backlinks**, so nothing earns crawl budget.

**This will not be fixed by requesting indexing.** Three things fix it:
1. **Delete the non-www sitemap** (above) — stops re-feeding dead URLs.
2. **Verify `/pdufa-calendar` returns a single clean 301/308** with no chain for Googlebot-smartphone. Once Google can follow it, the link equity and the link graph transfer to `/calendar`.
3. **Get external links.** 315 pages sitting uncrawled on a domain with **42 total clicks** is a site-authority problem. The research pages (`/research/conference-runup`, `/research/readout-reaction`) are the only genuinely linkable assets — they are original data no competitor has. Pitch those, not the calendar.

### ✅ Indexing requested 2026-07-21 (10 URLs, all confirmed queued)
`/readouts` · `/decisions` · `/research/readout-reaction` · `/fda-approval-rate` · `/clinical-trial-success-rates` · `/runup-by-year` · `/conferences` · `/coverage` · `/methodology` · `/screener`
**Working from the 7/18 batch:** `/research/readout-reaction` and `/coverage` are now **"URL is on Google"** (both were unindexed). `/research/readout-reaction` shows valid Breadcrumbs + Datasets. Requests do work — they're just 10/day against 315.

**Note:** `/conferences` — the main conference calendar — was **"unknown to Google," never crawled.**

---

## ✅ VERIFIED FIXED 2026-07-21 (builder shipped)

| Item | Status |
|---|---|
| **P0-B** API readout precision | ✅ **FIXED** — all 299 now `date_precision:"month"` + `date_month` field present. |
| **P0-C** research page contradictions | ✅ **FIXED** — prose now matches tables (−0.56 / −1.59 / −1.93 / +5.53); stats corrected to 6.2%. |
| **P0-D** "256 presentations" | ✅ **FIXED** — now reads 1,425. |
| Homepage schema | ✅ **SHIPPED** — `ItemList` + 7 `Event` + `Organization` + `VirtualLocation` (was `WebSite` only). |
| `/api` 404 | ✅ **FIXED** — now 308 → `/developers`. |
| `as_of` off-by-one | ✅ **FIXED** — now stamps today. |

### 🔴 P0-A — STILL OPEN, and now half-fixed in a way that hides it
`/pdufa/BNTX`, `/pdufa/CTMX`, `/pdufa/EVAX`, `/pdufa/MIRM` now **308-redirect and are out of the sitemap** — good. **But `/api/v1/events` still returns all three** on the 2026-08-17 Keytruda+Padcev row, still with `market_cap:null` and no `role` field. **The page is clean and the API is not.** Fix the join, don't just de-index the symptom. Still open: 10 null drug names · 40 past-dated events not flipped · `/watchlist` 404.

---

## 🔴🔴 NEW P0 — from `AUDIT_2026-07-19.md` (read that file for evidence)

| # | Item | One-line |
|---|---|---|
| **P0-A** | **Ticker fan-out — wrong companies on live FDA decisions** | 2026-08-17 Keytruda+Padcev listed under **BNTX, CTMX, EVAX** (none are parties; verified vs Merck/Pfizer PRs). Also **MIRM** on Incyte's zilurgisertib. Signature: bogus rows have `market_cap=null` + a different indication string → **joined on drug text, not sponsor.** Fix the join, ship `tests/test_no_ticker_fanout.py`, post to `/corrections`. |
| **P0-B** | **API fabricates day-precision on 299 readouts** | All 299 readouts sit on the **15th** and are tagged `date_precision:"day"`. The **page gets this right** ("Jun 2026 (est.)"); the **API contradicts it**. Set `date_precision:"month"`, add `date_month`. `/llms.txt` is live — LLMs are reading the wrong one. |
| **P0-C** | **`/research/conference-runup` contradicts itself 4×** | Table (correct, matches `conference_runup_FULL_v2.csv`) vs prose (stale): event-day −0.56 vs −0.63 · D+5 −1.59 vs −1.74 · D+10 −1.93 vs −2.00 · mean +5.53 vs +5.89. Summary stats also drift (6.5 vs 6.2 etc). **Regenerate every number from one dataframe.** Also: cap-tier table sums to 1,105 of 1,425 — **320 nulls undisclosed** on a page that promises every n. |
| **P0-D** | **`/conferences` says "256 presentations"; study says 1,425** | Stale promo copy. And only **2 of 14** conferences show any presenter — the restored 715-row/39-conference crawler output **is still unpublished**. Also "1 presenters" pluralisation bug. |

**New P1/P2 from same pass:** homepage has `WebSite` schema only (add `ItemList`+`Event` for next 10 — cheapest rich-result win) · 40 past-dated events not flipped to Overdue/Awaiting · `as_of` stamps **tomorrow** · 10 PDUFAs with **null drug name** · `/api` 404s while nav labels a link "API" · homepage "1,754 events" vs 1,425/1,752/5,285 elsewhere · RHHBY Giredestrant duplicated on 11-30 and 12-18 · 80% of API rows have null market cap.

**Note on `/calendar` canonical:** the three legacy URLs (`/pdufa-calendar`, `/pdufa-dates-2026`, `/biotech-catalyst-calendar`) are all **308 → `/calendar`** and correctly absent from the sitemap — they can never index and that's fine. The canonical competitor is **the homepage**, which is a near-identical PDUFA calendar. Differentiate `/` (tape/dashboard) from `/calendar` (by-month index).

**✅ Closed this pass:** stale ODIN title on `/calendar` is **gone** · `/changelog` now 200 · sitemap 546 URLs 100% www · conference CSV truncation still fixed · redirect topology clean (no loops) · decided-archive accuracy verified.

---

### ✅ SEO-2 — Indexing requested for 10 priority URLs (2026-07-18)
Submitted via Search Console URL Inspection → Request Indexing (all "added to priority crawl queue"):
`/` · `/calendar` · `/pdufa-calendar` · `/pdufa-dates-2026` · `/biotech-catalyst-calendar` · `/research/conference-runup` · `/research/readout-reaction` · `/ticker/MNKD` · `/ticker/MRNA` · `/ticker/VRTX`.
**GSC snapshot at submission: 10 indexed / 350 not indexed.** Re-check in 3–7 days.

**🔴 What the inspections REVEALED — a real crawl blocker, hand to builder:**
- **`/pdufa-calendar` → "Page fetch: Failed: Redirect error"** (last crawl Jul 10). Google **cannot follow the redirect to `/calendar`**, which is *why* the stale ODIN titles persist — it can't re-fetch to refresh them. **Verify the redirect chain is a single clean 301 (no loop, no chain, no relative-path bounce).** `curl -IL` shows 301→200, but Googlebot-smartphone is erroring — likely a redirect *chain* or a redirect that only fires for some user-agents.
- **`/calendar` → "Duplicate, Google chose different canonical than user."** Google is picking one of the old `pdufa-*`/`biotech-*` URLs as canonical instead of `/calendar`. **Fix:** the redirecting URLs must 301 (not canonical-tag) to `/calendar`, and `/calendar` must be self-canonical. Once the redirect error (above) clears, this resolves.
- **`/pdufa-dates-2026`, `/research/readout-reaction`, all 3 ticker hubs → "URL is unknown to Google" (Last crawl N/A)** — never crawled. The indexing requests fix this; they were structurally undiscovered.
- ✅ **`/research/conference-runup` is already indexed with valid `Breadcrumbs` + `Datasets` schema** — the research pages' structured data works.

### 🔴 SEO-1 (STILL THE #1 SEO PROBLEM) — Google's index is stale + off-brand
`site:pdufa.bio` today returns **only 5 URLs**, and every one carries the OLD title:
- *"…& **ODIN Scores** | PDUFA.BIO"* · *"…with **AI Approval Scores**"* · *"Biotech Catalyst **Intelligence**"*
- AI summary quotes: *"**ODIN v1108** predicts FDA approval probability… 54+ weighted signals"*, *"tracks **375+** catalysts with **ODIN AI approval scores**"*, *"**TIER_1 predictions have a 93.6% approval rate**."*

**✅ Live site is clean** — all 5 URLs 301 → `/calendar`, correct titles, no ODIN, footer says "no individual-drug approval probabilities." **This is 100% stale index.**

**Why it still hurts:** (1) it advertises **approval probabilities** — the one thing the brand refuses to sell; (2) **93.6% = the leaked ODIN v14 metric** (HO AUC 0.9363) repeated as an "approval rate" — off-brand *and* from a model the MCP flags KNOWN LEAKED; (3) **none of the 210 new ticker hubs or the research pages are indexed yet** — Google is showing 5 stale pages while 540 fresh ones wait.

**Action (owner just re-submitted the sitemap ✅ — now finish it):**
1. Search Console → **Request Indexing** on `/`, `/calendar`, and each stale `pdufa-*`/`biotech-*` URL (forces title refresh).
2. Submit a **priority sample of ticker hubs** (top-20 by search volume: MNKD, MRNA, VRTX, LLY, PFE…) for indexing — don't wait for the natural crawl on 210 new URLs.
3. **CI assert:** no public `<title>`/meta may contain `ODIN|AI score|approval prob|TIER_1|v1108`. (Prevents regression + signals the brand to crawlers.)
4. Consider a one-line `<meta name="robots" content="…">` unchanged, but add **`Last-Modified` headers** so Google re-crawls the changed titles faster.

### 🟠 SEO-1 — Google's index is still serving the OLD "ODIN Scores" titles
Google currently shows, for live URLs:
- *"PDUFA Calendar 2026: Upcoming FDA Drug Approval Dates & **ODIN Scores** | PDUFA.BIO"*
- *"PDUFA Dates 2026: Complete FDA Calendar with **AI Approval Scores** | PDUFA.BIO"*
- *"PDUFA.BIO — FDA PDUFA Calendar & Biotech Catalyst **Intelligence**"*

and an AI summary quoting: *"**ODIN v1108** … predicts FDA approval probability by analyzing 54+ weighted regulatory signals"* and *"**ODIN TIER_1 predictions have a 93.6% approval rate.**"*

**✅ The live site is clean — I verified all three URLs 301 → `/calendar`, with correct titles, no ODIN, and the footer's "no individual-drug approval probabilities."** This is **stale index**, not a live defect.

**But it is actively costing us,** because:
1. It advertises **approval probabilities** — the exact thing `/why-no-approval-probability` promises we never do. Anyone Googling us sees us contradicting our own brand.
2. **"93.6%" is the leaked ODIN v14 metric** (HO AUC 0.9363) being repeated as an "approval rate." It is both off-brand *and* sourced from a model the MCP itself flags as **KNOWN LEAKED**.
3. It's the first impression for every branded search.

**Action:** Search Console → **Request indexing** for `/`, `/calendar`, `/pdufa-calendar`, `/pdufa-dates-2026`, `/biotech-catalyst-calendar` + the 3 research pages. Confirm the 301s return `200` at the target (they do). Add a CI assert that no public `<title>`/meta ever contains `ODIN|AI score|approval probability|TIER_1`.

---

## ✅ CONFIRMED DONE — verified live 2026-07-13, do not revisit

| Area | Status |
|---|---|
| **Data freshness** | ✅ **Verified independently.** CELC shows `2026-07-14 ✓ Approved REVTORPYK (gedatolisib)` — the FDA approved it **July 14, three days ahead of the July 17 PDUFA**, and the site already reflects it. Calendar is genuinely current. |
| **Legacy ODIN URLs** | ✅ `/pdufa-calendar`, `/pdufa-dates-2026`, `/biotech-catalyst-calendar` all **301 → `/calendar`**, clean titles, no ODIN in live HTML |
| **Routes** | `/` `/calendar` `/conferences` `/adcomm` `/readouts` `/screener` `/developers` `/research` + **3 research pages** · `/about` · `/corrections` · `/llms.txt` · **`/glossary`** · `/account` · `/login` · `/pricing` · `/pricing/credits` · `/decisions/crl` — **all 200** |
| **Sitemap** | **338 URLs, 100% www** ✅ (the "170/non-www" reports were my stale cache — builder was right) |
| **Fabricated conferences** | ✅ **0 fabricated · 0 duplicates · 0 ANE** in current crawler output |
| **Unified panel dupes** | ✅ **202 → 0** (5,285 rows) |
| **Homepage responsive bug** | ✅ **FIXED** — `navddm` mobile nav now present on `/`; overflow gone |
| **Payments** | ✅ Correctly locked — checkout redirects to `/pricing?soon=1`, not Stripe. "Coming soon" + waitlist live |
| **Waitlist** | ✅ Persist-only to KV; the silent-lead-loss path now returns **503** instead of a false "you're on the list"; PII no longer logged |
| **API** | ✅ Anonymous works, **no locked fields**, headers + usage endpoint correct |
| **Research pages** | ✅ Full `Dataset` + `Article` + `BreadcrumbList` + `FAQPage` schema |
| **Conference Overlay v1.0** | ✅ RETIRED — `conference_score` returns a refutation notice |
| **`prior_crl` boolean (leak)** | ✅ Dropped; absent from ODIN v19's features |
| **Phase success-rate table** | ✅ Not published; cites Wong/Siah/Lo instead |
| **openFDA "77% CMC"** | ✅ Not published |
| **Crawler `ConferencePresentation` type** | ✅ Built; coverage 15 → **40** conferences |
| **CI guards** | ✅ 4 live: `test_seo_invariants` · `test_originality` · `api_contract` (49) · `billing_contract` (21) |

---

# 🔴 P0 — DATA INTEGRITY. Nothing publishes until these are green.

### P0-0 — ✅ **RESOLVED — the CSV truncation is fixed.**
*(Verified 2026-07-18.)* Canonical `conference_presentations_history.csv` is back to **715 rows / 39 conferences**; the bad file was renamed `.truncated_224`; and a **`.prev.csv` baseline now exists — the coverage-regression guard shipped.** Nothing else in this section applies anymore. Original writeup kept below for history.

<details><summary>original P0-0 (resolved)</summary>

The corrupt file now parses **because it was cut off at the break point, not because the escaping was fixed.**

| File | rows | tickers | **conferences** | date range |
|---|---|---|---|---|
| **`conference_presentations_history.csv`** (canonical, 07-13 15:47) | **224** | 117 | **11** | 2022-05-26 → 2026-12-12 |
| `...pre_rebuild_20260712_160021.csv` (backup, 07-12 23:00) | **715** | 240 | **39** | 2021-10-07 → 2026-12-12 |

- Canonical is a **strict subset** — overlap **224/224**. The backup holds **491 rows the canonical lost**.
- **The corruption was at row 225. The file is now exactly 224 rows.** That is truncation.
- **28 of 39 conferences gone.** This silently **undoes the entire 15 → 40 conference expansion** — EASL, ASGCT, EULAR, ATS, ASCO-GI, ASCO-GU, the CNS block (CTAD/AAIC/ECTRIMS/ADPD), AAAAI, ENDO, AAO, AAD, ARVO all vanished.
- ✅ **Not published** — the live API still serves 14 clean conference events. Caught in time.

**Fix:**
1. **Restore `conference_presentations_history.pre_rebuild_20260712_160021.csv`** — 715 rows, 39 conferences, and it passes every check: **fab=0 · dup=0 · ANE=0 · null tickers=0.** It is both clean *and* complete.
2. Re-apply the quote fix properly: `csv.QUOTE_ALL` + sanitise `snippet` (strip newlines, normalise quotes) **before** writing. Never truncate.
3. **Ship the coverage-regression guard** — a data fix destroyed two-thirds of the dataset and nothing caught it:
```python
# tests/test_crawler_no_regression.py — block deploy
import pandas as pd, sys
new  = pd.read_csv('catalysts_out/conference_presentations_history.csv')
prev = pd.read_csv('catalysts_out/conference_presentations_history.prev.csv')
errs = []
if len(new) < len(prev) * 0.95:
    errs.append(f'FATAL: row count collapsed {len(prev)} -> {len(new)}')
lost = set(prev['conference']) - set(new['conference'])
if lost:
    errs.append(f'FATAL: lost {len(lost)} conferences: {sorted(lost)[:12]}')
if new['ticker'].nunique() < prev['ticker'].nunique() * 0.95:
    errs.append('FATAL: ticker coverage collapsed')
if errs: print('\n'.join(errs)); sys.exit(1)
print(f'OK — {len(new)} rows, {new.conference.nunique()} conferences, no regression.')
```
> **Rule: data can be corrected, never silently reduced.** A crawl returning fewer rows or fewer conferences than the previous run must fail the build.

</details>

### P0-1 — ✅ **RESOLVED** (see P0-0)

---

## 🆕 NEW THIS PASS — small UX/SEO polish

### UX-1 — 🟡 Ticker-hub meta description has a **leading-space glitch**
`/ticker/CELC` renders `"…catalyst hub: 0 upcoming PDUFA/decision page(s)…"` and the char-count string shows `( 169` — a stray leading space from string concatenation. Cosmetic, but it's in **210 indexable descriptions**. One-line template fix (`.strip()` / trim the join).

### UX-2 — ✅ Data freshness is genuinely excellent — verified independently
- **CELC** shows `2026-07-14 ✓ Approved REVTORPYK (gedatolisib)`. FDA/Celcuity 8-K confirm approval **July 14, three days AHEAD of the July 17 PDUFA.** The site caught an early approval, and its ticker hub correctly reads **"0 upcoming"** as a result — that's not a bug, that's current data.
- Homepage/calendar clustering view, weekly cap-tier stacking, Q4-only estimates all present and dated. `catalysts_public.csv` mtime 07-12, spans to 2028.
- **No stale/wrong dates found in spot-checks** (CELC, MNKD, OTLK, MRNA, RARE, BBIO all reconcile).

### UX-3 — 🟡 Ticker-hub long-tail not yet winning (indexation, not quality)
`"MNKD PDUFA date catalysts"` → Timothy Sykes, Pharmaconomics, StockTitan, StocksToTrade. **pdufa.bio absent** — because the hub isn't indexed yet, not because it's weak (it's strong: aggregates both MNKD catalysts + past decision). **This resolves once SEO-1 indexing lands.** The hubs are the right build; they just need to get crawled.

---
```
catalysts_out/conference_presentations_history.csv
→ pandas: "EOF inside string starting at row 225"
→ header = 18 fields; row 226 = 11 fields
→ cannot be parsed AT ALL, even with on_bad_lines='skip'
```
**Cause:** the crawler writes the raw `snippet` (press-release text) into CSV **without escaping quotes**. One `"` inside a snippet breaks the file from that row to EOF.

**This is the file downstream consumers read.** Anything importing it crashes or silently truncates.

**Fix:**
- Write with `csv.QUOTE_ALL` (or `df.to_csv(..., quoting=csv.QUOTE_ALL)`), and **strip newlines + normalise quotes in `snippet` before writing**.
- **CI guard:** after every crawl, re-read the output with a strict CSV parser and assert `rows == expected`. A file that can't round-trip must fail the build.

### P0-2 — **Fabrication guard is still not shipped**
Current rebuild files:

| file | rows | fabricated | dupes | ANE |
|---|---|---|---|---|
| `...pre_rebuild_...160021.csv` | 715 | **0** ✅ | 0 | 0 |
| `...pre_rebuild_...15xxxx.csv` | 1,089 | **5** 🔴 | **90** | 3 |
| `..._FRESH.csv` | 980 | **5** 🔴 | 32 | 3 |

The 5 phantom events persist: **AUTL/COGT → ASH 2026, CRBP → ESMO, CTMX → SITC, CELC → SABCS** — all extracted from **2025** source text.

**Mechanism:** the crawler resolves a conference name to that conference's *next* occurrence, ignoring the year stated in the source.

**Rules to enforce:**
1. **A stated year always wins.** If the snippet contains a year earlier than the occurrence being assigned → historical. Never emit a future date.
2. **Past-tense verbs are disqualifying** (`presented`, `were presented`, `reported`) — cannot produce a future event.
3. **Require an affirmative future cue** (`will present`, `to present`, `scheduled to`) before any future date.
4. **Never fall back to a conference start date.** Unresolvable year → `date_basis=unresolved`, dropped from the public feed.
5. **Dedupe** on `(ticker, date, conference)`.

CI guard code is in `CRAWLER_REDTEAM_2026-07-12.md`.

> ⚠️ **`/llms.txt` is LIVE.** The site's conference API currently serves 14 clean events, so nothing false is public *yet*. **The guard must land before the next conference publish** — or phantoms get laundered into ChatGPT/Perplexity answers at scale, where you cannot claw them back.

### P0-3 — 🛑 **DO NOT rebuild `/research/conference-runup` from the EDGAR crawler**
**Measured presenter recall (new):**

| | AACR 2026 | AAN 2026 |
|---|---|---|
| Ground truth | 43 | 7 |
| **Recall** | **53.5%** | 71.4% |

| | recall |
|---|---|
| under $2B | **57%** |
| **over $2B** | **38%** |

**Missed:** RHHBY ($319B) · MRK ($304B) · JAZZ ($12B) · IDYA · ZLAB.
**Cause is structural:** a poster is *material* to a $200M biotech (8-K filed); *immaterial* to Merck (no filing). **EDGAR cannot see it.**

**The published study is 49.2% large-cap.** Rebuilding on a source with 38% large-cap recall **strips out half the large-caps and re-weights toward micro/small — the widest-dispersion cohort. The headline would move for sampling reasons, not real ones.**

> **Rule: never change the sampling frame and the published number in the same step.** If the universe changes, publish old and new side by side, with the recall figure, and say why they differ.

**Fix:** multi-source — EDGAR **+ press releases** (`fmp_press` is *already* a source in `catalysts_public.csv`) **+ ASCO/AACR abstract databases** (the only true ground truth). Then publish the recall number per conference and cap tier.

### P0-4 — **CLAUDE.md mandates a leaked model** *(owner action)*
Live MCP: `odin_score` → *"**LEGACY ODIN v14 — KNOWN LEAKED**, inflated ~368bp"*. `odin_score_v19` → *"**CURRENT CHAMPION**, honest test AUC **0.8934**"*.
CLAUDE.md still says *"ODIN v14 is the ONLY PDUFA scoring model. Never fall back."*
**Replace the ODIN block with v19-PRUNE and mark v14 KNOWN LEAKED — DO NOT USE.**

### P0-5 — **ODIN retrain on capped `prior_crl_count`**
`prior_crl_count` is a **running counter** (values ≥9 → 18 distinct values, one event each; max 26 = company-level). Std inflated **151%** → an event with 1 prior CRL is z-scored **0.364** when its true value is **1.084**. **The CRL signal is compressed to a third of true magnitude.**
Capped CSV exists (`..._crlcap4.csv`) — **but coefficients were fit on uncapped data, so capping the file changes nothing deployed. This needs a retrain.**

---

# 🟠 P1 — Correctness & the biggest growth lever

### P1-1 — **Dedupe the unified panel** — **202 duplicate rows** on `(ticker, date, catalyst_type)` in `conf_study/UNIFIED_catalyst_panel.csv`.

### P1-2 — **Cap the short-interest display**
**19% of SI rows have days-to-cover > 100.** Legitimate for illiquid nano-caps, **absurd on a page**: *"Short interest: 4,200 days to cover"* destroys credibility.
→ Display cap: `>60d` renders as **"very illiquid"**. Never show a raw DTC above ~30 without context. Always print the **settlement date**.

### P1-3 — ⭐ **`/ticker/{TICKER}` hubs** — still **404**. **The biggest SEO item left.**
Still absent from top 10 for the head term; you will not out-authority BiopharmaWatch/BPIQ/MarketBeat head-on this year. **The tail is the only winnable path.** ~400 pages from data you own — every PDUFA + readout + conference + AdComm + past decision + run-up + cash runway per company. Near-zero competition ("MNKD catalysts").
Your event pages already link to `/calendar`, `/conferences`, `/condition/*` — **the one link they can't make is to a ticker hub, because it doesn't exist.** That's the missing spine of the internal-link graph.
Also ship `/drug/{name}` (separate intent pool).

### P1-4 — **Rebuild BIFROST SI features** from `conf_study/si_panel_2017_2026.csv.gz`
Current features are **lookahead-biased** (one Apr-2026 snapshot smeared across 2020–26). T-1-compliant panel exists (3.63M rows, min lag 1 day). **This also makes `explosion_score` unusable** — SI/float are its top features.

### P1-5 — **SI-at-catalyst on event pages** — *"Short interest into this PDUFA: 6.2 days to cover (settlement 2026-06-30)."* Pure fact, nobody shows it. (Respect P1-2's display cap.)

---

# 🟡 P2 — Publish & polish

- **P2-1 — CRL tracker**, reframed as *"What happens after a CRL"*. Lead with the unbiased comeback table: **73.5% → 42.9% → 26.9%**. Do not use the openFDA reason-mix without stating the survivorship bias on the page.
- **P2-2 — Publish the market-cap null.** Trial design, enrollment size and short interest **all dissolve** under a cap-tier control; micro-caps move **8.71%** vs **2.19%** for large. Same shape as the SI debunk you already shipped. *Publish the null.*
- **P2-3 — `/glossary`, `/changelog`, `/watchlist`** — all 404. Extend the `/learn/what-is-a-crl` pattern.
- **P2-4 — Real-device mobile QA** — still never verified on an actual phone.
- **P2-5 — Owner actions:** Stripe credit price IDs (`STRIPE_PRICE_CREDITS_25K/_100K/_300K`) · `RESEND_API_KEY`. Both moot until Pro launches; neither blocks the waitlist.
- **P2-6 — Confirm FMP/ORATS redistribution terms** — derived stats OK; raw vendor data through the API is not.

---

# 📁 Data files (all in `conf_study/`)
| File | What |
|---|---|
| `UNIFIED_catalyst_panel.csv` | **5,487 events**, 3 catalyst classes, 2015–2026 *(202 dupes — see P1-1)* |
| `conference_runup_FULL_v2.csv` | 1,425 conference events, 2017–2026 |
| `readout_MASTER_enriched.csv` | 1,752 readouts × 88 cols — CT.gov design + FINRA SI + reaction |
| `si_panel_2017_2026.csv.gz` | 3.63M-row FINRA SI panel, 47,243 tickers, **zero lookahead** |

# 📚 Key audit docs
`STRESS_TEST_2026-07-12.md` (recall + panel stress tests) · `CRAWLER_REDTEAM_2026-07-12.md` (fabrication + CI guard) · `AUDIT_2026-07-12_POST_BUILDER_RESPONSE.md` · `VALIDATED_FINDINGS_AND_BUILDER_FIXES.md` (literature validation)

---

## ⚖️ The rules
1. **No scores, win rates, probabilities, sizing or entry/exit.** Median + IQR + **n** only.
2. **If it's visible on a public page, it's free in the API.**
3. **Nothing with `redistribute=False` ever ships.**
4. **Publish our own limitations on the page.** It's the differentiator no competitor will copy.
5. **Never publish a number we can't defend against the literature.**
6. 🆕 **Never change the sampling frame and the published number in the same step.**
7. 🆕 **Data integrity outranks presentation.** A page that renders perfectly and shows a conference that never happens is worse than a page with a layout bug.

---
*Facts and historical statistics only. Not investment advice.*
