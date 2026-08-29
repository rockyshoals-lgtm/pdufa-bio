# BUILDER NOTE — Stock Reaction Tracker: how to use it, and how to fix it

**Date:** 2026-08-29
**Subject file:** `C:\Users\dcmoo\Documents\Python\9realms\Odin Perfection\stock_reaction_tracker.html`
**Full audit:** `2026-08-29h_stock_reaction_tracker_provenance_audit.md` (same folder)
**Status:** DO NOT SHIP AS-IS. Do not quote its numbers. Read section 1 before touching anything.

---

## 1. The one thing to understand first

**Every number on that page is hardcoded into the HTML.** There is no data file behind it. No JSON, no CSV, no database, no build script. The tables, the metric cards, the calibration points, the bar chart — all of it is literal text typed into the markup on 2026-05-20 and untouched since.

So: **editing the page means editing numbers by hand, and the page can never refresh itself.** If you were expecting to point it at a fresher dataset, there is no seam to point.

The only live wiring is the quote refresh, and it is bound to a hardcoded connector UUID (`mcp__50fc209a-b685-46dc-ac20-834d9779a062__quote`) captured from whichever session authored the file. Today the same FMP server is exposed under a different name. Assume the Refresh button is dead until you prove otherwise.

## 2. It is not an artifact, and it is not live

It has never been published. It is not in the claude.ai artifact gallery and `list_artifacts` does not exist as a tool. It was written against `window.cowork.callMcpTool`, the **Cowork desktop artifact runtime**, so it only ever ran inside a desktop Cowork session. Anyone asking to "open the live tracker" is describing something that does not exist yet.

## 3. Known defects, in priority order

**P0 — find the missing tenth event.** The metric cards and the miss-attribution chart both aggregate over 10 events. The fired table lists 9. Direction accuracy is claimed as 6/10 but the table supports 5/9; magnitude is claimed 3/9 but the table supports 2. One event was dropped from the table and left in every total. Until that is resolved, no headline number on the page can be quoted anywhere.

**P0 — the forward table is 101 days stale and wrong.** MNKD was approved 2026-05-29. CRDF held ASCO 6/2. **CAPR's PDUFA moved from 2026-08-22 to 2026-11-22** (see `2026-08-29e_DATA_MOAT_and_NAV_FREEZE.md`) and the page still shows the old date with a "T-7 = Aug 13" exit that is now in the past. The days-to-catalyst counts are hardcoded integers, not computed — they were correct only on the day they were typed.

**P1 — resolve the accuracy contradiction.** The page footer says GUNGNIR v46's 0.8135 and BIFROST v5.5's 0.9487 were **retracted**, replaced by honest 0.6150 and 0.7447. The standing 9 Realms spec still carries the original figures as champion numbers. Two contradictory sets are in circulation. This needs David's explicit ruling, not a builder's judgment call — pick one and propagate it everywhere.

**P2 — check the Brier baseline label.** The card benchmarks against "honest v38.1 baseline 0.0895", but 0.0895 is the ODIN **v14** holdout Brier. Probably a copy-paste error.

**P3 — sample size honesty.** Four of the five calibration bins contain exactly one event. Either widen the window until the bins are populated or label the chart as illustrative.

## 4. How to actually fix it — recommended shape

Split the page from its data. Concretely:

Write a `stock_reaction_tracker.json` into the dropbox (or `odin_data/`) holding the fired events, forward positions, and derived metrics, and have a small builder script emit the HTML from it. Then the metrics stop being typed and start being **computed** — which by construction makes the 5.1 off-by-one impossible to reintroduce, because the count and the rows come from the same array.

Derive the forward table from the canonical catalyst dataset rather than a frozen copy, so a PDUFA date change like CAPR's propagates instead of rotting. Compute days-to-catalyst in JavaScript from the event date and `Date.now()` rather than baking an integer.

Replace the UUID-bound quote call with the current FMP tool name, and wrap it so a failure renders "quotes unavailable" rather than leaving `--` in every cell with the reason buried in the console.

If it should be genuinely live and shareable, publish it as a proper artifact with a capability that keeps state, rather than a local file that has to be opened by path.

## 5. Tooling gotchas on this machine

**The Filesystem MCP server is broken in Cowork sessions.** Every `mcp__remote-devices__Filesystem__*` call fails before running with an invalid-outputSchema error — it declares JSON Schema draft-07 and the validator only accepts 2020-12. This is server-wide, not per-tool.

**Use `Windows-MCP` instead.** Its `FileSystem` (modes: read/write/list/search/info/copy/move/delete) and `PowerShell` tools both work normally and are what located and read this file.

**Reading large files:** `Get-Content -Tail` and the FileSystem `limit` parameter both appear to be ignored — INDEX.md came back whole (~89 KB) either way and blew the output cap. Slice large files on the Windows side into a temp file first, or accept the overflow-to-disk and slice it there.

**Folder connection is not required.** Windows-MCP reached the disk with no folder connected to the session.

---

*Filed per Amendment 033. Questions to David before changing any number on that page — several of these are rulings, not builds.*
