# SESSION HANDOFF — 2026-07-15 (pdufa.bio + readout miner)

Migration doc for a fresh chat. Everything below is **verified state**, not intent.
Read the "Gotchas" section before touching anything — most of it is hard-won.

---

## 0. TL;DR — what changed today

| Area | State |
|---|---|
| `phase_readout_miner.py` | Non-catalyst scrub, imminence tiers, **filing enrichment (kill already-read-out)**. Shipped, tested. |
| `pdufa.bio` calendar | **CORT + CELC phantoms removed, deployed, verified live.** |
| `build_slate_from_crawl.py` | Two real bugs fixed (see §3). Guard now actually works. |
| `check_pdufa_decided.py` | NEW. Detects FDA decisions we still show as pending. **Found 4 more phantoms — unfixed.** |
| Daily job (6:15 PM) | Now: readout scan → diff → price refresh → chart rebuild → decided-PDUFA check. |
| Price cache | Was **26 days stale** (Jun 18). Now current. Refreshed daily. |

---

## 1. THE BIG OPEN ITEM (start here)

`check_pdufa_decided.py` found **4 forward PDUFAs that appear already decided**. They are
STILL LIVE ON THE SITE as pending. Each needs primary-source verification, then an archive row.

```
BIIB  listed 2026-08-24  ->  Approved 2026-07-13   "FDA Approves LEQEMBI IQLIK (lecanemab-irmb)..."
PFE   listed 2026-08-17  ->  Approved 2026-07-10   "U.S. FDA Approves PADCEV plus Keytruda ... MIBC"
MRK   listed 2026-08-17  ->  Approved 2026-07-10   (same MIBC approval)
IONS  listed 2026-06-30  ->  Approved 2026-06-24   (displays correctly, but still counted "scheduled")
```

**To fix each:**
1. Verify against company IR / SEC 8-K. **Do not trust the PR headline alone** — a sponsor's
   "FDA Approves X" may be a *different* drug/indication than the pending PDUFA.
2. Add a row to `pdufa_site_src/decisions/index.html` (exact format in §4).
3. Ensure `/fda-decision/{TICKER}-{DATE}/index.html` exists (template: copy VERA-2026-07-07).
4. Re-run `pdufa_site_src/build_slate_from_crawl.py` → the sweep removes it from the slate.
5. **The static calendar page does NOT auto-update** — see §5 (the generator problem).
6. `deploy_site.bat`.

---

## 2. UNRESOLVED / BLOCKED

- **`/runup-by-year` PNGs have no generator.** The page embeds 4 matplotlib PNGs
  (`runup_by_year_bar/facets/overlay.png`, `runup_current_inflight.png`). **No script in the repo
  writes those filenames.** Searched exhaustively. `runup_current_inflight.png` is stale (Jul 11)
  and still reflects CELC/CORT as pending. Either find the generator or write a new one.
- **`calendar/index.html` has no generator either.** It is pre-rendered HTML with the slate baked
  in; it does NOT read `api/data.js` at runtime. Today's fix was a surgical patch
  (`fix_calendar_page.py`). This will need re-doing on every decision until a generator exists.
  **This is the single biggest structural debt on the site.**
- **P2-6 — FMP redistribution terms UNREAD.** Newswire rows are written `redistribute=False`.
  Nothing with that flag may reach the site/API/sitemap. Blocks publishing exact-day readout dates.
- **P0-5 — ODIN retrain** on capped `prior_crl_count`. Capped CSV exists; coefficients were fit on
  uncapped data, so **nothing deployed has changed**. CRL signal still compressed to ~1/3.
- **Exact-day readout dates: structurally hard.** Measured lead time for scheduling PRs = **median
  T-3** (n=4 across 205 tickers). Conference dates give ~T-99 but are rare. CT.gov gives a WINDOW,
  never a day — do not try to sharpen it (see §3, the lag study).

---

## 3. GOTCHAS — read before editing (each cost real debugging)

### build_slate_from_crawl.py — the two bugs behind the CORT phantom
1. **`norm_drug()` used to strip the parenthetical** (`re.sub(r'\(.*?\)', '', s)`).
   The archive logs the BRAND name with generic in parens ("Lifyorli (relacorilant)"); the
   calendar carries the GENERIC ("Relacorilant + nab-paclitaxel"). Stripping parens leaves
   `"lifyorli"` — which shares **nothing** with `"relacorilant"`. **Every drug is renamed on
   approval**, so this silently broke the guard for ~every approval. CELC only escaped because
   "fulvestrant" appeared on both sides. → **Parens contents are now KEPT.**
2. **`already_decided()` was a gate on ENTRY only** — checked for new crawl rows, never for
   catalysts already on the slate. But the decision arrives AFTER the catalyst is on the board;
   that's the normal case. → **The whole slate is now swept every build.**

### Two false-positive guards in `already_decided()` — DO NOT REMOVE
- **A CRL is NOT terminal.** Sponsor resubmits → new PDUFA. Only an **approval** ends the story.
  A CRL only resolves an event within ~45 days of it. *This nearly deleted OTLK's live 2026-07-29
  PDUFA (14 days out): CRL'd, resubmitted Jun 1, FDA granted Class 1 review, new date Jul 29.*
- **Platform drugs.** KEYTRUDA is approved dozens of times. A shared `pembrolizumab` token is NOT
  proof *this* PDUFA was decided. If drug text matches >1 archive entry → ambiguous → **stand down**
  rather than delete a live catalyst.

### phase_readout_miner.py
- **CT.gov `pageToken` vs `nextPageToken`** — the API *returns* `nextPageToken` but *accepts*
  `pageToken`. Get it wrong and you silently cap at page 1.
- **`pd.to_datetime` on a MIXED-format series coerces the WHOLE series to NaT, silently.** Normalise
  to full ISO first. (A stale filter once printed "dropped 0" while 944 stale rows sailed through.)
- **Catastrophic regex backtracking.** `PR_SCHED` chains `[^.]{0,150}?`. Run it on a full 40KB PR
  body and it burns **649 CPU-seconds and dies silently**. Body is capped at `PR_TEXT_CAP=3000`.
  The date is in the HEADLINE anyway.
- **The stored `title` is the CONTEXT WINDOW**, not the match: `ctx = txt[date-300 : date+120]`.
  The date sits near offset ~300, i.e. the END. Reading the start of `title` shows the LOOKBACK.
  *I raised two false alarms this way.* The in-run self-check re-runs the real attribution on the
  same window — trust it over any post-hoc CSV audit.
- **A checker must read the same evidence as the thing it checks.** Token-presence tests cannot
  catch a mis-*decision* (a window containing both "initiation" and "readout" scores clean either
  way). Hence `re-decided != readout` in the self-check.

### Data sources
- **Polygon daily bars are shifted +1 day** vs FMP and UW. Polygon's "7/06" is everyone else's
  "7/07". FMP and UW agree exactly. **Do not use Polygon for date-aligned price work.**
- **FMP EOD lags ~1 week**; **UW is current to today**; **Polygon ~2 days but wrong-dated**.
  Batch = FMP. Today's close = UW (`px_pins.json`).
- **`/api/v3/press-releases/` is DEAD** (HTTP 403, legacy endpoint). Only
  `/stable/news/press-releases` works. `catalyst_crawler.py` still has the dead v3 fallback.
- **Keys live in `Odin Perfection/.env_master`** — loaded by `_load_dotenv()` in both
  `phase_readout_miner.py` and `catalyst_crawler.py`. Precedence: real env var > `./.env` >
  `.env_master`. ORATS is spelled two ways (`_KEY`/`_TOKEN`); they're aliased.

### Environment
- **The MCP shell kills child processes when a call times out.** Long jobs must be launched
  detached (a one-shot Scheduled Task works) or they die mid-run with no error.
- `decisions/index.html` is **minified** — a "line" is a huge blob. `Select-String` output is
  misleading; use Python + regex. *(I misread this and misdiagnosed the CORT bug once.)*

---

## 4. FILE / FORMAT REFERENCE

**Decisions archive row** (`pdufa_site_src/decisions/index.html`, inside `<div class="grid">`
under `<div class="mhead">2026 · N</div>`, newest-first; **bump N**):
```html
<a class="row" href="/fda-decision/TICK-YYYY-MM-DD"><div class="t">TICK · YYYY-MM-DD <span class="ok">✓</span></div><div class="d"><span class="ok">Approved</span> — Brand (generic)</div></a>
```
> Keep BOTH brand and generic in the label — that's what makes `already_decided()` match.

**Calendar page resolved row** (`pdufa_site_src/calendar/index.html`):
```html
<a class="row" href="/fda-decision/TICK-YYYY-MM-DD"><div class="t">TICK · YYYY-MM-DD · <span class="ok">✓ Approved</span></div><div class="d">Brand (generic) — Indication</div></a>
```

**Scripts written today**
| File | Purpose |
|---|---|
| `refresh_pxcache.py` | FMP batch → `_chart_pxcache.json`; applies `px_pins.json` (UW closes). |
| `px_pins.json` | UW-verified closes FMP hasn't posted. CELC 2026-07-14 = 111.05. |
| `check_pdufa_decided.py` | Scans company PRs for FDA decisions on pending PDUFAs. **Reports only.** |
| `fix_early_approvals.py` | Adds decision pages/rows; fixed CORT's `og:title` (said ARQT). |
| `fix_calendar_page.py` | Surgical patch of the static calendar page. Re-run pattern for future phantoms. |
| `daily_diff.py` | What's NEW vs yesterday in the readout scan. |

---

## 5. HOW TO RUN

```
run_phase_readout_miner.bat      # Desktop copy is the one used; has ABSOLUTE cd (needs it)
    [1] FULL   = CT.gov + SEC + scrub + tiers + KILL-enrichment   (no slow sweep)
    [7] = [1] + 900-ticker newswire/conference sweep (~20-40 min)
run_daily_readout_scan.bat       # unattended; Scheduled Task "pdufa_daily_readout_scan" 6:15 PM
deploy_site.bat                  # publish pdufa_site_src to prod (needs VERCEL_TOKEN in .env_master)
pdufa_site_src/build_slate_from_crawl.py --dry-run   # ALWAYS dry-run first; it deletes catalysts
```

**Miner CSV columns of note:** `imminence` (IMMINENT ≤45d / NEAR / SCHEDULED / DISTANT / OVERDUE),
`days_to_readout`, `redistribute`, `data_lock_date`, `trial`.
`completed_pending` rows have **blank `catalyst_date`** + `date_precision='pending'` — the lock
date is NOT the readout date, so we don't print one.

---

## 6. STANDING RULES (non-negotiable — from CLAUDE.md)

- **ODIN v19-PRUNE is the only PDUFA scorer.** v14 is **KNOWN LEAKED** (~368bp inflated).
- Real data only. **Verify every date against primary sources** (company IR / SEC 8-K).
  Drugs.com etc. are secondary — fine for a lead, not for publishing.
- **Never publish a number you can't defend.** Nothing with `redistribute=False` reaches the
  site/API/sitemap. BioPharmaCatalyst = private QA yardstick only.
- No scores/probabilities/sizing/entry-exit on the site. Median + IQR + n only.
- **Never change the sampling frame and the published number in the same step.**
- **Data integrity outranks presentation.**
- Educational only — not investment advice. Do not execute trades or move money.

---

## 7. CONTEXT WORTH CARRYING

- **CELC/gedatolisib (REVTORPYK)** approved 2026-07-14 for HR+/HER2−, **PIK3CA wild-type**
  (~60% of HR+ — the group locked out of every other targeted drug). VIKTORIA-1: triplet mPFS
  9.3mo vs 2.0 (HR 0.24), doublet 7.4 (HR 0.33). **Caveat: the 2.0-mo control is unusually weak,
  which inflates the HR** — absolute mPFS vs capivasertib (7.3) / everolimus (7.8–11.0) is much
  closer. Safety is the real win: 2.3% discontinuation vs 7.1% alpelisib; grade≥3 hyperglycemia
  only 2.3%. No OS data yet.
- **CORT/relacorilant**: two tracks — ovarian (**Lifyorli, approved 2026-03-25**) and Cushing's
  (CRL Dec 2025, **resubmitted 2026-06-17**). The 7/11 date was the ovarian goal date; FDA acted
  ~3.5 months early. Expect a Cushing's PDUFA ~Dec 2026.
- Portfolio context (April): GRCE, WHWK, CRDF, CABA, ALXO. Cardinal rule: **the runup IS the trade.**
```
