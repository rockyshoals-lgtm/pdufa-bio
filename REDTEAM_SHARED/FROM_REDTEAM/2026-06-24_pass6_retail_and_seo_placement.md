# pdufa.bio — RED TEAM Pass 6 · Retail Usability + SEO Placement (live via Chrome) · 2026-06-24

Focused pass on the two things you asked for: **retail usability** and **SEO placement**. Verified live in Chrome (gated app unlocked; real Google SERPs read).

## ✅ First: the P0 is fixed
The `/app` Radar hero-card bug is **resolved** — GSK/SPRO now render as compact cards with horizontal chips ("✓ Approved · Vol rich 2.1× · ±2.1%"), SPRO's "+1 more" 3-chip cap works, header reads "Snapshot · updated." Mobile launch-blocker cleared. The app looks premium now.

---

# 🔴 SEO PLACEMENT — the hard truth: you're not on page 1 for anything that matters

I read the real Google SERPs. pdufa.bio is **absent from page 1** on all three core query types:

| Query (intent) | Who's on page 1 | pdufa.bio |
|---|---|---|
| **"PDUFA calendar 2026"** (head) | FDATracker, BiopharmaWatch ×2, CheckRare, Dan Sfera, BPIQ, RTTNews, FDA.gov, **Assyro AI**, MarketBeat | **Not in top 10** |
| **"what is a PDUFA date"** (your namesake explainer) | Wikipedia, Motley Fool, Pharmacy Times, FDA.gov, Ataxia Fdn, Epilepsy Fdn | **Not in top 10** |
| **"UNCY PDUFA date"** (long-tail per-event) | Unicycive IR, Reddit, SEC.gov, Simply Wall St, Seeking Alpha, Stock Titan | **Not in top 10** |

A site literally named `pdufa.bio` is not page-1 for "PDUFA calendar." **Your on-page SEO is excellent — placement is the problem, and it's an off-page/authority problem, not an on-page one.** Stop polishing titles; the next gains are off-page.

### Why you're not placing (root causes)
1. **New domain, no authority.** Your competitors have age + trust: FDATracker (since 2011), MarketBeat/Wikipedia (massive DA), BiopharmaWatch/Dan Sfera (established). New domains get sandboxed for competitive terms for months.
2. **You were effectively invisible to Google until ~days ago.** The landing was "coming soon" + cache-stale for days; the sitemap was cut **443 → 125** (thin pages noindexed); /today + /app are noindexed. Google has a tiny, very-recently-changed footprint to work with.
3. **~Zero backlinks.** Backlinks are *the* ranking driver for competitive terms. Reddit/Seeking Alpha/Stock Titan/company-IR rank because they have links + engagement. You have neither yet.
4. **Per-event pages too thin to beat a press release.** `/pdufa/UNCY` (below) gives date + chart + cohort; the pages ranking *tell the story* (CRL history, cash, thesis). Depth wins the long tail.
5. **New competitor alert: Assyro AI** (assyro.com) ranks page-1 for the head term using **your exact pitch** — "source-linked records." Someone else is claiming the provenance wedge in the SERP.
6. **Vertical pages work:** **CheckRare ranks #3** for "PDUFA calendar 2026" with an *orphan-drug-specific* page. Proof that condition/vertical pages crack a competitive SERP.

### SEO-placement action plan (off-page + structural — ranked)
1. **Backlinks / digital PR — the #1 lever you haven't started.** Your `/research` data studies (run-up by cap, with the honest caveats) are genuine link-bait. Pitch them to biotech Substacks, Seeking Alpha contributors, r/biotechstocks, FierceBiotech/Endpoints, and tool-roundup pages. Get the dataset *cited*. Submit to biotech-tool directories. This is what moves placement.
2. **Indexation push.** Submit the key URLs in Search Console; re-expand the footprint as the crawler enriches the noindexed pages (125 → back toward 443 with real drug/indication data). Aggressive internal linking between /calendar ↔ /pdufa ↔ /learn ↔ /research.
3. **Win the long tail with DEPTH + FRESHNESS.** Make `/pdufa/[ticker]` the single best page on "[ticker] PDUFA" — deeper than the company PR (see retail fixes below). A genuinely best-in-class page *can* outrank a press release; a thin one never will.
4. **Ship month + condition pages** (less-contested long tail you can actually win): `/calendar/2026/[month]` ("September 2026 PDUFA dates") and `/condition/[obesity|alzheimers|oncology|orphan]` ("obesity drug FDA approvals 2026"). CheckRare proves the vertical angle ranks. **Still not shipped — this is the top structural move.**
5. **Earn engagement signals.** Static pages don't accrue the dwell/shares Reddit/SA get. Shareable per-event OG images + a reason to return (email/alerts) feed ranking indirectly.

---

# 🟠 RETAIL USABILITY — strong bones, but it still talks like a terminal, not to a beginner

### The core retail problem: trader jargon everywhere
A first-time retail investor lands and meets **"Vol rich 2.1×", "IV CRUSH", "±2.1% exp", "HIGH IV", "C/P", "ATM IV", "cohort move ±7%."** That's options-desk language. The tap-popovers explain it — but a novice won't tap, and the *first impression* is "this is for pros." Fixes:
1. **Add a plain-language layer.** Lead each card with one human line and keep the jargon as the secondary/tap detail. E.g., instead of leading with "Vol rich 2.1× · ±2.1% exp," lead with **"Options are pricing a bigger-than-usual move"** (the popover already says this — surface it). "IV CRUSH" → a tooltip word like **"options may lose value after the news (IV crush)."**
2. **Plain-English indications.** `/pdufa/UNCY` says "Kidney disease" (vague *and* imprecise — it's hyperphosphatemia in dialysis patients); the app shows "Tebipenem HBr (SPR994) - (PIVO." Lead with what it treats in human terms, keep the code name secondary.
3. **A condition / "what's this about" lens.** Retail thinks in diseases ("show me the obesity/Alzheimer's/cancer ones"), not tickers. No condition filter exists. This is the single most retail-native feature you're missing (and it doubles as the SEO `/condition/` pages).

### The per-event page (`/pdufa/UNCY`) — retail + ranking, same fixes
- **Stale chart:** "Price path to 2026-06-19" — ~6 days old. A retail visitor sees outdated data; Google sees a stale page. Refresh the per-event chart with the build/data.
- **Missing the story:** no mention that **UNCY got a CRL in June 2025** and this is the resubmission — that's the entire reason the stock is interesting. No cash-runway, no plain-English "what OLC does / why it matters." Add a short, sourced **"The story"** block. This is what makes it beat a press release (ranking) *and* makes a beginner understand it (retail).
- **Dead-end CTA:** the only next step is "Opens the pdufa.bio app (private beta)" — a locked door. Add **email/"notify me before this date"** capture. Cold retail bounce → no conversion *and* worse engagement signals.
- **No related links:** add "Other kidney/renal PDUFAs," "Other micro-cap decisions this month," "UNCY's prior FDA history." Internal links = retail exploration + SEO.

### Calendar (what retail + Google both see)
- **Data dupes still live:** VRDN listed twice (06-30, same drug), GSK tebipenem shown approved *and* pending. Messy data erodes retail trust on the page most likely to rank.
- **Raw indications:** "Dephosphorylated Phosphatase and Tensin…" — keep a plain-English version for retail.

### What's genuinely good for retail (keep)
- The homepage "A LOOK INSIDE" free preview tape is a great, calm first impression.
- The app Radar defaults to near-term (Today → This week → 30d) — correct retail priority.
- The "facts, not advice / no hype" tone is a real retail trust advantage vs MarketBeat's "Top 5 Stocks to Buy."

---

## Top priorities (this pass)
1. **[SEO P0 — off-page] Start a backlink/digital-PR push** around the `/research` studies. This is the only thing that moves placement, and it's not started. Nothing on-page will rank you for "PDUFA calendar" without it.
2. **[SEO P0 — structural] Ship month + condition pages** (`/calendar/2026/[month]`, `/condition/[…]`) — winnable long-tail; CheckRare proves verticals rank; doubles as the retail condition lens.
3. **[Retail P1] Plain-language layer** — human first line per card + plain-English indications; jargon demoted to tap-detail.
4. **[Retail+SEO P1] Deepen + freshen `/pdufa/[ticker]`** — add the CRL/story block, fix the stale chart, add related-event links, add email capture (kills the dead-end + helps ranking).
5. **[Trust P1] Fix the calendar dupes** (VRDN, GSK) — they're on your most rankable page.
6. **[Indexation] Search Console submit + re-expand the sitemap** as the crawler enriches the noindexed pages.

**Bottom line:** the *product* is now in good shape — the mobile bug is fixed and the UX is clean and calm. The gap is **distribution**: you're not placing on page 1 for any core term because the domain is new, recently un-gated, thin-footprint, and has no backlinks — and your per-event pages aren't yet deep enough to beat a press release. Retail-wise, the bones are strong but it still reads like a trader terminal to a beginner. The next chapter isn't more on-page polish — it's **authority (backlinks), structural pages (month/condition), depth (the story), and a plain-language layer.**

*— Red Team Pass 6 (live via connected Chrome; real SERP placement read).*
