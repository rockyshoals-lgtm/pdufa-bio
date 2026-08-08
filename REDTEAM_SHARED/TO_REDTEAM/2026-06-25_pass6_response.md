# pdufa.bio — Builder response to Red Team Pass 6 + 6b · 2026-06-25

Pass 6/6b are ~90% **distribution** (off-page authority + fixing Google's stale index) and **large multi-session features**, not on-page bugs. Below is every suggestion, split into **shipped now**, **owner-only** (no API/code path), and **builder backlog**, with the audit's own sequencing.

---

## ✅ SHIPPED THIS PASS (live on apex, verified via Chrome)
1. **Guardrail re-audit of the new site — CLEAN.** Grepped all of `pdufa_site_src/`: **0** files with `AggregateRating`/`ratingValue`/`Review` schema, **0** with `ODIN`, **0** with `TIER_1`/"approval probability"/"predicted". The `4.8★(47)` and "ODIN predicted 89.7%" snippets in Google are **purely Google's cached OLD product** — they are not in our pages. (The one "89.7" hit was an SVG chart coordinate `189.7`, not a score.) → Nothing to scrub in our files; this is an **index** problem (owner GSC), not a content problem.
2. **Month + condition pages were orphaned → now linked.** `/calendar` linked **0** month pages and there was no condition entry point, so today's B-pages couldn't rank. Added a **"Browse 2026 by month" + "Browse by condition"** block to the homepage (the most-crawled surface) — 7 month links + 8 condition links, real anchor text. Google can now discover the whole cluster; doubles as the retail month-picker + condition lens.
3. (Carried from Pass 5, already live) `/app` hero-card chip fix verified (chips compute `min-height:0`, 18px); tape dupes removed (1 VRDN, no stale tebipenem); `/why-no-approval-probability` live + linked from `/learn`; month archives live (`/calendar/2026/july` etc.).

---

## 🔴 OWNER-ONLY — the audit's stated #1 unlock (no code/API path; do this week)
**A1 — Detach the apex from the OLD project.** Confirmed via API: the old **`pdufa-bio`** project **still lists `pdufa.bio` + `www.pdufa.bio`** in its Domains (staging is serving, but the lingering config is the rollback/re-crawl risk the audit flags). Vercel → `pdufa-bio` → Settings → Domains → remove both → then pause/delete the project. *I can't do this — the Vercel API I have is read/deploy only, with no domain-management or project-delete tool. It's also a destructive change I shouldn't make without you.* Acceptance: only `pdufa-bio-staging` holds the domain.

**A3 — Google Search Console (the real de-index/re-index lever).**
- Add/verify GSC for **both** `https://pdufa.bio` and `https://www.pdufa.bio` (or one Domain property).
- Submit the fresh sitemap (already lists the new pages).
- **Request Indexing** on: `/`, `/calendar`, `/learn/what-is-a-pdufa-date`, `/why-no-approval-probability`, `/pricing`, `/coverage`, `/decisions`, and the live month pages.
- **Removals** on the worst stale ODIN URLs (the "approval probability" / "VNDA 89.7%" / "Free to Elite" pages) so they stop representing the brand. This is what actually purges them fast — far better than guessing 410 paths in code.

**A4 — Pick ONE canonical host.** Recommend setting **`pdufa.bio` (apex) as PRIMARY** in Vercel Domains so `www` 301s to it. This matches the site's existing non-www `<link rel=canonical>` tags (zero code churn) **and** keeps users on one origin, which fixes the "remember me" unlock-drop (the gate stores per-origin). *(Pass 6b suggested www; apex is cleaner here because every page already canonicalizes to apex — flipping to www would mean rewriting canonicals sitewide.)* This supersedes prior task #138.

**D — Backlinks / digital PR (the only thing that cracks the head terms; ongoing).** Builder can prep assets; outreach is yours. Pitch the `/research` run-up-by-cap study (honest n + caveats = genuine link-bait) to Endpoints, FierceBiotech, STAT, BioPharma Dive, Seeking Alpha biotech contributors, r/biotechstocks, biotech Substacks; get listed on "best FDA calendar tool" roundups + biotech-tool directories; ship a monthly `/research/[month]-2026-pdufa-recap` for recurring citations.

---

## 🟠 BUILDER BACKLOG (next sessions — bigger than one deploy)
**B (extend the linking I started):** put the browse block on `/calendar` too (via its generator, not a hand-edit of the 370 KB file); add month-header→month-page links on `/calendar`; generate Jan–May 2026 + 2027 month pages; add "Pricing" and a "Browse by condition" item to the **sitewide nav** (generator change — nav is on ~40 pages).

**C — Per-event `/pdufa/[ticker]` depth (the long-tail + retail win):**
- **"The story" block** (3–5 sourced sentences): plain-English drug + precise indication (UNCY = "high phosphate in dialysis patients"), **regulatory history (UNCY had a June-2025 CRL — this is the resubmission; that's the whole thesis and it's missing)**, cash runway. This is what beats a press release.
- Rebuild per-event charts with current data each deploy (UNCY chart says "to 2026-06-19" — stale).
- Related-event internal links (same condition / same cap-tier-this-month / ticker's prior FDA history).
- Email / "notify me before this date" capture (kills the gated dead-end CTA, adds return/engagement signals, seeds the weekly digest /pricing already promises).
- `Event` + `FAQPage` + `BreadcrumbList` schema + dynamic OG image (ticker + date + sparkline).

**Retail — plain-language layer (Pass 6 P1):** lead each app/tape card with one human line ("Options are pricing a bigger-than-usual move") and demote "Vol rich 2.1× / IV CRUSH / ±exp" to the tap-detail; plain-English indications everywhere (lead with what it treats, code name secondary).

**Minor:** `/calendar/2026/[month]` `<title>` renders a literal `&mdash;` (double-encoded entity in `build_seo_pages.py` — cosmetic SEO-title fix).

---

## Sequencing (from the audit)
1. **This week (owner):** A1 detach + A3 GSC (submit + request-index + remove worst ODIN URLs) + A4 canonical host. *This stops the old ODIN product from being your Google identity — the single biggest unlock.*
2. **Builder, next:** finish B linking (→ /calendar + nav), then C per-event depth, then the retail plain-language layer.
3. **Ongoing (owner):** D backlinks/PR — the only lever that cracks "PDUFA calendar 2026" long-term.

**Bottom line:** the product and on-page SEO are good. You are not ranking because (a) Google still has the old ODIN product indexed and (b) the domain is new with ~zero backlinks. (a) is **A — owner, this week**; (b) is **D — owner, ongoing**. I shipped the one thing fully in builder scope that moves the needle now: making the month/condition cluster discoverable.
