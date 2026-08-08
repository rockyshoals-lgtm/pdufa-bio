# pdufa.bio — Verification audit — 2026-08-02 (02:0x UTC / Aug 1 evening ET)
**Freshness proof:** every page below was fetched with `Cache-Control: no-cache` + a nanosecond cache-buster and returned **`x-vercel-cache: MISS`, `age: 0`** — these are origin responses, not CDN cache. Server `date: Sun, 02 Aug 2026 02:05:15 GMT`.
*Facts and historical statistics only — not investment advice.*

---

# ✅ CONFIRMED FIXED — 6 of 6 items I raised are verified corrected

| # | Item | Verified state |
|---|---|---|
| **B1** | robots.txt blocked the API `/llms.txt` advertises | **FIXED** — `Allow: /api/v1/` now precedes `Disallow: /api/`. Correct precedence; AI crawlers can now reach the endpoints `/llms.txt` names. |
| **A2** | API mirror lagged the pages (3rd recurrence) | **FIXED** — all three now correct: `VTRS Decided/Approved dcd=2026-07-29` · `OTLK Decided/Approved dcd=2026-07-24` · `CAPR Held / "3-9 against"`. All stamped `updated_at 2026-08-02`. |
| **A3** | `meta.as_of` future-dated (2026-08-02) | **FIXED** — now `as_of: 2026-08-01`, correctly ET-based rather than UTC-rollover. |
| **A1** | `/decisions` sort + year counter | **FIXED** — order is now strictly date-descending (VTRS 07-29 → MNKD/OTLK/OTSKY 07-24 → MRK 07-16 …), counter now reads **131**. |
| **B5** | Event schema: "94% of items not eligible" | **FIXED** — `/calendar` 40/40, `/readouts` 81/81, `/adcomm` 2/2 `startDate` now carry time + timezone (e.g. `2026-07-30T00:00:00-04:00`). Zero date-only remain on those pages. `/readouts` Event count also dropped 150 → 81, consistent with demoting undatable rows to `WebPage` as suggested. |
| — | VTRS/Gwyn Lo publish | **FIXED & correct** — detail page 200, homepage board leads with it, removed from upcoming, `/decisions` row correct. |

**Accuracy spot-check (independent, primary source):**
- CAPR CTGTAC, Jul 29: FDA committee voted **3 for / 9 against / 0 abstain**. Site renders "voted 3–9 against" — **correct**. *(Correction to my own AUDIT_2026-07-30, which described this as "9-3" — the site was right and my note was wrong.)*
- REPL CTGTAC, Jul 30: voted **10–3 favorable**. Site renders "voted 10–3 favorable" — **correct**.

---

# 🔴 NEW — 1. REPL's PDUFA (Aug 2, 2026) is missing entirely — that's tomorrow
Replimune's RP1 + nivolumab has an **FDA goal date of August 2, 2026**, confirmed in Replimune's own 8-K/press release following the Jul 30 AdComm.

Current state:
- `/adcomm` correctly shows the **REPL AdComm** (Jul 30, 10–3 favorable) ✓
- But there is **no REPL PDUFA record anywhere** — API returns exactly 1 REPL row (`adcomm_repl_2026-07-30`), and the only PDUFA in the Aug 1–10 window is MRNA 08-05.
- Homepage "Next FDA decisions" therefore opens with **MRNA · Aug 5** — skipping the nearest decision.

**Impact:** the single most time-sensitive item on the site is absent on the eve of the decision, and a visitor asking "what's the next FDA decision?" gets the wrong answer. It also means tomorrow's outcome won't have a record to attach to.
**Fix:** add `pdufa_repl_2026-08-02` (RP1/vusolimogene oderparepvec + nivolumab, advanced melanoma, post-anti-PD-1) to the slate + dataset now, and link the AdComm record to it. Worth checking *why* it was missed: the AdComm was captured but the associated PDUFA wasn't — if the AdComm ingest doesn't also create/confirm the PDUFA row, the same gap will recur for every AdComm'd drug.

---

# 🔴 NEW — 2. 303 of 448 live decision pages are missing from the sitemap
`/decisions` links **448** `/fda-decision/*` pages. The sitemap contains only **145** of them. **303 are absent — including every July 2026 decision:**
`VTRS-2026-07-29` · `OTLK-2026-07-24` · `OTSKY-2026-07-24` · `MRK-2026-07-16` … and 299 more back through 2025.

The newest `/fda-decision/` URL in the sitemap is dated **2026-06-26**, i.e. the sitemap's decision section hasn't been regenerated since roughly late June.

**Why this matters more than it looks:** these pages *are* internally linked from `/decisions`, so they're discoverable by crawl — but they're your highest-value, most-linkable, freshest content, and they're invisible to the one file Google uses to prioritise recrawl. This is very likely a contributor to the 478 "Discovered – currently not indexed."
**Fix:** regenerate the sitemap from the live decisions archive on every deploy (not from a stale static list), with a real per-URL `lastmod`.

---

# 🟠 STILL OPEN — the structural SEO items (multi-day work, not yet started)

| # | Item | Verified current state |
|---|---|---|
| **B7** | Sitemap freshness & structure | Still **flat** (no sitemap index), **521 URLs**, newest `<lastmod>` still **2026-07-24**. New VTRS page not included (see above). |
| **B2** | Ticker pages orphaned | Unchanged: internal links to `/ticker/*` — homepage **1**, `/calendar` **0**, `/decisions` **0**, `/screener` **0**. `/tickers` A–Z hub → **404** (not built yet). |
| **B3** | `/screener` invisible to Googlebot | Unchanged: **0 `<tr>`**, only 15 links, zero links to ticker/pdufa/decision pages. Still client-rendered. |
| **B4** | Thin ticker pages | Unchanged: VTRS 190 words · MRNA 209 · CAPR 195 · ZYME 179. |
| **B6** | `/research`, `/developers` under-linked | Unchanged: homepage → `/research` **2** anchors, → `/developers` **1**. Both `rel` clean (no nofollow), so they are crawlable — just thin on internal equity. No `/tickers`, `/corrections`, or `/about` link from the homepage at all. |

**Correction to my own playbook:** in `SEO_PLAYBOOK_2026-08-01` I wrote that ticker pages "currently emit none" for JSON-LD. That was an assertion I hadn't actually measured. Verified now: `/ticker/*` **do** emit `BreadcrumbList` + `ItemList` + `ListItem`. The B4 recommendation stands on word-count depth alone; disregard the JSON-LD claim.

---

# 📊 Search Console — unchanged, and that's expected
| | Pages |
|---|---:|
| Indexed | **36** |
| Not indexed | **522** |
| ↳ Discovered – currently not indexed | **478** |
| ↳ Redirect error | 18 |
| ↳ Crawled – currently not indexed | 13 |
| ↳ Page with redirect | 6 |
| ↳ Not found (404) | 5 |

Identical to yesterday. **This is not evidence the fixes failed** — GSC's index report lags by days to weeks, and the fixes that would move this number (B2/B3/B4/B7 — internal linking, server-rendered screener, page depth, sitemap) are precisely the ones not yet shipped. The items that *were* shipped (robots, schema, API mirror, sort order) affect crawler *access* and *rich-result eligibility*, not crawl demand, so a flat indexed count at this point is the expected reading.

Re-check weekly. The number that matters is **"Discovered – currently not indexed" falling from 478**.

---

# 🟡 Minor
- `/adcomm` groups both entries under the heading **"Scheduled meetings"**, but both have already been held and carry vote results. Consider splitting "Upcoming" vs "Recent results" so the heading doesn't contradict the rows.
- `/conferences` `startDate` remains date-only (14/14). **Leave as-is** — GSC already reports these 14 as *valid*, and date-only is correct modelling for multi-day conferences. Flagging only so it isn't "fixed" by mistake.

---

# Recommended order
1. 🔴 **Add REPL PDUFA 2026-08-02 today** — it decides tomorrow. Then fix the AdComm→PDUFA linkage so this can't recur.
2. 🔴 **Regenerate the sitemap from live data** — recovers 303 missing decision pages + current `lastmod`. Cheap, and directly targets the 478.
3. 🟠 **`/tickers` hub + server-rendered `/screener` rows** (B2/B3) — the main structural attack on "Discovered, not indexed."
4. 🟠 **Thicken ticker pages; `noindex` empty ones** (B4).
5. 🟠 **Sitemap index split by type** (B7) so you can measure §3–4 per section in GSC.
6. 🟢 Authority program (playbook §B8) — the durable lever.

**Bottom line:** everything I flagged has been fixed, and verified fixed against origin — robots/API/schema/sort/timestamps are all clean now, and the two AdComm vote figures check out against primary sources. The two new items are both *coverage* rather than correctness: a missing near-term PDUFA (REPL, tomorrow) and a sitemap that stopped including new decision pages in late June. Neither is a regression from this work; both look like pipeline gaps that predate it.

---
*Verify every date and outcome against primary FDA / SEC / company filings. Not investment advice.*

**Sources**
- Capricor CTGTAC vote (3 for / 9 against / 0 abstain), Jul 29 2026 — [AJMC](https://www.ajmc.com/view/fda-advisory-panel-votes-against-approval-of-deramiocel-for-dmd) · [BioSpace](https://www.biospace.com/fda/fda-advisers-vote-against-approval-of-capricors-dmd-therapy-in-chaotic-adcomm-meeting) · [FDA CTGTAC meeting page](https://www.fda.gov/advisory-committees/advisory-committee-calendar/cellular-tissue-and-gene-therapies-advisory-committee-july-29-2026-meeting-announcement-updated)
- Replimune RP1 CTGTAC vote (10–3 favorable) + **FDA goal date Aug 2 2026** — [Replimune 8-K exhibit (SEC)](https://www.sec.gov/Archives/edgar/data/0001737953/000110465926088857/tm2621708d1_ex99-1.htm) · [Replimune press release](https://www.globenewswire.com/news-release/2026/07/30/3336537/0/en/replimune-announces-favorable-outcome-of-fda-s-cellular-tissue-and-gene-therapies-advisory-committee-meeting-for-rp1-in-advanced-melanoma.html)
