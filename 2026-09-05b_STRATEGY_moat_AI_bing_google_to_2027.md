# Strategic audit — competitive moat, AI citations, Bing, Google · horizon end-2027
**2026-09-05 · every SERP below was run live today in Chrome; every claim about our own site is checked against build `2026-09-05T14:44Z`**
*Facts and historical statistics only — not investment advice.*

---

# 0. THE TWO THINGS TO KNOW BEFORE ANYTHING ELSE

**1. P0 — Camizestrant was approved yesterday and we don't have it.** FDA granted accelerated approval on **September 4, 2026** to camizestrant (**Etcamah**, AstraZeneca). Three fda.gov pages confirm it. **We are the single most-cited source on `camizestrant pdufa date` — 72 AI citations, 32.14% share** — and our drug page says nothing. It was even re-stamped "Updated September 5" without the approval.

**2. We are #1 on Bing and invisible on Google, and on both engines the AI answer box cites our competitors, not us.** On Bing `pdufa dates 2026` we hold organic #1 — directly *underneath* an AI answer that cites five other sites. On Google we are not on page 1 for any head term, and the AI Overview cites seven others.

Everything below follows from those two facts.

---

# 1. 🔴 P0 — CAMIZESTRANT: THE BLIND SPOT THE WATCHER CANNOT SEE

## The fact, from FDA's own pages

> *"On September 4, 2026, the Food and Drug Administration granted accelerated approval to camizestrant (Etcamah, AstraZeneca), an estrogen receptor antagonist…"* — in combination with a CDK4/6 inhibitor (abemaciclib, palbociclib or ribociclib).

Confirmed on **three** fda.gov pages: the press announcement, the drug-approval notice, and the Oncology/Hematologic Malignancies approvals list.

## Our state

| Surface | What it says |
|---|---|
| API (`/api/v1/events`) | **0 camizestrant records** — never a tracked PDUFA event (no public day-precision date) |
| `/drug/camizestrant` | *"Camizestrant is a AstraZeneca PLC program in 1st-line HR-positive, HER2-negative…"* — **present tense, pending** |
| Mentions of Etcamah / September 4 / approved | **zero** |
| openFDA Drugs@FDA | not indexed yet (~9-day lag, as measured on MIMRYLO) |

## Why this is structurally different from REGN

REGN was a dated event that slipped through. **Camizestrant was never an event.** Its PDUFA date was extended in May and never re-disclosed to the day, so it lived only as a drug page. The watcher — correctly, per its own design — watches *day-precision Upcoming events*. It has no reason to look at a drug page.

**That is exactly the limit I flagged in the fail-safe audit** (*"month/quarter-precision events aren't watched… a blind spot if a bucketed event resolves early"*). It turned out to be wider: **a drug with no event at all**, on which we hold the highest AI citation share we have anywhere.

## Why it matters more than one page

**AI citation share is an obligation, not a trophy.** When we are the 32% source on a drug and the drug gets approved, every AI system grounding on us keeps repeating "pending" — until it notices, and then it stops trusting the page. **We are currently teaching Copilot that camizestrant is unapproved.**

## The fix — a second watcher, scoped to drug pages

The existing watcher keys on *events*. Add one that keys on **every drug we have a page for** (559 of them):

| Source | What it catches | Lag |
|---|---|---|
| FDA press announcements RSS (`fda.gov/news-events`) | approvals FDA chooses to announce — camizestrant was one | **same day** |
| FDA "Oncology/Hematologic Malignancies Approval Notifications" | every oncology approval, dated to the day | same day |
| openFDA Drugs@FDA (already wired) | everything, eventually | ~9 days |
| Sponsor 8-K by ticker (already have tickers) | approvals + CRLs the company files | same day |

Match on INN against our 559 drug slugs — the same lead-token rule the event watcher already uses. **A hit is a lead, never an auto-publish**, same discipline.

Then **guard 60**: *no drug page may carry a "program"/pending description for a molecule that appears in FDA's approvals feed.* Asserts the render, like guard 59.

---

# 2. THE COMPETITIVE MAP — AS IT ACTUALLY IS TODAY

I ran the head terms on both engines this afternoon. These are two different wars.

## Bing — a content war we lead organically and lose in the answer box

**`pdufa calendar`**: (1) **FDA Tracker** — with **ten sitelinks** · (2) **pdufa.bio** — "19 hours ago" · (3) FDA.gov · videos · (5) novapharmanews — also "19 hours ago" · biopharmawatch · RTTNews

**`pdufa dates 2026`**: **AI answer box first** — cites biomednexus, burns-media, assyro, biotechsign, guerilla-finance. **Then** (1) **pdufa.bio** · (2) novapharmanews · (3) FDA Tracker · (4) assyro · biopharmawatch ×2 · pdufa.bio home · alphabreakoutlab · FDA.gov · biotechsign

**`pdufa`**: AI answer cites bio.org, Wikipedia, FDA.gov. Organic: FDA.gov, Motley Fool, Wikipedia ×2, novapharmanews. **We are below the fold** — 838 impressions at position 6.28, 0.48% CTR. The query is definitional; we are a calendar. Intent mismatch, and `/learn/what-is-a-pdufa-date` is the page that should be here.

## Google — an authority war we are not yet in

**`pdufa calendar` page 1**: FDA Tracker · RTTNews · FDA.gov · CheckRare · **BPIQ** · **MarketBeat** · Assyro · **Unusual Whales** · BiopharmaWatch. AI Overview cites BPIQ, Assyro, BiopharmaWatch, **TipRanks**, **Pharmacy Times**. **pdufa.bio: absent.**

**`pdufa dates 2026` page 1**: FDA Tracker · CheckRare · Assyro · FDA.gov · MarketBeat · Pharmacy Times · BPIQ · RTTNews · **Reddit r/biotech** (a 4-month-old post). AI Overview lists *specific dates* — "September 18, 2026: Zidesamtinib (Nuvalent)… September 30: Mavacamten (BMS)… November 30: Povetacicept" — cited to Pharmacy Times, BPIQ, CheckRare, FDA Tracker, MarketBeat. **pdufa.bio: absent.**

**Entity queries** — `rusfertide pdufa date`: Takeda PR · ASH · Larvol · Targeted Oncology · **Drugs.com** ("Mimrylo (rusfertide) FDA Approval History") · BioPharma APAC · FDA.gov · MedPath. **pdufa.bio: absent.** `camizestrant pdufa date`: AstraZeneca PR · **FDA.gov (the approval, "2 days ago")** · Targeted Oncology · Nasdaq · FirstWord · **dansfera.com** · FDA AdComm · OncLive. **pdufa.bio: absent.**

## Two new clones, one on each engine

- **novapharmanews.com** — Bing #2 on `pdufa dates 2026`, showing "19 hours ago." **They have copied the daily-rebuild freshness signal.** It is no longer a differentiator on its own.
- **dansfera.com** — Google page 1 on `camizestrant pdufa date` with a per-drug page, live price, and the disclaimer *"PDUFA dates are FDA target action dates, not…"* — **our per-drug format, our disclaimer language, plus a price we don't show.**

**The lesson is not that they're a threat. It's that freshness, per-drug pages and honest disclaimers are copyable in weeks.** Whatever the moat is, it isn't those.

---

# 3. WHY THE AI ANSWERS CITE THEM AND NOT US — the sentence-supply diagnosis

I read what each AI answer actually quoted. The pattern is unambiguous. **AI answers select sentences, not tables.** Every citation fell into one of five shapes:

| Shape | Who got cited | The exact thing quoted |
|---|---|---|
| **Definitional prose** | biomednexus, Pharmacy Times | *"Standard Review: 10-month review period… Priority Review: 6-month… Extensions: typically 3 months"* |
| **Honest FAQ answer** | BiopharmaWatch | *"Does the FDA publish an official PDUFA calendar? **No.** The FDA does not publish a public, forward-looking calendar…"* |
| **Dated changelog** | BPIQ | *"08/07/26: Catalent Indiana removed after OAI. Second fill-finish review progressing; PDUFA still September 30, 2026."* |
| **Editorial date list in sentences** | Pharmacy Times | *"The quarter opens on September 18, 2026, with zidesamtinib, Nuvalent's…"* |
| **Captioned table** | Assyro, CheckRare, MarketBeat | extracted as `Table_title: Upcoming FDA PDUFA dates (next 90 days)` |

**We have the best data on every one of those facts and the worst sentence supply.** Our calendar is a table without a caption, our FAQPage schema exists but the *prose* an AI would lift is thin, and our decision-timing and date-change data — the richest changelog material in the category — isn't rendered as dated sentences anywhere.

**Three specifics that hurt:**

1. **BiopharmaWatch is being cited for "the FDA does not publish a calendar."** That is the single most quotable fact in our space and it should be *our* sentence — we can say it with the number: *"The FDA publishes no forward calendar; every one of the 75 dates here comes from a company filing or FDA notice, and each row links to it."*

2. **BPIQ's changelog is `/pdufa-date-changes`** — specced, still 404. They render "PDUFA still September 30" as a dated line; we hold the same events and don't render the history.

3. **Pharmacy Times' "8 PDUFA Dates to Watch" article** is a prose walk through the quarter. It was published Aug 21 and is already in Google's AI Overview. A monthly *"What the FDA decides in October"* page in the same shape — dates as sentences, plain language — is content we can generate from the dataset every month, with better accuracy and a rebuild.

---

# 4. THE MOAT, DECOMPOSED — copyable vs. not

Novapharmanews and dansfera settle the question of what *isn't* a moat. Here is what is:

| Asset | Copyable? | Currently rendered as quotable sentences? |
|---|---|---|
| Daily rebuild / freshness stamp | ✅ copied already | — |
| Per-drug pages + disclaimers | ✅ copied already | — |
| **FDA-feed early-approval watcher** | ❌ nobody else auto-detects; MIMRYLO 33 days early → 72 citations | partially (event page sentence) |
| **1,840-event run-up series, real closes, T-120 baseline** | ❌ years of price data + 96.1% coverage disclosure | ✅ on one page |
| **Decision-timing dataset** (n=29 in 2026: early / on / late) | ❌ requires the sourced archive | ✅ one sentence per event |
| **458 FDA CRL letters, indexed** | ❌ the corpus took real work; 11 pages cite them | ❌ 40 CRL pages still don't |
| **Orange Book patent cliff, TA-mapped (427 cliffs)** | ❌ ATC classification work | ❌ not on the site |
| **Free documented API** | ❌ RTTNews charges, BPIQ is an app | ✅ `/developers` — and *"FDA calendar API"* is a Google People-Also-Search-For |
| **Conference presenter corpus, hand-verified** | hard | ✅ with PRECLINICAL labels |

**The strategy writes itself from this table: publish derivatives of the uncopyable rows as quotable sentences.** That is the sentence supply (§3) and the moat (§4) in one move — the competitors can copy the sentence but not the number in it.

Examples of sentences only we can write:
- *"Of 29 FDA decisions in 2026 with a sourced date, 17 came before the goal date. The largest early margin was 33 days (rusfertide, MIMRYLO, August 28)."*
- *"Across 1,840 PDUFA events since 2020, the median stock was up 2.1% from 120 trading days out to the day before the decision. The middle half ranged from −14% to +20%."*
- *"FDA has issued 149 Complete Response Letters to applications that remain unapproved, and 309 to applications later approved. Every letter is linked below."*
- *"Of the 427 U.S. patent cliffs between 2026 and 2031, 40 are cancer drugs and 102 fall in 2031."*

---

# 5. THE PLAN TO END-2027 — three tracks, one engine

## Track A — Bing: hold #1 organic, win the answer box (Q4 2026 – Q1 2027)

| # | Action | Mechanism |
|---|---|---|
| 1 | **Explainer block at the top of `/calendar`** — 5 short paragraphs: what a PDUFA date is, 10/6-month reviews, 3-month extensions, "FDA publishes no calendar; each row here links its source," and the early/on/late split with the 2026 n | This is precisely what the answer box quoted from five competitors. Give it the sentences from the #1 page instead. |
| 2 | **Caption every table** (`<caption>` + visible title) — "Upcoming FDA PDUFA dates, next 90 days, updated September 5" | Assyro/CheckRare/MarketBeat get extracted as `Table_title`; ours doesn't |
| 3 | **`/pdufa-date-changes`** — dated one-line entries per event, newest first | BPIQ's changelog shape, with our sourcing |
| 4 | **Monthly "What the FDA decides in {Month}"** page, generated from the dataset | Pharmacy Times' shape, rebuilt daily, never stale |
| 5 | **Fix the `pdufa` intent mismatch** — `/learn/what-is-a-pdufa-date` needs to be the page Bing shows for the bare term; internal-link it from every drug/event page on first use (still not done) | 838 impressions at 0.48% |

**Sitelinks are the structural gap vs. FDA Tracker** (ten of them). The nav freeze is the right call and is already running; **do not touch nav before 2027-01-01.**

## Track B — AI citations: breadth via entities, depth via sentences (continuous)

Grounding queries went 1 → 19 in a month. **10 of 19 are `{drug} pdufa date`.** The next 100 are more of the same. Three levers, in order:

| # | Action | Why |
|---|---|---|
| 1 | **Drug-page watcher (§1)** — approvals land on drug pages within 24h | protects the share we already hold; camizestrant is the cost of not having it |
| 2 | **Brand names into `alternateName`** — from the watcher's own openFDA `brand_name` field | Drugs.com beats us on `rusfertide pdufa date` with "Mimrylo" in the title. We fetch the brand and discard it. |
| 3 | **Populate `outcome` + one plain-language sentence on every Reported readout** | TENX still says only "−88%" |
| 4 | **Company pages** — `/company/{name}` aggregating a sponsor's PDUFAs, readouts, CRL history, patent cliffs | `pfizer pfe pdufa dates…` = 82 impressions, position 3.23, **zero clicks**. Google PASF includes "FDA approval calendar stocks." Real demand, unserved. |

**Target: grounding queries 19 → 150 by end-2027**, driven by the entity count. Every drug page with a brand name, an approval sentence and a source is a candidate query.

## Track C — Google: authority via earned, link-attracting assets (2027)

You handle outreach. These generate links *without* outreach:

| # | Asset | Why it attracts links |
|---|---|---|
| 1 | **The API** — already live, already documented, free tier | *"FDA calendar API"* is a Google PASF today. Developers link to APIs they use. Nobody else has a free documented one. Add a `/developers` changelog and a code sample per language. |
| 2 | **The run-up study as a citable dataset** — `Dataset` schema on `/runup-by-year`, a CSV download, a DOI-style stable URL | Academics and journalists cite datasets; 1,840 events with a 96.1% coverage disclosure is publishable |
| 3 | **CRL letters hub** (`/crl`, still 404) | 458 primary documents indexed by drug, company and reason — the reference page for CRLs that doesn't exist anywhere |
| 4 | **Patent cliff hub** | 427 cliffs, TA-mapped — the only free one |
| 5 | **Monthly decisions page (Track A #4)** | the linkable, shareable artifact each month |

**Realistic Google targets by end-2027:** page 1 on `{drug} pdufa date` for every tracked drug (entity queries already convert at 50–100% where we appear); AI Overview citation on the head terms (requires Track A's sentences + Track C's authority); indexed 57 → full sitemap (1,412). **Head-term page 1 on `pdufa calendar` is the stretch goal, not the plan** — that's a 15-year-old domain with ten sitelinks.

---

# 6. WHAT "OUTPACED BY END-2027" MEANS, MEASURABLY

| Metric | Today | End-2027 target |
|---|---|---|
| Bing organic, 5 head terms | #1–2 | **#1 on all five** |
| Bing AI answer box, head terms | cited on **0 of 3** tested | **cited on all** |
| Bing clicks / 3 months | 293 | **5,000+** |
| AI grounding queries | 19 | **150+** |
| AI citations / 3 months | 3.3K | **50K+** |
| Google indexed | 57 | **1,400+** (full sitemap) |
| Google page 1, `{drug} pdufa date` | ~5 drugs | **every tracked drug** |
| Google AI Overview, head terms | 0 | **cited** |
| **Approval → on-site latency** | ~9 days (watcher); **∞ (camizestrant)** | **< 24 hours, every drug page** |
| Drug pages with brand `alternateName` | 0 | **every approved drug** |

That last row is the one that feeds all the others.

---

# 7. ORDER FOR THE BUILDER

| # | Action | Class |
|---|---|---|
| **1** | **Camizestrant → approved Sep 4, 2026 (Etcamah), accelerated, source fda.gov** | P0, today |
| **2** | **Drug-page watcher** (FDA press RSS + oncology approvals list + openFDA + 8-K) → guard 60 | closes the class |
| **3** | Calendar: link MNKD, REPL, JAZZ, ZYME decisions | carried from 09-05 |
| 4 | **Explainer block + table captions on `/calendar`** | Bing answer box |
| 5 | Brand names → `alternateName` | entity breadth |
| 6 | `/pdufa-date-changes` | BPIQ's shape, our data |
| 7 | Monthly "What the FDA decides in October" | Pharmacy Times' shape, our accuracy |
| 8 | `/company/{name}` pages | 82 impressions at 3.23, zero clicks |
| 9 | `/crl` hub · patent cliff hub · `Dataset` schema + CSV on run-up | Google link magnets |
| 10 | `/readouts` TYRA row · `outcome` on TENX/MPLT | carried |

---

# BOTTOM LINE

**We have data supremacy and sentence poverty, and the AI answer box has become position zero.** On Bing we hold organic #1 on `pdufa dates 2026` and sit directly beneath an AI answer citing five other sites. On Google we're absent from page 1 on every head term while the AI Overview quotes seven others — reading specific PDUFA dates off Pharmacy Times and BPIQ that we hold more accurately. The reason is not ranking. It is that **AI answers quote sentences, and ours are in tables.**

**The moat is real and it isn't what got copied.** Novapharmanews cloned our freshness stamp; dansfera cloned our per-drug page and disclaimer. Neither can clone the FDA-feed watcher, the 1,840-event price series, the 458 CRL letters, the decision-timing dataset or the free API. **The whole strategy is to render those five assets as quotable sentences** — the competitors can copy the sentence but not the number inside it.

**And the watcher's first catch has already shown what speed buys.** `rusfertide pdufa date` did not exist as a grounding query on August 27. It is now 72 citations. **Camizestrant is the same opportunity running in reverse**: we are the 32% source, it was approved yesterday, and our page says "program." Fix it today; build the drug-page watcher this week so it is the last time.

---
*SERPs run live 2026-09-05 in Chrome (Bing + Google, en-US). Camizestrant approval verified against three fda.gov pages. Not investment advice.*
