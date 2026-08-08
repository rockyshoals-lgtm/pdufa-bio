# Builder response — Pass 16/17 crawler + tracker reconciliation · 2026-06-28

Implemented the crawler fixes review + closed three tracker items that were marked open but are actually live. Net: the crawler seed is now **publish-safe** (it wasn't), and the **security P0 is already closed** (verified live). Detail below.

## 1. Crawler patch (Pass 17) — VERIFIED SOUND ✅
Red-teamed the auto-applied edits to `catalyst_crawler.py`:
- `python3 -m py_compile` → OK. 1327 → 1371 lines (+44, matches the 5 edits).
- All 5 present and additive/exception-guarded: `recall_vs_bpc_bydrug` (by-drug recall), `fmp_transcript_catalysts()` (reuses existing `_scan_catalyst_text`), `--transcripts` flag + `main()` wiring, `seed_candidates.csv` emission. Backups intact.
- **Verdict: good engineering, no regressions. Ship it.**

## 2. The 44-row seed — "paste-and-ship" was UNSAFE. Curated 44 → 25. ⚠️→✅
Pass 16/17 said "paste the 40 `coverage_gaps` rows in with a source_url → ~90% recall." I verified every row first (two independent passes). **~43% of the auto-built seed was not publish-safe** — shipping it `redistribute=True` would have put ~19 factually wrong entries on the live calendar and broken the "98% sourced / facts-not-advice" promise. Breakdown of the 19 dropped (full reasons in `seed_rejected_audit.csv`):
- **5 ghost rows — already APPROVED** (do not belong on a forward calendar): GSK Utebzi (approved 6/17), REGN DB-OTO/Otarmeni (~Apr), NVO Sogroya/Noonan (2/27), AZN Enhertu early-BC (~May), GILD Trodelvy (6/24, + urothelial was withdrawn).
- **2 wrong-ticker**: GH (Guardant) for Camizestrant — that's the **companion diagnostic**, drug is AZN's. MRK for Trodelvy — Trodelvy is **Gilead's**.
- **4 duplicates** (same NDA twice): PFE≡ROIV (brepocitinib), PTGX≡TAK ×2 (rusfertide VERIFY), ABBV TEMPO-1≡TEMPO-2 (tavapadon).
- **6 not-a-PDUFA / no-filing**: NRXP KETAFREE (GDUFA generic goal date), LLY tirzepatide CV (data readout), LLY tirzepatide indication (withdrawn 5/25), AZN gefurulimab + PFE Tukysa + NVS Pluvicto (no FDA filing / already approved).
- **2 unconfirmable dates**: NVO Mim8, ABBV RINVOQ vitiligo (could land 2027).

The 25 KEEP rows are all verified pending US PDUFAs, **every one with a primary-source URL**, and with **honest date precision** instead of the imputed `2026-12-31`:
- 15 `day` (confirmed exact date), 8 `month` (quarter-deadline / "August 2026" estimates), 2 `year` (genuinely unknown — Camizestrant extended, Tavapadon no date).
- Ticker corrections applied: **ABEO→RARE** (UX111), **IRD→VTRS** (MR-141; Viatris is the FDA applicant). ALPMY drug relabeled to enfortumab vedotin (PADCEV)+pembro.
- Files: `bigpharma_pdufa_seed.csv` (25 rows, all sourced), `seed_rejected_audit.csv` (19 + reasons), backup `bigpharma_pdufa_seed.csv.bak_redteam44`.

**Bottom line: the seed will no longer INTRODUCE errors on merge. The remaining recall lift is real, but it's "verify-then-add," not "paste."**

## 3. Tracker reconciliation — 3 items are STALE (already live). P0 is CLOSED. ✅
The Living Tracker still flags these ❌ — they're done. Live proof:
- **`/api/data` gate (the only "true blocker"):** anonymous `GET https://pdufa.bio/api/data` → `"pro":false,"pro_gating":true`, and **zero `opt` fields** + no truthy `reg.slip` across the whole payload. Pro data (options/IV/implied-move/Silent-Shift) is stripped for anon callers. **Security-Audit Pass-11 #1 is closed.** (Was activated last session; the tracker carried the old finding forward without re-checking.)
- **`/coverage` `Dataset` schema:** present in deployed source.
- **Month-page `ItemList` + `BreadcrumbList`:** present (June page has ItemList + BreadcrumbList + FAQPage — not "FAQ only").

## 4. NEW findings (data quality, for your next crawl)
- **Live feed has a wrong-ticker row:** `ABEO — UX111 (ABO-102) — Sanfilippo A — 2026-09-19`. UX111's sponsor is **Ultragenyx (RARE)**; Abeona sold ABO-102 in 2022. Recommend correcting in the feed/source (the seed already lists it as RARE, but that won't overwrite the existing ABEO row — needs a feed fix + dedup).
- **Seed↔feed overlap:** the live feed already catches many mega-caps the seed also lists (PTGX, ROIV, TAK, REGN Garetosmab, BMY, MRK/PFE/ALPMY Keytruda+Padcev, MRNA, BIIB). The seed is insurance; confirm the crawler's ticker+drug dedup collapses these so they don't double-list (esp. where the seed's corrected ticker differs from the feed's).
- **Verify NVO Sogroya/Noonan:** live feed shows it pending 6/30, but the 2/27 sBLA approval covered "3 pediatric indications" — confirm whether Noonan is a separate still-pending sBLA or already included.

## 5. Intentionally declined
- **Homepage `SearchAction`:** the site has no sitewide search. Emitting `SearchAction` tells Google a search endpoint exists; with none, it's a false signal that conflicts with the facts-only brand. Recommend leaving it off until/unless a real `/search` ships.

## 6. Needs YOUR go (not pushed — deploys/live changes)
Nothing deployed this pass (seed change only affects the next crawl). Ready when you say go: the ABEO→RARE feed correction, `.html`→301 aliases, `/api/data` rate-limiting. Owner-gated: the crawl run + ~source-URL re-curation each run, conversion CTAs (email provider pick), GSC Removals, light-teal redesign, backlink push.

*— Builder, Pass 16–18 (crawler patch verified · seed curated 44→25 · gate/Dataset/ItemList confirmed live).*
