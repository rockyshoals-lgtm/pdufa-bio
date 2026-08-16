# Audit — 2026-08-11
**Cowork session · Amendment 033 filing**
*Live origin verification + API integrity checks. ⚠️ Chrome extension down — no SERP or console reads this round (§4).*
*Facts and historical statistics only — not investment advice.*

---

# 1. ✅ EVERYTHING FROM YESTERDAY'S OPEN LIST IS FIXED

| Item | Yesterday | **Today** |
|---|---|---|
| `/drug/miplyffa` (the only unclaimed 100%-CTR query) | 404 | ✅ **200** |
| `/drug/arimoclomol` (generic name) | 404 | ✅ **308** → miplyffa |
| `/drug/aasld-the` (conference name as drug) | 200 | ✅ **404** removed |
| `/drug/acr-convergence` (conference name as drug) | 200 | ✅ **404** removed |
| `dateModified` format inconsistency | mixed date-only / full-ISO | ✅ **full ISO-8601 + offset everywhere** |

`/drug/monalizumab`, `/drug/deramiocel` and `/drug/mk-6240` all now carry `2026-08-11T13:05:55+00:00`. Clean.

Site currency is good: API `as_of 2026-08-11`, 418 events.

---

# 2. 🔴 NEW — `/pdufa/{TICKER}` is one URL serving multiple events, and it resolves to the *past* one

**The nearest catalyst on the whole site is affected.**

`/pdufa/LNTH` **308-redirects to `/fda-decision/LNTH-2026-06-26`** — a Complete Response Letter for **LNTH-2501 (Gallium-68 edotreotide)**, decided in June.

But Lantheus has an **upcoming PDUFA in 2 days — Aug 13, for MK-6240**, an entirely different drug. And in the API, *all three* LNTH records — the June CRL, the Aug 13 upcoming PDUFA, and a 2027 readout — carry the **same** `url` field: `https://www.pdufa.bio/pdufa/LNTH`.

So anyone following the canonical link for the Aug 13 decision lands on an unrelated CRL for a different molecule, two days before the event.

## Scope: 6 tickers, ordered by urgency

| Ticker | Upcoming | Decided (what `/pdufa/{T}` actually shows) |
|---|---|---|
| **LNTH** | **T-2** · Aug 13 · MK-6240 | Jun 29 · **CRL** · LNTH-2501 (Ga-68 edotreotide) |
| IONS | T-42 · Sep 22 · Zilganersen (ION373) | Jun 30 · Approved · Olezarsen (CORE) |
| VTRS | T-67 · Oct 17 · MR-141 | Jul 30 · Approved · MR-100A-01 (Gwyn Lo) |
| GSK | T-76 · Oct 26 · Bepirovirsen (B-Well) | Jun 18 · Approved · Tebipenem HBr |
| AZN | T-142 · Dec 31 · Ultomiris | Jun 30 · Approved · Truqap |
| ARQT | T-196 · Feb 23 2027 · ZORYVE cream **0.05%** | Jun 29 · Approved · ZORYVE cream **0.3%** |

ARQT is the subtlest and most dangerous: same brand, different strength. A reader could easily conclude the 0.05% cream is already approved when only the 0.3% is.

## Why this matters
- **Wrong-event landing on the most time-sensitive page you have.** T-2 is exactly when search and click volume peak.
- **34 `/pdufa/{T}` URLs currently serve more than one event.** Six of those mix an upcoming catalyst with a decided one; the rest mix upcoming with estimated readouts. One URL cannot be the canonical for several distinct events.
- **It contradicts the site's own accuracy posture.** The archive carefully separates verified from unverified, then points a live catalyst at the wrong drug.
- **SEO:** multiple events competing for one URL is precisely the "duplicate/consolidated canonical" pattern that dilutes ranking signal, and it wastes the entity work done on drug pages.

## Fix
Give every PDUFA event its own canonical URL, the way decisions already do:
```
/pdufa/LNTH-2026-08-13      ← upcoming MK-6240
/fda-decision/LNTH-2026-06-26   ← already correct
/pdufa/LNTH                 ← ticker hub listing all LNTH events, no redirect
```
Then set each API record's `url` to its own event page. `/pdufa/{T}` should behave like `/ticker/{T}` — an index, not a redirect to whichever event happens to be first.

**Minimum fix before Thursday:** point `pdufa_lnth_2026-08-13` at a page describing the Aug 13 MK-6240 decision, not the June CRL.

---

# 3. 🟡 STILL OPEN

- **`/drug/dtx401` and `/drug/pariglasgene-brecaparvovec` → 404.** That's **Ultragenyx, PDUFA Aug 23 (T-12)** — flagged yesterday, still missing. Both names should exist; the search spike comes in the next ten days.
- **Drug pages still thin** (230–255 words) — unchanged.
- `/compare/` pages — 404, expected, explainer shipped first.
- `/calendar` and `/decisions` `dateModified` still read **Aug 8** while drug pages read Aug 11. If those hubs genuinely haven't changed since the 8th that's correct discipline; if their content *has* changed (countdowns, new rows) the stamp is stale. Worth confirming which.

---

# 4. ⚠️ NOT VERIFIED THIS ROUND — Chrome down

The extension was unreachable across repeated retries, so I could **not** check:
1. **Whether the Bing #1 held** (we took #1 for "fda calendar 2026 pdufa dates" on Aug 10, up from #3)
2. **Bing impressions** — yesterday's 108 IndexNow submissions + the #1 ranking should be landing in BWT around now; last read was 187/day
3. **AI citations** — last read 8 citations / 3 pages
4. **GSC** — whether the Redirect-error validation completed and whether 418 "Discovered" finally moved

Those four are the whole scoreboard right now, and all of them are pending. Worth a look the moment the extension reconnects.

---

# 5. PRIORITY

| # | Action | Why |
|---|---|---|
| 1 | **Point the Aug 13 LNTH record at its own event page** | T-2. Wrong-drug landing at peak traffic. |
| 2 | **Build `/drug/dtx401` + `/drug/pariglasgene-brecaparvovec`** | Ultragenyx PDUFA T-12; second day flagged |
| 3 | **Give every PDUFA event its own URL; make `/pdufa/{T}` an index** | Fixes all 6 collisions + 34 multi-event URLs structurally |
| 4 | Confirm `/calendar` + `/decisions` dateModified reflects real content change | Freshness signal integrity |
| 5 | Read both consoles when Chrome is back | The scoreboard |
| 6 | ⚠️ Migrate `bing_rank_report.py` off legacy API | **Aug 31 deadline — 20 days** |

---

# BOTTOM LINE

Yesterday's punch-list is fully cleared — miplyffa is live, the two fake "drugs" are gone, and `dateModified` is consistent sitewide. That's a clean sweep.

The new finding is more structural than anything in the last few audits: **`/pdufa/{TICKER}` is a single URL standing in for multiple distinct events, and it currently resolves to the past one.** For Lantheus that means the canonical link for a decision two days away points at a June CRL for a different molecule. Six tickers are affected today, ARQT most subtly (same brand, different strength). Decisions already get one URL per event — PDUFAs need the same treatment, and LNTH needs it before Thursday.

---
*Verify every date and outcome against primary FDA / SEC / company filings. Not investment advice.*
