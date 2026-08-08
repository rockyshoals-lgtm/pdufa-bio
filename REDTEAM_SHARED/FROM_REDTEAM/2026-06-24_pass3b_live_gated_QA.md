# Pass 3b — LIVE gated QA of /today + /app (finally eyes-on) · 2026-06-24

Chrome bridge is connected now, so I logged into the gated build (owner entered the pass) and inspected the rendered `/today` dashboard and `/app` PWA on a phone viewport (412px). Screenshots taken. This is the visual QA I couldn't do passes 1–3.

## ✅ Verified fixed on the rendered UI (not just markup)
- **LOA tile is gone from the tape card.** The 4th facts tile now reads **"X vol"** (avg daily volume) — e.g. GSK `$51.05 · $104.0B · 16mo · 4.0M vol`. No "LOA %" anywhere on a card. The #1 guardrail fix is real on-screen.
- **Today/Historic segmented control** — distinct filled-gold toggle, clearly separated from the filter chips. Good.
- **Tap-popovers fire (desktop).** Clicking the "VOL RICH VS COHORT" chip pops the full caveat ("…Context about premium, not a guarantee of move size or profit/loss, and not a trade recommendation"). #3 confirmed.
- **Detail sheet (mobile) is excellent and compliant.** Order: header + "Sourced:" → T-120 run-up chart (renders cleanly, green high / red low labels) → Drug → Facts (price/mcap/cash — **no LOA**) → Options (ORATS) → Registry (NCT link) → **collapsed "Base-rate context (LOA & hist. move) ›"** → not-advice footer. LOA correctly lives only in the collapsed section.
- **Historic view** — experimental banner + T-120 charts per card render well.
- **"This week" / "Next 30" rows on /app render perfectly** — compact, horizontal chips (Vol rich / IV CRUSH / ±exp), clean T-minus pills.

## 🔴 NEW — launch-blocking mobile bug: hero "Decisions — today & just in" cards are broken
- **What:** On `/app` Radar, the gold **hero/decided** cards (GSK, SPRO = ✓ Approved) render their chips (`✓ Approved`, `Vol rich 2.1×`, `±2.1% exp`) as **full-height vertical bars** — green/brown columns ~400px tall — blowing each card up to ~500px. It's the **first thing** a user sees in the app, and it's grotesque.
- **Scope:** ONLY the `.row.hero` cards in "Decisions — today & just in." Every normal row (incl. ACHV "date passed" and the entire "This week" section) renders fine. The **web `/today` cards are fine** — this is app-only + hero-only.
- **Likely cause:** the hero variant (applied via `row(...).replace('class="row','class="row hero')`) is letting the chips' flex container stretch — `align-items: stretch` on a card that's tall because of some sibling element (a chart/empty container?) on decided hero cards. Chips have no fixed height, so they stretch to the card's full height. Fix: pin the chips row to `align-items:center; align-self:flex-start` (or give `.chips`/`.cc` an explicit height / `flex:0 0 auto`), and check what's making the hero/decided card tall.
- **Repro:** open `/app` at mobile width with ≥1 Approved/CRL event in "today & just in."

## 🟠 NEW — `—` rendering bug in BOTH first-run modals
- The facts modal shows **"PDUFA.BIO `—` FACTS, NOT ADVICE"** and button **"I understand `—` show me the facts"**; the Historic modal shows **"HISTORIC DECISIONS `—` EXPERIMENTAL."** The `—` escape is being printed literally instead of an em-dash (—). It's the literal first text every new user reads on both Today and Historic. Fix: use the actual `—` character (or `—` in a JS string that's parsed, not a literal in HTML/text).

## 🟡 Carry-overs confirmed visually
- Header still says **"Live ORATS + FMP · LIVE · 2026-06-24 17:47 UTC · auto-refresh ~5×/day"** — the "LIVE" wording (W6) is still there; reconcile to "Snapshot · updated <time>."
- **"Sourced:" line** is still the faintest text on the card (contrast improved elsewhere). Promote it to a tappable chip (M3).

## Priority for the builder
1. **[P0] Fix the /app hero-card chip-stretch bug** (§ above) — it's the first screen of your mobile app and it's broken.
2. **[P0] Fix the `—` literal in both modals** — trivial, but it's the first impression.
3. **[P1] "LIVE" → "Snapshot · updated <time>"**; promote "Sourced:" chip.

Everything else from Pass 3 (purge `/` cache, detach old domain, `/readouts` on-site pages + drug names, calendar dupes) still stands. Net: the gated product's substance and compliance are verified-good; it's gated on two visible front-end bugs (one launch-blocking) and the Pass-3 items.

*— Red Team Pass 3b (live eyes-on via connected Chrome).*
