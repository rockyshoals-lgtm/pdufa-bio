# pdufa.bio — STATE OF PLAY (for the Red Team) · 2026-06-19

Read this first. It tells you exactly what's live, what's behind the gate (with the password), what's already been fixed, and what's still open. Audit the live product directly — most of it is public.

## 1. How to inspect everything

### Public (no login — crawl/inspect directly)
- **Landing (coming-soon teaser):** https://pdufa.bio/
- **PDUFA calendar hub:** https://pdufa.bio/calendar
- **FDA decisions archive:** https://pdufa.bio/decisions
- **Methodology / "facts not advice" wedge:** https://pdufa.bio/methodology
- **FDA approvals by year & commissioner:** https://pdufa.bio/fda-approval-rate
- **Clinical trial success rates by phase:** https://pdufa.bio/clinical-trial-success-rates
- **Per-event pages (86 of them):** e.g. https://pdufa.bio/pdufa/UNCY · /pdufa/ARQT · /pdufa/LLY · /pdufa/NVS · /pdufa/ABBV-rinvoq · /pdufa/VRTX
- **Historic decision pages (20):** e.g. https://pdufa.bio/fda-decision/CAPR-2025-07-11 · /fda-decision/REPL-2025-07-22
- **sitemap:** https://pdufa.bio/sitemap.xml (112 URLs) · **robots:** https://pdufa.bio/robots.txt

### Gated (the real interactive product — password required)
- **Web dashboard (Today / Historic):** https://pdufa.bio/today
- **Mobile app / PWA (Radar · Calendar · Watchlist · History · More):** https://pdufa.bio/app
- **Access pass:** `odin9realms-DUzX0EezWapap-fRnlkK8A`
  (On the landing, the "Have an access pass?" box unlocks both; or enter it directly on /today and /app.)

### Reference docs already in the repo (read these for the gated UI's structure)
- `../../pdufa_bio_LAYOUT_AUDIT.md` — full screen-by-screen IA + (data-trimmed) markup of BOTH the web dashboard and the mobile app. **This is the best artifact for auditing the gated app's layout.**
- `../../pdufa_bio_FULL_SITE_AUDIT.md` — full engine + front-end source.
- `../../HEIMDALL_RedTeam_Agent_Charter.md` — the prior red-team's charter.

## 2. What the product is
A **facts-not-advice** biotech FDA-catalyst tracker. Surfaces: a public SEO content layer (calendar/decision/explainer pages) + a gated interactive web dashboard + an installable mobile PWA. Differentiators: live price + options (implied move vs cohort), T-120 run-up charts, cohort base rates by market-cap tier (history, NOT predictions), ClinicalTrials.gov "Silent Shift" date-change monitoring, a source-verified historic decision archive with primary-source links + validation badges, auto-refresh ~5×/day.

## 3. Already addressed (do NOT re-flag these — they're shipped)
- 3-line "tape" cards; month-grouped calendar; Status filter (All/Pending/Decided).
- VOL wording = "Vol rich/low vs cohort" (not "cheap"); "High relative premium" filter (not "Vol >1.5×" / "Signals").
- Cohort LOA/hist-move collapsed behind a "Base-rate context ›" details on both web + app; labeled history-not-prediction.
- Structured source taxonomy (`source_type/detail/conf`) + date taxonomy (`date_kind` → PDUFA(FDA)/(company-guided)/(registry est.)) with confidence dot + "Sourced:" line.
- Historic validation badges (✓ source-verified / ~ probable price-only / ⚠ unverified/mislabel) on cards AND inline in the app detail header; "↗ View primary source" links; experimental banner on Historic.
- First-visit facts-not-advice modal (localStorage-gated, blocks interaction).
- Pinch-zoom restored (removed user-scalable=no). Charts fixed (no clipping; aspect-ratio pinned; ±18% headroom so the low price label isn't cut off).
- App: Radar "High visibility" group carries subtitle "…not as trade ideas"; 3-chip cap + "+N more"; History tab with charts/reasons/source links; search placeholder "Search ticker, drug, or trial…".
- PWA: manifest + icons + service worker (now network-first) + "Remember me" gate so the installed app opens straight to Radar.
- Gate is self-contained (crypto inlined, no CDN) so it loads on any device/network.
- SEO foundation: landing indexable + Organization/WebSite JSON-LD; per-page FAQ + Breadcrumb schema; OG/Twitter; canonical; sitemap; robots; noindex scoped to ONLY /today and /app.
- Vercel Pro; apex pdufa.bio live; Google Search Console verified + sitemap submitted.

## 4. Known-open / in-flight (good places to aim)
- **Phase-readout calendar** (/readouts) is scaffolded but **not yet populated** — a full primary-source crawler run (SEC + ClinicalTrials.gov across 666 tickers) is running now; readout pages + a quantified "stock-move-by-phase" dataset land when it finishes.
- **Historic pages:** only 20 of ~694 generated so far (source-verified subset); deep long-tail expansion pending.
- **Alerts / "what changed since last visit" / Silent-Shift push** — not built yet (HEIMDALL flagged as the #1 retention gap).
- **Contrast/accessibility:** muted text (`--mut2:#7890b3` on card) and small status type may fail WCAG AA; green/red is still the primary status channel (colorblind risk) — only partially mitigated with ✓/✗ glyphs.
- **Landing "look inside":** the landing has no interactive preview for cold visitors beyond the coming-soon teaser + explore links.
- **Web/app are two separate codebases** (today.html / app.html) and can drift.
- Mobile tooltips are `title=` (desktop-only) — caveats/sources don't show on tap on mobile.

## 5. Hard guardrails (any rec that violates these is rejected)
No buy/sell calls. No per-drug approval-probability %. No composite bullish/bearish scores. No generic full-market options terminal (options context must stay catalyst-scoped). Not affiliated with/endorsed by the FDA. Real data + honest provenance only; "experimental" labels stay until source-verified.

## 6. What we want from you
The full audit in your prompt's format (Exec summary → Competitor table → User jobs (retail/trader/institution) → SEO/IA + example title/H1 → Web UX teardown → Mobile UX teardown → **Top 10 ship-next checklist**). Be brutal and concrete. Competitors to weigh us against: BioPharmaCatalyst / BPIQ / BiopharmaWatch / FDATracker, Unusual Whales, and any biotech-native intel tools you know.

**Write your findings to `../FROM_REDTEAM/<date>_<pass>.md`.** The builder chat reads that folder and ships from it, logging what it implements into `../_implemented/`.
