# 04 — UI polish: pre-market styling + richer tiers

**Goal:** Make the pre-market board and the new tier system legible; keep the dark card aesthetic.

**Data source:** Fields already emitted by `/api/surges` and `/api/premarket`: `tier` (legacy),
`tier_new` (PRIME/BUILDING/WATCH/NOISE), `pm_move`, `flags` (ROCKET, VOL_NO_PRICE, EXHAUSTION_RISK,
CONTROLLED, THIN_QUOTE), `cont_odds_pct`, `relvol`, `odds_basis`, `odds_n`.

**Logic / UI:**
- Add badge styles + labels for PRIME/BUILDING/WATCH/NOISE (use `tier_new`); keep legacy fallback.
- Distinct header/accent when in pre-market mode; show the pre-market illiquidity disclaimer.
- Surface flags as chips; ROCKET gets the pulse/alert treatment, EXHAUSTION_RISK/THIN_QUOTE a caution color.
- Optional: small status line showing ADV-map freshness (`adv_map_built`) and `relvol_enabled`.
- Keep the "how to read" note updated to the unbiased-base-rate + pre-market framing (already patched).

**Acceptance criteria:**
- [ ] Renders < 1.5s; no layout break on mobile.
- [ ] Empty feed (no gappers / off-hours) handled gracefully with a note.
- [ ] Tier badges + flags styled consistently; disclaimers present.

**Priority:** P1.

**Deploy / key needs:** Static (`surges.html`), no key. Owner-gated deploy.
