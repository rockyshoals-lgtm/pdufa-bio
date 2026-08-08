# pdufa.bio — KAIZEN 改善
### Ultimate SEO · UX · UI · Retail-Investor pass
**Date:** 2026-07-10 · Verified live before writing. Product-strategy only; not investment advice.

---

## The single biggest finding

**The site has no retention loop and no company-level page.** Verified live — all of these 404:

`/watchlist` · `/ticker/{TICKER}` · `/drug/{name}` · `/alerts` · `/about` · `/glossary` · `/changelog` · `/llms.txt` · `/compare`

…and the homepage contains **no email capture, no watchlist, no add-to-calendar** at all.

So today: a retail investor lands from Google, gets their date, and **leaves forever.** There is no way to save a ticker, be reminded, or come back. Meanwhile every competitor captures email (RTTNews dangles a PDF lead-magnet; BiopharmaWatch a 3-day trial). *We have the best product and the worst funnel.* Fixing this is worth more than any further SEO or design work.

---

## 🔴 The Big Three (do these before anything else)

### K1 — `/ticker/{TICKER}` company catalyst hubs *(SEO + UX + retail, all at once)*
One page per company aggregating **every** catalyst: PDUFA + readouts + conferences + AdComm + past decisions + run-up chart + cash runway.
- **Why it's the highest-leverage page on the site:** it's the exact thing retail searches — *"MNKD catalysts," "CELC PDUFA date," "what's coming for OTLK"* — and it's **near-zero competition long-tail** (vs. "PDUFA calendar," which we're losing to DA-80 incumbents). Stop fighting head terms first; **win the tail, then the head follows.**
- ~400+ instantly-indexable, genuinely useful pages from data you already have.
- Schema: `Organization` + `ItemList` + `FAQPage` ("When is MNKD's next FDA decision?").
- Internal-link every event page → its ticker hub → TA hub → month hub.
- Also ship `/drug/{name}` (drug-name searches are a separate, large intent pool: *"gedatolisib FDA approval date"*).

### K2 — Watchlist + alerts + email *(the missing retention loop)*
- **Free, no-login watchlist** (localStorage): star any ticker → "My catalysts" view. Zero friction, zero cost.
- **Add-to-calendar (.ics / Google Calendar) on every event** — one click, free, and quietly viral. Nobody in the set does this well.
- **Free weekly email:** *"Your catalysts — next 7 days."* This builds the one asset you don't have: **an owned audience.** It also feeds Pro conversion and gives you a distribution channel that isn't Google.
- **Pro:** date-slip alerts + push/email the moment a PDUFA moves. That's the $10/mo job-to-be-done.
- Funnel: *free watchlist → free digest → paid alerts.* Clean, honest, high-converting.

### K3 — `/about`, `/methodology`, `/corrections` *(trust = the whole brand)*
- **`/about` is missing entirely** — a real E-E-A-T problem for a finance-adjacent site. Google needs a named entity behind the data (who, credentials, contact, `Organization` + `sameAs` schema).
- **Ship a public corrections log + changelog.** For a product whose entire promise is *accuracy*, publicly logging *"we had CELC's indication imprecise; fixed 2026-07-02"* is the most powerful trust signal available — **and no competitor does it.** It converts your one weakness (a young domain) into the thing that makes you more credible than RTTNews.
- Add a per-page **"Last verified: <date> · Source: <company 8-K>"** line. Accuracy is the promise; *showing the receipts* is the design expression of it.

---

## 🔍 SEO Kaizen

| # | Move | Why |
|---|---|---|
| **S1** | **Ticker + drug hubs** (K1) | The winnable, high-intent tail. Highest ROI SEO on the board. |
| **S2** | **AEO / answer-engine optimization** — ship `/llms.txt`, keep the free API open, write plain declarative answer sentences, add `dateModified` | Retail increasingly asks **ChatGPT/Perplexity** *"what FDA decisions are coming up?"* Being **cited by LLMs is the new page 1** — and it's a channel every competitor is ignoring. Our free, well-structured API + clean schema makes us the *easiest* source for an AI to quote. This is the biggest asymmetric SEO bet available. |
| **S3** | **Backlink engine off the run-up study** | The 1,683-event run-up dataset is genuinely unique. Publish a quarterly **"Biotech Run-up Report"** with embeddable charts; pitch Endpoints/STAT/Fierce/BioPharma Dive. This is the only real fix for the authority gap that's keeping us off head terms. |
| **S4** | **Free embeddable widget** — "Next PDUFA" badge for newsletters/IR pages/Substacks | Every embed = a backlink, automatically. Turns distribution into SEO. |
| **S5** | **Evergreen link-magnets** — `/fda-approvals-2025` (full list), `/crl-tracker`, `/fda-approval-rate-by-therapeutic-area` | Reference pages earn links passively and own huge long-tail. |
| **S6** | **Comparison pages** — "free BioPharmaCatalyst alternative", "best free PDUFA calendar" | High commercial intent, trivially winnable, competitors won't write them. |
| **S7** | **"What happened" outcome pages** — post-decision recap with the actual move | People search *"[TICKER] FDA decision result"* the day of. Captures the biggest traffic spike in the catalyst lifecycle — which we currently miss entirely. |
| **S8** | **Glossary** (`/learn/what-is-a-pdufa-date`, `/what-is-a-crl`) | Classic informational tail + internal-link spine. `/learn` exists — expand it. |
| **S9** | **Flush the stale "ODIN Scores" SERP title** | Request re-index; guard public meta against internal model names. |

**Strategic note:** stop optimizing *for* "PDUFA calendar." Win 400 ticker pages + 200 drug pages + AEO citations, accumulate authority, and the head terms fall out of it in 6–12 months. Fighting DA-80 incumbents head-on with a young domain is the slowest possible path.

---

## 🎯 Retail-Investor Kaizen (what they actually want)

Their real jobs-to-be-done, and whether we serve them:

| Job | Today | Kaizen |
|---|---|---|
| "What's coming for **my** tickers?" | ❌ nothing | **Watchlist** (K2) |
| "Don't let me miss it" | ❌ nothing | **Add-to-calendar + alerts** (K2) |
| "Is this date real / did it move?" | 🟡 partial | **Date-slip alerts** + "last verified" stamp |
| "What usually happens to names like this?" | ✅ cohort ±% | Upgrade to a **distribution**, add **"5 most similar past events + what happened"** (factual, not predictive — perfectly on-brand) |
| "Can they survive a CRL?" | ✅ cash runway on detail | Surface **cash runway on the calendar rows** — it's the single most decision-useful retail field and nobody else shows it |
| "What happened after?" | 🟡 archive | **Outcome recap + actual move** on every decided event |
| "What even is a CRL?" | 🟡 `/learn` | Glossary + inline tooltips |

**Two on-brand ideas that would delight retail without breaking the "no approval odds" rule:**
1. **"Similar past events"** — for any upcoming PDUFA, show the 5 most comparable historical events (same TA, cap tier, resubmission class) and *what actually happened*. Pure fact, zero prediction, enormously useful. This is the killer feature the positioning permits and competitors can't copy (they lack the 1,683-event archive).
2. **Options-implied move** *(optional)* — the market's own implied move is a **fact**, not our forecast. Retail loves it. But it flirts with the "no edge claims" purity and costs data spend — **flag as a deliberate positioning decision, not a default.**

---

## 🎨 UI/UX Kaizen

| # | Move | Note |
|---|---|---|
| **U1** | **Win mobile** — hamburger/drawer, 44px targets, sticky filter, swipeable event-type tabs | Still the weakest surface (no mobile nav; 31/61 targets <40px). Every competitor is desktop-portal-first — **mobile is the one place we can be categorically best**, and it's where retail actually checks. |
| **U2** | **Calendar heatmap** (catalysts/week × cap tier) | The screenshot-worthy signature no rival has. |
| **U3** | **Cohort distribution** replacing the flat `±X%` chip | Turns a number into insight; renders our data moat as a picture. |
| **U4** | **Logomark + per-event OG cards** (ticker · date · sparkline) | Recognition + social CTR + backlinks. Design as distribution. |
| **U5** | **Keyboard nav** (`j/k`, `/` to search) + saved Screener views as **URLs** | Power-user speed *and* shareable/indexable filter states (SEO twofer). |
| **U6** | **"This week" band** + live tape strip | Urgency and the "terminal" identity. |
| **U7** | **Accessibility pass** — contrast, focus rings, reduced-motion, aria | Right thing to do; also a quality signal. |
| **U8** | **Light-mode toggle** | Dark-only alienates a chunk of retail; cheap inclusivity. |

---

## 🥇 Ranked backlog (do in this order)

**Now (2 weeks) — funnel + tail**
1. **K1** `/ticker/{TICKER}` hubs (+ `/drug/{name}`) — biggest SEO+UX win
2. **K2** Watchlist + add-to-calendar + weekly email digest — the missing retention loop
3. **U1** Mobile: hamburger, 44px targets, sticky filters
4. **K3** `/about` + corrections log + "last verified" stamps

**Next (month 2) — moat as pictures + audience**
5. **"Similar past events"** module (the killer on-brand feature)
6. **U2/U3** heatmap + cohort distribution
7. **S7** outcome/"what happened" pages
8. **S3/S4** run-up report + embeddable widget (backlink engine)
9. **U4** logomark + per-event OG cards

**Then (month 3) — asymmetric bets**
10. **S2** AEO/`llms.txt` — get cited by ChatGPT/Perplexity
11. **S5/S6** evergreen link-magnets + comparison pages
12. Pro alerts + API webhooks (per the API spec)

---

## The Kaizen thesis in one line
We've won the **product**; we're losing the **funnel and the tail.** Ship company hubs + a watchlist + alerts, prove accuracy in public, render the run-up moat as pictures, and let LLMs quote us — and pdufa.bio stops being the best-kept secret in biotech catalysts and becomes the default.

---
*Verified live 2026-07-10 (cache-busted). Facts and historical statistics only — no per-drug approval probabilities. Not investment advice.*
