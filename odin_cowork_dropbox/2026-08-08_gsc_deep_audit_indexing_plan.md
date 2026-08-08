# Google Search Console deep audit — how to get more indexed
**2026-08-08 · Cowork session · Amendment 033 filing**
*Every figure read live from GSC + verified against live HTTP responses. Not investment advice.*

---

# THE HEADLINE

Google has crawled **~51 of 472** sitemap URLs. The other **421 show `Last crawled: N/A` — never fetched, not once.** They aren't rejected; they're queued behind a crawl budget that Google isn't willing to spend on this domain yet.

Two things buy that budget: **remove the signals that say "low quality"**, and **give Google evidence the pages are worth having**. Both are addressed below, and the first one is a same-day fix nobody has looked at.

---

# 1. 🔴 ELEVEN URLs REDIRECT INTO A 404 — the fix nobody has made

GSC reports 19 "Redirect error" URLs, validation **Failed (started 7/18, failed 7/24)**. I tested all 19 live:

| Behaviour | Count | Verdict |
|---|---:|---|
| **308 → 404** | **11** | 🔴 broken |
| 308 → 308 → 200 (2 hops) | 2 | 🟡 chain |
| 308 → 200 (1 hop) | 6 | ✅ fine |

**The 11 that land on a 404:**
```
pdufa.bio/pdufa-calendar-2026        pdufa.bio/leaderboard
pdufa.bio/meso-ryoncil-pdufa         pdufa.bio/tools
pdufa.bio/q1-2026-oncology-pdufa-dates   pdufa.bio/intel
pdufa.bio/verv-verv101-pdufa         pdufa.bio/feed
pdufa.bio/vnda-vqw-pdufa             pdufa.bio/record
                                      pdufa.bio/trade
```

**Root cause:** the non-www → www redirect is a **blanket path-preserving rule**. `pdufa.bio/tools` → `www.pdufa.bio/tools` → **404**, because `/tools` was dropped in a restructure. The redirect faithfully forwards a path that no longer exists.

**Why it matters more than 11 URLs suggests:**
- These are **legacy URLs with real history** — Google crawled and remembered them, and some have external links. A 404 discards that equity; a 301 to the right live page recovers it.
- 19 URLs repeatedly re-crawled and repeatedly failing is a **persistent low-quality signal on the domain**, and crawl budget is allocated per-domain. This is plausibly suppressing the 421.
- Validation already **failed once** (7/24), so this has been sitting broken for two weeks.

**Fix — explicit one-hop redirects, before the blanket www rule:**
```
/vnda-pdufa            → /pdufa/VNDA      (currently 2 hops)
/vnda-vqw-pdufa        → /pdufa/VNDA
/verv-verv101-pdufa    → /ticker/VERV
/meso-ryoncil-pdufa    → /ticker/MESO
/pdufa-calendar-2026   → /calendar
/q1-2026-oncology-pdufa-dates → /condition/cancer
/leaderboard /record /trade /intel /tools /feed → best live equivalent (or /)
/heatmap               → /research        (currently 2 hops)
```
Then click **VALIDATE FIX** in GSC so the 19 get re-evaluated rather than waiting for organic recrawl.

---

# 2. 🔴 PERFORMANCE DATA SETTLES THE STRATEGY ARGUMENT

Last 3 months: **38 clicks · 1,610 impressions · CTR 2.4% · average position 20.7.**

Top queries:

| Query | Clicks | Impressions | Read |
|---|---:|---:|---|
| pdufa.bio | 11 | 13 | branded — people who already know us |
| **deramiocel pdufa** | **1** | **2** | 🎯 drug-name query **converts** |
| **monalizumab** | **1** | **1** | 🎯 100% CTR |
| **miplyffa** | **1** | **1** | 🎯 100% CTR |
| pdufa dates | **0** | **55** | ❌ |
| pdufa date | **0** | **50** | ❌ |
| pdufa calendar | **0** | **44** | ❌ |
| fda pdufa calendar | 0 | 18 | ❌ |
| fda pdufa dates | 0 | 17 | ❌ |
| pdufa dates 2024 | 0 | 13 | historical-year demand |

**Roughly 250 impressions on head "pdufa date/calendar" terms produced literally zero clicks**, because average position is ~20 — page two, where nobody clicks. Meanwhile every non-branded click we earned came from a **drug name**.

That is the long-tail thesis confirmed with click data rather than argument. Head terms give us impressions we can't convert; entity queries convert at 50–100% CTR on one or two impressions.

**Implication:** stop optimising for the head. Build the entity pages.

## The specific gap: drug-name pages
"monalizumab" and "miplyffa" earned impressions **without us having a dedicated page for either**. Google is surfacing something adjacent. Give those queries a real page and they convert — the evidence is right there in the CTR.

**Build `/drug/{name}`** for every drug in the archive (~450 decided + upcoming). Each page: what it is, sponsor, indication, trial, PDUFA/decision date and outcome, label facts, cohort context. That is a **new long-tail surface roughly equal in size to the ticker surface**, targeting queries we can already prove convert.

Also worth owning: **"pdufa dates 2024"** (13 impressions). Historical-year archive pages (`/calendar/2024`, `/calendar/2025`) are evergreen, trivially generated from data already held, and nobody contests them.

---

# 3. 🟠 CTR IS THE OTHER HALF OF THE PROBLEM

CTR 2.4% at position 20.7 is roughly expected — but the 250 zero-click impressions mean our **titles and snippets aren't earning the click even when shown**. That matters for indexing too: Google demotes crawl priority for pages that get impressions and no engagement.

Two cheap fixes:
1. **Put the answer in the title.** *"2026 FDA PDUFA Calendar | pdufa.bio"* is a label. *"FDA PDUFA Calendar 2026 — 419 dates, updated daily, free"* is a reason to click. Specificity and freshness are our differentiators; neither currently appears in the title.
2. **Now that `dateModified` ships**, the "updated X ago" stamp should start rendering — that alone lifts CTR on a recency-driven query.

---

# 4. 🟡 SMALLER FINDINGS

- **`Page with redirect` (6)** and **`Not found 404` (5)** — same family as §1; the redirect map will absorb most of them.
- **`Duplicate, Google chose different canonical` (1)** — `/data-provenance` (crawled May 30). Google is preferring a different URL. Check its canonical tag.
- **Thin calendar month pages:** `/calendar/2027/january|february|april` are **282–291 words with 0 events** — real pages advertising nothing. Only 3 URLs, so not a budget drain, but they're weak pages in the sitemap. Either populate, `noindex` until they have events, or drop from the sitemap until populated.
- **`/changelog`** (728 words) is in the sitemap and uncrawled — low priority for a constrained budget.

---

# 5. THE PLAN, IN PRIORITY ORDER

| # | Action | Why it moves indexing |
|---|---|---|
| 1 | **Map the 11 redirect→404s to live pages; then click VALIDATE FIX** | Removes a two-week-old persistent quality signal + recovers legacy link equity. Same-day fix. |
| 2 | **Collapse the 2 two-hop chains to one hop** | Cheap; chains dilute signal |
| 3 | **Build `/drug/{name}` pages** | New long-tail surface the size of the ticker surface, aimed at queries GSC *proves* convert (monalizumab, miplyffa, deramiocel) |
| 4 | **Rewrite titles for click-worthiness** — lead with count + "updated daily" | 250 zero-click impressions is demand we already have and aren't capturing |
| 5 | **Historical-year archives** (`/calendar/2024`, `/calendar/2025`) | Evergreen, uncontested, data already exists, proven demand |
| 6 | **`noindex` or populate the empty 2027 month pages; drop `/changelog` from sitemap** | Stop spending scarce budget on pages with nothing to say |
| 7 | **Keep internal linking from `/calendar` + `/decisions` rows → ticker pages** | Still 0 there; it's the crawl path into the 421 |
| 8 | **Authority** — Zenodo DOIs, GitHub client library, journalist outreach | The only durable way to raise the budget ceiling |

**Sequencing note:** items 1–2 are the ones to do *first* and *alone*, then wait a week. If 421 starts falling after the redirect fix, that confirms the quality signal was the constraint and the rest gets much cheaper. If it doesn't move, the constraint is purely authority (item 8) and we should stop spending time on technical polish.

---

# 6. WHAT I'D STOP DOING

**Manual URL submission has hit its useful limit.** At ~10/day against 421 never-crawled pages it can't close the gap, and it treats a symptom. The sitemap ping is automated now and does the same job at scale. Manual requests are still worth it for a *changed high-value page* — a fresh approval, a rewritten ticker hub — and nothing else.

---

# BOTTOM LINE

The single most actionable finding is that **11 legacy URLs have been redirecting into 404s for two weeks, with a failed GSC validation sitting on them** — and it's a config fix, not a content project.

The most *strategically* important finding is in the click data: **every non-branded click we have ever earned came from a drug name**, while 250 impressions on head "pdufa calendar/date" terms produced zero. We are competing at position 20 for terms we can't win yet, and ignoring the queries we convert on at 100%. Building `/drug/{name}` pages targets proven demand, doubles the long-tail surface, and needs no new data — the archive already has every one of those drugs.

---
*Facts and historical statistics only. Not investment advice.*
