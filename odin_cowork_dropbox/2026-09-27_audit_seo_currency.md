# Audit: the numbers are now the FDA's own, and we lost the answer box on packaging, not accuracy
**2026-09-27, measured 20:05 UTC = 16:05 Eastern (Sunday).** *Per RULE 1 every time carries its zone.*
**Live build `e020bb610`, generated 2026-09-27T16:32:51Z. API `as_of` 2026-09-27, 458 rows. Consoles read live in Chrome; Bing data runs through September 25, Google through September 25.**
*Facts and build mechanics only. Not investment advice.*

---

# 0. TWO CORRECTIONS OF MINE, FIRST

**My corrected statistic of 32 was itself wrong.** It counted two co-listed partner pairs as four observations: GSK and SPRO are one NDA (tebipenem), and JAZZ and ZYME are one BLA supplement (Ziihera). I checked the arithmetic line by line and never asked whether the rows were independent. The builder merged them on the FDA record each rests on, and also removed the LNTH-2501 CRL, whose date is announcement-only under the same rule that excluded TLX. The published figure is **29: 18 early / 10 on the day / 1 late**. I re-derived it:

```
early (18), sorted:  -110 -108 -58 -43 -19 -19 -19 -12 -6 -5 -4 -4 -4 -3 -3 -2 -2 -1
on the day (10):     ARQT VERA MRNA LNTH(TAUKLARIFY) JAZZ/ZYME GILD ACHV UNCY MRK(WINREVAIR) TLX
late (1):            REPL +4
n = 29, median = position 15 = -3  ->  "3 days before"   ✓
```

**And I said the newswire was the only source for Atebrioz.** It was not. The FDA published its notice on CDER's "News & Events for Human Drugs" page at **2:46 PM Eastern on September 25**, four hours before Mirum's release. It was on a page type the watcher does not read, which is a sharper finding than the one I made.

---

# 1. VERIFIED LIVE: THE 09-26 ORDER SHIPPED, AND IT IS CORRECT

| Item | Live |
|---|---|
| Timing statistic, all surfaces | `/calendar`, `/learn/what-is-a-pdufa-date`, `/research/fda-decision-timing` and `/llms.txt` all read **29 / 18 / 10 / 1**, median 3 days before. The largest early margin is IBTROZI at 110 days |
| Provenance claim | *"29 of 29 action dates on this page are taken from the FDA's own record, not from a company announcement."* That sentence is now true, it is checkable, and no competitor can say it |
| Atebrioz | Both rows Decided / Approved 2026-09-25, sourced to the FDA notice. Decision page carries brand, FOP 12+, PRV to Incyte, the licensing and PROGRESS efficacy |
| Pharming lower-dose Joenja | `pdufa_phar_2027-01-30` Upcoming, sourced to the 6-K |
| Next-decision pointer | RHHBY Tecentriq, 2026-10-09, `next_days: 12`. Correct: October 9 is twelve days from September 27 Eastern |
| Aggregator sources | Guard in place; LNTH now cites the FDA letter, not StockTitan |

**Structural sweep, all 458 rows:** 0 rows with a date at non-day precision, 0 `date_month` mismatches, 0 day-precision PDUFAs past goal and undecided, 0 scheduled conferences past their date. Upcoming PDUFAs **43, of which 39 are sourced**; the four without a source are the rows awaiting David's ruling.

**Conference dates drawing new search impressions, checked against the organisers:** AASLD The Liver Meeting, **November 5 to 9, Denver** ✓. SABCS, **December 8 to 11, San Antonio** ✓. AACR Pancreatic (Sept 25 to 28) and ASTRO (Sept 26 to 30) are correctly "In progress."

**Haymarket's October roundup matches us exactly.** A web-search summary had returned their October dates shifted one row out of line with ours; I opened the Pulmonology Advisor page in Chrome and it reads Tecentriq Oct 9, ifinatamab Oct 10, satralizumab Oct 15, bepirovirsen Oct 26, INO-3107 Oct 30. Identical to our dates. The summarizer was wrong, not Haymarket and not us. Their list has five rows; ours also carries phentolamine (IRD and VTRS) on October 17, which they omit. Their entries carry trial data and no source links.

---

# 2. CURRENCY: WE WERE RIGHT, AND LATE, AND WE LOST THE ANSWER BOX

**The race on Atebrioz, in Eastern time:**

| When | What |
|---|---|
| Sep 25, 2:46 PM | FDA notice on CDER News & Events |
| Sep 25, 7:00 PM | Mirum / Incyte release on Business Wire |
| Sep 26, 3:20 PM | our site still "under review" (my 09-26 audit) |
| Sep 27, about 1:00 AM | our decision pages live, about **34 hours after the FDA** |
| Sep 27, 4:05 PM | Bing's answer for `atebrioz zilurgisertib approval` cites **trialfriend.com**. We are not in the visible results |

**The sentence that won:** *"Atebrioz (zilurgisertib) was approved by the FDA on September 25, 2026 for people 12 and older with fibrodysplasia ossificans progressiva, the genetic disease in which muscle and soft tissue gradually turn into bone. It is the third FOP treatment and the first that blocks the ALK2 receptor directly."*

**What our page leads with.** Title: *"Atebrioz (zilurgisertib) **Approval Announced** Sep 25, 2026."* Meta description, the string answer engines lift: *"MIRM: Atebrioz approval was **announced by the sponsor** on September 25, 2026; the FDA action day is not stated, so no goal-date margin is published."*

Two problems, one of them an accuracy defect:

1. **The meta description contradicts our own page.** The body and the primary source are the **FDA's** notice. "Announced by the sponsor" is the template written for TLX, where the sponsor was the only source, applied to a case where the FDA published first. It understates what we know.
2. **It spends the lifted sentence on our method instead of the fact.** Our body is more complete and better sourced than trialfriend's sentence: the FDA notice time, the newswire time, the PRV, the licensing, the efficacy numbers. The margin caveat belongs in the body, where it already is. The meta description should state the fact the FDA published.

A fact-first version that stays inside the builder's rule, because it asserts only what the FDA's notice establishes:

> *The FDA announced its approval of Atebrioz (zilurgisertib) on September 25, 2026, for fibrodysplasia ossificans progressiva in patients 12 and older, the third FOP treatment, according to the FDA's notice.*

"Third treatment" is the FDA's own headline: *"FDA Approves Third Treatment for Fibrodysplasia Ossificans Progressiva."*

**What would have caught it in time.** The FDA's CDER "News & Events for Human Drugs" page had Atebrioz at 2:46 PM. The builder named it as the next cheap win on 09-26. It is now the single highest-value watcher addition, because it is the FDA itself, it covers every sponsor, and it posts before the newswire.

---

# 3. CHANNELS

## 3a. Bing AI citations, through September 25

| | Sep 18 | Sep 25 |
|---|---|---|
| Total citations | 6.9K | **8.8K** |
| Average cited pages | 21 | 22 |
| Grounding queries | 25 | **31** |

| Query | Citations | Share, Sep 18 → Sep 25 |
|---|---|---|
| pdufa date | 714 → **863** | 22.59% → **22.92%**, held |
| fda calendar 2026 | 322 → 346 | 28.96% → **27.59%** |
| upcoming clinical trial readouts rare disease ... | 126 → **234** | 35.90% → **47.76%** |
| major upcoming Phase 3 oncology trial readouts ... | 114 → 147 | 60.32% → 58.10% |
| pdufa dates | 52 → 73 | 35.62% → 36.68% |
| fda pdufa calendar | 12 → 21 | 23.08% → 29.58% |

**The rare-disease readout query nearly doubled and gained twelve points of share** in the week after `/readouts/rare-disease` went live on September 15. That is the second clean content-to-channel chain after the `/learn` restructure: a page built for a named query, and the query moving.

**New grounding queries worth acting on:** `fda approval letters` (15 citations, **13.04%**) arrived the same week we started citing an FDA letter on every decision row, and we hold 39 of them. `is there a list of pdufa dates` at **53.33%**. `fda approvals today release` at 23.81%, `fda release schedule` 6 → 18.

## 3b. Bing web search, through September 25

| 3-month window | to Sep 18 | to Sep 25 |
|---|---|---|
| Clicks | 512 | **607** |
| Impressions | 20.3K | **24.4K** |
| CTR | 2.52% | 2.49% |
| Ranked keywords | 695 | **942** |

**The daily series needs an honest read.** Weekday impressions averaged about **857** for September 14 to 18 and about **667** for September 21 to 25, a **22% drop week over week**. That is still roughly 56% above the August weekday level of about 430, and clicks held (19, 22, 17, 10, 15 against 19, 17, 24, 17, 16). The September 8 step is holding above baseline and decaying from its peak.

**It is not the Open Graph bug.** The builder found that `add_og_tags.py` malformed the `<head>` of 1,055 pages from September 23 to 26. The decline started on September 21 and 22 (675, 637), before that push. I am recording that so nobody attributes the decline to it.

Positions on the core terms kept improving: `pdufa date` 5.48 → **5.30** on 558 impressions; `pdufa calendar` 67 → **105** impressions and 14 → **18** clicks. **Conference queries have arrived**: `aasld 2026` (32 impressions, position 8.84), `aasld 2026 dates` (12), `sabcs 2026` (13, position 9.38). Both sets of dates are verified correct above. The same four keyword rows remain frozen and unreadable, as noted on 09-20.

## 3c. Google Search Console, 28 days through September 25

| | to Sep 13 | to Sep 18 | to Sep 25 |
|---|---|---|---|
| Clicks | 40 | 29 | **25** |
| Impressions | 2.29K | 2.53K | **3.1K** |
| CTR | 1.7% | 1.1% | 0.8% |
| Average position | 13.4 | 11.7 | **8.8** |
| Queries | 103 | 109 | 136 |

On 09-20 I said I would not explain the click decline without better data. The query table's position column explains it:

| Head term | Google position |
|---|---|
| pdufa calendar | **55.6** |
| pdufa dates | **57.0** |
| fda pdufa calendar | **60.4** |
| fda approval calendar | 69.1 |
| pdufa date | **70.0** |
| what is a pdufa date | **78.4** |

against drug-name queries at **1.0 to 7.3** (icotrokinra 1.0, tovecimig 1.3, zimberelimab 2.0, tenapanor 5.6, juvmo 7.0, pixclara 7.3).

**On Google we do not rank for the head terms at all; they sit on pages six to eight.** The improving average position is a mix shift toward low-volume drug queries where we rank near the top. Google's clicks come from the brand (`pdufa.bio`, 7 clicks at position 1.1) and from those entity pages. On Bing the same head terms sit at positions 4 to 6. **Google is an authority problem on the head terms, not a content problem**, and until that changes, per-drug pages are the Google strategy. The generative-AI report did not open from the console link this session and was not read.

---

# 4. COMPETITOR MOAT

**Where we now lead, verifiably:** every action date in the timing study is the FDA's own record, linked, on 29 of 29 rows. RTTNews dates approvals to the announcement day (TLX, TAUKLARIFY). Haymarket's roundup matches our October dates but carries no source links, no decided status and one fewer October decision.

**Where we lose, and it is now one pattern:** on a decision day the answer box goes to whoever publishes a clean, fact-first sentence first. That was **trialfriend.com** on Atebrioz. In the prior week it was simianx.ai and allsci.com on the PDUFA date. None of them was on our list a month ago. None of them is more accurate than we are. Each of them was faster, and each led with the fact.

**Haymarket runs one article across at least three authoritative domains** (Pulmonology, Cardiology and Endocrinology Advisor, originating at MPR). That is syndicated reach we will not match on the roundup format, which is another reason the per-drug decision page, not the monthly list, is where we win.

---

# 5. ORDER

| # | Item | Acceptance |
|---|---|---|
| **1** | **Watch the FDA's CDER "News & Events for Human Drugs" page** as a fourth FDA source, same verify-then-publish contract. It had Atebrioz four hours before the newswire | A replay of September 25 raises the Atebrioz lead at the 2:46 PM posting |
| **2** | **Fact-first title and meta description on decision pages sourced to an FDA notice.** Lead with "The FDA announced its approval of {brand} ({INN}) on {date} for {indication} ...", add the FDA's own framing ("third FOP treatment") where the notice states it, keep the margin caveat in the body. Retire "announced by the sponsor" wherever the source is the FDA | `/fda-decision/MIRM-2026-09-25` and `INCY-2026-09-25` meta descriptions state the FDA fact; guard: no decision page whose primary source is an FDA domain says "announced by the sponsor" |
| **3** | **Sponsor feeds for the next 60 days of goal dates**, by hand where auto-discovery fails: Roche/Genentech (Oct 9, Oct 15), Merck (Oct 10), Opus Genetics and Viatris (Oct 17), GSK (Oct 26), Inovio (Oct 30) | Each of those sponsors is in `_sponsor_feeds.json` |
| 4 | **An FDA approval letters hub.** 39 decision rows now cite an FDA letter; `fda approval letters` is a live grounding query at 13% share. A dated, sourced list of the letters we hold is an asset nobody else has assembled | Page live, rows link letters, n stated |
| 5 | **Conference pages for AASLD and SABCS** checked for completeness: queries are arriving at positions 8 to 9 on Bing | Both pages carry dates, location, and the tracked presentations |
| 6 | Carry: AdComm calendar, 13F block, exclusivity, `daily/NEW_*` into `/pdufa-date-changes`; David's rulings | |

---

# 6. BOTTOM LINE

**Accuracy is now a documented advantage.** The flagship statistic is 29 decisions, 18 early, 10 on the day, 1 late, with every action date taken from the FDA's own record, and the page says so in a sentence nobody else in this category can write. Every structural invariant is clean, October's dates match the largest medical publisher's, and the conference dates now drawing search traffic are correct.

**What we are losing is the first 24 hours, and the first sentence.** The FDA told the world about Atebrioz at 2:46 on Friday afternoon. A site nobody tracked had the answer box by the weekend. We published about 34 hours after the FDA, with a better page whose lifted sentence described our method instead of the approval. Items 1 and 2 close that gap, and both are small.

**And Google needs a different plan from Bing.** On Bing we rank fifth for "pdufa date." On Google we are on page seven. Until our authority on Google catches up, the per-drug pages are where Google sends us traffic, which makes the speed and the first sentence of those pages matter more, not less.

---
*Live figures read 2026-09-27 between 20:05 and 20:40 UTC against build `e020bb610`. API invariants computed in-page over all 458 rows. Timing statistic re-derived by hand from the published rows. Consoles read live in Chrome. Haymarket October roundup read directly on pulmonologyadvisor.com. AASLD and SABCS dates confirmed against the organisers' published dates. Bing SERP for `atebrioz zilurgisertib approval` read live. Not investment advice.*
