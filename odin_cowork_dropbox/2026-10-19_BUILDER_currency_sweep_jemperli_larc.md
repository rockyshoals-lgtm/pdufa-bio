# Builder note: currency sweep of 2026-10-19; Jemperli rectal cancer published; the two held leads resolved
**2026-10-19, work 22:00 Pacific onward = 01:00 Eastern Oct 20 = 05:00 UTC Oct 20.** *RULE 1.*
*Facts only. Not investment advice.* Responds to "token done, check for currency and that we haven't missed any decisions, update accordingly."

## 1. Vercel token: proven in the CI log
Secret updated 2026-10-19T00:53Z. Every run since prints `vercel token identifies: rockyshoals-7744` and `Successfully purged the CDN cache` (runs 39287871245, 39302248808, 39345258818). The post-push purge is running again for the first time since 09-09.

## 2. Decisions missed: one, and it was never on the calendar
**Jemperli (dostarlimab-gxly), GSK, accelerated approval for dMMR/MSI-H Stage II/III locally advanced rectal cancer, FDA action day October 19, 2026.** Published tonight as `/fda-decision/GSK-2026-10-19`, row `pdufa_gsk_2027-02-28`.
- FDA action day from the FDA's own notification ("On October 19, 2026, the Food and Drug Administration granted accelerated approval to dostarlimab (Jemperli, GSK) ...", fda.gov/drugs/resources-information-approved-drugs/fda-grants-accelerated-approval-dostarlimab-locally-advanced-rectal-cancer). The same-day FDA press release is the item the feed watcher raised.
- Announcement: GSK US release, Issued Philadelphia, October 19, 2026.
- Goal date: GSK US release of August 24, 2026 (sBLA accepted for priority review): "The FDA has assigned a PDUFA action date of February 2027." **Month precision, so no early or late margin is published**, although GSK's release says the approval came ahead of the PDUFA date (Priority Review plus a Commissioner's National Priority Voucher). The timing statistic stays at 32.
- AZUR-1 (NCT05723562) figures on the page are the FDA's: 154 patients, cCR12 47% by central review (116 evaluable), 68% by investigator (144), ORR 79%, median follow-up 26.3 months.
- Drugs@FDA: openFDA (last updated 2026-10-16) has no BLA 761174 supplement for this action yet; `sync_fda_action_dates.py` will swap the letter in. `_drug_approvals_confirmed.json` records jemperli and dostarlimab so the drug pages, once built, cannot say "under review".

**Why it was missed.** The August 24 acceptance never reached the calendar: gsk.com publishes no RSS and the GSK newsroom is not in `_sponsor_feeds.json`, so a sponsor-stated goal date for a large-cap application went unrecorded for eight weeks. The row exists now only because the FDA acted. This is the same class of gap as the 10-08 audit's "two largest-cap sponsors publish no RSS" item; GSK is a third. Carried: a GSK newsroom listing parser (the `html:` listing path the watcher already supports for Novartis).

**Two small things the first render exposed, fixed before the push.**
- The row name first carried "(AZUR-1)" at the end, which defeats `drug_names.clean_drug_name`'s indication stripper, so the title came out "Jemperli (dostarlimab-gxly) - dMMR/MSI-H Approved Oct 19, 2026". Renamed to the established shape (brand (INN) - lower-case indication; trial in `_d.trial`): title is now "Jemperli Approved Oct 19, 2026 for Locally Advanced Rectal Cancer | GSK FDA Decision | pdufa.bio", description 148 characters.
- The Verified-against line said "Goal date none sourced" for a goal GSK did state, to the month. `inject_verified_against.py` now writes "Goal month February 2027, no day stated (GSK press release)" for a sourced month-precision goal, and only when the row's `source_url` is a goal source rather than its own decision letter or FDA record: HYRNUO (BAYRY-2026-09-09) carries the FDA letter in `source` with a date_note saying the goal was never sourced, and briefly picked up a "Goal month November 2026" it had no right to. Guard `test_verified_against_line.py` gains the month check: 0, planted (PLANT_VERIFIED=2, goal month credited to the FDA notification) 1, 0.

**Local guard run, first pass: 142 passed, 10 failed; every failure read, four fixed in code, the rest were my data.**
- `test_api_precision_honesty`: a month-precision row must carry `dm` ("2027-02"). Added.
- `test_decided_not_upcoming`: flagged GSK's bepirovirsen goal (Oct 26) as "Upcoming but /fda-decision/GSK-2026-10-19 says Approved": its near tier (14 days, same ticker) lacked the name-conflict refusal the sync itself has had since the 10-16 brepocitinib/Tukysa fix, so two GSK applications a week apart tripped it. The guard now uses the sync's rule (`_names_conflict`), one rule in one place. Bepirovirsen was never touched by the sync.
- `test_decision_lede_fact_first`: the new page had no lede. `inject_verified_against.py` runs before `build_decision_lede.py` and had already placed its line between the banner and the headline, which the lede builder's regex did not allow, so a page born today got no fact-first sentence until the next run. The builder now allows the block and puts the lede directly under the banner, above it.
- `test_decision_snippets`: a description must answer in one of the guard's shapes; "The FDA granted ... accelerated approval" is not one. Rewritten as "Jemperli (dostarlimab-gxly) was approved by the FDA on October 19, 2026 (accelerated approval) for dMMR/MSI-H locally advanced rectal cancer, on AZUR-1." (152 characters).
- `test_fda_days_by_action_date`: used `dt.date.today()` (Pacific, still Oct 19 at 22:50) against pages built for Eastern Oct 20, so its 45-day window reached Sept 4 and the page's did not. RULE 1 again, in a guard this time; it now uses `eastern_today()`. In CI (TZ=America/New_York) it could never fire.
- `test_drug_pages_state_approvals`: I had recorded a `dostarlimab` slug in `_drug_approvals_confirmed.json`; the drug page is `/drug/jemperli`. Removed.
- `test_dropbox_index_complete`: this note, not yet indexed.
- `test_one_date_per_page`, `test_sls_activity`: the known local-only pair.

## 3. The two held leads (issues #35, #36; escalation #37)
- **#35 drug:aficamten, `sponsor:CYTK:2026-10-19`.** The CYTK item is "Cytokinetics Announces Health Canada Approval of MYQORZO (aficamten) ...", dated October 19. A Health Canada action, not an FDA one; the FDA sNDA (MAPLE-HCM, `pdufa_cytk_2026-11-14`) is unchanged. Acked in `_drug_watch_ack.json` with that reason. The watcher cannot tell regulators apart by headline; that is correct behaviour for a lead.
- **#36 pdufa_ino_2026-10-30, FDA press release "FDA Approves Immunotherapy That May Allow Certain Patients with Rectal Cancer ...".** The item is the Jemperli approval above; INO-3107 (Inovio, recurrent respiratory papillomatosis) is a different application and its goal date stands. Acked in `_fda_drugs_feed_ack.json` pointing at the published page.
Both rows release on this run; #35, #36 and #37 are closed with the run URL.

## 4. Everything else checked, nothing missed
- openFDA approvals 2026-10-13 to 10-20 (data through 10-16): 17 entries; the only decision-class one on a tracked program is Anktiva BLA 761336 S-2 (10-14, already published). No Enspryng BLA 761149 or RYZUMVI NDA 217064 letter yet; both stay announcement-dated.
- FDA press RSS (15 items back to Sept 4): every drug approval item is published (Jemperli 10-19, Anktiva 10-14, MCT8 deficiency 09-28 and the Sanfilippo gene therapy 09-17 are on the site or out of scope as non-US-listed sponsors).
- FDA oncology notifications page: Anktiva 10-14, Tecentriq 10-08, Tukysa 10-07, Jaypirca 10-02, Welireg 09-24, Lyrfigtu 09-23. All but Lyrfigtu (Elevar, not US-listed) have pages. Jemperli is not on that page yet; the notification page carries it.
- No Upcoming PDUFA row has a goal date on or before 2026-10-19.

## 5. Run 39287871245 (16:43 UTC Oct 19) failed at the post-deploy verifier: diagnosed and fixed
`/api/v1/events?limit=5` returned one body on pass 1 (cache MISS) and a different one on pass 2 (MISS, 32 s later), then pass 3 equalled pass 2; `/build-info.json` went MISS with age 0 on pass 2. The deployment of the commit the job had just pushed went live between the passes, so pass 1 read the outgoing build. One transition that then holds is a deploy landing, not an unstable edge. `verify_live_deploy.py` now re-baselines on one change and requires it to hold for every later pass; a second change (flip-flop) or a change on the last pass (convergence unverified) still fails. Proved with a stubbed fetch: stable 0, deploy-landed 0, flip-flop 1, last-pass change 1. The two runs after it passed unchanged.

## 6. Local state
The tree had three stale autostashes and 355 modified generated files from 10-18; `git checkout -- .` followed by a fast-forward applied an old autostash and left a conflict in `pdufa_site_src/index.html`. Reset hard to origin/main (e61c19d), my one edit restored from a copy, then the publish and the chain ran on the clean base. The three autostash entries are still in `git stash list`; their content is all committed, so they can be dropped.

## 7. Shipped and verified live
b29c866, pushed 06:12 UTC Oct 20 (02:12 Eastern, 23:12 Pacific Oct 19); run 39379157258: 152 guards passed, `vercel token identifies: rockyshoals-7744`, `Successfully purged the CDN cache`, verifier PASS on all three passes, quarantine 0 held. Live at 06:30 UTC: `/fda-decision/GSK-2026-10-19` title "Jemperli Approved Oct 19, 2026 for Locally Advanced Rectal Cancer", fact-first lede, Verified-against line with the goal month; `/drug/jemperli` says "FDA approved on October 19, 2026"; `/ticker/GSK` lists the Oct 19 decision; the API row carries `decision_date 2026-10-19`, `date_precision month`, `date_month 2027-02`, `goal_date_held false`. Issues #35, #36, #37 closed with the run URL; no issue is open.

Observed, not changed: the ticker hub's decision-history rows name only the date and outcome ("Oct 19, 2026 ✓ Approved · FDA decision"), not the drug; the same for every row on every hub. A reader on /ticker/GSK cannot tell the Jemperli row from the Blenrep row without clicking. Worth a line each; carried.

## Carried
- Ticker hub decision-history rows: name the drug on each row.
- GSK newsroom listing parser for `_sponsor_feeds.json` (no RSS on gsk.com); same for any sponsor with a month-precision goal and no feed.
- Jemperli BLA 761174 letter swap when Drugs@FDA posts it; Enspryng 761149; RYZUMVI 217064.
- David's: SMTP for email alerts; `SEC_USER_AGENT`; 9realms MCP restart; 131 registry rows; Jaypirca SUPPL-5; MR-100A-01 brand; order 9 scope.
