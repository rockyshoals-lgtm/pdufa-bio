# pdufa.bio — SLS accuracy audit + hot-name SEO capture plan
**2026-08-02 · for the builder**
*All site data fetched from origin (`x-vercel-cache: MISS`, `age: 0`). Facts and historical statistics only — not investment advice.*

---

# 🔴 P0 — `/fda-decision/SLS-2025-02-20` publishes an FDA CRL that cannot exist

**What the page says today:** title *"SLS FDA Decision 2025-02-20: CRL"*, outcome rendered as **"✗ CRL"**, and `/ticker/SLS` summarises SELLAS as *"1 past FDA decision"* → *"Feb 20, 2025 ✕ CRL"*.

**Why it's false:** a Complete Response Letter can only be issued in response to a submitted marketing application (NDA/BLA). **SELLAS has never filed one.** Their lead asset galinpepimut-S (GPS) is still in the Phase 3 REGAL trial — awaiting the 80th event as of the May 12 2026 update — and SLS009 is Phase 2. There is no FDA action date, no CRL, and no record of one in company IR, SEC filings, or press coverage.

**Where it came from:** the page itself is labelled **"~ price-only (validating)"** with *"Validation: Outcome consistent with price; primary-source verification in pro."* So this "CRL" was **inferred from a price move** (the page shows a T-120 run-up $0.84 → $1.62 and a +4.0% decision-day move) — not observed. The inference engine saw a date and a price pattern and minted a regulatory event.

**Why this one matters more than a normal data bug:** SLS is currently one of the most-watched retail biotech tickers — WallStreetBets-driven rallies, a 32% July drawdown, retail voting it the #1 bullish name (50% of 3,400 votes vs ONDS 24%, IBRX 18%). Publishing "the FDA rejected this company's drug" about a company with no application pending, on a page Google can index, is a credibility and liability exposure that is completely out of proportion to the value of the record.

**Immediate action:** delete or `noindex` + retract `/fda-decision/SLS-2025-02-20`, and remove the "1 past FDA decision" claim from `/ticker/SLS`. Log it on `/corrections` — you already market that page as a differentiator; this is exactly what it's for.

---

# 🔴 P0 (systemic) — 68% of the decisions archive is price-inferred, and presented as fact

I scanned **all 450** decision pages for the provenance marker:

| Provenance | Pages | Share |
|---|---:|---:|
| **"price-only" (inferred from price action)** | **308** | **68%** |
| Sourced (external primary-source link) | 142 | 32% |

The 142 sourced pages are excellent — VTRS→Viatris newsroom, OTLK→GlobeNewswire, MRK→FDA.gov, CELC→Celcuity IR, BIIB→Biogen IR. The recent, manually-published work is genuinely well-sourced.

**The problem is presentation, not the existence of a lower-confidence tier.** The 308 inferred pages carry:
- Definitive titles: *"SLS FDA Decision 2025-02-20: CRL"*
- Definitive outcome glyphs: **✓ Approved** / **✗ CRL**
- Rows in `/decisions` indistinguishable from verified ones
- And they feed the aggregate on `/decisions` — *"221 appr · 96 CRL · 70%"* — so a headline statistic mixes verified and inferred outcomes

…while the only disclosure is a small "~ price-only (validating)" note, with real verification gated behind Pro.

**One thing you're already doing right:** the sitemap **deliberately excludes all 308** price-only pages (0 of 308 in sitemap; 132 of 142 sourced are included). That's a good instinct and it means *this was a considered design*. But the pages are still live, still linked from `/decisions` (448 internal links), and therefore still crawlable, indexable, and quotable — including by the AI assistants `/llms.txt` invites.

**Recommended fix (pick one, in order of preference):**
1. **`<meta name="robots" content="noindex,follow">` on every price-only page** — keeps them for internal navigation and Pro users, removes them from search and AI citation. Consistent with the sitemap policy you already adopted.
2. **Relabel honestly in the visible UI**: title → *"SLS 2025-02-20 — unverified, inferred from price action"*, replace ✓/✗ with a neutral "unconfirmed" badge, and add a visible banner. Never render an unverified outcome in the same visual language as a verified one.
3. **Split the headline stats** so `/decisions` reports "221 approvals / 96 CRLs" from *verified* records only, with inferred counts shown separately.

This directly serves the positioning in `/llms.txt` — *"We publish no approval probabilities… historical statistics only… we publish our own corrections."* Right now the archive's dominant tier quietly contradicts that.

---

# 🟠 SLS coverage gap — the actual catalyst is missing entirely

`/ticker/SLS` says **"no upcoming catalyst on file."** In reality SELLAS has the single most-anticipated small-cap readout on the board:

| Fact | Detail | Source |
|---|---|---|
| Trial | **REGAL**, Phase 3, galinpepimut-S (GPS) | Company IR |
| Indication | AML maintenance after second complete remission (CR2) | Company IR |
| Design | Event-driven overall-survival study; final analysis triggers at the **80th event** | Company IR |
| Status | **78 events as of May 11 2026**; company will announce when the 80th is reached | Q1 2026 update, May 12 2026 |
| Expected topline | **Q4 2026** (contingent on 80th event) | Company guidance |
| Second asset | **SLS009** Phase 2 in r/r AML — met all primary endpoints, FDA guidance to advance to first-line | Company IR, Jul 2025 |
| Cash | ~$107.1M as of Mar 31 2026 (later reports cite ~$138M post-raise) | Q1 2026 |
| NCT | NCT04229979 | ClinicalTrials.gov |

**Action:** add a readout record (`readout_sls_2026-Q4`, month/quarter precision with an explicit "event-driven — not a fixed date" flag) so `/ticker/SLS` and `/readouts` carry it. This is a textbook case for the confidence/precision fields you already have — the honest answer is *"triggered by the 80th event, guided Q4 2026,"* and being the site that says that precisely is exactly your differentiation versus the price-target blogs.

---

# 🔴 SEO — `/ticker/SLS` is not indexed, and "SLS" alone can't rank

**Verified live:** `site:pdufa.bio SLS` on Google returns only `/decisions` — **`/ticker/SLS` is not in the index.**

More telling, Google's own "People also search for" on that query returns: **SLS mortgage · SLS Dubai · SLS free toothpaste · Specialized Loan Servicing.** Google does not associate the bare token "SLS" with SELLAS Life Sciences at all.

**Root cause:** every ticker page is titled *"SLS FDA Calendar: PDUFA Dates & Decision History"* — ticker-only, no company name, no drug, no indication. There is nothing on the page for Google to bind to the biotech entity. This applies to all **208** ticker pages, and it compounds the thin-content problem (SLS page = 244 words).

**Fix — entity-rich templates:**
```
<title>SELLAS Life Sciences (SLS) FDA Catalysts: REGAL Phase 3 Readout Date &
       AML Pipeline | pdufa.bio</title>
<h1>SELLAS Life Sciences (SLS) — FDA catalysts &amp; readout calendar</h1>
```
Include in body text: full company name, lead asset(s) (galinpepimut-S / GPS, SLS009), indication (acute myeloid leukemia), trial name (REGAL), and NCT ID. Add `Organization` + `Dataset` JSON-LD with `tickerSymbol`, `alternateName`, and `sameAs` → company IR, Wikipedia/Wikidata, ClinicalTrials.gov. That's what lets Google resolve SLS → SELLAS rather than SLS → mortgage servicing.

---

# 🎯 The opportunity: retail is asking timing questions, and nobody good is answering them

Live Google SERP for **"SELLAS REGAL readout date"** — who ranks:
`ir.sellaslifesciences.com` · **Reddit r/sellaslifesciences ("Modeling REGAL readout date", 10+ comments)** · Yahoo Finance · Seeking Alpha · LARVOL · LucidQuest · Perplexity Finance.

**pdufa.bio ranks nowhere** — despite this being precisely the product.

Google's **"People also ask"** on that query:
- *When is the SLS Phase 3 readout?* ← **your exact product**
- How high could SLS stock go?
- What is the target price for Sellas stock?
- What is the price target for SLS in 2026?

**"People also search for":** SELLAS REGAL trial · REGAL trial AML · **SLS Phase 3 results date** · SELLAS Life Sciences Phase 3 · SELLAS interim analysis · SELLAS buyout update.

Retail is asking **"when is the readout"** and getting a Reddit modelling thread. That is an open goal for a site whose entire purpose is catalyst timing — and you can answer it *better* than the price-target blogs precisely because you won't publish a price target.

## Capture plan
1. **Answer the timing question explicitly on the page.** A short FAQ block on each ticker page with `FAQPage` JSON-LD (`/condition/cancer` already does this well — 1 FAQPage, 2 Q&A, and it's your best-performing page per GSC's "more impressions than usual"). For SLS: *"When is the SELLAS REGAL Phase 3 readout?"* → *"REGAL is event-driven; the final analysis triggers at the 80th event. 78 events had occurred as of May 11 2026; the company guides topline to Q4 2026 and will announce when the 80th event is reached."* Sourced, precise, no prediction.
2. **Lead with what you uniquely have:** cohort statistics. *"Micro-cap Phase 3 oncology readouts historically move ±X% on day one (n=…)"* — that's a differentiated answer to "how high could it go" that stays inside your no-probabilities rule.
3. **Explicit "no price target" positioning.** Two of the four PAA questions are price-target questions. Saying *"we don't publish price targets — here's the historical distribution instead"* is a credibility asset in a query set otherwise dominated by promotional content.

## Hot names to prioritise right now
| Ticker | Why it's hot | Site status | Action |
|---|---|---|---|
| **SLS** | #1 retail-voted biotech; REGAL readout pending | ticker page **not indexed**, false CRL, no REGAL record | Fix + enrich + index — highest urgency |
| **BMY / AZN** | **$400B AstraZeneca–BMS merger talks** reported Aug 2 (FT/Bloomberg/Reuters); AZN −8% on the news | both ticker pages live; **BMY PDUFA Aug 17** on calendar | Huge transient search volume — make sure BMY's Aug 17 PDUFA page is indexed and links to the ticker hub |
| **MRNA** | **PDUFA Aug 5** (mRNA-1010 flu) — 3 days out | on calendar, `/pdufa/MRNA` live | Ensure indexed *before* the decision; publish the decision same-day |
| **REPL** | RP1 AdComm 10–3 favorable; **PDUFA Aug 2** | AdComm on site; **PDUFA row still missing** (flagged 08-01) | Add the PDUFA record — decision is today |
| **CAPR** | Deramiocel AdComm 3–9 against; **PDUFA Aug 22** | correct on site ✓ | Well positioned — index the ticker page |
| **REGN** | Garetosmab BLA, Aug 2026 action date | on calendar | Index |
| **VKTX** | Viking obesity Phase 3 — high retail search | **no ticker page at all (404)** | Create |
| **IBRX / ONDS** | Named alongside SLS in retail sentiment polls | IBRX live; ONDS n/a (not biotech) | Index IBRX |

## The repeatable play
The pattern that wins here is **being early and precise on the catalyst that retail is already searching**:
1. Watch which tickers spike in retail attention (Stocktwits/WSB sentiment, unusual volume).
2. Ensure that ticker's page is **entity-rich, factually complete, and indexed** *before* the catalyst.
3. Publish the outcome **same-day with a primary source** — those are the pages that earn links and rank.
4. Never publish a price target or probability; answer with distributions and sample sizes. That's the moat.

---

# ⚠️ Indexing requests — blocked this session
The Search Console URL-inspection omnibox would not accept input this session (every submission bounced back to Overview; screenshots also returned CDP errors). This is a Chrome-extension failure, not a permissions problem. **No new indexing requests were submitted today.**

Queue to submit manually (2 minutes, or I can retry next session):
`/ticker/SLS` · `/pdufa/BMY` · `/ticker/BMY` · `/ticker/AZN` · `/pdufa/MRNA` · `/pdufa/REGN` · `/ticker/CAPR` · `/ticker/IBRX`
*(Submit `/ticker/SLS` only **after** the false-CRL fix — don't accelerate indexing of a page carrying a false regulatory claim.)*

---

# ✅ Confirmed improvements since yesterday
- **Event schema fixed and validating:** GSC Enhancements now reports **Events 14 valid / 2 invalid** (was "94% of items not eligible"). Breadcrumbs 26 valid/0 invalid; Datasets 3 valid/0 invalid.
- **Sitemap regenerated** — `lastmod` now **2026-08-02** (was stuck at Jul 24), and VTRS/OTLK/OTSKY/MRK decision pages are now included.
- **Correction to my 08-01 audit:** I reported "303 decision pages missing from the sitemap" as a bug. That was **mostly by design** — 308 price-only pages are deliberately excluded. The genuine gap was ~10 sourced pages, and the recent ones have since been added. My framing was wrong; the exclusion policy is sound.

# 📋 Still open from prior audits
`/tickers` A–Z hub → 404 · `/screener` still client-rendered (0 `<tr>`, 0 outbound links) · ticker pages 179–209 words · sitemap still flat (no index) · GSC still 36 indexed / 522 not / 478 "Discovered – currently not indexed" · **Core Web Vitals: "No data" on both mobile and desktop** (insufficient CrUX traffic — will resolve as traffic grows; not actionable yet).

---
*Verify every date and outcome against primary FDA / SEC / company filings. Not investment advice.*

**Sources**
- SELLAS REGAL status (78 events as of May 11 2026; Q4 2026 topline guidance; $107.1M cash) — [SELLAS Q1 2026 results](https://www.globenewswire.com/news-release/2026/05/12/3293399/0/en/sellas-life-sciences-reports-first-quarter-2026-financial-results-and-provides-corporate-update.html) · [SELLAS IR](https://ir.sellaslifesciences.com/news/News-Details/2026/SELLAS-Life-Sciences-Reports-First-Quarter-2026-Financial-Results-and-Provides-Corporate-Update/default.aspx)
- SLS009 Phase 2 primary endpoints met / FDA guidance — [SELLAS IR, Jul 2025](https://ir.sellaslifesciences.com/news/News-Details/2025/SELLAS-Meets-All-Primary-Endpoints-in-Phase-2-Trial-of-SLS009-in-rr-AML-and-Receives-FDA-Guidance-to-Advance-into-First-Line-Therapy-Study/default.aspx)
- Retail sentiment / meme dynamics — [Stocktwits](https://stocktwits.com/news-articles/markets/equity/sls-retail-prefer-sellas-ibrx-onds-pypl-bullish-pick/cZmleNCR7mO) · [StocksToTrade](https://stockstotrade.com/news/sellas-life-sciences-group-inc-sls-news-2026_07_22/)
- AstraZeneca–Bristol Myers $400B talks — [CNBC, Aug 2 2026](https://www.cnbc.com/2026/08/02/astrazeneca-and-bristol-myers-squibb-mull-400-billion-deal-report-.html) · [Bloomberg](https://www.bloomberg.com/news/articles/2026-08-02/astrazeneca-is-said-to-have-explored-bristol-myers-mega-merger) · [BioPharma Dive](https://www.biopharmadive.com/news/astrazeneca-bristol-myers-acquisition-rumors-deal-megamerger/826843/)
- Moderna mRNA-1010 PDUFA Aug 5 2026 — [24/7 Wall St.](https://247wallst.com/investing/2026/07/29/3-biotech-stocks-with-massive-upside-to-buy-in-august/)
