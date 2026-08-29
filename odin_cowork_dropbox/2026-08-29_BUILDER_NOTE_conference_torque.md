# Builder note — `conference_torque.html` ("Conference Catalyst Torque")

**Written:** 2026-08-29 · **Audience:** whoever is wiring this into pdufa.bio
**Subject file:** `C:\Users\dcmoo\Documents\Python\9realms\conference_torque.html` (16 KB, last modified 2026-08-04)
**Companion file:** `2026-08-29_conference_presenters_for_builder.csv` (this folder)

---

## What it is

A single self-contained HTML page. Not an app, not a build artifact, no server. Open it and it runs. It is a **medical-conference runup planner for small and micro caps** covering H2 2026, and it has three parts.

**1. The slate.** A table of 14 conferences from ESC (Aug 28) through ASH (Dec 12). For each one it prints the conference date and then three derived dates: equity entry at D-30, options entry at T-14, exit at D-1. A status chip tells you where today falls — `opens in Nd`, `EQUITY WINDOW OPEN`, `OPTIONS + EXIT SOON`, or `passed`. Those dates are arithmetic on the conference start date, computed in the browser at page load, so the page re-reads correctly every day without being republished.

**2. The live watchlist.** Ticker rows that call out to Unusual Whales at render time and come back with IV rank, implied move, market cap and call open interest. Each row gets a 0–100 "torque" score and a colored bar. You can add and remove tickers in the page; the list survives reload.

**3. The playbook.** Six static cards restating the empirical numbers from Conference Overlay v1.0, BIFROST Options Module v1.1, and the ORATS IV work — runup medians, the T-14 options entry, the limit-order rule, the "am I too late" IV thresholds, and position sizing.

The thesis underneath it is the conference signal finding: companies presenting at these meetings read out positive 90.2% of the time against a 76.7% base rate, and the runup into the presentation is the trade — you exit the day before, you never hold through.

---

## Where the data lives

This is the part that matters most, and the answer is in three different places.

### Baked into the HTML

The 14-conference slate is a hardcoded JavaScript array named `CONFS`, sitting in a `<script>` block near the bottom of the file. Each entry carries a code, display name, focus area, tier, boost percentage, start date and city. The tier weights (`ELITE` 20, `TIER1` 15, `TIER2` 12, `OTHER` 9) are hardcoded next to it. The six playbook cards are hardcoded HTML.

Nothing on that list is read from a file at runtime. To change a conference date, tier, or boost, you edit the HTML. There is no other lever.

### Fetched live, per render

The watchlist rows call one tool:

```
window.cowork.callMcpTool("mcp__unusual-whales__get_stock_screener", { ticker, limit: 1 })
```

and read four fields off the response: `iv_rank`, `implied_move_perc`, `marketcap`, `call_open_interest`. Rows fill in sequentially, one await per ticker, so a long watchlist populates visibly top to bottom.

This is the page's only external dependency and its only real failure mode. Outside a Cowork runtime that provides `window.cowork.callMcpTool`, the slate and playbook render fine and every watchlist row shows an error. If you host this on pdufa.bio as-is, part 2 is dead. Replacing that one call with your own server-side endpoint is the whole port.

### In the browser, per viewer

The watchlist itself is `localStorage` under the key `conf_torque_watchlist_v2`, seeded with three rows on first load. It is per-browser and per-viewer — it never leaves the machine, two people looking at the same page see different lists, and clearing site data resets it to the seed.

### The real pipeline — which is NOT connected to this page

Separately from the HTML, there is a genuine conference data pipeline in `9realms`, and the page does not read any of it:

| File | Rows | What it is |
|---|---|---|
| `conferences.json` | 41 conferences | Dates verified against each organiser's own site on 2026-08-03. Carries an `_unannounced` block for conferences whose dates aren't published (JPM 2027) rather than guessing them. |
| `catalysts_out/conference_presenters_mined.csv` | 174 | Presenters auto-mined from SEC EDGAR filings, each with the filing URL and the sentence that matched. |
| `catalysts_out/conference_presenters_VERIFIED_2026-08-12.csv` | 10 | The human-reviewed subset, with reviewer and note. |
| `catalysts_out/conference_presentations_history.csv` | 754 | Historical presentations, the backtest substrate. |
| `conference_miner.py`, `conference_presenter_miner.py`, `run_conference_crawl.py` | — | The crawlers. See `CONFERENCE_CRAWLER_RUNBOOK.md`. |
| `tests/test_no_fabricated_conferences.py` | — | Guards against invented conference rows. Worth reading before you touch any of this. |

So: `conferences.json` holds 41 verified conferences and the page hardcodes 14 of them. Those two lists drift independently and nothing reconciles them today.

---

## How to use it

**As a planner, as-is.** Open it any day. The slate tells you which windows are open right now. Add presenter tickers as abstract titles release, sort by torque, and work the high scorers that are inside an open window. Exit D-1. That is the intended loop.

**Reading the torque score.** It is computed in-page, not by any model:

```
torque = (100 - iv_rank) * 0.35      cheap IV is most of the score
       + cap tier bonus               micro 25, small 20, mid 8, large 2
       + min(20, call_OI / 500)       liquidity
       + conference tier weight       ELITE 20 → OTHER 9
                                      clamped to 0–100
```

Read it as a *setup quality* heuristic, not a probability. It says nothing about whether the readout is good — it says the option is cheap, the float is small, the calls are tradeable, and the venue is prestigious. Colors are green at 70+, amber at 50+, blue below.

**If you are porting it to pdufa.bio,** in priority order:

1. Replace the Unusual Whales call with a server-side endpoint. Don't ship browser-side vendor calls to the public site.
2. Drive `CONFS` from `conferences.json` instead of the hardcoded array, so the slate and the verified calendar can't drift.
3. Drive the watchlist seed from the verified presenters CSV rather than the three hardcoded tickers (see the defect below).
4. Keep `localStorage` for the user's own added tickers — that part is correct and should stay per-viewer.
5. Carry the disclaimer through. It's in the footer and it needs to stay.

---

## Things to fix before anyone trusts it

**The seeded watchlist does not match the mined data.** This is the one to deal with first. A comment in the source claims the three seed rows are "mined + verified presenters (INBX/TENX confirmed via PR; MBX EASD-thematic watch)". Checked against the mined CSV:

- **INBX** — appears zero times. Not mined, not verified.
- **MBX** — appears zero times. Not mined, not verified.
- **TENX** — appears once, for **AHA**. The page has it against **ESC**. Wrong conference.

None of the three are in the verified file. Whatever those seeds are, they are not what the comment says they are. Replace them from the verified CSV or drop them.

**Verified coverage is thin.** 10 human-verified records against 174 mined. The mined rows are EDGAR-sourced with the matching sentence attached, so they are traceable rather than invented, but "traceable" is not "checked" — some matched sentences describe *last year's* presentation (the NewAmsterdam row cites ESC **2025**), which is the classic false positive for this kind of crawler. Don't present mined rows to users as confirmed presenters.

**The slate is missing conferences you have presenters for.** 50 of the 174 mined rows are for conferences not on the page's 14 — AHA (16 rows), ERS (7), ASCO GI (6), ASBMR (4), ACAAI (4), and others. AHA in particular has more mined presenters than all but two conferences on the slate.

**One `pres_type` value is doing too much work.** 136 of 174 rows are the generic `presentation`; only 21 are `oral/late-breaker` and 17 `poster`. Since the overlay pays oral and late-breaker more than poster, that generic bucket is where the boost math is least reliable.

**No dark mode.** `color-scheme: light` is fixed and the palette is light-only. Fine as a local file, worth revisiting for the site.

---

## The companion CSV

`2026-08-29_conference_presenters_for_builder.csv` in this folder — 174 rows, one per mined presenter, sorted by conference start date. It is a join of the mined presenters against `conferences.json`, so each row carries full conference metadata alongside the presenter.

Columns: `ticker`, `company`, `conference`, `conference_name`, `conf_start`, `conf_end`, `city`, `focus`, `pres_type`, `drug`, `status`, `review_note`, `in_torque_html_slate`, `sec_filing_url`, `filed`, `evidence_sentence`, `retrieved_at`.

Three of those are the ones to actually use:

- **`status`** — `HUMAN_VERIFIED` or `MINED_UNVERIFIED`. 12 rows carry the verified flag, covering the 10 verified records (two ticker/conference pairs appear twice in the mined file). **Everything else is unverified.** Treat this column as the gate before anything reaches a user.
- **`in_torque_html_slate`** — whether that conference is one of the page's 14. `no` on 50 rows.
- **`evidence_sentence`** — the actual filing text that triggered the match, truncated to 400 chars, paired with `sec_filing_url`. This is how you check a row in about fifteen seconds rather than trusting it.

23 conferences are represented. Nothing in the file was generated or inferred — every row traces to an SEC filing URL.

---

*Informational and educational only. Not investment advice. Conference runup trades are high risk; the page's own guidance is limit orders on options and never holding through the event.*
