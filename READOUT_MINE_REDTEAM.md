# Red team: MAX READOUT MINE — 2026-07-17

## What holds up

Every falsifiable claim in `run_readout_max.bat` checks out. Measured against EDGAR live:

| claim | verdict |
|---|---|
| `quota = max(30, max_docs // len(GUIDANCE_PHRASES))` | **confirmed in code** |
| 26 phrases → quota 57 at `--max-docs 1500` | **26 exactly. 1500//26 = 57.** |
| 6000 → quota 230 | **6000//26 = 230.** |
| "~4.4% coverage" | **measured 4.6%** (1,265 of 27,340 docs) |
| "still-enrolling trials have not read out" | **correct and it is the whole game** |
| build aborts rather than ship a contaminated workbook | **confirmed** |

The colour-by-source-quality (green = company said it, amber = CT.gov estimate) is the single
best idea in the repo. It refuses to let a sponsor-typed guess look like a commitment.

**I was wrong once here.** My first counter used `^\s*"([^"]+)"` and reported 9 phrases, because
the list packs several per line. I concluded the .bat's arithmetic was stale. It wasn't — my
regex was. Re-counted via AST: 26. Retracted.

---

## What's actually broken

### 1. The list contains a duplicate — EDGAR FTS is case-insensitive

```
"Topline Results"   -> 2,337 docs
"topline results"   -> 2,337 docs     <- THE SAME QUERY
```

Identical totals because FTS ignores case. So the list has **25 unique phrases, not 26** — the
quota divides by a phrase that contributes nothing, and 57 doc-fetches are spent re-downloading
documents already in the pool. Same for `top-line data`/`topline data` overlap in intent.

### 2. Two generic phrases eat half the corpus

```
phrase                         docs    % of corpus
will host a conference call   8,000        29.3%
conference call to discuss    4,288        15.7%
                              ─────       ──────
                             12,288        45.0%
```

**Every company hosts conference calls.** These two phrases are 45% of the searchable corpus and
carry the least readout signal per document. Under a flat per-phrase quota they consume the same
57 (or 230) slots as `announces topline` — which has **36 docs total** and is nearly pure signal.

`will host a conference call` returning exactly **8,000** is suspicious: that is a round number,
not a count. It is likely EDGAR's `relation: "gte"` cap, meaning the true figure is higher and
coverage there is **worse than 0.7%**.

### 3. Raising 1500 → 6000 buys mostly noise

```
extra doc-fetches: 2,626
of which the top-3 (conference-call) phrases take: ~52%
coverage: 4.6% -> 14.2%
runtime:  ~7 min -> ~25-30 min
```

You would sit through 20 extra minutes to quadruple your coverage of *conference call
announcements*. The .bat calls this "the lever that moves" the company-stated ratio. It moves it
— but it is the most expensive way to move it.

### 4. The sample is relevance-ranked, not time-ranked

Taking the first 57 hits is only safe if EDGAR's order is random with respect to what we want.
It isn't — FTS returns by relevance. So we keep whichever 57 documents EDGAR's scorer likes, and
that correlates with nothing we care about. **The .bat says "WHICH 57 is arbitrary" and is right,
but treats it as noise. It is bias.**

---

## The fix: narrow the window, don't raise the budget

**A readout guidance from 14 months ago is worthless — the window has already passed.** The miner
searches a 450-day lookback and then samples 4.6% of it at random. Invert that:

```
current : 450-day window, take 4.6%   -> a thin random skim of mostly-dead guidance
better  :  60-day window, take ~40%   -> a near-census of LIVE guidance
```

Same doc budget. `27,340 × (60/450) ≈ 3,645` docs in the recent window; at `--max-docs 1500` that
is **~41% coverage of the filings that still matter**, in **~7 minutes** instead of 30.

**Concretely, in priority order:**

1. **Time-slice the FTS walk.** For each phrase, step the window in 30-day slices newest-first
   and take everything in each slice until the quota is spent. Converts an arbitrary
   relevance skim into a complete census of recent filings. This is the single highest-value
   change and it costs nothing.
2. **Delete `"topline results"`** (duplicate of `"Topline Results"`). Free slot, free budget.
3. **Weight the quota by corpus size, inversely.** `quota_i = budget × (1/n_i) / Σ(1/n_j)` —
   give `announces topline` (36 docs) all of them and cap `will host a conference call` at a few
   hundred. A flat quota is only fair if the phrases are equally informative; these differ by
   **200x** in specificity.
4. **Drop `--max-docs` back to 1500-2000.** With (1)-(3) it buys more than 6000 does today, in a
   quarter of the time.
5. **Log the `relation` field.** When EDGAR says `gte`, the total is a floor, not a count — and
   right now every coverage number computed against a capped total is optimistic.

---

## The thing this unlocks (from today)

KLRS: `"Kalaris Therapeutics Reports Positive TH103 Phase 1a SAD Results"` — published **07:00 ET**,
ignited **09:43**, high **10:40**. **A 2h43m head start, publicly available, missed.**

The miner's own comment already names the reason a naive phrase list fails:

> *"EDGAR full-text search requires ADJACENCY inside a quoted phrase. `to report topline` does
> NOT match `to Report 36-Week Topline Results` — the intervening words break it. So we search
> short, universal fragments and let the LEAD regexes find the date in the document."*

That is the correct architecture, and it is **better than the fix I proposed for the live news
scanner an hour ago** (regex on the headline). Search fragments FTS can match; regex the fetched
document. The live news firehose should adopt the same two-stage pattern rather than trying to
pattern-match headlines directly.
