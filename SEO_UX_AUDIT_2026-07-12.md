# SEO + UX Audit
**Date:** 2026-07-12 · Live, hard cache-bypass (`cache:'reload'` + bust) · *Crawler & conference overlay excluded per instruction.*

---

# 🔴 THE HEADLINE: the homepage is the only page that isn't responsive — and it's breaking mobile usability

## Root cause (precise, one-line fix territory)
**The homepage never got migrated to the shared responsive header.** Every other page has the mobile nav component; the homepage doesn't.

| Page | mobile nav (`navddm`) present? | Horizontal overflow @485px |
|---|---|---|
| **`/` (homepage)** | ❌ **NO** | 🔴 **220px overflow** |
| `/calendar` | ✅ yes | ✅ 0px |
| `/pdufa/CELC` | ✅ yes | ✅ 0px |

## What it does
| Viewport | scrollWidth | clientWidth | **Overflow** |
|---|---|---|---|
| 929px (small laptop / split screen) | 995 | 914 | **81px** |
| 485px (phone) | 705 | 485 | **220px (45%)** |

- **Culprit element:** `<aside class="panel">` — the *"Recently Decided"* sidebar. It doesn't stack; it just hangs off the right edge.
- **Nav:** 11 flat links, **no hamburger**, header balloons to **130px tall** at mobile (vs 67px on `/calendar`).
- **Tap targets:** **41 of 60** interactive elements under 44px at mobile.

## Why this is an SEO problem, not just a cosmetic one
Google indexes **mobile-first**. The mobile rendering of your homepage *is* what gets crawled and ranked. Horizontal overflow trips Google's **"Content wider than screen"** mobile-usability failure — on your **highest-authority page**, the one that receives brand searches and passes PageRank to everything else.

You are fighting for "PDUFA calendar" while your front door doesn't fit on a phone.

**Fix:** point the homepage at the same header/layout component `/calendar` and `/pdufa/*` already use, and make the `aside.panel` stack below the main column under ~900px. Then add `overflow-x: hidden` as a belt-and-braces guard, and a CI check:
```js
// tests/test_no_horizontal_overflow.mjs — block deploy
for (const path of ['/','/calendar','/pdufa/CELC','/readouts','/screener','/research/readout-reaction']) {
  await page.setViewport({width: 390, height: 844});
  await page.goto(BASE + path);
  const overflow = await page.evaluate(() =>
    document.documentElement.scrollWidth - document.documentElement.clientWidth);
  if (overflow > 0) throw new Error(`FATAL: ${path} overflows by ${overflow}px at 390w`);
}
```

---

# 🔴 SECOND: `/ticker/{TICKER}` hubs still don't exist — the biggest SEO win left

```
/ticker/CELC   → 404
/ticker/MNKD   → 404
/drug/gedatolisib → 404
```

This remains **the highest-ROI SEO item on the board** and it hasn't moved.

**Why it matters more now than it did:** you're still **absent from the top 10** for "PDUFA calendar 2026 FDA decision dates" (BiopharmaWatch ×2, BPIQ, FDA Tracker, Assyro, MarketBeat, TipRanks, RTTNews, Dan Sfera, CheckRare own it). You will not out-authority those domains head-on this year.

**The tail is winnable and it's sitting there unused.** ~400 pages — one per company — aggregating every PDUFA + readout + conference + AdComm + past decision + run-up + cash runway for that ticker. That's exactly what retail types: *"MNKD catalysts", "CELC PDUFA date"*. Near-zero competition.

**Your event pages are already well-linked** — `/pdufa/CELC` links out to `/calendar`, `/conferences`, `/condition/cancer`, `/calendar/2026/july`. The one link it *can't* make is to a ticker hub, because there isn't one. That's the missing spine of the internal-link graph.

---

# 🟠 THIRD: three cheap pages still missing

| Route | Status | Why it matters |
|---|---|---|
| **`/about`** | 404 | **E-E-A-T gap.** A finance-adjacent site with no named entity behind it. Google needs to know who you are. Cheapest credibility win available. |
| **`/llms.txt`** | 404 | AEO. Retail increasingly asks ChatGPT/Perplexity *"what FDA decisions are coming?"* Your free, clean API makes you the easiest source to quote — nobody in this category is playing here. |
| **`/glossary`** | 404 | Informational long-tail + internal-link spine. `/learn/what-is-a-crl` is live and correctly schema'd — extend the pattern. |

Also still absent: `/corrections`, `/changelog` — and **you now have a genuinely great corrections story to tell** (the 68%-flat stat you refused to publish, the retired Conference Overlay, the ret_1d bug report you rejected). That page would write itself and no competitor would ever publish one.

---

# ✅ WHAT'S GOOD — and it's a lot

## Sitemap is healthy and growing
**334 URLs, 100% www.** Notable growth since last pass:

| Section | Count | |
|---|---|---|
| `/fda-decision/*` | **146** | ⬆ was 20 |
| `/pdufa/*` | **100** | ⬆ was 86 |
| `/conference/*` | **14** | 🆕 per-conference pages |
| `/research/*` | 5 | all schema'd |
| `/adcomm/*` | 3 | 🆕 |
| `/learn/*`, `/condition/*`, `/calendar/*` | 8 / 8 / 11 | healthy |

## Everything else checks out
- **All research pages** carry `Dataset` + `Article` + `BreadcrumbList` + `FAQPage`.
- **`/account`** — surfaces API key + usage/quota ✅
- **`/login`** — email field + graceful support fallback ✅
- **`/screener`** — filters working ✅
- **Event pages** — strong internal linking to month/condition/conference hubs ✅
- **Pro "coming soon"** — payments correctly disabled, waitlist capturing ✅

---

# Ranked actions

| # | Item | Impact | Effort |
|---|---|---|---|
| **1** | **Fix the homepage responsive bug** — migrate it to the shared header; stack `aside.panel` under ~900px; add the CI overflow guard | 🔴 **H** — mobile-first indexing, your top page | **L** |
| **2** | **44px tap targets** (41/60 failing at mobile) | 🟠 M | L |
| **3** | **`/ticker/{TICKER}` hubs** (+ `/drug/{name}`) | 🔴 **H** — the only winnable SEO path this year | M |
| **4** | **`/about`** — E-E-A-T | 🟠 M | **L** |
| **5** | **`/corrections` + `/changelog`** — you've earned this one | 🟠 M | L |
| **6** | **`/llms.txt`** — AEO land-grab | 🟠 M | L |
| **7** | `/glossary` — extend the `/learn` pattern | 🟡 L | L |

**Do #1 today.** It's a layout swap on one page, it's your most-crawled URL, and it's currently failing the single check Google applies to every mobile page.

---
*Not investment advice.*
