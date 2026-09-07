# Builder note — conference runup surface

**Date:** 2026-09-07 · **For:** whoever is wiring this into pdufa.bio
**Subject:** `C:\Users\dcmoo\Documents\Python\9realms\conference_torque.html` (16 KB, last modified 2026-08-04)
**Companion data:** `2026-09-07_conference_presenters_and_windows.csv` (this folder)
**Read first:** `2026-09-07_AUDIT_conference_runup_stack.md` (this folder)

> **Supersedes** the note dated 2026-08-29 in this folder. That one carried the wrong date — the session clock was reporting Aug 29 while the actual date was Sep 7 — so its window statuses were nine days stale. Use this one.

---

## Read the audit note before you build anything

The short version: **the page's Playbook numbers are contradicted by our own research.** It advertises a nano/micro D-30 runup of +4.88% at a 58.5% win rate. Three datasets on disk — including two dated a month *before* the page was built — put nano at −7.86% and micro at −1.95%, with the overall median across 1,425 events at −0.03% and 49.8% positive. A coin flip.

This does not mean the page is worthless. It means **the calendar and window machinery are sound and the edge claims are not.** Build the first, gate the second.

---

## What the page is

A single self-contained HTML file. No server, no build step, no framework. Three parts:

**1. The slate.** 14 conferences, ESC through ASH, each with three derived dates — equity entry D-30, options entry T-14, exit D-1 — plus a status chip computed against today's date at page load. This part is correct and genuinely useful; the arithmetic re-evaluates daily without a republish.

**2. The live watchlist.** Ticker rows that fetch IV rank, implied move, market cap and call open interest, then compute a 0–100 "torque" score.

**3. The playbook.** Six static cards. **This is the part under dispute.**

---

## Where the data lives — four places

**Hardcoded in the HTML.** The 14-conference `CONFS` array, the tier weights (`ELITE` 20, `TIER1` 15, `TIER2` 12, `OTHER` 9), and all six playbook cards. Nothing is read from a file at runtime. To change a date or tier you edit the HTML.

**Fetched live, per render.** Exactly one call:

```js
window.cowork.callMcpTool("mcp__unusual-whales__get_stock_screener", { ticker, limit: 1 })
```

reading four fields: `iv_rank`, `implied_move_perc`, `marketcap`, `call_open_interest`. Rows fill sequentially, one await each. This is the only external dependency and the only hard failure mode — outside a Cowork runtime that provides `window.cowork.callMcpTool`, the slate and playbook render fine and every watchlist row errors. **Host this as-is on pdufa.bio and part 2 is dead.**

**In the browser, per viewer.** The watchlist is `localStorage` under `conf_torque_watchlist_v2`. Per-browser, never leaves the machine, resets to seed when site data clears.

**On disk, unconnected to the page.** The real pipeline, which the HTML reads none of:

| File | Rows | What it is |
|---|---|---|
| `conferences.json` | **42** conferences | Verified against organiser sites. Carries an `_unannounced` block that withholds JPM 2027 rather than guessing. |
| `catalysts_out/conference_presenters_mined.csv` | 174 | EDGAR-mined presenters, each with filing URL and matched sentence |
| `catalysts_out/conference_presenters_VERIFIED_2026-08-12.csv` | 10 | human-reviewed subset |
| `catalysts_out/conference_presentations_history.csv` | 754 | historical presentations |
| `_conference_runup_stats.json` | 1,425 events | the current runup statistics — **not** what the page displays |
| `conference_miner.py`, `run_conference_crawl.py` | — | crawlers; see `CONFERENCE_CRAWLER_RUNBOOK.md` |
| `tests/test_no_fabricated_conferences.py` | — | guards against invented rows; read before touching any of this |

The page hardcodes 14 of the 42 conferences. Those lists drift independently and nothing reconciles them.

---

## Current state of the runups, as of 2026-09-07

Computed from `conferences.json` against today. Mined and verified counts from the presenter files.

| Conference | Start | Days out | Status | Mined | Verified | On page's slate |
|---|---|---|---|---|---|---|
| ESC | Aug 28 | −10 | **passed** | 9 | 2 | yes |
| ERS | Sep 5 | −2 | **passed** | 7 | 0 | **no** |
| WCLC | Sep 12 | 5 | **options + exit soon** | 2 | 1 | yes |
| AACR-PANC | Sep 25 | 18 | equity open | 0 | 0 | **no** |
| ASTRO | Sep 26 | 19 | equity open | 1 | 0 | **no** |
| EASD | Sep 28 | 21 | equity open | 8 | 3 | yes |
| WMS | Sep 29 | 22 | equity open | 0 | 0 | **no** |
| ACG / AAO / ASBMR | Oct 9 | 32 | opens in 2d | 1 / 2 / 4 | 0 / 0 / 1 | **no** |
| ECTRIMS / ASN / IDWeek | Oct 21 | 44 | opens in 14d | 0 / 9 / 0 | 0 | yes |
| ESMO | Oct 23 | 46 | opens in 16d | 15 | 2 | yes |
| SITC | Nov 4 | 58 | opens in 28d | 33 | 0 | yes |
| AASLD | Nov 5 | 59 | opens in 29d | 9 | 0 | yes |
| AHA | Nov 6 | 60 | opens in 30d | **16** | 0 | **no** |
| ACR | Nov 6 | 60 | opens in 30d | 9 | 0 | yes |
| SABCS | Dec 8 | 92 | opens in 62d | 11 | 0 | yes |
| ASH | Dec 12 | 96 | opens in 66d | 16 | 0 | yes |

Three things fall out of this table.

**Two conferences have already passed and one of them was never on the page.** ERS (Sep 5) had 7 mined presenters and no slate entry, so its entire window came and went invisibly.

**WCLC is the only live options window right now** — 5 days out, T-14 opened Aug 29, exit is Sep 11. It has 2 mined presenters, 1 verified.

**The slate misses where the presenters actually are.** 50 of 174 mined rows sit on conferences absent from the page — AHA alone has 16, more than all but two conferences on the slate. Meanwhile ECTRIMS and IDWeek are *on* the slate with zero presenters each. The hardcoded 14 was not chosen from the presenter data.

---

## Build order

**1. Drive the slate from `conferences.json`.** Replace the hardcoded `CONFS` array. This kills the drift, picks up all 42 conferences, and fixes the coverage gap in one change. Keep tier and boost as a separate lookup keyed by code, since `conferences.json` does not carry them.

**2. Replace the Unusual Whales call with a server-side endpoint.** Do not ship browser-side vendor calls to a public site — it exposes the integration and dies outside Cowork. One endpoint returning the same four fields is the whole port.

**3. Fix the seeded watchlist — it misrepresents its own provenance.** A source comment claims the three seeds are "mined + verified presenters (INBX/TENX confirmed via PR; MBX EASD-thematic watch)". Against the mined file: **INBX appears zero times. MBX appears zero times. TENX appears once, for AHA — the page has it against ESC.** None are in the verified file. Seed from `conference_presenters_VERIFIED_2026-08-12.csv` or ship an empty watchlist.

**4. Gate on `status`.** The companion CSV carries `HUMAN_VERIFIED` vs `MINED_UNVERIFIED`. Only 12 rows are verified. Never render an unverified row to a user as a confirmed presenter — at least one mined row matches on a sentence about ESC **2025**, i.e. last year's presentation, which is the expected crawler failure mode.

**5. Rewrite the Playbook panel or drop it.** See the audit note. As written it makes edge claims our own research refutes. Two honest options: replace the numbers with the current ones from `_conference_runup_stats.json`, or replace the panel with the research finding itself — *"we checked 1,401 presentations over ten years; the median presenter does nothing"* — which is defensible, original, and on-brand for a site that refuses to sell probability scores. The two study documents both recommend publishing exactly that.

**6. Keep `localStorage` for user-added tickers.** That part is correct and should stay per-viewer.

**7. Carry the disclaimer through.** It's in the footer and it stays.

---

## Reading the torque score

Computed in-page, not by any model:

```
torque = (100 - iv_rank) * 0.35      cheap IV is most of the score
       + cap tier bonus               micro 25, small 20, mid 8, large 2
       + min(20, call_OI / 500)       liquidity
       + conference tier weight       ELITE 20 → OTHER 9
                                      clamped to 0-100
```

It is a *setup quality* heuristic, not a probability. It says the option is cheap, the float is small, the calls are tradeable and the venue is prestigious. It says nothing about whether the readout will be good.

Two cautions. The cap-tier bonus rewards micro and nano hardest — and those are the two worst cells in the 1,425-event study (micro −1.95%, nano −7.86% at 30 days). The tier weights derive from the same Conference Overlay v1.0 whose runup figures are in dispute. Both should be re-derived, not ported forward on faith.

---

## The companion CSV

`2026-09-07_conference_presenters_and_windows.csv` — 174 rows, one per mined presenter, sorted by conference start. Joined against `conferences.json` and stamped with today's window arithmetic.

Columns: `ticker`, `company`, `conference`, `conference_name`, `conf_start`, `conf_end`, `city`, `focus`, `days_to_conf_from_2026_09_07`, `window_status_2026_09_07`, `equity_entry_D30`, `options_entry_T14`, `exit_D1`, `pres_type`, `drug`, `status`, `review_note`, `in_torque_html_slate`, `sec_filing_url`, `filed`, `evidence_sentence`, `retrieved_at`.

Four that matter:

- **`status`** — the gate. 12 rows `HUMAN_VERIFIED`, everything else `MINED_UNVERIFIED`.
- **`window_status_2026_09_07`** — 16 rows already passed, 2 in the options window, 9 with equity windows open. **Recompute this rather than trusting it; it is a snapshot of today.**
- **`in_torque_html_slate`** — `no` on 50 rows, the coverage gap.
- **`evidence_sentence`** with `sec_filing_url` — the actual filing text that triggered each match, so a row can be checked in about fifteen seconds instead of trusted.

23 conferences represented. Nothing generated or inferred; every row traces to an SEC filing.

One caveat on `pres_type`: 136 of 174 rows are the generic `presentation`, only 21 `oral/late-breaker` and 17 `poster`. The overlay pays oral more than poster, so that generic bucket is where any type-based boost is least reliable.

---

## Calendar hygiene items

`conferences.json` was modified 2026-09-05, adding AACR-PANC (42 rows now). Three small fixes worth making while you're in there: `_verified_on` still reads `2026-08-03` and was not bumped; the rows are no longer chronologically sorted (AACR-PANC is appended after ADA 2027-06-18); and its `city` uses `"San Diego, CA (Hilton San Diego Bayfront)"` against the `"City, CC"` convention used everywhere else. Worth extending `tests/test_no_fabricated_conferences.py` to cover sort order and the `_verified_on` bump.

---

*Informational and educational only. Not investment advice. Conference runup trades are high risk; the best-evidenced rule in the entire stack is that post-event drift is negative — median −1.59% by D+5 — so never hold through the event.*
