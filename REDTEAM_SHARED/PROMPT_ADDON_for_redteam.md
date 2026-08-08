# >>> PASTE THIS BLOCK AT THE TOP (OR BOTTOM) OF YOUR RED-TEAM PROMPT <<<

## 6. Shared Workspace (read this FIRST — do not ask the user to paste anything)

You are collaborating with a second Claude ("the builder") through a shared folder. Everything you need is there or on the live site.

**Before you audit, READ these files (they exist on this machine):**
- `C:\Users\dcmoo\Documents\Python\9realms\REDTEAM_SHARED\FROM_CLAUDE\00_STATE_OF_PLAY.md` — what's live, what's gated (with the password), what's ALREADY been fixed (don't re-flag those), known-open items, and hard guardrails.
- `C:\Users\dcmoo\Documents\Python\9realms\pdufa_bio_LAYOUT_AUDIT.md` — full screen-by-screen IA + markup of the gated web dashboard AND mobile app (use this to audit the gated UI's layout).
- `C:\Users\dcmoo\Documents\Python\9realms\REDTEAM_SHARED\_implemented\` — anything already shipped from prior findings (skip these).

**Inspect the live product directly:**
- Public (no login): https://pdufa.bio/ , /calendar , /decisions , /methodology , /fda-approval-rate , /clinical-trial-success-rates , and per-event pages like /pdufa/UNCY , /pdufa/LLY , /pdufa/NVS , /fda-decision/CAPR-2025-07-11 . Also /sitemap.xml , /robots.txt .
- Gated interactive product — **web dashboard** https://pdufa.bio/today and **mobile app/PWA** https://pdufa.bio/app . Access pass: `odin9realms-DUzX0EezWapap-fRnlkK8A` (enter on the landing's "Have an access pass?" box, or directly on /today and /app). On mobile, /app is installable.

**WRITE all your findings to:**
`C:\Users\dcmoo\Documents\Python\9realms\REDTEAM_SHARED\FROM_REDTEAM\` — one dated Markdown file per pass (e.g. `2026-06-19_pass1.md`), in the exact output format defined in this prompt (Executive Summary → Competitor table → User Jobs tables → SEO/IA + example title/H1 → Web UX teardown → Mobile UX teardown → **Top 10 ship-next checklist**). Make each finding specific enough that an engineer can implement it without a follow-up question (exact copy, exact element, exact value).

**Coordination rules:**
- A prior red-team ("HEIMDALL") already ran; its fixed items are in `00_STATE_OF_PLAY.md` → "Already addressed." Do NOT re-flag resolved issues — spend your fire on what's still open.
- You don't need screenshots from the user — read the LAYOUT_AUDIT doc and hit the live URLs yourself.
- The builder will read `FROM_REDTEAM/`, implement, and log results to `_implemented/`. You can re-audit after each build pass.
