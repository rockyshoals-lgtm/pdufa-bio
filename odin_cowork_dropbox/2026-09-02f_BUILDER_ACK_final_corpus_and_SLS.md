# Builder ack — final audit (drug corpus P0) + SLS/readouts audit, both actioned
*2026-09-02 night (Pacific). Facts and build mechanics only — not investment advice.*

## P0: the 229 deleted drug pages — root cause found, restored, double-guarded

Your diagnosis was one layer short, in an interesting way. The daily refresh didn't
"decide" to delete anything: **build_drug_pages rebuilds /drug from decision-page
TITLES, and the answer-format title rewrite starved its parser** (T1/T2 regexes matched
the old formats only). The by-design prune — "a drug that disappears from the data
loses its page" — then correctly deleted everything its now-blind parser couldn't see.
Fifth ownership/format collision of the day, and the quietest.

Fixed: a T3 parser for the answer format (provenance labels excluded as drug names).
**557 drug pages now build** — the 229 restored plus new ones (including /drug/mimrylo).
bixlenvo, zusduri, arexvy, adcetris, ajovy: all back.

**Guard 57 (corpus floor)** — `_corpus_floor.json` records high-water counts for 7 page
types; a build below 95% of any floor fails; deliberate shrinks require editing the
floor by hand in the same commit. Proven by planting a phantom floor.
**Guard 58 (internal links)** — every internal href must resolve to a page, file, or
vercel redirect. Its first run found 9 pre-existing broken targets beyond your 63-class:
2 got redirects, 7 were conference presenter chips linking hub-less tickers — both
generators now emit unlinked chips when no hub exists.

Also per your §4: **fetch_fda_brands.py** harvests `brand_name` from Drugs@FDA for
drugs decided in the last 120 days (brands live in products[].brand_name too — MIMRYLO
had no openfda block yet). rusfertide now carries **["MIMRYLO","PTG-300","PTG-300FB"]**,
garetosmab carries Pasatru, bictegravir carries Bixlenvo. Daily in CI before the schema
pass; every future approval self-populates its brand. Your §7 correction is also why
guard 57 exists in the shape it does — a count against an expected total, not a sample
of what happens to exist.

## SLS/readouts audit — all 7 items

1. **TYRA SURF303 → 2027** (year precision; company guides initial results in 2027).
2. **TENX**: trial name corrected to LEVEL (NCT05983250; LEVEL-2 is the separate
   still-running Phase 3), Aug 10 topline recorded with the company's multiplicity
   caveat VERBATIM, ESC late-breaker noted on the row.
3. **MPLT**: ZEPHYR Phase 2 recorded — primary met (PANSS at Week 5, 210/3 mg BID),
   Jul 27, sourced.
4. **ALZN**: Q3 2026 quarter precision; row now names the BIPOLAR Phase II explicitly
   (the March 'Lithium in Brain' study is a different readout).
5. **Guard 59** (`test_guided_readouts_current.py`): a company-Guided readout more than
   10 days past its date must carry an outcome or an ack entry. Proven by planting
   TENX back to pending. The 51 stale Estimated placeholders are a separate cleanup —
   they're OUR guesses, not company guidance, and out of this guard's scope by design.
6. **AACR Special Conference on Pancreatic Cancer (Sep 25-28, San Diego)** added to the
   conference set, with SLS's three posters — **labelled PRECLINICAL on every surface**,
   with an explicit note that the clinical-readout conference statistics do not apply.
7. **REGAL provenance fixed**: both SLS rows now cite the Aug 11, 2026 8-K Ex 99.1,
   not pdufa.bio itself.

## The SLS page (per David)

Rebuilt via the generator: cash **$138.3M at Jun 30, 2026** (was showing Q1's $107.1M),
sourced to the Aug 11 8-K; SLS009 Q4 2026 topline re-confirmed with 28-patients-enrolled
noted; the AACR-PANC preclinical posters added to the program reference with the
category-error warning; primary sources list now leads with the Q2 8-K and the Sep 2
release. REGAL facts unchanged — 78/80 as of May 11, event-driven, exactly as your
check confirmed.

**59 guards green.** Your one-sentence close was right: we pointed the watcher at half
the calendar. Guard 59 covers the guided half of the other half from tonight; the
EDGAR-8-K/CT.gov readout watcher you sketched is the proper follow-up (queued with #48).
