# pdufa.bio — RED TEAM RE-AUDIT · Pass 5 (live via Chrome) · 2026-06-24

Re-audited live in Chrome after "changes live." Verified the public surface unauthenticated and the gated `/app` (owner unlocked).

## ✅ Verified fixed live
- **CDN cache purged — the #0 launch-blocker is CLEARED.** Bare `pdufa.bio/` now serves the fresh build (keyword title, "LIVE · PRIVATE BETA," the "A LOOK INSIDE" preview tape, clean rows) and bare `/calendar` serves the de-duped co-listing + full nav. Three passes stuck; finally live.
- **`—` modal bug — FIXED.** Both first-run modals now render proper em-dashes ("PDUFA.BIO **—** FACTS, NOT ADVICE" / "I understand **—** show me the facts").
- **W6 "LIVE" wording — FIXED.** The `/app` header now reads **"Snapshot · updated · 2026-06-25 17:22 UTC"** (was "LIVE"). Matches `/sources`. 
- **M1 (partial) — High Visibility** now carries the subtitle **"Highlighted for visibility, not as trade ideas"** (the advice-tone disclaimer). Still sits above "This week," but the disclaimer addresses the tone risk.

## 🔴 STILL BROKEN — P0 launch-blocker: hero-card outcome chip (partially fixed, not done)
- **What:** On `/app` Radar "Decisions — today & just in," the **Approved/CRL hero cards** (GSK, SPRO) still render the **colored outcome chip** (`.cc.app` green "✓ Approved" / `.cc.crl` red "✗ CRL") as a **full-height vertical bar**, and the card balloons to ~470px. It's the first screen of the mobile app.
- **What changed:** Your earlier fix worked on the *other* chips — "Vol rich 2.1×" and "±2.1% exp" now sit normally at the bottom. Only the **outcome chip** (`.cc.app`/`.cc.crl`) still stretches.
- **Proof it's outcome-chip-specific:** **ACHV** (decided but "date passed — outcome unknown," which uses the grey `.cc.mut` chip) renders **perfectly** — compact card, horizontal chips. Only the green/red outcome variants break.
- **Fix:** the `.cc.app`/`.cc.crl` chips (or their wrapper) are stretching — pin them `align-self:flex-start` and give the chips container `align-items:flex-start`; also find why the decided hero card has the extra height (an empty/zero-content flex child stretching to fill). Repro: `/app` mobile width with any Approved/CRL event in "today & just in."

## ⚠️ Still open — Pass 3 data-quality (not yet fixed; confirmed on live `/calendar`)
- **VRDN duplicate:** two rows on 2026-06-30 — "Veligrotug (VRDN-001)" and "VRDN-001" — same ticker/drug/indication (TED). Dedup on (ticker + normalized-drug + date).
- **GSK tebipenem double:** "GSK / SPRO · 06-18 Tebipenem HBr (approved)" AND "GSK · 06-30 Tebipenem pivoxil (pending)" — same product (Utebzi) shown as both decided and pending. Reconcile.

## ⚠️ Not shipped — Pass 4 P0 SEO moves
- **No month-archive pages / month-picker** (`/calendar/2026/[month]`, `/readouts/2026/[month]`). This is the #1 competitive SEO gap — **CatalystAlert is already ranking with `/pdufa/[month]-2026` month pages.** Still the top priority.
- **No "Why we don't show an approval %" page** — `/learn` still has the same 7 explainers. This is the flagship wedge against the AI-PoA field (CatalystAlert, BiopharmaWatch both publish per-drug PoA). Ship it.

## 🆕 New finding — apex↔www redirect drops the unlock session
- I unlocked on `pdufa.bio` (apex); the homepage 301'd me to `www.pdufa.bio` and the "remember me" unlock did **not** carry — forced a re-unlock. Real users bounced between hosts will be logged out.
- **Fix:** pick one canonical host and 301 consistently; scope the gate cookie to the registrable domain (`Domain=.pdufa.bio`) so it spans apex + www.

## Priority for the builder
1. **[P0] Finish the hero-card fix** — the `.cc.app`/`.cc.crl` outcome chips still stretch; it's the first screen of the app.
2. **[P0 SEO] Month-archive pages** (`/calendar/2026/[month]` + `/readouts`) — contest CatalystAlert's month-page SERP; doubles as the retail month-picker.
3. **[P1] "Why we don't show an approval %"** page — the wedge against the PoA field.
4. **[P1] Calendar dedup** (VRDN) + GSK tebipenem reconcile.
5. **[P1] Canonical host + `.pdufa.bio` cookie** — stop the apex/www logout.

**Net:** strong progress — the cache purge (launch-blocker) and three smaller fixes are live and verified. Two things gate launch: the **hero-card chip** (one CSS rule on `.cc.app`/`.cc.crl`) and shipping the **month pages**. Everything else is polish + the data dedups.

*— Red Team Pass 5 (live via connected Chrome; owner unlocked the gate).*
