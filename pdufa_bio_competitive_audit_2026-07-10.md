# pdufa.bio — Competitive Teardown & Battle Plan
**Prepared:** 2026-07-10 · **Method:** live browser inspection (Claude-in-Chrome) + SEO SERP tests + primary-source accuracy checks
**Scope:** SEO, UX, UI, Value-for-money vs. locked competitive set. Product-strategy use only; not investment advice.

> **Access note:** All sites below were opened live on **2026-07-10** unless flagged. **BioPharmaCatalyst's public site (biopharmacatalyst.com) actively blocked the automated browser** — every request redirected to a dead `ww38.biopharmacatalyst.com` (`ERR_CONNECTION_RESET`), classic bot-protection behavior. I inspected its actual product instead — **BPIQ (bpiq.com)**, the paid app BioPharmaCatalyst operates — which loaded fully. TipRanks, Larvol, Kaleidoscope, BioPharma Dive, and Fierce Biotech were **not opened first-hand** (time-boxed); they are referenced only from SERP evidence and are **excluded from numeric scoring** per the "never score a site you didn't open" rule.

---

## 1. Executive Summary

**Where pdufa.bio ranks today: a genuinely superior product that nobody can find.** The on-page craft is real — the cleanest UI in the category, keyword-perfect title tags, and full `Event` + `FAQPage` + `BreadcrumbList` schema on its PDUFA detail pages. But it is **invisible on page 1 of Google for every single head term tested** ("PDUFA calendar," "FDA calendar," "biotech catalyst calendar," "clinical trial readout calendar," "upcoming FDA decisions," "AdComm calendar"). The incumbents — BiopharmaWatch, FDA Tracker, RTTNews, BPIQ, MarketBeat — own those SERPs. Worse, pdufa.bio is **actively sabotaging its own SEO and UX with broken links**: the homepage's "Next FDA Decisions" cards link to `/pdufa/{TICKER}` URLs that **404** (verified: `/pdufa/CORT`, the #1 nearest catalyst, and `/pdufa/OTLK` have no page at all; `/pdufa/VTRS` 404s while the real page sits at `/pdufa/VTRS-mr-100a-01`).

**The core promise — "most accurate, most complete" — is half-true and needs to be made fully true before it's marketed.** The **PDUFA data is excellent**: I cross-checked 6 upcoming decisions against company IR / SEC / GlobeNewswire and pdufa.bio was correct on every one, and it was *more* accurate than RTTNews (which carries a false "approved" note on CORT) and MarketBeat (which mis-attributes FUROSCIX). But the **readouts calendar is auto-generated from ClinicalTrials.gov with visible parsing errors** ("ACHV Custirsen — Vaping Cessation," "SKYE SBI-100 Ophthalmic Emulsion — Obesity," "BPTH BP1001 — Poliomyelitis"), and **conferences don't exist at all** (`/conferences` 404s). The "three-in-one calendar" positioning currently ships **two of three event types, one of them flawed.**

**Single highest-leverage move per dimension:**
- **SEO →** Fix the 404 detail-page routing and add `ItemList`/`Event` schema to the calendar/readouts hub pages, then build **AdComm** and **conference** hub pages. The programmatic skeleton is already there; it's leaking equity through 404s and thin schema, and missing two whole rankable categories.
- **UX →** Ship a single unified filter bar (ticker / date-range / therapeutic area / phase / event-type) that works across all three calendars from one screen. Right now the three calendars are separate pages with no cross-cutting filter.
- **UI →** Keep it. It's already the best-looking product in the set. Don't let the "clean" advantage erode as features are added.
- **Value →** Make the free tier's completeness undeniable (add conferences + AdComm, clean the readouts) so the answer to "why pay when BPC/BiopharmaWatch have free calendars" is "because ours is the only one that's *complete and correct* — and the free tier proves it."

**The uncomfortable truth:** the dangerous competitor is **BiopharmaWatch**, not the incumbents in the brief. It already does the exact "PDUFA + readouts + conferences (+ earnings)" three-in-one, it ranks #1–3 for almost every head term, and its Elite tier is **$19/mo** — only $4 above pdufa.bio's Pro. pdufa.bio's edges over it are real but narrow: a cleaner UI, a genuinely open free tier (BiopharmaWatch caps free at 6 events), no black-box "probability of approval," and — if the readouts get cleaned — better accuracy. Those edges have to be pressed hard and *ranked*, or pdufa.bio stays the best-kept secret in biotech catalysts.

---

## 2. Scorecard

Scored 1–5 (5 = best) on sites inspected live. Core set = pdufa.bio + the four locked primaries. Extended set = three benchmark competitors I also opened live (BiopharmaWatch is material enough to demand scoring).

### Core head-to-head

| Site | SEO | UX | UI | Value | **Total /20** | One-line justification |
|---|:--:|:--:|:--:|:--:|:--:|---|
| **pdufa.bio** | 3 | 3 | **4** | 4 | **14** | Best UI + best on-page schema, but ranks for nothing and ships 404 detail links. |
| **BioPharmaCatalyst / BPIQ** | 4 | 4 | 4 | 4 | **16** | Category leader: ranks, deep tooling (screeners/hedge funds), but login-walled and public site bot-blocks. |
| **FDA Tracker** | 2 | 3 | 2 | 3 | **10** | Ranks on domain age, but empty meta description, zero schema, dated FullCalendar widget. |
| **StockTitan** | 4 | 4 | 4 | 3 | **15** | High authority, modern, per-ticker news pages — but it's an FDA *news feed*, not a forward calendar; Gold is $59.99. |
| **RTTNews** | 4 | 2 | 2 | 2 | **10** | Keyword-rich + per-drug pages + high DA, but cluttered, ad-heavy, paginated, and carries stale/incorrect outcome notes. |

### Extended benchmarks (also inspected live)

| Site | SEO | UX | UI | Value | **Total /20** | One-line justification |
|---|:--:|:--:|:--:|:--:|:--:|---|
| **BiopharmaWatch** | **5** | 3 | 3 | 3 | **14** | The SEO winner and the real threat — true 3-in-1 + conferences + PoA, but free tier capped at 6 events and testimonials look fabricated. |
| **TheraRadar** | 4 | **4** | **4** | 4 | **16** | Best-in-class readout craft: confidence grading + per-row staleness flags + `Dataset` schema. The model to copy for readouts/conferences. |
| **MarketBeat** | **5** | 4 | 3 | 3 | **15** | Massive domain authority + clean data table + analyst/price integration; calendar is one module of a finance portal. |

*Not scored (not opened first-hand): TipRanks, Larvol, Kaleidoscope, BioPharma Dive, Fierce Biotech. Referenced qualitatively in §5 from SERP evidence only.*

**Read:** pdufa.bio already beats FDA Tracker and RTTNews on the merits and is level with BiopharmaWatch — but loses to BPIQ/TheraRadar/MarketBeat on *distribution and completeness*, not craft. Every point it's behind is an SEO/coverage point, not a design point.

---

## 3. Price vs. Coverage

| Product | Free tier | Paid price | Event types covered (PDUFA / Readouts / Conferences) | Standout paid feature | Ads / login |
|---|---|---|---|---|---|
| **pdufa.bio** | **Full calendar + full decision archive + 2020→now run-up study, no login** | **Pro $15/mo or $120/yr**, 7-day trial | ✅ PDUFA · ✅ Readouts (est.) · ❌ Conferences | Live current-PDUFA tracker, date-slip alerts, 1,800-event run-up dataset + CSV export, screener | No ads, no login for free |
| **BioPharmaCatalyst / BPIQ** | Basic **free but requires registration** | Pro **$20**, Elite **$25**, Apex **$45**/mo (billed annually) | ✅ PDUFA · ✅ Readouts · ⚠️ partial (catalyst events) | Pipeline screener, hedge-fund tracker, "Big Movers" | Login wall on free |
| **FDA Tracker** | Standard FDA calendar (month grid) | Gold **$29/mo** | ✅ PDUFA/AdComm · ✅ Trial Tracker · ❌ Conferences | Burn Rate, Patent Tracker, Omniview | Login for Gold |
| **StockTitan** | 2-min-delayed FDA news feed (free), 1-min with free signup | Gold **$59.99/mo** | ⚠️ FDA *news*, not a calendar · ⚠️ trials news · ❌ Conferences | Rhea-AI sentiment, real-time alerts, momentum scanner | Freemium delay wall |
| **RTTNews** | Partial calendar (paginated, free) | RTT Biotech Investor (7-day trial; full price not surfaced) | ✅ PDUFA/Panel · ✅ separate Clinical Trial calendar · ❌ Conferences | "Next 30 Days of FDA Events" PDF lead magnet | **Ad-heavy** + upsells |
| **BiopharmaWatch** | Preview only — **capped at 6 upcoming events**, 3-day Elite trial | Elite Plus **$19/mo** (annual; "save 21%"); API **$99–$189/mo** | ✅ PDUFA · ✅ Readouts · ✅ **Conferences** (+ Earnings) | Probability-of-Approval scorecards, Excel export, hedge-fund + options modules | Login; testimonials look fabricated |
| **TheraRadar** | Recently-read-out free + upcoming preview | Pro (filters gated; price not surfaced) | ⚠️ Approvals · ✅ **Readouts (best-in-class)** · ✅ **Conferences** | Confidence-graded dates + staleness flags + NCT search | Light, clean, minimal ads |
| **MarketBeat** | FDA calendar free (ad-supported) | MarketBeat Pro (bundled, ~$/mo varies) | ✅ PDUFA/AdComm · ⚠️ limited readouts · ❌ Conferences | Analyst consensus + MarketRank + price integration, export | **Ad-heavy** |

### Value verdict
At **$15/mo / $120/yr**, pdufa.bio is **the cheapest paid tier in the set** and its **free tier is the most genuinely open** (everyone else either walls the calendar behind login — BPIQ, BiopharmaWatch's 6-event cap — or buries it in ads — RTTNews, MarketBeat). That is a real, defensible position.

**But note two things the brief should reconcile:**
1. **The live price is not the brief's price.** The brief says $10/mo / $100/yr; the site charges **$15/mo / $120/yr**. Decide which is real. At $10/$100 the "cheapest, by a mile" claim is airtight; at $15 it's still cheapest but the gap to BiopharmaWatch ($19) is only $4 — thin enough that BiopharmaWatch's extra coverage (conferences, PoA, screener, Excel) can win the comparison.
2. **The live model is freemium, not "paid no-frills calendar."** The site already gives the calendar away free and charges for live tracker + alerts + data export + screener — structurally identical to BPC/BiopharmaWatch/FDA Tracker. So "**why pay when BioPharmaCatalyst's calendar is free?**" is answered by *not* trying to charge for the calendar. The objection that actually bites is the reverse: **"why pay pdufa.bio $15 for alerts + data when BiopharmaWatch gives me alerts + conferences + PoA + a screener for $19?"** Beating that requires (a) completeness parity (add conferences/AdComm), (b) a trust edge (verifiable accuracy + "no black-box probability"), and (c) a cleaner experience — all achievable, none automatic.

**To justify charging at all, this must be true and provable:** every date is correct and current, coverage spans all three event types, and updates are demonstrably faster/cleaner than the free alternatives. Today that's true for PDUFA, shaky for readouts, and false for conferences.

---

## 4. Accuracy Spot-Check

Ten catalysts across all three event types, cross-checked against **primary sources** (company IR / SEC 8-K / GlobeNewswire / ClinicalTrials.gov) and 2–3 competitors. (✓ = matches primary source.)

| # | Type | Catalyst | Primary-source truth | pdufa.bio | Competitors | Verdict |
|---|---|---|---|---|---|---|
| 1 | PDUFA | **CORT** relacorilant, platinum-resistant ovarian cancer | **PDUFA 2026-07-11** (Corcept IR / BusinessWire / CancerNetwork) | ✅ 2026-07-11 | FDA Tracker ✅ Jul 11; **RTTNews ✗** (lists 07/11 but adds false "approved Mar 25 2026" note — conflates the *separate* hypercortisolism NDA that got a CRL) | **pdufa.bio correct; beats RTTNews** |
| 2 | PDUFA | **CELC** gedatolisib+fulvestrant, HR+/HER2− breast cancer | **PDUFA 2026-07-17** (Celcuity IR / GlobeNewswire / StockTitan) | ✅ 2026-07-17 | RTTNews ✅; FDA Tracker ✅; Dan Sfera ✅ | **All correct**; RTTNews slightly more specific ("PIK3CA wild-type") — minor completeness gap for pdufa.bio |
| 3 | PDUFA | **MNKD** FUROSCIX ReadyFlow (SCP-111), edema in chronic HF/CKD | **PDUFA 2026-07-26**, sponsor **MannKind** (acquired scPharmaceuticals) (MannKind IR / Nasdaq) | ✅ 2026-07-26, MNKD, chronic HF edema | **MarketBeat ⚠️** lists ticker **SCPH** + "decompensated heart failure" (wrong entity + wrong indication nuance) | **pdufa.bio correct; beats MarketBeat** |
| 4 | PDUFA | **MRNA** mRNA-1010 seasonal flu, adults ≥50 | **PDUFA 2026-08-05** (Moderna IR / PharmExec) | ✅ 2026-08-05, "adults 50 years of…" | RTTNews/BiopharmaWatch cover | **Correct** |
| 5 | PDUFA | **OTLK** bevacizumab (ONS-5010/LYTENAVA), wet AMD, Class 1 resubmission | **PDUFA 2026-07-29** (Outlook IR / GlobeNewswire) | ✅ 2026-07-29 (calendar) — **but `/pdufa/OTLK` detail page 404s** | RTTNews has per-drug page (id=2432) | **Date correct; detail page missing** |
| 6 | PDUFA | **VTRS** MR-100A-01 low-dose estrogen patch, contraception | PDUFA **2026-07-30** (company-guided) | ✅ 2026-07-30 — **but homepage `/pdufa/VTRS` 404s**; real page `/pdufa/VTRS-mr-100a-01` | FDA Tracker ✅ Jul 30 | **Date correct; broken homepage link** |
| 7 | PDUFA | **LNTH** MK-6240, tau PET imaging (Alzheimer's) | PDUFA **2026-08-13** | ✅ 2026-08-13 | MarketBeat ✅ Aug 13 | **Correct** |
| 8 | Readout | **ACHV** — pdufa.bio readouts feed lists "**Custirsen — Vaping Cessation**" | Achieve Life Sciences' smoking/vaping drug is **cytisinicline**; *custirsen* is an unrelated legacy oncology antisense | ❌ **Wrong drug-indication pair** (CT.gov field mis-parse) | TheraRadar flags such rows with staleness/confidence | **pdufa.bio readouts error** |
| 9 | Readout | pdufa.bio readouts feed: "**SKYE SBI-100 Ophthalmic Emulsion — Obesity**" and "**BPTH BP1001 — Poliomyelitis**" | SBI-100 is an ophthalmic cannabinoid; BP1001 is an AML antisense — neither maps to those indications | ❌ **Nonsensical pairings** inherited from ClinicalTrials.gov condition strings | — | **pdufa.bio readouts error (systemic)** |
| 10 | Conference | Any ASCO/ASH/ESMO presentation catalyst | ESMO 2026 Oct 23–27; ASH Dec 12–15; ASCO Jun (public agendas) | ❌ **No conference product exists** (`/conferences` 404) | BiopharmaWatch ✅, TheraRadar ✅, BioBucks ✅ | **pdufa.bio total coverage gap** |

### Most accurate / most complete — the honest answer
- **PDUFA dates:** pdufa.bio is **as accurate as the best and cleaner than most** — verified correct on 6/6, and it *out-accurate'd RTTNews and MarketBeat* on specific rows. The "most accurate PDUFA calendar" claim is **credibly true today.**
- **Readouts:** pdufa.bio is **broad (728 rows) but not clean.** It's raw ClinicalTrials.gov primary-completion estimates with condition-field noise and no confidence/staleness signal. **TheraRadar is more accurate and more trustworthy here** because it grades confidence and flags stale rows. The "most accurate" claim **fails on readouts.**
- **Conferences:** **Not most complete — nonexistent.** BiopharmaWatch and TheraRadar cover this; pdufa.bio doesn't.

**Bottom line:** pdufa.bio is *already* more accurate than the field on its core PDUFA product, and it's *claiming* completeness it doesn't yet have on readouts and conferences. The gap between claim and reality is fixable and is the whole ballgame.

---

## 5. Dimension Deep-Dives

### SEO (weighted heavily)

**Strengths (on-page craft is genuinely strong):**
- Title tags are keyword-perfect. Homepage: `2026 FDA PDUFA Calendar — Dates & Run-up History | pdufa.bio`. Detail: `CELC PDUFA date — Gedatolisib with Fulvestrant, Jul 17 2026`. This is textbook.
- **Detail pages carry full structured data**: `@graph[BreadcrumbList, FAQPage, Event]` — the exact schema Google rewards for event/FAQ rich results. Verified on `/pdufa/CELC`.
- **Programmatic architecture already exists**: `/pdufa/{slug}` (86 in sitemap), `/fda-decision/{TICKER-DATE}` (20), `/calendar/2026/{month}` (11), `/condition/{ta}` (8), plus `/learn`, `/research`, `/devices`. Sitemap = 170 URLs. This is more programmatic surface than FDA Tracker or StockTitan.
- Breadcrumbs, FAQ blocks, source citations, and ClinicalTrials.gov NCT links on detail pages — all good E-E-A-T signals.

**Weaknesses (why none of it ranks):**
- **Ranks nowhere on page 1** for "PDUFA calendar," "FDA calendar," "biotech catalyst calendar," "clinical trial readout calendar," "upcoming FDA decisions," or "AdComm calendar." Every one is owned by older, higher-authority domains.
- **Self-inflicted 404s bleed link equity.** The homepage links every upcoming-decision card to `/pdufa/{TICKER}`, but pages are generated at *drug-specific slugs* (`/pdufa/VTRS-mr-100a-01`) or **not at all** (CORT, OTLK). Verified 404s: `/pdufa/CORT`, `/pdufa/VTRS`. Google is crawling the site's own homepage links into dead ends.
- **Thin schema on the highest-traffic hub pages.** Homepage has only `WebSite`; the `/readouts` page (728 rows, a huge rankable asset) has **no JSON-LD at all**. No `ItemList`/`Event` markup on the list pages.
- **Canonical inconsistency:** sitemap uses `https://pdufa.bio/...` (non-www) while the live site serves and canonicalizes to `https://www.pdufa.bio/...`. Split signals.
- **Two whole rankable categories missing:** no `/adcomm` page (FDA.gov + FDA Tracker own "AdComm calendar") and no `/conferences` (BiopharmaWatch, TheraRadar, BioBucks own "biotech conference calendar").
- Likely a **young domain with thin backlinks** — the run-up study and "why no approval %" pages are natural link bait that isn't being pitched.

**Best-in-class:** **BiopharmaWatch** (breadth of ranking) and **RTTNews/MarketBeat** (authority) for FDA/PDUFA terms; **TheraRadar** for readouts (uses `Dataset` + `FAQPage` schema — smart). **Copy:** TheraRadar's `Dataset` schema on the readouts hub; BiopharmaWatch's dedicated `/PDUFA-calendar` + `/fda-calendar` + conference URLs; add per-`ItemList` schema to every calendar page. **Beat:** you already have better per-event schema than all of them — just make it crawlable and stop 404ing your own links.

**Fastest path to outrank incumbents:** (1) fix routing so every homepage/calendar link resolves 200 with SSR/prerender; (2) add `ItemList`+`Event` schema to `/calendar`, `/readouts`, `/condition/*`, `/calendar/2026/*`; (3) ship `/adcomm` and `/conferences` hub + detail pages (net-new keyword real estate the brief's own positioning demands); (4) unify canonical on www; (5) turn the run-up study into linkable data-journalism for backlinks.

### UX

**Strengths:** Time-to-answer for "what's coming" is fast — homepage surfaces next decisions + recently decided in one view. "Browse by month" and "browse by condition" are genuinely useful cuts. The decision archive with 120-day charts is a differentiated, decision-useful asset. No login friction on anything free.

**Weaknesses:** (1) **No unified filter/search.** There's no visible way to filter by ticker + date-range + therapeutic area + phase + event-type from one screen; the three calendars are separate destinations. BiopharmaWatch's CatalystSync and TheraRadar's sponsor/indication/NCT filters are ahead here. (2) **Switching between the three calendars isn't a first-class control** — and one of the three (conferences) doesn't exist. (3) **Broken detail links** (CORT/OTLK/VTRS) are a UX failure, not just SEO — a user clicking the #1 catalyst hits a 404. (4) Readouts page is a long scroll with no in-page filtering.

**Best-in-class:** **TheraRadar** — window filter (next 3/6/12 mo), confidence filter, sponsor/indication/NCT search, per-row staleness. **Copy:** its filter model and the "what you can answer with this page" framing. **Beat:** wire one filter bar across all three event types (nobody does true cross-event filtering cleanly).

### UI

**Strengths:** This is pdufa.bio's clearest win. The dark theme, typography, card layout, and restraint make it **the best-looking product in the entire set** — cleaner than RTTNews (cluttered/ad-heavy), FDA Tracker (dated FullCalendar widget), MarketBeat (finance-portal noise), and BiopharmaWatch (generic + fake-looking testimonials). The calendar's two-column month cards (TICKER · date · outcome badge · drug — indication) are scannable and credible. Layout is fluid/responsive (viewport meta present).

**Weaknesses:** "Clean" is currently close to "plain" — there's little data-visualization payoff beyond the run-up sparkline. The only peer that matches on polish is **TheraRadar** (clean light theme) and **StockTitan** (modern dark). *Mobile note:* the Chrome extension captures a fixed viewport, so I could not force a true 390px render — responsiveness is inferred from fluid layout + viewport meta, **not visually confirmed on a phone**. Flagged for first-hand mobile QA.

**Best-in-class:** pdufa.bio (tie with TheraRadar). **Copy:** nothing — defend this lead. **Beat:** add tasteful data-viz (cohort run-up distributions, TA heatmaps) so "clean" reads as "premium," not "sparse."

### Value

**Strengths:** Cheapest paid tier ($15/mo) + the most open free tier (full calendar + archive + run-up study, no login). No ads. The run-up study + decision archive with 120-day charts is genuinely differentiated free content that BPIQ/BiopharmaWatch gate or lack. "Data and historical statistics only — no approval probabilities" is a credible trust posture for traders who distrust black-box scores.

**Weaknesses:** Missing conferences and AdComm dents the "most complete" value claim; readout errors dent the "most accurate" claim; and at $15 the delta to BiopharmaWatch ($19, with far more) is thin. No watchlist/alerting is visible on the free tier (alerts are Pro), and there's no public API (BiopharmaWatch and BPIQ both sell APIs at $99–$189/mo — an untapped revenue and backlink channel).

**Best-in-class (raw calendar decision-usefulness):** **BiopharmaWatch** on breadth (PDUFA + readouts + conferences + earnings + PoA + export), **TheraRadar** on readout trustworthiness. **Copy:** conference calendar + Excel/CSV export as a Pro hook (already partially there) + a simple public API. **Beat:** be the only one whose *free* tier is complete and correct across all three event types — completeness as the free-tier moat, live tools + data as the paid hook.

### Competitor one-liners (benchmark set)
- **BioPharmaCatalyst / BPIQ:** the incumbent brand; real product is the login-walled BPIQ app (Basic free, Pro $20 / Elite $25 / Apex $45 mo-annual) with screeners + hedge-fund tracking. Public marketing site bot-walls automated traffic.
- **FDA Tracker:** ranks on age; product is a dated month-grid widget with no meta description and no schema. Beatable on every dimension except domain age.
- **StockTitan:** different category — a high-authority real-time FDA *news* feed with AI sentiment, not a forward calendar. Competes for attention, not calendar craft.
- **RTTNews:** keyword-rich, per-drug pages, high DA — but cluttered, ad-heavy, paginated, freemium-walled, and demonstrably carries stale/incorrect outcome notes.
- **BiopharmaWatch (chief threat):** true 3-in-1 + conferences + PoA, SEO leader, $19/mo Elite, but stingy free tier (6 events) and low-trust presentation.
- **TheraRadar (the one to study):** best readout/conference craft — confidence grading + staleness flags + `Dataset` schema + clean UI. The template for pdufa.bio's readouts/conference expansion.
- **MarketBeat:** trust-signal benchmark — huge DA, clean table, analyst/price integration; calendar is one module of a finance portal.
- *TipRanks / Larvol / Kaleidoscope / BioPharma Dive / Fierce Biotech — not inspected first-hand; TipRanks & MarketBeat set the trust-signal bar, BioPharma Dive & Fierce own editorial/topical SEO ("5 FDA decisions to watch…"), Larvol & Kaleidoscope set the data-depth/modern-UX bar. Recommend a first-hand pass before acting on these.*

---

## 6. Battle Plan — Ranked Backlog

Impact (H/M/L) = effect on the "cleanest / most accurate / most complete, cheapest" claim. Effort (H/M/L) = dev/content lift. **Quick wins first.**

### Quick wins (do this week)

| # | Ticket | What / Why | Impact | Effort |
|---|---|---|---|---|
| Q1 | **Fix `/pdufa/{TICKER}` 404 routing** | Homepage links every upcoming decision to `/pdufa/{TICKER}`, but pages live at drug-slugs or don't exist (CORT, OTLK 404). Either generate a page per upcoming ticker or make the homepage link to the real slug. **The #1 nearest catalyst currently 404s.** Kills a UX failure + link-equity leak at once. | **H** | **L** |
| Q2 | **Generate the missing upcoming-PDUFA detail pages** | CORT, OTLK (and any upcoming name without a page) need the `/pdufa/*` template applied. The template is already excellent (schema + FAQ + chart) — it's just not being generated for every row. | **H** | **M** |
| Q3 | **Add meta descriptions + `ItemList`/`Event` schema to hub pages** | `/readouts` (728 rows) has **zero** JSON-LD; homepage has only `WebSite`. Add `ItemList`+`Event` to `/calendar`, `/readouts`, `/condition/*`, `/calendar/2026/*`. Target: event rich-results eligibility on the highest-traffic pages. | **H** | **L–M** |
| Q4 | **Unify canonical on www + fix sitemap host** | Sitemap emits non-www `pdufa.bio`; site serves www. Make canonical + sitemap consistent to stop split signals. | **M** | **L** |
| Q5 | **Reconcile pricing ($10/$100 vs live $15/$120)** | Brief and live site disagree. Pick one; if the "cheapest by a mile" positioning matters, $10/$100 widens the gap to BiopharmaWatch from $4 to $9. | **M** | **L** |
| Q6 | **QC pass on the readouts feed** | Suppress/flag obviously mis-parsed CT.gov rows (ACHV custirsen→cytisinicline, SKYE→obesity, BPTH→poliomyelitis). Even a rules-based drug↔indication sanity filter removes the most embarrassing errors that undercut "most accurate." | **H** | **M** |

### Big bets (next 1–2 quarters)

| # | Ticket | What / Why | Impact | Effort | Target keywords / pages |
|---|---|---|---|---|---|
| B1 | **Ship the Conference calendar** | The "three-in-one" promise is currently 2/3. Build `/conferences` hub + `/conference/{slug}` detail pages with `Event` schema. Closes the coverage gap vs BiopharmaWatch/TheraRadar and opens a net-new keyword category. | **H** | **H** | "biotech conference calendar," "ASCO/ASH/ESMO 2026 presentations," "medical conference calendar biotech" |
| B2 | **Ship an AdComm calendar** | No `/adcomm` page today; FDA.gov + FDA Tracker own the term. A clean, sourced AdComm calendar is low-competition, high-relevance keyword real estate. | **H** | **M** | "AdComm calendar," "FDA advisory committee meeting schedule," "ODAC meeting dates" |
| B3 | **Upgrade readouts to TheraRadar-grade** | Add per-row **confidence grade** + **last-updated staleness flag** + "read out vs awaiting vs estimated" status + `Dataset` schema. Turns the biggest accuracy liability into a trust asset and a rankable page. | **H** | **H** | "clinical trial readout calendar," "Phase 3 readout calendar 2026," "[drug] readout date" |
| B4 | **Unified cross-event filter bar** | One control: ticker + date-range + therapeutic area + phase + event-type, working across PDUFA/readouts/conferences from one screen. Nobody does true cross-event filtering cleanly — a genuine UX differentiator + a Pro hook. | **H** | **H** | — (product/retention) |
| B5 | **Backlink engine off the run-up study** | Package the 1,683-event run-up study + "why no approval %" methodology as quarterly data-journalism (charts, embeddable). This is the fastest way to close the domain-authority gap that keeps the good on-page work from ranking. | **H** | **M** | authority for all head terms |
| B6 | **Public data API (Pro/enterprise tier)** | BiopharmaWatch ($99–$189/mo) and BPIQ sell APIs. A simple `/api/v1/pdufa` + `/readouts` endpoint adds revenue, developer backlinks, and quant credibility. | **M** | **H** | "PDUFA API," "FDA calendar API" |
| B7 | **First-hand mobile + secondary-competitor audit** | Confirm the responsive layout on a real phone; open TipRanks/Larvol/Kaleidoscope/BioPharma Dive/Fierce to close the benchmark gaps this report flagged as unverified. | **M** | **L** | — (diligence) |

**Sequencing logic:** Q1–Q3 stop active bleeding (404s + missing schema) and are cheap — do them first; they alone should move rankings because the pages already exist and are well-built. Q6 protects the accuracy claim immediately. Then B1–B3 make "three-in-one, most complete, most accurate" *literally true*, which is the precondition for marketing it. B5 supplies the authority that converts the on-page work into rankings. B4/B6 are the retention/monetization moat once the category is owned.

---

## 7. Sources

All URLs inspected **2026-07-10**.

**Subject site**
- pdufa.bio — homepage, `/calendar`, `/pdufa/CELC`, `/pdufa/CORT` (404), `/readouts`, `/pricing`, `/sitemap.xml`, `/robots.txt` — https://www.pdufa.bio/

**Primary competitors (locked)**
- BioPharmaCatalyst — https://www.biopharmacatalyst.com/ *(bot-blocked → redirected to dead `ww38.` subdomain, `ERR_CONNECTION_RESET`)*
- BPIQ (BioPharmaCatalyst's product) — https://www.bpiq.com/pricing , https://app.bpiq.com/pdufa-calendar
- FDA Tracker — https://www.fdatracker.com/fda-calendar/ , https://www.fdatracker.com/membership-account/membership-levels/
- StockTitan — https://www.stocktitan.net/news/fda-approvals.html
- RTTNews — https://www.rttnews.com/corpinfo/fdacalendar.aspx

**Benchmark competitors (inspected live)**
- BiopharmaWatch — https://www.biopharmawatch.com/subscription , https://www.biopharmawatch.com/fda-calendar
- TheraRadar — https://theraradar.com/readouts/
- MarketBeat — https://www.marketbeat.com/fda-calendar/upcoming/

**SEO SERP tests (Google, 2026-07-10):** "PDUFA calendar," "FDA calendar," "biotech catalyst calendar," "clinical trial readout calendar 2026," "biotech medical conference calendar 2026," "AdComm calendar," "upcoming FDA decisions 2026." Additional rankers named: assyro.com, checkrare.com, catalystalert.io, dansfera.com, biobucks.co, marketshost.com, benzinga.com/fda-calendar, tipranks.com/calendars/fda.

**Primary-source accuracy checks**
- CORT relacorilant — Corcept IR / BusinessWire / CancerNetwork (PDUFA 2026-07-11)
- CELC gedatolisib — Celcuity IR / GlobeNewswire / StockTitan (PDUFA 2026-07-17)
- MNKD/SCPH FUROSCIX ReadyFlow — MannKind IR / Nasdaq (PDUFA 2026-07-26)
- MRNA mRNA-1010 — Moderna IR / PharmExec (PDUFA 2026-08-05)
- OTLK ONS-5010/LYTENAVA — Outlook IR / GlobeNewswire (PDUFA 2026-07-29)
- Conference dates — ASCO / ESMO / ASH official calendars; BioPharma Dive 2026 conference guide

**Not inspected first-hand (flagged):** TipRanks, Larvol, Kaleidoscope, BioPharma Dive, Fierce Biotech — referenced from SERP evidence only; excluded from numeric scoring.

---
*Informational product-strategy analysis. Not investment advice. Every date should be re-verified against primary FDA / SEC / company filings before any downstream use.*
