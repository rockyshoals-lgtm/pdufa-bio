# Plan: #1 on both engines by 31 Dec 2026
**2026-08-29 · re-audit on a current run + live SERP checks on both engines**
*Facts and historical statistics only — not investment advice.*

---

# PART 1 — RE-AUDIT: the 08-29 batch shipped and verified

Site built `2026-08-29T03:19Z`, 49 guards passing. Every lever from the ranking map is live:

| Lever | Status | Verified |
|---|---|---|
| 1 — Snippets on low-CTR pages | ✅ | `/pricing` title 73ch / desc 155ch · `/sls` 81/158 — both keyword-led, within limits |
| 2 — Legacy URLs | ✅ | **`/pdufa-dates` 404 → 308 → `/calendar`** · `/pdufa-calendar` 308 · `/odin` 308 |
| 3 — Link graph to `/calendar` | ✅ | drug 3 · ticker 5 · pdufa-event 5 · condition 3 inbound links each |
| 4 — Answer sentences | ✅ | see below — this is the best work in the batch |
| 5 — Position 7–8 rescue | ✅ | `/learn/what-is-a-pdufa-date` retitled *"What Is a PDUFA Date? FDA Goal Dates Explained, With 2026 Data"*, Q=3, 677w · conference pages Q=3 |
| 6 — `/condition` hub | ✅ | **404 → 200**; `/condition/cancer` Q 2→**5**; `/condition/rare-disease` Q=5; 9 siblings cross-linked |
| 7 — Alias join | ✅ | daraonrasib handled on `/drug/daraxonrasib` |

**The answer sentences are the strongest thing shipped.** They are exactly the citation unit:

> *"Rusfertide's PDUFA date is Sep 30, 2026. That is the FDA's goal date to complete review of the application; the agency can act earlier or extend it."*

> *"Daraxonrasib (RMC-6236) is under FDA review, but no action date has been publicly disclosed (NDA accepted 2026-07-22; action date not public)."*

Answer, date, and the honest limit — in two sentences an engine can lift whole.

## Correction to my own 08-29b finding
I said daraxonrasib's **7.23% citation share** was "a page-authority problem on that specific drug." **That was over-confident.** The page now shows why: **daraxonrasib has no publicly disclosed action date.** But camizestrant *also* has no public date and holds **37.5%** — so "no date" doesn't explain it either. **I don't know the cause, and I should not have asserted one.** Re-measure after this batch has had two weeks to be recrawled.

## Two small gaps in the batch
1. **`/condition` hub has `Question=0`** — every other hub carries a FAQ.
2. **`/condition/cancer` dropped 2,921 → 715 words.** Rebuilding from the living dataset was right (it had been frozen since June), but that's a 75% cut on Google's #2 impression page. **Watch its position; if it slips from 10.0, restore depth.**

---

# PART 2 — WHERE WE ACTUALLY RANK (live SERP, not console averages)

## Bing — "pdufa calendar"

| # | Result |
|---|---|
| 1 | **FDA Tracker** — *with a 9-link sitelink block* |
| **2** | **pdufa.bio /calendar** — "4 hours ago" |
| 3 | FDA.gov (FDA-TRACK) |
| 4 | novapharmanews |
| 5+ | biopharmawatch · RTTNews · MarketBeat · bpiq · BioPharmCatalyst |

**We are #2 on Bing, one position from the target.** The console's "5.04" is an average across 321 queries; on the head term we're second.

## Google — "pdufa calendar"

| # | Result |
|---|---|
| 1 | FDA Tracker |
| 2 | RTTNews |
| 3 | FDA.gov |
| 4 | CheckRare |
| 5 | **Assyro AI** — *"source-linked deadlines"* |
| 6–10 | BPIQ · Ataxia Foundation · MarketBeat · BiopharmaWatch · BioPharmCatalyst |

**pdufa.bio does not appear in the top 20.**

---

# PART 3 — THE HONEST ASSESSMENT

**Bing #1 by 31 Dec 2026: realistic. I'd put it at ~70%.**
We're #2, we own the freshness signal, and the gap to FDA Tracker is a brand/sitelink gap rather than a content gap.

**Google #1 by 31 Dec 2026: not realistic, and I won't write a plan that pretends otherwise.**

The blocker is measured, not speculative:
- **57 pages indexed. Flat for eleven days.** 1,290 in "Discovered – currently not indexed."
- Average position **20.5**; absent from the top 20 on the head term.
- The nine sites above us are 5–15 years old with accumulated citation profiles. Domain authority is the one input that cannot be engineered in four months.

**What Google *can* realistically reach by 31 Dec: top 10 for "pdufa calendar", 300+ indexed pages, and 300+ clicks/quarter.** That is a large win and it's the honest target. Chasing #1 there in 2026 would burn the quarter on the one lever that doesn't respond to effort.

---

# PART 4 — THE PLAN

## 🎯 Targets

| | Bing | Google |
|---|---|---|
| **"pdufa calendar" rank** | **#1** | **top 10** |
| Indexed pages | — | **300+** (from 57) |
| Clicks / month | **1,200+** (from ~300) | **150+** (from ~18) |
| AI citations / month | **12,000+** (from ~4,800 run-rate) | — |
| Grounding queries | **40+** (from 16) | — |

## SEPTEMBER — close the Bing gap

**1. Earn the sitelink block.** FDA Tracker's #1 result carries nine sitelinks; ours carries none. That is the single visible difference at the top of the SERP. Sitelinks are earned through a clear, stable, shallow hub structure with descriptive anchors. We now have Calendar · Decisions · Readouts · Patents · Explore · Research · API — **that is exactly the shape Bing rewards.** Keep the nav stable for the whole quarter; do not rename or reorder.

**2. Capture the People-Also-Ask boxes.** Google's PAA for this query is a gift:
> *"Does FDA approve before the PDUFA date?"* · *"Are PDUFA dates public?"* · *"What are the upcoming FDA approvals for 2026?"* · *"What is an FDA PDUFA date?"*

**We have a sourced, 26-of-26 answer to the first one and nothing else on the internet does.** Make `/research/fda-decision-timing` answer it in the exact PAA phrasing, in the first sentence, in `FAQPage`. Do the same for the other three across `/calendar` and `/learn/what-is-a-pdufa-date`. **PAA entries are the cheapest route onto Google page 1 without domain authority.**

**3. `/condition` hub FAQ**, and watch `/condition/cancer`'s position after the word cut.

## OCTOBER — scale the citation engine

**4. Apply the answer-sentence template to every drug on the calendar.** 16 grounding queries today; every `{drug} pdufa date` page is a candidate. This is generated work — the format is proven and one query already holds **100% share**.

**5. Ship `/compare/`.** The last unbuilt surface, and the most citable format that exists. Five decided drugs with named incumbents.

**6. External citations — the only Google lever.** In priority order: Wikipedia FDA-approval articles needing a decision-date source; the patent-cliff dataset pitched to biotech newsletters as an annual reference; Google Dataset Search.

## NOVEMBER — compound

**7. Long-tail surfacing.** Only 3.5% of pages earn an impression. Every drug page should link its ticker, condition, conference and patent-cliff entry. This is the lever on 1,290 unindexed pages.

**8. Freshness as a moat.** We already stamp "4 hours ago" against novapharmanews' identical stamp. Daily rebuilds plus the live countdown are a structural advantage over FDA Tracker's static calendar — **lean on it in titles**.

## DECEMBER — defend and measure

**9. Re-audit against this document.** If Bing #1 hasn't landed by 1 Dec, the gap is sitelinks/brand, not content — pivot the last month to brand queries.

---

# PART 5 — LEADING INDICATORS (check weekly)

| Metric | Now | Healthy trajectory |
|---|---:|---|
| Bing rank, "pdufa calendar" | **#2** | #1 by 1 Nov |
| Bing sitelinks | **0** | ≥4 by 1 Nov |
| Google indexed | **57** | 100 by 1 Oct · 200 by 1 Nov · 300 by 31 Dec |
| Grounding queries | **16** | 25 by 1 Oct · 40 by 1 Dec |
| AI citations/day | **289** | 400+ sustained |
| Pages earning impressions | **45 / 1,270** | 150 by 1 Nov |

**If Google's indexed count is still under 100 on 1 October, the external-citation work isn't landing** — and that's the signal to escalate it rather than continue shipping pages.

---

# PART 6 — WHAT COULD BREAK IT

1. **Touching the nav.** Sitelinks need stability. Freeze it for the quarter.
2. **`/condition/cancer`'s 75% word cut** — the one uncontrolled change in this batch.
3. **A factual error at scale.** The whole position rests on being the source that shows its work. One wrong sourced claim costs more than any ranking.
4. **Chasing Google #1.** The quarter's biggest risk is spending it on the one lever that won't move.

---

# BOTTOM LINE

**We are #2 on Bing for the head term and absent from Google's top 20.** Everything in the ranking map shipped and verified, and the answer sentences are the best SEO work done on this site.

**Bing #1 is a realistic 2026 target.** The remaining gap to FDA Tracker is a sitelink block, which is earned through nav stability and brand signal — both of which are now in place if we leave them alone.

**Google #1 is not a 2026 target and I'd rather say so now.** 57 indexed pages, flat for eleven days, against competitors a decade older. Top 10 plus 300 indexed is the honest goal, and the route there is PAA capture and external citations — not more pages.

**The unfair advantage is already sitting there:** Google's own People-Also-Ask asks *"Does FDA approve before the PDUFA date?"* and we are the only site on the internet with a sourced, complete 2026 answer. That is the cheapest page-one entry available to us.

---
*Bing + Google SERPs and both consoles read live 2026-08-29. Not investment advice.*
