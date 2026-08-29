# Stock Reaction Tracker — Provenance, Data Sources, and Audit

**Date:** 2026-08-29
**Run type:** artifact_provenance + audit
**Requested by:** David (Cowork session, desktop "yo")
**Classification:** AMBER — file is real and useful, but 101 days stale, self-contradictory in its headline metrics, and its live-refresh path is almost certainly dead.
**Cross-refs:** README.md (dropbox conventions), INDEX.md, 2026-08-29e_DATA_MOAT_and_NAV_FREEZE.md, Amendments 027/028/031/032

---

## 0. The question that started this

David asked me to look up a live artifact called "stock-reaction-tracker" using `list_artifacts`, read its HTML, and summarize what it shows and where its data comes from. That framing turned out to be wrong in two ways, and the correction is the most important finding in this document.

---

## 1. WHERE THE FILE ACTUALLY LIVES

```
C:\Users\dcmoo\Documents\Python\9realms\Odin Perfection\stock_reaction_tracker.html
```

- **Size:** 14,296 bytes
- **Last modified:** 2026-05-20 19:27:16
- **Age as of today:** 101 days
- **NOT** in the claude.ai artifact gallery. **NOT** published. **NOT** a live artifact.

It is a plain HTML file sitting in the `Odin Perfection` folder alongside the master log and the immutable directives.

## 2. WHAT I COULD AND COULD NOT USE TO FIND IT

This matters for anyone repeating the exercise.

**`list_artifacts` does not exist in this session.** There is no such tool on the remote-devices bridge to "yo", and none among the deferred tools. The remote-devices server connected fine and exposed Filesystem, PDF Tools, Windows-MCP, Claude Browser, the 9Realms MCP, Perplexity, and ClinicalTrials.gov — but no artifact tools at all.

**The claude.ai artifact listing is empty.** I used the Artifact tool's own `list` action, scoped to both owned and shared artifacts. It returned nothing published and nothing shared. So the artifact gallery genuinely holds no "stock-reaction-tracker", which is consistent with the file having never been published.

**The Filesystem MCP server is broken in this session.** Every call to `mcp__remote-devices__Filesystem__*` fails before it runs:

> Tool '...' has an invalid outputSchema: JSON Schema declares an unsupported dialect ("$schema": "http://json-schema.org/draft-07/schema#"). The default validator supports JSON Schema 2020-12 only.

This hit `list_allowed_directories` and `list_directory` identically, so it is a server-wide schema-dialect problem, not a per-tool bug. **Workaround: use `Windows-MCP` `FileSystem` and `PowerShell` instead** — both work normally and were what actually located and read the file.

**No folder was connected to the session.** The device bridge reported "no folder is connected yet". Windows-MCP reaches the disk regardless of the folder-connection state, which is why the search succeeded anyway.

## 3. WHAT THE PAGE DISPLAYS

Title: *Stock Reaction Tracker — Odin Catalyst*. Subtitle describes it as prediction calibration versus realized D1/D5 returns, "Amendment 027 compliant".

**Six headline metric cards:** fired events tracked (10), direction accuracy (60.0%, "6 of 10 correct"), magnitude exact-match (33.3%, "3 of 9 with verified D1"), Brier score (0.351, flagged amber against a "honest v38.1 baseline 0.0895"), CATAS misses (1, TRDA −57.3%), and realized P&L impact ($0, annotated "Cardinal Rule saved us").

**Fired catalysts table (last 30 days)** — nine rows: TRDA, MIRM, AVTX, CADL, WVE, ALXO, AXSM, ARVN, LNTH. Columns are ticker, catalyst type, date, ODIN tier, P(positive), predicted bucket, realized D1 %, realized D5 %, a live-price cell, realized bucket, and direction/magnitude match marks.

**Forward catalysts table** — four rows: UNCY (PDUFA NTM004 UDC, 2026-06-27, entry 7.74), CAPR (PDUFA deramiocel DMD, 2026-08-22, entry 30.74), CRDF (ASCO 2026 calls, 2026-05-21, entry 2.40), MNKD (PDUFA T-9, 2026-05-29, watch only, no position). Each carries a days-to-catalyst count, tier, P(pos), entry price, a live-price cell, a live P&L cell, and a planned exit day.

**Two Chart.js charts:** a calibration scatter of predicted P(positive) against realized hit rate per 10% bin with a y=x reference line, and a horizontal bar chart of miss attribution across six causes (magnitude model gap 2, upside undercall 3, IIS low-dose guidance 1, earnings not binary 1, none/correct 2, data not verified 2).

**Footer** carries the compliance stamps (Amendments 027, 028, 031, 032), the Cardinal Rule, and an honest-accuracy line reproduced verbatim in section 6 below.

## 4. WHERE THE DATA COMES FROM — THE REAL ANSWER

**Almost all of it is hardcoded inline in the HTML.** There is no backing JSON, CSV, or database. Every number in the six metric cards, every row of both tables, every point in the calibration scatter, and every bar in the miss-attribution chart is a literal typed into the markup. The calibration bins even carry hand-written comments naming the constituent tickers (`{x: 0.65, y: 0.67}, // 0.60-0.70: AVTX, ALXO, MIRM — 2/3`).

The practical consequence: **the page cannot update itself.** It is a snapshot of what was true on 2026-05-20, and it will display those same numbers forever.

**The single dynamic element is live quotes.** A `loadQuotes()` function fires on page load and on the "↻ Refresh quotes" button. It requests a batch quote for all thirteen tickers and fills in the `data-tkr` price cells and the `data-pnl` forward-position P&L cells. The call is:

```js
window.cowork.callMcpTool("mcp__50fc209a-b685-46dc-ac20-834d9779a062__quote", {
  endpoint: "batch-quote-short",
  symbols: tickers
});
```

Two things follow from that line. First, `window.cowork.callMcpTool` is the **Cowork desktop artifact runtime API** — so this file was authored to run as a Cowork desktop artifact, not as a claude.ai artifact and not as a standalone page. That fully explains why it never appeared in the artifact gallery. Second, the tool name is bound to a **UUID-scoped connector ID** (`50fc209a-b685-46dc-ac20-834d9779a062`) captured from the session that authored it. In today's session the same FMP server is exposed as `mcp__FMP__quote` — a different name. Whether the desktop runtime still maps that old UUID is untested, but a hardcoded connector UUID is fragile by construction and is the most likely thing to have broken.

Everything else the footer cites — FMP `/stable/historical-price-eod-light` and `/stable/quote` for the D1/D5 history, and the "internal Odin Catalyst ledger" for tiers and probabilities — describes how the numbers were **originally derived by hand**, not a live wiring the page maintains.

**External dependency:** Chart.js 4.5.0 from `cdn.jsdelivr.net`, with an SRI integrity hash and `crossorigin="anonymous"`. This is well-formed and would survive publication as a claude.ai artifact, since jsdelivr `/npm/` is on the script allowlist.

## 5. AUDIT FINDINGS

**5.1 — The headline metrics do not reconcile with the table. (RED)**

The cards claim 10 fired events tracked; the fired table has **9 rows**. The cards claim direction accuracy "6 of 10 correct"; counting the direction column in the table gives **5 of 9** (MIRM, AVTX, CADL, AXSM, ARVN correct; TRDA, WVE, ALXO, LNTH wrong). The cards claim magnitude exact-match "3 of 9"; the table shows **2** clean matches (MIRM, CADL), with AVTX, AXSM, and ARVN marked as directional-but-wrong-magnitude. The miss-attribution bars also sum to 10 (2+3+1+1+2+2).

The consistent off-by-one says **one fired event was dropped from the table but left in every aggregate**. Whoever picks this up needs to find the tenth event before any of these numbers can be quoted.

**5.2 — The forward table is 101 days stale and at least partly falsified by events. (RED)**

Every forward row has been overtaken. From this dropbox's own INDEX: MNKD was **approved 2026-05-29**; CRDF held ASCO 6/2 and faded from +20% to +3%; CABA's EULAR binary fired positive 6/3. Most importantly, `2026-08-29e_DATA_MOAT_and_NAV_FREEZE.md` documents that **CAPR's PDUFA moved from 2026-08-22 to 2026-11-22** — the tracker still shows 2026-08-22 with "94 days" and a planned "T-7 = Aug 13" exit that is now in the past. The hardcoded day counts were computed from roughly 2026-05-20 and have been counting down to nothing ever since.

**5.3 — The footer contradicts the standing model specs. (AMBER — needs a ruling)**

Verbatim from the file:

> Honest accuracy: ODIN v38.1 test AUC 0.7288 (n=259). GUNGNIR v46 honest 0.6150 (claimed 0.8135 retracted). BIFROST v5.5 honest 0.7447 (claimed 0.9487 retracted). BIFROST v4 runup R²=0.583 validated.

The standing 9 Realms spec still carries GUNGNIR v46 at AUC 0.8135 and BIFROST v5.5 at LR AUC 0.9487 as champion numbers. This page says both were **retracted**, and the direction of the correction matches the Red Team finding already on record — that BIFROST's greedy forward selection ran directly against the test set, inflating absolute AUC. The retracted figures are also far below the estimated 0.85–0.90 range that audit suggested for BIFROST, which is a larger correction than that note anticipated.

This needs an explicit ruling, because two different numbers for the same model are in active circulation.

**5.4 — The Brier baseline label looks wrong. (AMBER)**

The Brier card compares 0.351 against a "honest v38.1 baseline 0.0895". But 0.0895 is the **ODIN v14 holdout Brier** from the model spec. Either the label is a copy-paste error or v38.1 coincidentally lands on the identical value, which would be a surprise. Worth a second look, though the amber flag on the card is directionally right either way — 0.351 is poor calibration however it is benchmarked.

**5.5 — Sample size. (AMBER)**

Nine or ten events over thirty days cannot support a 60% direction accuracy claim to one decimal place, and a five-point calibration curve where four of the five bins contain a single event each is decorative rather than diagnostic. The chart's own comments admit this (`0.40-0.50: CADL 0/1`). Treat the whole page as a qualitative scoreboard, not a calibration measurement.

## 6. WHAT IS ACTUALLY WORTH KEEPING

The concept is sound and it is the one artifact in the estate that closes the loop between prediction and outcome. The miss-attribution taxonomy in particular — magnitude model gap, upside undercall, IIS low-dose guidance, earnings-not-binary — is genuinely useful and does not exist anywhere else. The honest-versus-claimed accuracy footer is the most intellectually honest line in the whole 9 Realms estate.

What it needs is to stop being a hand-typed snapshot. See the builder note.

---

*Filed to the Odin Cowork Dropbox per Amendment 033. Companion: `BUILDER_NOTE_stock_reaction_tracker_data_source.md`.*
