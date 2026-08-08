# Coverage Miss — Merck Lipfendra (enlicitide), approved 2026-07-16
*Flagged by owner. Verified against FDA + Merck + trade press. Not investment advice.*

---

# 🔴🔴 P0 — The site missed the biggest cardiology approval of the year, completely

On **July 16, 2026** the FDA approved **Lipfendra (enlicitide decanoate, MK-0616)** — the **first-ever oral PCSK9 inhibitor** — to Merck (MRK). Until now, PCSK9 inhibitors existed only as injections; this is a once-daily pill that cut LDL-C ~56–59% vs placebo. It is one of the most significant approvals of 2026.

**It is not in pdufa.bio at all.** I searched the full API (`limit=3000`) for every reasonable key:
```
pcsk9 · cholesterol · ldl · enlicitide · mk-0616 · lipfendra  →  0 matches
```
MRK's records in the dataset start at **2026-08-15** (Ensifentrine) and run forward — **there is no July record, and no LDL/PCSK9 record on any ticker.** This isn't a wrong date or a missing outcome. **The event was never in the dataset — not as a decision, and not even as an upcoming PDUFA before the decision.**

### Why this is worse than the staleness finding
Centanafadine (7/24) was a *near-term* PDUFA already on the calendar, so the daily job caught it. **Lipfendra was a mid-July catalyst that the frozen bulk refresh never ingested** — so it was invisible *before* the decision (no upcoming PDUFA) and *after* (no decision record). This is the concrete cost of the 326-row bulk being frozen at July 11: **a "most complete, most current FDA calendar" silently omitted the first oral PCSK9 inhibitor.** For the positioning, this is the exact failure the product cannot have.

---

# The record to add (verified — FDA press release + Merck + FDA drug-approval page)

| Field | Value |
|---|---|
| Ticker | **MRK** (approval granted to Merck Sharp & Dohme LLC) |
| Brand | **Lipfendra** |
| Drug | **enlicitide decanoate** (MK-0616) — cyclic-peptide oral PCSK9 inhibitor |
| Indication | Hypercholesterolemia, incl. heterozygous familial hypercholesterolemia (HeFH); adjunct to diet/exercise to lower LDL-C |
| Decision date | **2026-07-16** (FDA news release dated 2026-07-17; "content current as of 07/17/2026") |
| Outcome | **Approved** |
| Review | **Priority Review**; also reviewed under the **Commissioner's National Priority Voucher (CNPV)** pilot |
| Firsts | **First oral PCSK9 inhibitor** (class previously injection-only: Repatha/evolocumab, Praluent/alirocumab) |
| Pivotal | CORALreef Lipids — NCT05952856 (MK-0616-013); ~3,207 pts across 2 trials; 56–59% LDL-C reduction vs placebo at Wk24 |
| Primary source | FDA: `fda.gov/news-events/press-announcements/fda-approves-first-oral-pcsk9-inhibitor-lower-ldl-cholesterol-adults-high-cholesterol` |

**Note on date:** the FDA *press release* is dated July 17; the owner and trade press (AJMC, Pharmacy Times) cite the **approval as July 16**. Use **2026-07-16** as `decision_date` unless the approval letter says otherwise; either way it belongs in the archive now.

---

# The fix (same root cause, now with a name)
1. **Manually add the Lipfendra record now** (data above) so the flagship archive isn't missing the year's marquee cardiology approval while the refresh is debugged.
2. **This is exhibit A for the bulk-refresh P0.** The daily job only touches near-term + already-listed events; anything that entered the FDA pipeline and resolved after July 11 without being pre-loaded is invisible. The full rebuild has to run — and a **backfill of all decisions since July 11** should be the first thing it does. There may be *other* misses in that window, not just this one.
3. **Add a reconciliation check:** cross-match the decided archive against the FDA "Novel Drug Approvals" / press-announcements feed for the trailing 30 days; any FDA approval of a tracked (or trackable) sponsor that's absent from the archive should raise an alert. That's the guard that would have caught this automatically.

```python
# tests/test_fda_reconcile.py (sketch)
# pull FDA press-announcements RSS for last 30d; for each drug-approval item,
# assert a matching Decided row exists (by sponsor+drug) in catalysts_public.csv,
# else WARN with the FDA URL. Catches silent coverage gaps like Lipfendra.
```

---

**One sentence:** the site didn't get Lipfendra's date wrong — it never had it at all, and a calendar that missed the first oral PCSK9 inhibitor is the clearest possible proof that finishing the bulk refresh (and backfilling every decision since July 11) is the one thing that matters right now.

---
*Facts and historical statistics only. Not investment advice.*

Sources: FDA press release — https://www.fda.gov/news-events/press-announcements/fda-approves-first-oral-pcsk9-inhibitor-lower-ldl-cholesterol-adults-high-cholesterol · AJMC — https://www.ajmc.com/view/fda-approves-enlicitide-first-oral-pcsk9-for-high-cholesterol · Merck (CORALreef Lipids) — https://www.merck.com/news/mercks-enlicitide-decanoate-an-investigational-oral-pcsk9-inhibitor-significantly-reduced-ldl-c-in-phase-3-coralreef-lipids-trial/
