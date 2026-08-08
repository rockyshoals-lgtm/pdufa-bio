# Builder Prompt — Finish the rebuild + make data self-updating

*Paste everything below the line to the builder. It is self-contained. Owner: David. Not investment advice; facts only.*

---

## Objective

The pdufa.bio dataset is **frozen**: 326 of 387 API rows still carry `updated_at = 2026-07-11`, while the daily job only touches near-term and just-decided events. Anything that entered the FDA pipeline and resolved **after July 11 without being pre-loaded is invisible.** This already caused a real miss (below).

Do three things, in order, and make them **fully automated and self-maintaining** so this never recurs:

1. **Backfill** every decision and data change since 2026-07-11 (bring the whole dataset to present day).
2. **Fix the confirmed miss** immediately (Merck Lipfendra — data below).
3. **Automate** a full daily rebuild + FDA reconciliation so `Data through` shows today, the live-dot stays green, and misses self-detect.

Acceptance is defined at the bottom. The auditor will re-verify against the live API.

---

## 1. Immediate fix — add the missed approval NOW

The site completely omitted the biggest cardiology approval of the year. Verified against the FDA press release, the FDA drug-approval page, Merck, and trade press:

| Field | Value |
|---|---|
| ticker | **MRK** (granted to Merck Sharp & Dohme LLC) |
| brand | **Lipfendra** |
| drug | **enlicitide decanoate** (MK-0616), oral PCSK9 inhibitor (cyclic peptide) |
| indication | Hypercholesterolemia incl. heterozygous familial hypercholesterolemia (HeFH); adjunct to diet/exercise to lower LDL-C |
| status | **Decided** |
| outcome | **Approved** |
| decision_date | **2026-07-16** (FDA press release dated 07-17; owner + trade press cite approval 07-16 — use 07-16) |
| review | Priority Review; also Commissioner's National Priority Voucher (CNPV) pilot |
| first | **First oral PCSK9 inhibitor** (class was injection-only: Repatha/evolocumab, Praluent/alirocumab) |
| pivotal | CORALreef Lipids — NCT05952856; ~3,207 pts; 56–59% LDL-C reduction vs placebo at Wk24 |
| source | https://www.fda.gov/news-events/press-announcements/fda-approves-first-oral-pcsk9-inhibitor-lower-ldl-cholesterol-adults-high-cholesterol |

Add it to the decided archive with `outcome`, `decision_date`, and source link populated, exactly like the MNKD/OTSKY records you fixed on 07-26.

---

## 2. Backfill everything since 2026-07-11

Re-run the full primary-source crawl for the entire dataset (not just near-term) so every row's `updated_at` becomes current and any other post-July-11 catalyst that slipped through is captured. **Lipfendra may not be the only miss** — reconcile the whole window (see §3 guard). Refresh prices / market caps for all rows via the new Polygon feed while you're rebuilding.

---

## 3. Automate a daily full rebuild + reconciliation (the core ask)

Build a scheduled job (GitHub Action `cron`, or Vercel Cron → serverless function) that runs **at least daily, unattended**, and:

**a) Rebuilds the entire dataset** from primary sources, then redeploys/commits the refreshed data. All of these are confirmed reachable from a server with allowlisted egress (I tested them today — all returned 200):

- **FDA press-announcements RSS** — current, curated, best signal for major/novel approvals:
  `https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml`
  (Today it correctly lists the *Jul 17 "FDA Approves First Oral PCSK9 Inhibitor"* item — i.e. Lipfendra. Your pipeline should have caught this.)
- **openFDA drugsfda** — broader approval coverage (note: ingestion lags days–weeks, so use as enrichment, not the sole source):
  `https://api.fda.gov/drug/drugsfda.json`
- **ClinicalTrials.gov v2** — readout / primary-completion dates:
  `https://clinicaltrials.gov/api/v2/studies`
- **Polygon (Ultimate)** — prices, market caps (the vendor you migrated to; replaces the frozen price step).

**b) Runs an FDA reconciliation guard** — this is the check that would have caught Lipfendra automatically. For every drug-approval item in the FDA RSS over the trailing 30 days, assert a matching `Decided` row exists in the decided archive (match on sponsor + drug/brand). Any approval present in the FDA feed but **absent from the archive → alert** (email/Slack/log) with the FDA URL, and ideally auto-open a backfill task.

**c) Emits a freshness/consistency check that fails loudly:**
- `max(updated_at)` older than ~24–48h → alert (the rebuild silently died).
- Any `Decided` row missing `outcome`, or with `days_to_decision > 0` → fail.
- Any date+drug PDUFA group with mixed null / non-null market cap → fail (the join-artifact guard).

**d) Keeps the honest freshness UI you already built** — the `Data through {mode(updated_at)}` badge + amber-past-7-days dot is correct; don't remove it. The goal of this whole task is simply to make `mode(updated_at)` **equal today**, so the badge reads today and the dot is green — earned, not asserted.

### CI guards to commit (block deploy / page on failure)
```python
# test_data_freshness.py — newest updated_at must be < 48h old
# test_fda_reconcile.py  — every FDA-RSS approval (30d) has a matching Decided row
# test_decided_consistency.py — Decided ⇒ outcome set AND days_to_decision <= 0/null
# test_no_ticker_fanout.py — no date+drug group with mixed null/non-null market_cap
```

---

## 4. Two minors to fold in (already flagged, cheap)

- **Event schema `startDate` is date-only** (`2026-07-29`) → Google Search Console flags "94% of Events not eligible for rich results." Add a nominal time + timezone offset (e.g. `2026-07-29T00:00:00-04:00`); keep `VirtualLocation` + `OnlineEventAttendanceMode` (they're fine). Re-run the Rich Results Test after.
- **Decided archive sorts by scheduled `date`, not `decision_date`** → MNKD shows as "decided 2026-07-26" (its PDUFA target) when it was decided 07-24. Now that `decision_date` exists, sort/display "recently decided" by it.

---

## Acceptance criteria (the auditor will verify all of these against the live API)

1. `GET /api/v1/events` → **`mode(updated_at)` is today's date**; homepage badge reads "Data through {today}"; live-dot green.
2. **Lipfendra present**: searching the API for `enlicitide` / `lipfendra` / `pcsk9` returns the MRK record above with `outcome:"Approved"`, `decision_date:"2026-07-16"`.
3. **No post-July-11 approval in the FDA RSS (30d) is missing** from the decided archive (reconciliation passes).
4. **All four CI guards pass** and run in the scheduled job.
5. The rebuild runs **on a schedule with no manual step** — show the cron config (Action YAML or Vercel cron) and one successful unattended run in the logs.
6. Minors (Event `startDate` TZ, archive sort by `decision_date`) shipped.

**North star:** the site should be able to prove it's current without anyone touching it — the FDA publishes an approval, the next scheduled run ingests it, the reconciliation guard confirms nothing was missed, and the "Data through" badge advances on its own.
