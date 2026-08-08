# pdufa.bio — Pass 8 · Verify latest build + next actions · 2026-06-26

Re-audited live (Chrome + Vercel). **Big round: the two top structural SEO pages shipped.** Details + the new bugs that will limit them.

## ✅ SHIPPED this round (verified live) — strong progress
- **Month pages (B1) — LIVE.** `/calendar/2026/[month]` (e.g. `/calendar/2026/september`): H1, prev/next nav ("← August | October →"), a count chip, `FAQPage` schema that bakes in the no-PoA stance, and a "here's why" link. Top SEO move — done.
- **Condition pages (B2) — LIVE.** `/condition/[slug]` (e.g. `/condition/obesity` → `/condition/obesity-metabolic`), with a **cross-link chip row** to 7 sibling conditions (Cancer, CNS, Immunology, Cardiovascular, Rare Disease, Infectious Disease, Hematology). Winnable-vertical SEO + the retail condition lens — done.
- **`/why-no-approval-probability` — LIVE.** The wedge page against the AI-PoA field (CatalystAlert/BiopharmaWatch), linked from month + condition pages. Exactly right.
- **Old ticker URL handled:** `/vnda-pdufa` now **serves the new VNDA facts page** (Imsidolimab, 2026-12-12) with `canonical → /pdufa/VNDA`. The old ODIN "89.7% probability" content is gone there.
- **Nav consistency fixed:** Coverage + Pricing now appear in a unified nav across all templates (was 9 vs 5).

That's the highest-leverage structural work from the page-1 plan — credit where due.

## 🔴 NEW issues on the new pages (fix these or the new pages won't do their job)

**1. The new pages link OFF-SITE instead of to your own pages — this defeats their main purpose. (highest priority)**
Month-page rows link straight to `sec.gov`; condition-page rows link straight to `clinicaltrials.gov`. The entire SEO point of month/condition hub pages is to **funnel link equity into your `/pdufa/[ticker]` and per-readout pages** and keep users on-site. Right now they're donating both to SEC/NIH.
*Fix: every row links to the on-site `/pdufa/[ticker]` (or a `/readout/[id]`) page; the primary-source link lives *on* that detail page. Internal-link graph is the whole game.*

**2. Condition pages are mis-categorized — it undermines the curation wedge. (high)**
`/condition/obesity-metabolic` lists ophthalmology and unrelated drugs as obesity/metabolic: **"SBI-100 Ophthalmic Emulsion — Obesity"** (an eye drop, not obesity), Eylea / ranibizumab / EYP-1901 / Otx-Tki (diabetic-eye readouts), **"Enobosarm & Abemaciclib — Obesity"** (a breast-cancer combo), **"WVE-210201 — Obesity"** (a DMD drug). The keyword filter is matching "diabetic"/loose terms and producing a partly-wrong list. For a "curated, sourced" product, an eye-drop filed under "Obesity" is exactly the credibility hit you can't afford. *Fix: tighten the condition mapping (curated TA tags, not substring match); exclude ophthalmology-diabetic-eye from "metabolic."*

**3. Condition pages show only readouts, no PDUFA decisions — but the title says both.** Title: "FDA **Decisions** & Readouts," body: only "Trial readouts (35)." Obesity has real PDUFA decisions (CagriSema, tirzepatide). *Fix: add the PDUFA-decisions section, or fix the title.*

**4. Title double-escape bug on month pages.** `<title>September 2026 FDA PDUFA decisions &amp;mdash; FDA Calendar</title>` — the `&mdash;` is double-escaped, so the SERP/tab shows a literal "**&mdash;**." (Same class as the old `—` bug.) *Fix: emit a real "—".*

**5. Month-page data ≠ main `/calendar` data.** `/calendar/2026/september` lists 4 events (TLX 177Lu-TLX591, NUVL Neladalkib, RARE UX111, MIRM zilurgisertib) with SEC links; the main `/calendar` September section lists ~12 (TLX **TLX101-Px**, NUVL/RPRX Zidesamtinib, MRK WINREVAIR, IONS…). **Two different datasets for the same month** — the month pages look newer/SEC-sourced, the main calendar older. Users/Google see conflicting "September 2026" lists. *Fix: one source of truth; regenerate `/calendar` from the same (newer) data as the month pages.*

**6. Condition pages have no JSON-LD schema** (month pages have `FAQPage`; condition pages have none). Add `ItemList` + `FAQPage`.

**7. "· nan" rendering bug** on per-event pages: the CT.gov line shows "NCT05352893 **· nan**" (a NaN leaking into the status). *Fix: hide when status is null/NaN.*

**8. Copy bug:** condition description reads "obesity and metabolic **disease disease**" (duplicate word).

## ⚠️ STILL OPEN (carry-over — not addressed this round)
- **Per-event depth (Workstream C) — not done.** `/pdufa/VNDA`+`/pdufa/UNCY` still: stale chart ("Price path to **2026-06-19**"), no story block (CRL/cash/plain-English), dead-end "private beta" CTA, **no email capture** (even though `/pricing` promises a weekly digest), no related-event links. This is what makes the per-event page beat a press release — still the long-tail unlock.
- **Calendar dupes (since Pass 3):** VRDN twice on 06-30, GSK tebipenem approved-and-pending double. Still live.
- **Nav now 11 flat items** — consistency is fixed but it's overflowing; group into ~4–5 dropdowns (Calendar▾ / Decisions▾ / Learn▾ / Pricing).
- **Old ODIN-only URLs are 404, not 410** (`/track-record` etc.) — 410 deindexes faster.
- **Index still stale** (Google lag) — keep using GSC Removals on the worst old ODIN URLs.
- Plain-English indication layer (retail).

## NEXT ACTION ITEMS (prioritized)
1. **[P0] Re-point month/condition/readout rows to on-site `/pdufa/[ticker]` + per-readout pages** (not SEC/CT.gov). Without this, the new hub pages don't build your internal-link graph — the main reason to have them.
2. **[P0] Fix condition mis-categorization** (curated TA tags) — the eye-drop-under-Obesity problem; it's a credibility killer.
3. **[P1] Reconcile month-page vs main-calendar data** to one source; fix the `&amp;mdash;` title escape; add condition-page schema + PDUFA section + "disease disease."
4. **[P1] Per-event depth (C):** story block, fresh chart, email capture, related links, fix "· nan."
5. **[P1] Calendar dupes** (VRDN, GSK) + plain-English indications.
6. **[P2] Group the 11-item nav; 410 the dead ODIN URLs; keep GSC Removals going.**

## Verdict
The structural foundation for page-1 is now **built** — month pages, condition pages, and the no-PoA wedge page are the right moves and they shipped. The gap is now **quality and wiring**: the hub pages leak to off-site sources instead of feeding your own per-event pages, the condition filter is noisy enough to dent the curation wedge, and two datasets disagree. Fix the internal linking (item 1) and the condition data (item 2) and these pages start earning their keep. Then finish per-event depth (the long-tail closer) and the off-page PR push (the only thing that cracks the head terms).

*— Red Team Pass 8 (live verify via Chrome + Vercel).*
