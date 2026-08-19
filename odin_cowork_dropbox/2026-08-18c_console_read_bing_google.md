# Console read — Bing, Google, AI citations
**2026-08-18 · both consoles read live tonight · supersedes the estimates in `2026-08-18b`**
*Facts and historical statistics only — not investment advice.*

---

# 1. THE NUMBERS

## Bing (data begins Aug 8 — ~9 days)
| | |
|---|---:|
| Clicks | **66** |
| Impressions | **2.7K** |
| CTR | **2.47%** |

## Google (3 months)
| | |
|---|---:|
| Clicks | **34** |
| Impressions | **1.96K** |
| CTR | **1.7%** |
| **Average position** | **21** |

**Bing produced 66 clicks in ~9 days. Google produced 34 in 90 days.** That's **7.3/day vs 0.38/day — Bing is running ~19× Google.**

## AI citations — the standout
| | Aug 12 | **Aug 18** |
|---|---:|---:|
| Total citations | 115 | **413** |
| Avg cited pages | 7 | **8** |
| Grounding queries | 1 | **5** |

**3.6× in six days.** This is the fastest-growing channel by a wide margin.

---

# 2. 🔴 THE BIGGEST SINGLE LEVER: the CTR cliff

Bing keyword data, 3 months:

| Keyword | Impressions | Clicks | CTR | Avg position |
|---|---:|---:|---:|---:|
| **pdufa** | **237** | **0** | **0.00%** | 6.32 |
| **pdufa date** | **95** | **0** | **0.00%** | 6.79 |
| pdufa date for daraonrasib in usa | 47 | 0 | 0.00% | 7.26 |
| pdufa mk 6240 | 12 | 0 | 0.00% | 4.00 |
| pdufa approval | 12 | 0 | 0.00% | 5.58 |
| **pdufa calendar** | 12 | **3** | **25.00%** | **2.08** |
| **fda pdufa calendar** | 11 | **3** | **27.27%** | **3.64** |
| rusfertide pdufa date | 7 | 1 | 14.29% | 2.86 |

**The pattern is unambiguous: at position 2–3 we convert at 25–27%. At position 6–7 we convert at 0%.**

Not "low" — **zero**. 332 impressions on the two highest-volume terms produced nothing.

**The arithmetic:** move "pdufa" (237) and "pdufa date" (95) from position ~6.5 to position ~2.5 and, at our own observed 25% CTR, that's **~83 clicks — more than the entire 3-month Bing total of 66.**

Page-level confirms it:

| Page | Impressions | Clicks | CTR | Position |
|---|---:|---:|---:|---:|
| `/calendar` | 1.2K | 31 | 2.63% | 4.98 |
| **`/` (homepage)** | **519** | **1** | **0.19%** | 6.45 |
| `/readouts` | 122 | 4 | 3.28% | 4.02 |
| `/decisions` | 79 | 4 | 5.06% | 5.29 |
| `/calendar/2026/august` | 49 | 0 | 0.00% | 2.71 |
| **`/pdufa/REGN-garetosmab`** | 16 | **4** | **25.00%** | 2.75 |

**The homepage is the worst asset on the site:** 519 impressions, **one** click. It's absorbing the "pdufa" head term and converting nothing. `/calendar` outperforms it 14:1 on clicks from twice the impressions.

---

# 3. TWO CORRECTIONS TO MY OWN AUDITS

**(a) Per-event PDUFA URLs already exist. I tested the wrong format — twice.**

```
/pdufa/REGN-garetosmab    200 ✅
/pdufa/LNTH-florquinitau  200 ✅
/pdufa/LNTH-2026-08-13    404   ← the format I kept testing
```

The scheme is `/pdufa/{TICKER}-{drug-slug}`, not `{TICKER}-{date}`. I reported this as "not done" on 08-16 and 08-18. **It was done.** And it's working — `/pdufa/REGN-garetosmab` is the **best-converting page on the site at 25% CTR**.

Coverage is partial though: `/pdufa/CAPR-deramiocel` 404s. **Completing the set is now evidence-backed, not a hunch.**

**(b) My Google authority thesis is confirmed — harder than I put it.**

| | Aug 12 | **Aug 18** |
|---|---:|---:|
| Indexed | 55 | **57** |
| Not indexed | 453 | **858** |

We added ~190 sitemap URLs. **Indexed went +2. Not-indexed went +405.**

And the reason breakdown is decisive:

| Reason | Pages |
|---|---:|
| **Discovered – currently not indexed** | **823** |
| Redirect error | 19 |
| Page with redirect | 6 |
| Not found (404) | 5 |
| Crawled – currently not indexed | 3 |
| Alternate page w/ canonical | 1 |
| Duplicate, different canonical | 1 |

**96% of Google's problem is one bucket, and it's pure authority.** Technical debt is 24 pages. Indexation rate: 57/915 = **6.2%**.

I said "stop shipping pages for Google." The data says it more bluntly: **every page we ship is currently going straight into the not-indexed pile.**

---

# 4. 🟢 THE CLEAREST OPPORTUNITY I'VE FOUND: drugs we're cited for but have no page

Grounding queries, live tonight:

| Query | Citations | Citation share | Do we have the page? |
|---|---:|---:|---|
| rusfertide pdufa date | 21 | 16.67% | ✅ `/drug/rusfertide`, 5 Q |
| **pdufa date for daraonrasib in usa** | **14** | **8.43%** | ❌ **`/drug/daraonrasib` → 404** |
| upcoming clinical trial readouts rare disease | 9 | 24.32% | — |
| **camizestrant pdufa date** | **5** | **33.33%** | ❌ **`/drug/camizestrant` → 404** |
| neladalkib pdufa date | 3 | 20.00% | ✅ `/drug/neladalkib`, 5 Q |

**We are being cited for two drugs we don't have pages for.** Something else of ours is grounding those answers.

**daraonrasib is the single best target on the site:**
- **14 AI citations at only 8.43% share** — the lowest of the five
- **47 Bing web impressions at position 7.26 with 0 clicks**
- **No page exists**

Both channels want a `/drug/daraonrasib` page and neither is being served. Compare neladalkib: has a page with 5 questions, holds **20%** share.

**Four of five grounding queries are the pattern `{drug} pdufa date`.** That is the query family we win, and we have 544 drug pages already built to serve it.

---

# 5. WHAT TO DO, IN ORDER

| # | Action | Evidence | Effort |
|---|---|---|---|
| 1 | **Build `/drug/daraonrasib` and `/drug/camizestrant`** | 19 citations + 47 impressions with no page | hours |
| 2 | **Fix the homepage's head-term conversion** — 519 impressions, 1 click. Title/description aren't earning the click for "pdufa" and "pdufa date". Consider pointing those terms at `/calendar`, which converts 14× better. | 0.19% CTR at pos 6.45 | hours |
| 3 | **Complete the per-event PDUFA URL set** — `/pdufa/{TICKER}-{drug}` | best page on the site, 25% CTR | 1 day |
| 4 | **Audit every drug in the grounding list for a live page**, then extend to the whole `{drug} pdufa date` family | 4 of 5 queries follow it | 1 day |
| 5 | **Fix Google's 24 technical pages** — 19 redirect errors + 5 404s. Small, but validation is "Started" and it's the only Google lever that isn't authority. | | hours |
| 6 | **Stop adding pages for Google's benefit; pursue citations** — Wikipedia FDA-approval articles, newsletter pickups of the patent-cliff dataset | +190 pages → +2 indexed | ongoing |
| 7 | Conference-page FAQs (still `Question=0` on 14 pages) | ~50 questions, afternoon | hours |
| 8 | Decision-page FAQs 1 → 3 | 334 → ~1,000 questions | 1 day |

---

# 6. BOTTOM LINE

**AI citations are the story: 115 → 413 in six days, five grounding queries where there was one.** That channel is compounding faster than either search engine and it's the one our structure was built for.

**Bing's constraint is position, not content.** We convert at 25–27% at position 2 and **0%** at position 6–7. The two highest-volume keywords — "pdufa" and "pdufa date," 332 impressions — sit at 6.3–6.8 and produce nothing. Fixing that one gap is worth more than everything shipped in the last week.

**Google's constraint is authority, and it's now measured:** +190 pages bought +2 indexed and +405 not-indexed. 823 of 858 are "Discovered – currently not indexed." More content will not move it.

And two things I got wrong: **per-event PDUFA URLs were already shipped** (I tested `{TICKER}-{date}`; the scheme is `{TICKER}-{drug}`), and they're the best-converting pages on the site. That makes completing them an evidence-backed priority rather than a guess.

---
*Read from Bing Webmaster Tools and Google Search Console, 2026-08-18. Not investment advice.*
