# Builder note: RYZUMVI (phentolamine 0.75%) approved for presbyopia; two held leads resolved; Onswik on the letters hub
**2026-10-17, work 21:10 to 22:30 Pacific (Oct 16) = 00:10 to 01:30 Eastern = 04:10 to 05:30 UTC (Saturday).** *RULE 1.*
*Facts only. Not investment advice.*

## 1. The held leads (GitHub notice: held since 2026-10-16T16:13:56Z UTC, 2 consecutive runs)
- `[sponsor_feed] pdufa_ird_2026-10-17`: Opus Genetics "Announces FDA Approval of Phentolamine Ophthalmic Solution 0.75% for the Treatment of Presbyopia".
- `[drug_pages] phentolamine-ophthalmic`: the same release, read through the drug page.

**Verified, primary sources:**
- **Opus Genetics release** on ir.opusgtx.com, "October 16, 2026 12:00pm EDT": Opus "today announced that the U.S. Food and Drug Administration (FDA) has approved the Company's supplemental New Drug Application (sNDA) for phentolamine ophthalmic solution 0.75% for the treatment of presbyopia in adults."
  - The product is RYZUMVI (NDA 217064, approved 2023 for pharmacologically induced mydriasis).
  - Approval rests on VEGA-2 and VEGA-3.
  - Viatris holds exclusive U.S. commercial rights, and the approval triggers a milestone payment to Opus.
- **Goal date:** Opus release of 2026-02-25, "The FDA has assigned a PDUFA goal date of October 17, 2026." The IRD row had cited a **BioSpace copy** (an aggregator); it now cites the sponsor's own page. VTRS's row keeps its Viatris 8-K source.
- **FDA action day: not on record.** openFDA (last_updated 2026-10-16) shows no new NDA 217064 supplement, and no FDA feed item exists. The release does not state the FDA's day. So, on the Enspryng / LNTH pattern, both rows get:
  - `dcd` 2026-10-16 and `decision_date_unsourced`;
  - **no margin against the Saturday goal date**, and no entry in the timing statistic until Drugs@FDA posts the letter.

**Published:**
- `pdufa_ird_2026-10-17` and `pdufa_vtrs_2026-10-17` set to Decided / Approved.
- `/fda-decision/IRD-2026-10-16` and `/fda-decision/VTRS-2026-10-16`, one per partner ticker (the INCY/MIRM Atebrioz convention), each with three FAQs.
- `_drug_approvals_confirmed.json` records phentolamine-ophthalmic 2026-10-16.
- Both lead keys acked with reasons, in `_newswire_ack.json` and `_drug_watch_ack.json`.

**The quarantine worked as designed this time.** This is item 4 of the 10-16 audit: the first held lead since the 10-15 fix. Two runs held the IRD/VTRS rows and the rest of the site kept deploying; the notice itself says "The rest of the site is still rebuilding and deploying". The fix holds.

## 2. Onswik on /fda-approval-letters
`sync_archive_fda_dates.py` searched Drugs@FDA for "Onswik" and for "insulin", the first word of the INN. That found two insulin approvals, so the page was marked ambiguous and left off the letters hub. When the combined search is ambiguous, the matcher now accepts the brand alone if the brand names exactly one approval. The cache entry was cleared so it re-checks.

## 2b. Two defects publishing exposed, both fixed
- **The rebuild deleted `/drug/phentolamine-ophthalmic` (and `/drug/mr-141`) the moment the rows were decided.**
  - `build_drug_pages.py` skips a Decided row whose action day differs from its goal day (10-16 vs 10-17), on the assumption that the archive source renders that decision.
  - The archive source parses decision-page titles, and it does not read "Approval Announced" titles (every announcement-dated page: Enspryng, RYZUMVI, LNTH).
  - Both rows were skipped, the page had no events, and the from-scratch rebuild dropped it. That deletes an indexed URL on the day of the approval.
  - Fix: the skip now applies only when the archive row really is on the same drug page; otherwise the dataset row renders the decision, dated and linked to its decision page.
  - Both pages are back: `/drug/phentolamine-ophthalmic` reads "FDA decision · Oct 16, 2026 ✓ Approved". `test_drug_pages_state_approvals` caught the vanished page locally.
- **`quarantine_leads.py apply` crashed with FileNotFoundError** restoring a held page whose directory the rebuild had removed. In CI that would have aborted the step. It now recreates the directory.
- **Self-correction:** my first draft of the rows' `seo_desc` said "the day before its October 17 goal date", which is a margin taken from an announcement date. It now reads "The goal date was October 17, 2026."

## 3. Incident during this work (recorded so it is not repeated)
1. A `git pull --rebase` autostash conflicted across ~1,700 generated pages. Locally built pages from the interrupted 10-16 run collided with CI's refresh commits.
2. I stopped the local chain before it built on the conflicted tree.
3. My process filter (`python.exe` with `-X utf8` or `9realms` in the command line) **also stopped two `mcp_9realms_vnext.py` processes, David's 9realms MCP server**. Those need the Claude app to restart the server. Next time, stop by PID taken from the .bat's own process tree, never by pattern.
4. Recovery: `git reset --hard` to e953fec (remote state). The real local work (the matcher fix, today's new files) and the non-site files (tracker, charts, stock cache) were restored from `stash@{0}`, which is kept. The publish was then re-run on the clean base.

## Carried, still David's
- Bing Request indexing for `/fda-decision/RHHBY-2026-10-15`, `/fda-decision/IRD-2026-10-16` and `/fda-decisions-today`.
- CI `SEC_USER_AGENT` empty in the SLS step.
- `goal_date_held`; Jaypirca SUPPL-5; RXC-005 aliases; SMTP; Drive exclusion; AZN Ultomiris / NVO CagriSema / NVO Mim8 sources; the 20 nct-mismatch readouts; the 131 registry rows.
