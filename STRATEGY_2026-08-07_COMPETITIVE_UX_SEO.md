# pdufa.bio — How we beat the competition
**Strategy brief · 2026-08-07 · UX/UI + SEO + AEO**
*Built from live SERP recon and competitor teardowns done today, not from priors.*

---

# 1. WHERE WE ACTUALLY STAND

Live Google SERP for the money query **"fda calendar 2026 pdufa dates"**:

| # | Who | What ranks |
|---|---|---|
| 1 | **Assyro AI** | `/tools/pdufa-calendar` |
| 2 | **FDA Tracker** | `/fda-calendar` |
| 3 | **BiopharmaWatch** | `/fda-calendar` |
| 4 | CheckRare | orphan-drug PDUFA list |
| 5 | MarketBeat | `/fda-calendar/upcoming` |
| 6 | **Reddit r/biotech** | *"13 upcoming 2026 PDUFA dates I've been tracking"* |
| 7 | FDA.gov | Novel Drug Approvals 2026 |
| 8 | **BiopharmaWatch again** | `/PDUFA-calendar` — they own two page-1 slots |

**pdufa.bio is not on page 1.** We have 51 indexed pages and 421 still "Discovered – not indexed."

That's the bad news. The good news is what the teardown revealed.

---

# 2. THE DECISIVE FINDING: NOBODY HAS BUILT THE LONG TAIL

A `site:` sweep across Assyro + BiopharmaWatch + FDA Tracker returns only three kinds of page:

1. **Hub pages** — `/fda-calendar`, `/pdufa-calendar`
2. **Glossary/definition pages** — *"Prescription Drug User Fee Act (PDUFA)"*, *"What is a PDUFA date"*
3. **Blog explainers** — *"FDA Review Clock: PDUFA Timelines Explained"*, *"FDA User Fees Guide"*, *"How to Invest in Biotech Stocks"*

**Not one of them has a per-drug, per-ticker, or per-decision indexable URL.**

Assyro's calendar is the tell — its state lives in **query parameters**:
`/tools/pdufa-calendar?view=calendar&window=90&selectedEventId=pdufa_bed8c2a…`
Every event is behind a query string. That is **zero SEO surface area per event**. Their entire catalyst dataset ranks on exactly one URL.

We already have roughly **377 long-tail URLs** they have no equivalent of:
`/ticker/*` (157) · `/fda-decision/*` (135) · `/pdufa/*` (85)

**Strategic read:** the hub-page war is crowded and we're behind on authority. The long-tail war is *empty* and we're the only one with an army. Stop trying to out-rank Assyro on "fda calendar 2026" first. **Win 377 low-competition queries nobody is contesting, use that to build authority, then take the hub.**

---

# 3. COMPETITOR WEAKNESSES WE CAN ATTACK NOW

### Assyro AI (the new #1)
Modern dark UI, four view modes (Calendar / Timeline / Status Board / Table), rich filters (status, application type, published date, urgency window), search.
- 🎯 **Their freshness badge says "Synced 1w ago."** They are a **week stale**. We sync daily and publish decisions same-day. *This is the single most attackable weakness in the category.*
- 🎯 **69 records** in the 90-day window. We carry **419 events**.
- 🎯 The calendar is a **lead magnet** for an enterprise product ("Book a Demo", "Solutions", "Pricing"). It exists to capture emails, not to be the best catalyst tracker. It will never get the depth we give it.
- 🎯 No historical outcomes. No decision archive. No original research.

### BiopharmaWatch
Owns two page-1 slots; 1,100+ companies, 85+ metrics; strong blog.
- 🎯 Wins on **educational content**, which is cheap for us to contest and which we currently ignore.
- 🎯 Their FDA-calendar copy is machine-generated boilerplate ("The FDA has set a PDUFA target action date of August 13, 2026") — thin, undifferentiated, easy to beat on depth.

### FDA Tracker
- 🎯 Splits "Standard" vs "Enhanced" (paywalled) calendar. Free tier is deliberately weak. Our free tier is genuinely complete — say so.

### Reddit
- 🎯 A Reddit thread outranks all of us for some queries. That's a demand signal: people want a **human, opinionated, current** list. It's also a distribution channel we're not using.

---

# 4. THE FIVE WEDGES

Things we have that competitors **cannot copy quickly**, ranked by leverage.

## Wedge 1 — Same-day, primary-sourced decisions (attacks "Synced 1w ago")
We published VTRS/Gwyn Lo, MRNA/mFLUSIVA and REPL/TUDRIQEV within days, with correct goal-date-vs-actual-date modelling. Assyro is a week behind.

**Do:**
- Put a **live freshness stamp** on every page: *"Updated 4 hours ago · next FDA decision in 6 days."* Make it the first thing above the fold. Competitors' staleness becomes visible by contrast.
- Add a **"Decided today / this week"** module on the homepage. Recency is the product.
- Publish the outcome page **within the hour** of a decision, with the brand name in the title. That page is the one that earns links from Reddit/X/journalists in the 24h window when everyone is searching.

## Wedge 2 — The verified/unverified transparency (nobody else does this)
`/decisions` publishing *"449 records · Verified 142 · Unverified 307"* and **deleting the approval-rate stat rather than computing it from mixed data** is a genuinely rare posture. It's also exactly what Google's quality guidelines reward on YMYL finance/health content.

**Do:**
- Make it a **brand pillar**, not a footnote. A `/trust` page: how we verify, what we won't publish, what we got wrong (`/corrections`), our error rate.
- Put a **provenance badge on every fact** — "✓ primary source" with the linked filing vs "~ inferred." Competitors publish numbers with no provenance at all; make that comparison unavoidable.
- This is also our defence: we retracted a false SLS CRL within days of finding it. That story is a trust asset — publish it.

## Wedge 3 — Original research with sample sizes (unmatched)
Run-up studies across ~5,100 catalysts, CC BY 4.0, with n and IQR, and published limitations. Nobody in the category has this.

**Do:**
- Every ticker page gets a **cohort context line**: *"Micro-cap FDA decisions historically moved ±7% on decision day (n=302)."* This answers "how high could it go?" without a price target — differentiated and defensible.
- Get **DOIs** (Zenodo/OSF) for each study. Academic citations are durable authority that no competitor is chasing.
- Pitch the counter-intuitive findings — *"the conference run-up is a 2020 artifact"*, *"nano-cap presenters are the worst cohort"* — to Endpoints/STAT/Fierce. Those are link magnets.

## Wedge 4 — Free, no-key API + `/llms.txt` (the AEO land-grab)
Competitors paywall (FDA Tracker "Enhanced") or gate behind demos (Assyro). We give the data away with attribution.

**Do:**
- **Own the AI answer layer.** When someone asks ChatGPT/Perplexity "when is the next FDA decision for X," the answer should cite us. Now that `Allow: /api/v1/` is fixed, this is live — instrument it (check referrer traffic from AI surfaces).
- Publish a **client library on GitHub** (Python + JS). Dev repos earn links and drive `/developers` traffic, which is currently our worst-performing high-value page.
- Add a **"cite this page"** widget with BibTeX/APA. Makes us the quotable default.

## Wedge 5 — Entity depth per ticker (the 377-URL army)
`/sls` at 3,185 words with the full REGAL fact set is the proof-of-concept. It's the best page in the category for that ticker, by a wide margin.

**Do:** industrialise it. See §5.

---

# 5. UX/UI — WHAT TO BUILD

### 5.1 Match Assyro's view modes, then beat them on URLs
They have Calendar / Timeline / Status Board / Table. We have lists. Build the views — **but give each one a real URL**, which they can't:
```
/calendar/2026/august          ← month view (already exists, extend)
/calendar/timeline             ← gantt of the next 90 days
/calendar/week                 ← this week's decisions
/screener?...                  ← keep filters in query params (correctly noindexed)
```
Their filter state is a query param; ours should be a **path** wherever it represents a distinct, linkable answer. Every filter combination worth a search query deserves a URL.

### 5.2 The single highest-value UX addition: a countdown-first hero
Retail's actual question is *"when, and what happens then?"* Put it above the fold on every catalyst page:

> **VTRS · Gwyn Lo · 6 days** → PDUFA Aug 17
> Micro-cap decisions historically move **±7%** on day one (n=302)
> ✓ Verified · FDA source · updated 4h ago

That single block delivers timing + context + provenance + freshness. No competitor has all four.

### 5.3 Ticker page template (roll to all 157)
`/sls` proves the format. Standardise it:
1. **Answer box** — the timing question, in one sentence, with the date and its confidence
2. Upcoming catalysts table
3. Full decision history (linked to `/fda-decision/*`)
4. Cohort statistics with n
5. **FAQ block** with `FAQPage` JSON-LD — literally the People-Also-Ask questions
6. Related tickers in the same TA (lateral crawl paths)
7. `Organization` + `Dataset` JSON-LD with `sameAs` → IR, Wikidata, ClinicalTrials.gov

### 5.4 Mobile + performance
Core Web Vitals still shows **"No data"** on both mobile and desktop — insufficient CrUX traffic. That flips to a ranking factor the moment traffic arrives, so get ahead of it: server-render everything above the fold, no layout shift on the countdown, defer non-critical JS.

### 5.5 Small UX wins with outsized effect
- **Add-to-calendar (.ics)** per event — utility that earns bookmarks and repeat visits.
- **Email/RSS alert per ticker** — turns a one-off search into a returning user, and is the top of the Pro funnel.
- **"Last 7 days of decisions"** permalink — the page journalists will bookmark.
- **Share-card images** (OG) auto-generated per event, with ticker/drug/date/countdown. Makes X/Reddit posts render richly — free distribution.

---

# 6. SEO/AEO — THE PLAN

### 6.1 Win the long tail first (uncontested)
Target patterns nobody else has a page for:
- `{TICKER} PDUFA date` · `{company} FDA decision date` · `{drug} FDA approval date`
- `when is the {TICKER} phase 3 readout` ← Google's own PAA question
- `{drug} PDUFA date {year}` · `{TICKER} FDA calendar`

377 pages × even modest volume beats one hub page we can't rank yet. And each one that ranks feeds authority back to the hub.

### 6.2 Contest the educational keywords we've ceded
Competitors win *"What is a PDUFA date"*, *"FDA review clock"*, *"How to invest in biotech stocks"*. We have `/learn` (8 pages) doing nothing. These are cheap, evergreen, link-attracting, and they establish topical authority that lifts the whole domain.

Write the definitive versions — ours can be better because we can **cite our own data**: *"A PDUFA date is the FDA's target action date. In our archive of 449 decisions, the FDA acted early in X% of cases (n=…)"*. Nobody else can write that sentence.

### 6.3 Structured data as competitive moat
We already have Events valid (14/2), Breadcrumbs 26/0, Datasets 3/0. Extend:
- `FAQPage` on every ticker + learn page → PAA boxes
- `Dataset` on every research page → Google Dataset Search (a surface with *no* competition here)
- `Organization` + `sameAs` on ticker pages → entity binding
- `SpecialAnnouncement`/`NewsArticle` on same-day decision pages → freshness surfaces

### 6.4 AEO — be the source AI quotes
This is the fastest-moving surface and we're best positioned:
- `/llms.txt` is live and the API is now crawlable
- Write answers in **extractable form**: one-sentence answer, then the evidence. AI lifts the first clean sentence.
- Always include **n and date** — models prefer citable specifics
- Never publish probabilities — that refusal is itself quotable and builds the "reliable source" reputation

### 6.5 Distribution (the authority gap)
Structure alone won't fix 421 uncrawled pages; authority will.
- **Reddit** ranks for our queries — participate honestly in r/biotech, r/SLS threads with data, not links
- **Zenodo DOIs** for research
- **Wikipedia/Wikidata** citations on PDUFA-related articles (follow their sourcing rules)
- **GitHub** client library
- **Journalist outreach** — a free, no-key API is a reporter's tool, and reporters link tools

---

# 7. 30 / 60 / 90

**Days 1–30 — finish the foundation, then industrialise**
1. Close the open data bugs (BMY/Bevacizumab title, brand names mFLUSIVA/TUDRIQEV, MRNA self-referential source, REPL decision page 404)
2. Roll the `/sls` template + `FAQPage` schema to the top 30 tickers by search interest
3. Ticker links from `/calendar` and `/decisions` rows (currently 0)
4. Live freshness stamp above the fold sitewide
5. Keep submitting 8–10 URLs/day; watch "Discovered – not indexed" fall

**Days 31–60 — expand surface + contest education**
6. Remaining 127 ticker pages on the template
7. Timeline / week / month calendar views **with real URLs**
8. 8–12 definitive `/learn` articles citing our own dataset
9. `.ics` export + per-ticker alerts
10. Split sitemap into an index so per-section progress is measurable

**Days 61–90 — authority + moat**
11. Zenodo DOIs; Wikipedia/Wikidata citations
12. GitHub client library + "cite this page" widget
13. Journalist pitch on the counter-intuitive findings
14. `/trust` page; publish the SLS retraction as a trust story
15. Auto-generated OG share cards

---

# 8. HOW WE KNOW IT'S WORKING

| Metric | Now | 90-day target |
|---|---:|---|
| Indexed pages | **51** | 300+ |
| "Discovered – not indexed" | **421** | < 150 |
| Page-1 rankings for `{TICKER} PDUFA date` | ~0 | 50+ |
| Total search clicks (90d) | **39** | 1,000+ |
| Referring domains | low | +25 quality |
| AI citations (ChatGPT/Perplexity) | untracked | **instrument this now** |

Leading indicator: **"Discovered – not indexed" falling.** It already moved 478 → 421 this week after the sitemap fix, so the mechanism works.

---

# 8b. ADDENDUM — WE RANK #3 ON BING/DDG AND NOWHERE ON GOOGLE. THAT'S GOOD NEWS.

**Owner observed we're on DuckDuckGo page 1. Verified — and it's diagnostically important.**

DuckDuckGo does not run its own web index for the most part; its results are **primarily Bing's index**. So DDG ≈ Bing, and both differ from Google. Tested the same query on all three today:

| Engine | pdufa.bio position for *"fda calendar 2026 pdufa dates"* |
|---|---|
| **Bing** | **#3 organic** — `pdufa.bio/calendar`, ahead of Assyro (#5), MarketBeat, FDA Tracker |
| **DuckDuckGo** | **Page 1** (`/calendar`) — mirrors Bing |
| **Google** | **Not on page 1** |

Bing's page-1 order: 1 novapharmanews · 2 biopharmawatch · **3 pdufa.bio** · 4 novapharmanews · 5 assyro · 6 MarketBeat · 7 FDA Tracker.

## Why this matters more than it looks
**It isolates the problem.** Two engines with different crawlers and ranking systems see the same pages. Bing crawled us, indexed us, and ranks us **third — above the site that leads Google**. Google has us at 51 indexed pages with 421 still uncrawled.

So the content is **not** the constraint. Quality, relevance, structure and freshness are demonstrably good enough to rank top-3 on a major engine. **Google's gap is crawl budget and domain authority, not merit.** That validates the whole §2 thesis — we don't need to rewrite anything, we need Google to *see* what Bing already sees, and we need the authority that makes Google trust it.

It also means the current traffic number (39 clicks/90d, Google-only) **understates reality** — we should be measuring Bing/DDG separately.

## Two new competitors this surfaced
- **novapharmanews.com** — #1 on both Bing and DDG, timestamped **"1 hour ago"**. Publishing at very high frequency.
- **biomednexus.com** and **guerilla-finance.com** — cited in Bing's AI answer though not ranking organically.

Note the freshness stamps Bing shows: *"1 hour ago"*, *"1 day ago"*. **Our result carries no visible timestamp.** Bing weights and displays recency heavily — this is a direct, cheap win (§5.2).

## The sharpest finding: we rank but aren't quoted on broad queries — and ARE on long-tail
Bing's AI answer for the broad query cites **guerilla-finance, assyro, biomednexus, novapharmanews** — **not us**, despite our ranking #3. Those sites won the citation by writing **declarative explainer prose** ("Standard Review: 10-month review period from NDA/BLA acceptance…"). Our calendar page is a data table — excellent for humans, hard for an answer engine to lift.

But on the **long-tail** query *"CAPR PDUFA date deramiocel"*, pdufa.bio ranks **and appears in Bing Copilot's cited references** — headline: *"CAPR PDUFA date — CAP-1002, Aug 22 2026"*.

**Conclusion: the long tail is where we win on both surfaces at once — ranking *and* AI citation.** On broad head terms we can rank but get out-quoted by explainer content. That's precisely the §6.1/§6.2 split: take the long tail now, and add extractable answer-prose to compete for head-term citations.

## Actions this adds
1. **Set up Bing Webmaster Tools** (if not already) and **enable IndexNow** — near-instant indexing on Bing/Yandex on every deploy. We're already winning there; compound it. It's also the cheapest indexing lever available, versus Google's ~10/day manual quota.
2. **Track Bing/DDG rankings and traffic separately.** Judging ourselves only on Google Search Console has been hiding a top-3 position.
3. **Add a visible "updated X ago" timestamp** to every page — Bing displays it, and our fastest-moving rival leads with *"1 hour ago"*.
4. **Add extractable answer prose** above the tables (one declarative sentence per page) so we get *quoted*, not just ranked.
5. Benchmark **novapharmanews.com** properly — it beat everyone on both Bing and DDG and wasn't on the July competitor list.

---

# 9. THE ONE-PARAGRAPH VERSION

Assyro, BiopharmaWatch and FDA Tracker are fighting over a handful of hub pages, and all three are stuck there because their event data lives behind query parameters — they have no per-drug or per-ticker URLs at all, and the category leader is running a **week stale**. We have 377 long-tail pages they can't match, daily freshness, a 449-record decision archive with published provenance, original research with sample sizes, and a free API that AI assistants can now crawl. So: don't fight for "fda calendar 2026" yet. Take the 377 uncontested queries, make each ticker page the best page on the internet for that ticker, wrap it in FAQ/Dataset schema, lead every page with a countdown and a freshness stamp, and convert the trust posture — verified vs unverified, no price targets, published corrections — from a footnote into the brand. The authority that earns will win the hub page later, and by then the moat is 377 pages deep.

---
*Facts and historical statistics only. Not investment advice.*
