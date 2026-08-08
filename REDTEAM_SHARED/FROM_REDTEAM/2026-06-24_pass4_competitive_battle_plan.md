# pdufa.bio — COMPETITIVE BATTLE PLAN (live-audited) · 2026-06-24

I visited and audited the competitors live in Chrome (not from memory). This is the field as it actually renders today, the strategic fault lines, and exactly how to beat each of them — segmented by **retail**, **active traders**, and **institutions**.

---

## 1. The field, as audited live

| Competitor | Wedge | Per-drug PoA? | Data crawlable (SEO)? | Monetization | Biggest weakness |
|---|---|---|---|---|---|
| **MarketBeat** /fda-calendar | Generalist finance giant; FDA calendar is one of 100 tools | **No** (factual) | **Yes** (server-rendered) | "All Access" + "Top 5 Stocks to Buy" | Noisy/stale ("H1 2026", 2024-dated "updates", data errors); hype-forward; no biotech depth; filters paywalled |
| **CatalystAlert** | **AI-first** catalyst calendar, modern UI, fast-moving (BETA) | **Yes** — gated "AI %" on every card | **Yes** (server-rendered month pages) | Freemium, 50%-off launch | Firehose noise (151 "catalysts"/mo incl. earnings, generic "INC Reports…", healthy-volunteer rows); AI% is the false-precision you reject |
| **BiopharmaWatch** | SEO-first "**Free** PDUFA calendar" + screener | **Yes** — PoA % + AI "PoA Summary" paragraphs | Partial (JS-rendered grid) | Freemium | Does PoA + AI rationale (false precision); data not in crawlable text; thinner brand |
| **BioPharmCatalyst** | **Everything-platform** (FDA/PDUFA/Conf/Earnings/IPO/Device/Historical calendars + pipeline screener + hedge/insider/M&A/cash DB + Discord + podcast + crash course) | No | **No** (calendar data JS-rendered; page text = nav only) | Freemium + API | Sprawling, dated; its core *data* doesn't rank (not crawlable); breadth over clarity |
| **BPIQ** | Filterable catalyst DB (600+ co / 1,800 assets; stage/indication/MoA) | No | No (gated app) | Paid, discount-driven | Paywalled app = invisible to Google; churn-y discount vibe |
| **FDATracker** | "Analytics for Pharma & Biotech Traders" (AdCom, cash-runway, Omniview) | No | No (gated) | Paid | Dated 2010s UI; gated; analyst-niche, not retail-legible |
| **Unusual Whales** | Options-flow terminal; FDA calendar is a minor side tab | No | Partial | Sub (~tiered) | FDA calendar is an afterthought; not catalyst-scoped; not biotech-native |
| **BiotechSigns** | "AI catalyst intelligence," 8,000 cos | AI-implied | Partial | Freemium | Another AI black box; breadth over trust |
| **Dan Sfera** | Personal-brand catalyst calendar | No | Yes | Audience/affiliate | One-person brand; shallow data |

---

## 2. Three strategic fault lines (this is where the game is won)

**Fault line A — the PoA divide.** The field is split: **CatalystAlert, BiopharmaWatch, BiotechSigns publish per-drug "AI %" / PoA**; MarketBeat, BPC, BPIQ, FDATracker do **not**. The AI players are *training users to expect a probability number*. That makes your "we refuse to fake a probability" both a **risk** (users may feel something's "missing") and your **sharpest sword** — but only if you argue it loudly. Right now you state it; you don't *sell* it.

**Fault line B — the crawlability divide.** CatalystAlert and MarketBeat **server-render their data** (it's in the HTML → it ranks). BPC, BiopharmaWatch, BPIQ, FDATracker **JS-render or gate** their data (Google sees an empty shell). You server-render per-event pages — you're on the right side. **The opening:** out-rank the JS-renderers (BPC, BiopharmaWatch) on the long tail, and match CatalystAlert's month-page structure to contest the head terms.

**Fault line C — the curation/quality divide (your biggest unclaimed territory).** **Every single competitor's data is noisy.** MarketBeat mixes stale 2024 "updates" and "H1 2026" mush; CatalystAlert dumps 151 rows/month of earnings + generic "Reports Financial Results" + healthy-volunteer Phase-1 PK; BiopharmaWatch and BPC are broad but unsourced. **Nobody is the clean, curated, per-fact-sourced, provenance-tagged one.** Your date-taxonomy (FDA-set vs company-guided vs registry-est + confidence), validation badges, primary-source links, and CRL-reason curation are **unique in the market**. This is the wedge no one can copy without rebuilding their whole pipeline.

**Fault line D — the depth divide.** Only pdufa.bio combines: T-120 run-up charts + **catalyst-scoped** options/implied-move + cohort base rates by cap + CRL reasons + CT.gov Silent-Shift. Competitors are a mile wide and an inch deep per event. (BiopharmaWatch shows a single "Run Up/Down %" number; you show the *path*.)

**The one-sentence positioning that wins:** *"The calm, sourced biotech-catalyst tape — every fact traceable to a primary source, and we'll never fake an approval probability."* That sentence is true only for you.

---

## 3. How to beat them — by cohort

### 3a. RETAIL investors
**What they need:** "what's hitting soon, in plain English, to names I care about — without being sold to."
**Who's winning them now:** MarketBeat (DA + free) and CatalystAlert (slick + free + the seductive AI%). Both are noisy and hype-/AI-forward.
**Your wedge:** calm, plain-English, curated, free per-event pages, no hype, no fake odds.
**Moves to win:**
1. **Ship month pages** `/calendar/2026/[month]` with prev/next nav + a count strip — **directly contest CatalystAlert's `/pdufa/february-2026`** (they're already ranking with this; it's your single most urgent SEO gap).
2. **Condition / therapeutic-area filter** ("Cancer, Obesity/Metabolic, Alzheimer's, Rare disease…"). BiopharmaWatch has TA+drug-type filters; you don't. Retail thinks in conditions ("show me the obesity drugs").
3. **Email capture / weekly digest** — CatalystAlert, BiopharmaWatch, and MarketBeat all have it; you don't. "PDUFAs this week → your inbox." This is also your retention spine (#5/#10).
4. **A public "Why we don't show an approval %" page** — turn Fault line A into content. Name the failure mode (strong Phase 3 → CRL on CMC/safety) and contrast "a fake 82%" with "here's the verified history." This converts your guardrail into a *marketing weapon* against CatalystAlert/BiopharmaWatch.
5. **Near-term default + plain-English indications** (you still show "cUTI", "dPTEN HSPC" raw).

### 3b. ACTIVE / OPTIONS traders
**What they need:** implied move vs history, IV-crush risk, run-up path, cash/dilution, AdCom timing, "did the date move."
**Who's winning them now:** Unusual Whales (options, but not catalyst-scoped), FDATracker (AdCom/cash, dated), BPC (insider/cash DB).
**Your wedge:** you're the only one with **catalyst-scoped** options/implied-move + T-120 run-up + cohort base rates + Silent-Shift — combined.
**Moves to win:**
1. **Add the AdCom calendar + AdCom date on the event** (FDATracker's core draw; crawler data should support it now) — and earnings proximity + conference flag = the detail-sheet "Context" block (#M8). This is the biggest trader gap you can close.
2. **Lead with the run-up *path*, not a number.** BiopharmaWatch reduces it to "Run Up/Down 86.46%"; your T-120 swing-high/low chart is strictly better — make it shareable (dynamic OG image) so traders post it.
3. **Surface the Silent-Shift registry-slip log** as a standalone feed ("dates that quietly moved this week") — genuinely unique; no competitor monitors CT.gov date changes.
4. **Sort axes** (soonest / today's move / cap) + the options-context one-liner stay catalyst-scoped (don't drift toward UW's terminal — that's the guardrail and also not your wedge).

### 3c. INSTITUTIONS / fund analysts
**What they need:** a citable source of record — per-fact provenance, coverage/completeness stats, a clean feed/API, historical datasets.
**Who's winning them now:** BPC (API & data inquiries, hedge/insider/cash DBs), FDATracker (analytics), Bloomberg/Biomedtracker (out of reach). None are *honest about their own uncertainty*.
**Your wedge:** you already mark your own misses (validation badges, "price-only" labels, corrections) — radical transparency a black box can't match. `/sources` + the `/research` dataset are the seeds.
**Moves to win:**
1. **Publish a coverage statement** on `/sources`: # PDUFAs tracked, % source-verified, update cadence, what's *not* covered. Institutions buy *known* limitations.
2. **A CSV / API / webhook feed** (even read-only, even waitlisted) — BPC monetizes "API & Data inquiries"; you have none. This is the institutional door.
3. **Expand `/research`** into a small library of citable, n-disclosed datasets (you nailed the first one — run-up by cap, with the honest non-monotonic caveat). Each is link-bait that funds and journalists cite → authority + backlinks.
4. **Versioned methodology + changelog** — "what changed in the dataset, when." Source-of-record credibility.

---

## 4. SEO action plan (ranked by impact)

1. **Month-archive pages** `/calendar/2026/[month]` + `/readouts/2026/[month]` (server-rendered, prev/next, count strip, "About PDUFA dates in [Month] 2026" blurb, FAQ schema). **This is the #1 move — CatalystAlert is already eating this SERP.** Doubles as the retail month-picker UX.
2. **Programmatic per-condition pages** `/condition/[obesity|alzheimers|nash|…]` — "Upcoming FDA decisions in [condition] 2026." BiopharmaWatch has the filter but not indexable pages; own the "obesity drug FDA approval 2026" long tail.
3. **The "Why no approval %" flagship** (Fault line A as content) + keep expanding `/learn` (you're already ahead of most here — BiopharmaWatch's FAQ covers the same 7 topics; out-depth them).
4. **Out-rank the JS-renderers on the long tail:** your server-rendered `/pdufa/[ticker]` and `/fda-decision/[…]` pages can beat BPC and BiopharmaWatch on "[ticker] PDUFA date" / "[drug] FDA decision" because *their data isn't crawlable*. Make sure every per-event page has unique drug+indication+sourcing (the thin-approval-page fix from Pass 3).
5. **Dynamic per-event OG images** (ticker + date + run-up sparkline) — you're a screenshot-shared "tape"; CatalystAlert has share buttons on every card. Make your pages the prettiest unfurl in the Discord/X biotech threads.
6. **`/research` dataset library** (institutional + backlink magnet) and **per-company FDA-event pages** (MarketBeat does these programmatically; you can do them *sourced*).

---

## 5. Competitor → how to beat them (live-audited specifics)

- **CatalystAlert (the real threat):** (1) Match the month-page structure *now*. (2) Beat them on **curation** — their 151-row firehose is mostly earnings/generic noise; your curated, sourced ~30-50 real catalysts is a better product, say so. (3) Weaponize "no AI%": their gated "AI %" is the false precision; your honest base rates + verified outcomes are the antidote. (4) You're calmer and cleaner — their UI is busy.
- **BiopharmaWatch:** (1) Out-crawl them — their data is JS-rendered; your per-event pages rank where theirs can't. (2) Out-honest them — they publish "PoA 99%" with an AI paragraph; you publish verified history + "we don't fake odds." (3) Match their TA filter, then beat it with indexable `/condition/` pages.
- **MarketBeat:** (1) You'll never beat their DA on head terms — **win the biotech-native long tail** and depth (run-up, options, CRL reasons) they completely lack. (2) Contrast calm-facts vs their "Top 5 Stocks to Buy Now" hype. (3) Out-fresh them — their calendar is full of stale 2024/2025 "updates."
- **BioPharmCatalyst:** (1) Their *data doesn't rank* (JS) — take the SEO. (2) Don't fight their breadth; win on clarity + provenance + a cleaner, mobile-native UI. (3) Their insider/hedge/cash DBs serve pros — your Smart-Money/UOA context can match the *facts* without their sprawl.
- **FDATracker:** (1) Take their AdCom + cash-runway draw and present it retail-legibly with modern UI. (2) Their site is dated and gated; your free, fast, server-rendered pages out-SEO and out-UX them.
- **Unusual Whales / BiotechSigns:** (1) Stay catalyst-scoped — don't become a terminal (UW) or a black box (BiotechSigns). (2) Own the *event*; let them own raw flow / AI vibes.

---

## 6. Top priorities (do these to win)
1. **[P0 SEO] Month-archive pages** for `/calendar` + `/readouts` — contest CatalystAlert's month-page SERP and deliver the retail month-picker in one build.
2. **[P0 brand] "Why we don't show an approval %" page** — convert your guardrail into the wedge against the AI-PoA field, before users get trained to expect a number.
3. **[P1] Email/weekly-digest capture** — table stakes the whole field has and you don't; also your retention spine.
4. **[P1] Condition/TA filter + `/condition/` pages** — retail-native lens + long-tail SEO BiopharmaWatch can't rank.
5. **[P1 traders] AdCom + Context block** (AdCom/earnings/conference) — close the FDATracker/UW trader gap.
6. **[P2 institutions] Coverage statement + CSV/API waitlist + `/research` expansion** — open the source-of-record door BPC monetizes.
7. **[P2] Dynamic per-event OG images** — win the social unfurl on a share-driven beat.

**Bottom line:** you sit in the one defensible gap on the board — *curated + sourced + deep + honest*. The AI players (CatalystAlert/BiopharmaWatch) are faster and have the seductive "%"; the incumbents (MarketBeat/BPC) have DA and breadth. You beat both by (a) matching their SEO **structure** (month pages, email, conditions), and (b) out-running them on the thing none of them can fake: **provenance, curation, and the integrity to not invent a probability.** Lean all the way into it.

*— Red Team Pass 4 (live competitor audit via connected Chrome).*
