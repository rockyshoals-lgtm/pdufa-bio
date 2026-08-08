# pdufa.bio — MASTER BUILDER BRIEF
**Filed 2026-08-03 · Cowork session · Amendment 033 filing**
*Consolidates the 2026-07-30 → 2026-08-03 audit cycle into one actionable document.*
*All site measurements taken from live origin responses (`x-vercel-cache: MISS`, `age: 0`) — not CDN cache. Search Console data read live. Facts and historical statistics only — not investment advice.*

---

## HOW TO USE THIS DOC
Sections are ordered **P0 → P3 by impact**. Each item has: what's wrong · how I verified it · exactly what to change. Section 7 is the measurement plan. Section 8 credits what's already fixed so you don't redo it.

Two items (1.1 and 1.2) are **credibility/liability**, not SEO. Do those first regardless of roadmap.

---

# 1. P0 — CORRECTNESS

## 1.1 🔴 A false FDA Complete Response Letter is published for SELLAS (SLS)

**Live now:** `/fda-decision/SLS-2025-02-20` renders title *"SLS FDA Decision 2025-02-20: CRL"*, outcome **"✗ CRL"**. `/ticker/SLS` summarises: *"1 past FDA decision"* → *"Feb 20, 2025 ✕ CRL"*.

**This cannot be true.** A CRL is issued only in response to a submitted marketing application (NDA/BLA). **SELLAS has never filed one.** Lead asset galinpepimut-S (GPS) is in the Phase 3 REGAL trial (awaiting the 80th event); SLS009 is Phase 2. No FDA action date, no CRL, nothing in company IR or SEC filings.

**Provenance:** the page self-labels **"~ price-only (validating)"** with *"Validation: Outcome consistent with price; primary-source verification in pro."* The "CRL" was **inferred from a price pattern** (page shows T-120 run-up $0.84→$1.62, decision-day move +4.0%), not observed.

**Why urgent:** SLS is currently among the most-watched retail biotech tickers — WSB-driven rallies, −32% July, retail sentiment polls ranking it #1 bullish (50% of 3,400 votes vs ONDS 24%, IBRX 18%). A publicly-indexable page asserting "the FDA rejected this company's drug," about a company with no application pending, is disproportionate risk for a record of near-zero value.

**Do:**
1. Delete or `noindex` + retract `/fda-decision/SLS-2025-02-20`.
2. Remove "1 past FDA decision" from `/ticker/SLS`.
3. Log it on `/corrections` — you already market that page as a differentiator; this is exactly its purpose.

---

## 1.2 🔴 68% of the decisions archive is price-inferred but presented as verified fact

I scanned **all 450** live decision pages for the provenance marker:

| Provenance | Pages | Share |
|---|---:|---:|
| **"price-only" (inferred from price action)** | **308** | **68%** |
| Sourced (external primary-source link) | 142 | 32% |

The 142 sourced pages are genuinely good — VTRS→Viatris newsroom, OTLK→GlobeNewswire, MRK→FDA.gov, CELC→Celcuity IR, BIIB→Biogen IR.

**The problem is presentation, not the existence of a lower-confidence tier.** The 308 inferred pages carry definitive titles, definitive ✓/✗ glyphs, rows in `/decisions` visually identical to verified ones, and they feed the headline aggregate *"221 appr · 96 CRL · 70%"* — so a public statistic blends verified and inferred outcomes. The only disclosure is a small "~ price-only" note, with real verification gated behind Pro.

**Credit where due:** the sitemap **already excludes all 308** (0/308 in sitemap; 132/142 sourced included). The verification tier was a considered design. But the pages remain live, linked from `/decisions` (448 internal links), and therefore crawlable, indexable and AI-quotable.

**Do (pick one, in order of preference):**
1. **`<meta name="robots" content="noindex,follow">` on every price-only page.** Keeps them for navigation and Pro; removes them from search and AI citation. Consistent with the sitemap policy already adopted. ← recommended
2. Relabel visibly: title → *"SLS 2025-02-20 — unverified, inferred from price action"*; replace ✓/✗ with a neutral "unconfirmed" badge; add a banner. Never render unverified outcomes in the same visual language as verified ones.
3. Split headline stats so `/decisions` reports approvals/CRLs from **verified records only**, with inferred counts shown separately.

This directly serves the `/llms.txt` positioning — *"historical statistics only… we publish our own corrections."* Today the archive's dominant tier quietly undercuts that claim.

---

# 2. P0 — THE CRAWL BOTTLENECK (root cause found)

## 2.1 🔴 Google has not read your sitemap since **July 27**

**Search Console → Sitemaps, read live:**
> `https://www.pdufa.bio/sitemap.xml` · Type: Sitemap · Submitted **Jul 21, 2026** · **Last read: Jul 27, 2026** · Status: Success · **Discovered pages: 520**

Every sitemap improvement since Jul 27 is **invisible to Google** — the VTRS page being added, the `lastmod` refresh, the restructure (the file moved 520 → 429 URLs during the audit window).

**This explains the symptom that looked alarming:** URL Inspection on `/pdufa/BMY` and `/pdufa/REGN` returns **"URL is unknown to Google"** and **"No referring sitemaps detected"** — even though both **are** in the current sitemap. Google is simply working from a six-day-old copy.

**It is also the most plausible single contributor to the 478 "Discovered – currently not indexed."**

**Do — ping Google on every deploy.** Options, best first:
1. **Search Console API `sitemaps.submit`** in the deploy step (service-account auth) — the supported, reliable path.
2. **IndexNow** for Bing/Yandex — trivial POST of changed URLs; free coverage, no Google benefit.
3. Manual resubmit in GSC (what I did this session) — works, but not automatable.

At this authority level a static sitemap can go a week or more between reads. Without a ping, every fix you ship waits on Google's discretionary schedule.

*(I resubmitted `sitemap.xml` in GSC this session to force a re-read.)*

## 2.2 🔴 Indexation status — the number to move

| | Pages |
|---|---:|
| Indexed | **36** |
| Not indexed | **522** |
| ↳ **Discovered – currently not indexed** | **478** |
| ↳ Redirect error | 18 |
| ↳ Crawled – currently not indexed | 13 |
| ↳ Page with redirect | 6 |
| ↳ Not found (404) | 5 |
| ↳ Alternate page w/ proper canonical | 1 |
| ↳ Duplicate, Google chose different canonical | 1 |

**≈6.5% of the site is indexed.** What I ruled out: robots.txt is fine; all sitemap URLs return 200; `pdufa.bio` and `http://` both 308 → `https://www.pdufa.bio` correctly; canonicals correct; every page has one `<h1>` and a unique title. **The technical foundation is sound — this is a crawl-demand problem**, driven by §2.1 (stale sitemap reads), §3 (orphaned pages), §4 (thin content) and §6 (authority).

Manual "Request indexing" cannot fix 478 pages (~10/day quota). Keep it for changed high-value pages only.

---

# 3. P1 — INTERNAL LINK STRUCTURE

## 3.1 🔴 208 ticker pages (40% of the site) are effectively orphaned
Server-rendered `<a href>` links to `/ticker/*`, counted live:

| Page | total internal links | → `/ticker/*` |
|---|---:|---:|
| Homepage | 57 | **1** |
| `/calendar` | 78 | **0** |
| `/decisions` | 463 | **0** |
| `/screener` | 15 | **0** |
| `/condition/cancer` | 79 | **0** |

Reachable essentially only via the sitemap — which confers no link equity. Textbook "Discovered, not indexed." Contrast the group that *is* linked: `/decisions` emits **448** links to `/fda-decision/*`, and those are the pages Google actually indexes.

**Do:**
1. Build **`/tickers`** — an A–Z index (currently **404**), paginated ~50/page, plain anchors to all 208. Link from footer and `/screener`.
2. Cross-link both directions: every `/pdufa/{T}`, `/fda-decision/{T}-{date}`, and `/readouts` row → `/ticker/{T}`.
3. Related-ticker blocks (5–10 same-TA peers) on each ticker page.
4. Footer anchors to `/tickers`, `/developers`, `/research`, `/corrections` (homepage currently links `/about` **0** times, `/corrections` **0**).

Target: **every sitemap URL reachable within 3 clicks of the homepage via a server-rendered anchor.**

## 3.2 🔴 `/screener` is invisible to Googlebot
72KB, **zero `<tr>`**, 15 links, **zero** links to ticker/pdufa/decision pages. The table is client-rendered; Googlebot's HTML fetch sees a shell. Your highest-commercial-intent page passes **no** link equity.

`/calendar` proves you already do this right (78 server-rendered links, 54 to `/pdufa/*`).

**Do:** server-render the first 50–100 rows with real `<a href>` per row at build time; let JS take over sorting/filtering (progressive enhancement).

## 3.3 🟠 `/research` and `/developers` — your two best link magnets are dark
- `/research` → "Crawled – currently not indexed" (last crawl **Mar 30, 2026**; fetch OK, indexing allowed). Homepage links: **2**.
- `/developers` → "Discovered – currently not indexed", **never crawled**, **"Referring page: None detected."** Homepage links: **1**.

Both are `rel`-clean (no nofollow) — they're crawlable, just starved of internal equity. Painful because these are exactly the pages that *earn* links: original CC BY 4.0 research and a free no-key API.

**Do:** prominent in-content links (homepage hero → "Free API, no key" → `/developers`; every research page ↔ `/developers`); give each study its own indexable URL with `Dataset` + `ScholarlyArticle` JSON-LD; ensure both carry current `lastmod`.

**Note:** *every* page I inspected this session showed "Referring page: None detected" (MRNA, BMY, AZN, CAPR, REGN) despite real internal links — consistent with Google not having recrawled the linking hubs. Fixing §2.1 should improve this too.

---

# 4. P1 — CONTENT & ENTITY BINDING

## 4.1 🔴 Ticker pages can't rank — bare tickers don't resolve to companies
**Verified:** `site:pdufa.bio SLS` returns only `/decisions`. **`/ticker/SLS` is not indexed.**
More telling — Google's "People also search for" on that query: **SLS mortgage · SLS Dubai · SLS free toothpaste · Specialized Loan Servicing.** Google does not associate "SLS" with SELLAS at all.

**Cause:** every ticker page is titled *"SLS FDA Calendar: PDUFA Dates & Decision History"* — ticker-only. No company name, drug, or indication for Google to bind an entity to. Applies to all **208**.

**Do — entity-rich templates:**
```html
<title>SELLAS Life Sciences (SLS) FDA Catalysts: REGAL Phase 3 Readout Date
       & AML Pipeline | pdufa.bio</title>
<h1>SELLAS Life Sciences (SLS) — FDA catalysts &amp; readout calendar</h1>
```
Body must contain: full company name · lead assets (galinpepimut-S/GPS, SLS009) · indication (acute myeloid leukemia) · trial name (REGAL) · NCT ID.
Add `Organization` + `Dataset` JSON-LD with `tickerSymbol`, `alternateName`, `sameAs` → company IR, Wikidata, ClinicalTrials.gov.

*(Correction to my 08-01 playbook: I claimed ticker pages emit no JSON-LD. Verified false — they emit `BreadcrumbList` + `ItemList` + `ListItem`. The recommendation stands on entity binding + depth, not absence of schema.)*

## 4.2 🟠 Thin at scale
Measured visible word counts: `/ticker/*` **179–209 words** (208 pages) · `/fda-decision/*` ~314 (145) · `/pdufa/*` ~504 (77). Your thinnest group is your least-indexed group.

**Do:** target 400–600 words of *differentiated* content per ticker page — full decision history table (you have it), upcoming catalysts, cohort context from your own research ("micro-cap FDA decisions historically move ±7% on decision day, n=302"), short plain-English pipeline summary. **`noindex` any ticker with zero history *and* zero upcoming catalysts** — 120 strong pages beat 208 weak ones.

---

# 5. P1 — DATA COVERAGE GAPS

| Gap | Detail | Action |
|---|---|---|
| **SLS REGAL readout missing** | `/ticker/SLS` says *"no upcoming catalyst on file"* — but REGAL is the marquee small-cap readout. Event-driven Phase 3, GPS in AML maintenance after CR2; final analysis triggers at the **80th event**; **78 events as of 2026-05-11**; topline guided **Q4 2026**; NCT04229979. Plus SLS009 Phase 2 (met all primary endpoints, FDA guidance to first-line). | Add readout record at month/quarter precision with an explicit **"event-driven — not a fixed date"** flag. Ideal use of your confidence/precision fields. |
| **REPL PDUFA missing** | RP1 + nivolumab, FDA goal date **2026-08-02**. The AdComm (Jul 30, 10–3 favorable) is on-site; the PDUFA row is not. Flagged 08-01, still open. | Add it, **and fix the AdComm→PDUFA linkage** so an AdComm ingest always creates/confirms the matching PDUFA row — otherwise this recurs for every AdComm'd drug. |
| **VKTX has no page** | `/ticker/VKTX` → **404**. Viking Therapeutics is a top-searched obesity name. | Create. |
| **`/adcomm` heading** | Both entries sit under *"Scheduled meetings"* but are held with results. | Split "Upcoming" vs "Recent results". |

---

# 6. P2 — HOT-NAME CAPTURE (the growth play)

## 6.1 The demand is there and nobody good is serving it
Live SERP for **"SELLAS REGAL readout date"**: company IR · **Reddit r/sellaslifesciences ("Modeling REGAL readout date")** · Yahoo Finance · Seeking Alpha · LARVOL · LucidQuest · Perplexity Finance. **pdufa.bio ranks nowhere** — for a query that is literally your product.

Google **People-also-ask** on that query:
- ***"When is the SLS Phase 3 readout?"*** ← your exact product
- "How high could SLS stock go?" · "What is the target price for Sellas stock?" · "What is the price target for SLS in 2026?"

**People also search for:** SELLAS REGAL trial · REGAL trial AML · **SLS Phase 3 results date** · SELLAS Life Sciences Phase 3 · SELLAS interim analysis · SELLAS buyout update.

Retail asks *"when is the readout"* and gets a Reddit modelling thread.

## 6.2 How to take it
1. **Answer the timing question on the page**, with `FAQPage` JSON-LD. (`/condition/cancer` already does this — 1 FAQPage, 2 Q&A — and it's your best performer per GSC's "more impressions than usual" callout.) For SLS: *"When is the SELLAS REGAL Phase 3 readout?"* → *"REGAL is event-driven; final analysis triggers at the 80th event. 78 had occurred as of May 11 2026; the company guides topline to Q4 2026 and will announce when the 80th is reached."* Sourced, precise, no prediction.
2. **Answer "how high could it go" with distributions, not targets** — cohort move medians + IQR + n. Differentiated, and inside your no-probabilities rule.
3. **Say explicitly that you don't publish price targets.** Two of four PAA questions are price-target questions; refusing them credibly is an asset in a query set otherwise full of promotional content.

## 6.3 Priority names right now
| Ticker | Why | Site status | Action |
|---|---|---|---|
| **SLS** | #1 retail-voted biotech; REGAL pending | not indexed · false CRL · no REGAL record | Fix 1.1 → enrich → **then** index |
| **BMY / AZN** | **$400B AstraZeneca–BMS merger talks** (FT/Bloomberg/Reuters, Aug 2); AZN −8% | both live; **BMY PDUFA Aug 17** | Transient volume spike — indexed this session |
| **MRNA** | **PDUFA Aug 5** (mRNA-1010 flu) | live | Indexed this session; publish outcome same-day |
| **REPL** | AdComm 10–3 favorable; **PDUFA Aug 2** | **PDUFA row missing** | Add now (§5) |
| **CAPR** | AdComm 3–9 against; **PDUFA Aug 22** | correct ✓ | Indexed this session |
| **REGN** | Garetosmab, Aug action date | live | Indexed this session |
| **VKTX** | Obesity Phase 3, high retail search | **404** | Create |
| **IBRX** | Named alongside SLS in sentiment polls | live | Index |

## 6.4 The repeatable play
Watch retail attention spikes → ensure that ticker's page is **entity-rich, complete and indexed *before* the catalyst** → publish the outcome **same-day with a primary source** → never publish a price target or probability. Same-day sourced outcome pages are what earn links and rank.

---

# 7. MEASUREMENT

Re-check **GSC → Page indexing weekly**. The two numbers that matter:
- **"Discovered – currently not indexed" falling from 478**
- **Indexed rising from 36**

Expect movement 2–4 weeks after §2.1 + §3 ship. If "Discovered" doesn't budge after sitemap-ping + internal linking, the binding constraint is **authority**, not structure — at which point: Zenodo/OSF DOIs for the research, Wikipedia/Wikidata citations for PDUFA articles, a GitHub client library for the API, and pitching the free API to reporters covering FDA decisions. Avoid paid links entirely; a manual action would cost far more than the traffic is worth on a site whose credibility *is* the product.

**Also fix (cheap, affects measurement):**
- **Future-dated timestamps.** API `meta.as_of` was 2026-08-02 while the badge correctly read Aug 1; now the **sitemap `<lastmod>` contains 2026-08-03** on Aug 2. The daily job stamps from a rolled-over UTC date. Stamp from the same timezone the badge uses (America/New_York). `lastmod` is precisely the signal Google uses to prioritise recrawl — future dates undermine it.
- **Split the flat sitemap into a sitemap index** by type (`sitemap-pdufa.xml`, `-decisions.xml`, `-tickers.xml`, `-research.xml`) so GSC reports indexed/not-indexed **per section** — that's how you'll measure whether §3/§4 worked.
- **Core Web Vitals: "No data"** on mobile and desktop — insufficient CrUX traffic. Not actionable yet; will populate as traffic grows.

---

# 8. ✅ CONFIRMED FIXED (verified live — don't redo)

| Item | Verified state |
|---|---|
| robots.txt blocked the API `/llms.txt` advertises | **FIXED** — `Allow: /api/v1/` now precedes `Disallow: /api/` |
| API mirror lagged the pages | **FIXED** — VTRS `Decided/Approved dcd=2026-07-29` · OTLK `Decided/Approved dcd=2026-07-24` · CAPR `Held / "3-9 against"` |
| `meta.as_of` future-dated | **FIXED** at the time of check (now 2026-08-01, ET-based) — but see §7, it has resurfaced in the sitemap |
| `/decisions` sort + counter | **FIXED** — strict date-descending (VTRS 07-29 first), counter 131 |
| Event schema "94% not eligible" | **FIXED** — `/calendar` 40/40, `/readouts` 81/81, `/adcomm` 2/2 now carry time+TZ. **GSC Enhancements now: Events 14 valid / 2 invalid.** Breadcrumbs 26/0, Datasets 3/0 |
| VTRS Gwyn Lo publish | **FIXED** — detail page 200, homepage board leads with it, removed from upcoming |
| Sitemap regeneration | **FIXED** — `lastmod` current, recent decisions included (Google just hasn't re-read it — §2.1) |

**Accuracy spot-checks passed** (independent primary sources): CAPR CTGTAC **3 for / 9 against** — site renders "3–9 against" ✓. REPL CTGTAC **10–3 favorable** — site renders "10–3 favorable" ✓.

**My own corrections:** (a) my 07-30 note describing the CAPR vote as "9-3" was wrong — the site was right. (b) my 08-01 claim that "303 decision pages are missing from the sitemap" was mostly **by design** (price-only exclusion); the genuine gap was ~10 sourced pages, since added. (c) my 08-01 claim that ticker pages emit no JSON-LD was unverified and false.

---

# 9. INDEXING SUBMITTED (this cycle, all confirmed queued)
**2026-08-03:** `/pdufa/MRNA` · `/pdufa/BMY` · `/ticker/AZN` · `/pdufa/CAPR` · `/pdufa/REGN` · **sitemap.xml resubmitted for re-read**
**Earlier:** `/` · `/calendar` · `/decisions` · `/conferences` · `/readouts` · `/screener` · `/adcomm` · `/runup-by-year` · `/research` · `/research/conference-runup` · `/research/readout-reaction` · `/developers` · `/condition/cancer` · `/pricing` · `/methodology`

**Deliberately withheld:** `/ticker/SLS` — do not accelerate indexing of a page carrying a false regulatory claim. Submit **after** §1.1 ships.

---

# 10. BUILD ORDER

| # | Action | Section | Effort |
|---|---|---|---|
| 1 | Retract the false SLS CRL + log on `/corrections` | 1.1 | 15 min |
| 2 | `noindex` the 308 price-only decision pages; split headline stats | 1.2 | 1–2 hr |
| 3 | **Sitemap ping on every deploy** (GSC API `sitemaps.submit`) | 2.1 | 1 hr |
| 4 | Add REPL PDUFA + fix AdComm→PDUFA linkage; add SLS REGAL readout; create VKTX | 5 | half day |
| 5 | Entity-rich ticker titles/H1/JSON-LD (all 208) | 4.1 | 1 day |
| 6 | `/tickers` A–Z hub + server-render `/screener` rows | 3.1, 3.2 | 1 day |
| 7 | Thicken ticker pages; `noindex` empty ones | 4.2 | 1–2 days |
| 8 | FAQPage blocks on ticker pages (timing questions) | 6.2 | 1 day |
| 9 | Fix future-dated `lastmod`/`as_of`; split sitemap index | 7 | half day |
| 10 | Authority program | 7 | ongoing |

---
*Verify every date and outcome against primary FDA / SEC / company filings. Not investment advice.*

## Sources
- SELLAS REGAL status (78 events as of 2026-05-11; Q4 2026 topline guidance) — [SELLAS Q1 2026 results](https://www.globenewswire.com/news-release/2026/05/12/3293399/0/en/sellas-life-sciences-reports-first-quarter-2026-financial-results-and-provides-corporate-update.html) · [SELLAS IR](https://ir.sellaslifesciences.com/news/News-Details/2026/SELLAS-Life-Sciences-Reports-First-Quarter-2026-Financial-Results-and-Provides-Corporate-Update/default.aspx)
- SLS009 Phase 2 endpoints met / FDA guidance — [SELLAS IR, Jul 2025](https://ir.sellaslifesciences.com/news/News-Details/2025/SELLAS-Meets-All-Primary-Endpoints-in-Phase-2-Trial-of-SLS009-in-rr-AML-and-Receives-FDA-Guidance-to-Advance-into-First-Line-Therapy-Study/default.aspx)
- Retail sentiment / meme dynamics — [Stocktwits](https://stocktwits.com/news-articles/markets/equity/sls-retail-prefer-sellas-ibrx-onds-pypl-bullish-pick/cZmleNCR7mO) · [StocksToTrade](https://stockstotrade.com/news/sellas-life-sciences-group-inc-sls-news-2026_07_22/)
- CAPR CTGTAC vote 3–9 against — [AJMC](https://www.ajmc.com/view/fda-advisory-panel-votes-against-approval-of-deramiocel-for-dmd) · [FDA CTGTAC](https://www.fda.gov/advisory-committees/advisory-committee-calendar/cellular-tissue-and-gene-therapies-advisory-committee-july-29-2026-meeting-announcement-updated)
- REPL RP1 vote 10–3 favorable + FDA goal date Aug 2 2026 — [Replimune 8-K (SEC)](https://www.sec.gov/Archives/edgar/data/0001737953/000110465926088857/tm2621708d1_ex99-1.htm) · [Replimune PR](https://www.globenewswire.com/news-release/2026/07/30/3336537/0/en/replimune-announces-favorable-outcome-of-fda-s-cellular-tissue-and-gene-therapies-advisory-committee-meeting-for-rp1-in-advanced-melanoma.html)
- AstraZeneca–Bristol Myers $400B talks — [CNBC](https://www.cnbc.com/2026/08/02/astrazeneca-and-bristol-myers-squibb-mull-400-billion-deal-report-.html) · [Bloomberg](https://www.bloomberg.com/news/articles/2026-08-02/astrazeneca-is-said-to-have-explored-bristol-myers-mega-merger) · [BioPharma Dive](https://www.biopharmadive.com/news/astrazeneca-bristol-myers-acquisition-rumors-deal-megamerger/826843/)
- Viatris Gwyn Lo approval (2026-07-29) — [Viatris newsroom](https://newsroom.viatris.com/2026-07-29-Viatris-Receives-U-S-FDA-Approval-for-Gwyn-Lo-TM-,-a-Once-Weekly-Contraceptive-Patch)
