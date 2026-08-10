# Ranking audit — Bing #1 achieved
**2026-08-10 · Cowork session · Amendment 033 filing**
*Live SERP checks on both engines + both consoles. Not investment advice.*

---

# 1. 🏆 THE HEADLINE: pdufa.bio IS NOW #1 ON BING

Query: **"fda calendar 2026 pdufa dates"**

| Position | Aug 7 | **Aug 10** |
|---:|---|---|
| 1 | novapharmanews | **🏆 pdufa.bio** |
| 2 | biopharmawatch | biopharmawatch |
| 3 | **pdufa.bio** | novapharmanews |
| 4 | novapharmanews | novapharmanews |
| 5 | assyro | assyro |

**We moved #3 → #1 in three days**, passing both novapharmanews (which held #1 on Bing *and* DuckDuckGo) and staying ahead of Assyro, the Google leader. Since DuckDuckGo is Bing-powered, this should carry there too.

This is the first hard ranking win of the whole engagement, and it followed the fixes that shipped this week — redirect repair, `dateModified`, drug pages, sitemap regeneration.

## Google: unchanged, still off page 1
Same query, Google page 1: Assyro · BiopharmaWatch · FDA Tracker · CheckRare · MarketBeat · Reddit · RTTNews · FDA.gov · BPIQ. **pdufa.bio absent.** Two new entrants appeared (RTTNews, BPIQ), so the SERP is getting *more* crowded, not less.

The two-engine divergence is now stark: **#1 on Bing, unranked on Google, same content.** That remains an authority/crawl-budget story, not a quality story.

## Long-tail is working too
**"monalizumab fda decision date"** on Bing → **pdufa.bio at #5**, behind only FDA.gov, MarketBeat, Drug Trial Snapshots and Drugs.com. That page is roughly *one day old*. Competing on page 1 against FDA.gov and Drugs.com that fast is a strong signal the `/drug/` bet is sound.

---

# 2. CONSOLE NUMBERS

## Google Search Console — flat
| Metric | Aug 9 | **Aug 10** |
|---|---:|---:|
| Indexed | 55 | **55** |
| Not indexed | 453 | **453** |
| Discovered – not indexed | 418 | **418** |

**Redirect error (19) validation: still "Started"** — Google is still working through it. No movement expected until that completes; it typically takes 1–2 weeks. Nothing to do but wait.

## Bing Webmaster Tools — reporting lags a day
Still showing **Aug 8** data: 2 clicks / **187 impressions**, and **AI Performance: 8 citations / 3 cited pages**. BWT is ~24–48h behind, so today's #1 ranking won't appear in these figures yet. Worth re-reading in 2 days — that's when the ranking gain should show up as an impression jump.

Site Explorer threw *"This might be a momentary issue"* — indexed-URL count still unavailable.

---

# 3. ✅ FIXED SINCE YESTERDAY

| Item | Status |
|---|---|
| `/drug/galinpepimut-s` (SLS lead asset) was 404 | ✅ **now 200** |
| Cross-trial explainer had only `WebPage`+`WebSite` | ✅ **now `Article` + `Organization`** — correct schema for the most citable page on the site |
| `/calendar` `dateModified` was date-only | ✅ **now full ISO-8601 + offset** |
| Drug page count | 313 → **310** (3 removed, some cleanup ran) |

---

# 4. 🟡 STILL OPEN

| Item | Status | Why it matters |
|---|---|---|
| **`/drug/miplyffa` → 404** (and `/drug/arimoclomol` → 404) | ✗ | Miplyffa is one of only **three** drug queries with a documented click, at 100% CTR. Still no page under brand or generic name. |
| **`/drug/aasld-the` and `/drug/acr-convergence` still live (200)** | ✗ | Conference names published as drugs. Two URLs, 5-minute delete. |
| **`/drug/monalizumab` `dateModified` still date-only** (`2026-08-08`) | ✗ | Sibling `/drug/deramiocel` has full ISO. Inconsistent within the same template — can't render "hours ago". |
| Drug pages still thin (230–255 words) | ✗ | Ranking #5 anyway, so the ceiling is higher with depth |
| `/compare/` pages | 404 | Expected — explainer shipped first, correct sequencing |

## ⚠️ One to watch: timestamps are UTC, not ET
`/learn/why-cross-trial-comparisons-mislead` carries `dateModified: 2026-08-10T00:15:18+00:00`, and the sitemap's newest `lastmod` is **2026-08-10**. It is currently **10:35 ET on Aug 10** — so these are legitimate *in UTC*, but for a US audience the site will display tomorrow's date during US evening hours. Not the earlier future-dating bug, but the same root cause: stamping from UTC rather than America/New_York. Worth switching, since the whole point of the timestamp is to look current to a US reader.

---

# 5. WHAT I'D DO NOW

| # | Action | Why |
|---|---|---|
| 1 | **Build `/drug/miplyffa` + `/drug/arimoclomol`** | Only unclaimed 100%-CTR query we know of |
| 2 | **Delete the 2 conference slugs** | 5 minutes; they're wrong |
| 3 | **Fix `monalizumab` dateModified to full ISO; stamp from ET not UTC** | Consistency + correct display for US readers |
| 4 | **Push hard on Bing now that we're #1** — use the 100/day submission quota (12% used) | We are winning there; compound it while the position is fresh |
| 5 | **Thicken drug pages to 400–600 words** | Already at #5 on Bing while thin; depth raises the ceiling and helps Google |
| 6 | Re-read BWT in 2 days | The #1 ranking should show as an impression jump |
| 7 | ⏳ Wait on GSC redirect validation | Nothing actionable until it completes |
| 8 | ⚠️ Migrate `bing_rank_report.py` off the legacy API | **Hard deadline Aug 31** — 3 weeks |

---

# 6. BOTTOM LINE

**We took #1 on Bing for the head query, up from #3 three days ago**, ahead of the site that previously led both Bing and DuckDuckGo. And a one-day-old drug page is already #5 for a drug-name query against FDA.gov and Drugs.com — the long-tail strategy is validating faster than expected.

Google hasn't moved: 55 indexed, 418 still never crawled, redirect validation still running. That gap is now the clearest statement of where the constraint actually is — same content, #1 on one engine and unranked on the other, which is authority and crawl budget rather than anything on the page.

The practical read: **stop treating Google as the scoreboard.** Bing is delivering ~10× the daily impressions, we're now #1 there, it gives 100 URL submissions a day against Google's 10, and it's the only place we can measure AI citations. Win where we're winning, and let the Google fixes compound in the background.

---
*Facts and historical statistics only. Not investment advice.*
