# Search position analysis — Bing, Google, and what to do next
**2026-08-18 · measured against the live site tonight**
*Facts and historical statistics only — not investment advice.*

---

# 0. WHAT I CAN AND CANNOT SEE

**Chrome isn't connected**, so I could not read Search Console or Bing Webmaster Tools. My last hard rank/click numbers are from **Aug 10–12** and are six to eight days stale:

| Metric | Last measured | Date |
|---|---|---|
| Bing rank, "fda calendar 2026 pdufa dates" | **#1** | Aug 10 |
| Bing clicks / impressions | 18 / 776 over 3 days | Aug 8–10 |
| AI citations | 115 in 3 days (8 → 35 → 72) | Aug 12 |
| Grounding queries citing us | 1 — "rusfertide pdufa date", 16.67% share | Aug 12 |
| Google | **55 indexed / 418 "discovered, not indexed"** | Aug 12 |
| Google 90-day | 38 clicks / 1,610 impressions | Aug 12 |

**I'm not going to guess at what those are now.** What I *can* measure precisely is the input side — and that has changed a lot.

---

# 1. THE INPUT SIDE: measured tonight

## 1.1 Crawlable surface

| | Aug 8 | Aug 12 | **Aug 18** |
|---|---:|---:|---:|
| URLs in sitemap | 787 | 1,076 | **1,267** |

Sections: drug 544 · fda-decision 334 · ticker 156 · pdufa 96 · **patent-cliff 40** · readouts 20 · conference 14 · calendar 12 · learn 9 · condition 9 · research 6

**+61% in ten days.** I pushed all 1,045 changed URLs to IndexNow tonight — HTTP 200 on both endpoints.

## 1.2 Citation surface — the leading indicator, now measured not estimated

I sampled every page type rather than assuming:

| Page type | Pages | Q/page (sampled) | Answerable questions |
|---|---:|---:|---:|
| drug | 544 | 4.5 | **≈2,450** |
| ticker | 156 | 4.0 | 624 |
| fda-decision | 334 | ~0.9 (9/10 carry one) | ≈300 |
| pdufa | 96 | 3.0 | 288 |
| patent-cliff | 40 | ~2.0 | ≈80 |
| calendar | 12 | 3.0 | 36 |
| hubs (10) | 10 | ~3.5 | 35 |
| learn | 9 | 2.0 | 18 |
| glossary | 1 | **12** | 12 |
| **conference** | **14** | **0** | **0** ⚠️ |
| **Total** | ~1,216 | | **≈3,840** |

**Baseline on Aug 8 was ~620** (310 drug pages × 2 questions, zero on hubs).

**The citation surface has grown roughly 6× in ten days.** That is the mechanism that produced 115 AI citations in 3 days from a standing start, and it has been multiplied since.

---

# 2. 🔴 THE STRATEGIC POINT NOBODY HAS NAMED

**Bing and Google now need opposite strategies, and doing more of what works on Bing may actively hurt on Google.**

On Aug 12 Google had **55 indexed out of 1,076 — about 5%** — with **418 sitting in "Discovered, currently not indexed."** We have since added ~190 more pages.

"Discovered, currently not indexed" is not a technical fault. It is Google saying: *we found these and decided they weren't worth the crawl budget.* Crawl budget is allocated by **site authority**, not by page count.

So:

| | Bing | Google |
|---|---|---|
| What's working | content velocity + IndexNow push | nothing yet |
| Constraint | none — it rewards freshness and structure | **authority / external trust** |
| Right move | **keep shipping pages** | **stop shipping pages; earn citations** |

**Adding a 41st patent-cliff page does nothing for Google.** Adding one credible external citation might unlock hundreds.

---

# 3. RECOMMENDATIONS, RANKED BY EXPECTED EFFECT

## 3.1 🟢 Cheapest win available — conference pages have zero FAQ
14 pages titled *"Biotech Presenters & Dates"* with **`FAQPage=0, Question=0`**. Every other page type on the site carries one.

Add 3–4 each: *"When is ASH 2026?"* · *"Which companies are presenting at ESMO 2026?"* · *"Where is SITC 2026 being held?"* — all answerable from data already on the page, all real queries with seasonal spikes.

**~50 new answerable questions for an afternoon's work.**

## 3.2 🟢 Triple the decision archive's surface — 334 pages at 1 question each
9 of 10 decision pages carry exactly **one** question. They're the highest-intent pages we own (*"was X approved"*), and 286 of them now link a primary source.

Go from 1 → 3:
- *"Was [drug] approved?"* (exists)
- *"Why did [drug] get a CRL?"* — where the source says
- *"What happened to [ticker] stock after the decision?"* — we have the measured move

**334 → ~1,000 answerable questions**, on pages that already rank and already carry citations.

## 3.3 🟠 Close the Google measurement blind spot — open since Aug 8
`ping_search_engines.py` still reports:

> *"Google Search Console: **NOT CONFIGURED**. This is the only real channel to Google; the old ping URL is gone."*

Without the service account there is **no programmatic sitemap submission and no visibility into Google at all**. Ten days of Google strategy has been guesswork. Setup is documented in `SETUP_GSC_SERVICE_ACCOUNT.md`.

## 3.4 🟠 The Google unlock is external citations, not more pages
The asset is already built and nobody's using it as an asset: **a free, CC-licensed FDA decision archive where 286 of 458 records link a primary source, and the sourcing rate is published.** That is genuinely citable material.

Concrete targets, in order of realism:
- **Wikipedia** — FDA approval articles routinely need a citation for decision dates. Our decision pages carry the primary source alongside. This is the single highest-authority link available and it's earned, not bought.
- **Biotech newsletters** (Endpoints, STAT, Fierce) — offer the patent-cliff dataset as a free reference; 427 drugs with LOE dates is a story they run annually.
- **`r/biotech`, `r/biotechplays`** — answer date questions with the sourced page, not a pitch.
- **Google Dataset Search** — `Dataset` schema is already on `/research` and `/developers`. Confirm it's being picked up; that's an uncontested surface in this category.

## 3.5 🟡 Per-event PDUFA URLs — still 404
96 `/pdufa/{TICKER}` pages currently collapse multiple events. Splitting to `/pdufa/{TICKER}-{date}` roughly doubles that section **and** matters more than it looks: **AI engines cite specific URLs.** One URL representing three events caps what can be cited.

## 3.6 🟡 Protect the Bing #1
The four-week hold on `/calendar`'s URL, canonical, title, H1 and opening paragraph started Aug 12. **Don't touch it until ~Sept 9.** Everything above is additive or on other pages, deliberately.

---

# 4. THE ONE THING I'D FIX FIRST

Not on this list, because it's an accuracy issue rather than a growth one, but it interacts:

**`/calendar` publishes 73 while the API returns 68 — and that number is in `FAQPage` schema.** We are feeding an AI-citable number that our own API contradicts, on the page that holds our #1 ranking. Growth work that drives more engines to quote that page increases the cost of the error.

Root cause from tonight's audit: the page builds from `data.js`, the API serves `dataset.mjs`, and nothing reconciles them.

---

# 5. SUMMARY

**Bing:** the strategy is working and the inputs have compounded — sitemap +61%, citation surface ~6× in ten days. Keep shipping, keep IndexNow automated, don't touch `/calendar` until September.

**Google:** 5% indexation is an authority problem, and it is the one problem more content cannot solve. The next move is external citations and closing the GSC blind spot — not a 41st page.

**Cheapest wins:** conference-page FAQs (~50 questions, an afternoon) and decision-page FAQs 1 → 3 (~700 questions, a day). Both use data already on the page.

---
*Rank and click figures above are from Aug 10–12 and need a console read to refresh. Not investment advice.*
