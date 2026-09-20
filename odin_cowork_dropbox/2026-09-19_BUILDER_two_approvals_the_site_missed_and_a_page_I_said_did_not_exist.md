# Builder, 09-19: two approvals the site missed, the guard that blocked the morning, and a page I said did not exist
**2026-09-19, written 14:30 Pacific = 17:30 Eastern = 21:30 UTC.** *Per RULE 1 every time here carries its zone. Facts and build mechanics only; not investment advice.*

David: *"check the site again today, ensure everything is up to date and accurate, there was a push error this morning."* Two commits, both live and verified: `00106da20` (the approvals, the CI fix, the watcher) and `850d5d1b4` (a retraction of my own 09-18 finding). The autonomous run at 21:14 UTC went green and pushed `993ea9028` on its own -- the first successful scheduled run since the two failures. **91 guards pass, 0 fail.**

---

## 1. The retraction, first, because I wrote the wrong thing yesterday

Yesterday's note said the nav's **Pro** link had "always 404ed" because `pdufa_site_src/pricing/index.html` never existed, and I moved that link to `/developers#tiers` on 954 pages and told you a real `/pricing` page was your commercial decision.

**/pricing has been live the whole time.** `pdufa_site_src/vercel.json` rewrites `/pricing` to `pricing.html` (and 308s `/pricing.html` and `/pricing-elite` onto it). It is indexable, its canonical is itself, it states the same $10/mo and $100/yr as /developers, and it says plainly that Pro is not on sale yet. The dead-link guard I wrote resolved only `<path>/index.html` and never read the routing table; it produced a false positive, and a fixer then "repaired" it sitewide -- a **nav-freeze violation on a false premise** (the freeze file forbids changing the URLs behind the bar until 2027-01-01). Worse than the 954: the next nav rebuild carried it to 1,678 pages, the blanket `href="/pricing"` replace also swept up 204 body links ("See pricing →", "subscribe", "top-up credits", the footer's "Pricing"), and the 09-18 commit edited `pricing.html`'s own nav while claiming the page did not exist.

I found it only because my live verifier for today's push asserted "/pricing is not 200" and the site answered 200. That is the check working as intended -- against me.

**Fixed in `850d5d1b4`:**
- `site_routes.py`: one resolver for guards and fixers. A URL serves if it is in the static tree, **or** vercel.json rewrites it to something that serves, **or** vercel.json redirects it to something that serves. Literal sources only; anything served by a wildcard rule still needs an allowlist entry, so the guard cannot go blind in the other direction.
- `tests/test_no_dead_internal_links.py` and `fix_dead_internal_links.py` resolve through it. The fixer's step 1 is reversed: it restores `PRO = ("/pricing", "Pro")` in `rebuild_nav.py` and on every page's `class="pro"` anchor, and the 204 body links are back. Not one `href="/developers#tiers"` remains on the site (none existed before 09-18).
- `_nav_frozen_until_2027.json` pro entry restored; the revert is recorded in its `changes` list with the reason, next to the wrong entry it undoes.
- Live: `/calendar`, `/developers`, `/fda-decision/RARE-2026-09-17` all render `<a class="pro" href="/pricing">`.

Two lessons for the guard suite, both now enforced. A resolver has to model how the host serves, not how the tree is laid out. And a fixer must never do a blanket string replace on an href that also appears in body copy.

While in there I read `/pricing` for the first time and it turned up **task #82**: the run-up study's size is stated as **1,849** (home), **1,827** (/decisions, /pricing), **1,786** (/developers) and **1,888** (/fda-approval-rate, "our universe"). Some may be different cohorts; home, /decisions, /pricing and /developers plainly describe the same T-120→T+5 dataset. This is the same disease the 09-14 audit cured for the timing statistic -- no single owner. Not touched today; it needs the true row count established from the dataset file first, then one builder and a cross-surface guard.

---

## 2. Why this morning's runs failed (13:37 UTC and 15:28 UTC; nothing pushed)

`gh run view --log-failed` on both: **`test_board_completeness`**. `build_freshness_stamp.next_decision()` had a 7-day cutoff on awaiting events; TLX's September 11 goal was 8 days gone, so build-info promoted RARE as "next" while the homepage board -- which has no cutoff -- still listed TLX first. Two surfaces, two rules, one guard that noticed. The cutoff is gone: an undecided day-precision PDUFA is "next" on both surfaces until it is decided, and `next_days` is null with `days_since_goal` set while it waits. That is the rule the 09-15 audit asked for and I had implemented on one surface only.

---

## 3. Two approvals the site had not published

Both read from the primary document before a byte was written.

**RARE -- FAYUVI (rebisufligene etisparvovec-hopf; UX111 / ABO-102), Sanfilippo syndrome type A.** FDA press release 2026-09-17 and Ultragenyx 8-K filed the same day (acc. 0001515673-26-000006, Item 8.01: standard full approval, Priority Review Voucher). Goal date September 19; **decided two days early**. The site said "decides tomorrow" for a drug that had been approved for two days. Decision page `/fda-decision/RARE-2026-09-17`; calendar row "ABEO / RARE · 2026-09-19 ✓ Approved" linking to it.

**TLX -- Pixclara (floretyrosine F 18; TLX101-Px), PET imaging of glioma.** Telix 6-K filed 2026-09-14 (acc. 0001628280-26-061892, EX-99.1, the ASX announcement) states FDA approval. Goal date September 11; the site said "awaiting" for five days. **The recorded decision date is the announcement date, 3 days after the goal**, and the row says so (`decision_date_note`): the FDA's own action day is not yet in Drugs@FDA and the margin will be corrected from the approval letter if it is earlier. Decision page `/fda-decision/TLX-2026-09-14`.

**Timing statistic restated 28/18/7/3 → 30/19/7/4** on all three surfaces (`/calendar`, `/learn/what-is-a-pdufa-date`, `/research/fda-decision-timing`); live-verified on each. build-info's next pointer is MRK 2026-09-21, upcoming, 2 days.

---

## 4. Why the watcher missed both, and what it does now

It queried **Drugs@FDA only**, which is CDER-only and lags. A CBER gene therapy announced under a brand name assigned at approval, and a diagnostic imaging agent with no FDA press release and a sponsor newsroom that 403s scripts, were both structurally invisible -- not late, invisible.

Three passes now, every armed event, every run:
1. **Drugs@FDA** (unchanged).
2. **FDA press-release feed**, matched on sponsor **and** indication. One disease token of nine or more characters is enough for a lead: "sanfilippo" alone identifies the event.
3. **The sponsor's own 8-K / 6-K in EDGAR full-text**, last 14 days, filer must be the sponsor (the wrong-filer trap from 09-15 -- Nuvalent→BridgeBio, Roche→Cogent -- is checked), and the document must contain a **sentence** stating the FDA approved the drug. The first version of this pass flagged three pipeline decks that said "potential approval"; the sentence-level regex on the drug's first search term ends that.

Proof on a copy of the dataset with RARE and TLX re-armed (`_prove_watch_passes.py`): the press pass catches FAYUVI, the EDGAR pass catches both. Real run after: 40 armed events, 0 unreviewed approvals. Still verify-then-publish: a hit is a lead, never an auto-publish.

---

## 4b. Found by the live verifier, after the push: Pixclara was still "Awaiting" on the calendar

The API said Decided, the decision page was live, and `/calendar` and `/calendar/2026/september` still rendered **"TLX · 2026-09-11 Awaiting"**, with the calendar's September sentence saying the FDA was "due to decide on ... TLX101-Px". Cause: `mark_calendar_awaiting.py` had (correctly) badged the row on 09-14; `mark_calendar_decided.py`'s row pattern did not allow the badge, so a row that went Awaiting could **never** be marked decided afterwards. Every after-the-goal-date approval would have hit this. The pattern now accepts and drops the badge (commit `c…`, below); a new guard `tests/test_decided_rows_marked_on_calendar.py` is the mirror of the 09-14 Awaiting guard -- a dataset row that is Decided with an outcome must link its decision page on every calendar page and must not say Awaiting. Proven 0 → planted the TLX shape → 1 → `mark_calendar_decided` heals → 0. On first run it also flagged five hand-restored rows (ACHV, UNCY, ARQT, LNTH, VERA) that link their decision pages in an older markup shape; those tell the reader the truth, so the invariant is the decision-page link, not the marker attribute.

Chasing that into the September page's structured data: the month pages' JSON-LD ItemList (`"<Month> 2026 FDA PDUFA dates"`) had been written **once** by `seo_pass14_fixups.py` (`if "ItemList" not in page`) and never touched since. June, July and August told every schema consumer that decided events were still scheduled; September listed three decided events (TLX, NUVL, RARE) and omitted the two actually ahead; November listed 3 of 13; August's `numberOfItems` (6) did not match its own four items. `sync_calendar_itemlist.py` -- the owner of the /calendar ItemList since 09-06 -- now owns the month pages too, same definition of "ahead", same Event items, one list per page, removed entirely on months with nothing ahead; the 09-06 guard extends to them (proven against the pass-14 shape).

## 5. Also today

- `/pdufa/RPRX` said zidesamtinib was "under FDA review" 59 days after its approval. RPRX holds a royalty; the decision lives under NUVL. Hand-linked in `_event_page_decisions.json`, bannered.
- `mark_calendar_decided` resolved multi-ticker labels on the **first** ticker only, so "ABEO / RARE" never found a decision filed under RARE. Every ticker in the label is tried now.
- `/pdufa/TLX-tlx101-px` became an indexable twin of `/pdufa/TLX` the moment the event decided; the title-census guard caught it on the first run. Canonicalised (11 known twins in the map).
- 11 untracked `index (1).html` copies under `/drug` (filesystem artefact, 13:54 Pacific today) removed. sls collector run (was 5 days stale).
- Rebase incident: CI's `993ea9028` landed while I was working on the same 1,678 pages; `git stash pop` conflicted on 504 files. Per the rebase playbook I reset to origin, took only the five source files from the stash, and re-ran the scripts on the fresh tree. Nothing hand-edited was lost; the generated pages were regenerated.

---

## 6. Open, in order

- **#82** run-up study size, one owner (above).
- **#77** second half: openFDA pass over the Decided rows; 13 Estimated readouts re-synced into the past need a ruling.
- **Pixclara's FDA action day** from the letter / Drugs@FDA; if earlier than 09-14 the row, the page and the 30/19/7/4 statistic move.
- Carried: 9 unbacked window pages (ratchet 9; the 5 unsourced upcoming rows ABBV / AZN / BAYRY / NVO×2 await your downgrade-or-withdraw ruling); 22 readout leads (#52); `/calendar/2025` unmarked rows; TA back-fill.

*Live verification: `_verify_live_0919.py`, run against production from a non-browser client after each deploy. Commits `00106da20`, `993ea9028` (CI), `850d5d1b4`.*

---

## 7. Appended 17:25 Pacific = 20:25 Eastern = 2026-09-20 00:25 UTC -- task #82 done: one size for the run-up study

David: *"fix runup study size across the website to where it's accurate."*

**The accurate number** is whatever `runup_study_stats.json` says, because `runup_study_stats.py` rebuilds it from `pdufa_runup_bifrost_v2.csv` on every CI run: today **1,852 PDUFA decisions** (2020-01-08 to 2026-09-18), 1,321 approvals / 531 CRLs = **71.3%**, and **1,781** of them (96.2%) carry the full daily T-120 → T+5 price path. The home board and `/runup-by-year` already read it. Five other surfaces had the number typed in by hand in July and never touched again:

| surface | said | now | which statistic |
|---|---|---|---|
| `/decisions` | 1,827 decisions, 70.9% approved | 1,852, 71.3% | n_events, approval_rate |
| `/pricing` | "the 1,827-event T-120→T+5 daily data" | 1,781-event | t120_coverage_n (Pro's export is the per-event daily path; only events with a path count) |
| `/developers` | "price path for 1,786 FDA decisions" | 1,781 | t120_coverage_n |
| `/vktx` | run-up study (1,827) -- a literal in `build_vktx_hub.py` | 1,852, read from the stats file | n_events |
| `/fda-approval-rate` | "first-cycle approval rate 73.5%, n=1,888" | "approval rate, all review cycles 71.3%, n=1,852" | approval_rate, n_events |

**The approval-rate page needed more than a number swap.** The run-up dataset has no review-cycle column, so a *first-cycle* rate cannot be computed from it, and I could not reproduce 73.5% / 1,888 from any file in the repository. The block now says what the figure is -- approvals ÷ (approvals + CRLs) across all review cycles -- and the comparison to FDA's first-cycle reports is restated honestly: a resubmission after a CRL is approved far more often than a first submission, so an all-cycle rate is the *flattering* one, and ours is still below the FDA's. The same page's "ran about 70-74% in 2024-26" was also wrong (2026 is at 85.3% so far, n=156) and is now generated from `by_year`: "74.8% in 2024, 70.0% in 2025 and 85.3% in 2026 so far".

**Owner and guard.** `sync_runup_study_size.py` (new CI step, right after the stats refresh) rewrites those anchors from the stats file, idempotently. `tests/test_runup_study_size_one_owner.py` asserts the render on the seven anchored surfaces **and** does a census: any thousands-count within 80 characters of "run-up study" / "run-up dataset" / "T-120→T+5" on any indexable page must be 1,852 or 1,781 (the conference run-up study, 1,425 presentations, is excluded by name). Proven 0 → planted 1,827 on `/decisions` → 1 → sync heals → 0.

**Found by the census, fixed:** two stale copies of the homepage were publicly served with `robots index,follow` -- `/index_redesign.html` and `/_home_pdufa_backup.html` still said "73 upcoming PDUFAs · 10 decided in 2026 · 1,754 events in the run-up study". Every builder already skipped them; Vercel did not. Moved out of `pdufa_site_src` into `_site_attic/` (not deployed); they 404 now. The other top-level `.html` files are either redirected (`/today`, `/app`), `noindex` placeholders ("locked"), or served on purpose (`/pricing`, `/surges`, `/runup`); `/holding.html` and `/ping.html` are index-eligible utility pages with no data on them -- left alone, noted.

Not touched, on purpose: `/corrections` "n=1,792" is the record of a past correction and stays as written; `/research/readout-reaction` is the readout study (1,752), a different dataset with its own owner.
