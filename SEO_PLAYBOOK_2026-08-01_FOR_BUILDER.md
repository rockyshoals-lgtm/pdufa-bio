# pdufa.bio — SEO & Crawl Growth Playbook + VTRS deploy verification
**For the builder — 2026-08-01**
*All numbers below were measured today from live pages, the live API, the live sitemap, and Google Search Console. Not investment advice.*

---

# PART A — VTRS deploy: shipped, with two follow-ups

## ✅ Landed
- `https://www.pdufa.bio/fda-decision/VTRS-2026-07-29` → **200**, correct title: *"VTRS FDA Decision (Jul 29, 2026): Gwyn Lo (norelgestromin/ethinyl estradiol) — Approved"*
- Homepage **"Recently decided" now leads with VTRS-2026-07-29** ✓, and VTRS is **correctly removed from "Next FDA decisions"** ✓
- Freshness badge: "Data through Aug 1" ✓

## 🔴 A1 — `/decisions` sorts VTRS *below* MNKD, and the year counter wasn't bumped
Rendered order on `/decisions` today:
```
MNKD  2026-07-24     ← 07-24 listed ABOVE 07-29
VTRS  2026-07-29     ← should be first
OTLK  2026-07-24
OTSKY 2026-07-24
```
Counter still reads **`2026 · 128`** — should be **129** now that VTRS is added.

**Why it matters beyond cosmetics:** `build_home_board.py::load_decisions()` parses `/decisions/index.html` top-down and sorts by date, so the homepage board self-corrects — but the archive page itself is the canonical human/crawler view, and an out-of-order "newest first" list undermines the freshness signal on your single best internal-linking hub (see B3 — `/decisions` emits 448 internal links).
**Fix:** insert new decision rows in date-descending position (VTRS above MNKD) and bump the `<div class="mhead">2026 · N</div>` counter in the same edit. Consider generating that page from the dataset rather than hand-inserting, so ordering and count can't drift.

## 🔴 A2 — The API mirror did **not** ship (this is the item from the last two audits, still open)
Live `/api/v1/events` right now:

| Ticker | API says | Truth (rendered site + primary source) |
|---|---|---|
| VTRS | `date 2026-07-30, status "Awaiting", outcome null` (upd 07-30T22:08Z) | **Approved 2026-07-29** (Gwyn Lo) |
| OTLK | `status "Awaiting", outcome null` | **Approved 2026-07-24** (LYTENAVA) |
| CAPR | `status "Scheduled", outcome null` (upd 07-11) | AdComm **held 07-29, voted against** |

The page-side of the VTRS publish shipped but the `dataset.mjs` record didn't. Net effect: the site is right, the machine-readable feed is wrong for all three — and that feed is what `/llms.txt` hands to AI assistants (see B1).
**Fix:** update `pdufa_site_src/api/v1/dataset.mjs` for VTRS (`st:"Decided"`, `oc:"Approved"`, `dcd:"2026-07-29"`, bump `ua`), and back-fill OTLK + the CAPR AdComm. Then make the manual/AdComm publish path write the API record **in the same commit** as the page — that's the durable fix; this bug has now recurred three times.

## 🟡 A3 — `meta.as_of` is future-dated
API reports `as_of: 2026-08-02` while today is Aug 1 and the on-page badge correctly says "Aug 1." The daily job (12:00/21:00 UTC) appears to stamp from a UTC date that has already rolled over. Stamp `as_of` from the same timezone the badge uses (America/New_York) so the feed never advertises tomorrow's data.

---

# PART B — SEO: the real diagnosis

## The one number that reframes everything
Google Search Console → Page indexing, today:

| | Pages |
|---|---:|
| **Indexed** | **36** |
| **Not indexed** | **522** |

Breakdown of the 522:
| Reason | Pages |
|---|---:|
| **Discovered – currently not indexed** | **478** |
| Redirect error | 18 |
| Crawled – currently not indexed | 13 |
| Page with redirect | 6 |
| Not found (404) | 5 |
| Alternate page with proper canonical | 1 |
| Duplicate, Google chose different canonical | 1 |

**≈6.5% of the site is indexed.** And the dominant bucket — 478 pages — is *"Discovered, currently not indexed,"* which means **Google knows these URLs exist (it read them from your sitemap) and has decided not to spend crawl budget fetching them.** They have never been crawled.

**This is the critical insight: your problem is not discovery, and it is not a technical block.** I verified:
- `robots.txt` allows everything relevant; `Allow: /`
- All **520/520 sitemap URLs return HTTP 200** (no redirect/404 rot in the sitemap)
- `https://pdufa.bio` and `http://` both **308 → `https://www.pdufa.bio`** correctly; canonicals present and correct on every page I sampled
- Every page sampled has exactly one `<h1>`, a unique title, and a meta description

The technical foundation is genuinely good. **What's missing is crawl demand** — Google's willingness to spend budget on the site. Crawl demand is driven by (1) internal link structure, (2) external authority, (3) content uniqueness/depth, (4) freshness signals. All four have specific, fixable gaps below.

**Corollary that matters for how you spend time:** manually clicking "Request indexing" cannot fix this. That's ~10 URLs/day against a 478-page backlog, and it treats the symptom. I've been submitting them (20 URLs over three sessions, all confirmed queued) and it's worth continuing for *changed high-value pages*, but the structural fixes below are what actually move 478 pages.

---

## B1 🔴 `robots.txt` blocks the very API that `/llms.txt` advertises
`/llms.txt` explicitly invites AI assistants to use the API and names these endpoints:
`/api/v1/events`, `/api/v1/pdufa`, `/api/v1/readouts`, `/api/v1/adcomm`, `/api/v1/conferences`

But `robots.txt` says:
```
Disallow: /api/
```
Every well-behaved AI crawler (GPTBot, ClaudeBot, PerplexityBot, Google-Extended) reads robots.txt first and **will not fetch those endpoints.** You are simultaneously telling AI systems "here is our free, no-key API, please quote it" and "you may not fetch it."

**Fix — allow the read-only v1 endpoints while keeping the rest of `/api/` closed:**
```
User-agent: *
Allow: /api/v1/
Disallow: /api/
```
(`Allow` of a longer path wins over `Disallow` in Google/Bing's matching rules.) Then confirm with GSC's robots.txt tester. This is a genuinely high-leverage fix: your whole AEO/"be quotable by AI" strategy in `/llms.txt` is currently self-blocked, and AI answer surfaces are exactly where a free, structured, primary-sourced catalyst dataset should win.

---

## B2 🔴 208 ticker pages — 40% of the site — are effectively orphaned
`/ticker/*` is your single largest URL group (208 of 520 sitemap URLs). I counted real, server-rendered `<a href>` links to them from your main hubs:

| Page | total internal links | → `/ticker/*` |
|---|---:|---:|
| Homepage | 57 | **1** |
| `/calendar` | 78 | **0** |
| `/decisions` | 463 | **0** |
| `/screener` | 15 | **0** |
| `/condition/cancer` | 79 | **0** |

**They are reachable essentially only via the sitemap.** A sitemap is a *hint*, not an endorsement — it confers no link equity. That is textbook "Discovered – currently not indexed," and it almost certainly accounts for the bulk of the 478.

Compare with the group that *is* well-linked: `/decisions` emits **448** links to `/fda-decision/*`, and decision pages are the part of the site Google actually indexes and shows.

**Fix — build real hub pages with server-rendered anchors:**
1. **`/tickers` A–Z index** (paginated ~50/page, or grouped A–E, F–J…): plain `<a href="/ticker/VTRS">VTRS — Viatris</a>` links to all 208. Link it from the footer and from `/screener`.
2. **Cross-link from event pages:** every `/pdufa/{T}`, `/fda-decision/{T}-{date}` and `/readouts` row should link to `/ticker/{T}`. You already link the other direction; make it bidirectional.
3. **Related-ticker blocks:** on each ticker page, link 5–10 peers in the same therapeutic area. This creates lateral link paths so crawl equity flows across the group rather than dead-ending.
4. **Footer hub links** to `/tickers`, `/developers`, `/research`, `/corrections` as plain anchors.

Target: **every URL in the sitemap reachable within 3 clicks of the homepage** via a server-rendered anchor.

---

## B3 🔴 `/screener` is invisible to Googlebot
`/screener` is 72KB but contains **zero `<tr>` rows and zero internal links** — the table is built client-side by JS from the data file. Googlebot's initial HTML fetch sees an empty shell. It's indexed on its title/description alone, and — worse — it passes **no link equity at all** to the ticker/event pages it displays.

Your `/calendar` page proves you already know how to do this right: 78 server-rendered links including 54 to `/pdufa/*`.

**Fix:** server-render the screener's first page of rows (50–100) into the HTML at build time, with real `<a href>` per row, and let JS take over for sorting/filtering (progressive enhancement). This converts your highest-intent commercial page from an SEO dead-end into a major internal-link hub. Same audit applies to any other JS-only view — check `/app`, `/today` (both robots-disallowed, fine) and any tab-driven sections.

---

## B4 🟠 Thin, templated content at scale
Measured visible word counts:

| Page type | Words | Count |
|---|---:|---:|
| `/ticker/*` | **~190** | 208 |
| `/fda-decision/*` | ~314 | 145 |
| `/pdufa/*` | ~504 | 77 |

208 near-identical ~190-word pages is a pattern Google routinely declines to index — it reads as templated scale rather than unique value. Note the correlation: your *thinnest* group is your *least* indexed group.

**Fix — make ticker pages genuinely useful (target 400–600 words of real, differentiated content):**
- Full decision history table for that ticker (you have it: approvals, CRLs, dates, outcomes) with links to each `/fda-decision/` page
- Upcoming catalysts (PDUFA/readout/AdComm/conference) with dates
- Cohort context: "Micro-cap FDA decisions historically move ±7% on decision day (n=302)" — your own research, with the sample size, which is your differentiator
- A short plain-English summary of what this company has pending
- `BreadcrumbList` + `Dataset` JSON-LD (ticker pages currently emit none)

Rule of thumb: if a page can't say something the other 207 can't, it shouldn't be a separate indexable URL. Any ticker with zero history *and* zero upcoming catalysts should be `noindex`ed (or excluded from the sitemap) until it has an event — better 120 strong pages than 208 weak ones.

---

## B5 🟠 Event schema: 94% of items ineligible for rich results
GSC Overview states verbatim: **"Events: 94% of your items aren't eligible for rich results."** Per page: `/calendar` **54 invalid**, `/readouts` **150 invalid**, `/adcomm` **2 invalid**, while `/conferences` is **14 valid**.

Root cause (consistent across all three failing pages): PDUFA/readout/AdComm `Event` objects emit a **date-only `startDate`** plus a `VirtualLocation`. Google's Event type requires a datetime with timezone to be rich-result eligible.

**Fix:**
```json
"startDate": "2026-08-17T00:00:00-04:00",
"eventAttendanceMode": "https://schema.org/OnlineEventAttendanceMode",
"location": { "@type": "VirtualLocation", "url": "https://www.pdufa.bio/pdufa/BMY" }
```
For rows with only a month-level estimate, either use the first of the month with a clear `"eventStatus"`, or demote to `WebPage` (your `/calendar` already demotes 14 undatable rows to `WebPage` — extend that pattern). This clears ~206 items and unlocks date-chip rich results on your two biggest hub pages. `/conferences` already passes, so the emitter fix is scoped and provable.

---

## B6 🟠 `/research` and `/developers` — your two best link magnets aren't indexed
- **`/research`** → "Crawled – currently not indexed" (last crawl **Mar 30, 2026**; fetch successful, indexing allowed — Google crawled it and declined). Only 2 internal links from the homepage.
- **`/developers`** → "Discovered – currently not indexed", **never crawled** (Last crawl: N/A), **"Referring page: None detected."** Only 1 homepage link, and it isn't registering as a referring page.

This is painful because these are precisely the pages that *earn* links: original event-study research (CC BY 4.0) and a free, no-key API. They're your authority engine and they're dark.

**Fix:**
1. Verify both links are plain server-rendered `<a href>` in the static HTML — not JS-injected, not inside a `<button>`/`onclick`, no `rel="nofollow"`. GSC reporting "None detected" for `/developers` strongly suggests the nav "API" link isn't being seen as a crawlable link.
2. Add prominent in-content links: homepage hero → "Free API, no key" → `/developers`; every research page → `/developers`; `/developers` → each research page.
3. Give each research study its own indexable URL with `Dataset` + `ScholarlyArticle` JSON-LD (`/research/conference-runup` and `/research/readout-reaction` already carry valid Breadcrumbs + Datasets — extend to all studies).
4. Add `lastmod` for both in the sitemap and keep it current.

---

## B7 🟡 Sitemap: freshness + structure
- Newest `<lastmod>` in the sitemap is **2026-07-24** — a week stale, even though decisions changed since (VTRS shipped today). Google uses `lastmod` to prioritize recrawl; a stale one tells Google "nothing changed, don't bother."
- It's a **single flat file of 520 URLs.** At this size that's tolerable, but a **sitemap index** split by type (`sitemap-pdufa.xml`, `sitemap-decisions.xml`, `sitemap-tickers.xml`, `sitemap-research.xml`) gives you per-section indexed/not-indexed reporting in GSC — which is how you'd *measure* whether the ticker-page fix in B2/B4 is working.

**Fix:** regenerate `lastmod` per URL on every build from actual file mtime/content hash; split into a sitemap index; keep `Sitemap:` in robots.txt pointing at the index. Also consider **IndexNow** (Bing/Yandex; trivial to POST changed URLs on deploy) — it won't help Google, but it's free coverage.

---

## B8 🟢 Authority — the thing no technical fix substitutes for
478 pages sitting uncrawled is ultimately a statement about site authority. 39 total web-search clicks in the last 3 months is a very small footprint, and crawl budget scales with perceived importance. The good news: you have unusually linkable assets most data sites don't.

**Highest-yield, in order:**
1. **Publish the research as citable datasets.** You already release CC BY 4.0 with sample sizes and published limitations — that's a genuinely strong, rare posture. Put each study on Zenodo/OSF with a DOI and link back. Academic/data citations are durable authority.
2. **Wikipedia/Wikidata**: PDUFA, Prescription Drug User Fee Act, and biotech-catalyst articles legitimately need a free, citable calendar reference. Follow their sourcing rules; don't spam.
3. **r/biotech, r/investing, Biotech Twitter/X**: your counter-intuitive findings are natively shareable — *"the conference run-up is a 2020 artifact"* and *"nano-cap presenters are the worst cohort, not the best"* are exactly the kind of claims that get linked and argued with. Lead with the finding, not the product.
4. **Pitch the data to journalists** covering FDA decisions (Endpoints, STAT, Fierce). A free, no-key API with a clean calendar is a reporter's tool; reporters link tools.
5. **Be the canonical source in AI answers** — fix B1 first, then `/llms.txt` does real work. Being quoted by ChatGPT/Perplexity increasingly drives direct traffic and secondary citations.
6. **HARO/Qwoted** for FDA-calendar questions; **GitHub** — publish the client library / dataset loader for the API; developer repos earn links and `/developers` traffic.

Avoid: paid link schemes, directory spam, PBNs. With a site whose credibility *is* the product, a manual action would be far more costly than the traffic is worth.

---

# Priority order (impact ÷ effort)

| # | Action | Why | Effort |
|---|---|---|---|
| 1 | **Fix `robots.txt` to allow `/api/v1/`** (B1) | Unblocks your entire AI-citation strategy; 2-line change | 5 min |
| 2 | **Ship the API mirror**: VTRS + OTLK + CAPR (A2) | Correctness; feed contradicts the site for 3 events | 30 min |
| 3 | **Fix `/decisions` sort + counter** (A1) | Freshness signal on your best link hub | 15 min |
| 4 | **Event `startDate` time+TZ** (B5) | Clears ~206 invalid items; rich results on 2 biggest pages | 1 hr |
| 5 | **Server-render `/screener` rows + `/tickers` A–Z hub** (B2, B3) | Attacks the 478 directly; converts dead pages into hubs | 1 day |
| 6 | **Thicken ticker pages; `noindex` empty ones** (B4) | Turns 208 thin pages into indexable assets | 1–2 days |
| 7 | **Internal links + sitemap `lastmod`/index** (B6, B7) | Gets `/research` + `/developers` crawled; enables measurement | half day |
| 8 | **Authority program** (B8) | The only durable fix for crawl budget | ongoing |

**Measurement:** re-check GSC Page indexing weekly. The number to watch is **"Discovered – currently not indexed" falling from 478**, and **Indexed rising from 36**. If items 5–7 work, you should see movement within 2–4 weeks. If "Discovered" doesn't budge after the internal-linking fix ships, the constraint is authority (B8), not structure.

---

## Indexing requested by me so far (all confirmed queued in GSC)
`/` · `/calendar` · `/decisions` · `/conferences` · `/readouts` · `/screener` · `/adcomm` · `/runup-by-year` · `/research` · `/research/conference-runup` · `/research/readout-reaction` · `/developers` · `/condition/cancer` · `/pricing` · `/methodology`

---
*Facts and historical statistics only. Not investment advice. Verify every date and outcome against primary FDA / SEC / company filings.*
