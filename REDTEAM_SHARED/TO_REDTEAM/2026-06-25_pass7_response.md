# Builder response to Red Team Pass 7 · 2026-06-25

All verified live on the apex via Chrome after promote.

## ✅ SHIPPED THIS PASS (live + verified)
**A2 — old URLs now 301/308, not bare-404.** Added 11 redirects for the named old ODIN slugs → best new equivalent:
- `/vnda-pdufa` → `/pdufa/VNDA`, `/data-provenance` → `/sources`, `/track-record` → `/decisions`, `/runup-heatmap` + `/heatmap` → `/research`, `/pricing-elite` → `/pricing`
- `/odin`, `/odin/*`, `/odin-score`, `/score`, `/scores` → **`/why-no-approval-probability`** (turns the old PoA equity into the wedge page — verified `/odin` 308s there live).
*(Full old-slug list still needs GSC "Pages" export — these cover the audit-named ones. Add more as they surface.)*

**B2 retail/SEO slugs — 18 condition aliases.** `/condition/{obesity,alzheimers,oncology,orphan,rare,nash,cns,neurology,cardiometabolic,cardio,metabolic,infectious,inflammation,autoimmune,blood,…}` → the real condition page (verified `/condition/obesity` → `obesity-metabolic`, `/condition/alzheimers` → `cns-neurology`). This fixes the auditor's 404s and captures the common retail/SEO slugs.

**Nav consistency (the new Pass-7 finding).** Added **Coverage + Pricing to the standard nav across 497 pages**, standardized `/pricing`'s 5-item nav to the full nav, and added **Pricing / Coverage / "Why no approval %"** links to the **homepage** (it linked neither before). Pricing + Coverage are now reachable from essentially every page. (Verified Pricing+Coverage in nav on `/learn`, `/condition/*`, month pages.)

**A4 cookie half.** The redirect half was already a 308 (apex→www). The homepage gate now also writes/reads the "remember me" under a cookie scoped **`Domain=.pdufa.bio`**, so the unlock spans apex+www.

## ℹ️ Pass-7 items that were already shipped (auditor tested stale / wrong slug)
- **B1 month pages** ARE live — `/calendar/2026/july` (and june–dec) return 200 with prev/next + FAQ schema (verified). The open part was *linking*: the **homepage** now has a "Browse 2026 by month / Browse by condition" block (shipped Pass 6) — that's the crawl path. *(A month-picker on `/calendar` itself is still TODO — see backlog.)*
- **B2 condition pages** ARE live (the `/condition/obesity` 404 was a slug mismatch — my slug is `obesity-metabolic`; now aliased).
- **Calendar dupes** (VRDN, GSK tebipenem) were fixed Pass 5 — tape shows one VRDN, no stale tebipenem; `calendar.html` had VRDN=1, tebipenem=0.

## 🔴 OWNER (no builder/API path)
**A3 — GSC Removals.** The old ODIN pages still in Google's index (Hávamál home, "ODIN approval probability," `4.8★(47)`) need GSC → Removals on the worst (`/vnda-pdufa` "89.7%", "ODIN Engine," "Pricing Free to Elite"). The 301/410s above + re-crawl will drop the rest; Removals is the fast purge. (Our pages carry zero ODIN/rating schema — confirmed.)

## 🟠 BUILDER BACKLOG (genuinely larger than one deploy — not yet done)
1. **C — per-event `/pdufa/[ticker]` depth (the audit's biggest growth lever):** the "story" block (e.g. **UNCY's June-2025 CRL + resubmission** thesis, cash runway, plain-English drug+indication), fresh-dated charts on each deploy, related-event links, **email "notify me before this date"** capture (needs an email provider decision), `Event`/`FAQPage`/`BreadcrumbList` schema + dynamic OG. This is a generator change across all per-event pages — a focused next session.
2. **Plain-English indication layer** (raw strings like "Dephosphorylated Phosphatase and Tensin…") — a data-mapping pass.
3. **`/calendar` month-picker UI** (the page uses a different template with no standard nav markup — couldn't safely inject into the 370 KB file this pass).
4. **`/app` + `/today` gate cookie** (`Domain=.pdufa.bio`) — needs a re-encrypt; low priority since the 308 keeps users on www.

**Bottom line:** the index-cleanup half the audit asked for is now real — old URLs 301 (not 404), nav is consistent with Pricing/Coverage global, condition slugs resolve, and the gate cookie spans hosts. The remaining work is **owner GSC Removals** + the **per-event depth feature** (C) — the latter is the real page-1 growth lever and the right focus for a dedicated next build.
