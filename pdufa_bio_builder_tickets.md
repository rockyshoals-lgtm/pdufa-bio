# pdufa.bio — Builder Tickets
**Source audit:** `pdufa_bio_competitive_audit_2026-07-10.md` · **Updated:** 2026-07-10
Work top to bottom. Quick wins (Q) first — they're cheap and high-impact. Then big bets (B).
Each ticket = what to do, why it matters, and "done when."

---

## 🔴 QUICK WINS — do these first (days, not weeks)

### Q1 — Fix broken `/pdufa/{TICKER}` links on the homepage & calendar
**Impact: HIGH · Effort: LOW**
- **Problem:** Homepage "Next FDA Decisions" cards link to `/pdufa/CORT`, `/pdufa/VTRS`, etc. Those return **404**. Real pages use drug-slugs (e.g. `/pdufa/VTRS-mr-100a-01`) or don't exist (CORT, OTLK). The #1 nearest catalyst on the homepage is a dead link.
- **Do:** Make every event card link to the actual generated slug for that event (pull the real slug from the same data source the detail page uses). No card should ever point at a bare `/pdufa/{TICKER}` unless that exact page exists.
- **Done when:** Clicking every card on `/` and `/calendar` lands on a real 200 page. Automated check: crawl all internal links, 0 return 404.

### Q2 — Generate the missing upcoming-PDUFA detail pages
**Impact: HIGH · Effort: MEDIUM**
- **Problem:** Some upcoming names have no detail page at all (verified missing: **CORT**, **OTLK**). The detail template itself is great — it's just not generated for every row in the calendar.
- **Do:** Ensure the `/pdufa/*` page generator runs for **every** event in the upcoming calendar, not just a subset. Backfill CORT, OTLK, and any other upcoming ticker without a page.
- **Done when:** Every event listed on `/calendar` has a corresponding 200 detail page, and all are in `sitemap.xml`.

### Q3 — Add structured data + meta descriptions to the hub pages
**Impact: HIGH · Effort: LOW–MEDIUM**
- **Problem:** `/readouts` (728 rows) has **no JSON-LD**. Homepage has only `WebSite`. The list pages have no `ItemList`/`Event` markup, so Google can't read them as events.
- **Do:** Add `ItemList` + per-row `Event` JSON-LD to `/calendar`, `/readouts`, `/condition/*`, and `/calendar/2026/*`. Add a unique `<meta name="description">` to each hub page. (The detail pages already do this correctly — reuse that pattern.)
- **Done when:** Google Rich Results Test passes for `Event`/`ItemList` on `/calendar` and `/readouts`; every hub page has a non-empty meta description.

### Q4 — Make www vs non-www consistent
**Impact: MEDIUM · Effort: LOW**
- **Problem:** `sitemap.xml` emits non-www `https://pdufa.bio/...`, but the site serves and canonicalizes to `https://www.pdufa.bio/...`. Split signals confuse crawlers.
- **Do:** Pick one host (recommend keeping `www`), 301 the other, and regenerate the sitemap + all canonical tags to match.
- **Done when:** Sitemap URLs, canonical tags, and the served host all agree; the non-canonical host 301-redirects.

### Q5 — Lock the pricing decision
**Impact: MEDIUM · Effort: LOW** *(product decision, not code)*
- **Problem:** Live site charges **$15/mo / $120/yr**; the strategy brief says $10/$100. They must match. At $10/$100 the "cheapest by a mile" claim is airtight (vs BiopharmaWatch $19); at $15 the gap is only $4.
- **Do:** Confirm the intended price with the owner, then make the pricing page, checkout, and any marketing copy consistent.
- **Done when:** One price everywhere.

### Q6 — Sanity-filter the readouts feed
**Impact: HIGH · Effort: MEDIUM**
- **Problem:** The readouts calendar is raw ClinicalTrials.gov data and shows obviously wrong drug↔indication pairs, e.g. "ACHV Custirsen — Vaping Cessation" (should be cytisinicline), "SKYE SBI-100 Ophthalmic Emulsion — Obesity," "BPTH BP1001 — Poliomyelitis." These undercut the "most accurate" claim.
- **Do:** Add a rules-based sanity check on the drug/indication fields; suppress or flag rows that fail (e.g. known drug mapped to an unrelated condition). Start with a manual blocklist of the worst offenders, then automate.
- **Done when:** A scan of the readouts page surfaces no nonsensical drug-indication pairs; flagged rows are hidden or marked "unverified."

---

## 🟠 BIG BETS — schedule after quick wins (weeks)

### B1 — Ship the Conference calendar
**Impact: HIGH · Effort: HIGH**
- **Why:** The "three-in-one" promise is currently 2 of 3 — `/conferences` 404s. Competitors (BiopharmaWatch, TheraRadar, BioBucks) own the conference keyword.
- **Do:** Build `/conferences` hub + `/conference/{slug}` detail pages with `Event` JSON-LD. Cover ASCO/ASH/ESMO/AACR etc. with company presentation catalysts.
- **Target keywords:** "biotech conference calendar," "ASCO/ASH/ESMO 2026 presentations," "medical conference calendar biotech."
- **Done when:** Conference calendar is live, filterable, schema-marked, and in the sitemap.

### B2 — Ship an AdComm (advisory committee) calendar
**Impact: HIGH · Effort: MEDIUM**
- **Why:** No `/adcomm` page today; low-competition, high-relevance term currently owned by FDA.gov + FDA Tracker.
- **Do:** Build `/adcomm` hub + detail pages (sourced from FDA Federal Register notices) with `Event` schema.
- **Target keywords:** "AdComm calendar," "FDA advisory committee meeting schedule," "ODAC meeting dates."
- **Done when:** AdComm calendar live + schema-marked + in sitemap.

### B3 — Upgrade readouts to "confidence + staleness" grade
**Impact: HIGH · Effort: HIGH**
- **Why:** Turns the biggest accuracy liability into a trust asset. TheraRadar wins here by grading confidence and flagging stale dates.
- **Do:** Add per-row **confidence grade**, **last-updated / staleness flag**, and status ("read out" vs "awaiting" vs "estimated"). Add `Dataset` JSON-LD to the readouts hub.
- **Target keywords:** "clinical trial readout calendar," "Phase 3 readout calendar 2026," "[drug] readout date."
- **Done when:** Every readout row shows confidence + freshness; stale rows are visually distinct.

### B4 — Unified cross-event filter bar
**Impact: HIGH · Effort: HIGH**
- **Why:** No competitor filters cleanly across all event types. A single filter bar (ticker · date-range · therapeutic area · phase · event-type) working across PDUFA + readouts + conferences is a genuine UX differentiator and a Pro hook.
- **Do:** One persistent filter component that queries across all three calendars from any screen.
- **Done when:** A user can filter by all five dimensions from one control and see combined results.

### B5 — Backlink engine off the run-up study
**Impact: HIGH · Effort: MEDIUM** *(content/marketing)*
- **Why:** The good on-page SEO isn't ranking largely because the domain lacks authority/backlinks. The 1,683-event run-up study is natural link bait.
- **Do:** Publish quarterly data-journalism from the run-up study (charts, embeddable graphics, shareable stats). Pitch to biotech newsletters/press.
- **Done when:** Recurring publishing cadence live; backlinks accruing.

### B6 — Public data API (new paid tier)
**Impact: MEDIUM · Effort: HIGH**
- **Why:** BiopharmaWatch ($99–$189/mo) and BPIQ sell APIs — revenue + developer backlinks + quant credibility.
- **Do:** Ship read-only `/api/v1/pdufa`, `/api/v1/readouts` (JSON, API-key auth). Document it.
- **Target keywords:** "PDUFA API," "FDA calendar API."
- **Done when:** Documented, authenticated API live with at least PDUFA + readouts endpoints.

### B7 — Diligence: mobile QA + secondary-competitor pass
**Impact: MEDIUM · Effort: LOW**
- **Why:** Loose ends from the audit. Mobile responsiveness was inferred, not visually confirmed on a phone; five secondary competitors weren't opened first-hand.
- **Do:** Test the site on a real phone (390px). First-hand review of TipRanks, Larvol, Kaleidoscope, BioPharma Dive, Fierce Biotech.
- **Done when:** Mobile QA signed off; short notes on the five competitors added to the audit.

---

## Suggested order
**Week 1:** Q1 → Q2 → Q3 → Q4 → Q6 (Q5 is a decision, resolve in parallel)
**Weeks 2–8:** B2 (fast) → B1 → B3 → B5 (ongoing) → B4 → B6 → B7

**Guiding principle:** Q1–Q3 stop active SEO/UX bleeding using pages that already exist and are well-built — they should move rankings on their own. B1–B3 make "three-in-one, most complete, most accurate" *literally true*, which is the precondition for marketing the claim. Don't touch the UI look — it's already the cleanest in the category; protect that lead.
