# Crawler Red-Team + Re-Audit
**Date:** 2026-07-12 · *Scoped: crawler + data integrity. Homepage overflow / ticker hubs / tap targets excluded — builder is on them.*

---

# 0. The correction stands. I was wrong to scope the crawler out.

You're right, and it's the more important lesson of this whole engagement:

> **A page that renders perfectly on mobile and shows a conference that never happens is worse than a page with an overflow bug.**

I accepted "don't worry about the crawler this pass" and went looking at layout. **The layout bug costs you a ranking signal. The fabrication bug costs you the entire brand** — because "most accurate calendar" is the only thing pdufa.bio actually sells. I should have pushed back on the scoping. Noted permanently: **data integrity outranks presentation, always.**

---

# 1. ✅ The crawler fix is real — and the `date_basis` column is the right instinct

`conference_presentations_history_FRESH.csv` — **980 rows, 2022-03 → 2026-12**:

| | |
|---|---|
| `catalyst_type` | **100% `ConferencePresentation`** ← P2-1 shipped |
| `source` | **100% `sec_edgar`** ← original, redistributable, no competitor data |
| `date_basis` | **observed 885 / projected 95** ← the exact distinction that was missing |
| `pres_type` | unspecified 710 · poster 94 · oral 86 · **late-breaking 80** · plenary 10 ← *presentation type is finally captured* |
| conferences | 42 distinct — ASCO 156, AACR 135, ESMO 92, ASH 73, SITC 51, EHA 43 |
| null tickers | **0** ✅ |

**And the projected rows are now clean:** 95 projected, **0 dated in the future**, 0 orphaned in the past. The 74-of-121 problem you found is fixed.

---

# 2. 🔴 BUT — there's residual fabrication, and it's a *different* mechanism

**5 future-dated events are fabricated.** They're marked `date_basis = observed` — so they slipped past the projected-row fix.

## The mechanism
**The crawler resolves a conference name to that conference's *next* occurrence, ignoring the year stated in the source text.**

A 2025 presentation described in the past tense becomes a **2026 event that will never happen.**

| Ticker | Assigned date | Conf | Year in source text | Snippet |
|---|---|---|---|---|
| **COGT** | **2026-12-12** | ASH | **2025** | *"…**In December 2025, presented** full data…"* |
| **CELC** | **2026-12-08** | SABCS | **2025** | *"…results **were presented at the 202**[5]…"* |
| **CTMX** | **2026-11-04** | SITC | **2025** | *"…**were presented at the 202**[5]…"* |
| **CRBP** | **2026-10-23** | ESMO | **2025** | *"…Reports Q4 and **2025** Financial Results… **Presented data at ESMO**…"* |
| **AUTL** | **2026-12-12** | ASH | **2025** | *"…**presented** initial data…"* |

**COGT is the smoking gun:** the source literally says *"In December 2025, presented"* — and the crawler emitted **December 2026**.

**CRBP is the most embarrassing:** it's a **Q4 2025 earnings release** recapping a past ESMO presentation, turned into an upcoming ESMO 2026 catalyst.

## The fallback-date fingerprint
Future-dated rows cluster on canonical 2026 conference start dates:
```
2026-10-23 ×6   (ESMO 2026 start)
2026-12-12 ×5   (ASH 2026 start)
2026-11-06 ×4   (SITC 2026)
```
That's not a coincidence — it's the conference-name→next-occurrence lookup firing on historical mentions.

## ✅ Caught before it shipped
Live check: `/conferences` and `/api/v1/events?type=Conference` (14 events) contain **none** of these five. **The fabrication is in the crawler output, not on the site.** That's the ideal outcome — and it's the whole argument for red-teaming the pipeline, not the page.

---

# 3. The fix (precise)

1. **A stated year always wins.** Parse years from the snippet. If the text contains a year *earlier* than the conference occurrence you're about to assign → **it's historical. Never emit a future date.**
2. **Past-tense verbs are disqualifying.** `presented · were presented · reported · showed · demonstrated` → **cannot** produce a future-dated event.
3. **Require an affirmative future cue** before emitting any future date: `will present · to present · scheduled to · plans to present · upcoming`.
4. **Never use a conference start date as a fallback.** If the year is unresolvable, mark `date_basis=unresolved` and **drop it from the public feed**.
5. **Dedupe** — currently **63 rows across 25 duplicate groups** on `(ticker, date, conference)`.

## CI guard (blocks deploy)
```python
# tests/test_no_fabricated_events.py
import pandas as pd, re, sys
PAST = r'\b(presented|were presented|reported|showed|demonstrated)\b'
FUT  = r'\b(will present|to present|scheduled to|plans to present|upcoming)\b'
d = pd.read_csv('catalysts_out/conference_presentations_history_FRESH.csv')
d['catalyst_date'] = pd.to_datetime(d['catalyst_date'], errors='coerce')
today = pd.Timestamp.today().normalize()
errs = []
fut = d[d['catalyst_date'] > today]
for _, r in fut.iterrows():
    s = str(r['snippet']).lower()
    yrs = [int(y) for y in re.findall(r'\b(20[12]\d)\b', s)]
    if yrs and max(yrs) < r['catalyst_date'].year:
        errs.append(f"FABRICATED: {r['ticker']} {r['catalyst_date'].date()} — source says {max(yrs)}")
    if re.search(PAST, s) and not re.search(FUT, s):
        errs.append(f"PAST-TENSE FUTURE EVENT: {r['ticker']} {r['catalyst_date'].date()}")
if d.duplicated(subset=['ticker','catalyst_date','conference']).any():
    errs.append("DUPLICATE (ticker,date,conference) rows present")
if errs:
    print('\n'.join(errs[:20])); sys.exit(1)
print(f'OK — {len(fut)} future events, none fabricated, no duplicates.')
```

**This guard is more valuable than any layout test.** It defends the one claim the product is built on.

---

# 4. Answering the sequencing question: **/about → /corrections → /llms.txt. In that order. And not yet on the last one.**

### ✅ `/about` — **yes, do it now.**
It's cheap, it closes a real E-E-A-T gap, and — critically — **`/corrections` is worthless without a named human behind it.** An anonymous corrections page is a shrug. A signed one is a reputation. Do `/about` first *because* it's the foundation for the next page.

### ✅ `/corrections` — **yes, and you're right that no competitor would publish it. But it has to be second, not first.**

**You cannot launch a corrections page while an uncorrected error is sitting in the pipeline.** That's the single way to make it backfire.

**So: fix the 5 fabricated events, then launch `/corrections` with the fabrication as entry #1.** That is the most credible possible opening for that page:

> *"Our new conference crawler invented five presentations that will never happen — it read a 2025 ASH presentation described in the past tense and scheduled it for December 2026. We caught it in review before it reached the site. Here's the bug, here's the guard we added, here's the CI test that now blocks it."*

Nobody in this category would ever write that paragraph. **The bug is the story.** It's also the perfect companion to the two you already have — the 68%-flat stat you refused to publish, and the Conference Overlay you retired. Three entries, all of them "we were wrong and we told you." That page *is* the brand.

### 🔴 `/llms.txt` — **no. Not until the crawler is verified clean.**

This is the non-obvious one, and it's why I'd hold it.

`llms.txt` is an **invitation for ChatGPT, Perplexity and Gemini to ingest and quote you at scale.** Point them at a calendar containing five conferences that don't exist and **your fabrications get laundered into AI answers** — where they're confidently repeated, screenshotted, cached, and re-cited long after you've fixed the source.

**A wrong date on your website is a wrong date. A wrong date in `llms.txt` is a wrong date that ChatGPT tells ten thousand people with total confidence.** And you will never fully claw it back.

**Data integrity is a hard prerequisite for AEO — not a parallel workstream.** Ship `llms.txt` the day *after* the CI guard is green. It's a one-hour job whenever you want it; the cost of shipping it early is unbounded.

---

# 5. Site re-audit — nothing new broke
*(excluding the items the builder is actively on)*

- Sitemap: **334 URLs, 100% www** ✅
- Research pages: full `Dataset` + `Article` + `FAQPage` + `BreadcrumbList` schema ✅
- `/account`, `/login`, `/screener`, `/developers` — all 200 ✅
- Pro "coming soon": payments correctly disabled, waitlist live ✅
- API: `_locked: none`, anonymous access working ✅
- Still absent from top 10 for the head term — expected; the tail (ticker hubs) is the path.

⚠️ **One residual:** `catalysts_out/catalysts_public.csv` still carries **4 conference rows with `ticker = NaN`**. The FRESH file has zero null tickers — make sure the public feed is regenerated from FRESH and that a null ticker can never enter it.

---

# The order
1. **Fix the 5 fabricated events + dedupe + ship the CI guard** ← nothing else matters until this is green
2. **Regenerate the public feed from FRESH** (kill the 4 null-ticker rows)
3. `/about`
4. `/corrections` — **with the fabrication as entry #1**
5. `/llms.txt` — only once the guard is green

---
*Facts and historical statistics only. Not investment advice.*
