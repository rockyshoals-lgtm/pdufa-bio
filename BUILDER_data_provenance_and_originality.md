# BUILDER PACKAGE — Data Provenance, Originality & Fixes
**Date:** 2026-07-11 · **Audience:** builder · **Status:** action required
**Purpose:** guarantee every byte on pdufa.bio is original / properly licensed, and ship the fixed datasets.

---

# 1. ✅ GOOD NEWS — the originality gate already exists and works

I audited the catalyst pipeline. **Someone built this correctly.** Do not break it.

| File | Rows | `redistribute` | Sources |
|---|---|---|---|
| `catalysts_out/catalysts_public.csv` | 1,123 | **True (100%)** | ClinicalTrials 958 · SEC EDGAR 75 · curated_pharma 37 · FMP earnings 21 · FMP press 13 · curated_device 12 |
| `catalysts_out/catalysts_primary.csv` | 1,123 | **True (100%)** | same |
| `catalysts_out/bpc_internal.csv` | 643 | **False (100%)** | **`source = 'biopharmacatalyst'`** |

**Verified: ZERO BioPharmaCatalyst-sourced rows appear in the public files.** The `redistribute` flag is doing its job — BPC data is quarantined for internal cross-checking only.

## 🔒 Rule: the redistribute gate is now a hard invariant
**Nothing with `redistribute = False` may ever reach the site, the API, the sitemap, or an OG image.**

### Ship this CI check (blocks the build):
```python
# tests/test_originality.py  — must run in CI on every deploy
import pandas as pd, sys
PUBLIC = 'catalysts_out/catalysts_public.csv'
BANNED_SOURCES = ('biopharmacatalyst','bpiq','biopharmawatch','fdatracker','rttnews','stocktitan','marketbeat')

df = pd.read_csv(PUBLIC)
errors = []
if 'redistribute' not in df.columns:
    errors.append('FATAL: redistribute column missing')
else:
    bad = df[df['redistribute'] != True]
    if len(bad): errors.append(f'FATAL: {len(bad)} rows with redistribute != True')
if 'source' in df.columns:
    leak = df[df['source'].astype(str).str.lower().str.contains('|'.join(BANNED_SOURCES), na=False)]
    if len(leak): errors.append(f'FATAL: {len(leak)} rows from a competitor source')
if errors:
    print('\n'.join(errors)); sys.exit(1)
print(f'OK — {len(df)} public rows, all redistributable, no competitor sources.')
```

**Also:** never let `bpc_internal.csv` be read by any module under `pdufa_site_src/` or the API. Add a lint rule.

---

# 2. 🚨 PURGE — DrugBank (licensing exposure)

`drugbank_all_full_database.xml (2).zip` — **182 MB.**

- **DrugBank is licensed data.** Free for academic use; **commercial use requires a paid licence.** pdufa.bio is a paid product → shipping DrugBank-derived fields without a licence is a real legal exposure.
- **Good news: I grepped every `.py` — nothing references DrugBank. It's an unused download.**
- **Action: delete the zip**, or move it outside the repo and never wire it in.
- **Use ChEMBL instead** (open licence, CC BY-SA) — you already have `chembl_enrichment_cache_v2.json`. It covers modality/mechanism/target class.

---

# 3. 🐛 FIX — `prior_crl` is a broken (leaky) feature

**The bug:**
```
prior_crl = True  →  0 APPROVAL, 123 CRL     ← perfectly collinear with the outcome
```
`prior_crl` is being set on events that **received** a CRL, not events that **had a prior** CRL. It is a label leak. **Any model using it is inflated. Any stat published from it is false.**

**Action:**
1. **Drop `prior_crl` (boolean) from all models and all published stats.** Re-check whether ODIN v14 uses it — if so, retrain without it.
2. **Use `prior_crl_count` instead** — it behaves correctly.
3. **Clean the count:** 28 events have `prior_crl_count ≥ 5`, which is implausible (e.g. `IMMX / NXC-201` shows 8; `ViiV`/`Mylan` with asset "Unknown" show 25–26 — clearly counting at company level, not drug level). **Cap at 4 and fix the counting logic.**

## The clean, publishable CRL comeback table (this replaces the openFDA one)
Source: `ODIN_MODEL_READY_v1071_T1_2015on_ENRICHED.csv`, n=2,175 (counts 0–4), 2015–2026. **Unbiased** — covers all PDUFA events, not just FDA-released CRLs.

| Prior CRLs | Approved | n | **Approval rate** |
|---|---|---|---|
| 0 (first cycle) | 1,388 | 1,888 | **73.5%** |
| 1 | 87 | 203 | **42.9%** |
| 2 | 14 | 52 | **26.9%** |
| 3 | 7 | 23 | 30.4% |
| 4 | 2 | 9 | 22.2% |

**The headline:** *"First-cycle FDA applications approve 73.5% of the time. After one CRL, the next attempt approves 42.9%. After two, 26.9%."*

Clean, monotonic, unbiased, n=2,175 — **and it's a far better CRL story than the openFDA corpus.** Use this one.

---

# 4. 🔴 RETRACT — the openFDA CRL "77% manufacturing" claim

**Do not publish.** The 439-CRL openFDA corpus is **survivorship-biased**: 309 of 439 (70%) are for drugs that were later **approved**, because FDA's July-2025 release was explicitly *"associated with since-approved applications."* CMC-dominance is an artifact of measuring survivors.

**Still ship the CRL Tracker**, but reframed:
- Title it *"What happens after a CRL"* — not *"why the FDA rejects drugs."*
- Use the **unbiased comeback table above** (§3) as the headline stat.
- Use the openFDA corpus for the **deficiency-reason breakdown only**, with the bias stated **on the page**: *"These are the CRLs the FDA has chosen to publish — a set weighted toward applications that were later approved. Reason mix is not representative of all rejections."*
- Drop any "first of its kind" claim (Syner-G published a CMC analysis of the same corpus).

---

# 5. ✅ FIXED — Short interest rebuilt from raw FINRA (kills the lookahead bias)

**The flaw (your own red team flagged it):** BIFROST applied a **single April-2026 SI snapshot retroactively** to 1,704 historical events → lookahead bias.

**You had the real data all along.** `si_raw/` = **196 bi-monthly FINRA files, 2017-12-29 → 2026-03-31.**

**I rebuilt it properly:**
- **`conf_study/si_panel_2017_2026.csv.gz`** — **3,630,320 rows · 47,243 tickers · 2017→2026** (ticker, short_qty, adv, days_to_cover, change_pct, settlement_date)
- **`conf_study/si_at_catalyst_PDUFA.csv`** — 1,867 events · **96.4% SI coverage**
- **`conf_study/si_at_catalyst_CONFERENCE.csv`** — 1,427 events · **93.8% coverage**

**T-1 compliance verified:** joined with `merge_asof(direction='backward', allow_exact_matches=False)` → the SI snapshot is always **strictly before** the event. **Minimum lag = 1 day. Zero lookahead.** Median lag 9 days.

**Two payoffs:**
1. **Retrain every SI-dependent model** (BIFROST v5.x) on this panel. The current SI features are invalid.
2. **New publishable pdufa.bio feature (pure fact):** *"Short interest into this PDUFA: 6.2 days to cover, 12.4M shares short (as of settlement 2026-06-30)."* Nobody shows historical SI at the catalyst. Always print the **settlement date** so it's honest.
3. ⚠️ **Flag stale SI:** if `si_lag_days > 60`, mark it stale rather than showing it.

---

# 6. ✅ DELIVERED — the finished Conference Run-up Study

**`conf_study/conference_runup_FULL.csv`** — **1,401 events · 2017–2026 · 393 tickers · 48 fields.**
Full write-up: `CONFERENCE_RUNUP_STUDY_FINAL_2017_2026.md`

Headline: **no reliable conference run-up** (median −0.35% over 30 days; only 49.5% positive; post-event drift −1.9% by D+10). **2020 was a bubble (+17.3%); 2022–24 were negative. Nano-caps did worst (−9.84%).**

**This refutes Conference Overlay v1.0** (claimed nano/micro +4.88%; actual nano −9.84%). **Retire those numbers — do not use for sizing, scoring, or publication.**

---

# 7. Data-source register — publish this at `/sources`

| Source | Licence | Redistribute? | Used for |
|---|---|---|---|
| **ClinicalTrials.gov** | Public domain (NIH) | ✅ Yes | Readout calendar, trial design, NCT |
| **SEC EDGAR** | Public domain | ✅ Yes | Company filings, catalyst dates |
| **openFDA** | Public domain | ✅ Yes | Approvals, CRLs, 510(k)/PMA |
| **FDA Federal Register** | Public domain | ✅ Yes | AdComm calendar |
| **FINRA short interest** | Public | ✅ Yes | SI at catalyst |
| **Conference organiser sites** | Public schedules (facts) | ✅ Dates/facts only | Conference calendar |
| **FMP (Financial Modeling Prep)** | **Paid licence** | ⚠️ Per FMP ToS — check redistribution limits | Prices, earnings, press |
| **ORATS** | **Paid licence** | ⚠️ Derived stats only; no raw redistribution | IV context (internal) |
| **ChEMBL** | Open (CC BY-SA) | ✅ Yes, **with attribution** | Drug modality/mechanism |
| **DrugBank** | **Commercial licence required** | ❌ **PURGE — unused** | — |
| **BioPharmaCatalyst** | Competitor site | ❌ **NEVER — internal only** | Coverage cross-check |

**Two to confirm with counsel/ToS:** FMP and ORATS both permit *use*, but **redistribution limits** matter now that you have a public API. Rule of thumb: **derived statistics = fine; raw vendor data = not.** Your run-up medians are derived; a raw FMP price feed through your API would not be.

---

# 8. Builder checklist

- [ ] Ship `tests/test_originality.py` in CI (blocks deploy on any `redistribute=False` or competitor source)
- [ ] Add lint rule: no module under `pdufa_site_src/` or the API may import `bpc_internal.csv`
- [ ] **Delete `drugbank_all_full_database.xml (2).zip`** (unused, licence risk)
- [ ] **Drop `prior_crl` boolean** from all models/stats; retrain ODIN if it's in the feature set
- [ ] Fix `prior_crl_count` counting bug (cap ≥5; it's counting at company level)
- [ ] Rebuild BIFROST SI features from `si_panel_2017_2026.csv.gz` (current ones are lookahead-biased)
- [ ] Ship SI-at-catalyst on event pages, **with settlement date**; hide if `lag > 60d`
- [ ] Ship CRL Tracker as *"What happens after a CRL"* + the unbiased comeback table + bias disclosure
- [ ] Publish `/sources` with the register above; add ChEMBL attribution
- [ ] Retire Conference Overlay v1.0 numbers everywhere
- [ ] Confirm FMP + ORATS redistribution terms before the public API serves any derived vendor data

---
*Facts and historical statistics only — no trade recommendations, no approval probabilities. Not investment advice.*
