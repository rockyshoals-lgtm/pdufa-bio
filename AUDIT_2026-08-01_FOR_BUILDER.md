# pdufa.bio — Audit for the builder — 2026-08-01
*Method: live rendered pages (cache-busted), live `/api/v1/events`, Google Search Console URL Inspection, and primary sources. Not investment advice.*

This is a build/deploy punch-list, ordered by impact. Items 1–2 are correctness; 3–4 are SEO growth; 5–6 are hygiene.

---

## 1. 🔴 P0 — VTRS / Gwyn Lo approval is prepared but STILL not deployed (3 days stale)
FDA approved **Viatris Gwyn Lo** (norelgestromin/ethinyl estradiol transdermal patch) on **2026-07-29** (505(b)(2); Phase 3 Luminous = NCT05139121). Source: Viatris/PRNewswire, Jul 29 2026.

The publish was fully prepared in the working tree and **passes all 14/14 CI guards**, but as of today it is NOT live:
- `https://www.pdufa.bio/fda-decision/VTRS-2026-07-29` → **404**
- Homepage still lists **VTRS in _upcoming_**; "Recently decided" still leads MNKD/OTLK
- `/decisions` still leads MNKD 07-24 (counter still 128, not 129)
- `/api/v1/events` → VTRS `status:"Awaiting", outcome:null`

**Prepared, guard-passing edits waiting to ship (working tree):**
`pdufa_site_src/api/data.js` (forward MR-100A-01 removed) · `pdufa_site_src/api/v1/dataset.mjs` (VTRS→Decided/Approved, oc+dcd, FDA url) · `pdufa_site_src/decisions/index.html` (VTRS row + counter→129) · `pdufa_site_src/fda-decision/VTRS-2026-07-29/index.html` (new detail page) · `pdufa_site_src/calendar/index.html` (VTRS row marked Approved) · `pdufa_site_src/index.html` (board regenerated).

**Action:** commit + push these six files (Vercel auto-deploys). Note there were stale `.git/*.lock` files blocking a local commit on 07-30 — if they persist, clear `.git/index.lock`, `.git/HEAD.lock`, `.git/refs/heads/main.lock` first. **Do NOT run a fresh `build_home_board.py` on a clean checkout before committing these** — the board reads the decisions archive + slate, so the decisions-page row and the removed slate entry must land in the same commit or the homepage will show VTRS twice (once upcoming, once decided) or not at all.

---

## 2. 🔴 P0 — `/api/v1/events` mirror lags the pages for manual/AdComm publishes
Live API vs the (correct) rendered site, fresh origin read:

| Event | Rendered site | `/api/v1/events` |
|---|---|---|
| OTLK LYTENAVA | Approved 07-24 | `status:"Awaiting", outcome:null` |
| CAPR Deramiocel AdComm | Held 07-29, voted against | `status:"Scheduled", outcome:null` (upd 07-11) |
| VTRS Gwyn Lo | Approved 07-29 (pending deploy) | `status:"Awaiting", outcome:null` |
| MNKD / OTSKY / MRK | Approved | ✅ correct (`Decided/Approved`) |

**Diagnosis:** decisions published through the standard pipeline (which writes `dataset.mjs`) mirror correctly; decisions published via the manual/AdComm path update the page + decisions archive but **not** the API dataset. `/llms.txt` points ChatGPT/Perplexity/Gemini at this API, so they read stale "awaiting" for approved drugs.
**Action:** (a) back-fill `status/outcome/decision_date` (+bump `updated_at`) for **OTLK** and the **CAPR AdComm** in `dataset.mjs`; (b) make the manual/AdComm publish step write the API record in the same commit it writes the page (single source of truth). VTRS's dataset.mjs edit is already staged in item 1.

---

## 3. 🟠 SEO — two hub pages are not indexed (found via URL Inspection today)
- **`/research`** → "Crawled – currently not indexed" (last crawl Mar 30 2026; fetch OK, indexing allowed — Google simply didn't select it).
- **`/developers`** → "Discovered – currently not indexed", **never crawled** (Last crawl N/A), and **"Referring page: None detected"** — i.e. effectively orphaned. The nav "API" link isn't being counted as an internal link (likely JS-rendered/`nofollow`, so Googlebot isn't following it).

**Action:** (a) add real, server-rendered `<a href>` internal links to both `/research` and `/developers` from high-authority pages (homepage footer + /about already links /research; add /developers to the footer as a plain anchor, not JS). (b) Confirm both carry `<lastmod>` in sitemap.xml. (c) I've requested indexing for both today, but the durable fix is internal linking — a page Google won't crawl on its own needs link equity, not just a manual nudge.

---

## 4. 🟠 SEO — Event schema: 94% of Event items invalid
GSC Overview states verbatim: **"Events: 94% of your items aren't eligible for rich results."** Per-page: `/calendar` **54 invalid**, `/readouts` **150 invalid**, `/conferences` **14 valid** (conference events are fine).
**Root:** PDUFA/readout Event objects emit a **date-only `startDate`** + `VirtualLocation`. **Action:** emit `startDate` with a time + timezone (e.g. `2026-08-17T00:00:00-04:00`), or demote undatable rows to `WebPage`. Clears ~204 items and unlocks date-chip rich results on the two biggest hub pages.

---

## 5. 🟡 Data-stamp anomaly — API `as_of` is a day ahead of the calendar
Today is 2026-08-01; homepage badge reads "Data through Aug 1" (correct) but `/api/v1/events` `meta.as_of` = **2026-08-02**. Looks like the daily job is stamping `as_of` from a UTC "tomorrow" rollover (job runs 12:00/21:00 UTC).
**Action:** stamp `as_of` from the same clock/timezone the badge uses (America/New_York) so the API and the page agree and don't advertise future-dated data.

---

## 6. 🟡 Sitemap freshness
`/sitemap.xml` newest `<lastmod>` = **2026-07-24** — several days stale. If the daily rebuild is supposed to bump lastmod on changed URLs, it isn't reflecting in the served sitemap.
**Action:** confirm the sitemap regeneration step runs in the daily job and that changed pages (decisions, calendar) get a current `<lastmod>` so recrawls see fresh signals.

---

## Indexing requested this session (all confirmed queued)
Round 3 today: `/research` (was: crawled-not-indexed), `/developers` (was: discovered-not-indexed), `/condition/cancer` (indexed; gaining impressions per GSC), `/pricing`, `/methodology`.
Earlier: `/`, `/decisions`, `/calendar`, `/conferences`, `/readouts`, `/screener`, `/adcomm`, `/runup-by-year`, `/research/conference-runup`, `/research/readout-reaction`.

## Build order
1. Ship VTRS (item 1) + back-fill API for OTLK/CAPR (item 2) — one decision-integrity push.
2. Fix Event `startDate` time+TZ (item 4) — unblocks 94% of Event items.
3. Internal-link + sitemap `/research` and `/developers` (item 3).
4. Fix `as_of` timezone (item 5) + confirm sitemap `lastmod` regen (item 6).

*Facts and historical statistics only. Not investment advice. Verify every date/outcome against primary FDA/SEC/company filings.*
Source: Viatris — "Viatris Receives U.S. FDA Approval for Gwyn Lo, a Once-Weekly Contraceptive Patch" (Jul 29 2026), https://newsroom.viatris.com/2026-07-29-Viatris-Receives-U-S-FDA-Approval-for-Gwyn-Lo-TM-,-a-Once-Weekly-Contraceptive-Patch
