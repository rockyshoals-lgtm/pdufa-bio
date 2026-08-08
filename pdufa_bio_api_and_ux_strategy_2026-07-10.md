# pdufa.bio — API Teardown + UX/UI Differentiation Strategy
**Date:** 2026-07-10 · **Method:** live API testing (cache-busted) + UX inspection
Product-strategy use only; not investment advice.

---

## Part 1 — The API: how it works, and does it work well?

### How it works (verified live)
- **Base:** `https://www.pdufa.bio/api/v1` · **Docs:** `/developers` (clean, honest, has curl examples).
- **Endpoints (all 200, JSON):**
  - `/api/v1/pdufa` — 83 PDUFA decisions
  - `/api/v1/readouts` — 307 trial readouts
  - `/api/v1/events` — **406, all four catalyst types combined** (PDUFA + readouts + conferences + AdComm)
- **Query params all work** (tested with correct names): `ticker` (CELC→1), `type` (Conference→14, AdComm→2), `ta` (Oncology→18), `status` (Upcoming→73, matches the homepage counter), `from`/`to` date range (Sep–Dec→41), `limit`/`offset` (max 1000), `format=csv`.
- **Envelope:** `{ meta:{source,total,returned,as_of,limit,offset}, data:[…] }`. Every record carries a **`url` back to its detail page** (built-in attribution/backlink).
- **Response fields:** `ticker, date, name, type, therapeutic_area, market_cap_tier, status, url`.
- **Infra:** ~400ms response, **CORS open** (`*`), **edge-cached ~30 min**, **no auth in preview**, **attribution license** ("free with a link back to pdufa.bio").

### Does it work well? — **Yes. This is a genuinely solid, well-designed API.** (Grade: A−)
Clean REST, sensible envelope, working filters, combined `/events` endpoint, CSV export, permissive CORS, honest docs, and a link-back on every record. It already beats most competitors, who either have **no public API** (FDA Tracker, RTTNews, StockTitan, MarketBeat) or gate it hard (BiopharmaWatch: **$99–$189/mo**).

> **Note / self-correction:** in an earlier pass I reported "filters broken / conferences 404." That was **my testing error** — I used undocumented param names (`therapeutic_area` instead of `ta`) and a malformed cache-buster. With the documented params, everything works.

### Real gaps (what to fix before charging for it)
1. **Fields are shallow — the moat data isn't exposed.** The API returns the *calendar skeleton* only. It does **not** include the differentiated assets: the **T-120→T+5 run-up series**, **cohort base-rate move**, **NCT ID**, **sponsor**, **drug class**, or decision outcome detail. Right now you're giving away the commodity and withholding nothing of the premium — because the premium isn't in the API at all yet.
2. **No enforced rate limits / keys yet** ("reasonable use" is a request, not a control). Fine for preview; needed before commercial.
3. **No stable event IDs** (records keyed by ticker+date); add an `id` for reliable joins.
4. **Minor data QA:** many `/readouts` rows normalize to a single mid-month date (e.g. `2026-06-15`) — fine as "month precision," but expose a `date_precision` field so consumers know it's a month, not a day.
5. **No changelog/webhooks** — the highest-value thing an investor wants is *"tell me when a date moves,"* which is push, not pull.

---

## Part 2 — Should the API be behind the paywall?

**Recommendation: No — keep a free tier. Paywall *depth and volume*, not *access*. Freemium, three tiers.** The docs already hint at exactly this ("open in preview; commercial/high-volume needs an `x-api-key` — See Pro"). Formalize it:

| Tier | Price | What they get | Why |
|---|---|---|---|
| **Free (keep it)** | $0, attribution required | Calendar skeleton (`ticker,date,name,type,ta,cap_tier,status,url`), all event types, ~60 req/hr, 30-min cache, non-commercial | **The free API is a growth engine, not a product.** Every record returns a `url` back to the site → **distributed backlinks + brand mentions** wherever developers embed it (Discord bots, Sheets, dashboards). That's exactly the off-page authority you need to win the head-term SEO race. Giving the *list* away is free marketing. |
| **Pro** | already **$10/mo** | The **depth fields** (run-up T-120→T+5 series, cohort base-rate move, NCT, sponsor, cap), **CSV/bulk export**, higher limits, no attribution requirement, **date-slip webhooks/alerts** | The moat is **data depth + accuracy**, not the date list (which is free everywhere). Sell the analytics, not the calendar. |
| **Commercial / Quant** | future **$99–$199/mo** | High-volume key, full **historical run-up dataset**, SLA, priority support | This is precisely where BiopharmaWatch charges $99–$189. You can undercut and out-quality them. |

**The core principle:** the calendar is a commodity — competitors give it away free. **What nobody else has is the run-up study + cohort base rates.** So: *free API = the dates (SEO/backlink flywheel); paid API = the run-up/cohort intelligence (revenue).* Locking the whole API away kills the backlink flywheel you need for rankings; leaving the *depth* free leaves money on the table and no reason to upgrade. Freemium threads both.

**One caution:** an open, un-keyed, un-throttled API can be scraped wholesale — a competitor could rebuild your calendar. Mitigate by (a) keeping only the commodity fields free, (b) adding soft rate limits + keys now, (c) enforcing the attribution license, and (d) reserving run-up/cohort/historical data for authenticated Pro keys.

---

## Part 3 — What could an investor actually use the API for?

Concrete jobs-to-be-done (this is also your Pro marketing copy):
- **Automated watchlist / portfolio catalyst alerts** — poll `/events?ticker=…` for their holdings; get pinged when a name has an upcoming PDUFA, readout, conference, or AdComm.
- **Date-slip monitoring** — diff `as_of` snapshots to catch when a PDUFA moves, drops, or a readout window shifts (the #1 requested feature — best delivered as a **webhook**).
- **Google Sheets / Excel models** — pull `?format=csv` into a live catalyst tab for position sizing and calendar planning.
- **Custom dashboards & Discord/Slack/Telegram bots** — power a community "this week's catalysts" feed (each post links back to you → backlinks).
- **Run-up backtesting & quant features** *(Pro depth)* — feed the T-120→T+5 series + cohort base rates into a trading model to size run-up trades by cap tier and days-to-event.
- **Screeners & scanners** — combine `/events` with the investor's own price/options data to build a catalyst-aware scanner.
- **Calendar sync** — generate `.ics`/Google Calendar entries per ticker (an easy, high-delight Pro feature to add).
- **Brokerage/newsletter overlays** — a newsletter or fintech embeds your dates (attribution → brand reach).

**Takeaway:** the free API sells *reach and links*; the paid API sells *the run-up/cohort intelligence and push alerts* — which is the one thing traders will actually pay $10/mo for.

---

## Part 4 — UX/UI: what will set us apart (going deeper)

The design foundation is now genuinely strong (Space Grotesk + IBM Plex Mono, a **run-up sparkline on every row**, ⌘K search, and a real cross-event **Screener** at `/screener` — 406 catalysts, filter by ticker/type/TA/date). That already out-crafts the field. To make the differentiation *decisive*, push these — roughly in priority:

**1. Own one identity: "the catalyst tape / terminal."** Everyone else is a *data portal*; be an *instrument*. Lean into Bloomberg-density + Linear-craft: mono numerics, tight rhythm, a live "catalyst ticker" strip across the top of the calendar (next 5 events scrolling), dark-first. This is a positioning nobody in the set occupies.

**2. Data-viz nobody else has (the "clean → premium" upgrade).**
   - **Calendar heatmap** — catalysts-per-week by cap tier; the screenshot-worthy hero.
   - **Cohort distribution** — replace the flat `±X% cohort` chip with a tiny distribution showing where this cap-tier historically moves. Turns a number into insight.
   - **Run-up curve overlays** on detail pages (this event vs the cohort median curve).
   - These are your data assets rendered as pictures — the exact thing free calendars can't copy.

**3. Speed + friction as the brand.** No login, no ads, sub-second, edge-cached. Make "the fastest clean answer to *what's coming*" the felt experience — and say it. Competitors are slow, gated, ad-heavy; velocity is a design differentiator.

**4. Win mobile — the surface everyone loses.** Every competitor is desktop-portal-first. A genuinely great **mobile** catalyst calendar (sticky filter bar, swipeable event-type tabs, tap-to-detail, **add-to-calendar**, 44px targets, a hamburger/drawer) would be a category-leading experience on the device traders actually check. *This is the single biggest untapped UX win — and it's also our current weakest surface (no mobile nav, sub-40px targets).*

**5. Shareable + addressable.** Make every Screener filter state a **URL** (shareable + individually indexable for long-tail SEO), and ship **per-event OG images** (ticker · date · sparkline) so shared links render as branded cards → social embeds → backlinks. Design as a distribution channel.

**6. Power-user interaction.** Keyboard nav (`j/k` through the calendar), hover-peek the run-up on any row, **saved views + watchlist**, and ⌘K that jumps to any ticker/date/TA. Traders reward speed and keyboard control; it also deepens engagement signals.

**7. Trust microcraft.** Inline source citations + "verify" links, per-row freshness timestamps (you already have staleness flags on readouts — extend everywhere), and crafted empty/loading/error states. Accuracy is the promise; *showing* the sourcing is the design expression of it.

**The one-line thesis:** *competitors are portals; we are the instrument — fast, branded, data-drenched, keyboard-driven, and the only one that's equally great on a phone.* The moat is the run-up/cohort data rendered as signature visualizations; the growth engine is a free, link-back API and shareable per-event cards.

---
## Sources (live 2026-07-10, cache-busted)
pdufa.bio `/developers`, `/api/v1/pdufa|readouts|events` (+ filters tested), `/screener`, `/`, `/calendar` — https://www.pdufa.bio/
