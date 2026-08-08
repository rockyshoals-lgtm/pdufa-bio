# pdufa.bio — RED TEAM ⇄ BUILDER war room

Two Claude sessions collaborate through this folder:
- **RED TEAM** (the 3-persona panel in the other chat) — audits and proposes.
- **BUILDER** (the implementation chat) — reads findings here and ships them.

## Protocol
- **RED TEAM writes findings to:** `FROM_REDTEAM/` — one dated Markdown file per pass, e.g. `2026-06-19_pass1.md`. Use the output format in your prompt (Exec summary → competitor table → user-jobs → SEO/IA → web UX → app UX → Top 10). Be specific enough that an engineer can implement without a follow-up.
- **BUILDER writes context + status to:** `FROM_CLAUDE/` — start with `00_STATE_OF_PLAY.md` (what's live, what's gated, what's already fixed, guardrails). BUILDER updates `FROM_CLAUDE/STATUS.md` as items ship.
- **Shipped items move to:** `_implemented/` (BUILDER logs what it implemented from each red-team finding, with the date + result), so RED TEAM doesn't re-flag resolved issues.

## Don't duplicate prior work
A first red-team ("HEIMDALL") already ran. Its charter is `../HEIMDALL_RedTeam_Agent_Charter.md` and the items already fixed are listed in `FROM_CLAUDE/00_STATE_OF_PLAY.md` → "Already addressed." Read those first; focus your fire on what's NOT yet resolved.

## Hard guardrails (never recommend violating)
Facts, not advice. No buy/sell calls, no per-drug approval probabilities, no composite bullish/bearish scores, no generic options terminal. Not affiliated with the FDA. Real data + honest provenance only.
