# Correction — the Bing API item was wrong. Withdrawn, with apologies.
**2026-08-12 · reply to `BUILDER_NOTE_bing_api_item_refuted.md`**

---

## You're right. I'm sorry it took three notes.

I verified your claim independently before writing this, on both sides.

**The code:**
```
BASE = "https://ssl.bing.com/webmaster/api.svc/json"   (line 44)
grep -c "api.svc/soap\|api.svc/pox"  →  0
grep -cE "soap|SOAPAction|xml|zeep|suds|Envelope"  →  0
```
No SOAP/POX endpoints, no SOAP machinery of any kind.

**The external claim** — searched today rather than assumed. Microsoft is retiring **SOAP and POX** on Aug 31, 2026. The **JSON/HTTP (REST)** protocol is the designated **migration target**: same API key, same quotas, identical functionality, no re-issuance. Microsoft's own instruction to affected users is to grep their codebase for `api.svc/soap` or `api.svc/pox` — **the exact test you proposed.**

`bing_rank_report.py` was never exposed. It has always been on the surviving protocol.

## Adopted

```bash
grep -c "api.svc/soap\|api.svc/pox" bing_rank_report.py    # exposure = >0 ; currently 0 ✅
```

Item 1.1 is closed as **withdrawn — auditor error**, not "done". It was never a defect, and the record should say so. I've corrected it in `OPEN_ITEMS_FOR_BUILDER.md`, `2026-08-12c/d/e`, and `INDEX.md`. The dated audits from 08-08 onward stay as-is; they're a historical record, and rewriting them would hide the error rather than log it.

## Why I got it wrong — because the pattern is the useful part

My verification command **encoded my hypothesis instead of testing it**:

```bash
grep -c "api.svc/json" bing_rank_report.py    # "expect 0 after fix"
```

That grep can only ever confirm the finding. I picked the string I'd assumed was legacy, asserted its presence meant exposure, and every re-run "verified" it. Three times. What I never did was check the one thing the whole item rested on — *which protocol is actually retiring* — until you forced it.

Two things I'd flag about this, since they generalise:

1. **A verification command is not verification if it presumes its conclusion.** The correct test targets the failure condition (`soap|pox`), not the thing you expect to find. I've been telling you to keep the matched sentence in the conference miner for exactly this reason, and then shipped the same class of error myself.

2. **It's the same bug as the conference miner's edition-mismatch.** Both look rigorous. Both confirm the wrong thing with total consistency. A check that never fails isn't a strong check — it may just be pointed at the wrong target.

I've added this to `PLAIN_LANGUAGE_SPEC_AND_REDTEAM_PROTOCOL.md` §2.5 as a standing rule: **every verification command in an audit must be able to fail, and I must state what a passing result would look like before I run it.**

## Consequence for the backlog

**Nothing on the site has an external deadline.** I've been presenting this as the #1 item, above real defects, for five days. The genuine top items are now:

1. `/calendar` publishes **67 / 52** while the API returns **64 / 46** for the same window — and it's inside `FAQPage`, so we're feeding it to engines
2. The conference presenter corpus is **>90% historical** — do not wire it to the display before the miner is fixed
3. `/pricing` advertises a **7-day free trial that doesn't exist**, on the page that's about to get an email form

Your canary point stands too: if the JSON endpoint breaks on Sept 1 anyway, the daily rank snapshot fails loudly in CI that morning. That's better than a migration nobody needed.

---
*Not investment advice.*

**Sources**
- [Bing Webmaster Tools API Services — Microsoft Learn](https://learn.microsoft.com/en-us/bingwebmaster/api-protocols)
- [Bing Webmaster Tools SOAP/POX APIs Retire August 31, 2026 — Search Engine Roundtable](https://www.seroundtable.com/bing-webmaster-tools-soap-pox-apis-retire-41805.html)
