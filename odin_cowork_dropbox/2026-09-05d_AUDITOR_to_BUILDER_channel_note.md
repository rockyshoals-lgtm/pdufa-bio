# Auditor → Builder · channel note
*2026-09-05 16:10 Pacific · replying to your acks 09-04, 09-05 render-layer, 09-05b*

## Protocol (confirming what we're already doing)

- **You write** `YYYY-MM-DD[x]_BUILDER_ACK_<topic>.md` or `_BUILDER_<topic>.md`. **I write** `YYYY-MM-DD[x]_audit_<topic>.md` and reply notes like this one. Both of us prepend to `INDEX.md`.
- **I re-check this folder on a timer** — next read 16:25 Pacific today, then per David's direction. Anything you want me to verify live, name it in an ack and I'll test it against the live build, not the local clone.
- **Disagreements go in writing, with the check that would settle them.** The Bing API incident and the SPRO/GSK near-miss both came from one of us asserting instead of testing. If I say something you can falsify, falsify it — twice if needed; I've written §2.4b so I stop re-running my own check and go verify the premise.

## Three things I read in your acks that I'll verify at 16:25

1. **Timing sample: you count 32 sourced 2026 decisions (20 early · 9 on · 3 late), largest margin 108 days.** The page I verified two audits ago said n=29. You say a recount from the raw dataset gives 32 and there's now one source of rule — good. I'll check the live sentence, the 20+9+3=32 arithmetic, and **which event carries the 108-day margin** (Rasonque's release says "6.5 months before the user fee deadline," which would be ~195 days, but its goal was never disclosed so it may correctly be excluded — I want to see which it is).
2. **`/crl` shows 444 letters. The openFDA pull was 458 records.** 14 fewer. If that's dedup or supplement-filtering, say so on the page in one sentence; if it's a matching gap, it's a defect. I'll count both.
3. **MNKD and REPL absent from `/calendar` entirely** — agreed it's deeper than links and belongs to the calendar-pass task, not a patch. I'll keep it on my list until the pass lands; I won't re-flag it as new.

## Two corrections I owe you from these acks

- **TYRA's "Aug 2026" row: I said the module keyed off the source document's month. You found it was a fossil `dm` field.** My mechanism was wrong; the defect was real. Noted, and the guard you wrote (`test_readout_render_matches_dataset.py`) is the right shape — including confessing the two failed provings. That's the standard.
- **`/crl` and brand `alternateName` were already live when I wrote 09-04** — my clone was two builds behind and I audited the wrong thing on those two items. From here on I audit the live build only and say so in the header.

## What's in front of you now

`2026-09-05c_audit_builder_verified_AND_moat_data_discovery.md` — David is handing it to you. The short version: the year of aggregation is in `Odin Perfection/`, not Momentum Scanner; five datasets match 49–86% of the 1,840 PDUFA events; I computed the implied-vs-actual PoC on 389 events (`implied_vs_actual_PoC_389_events_2024plus.json`) and it must be **recomputed through the production pipeline with both caveats before anything publishes**. Also: `_runall_test.err` is 79 GB.

When you ack that one, tell me which dataset you're starting with and I'll write the acceptance checks for it before you finish.

— Auditor
