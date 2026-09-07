# 2026-09-07 AUDITOR → BUILDER 08:40 re-audit — RUN 08:49–08:55 Pacific (11:49–11:55 Eastern)
*Live site only (https://www.pdufa.bio, curl with `Cache-Control: no-cache`), never the clone. Machine clock Pacific; market/FMP/company releases Eastern; Vercel headers UTC; every timestamp names its zone. Informational and educational only — not investment advice. No probabilities, no price targets.*

## Status of the two inputs
- **08:00 audit: FILED in full** (`2026-09-07_audit_0800.md`, 13,844 bytes, written 08:12 PT). Not a stub. Its ORDER of five is the list graded below.
- **08:20 builder ack: ABSENT.** Checked 08:49, 08:50 and again at 08:53 PT after the 3-minute wait. No `2026-09-07_BUILDER_ACK_0820.md`, no other BUILDER_* file modified after 08:00 PT today. (The two files named `2026-09-07_AUDIT_conference_runup_stack.md` / `2026-09-07_BUILDER_conference_runup_surface.md` carry today's date in the name but were written 2026-09-06 18:44 PT and are already covered by the 09-06d/torque cycle — not new, not an ack.)
- **Live build unmoved:** `/build-info.json` `built` **2026-09-07T03:47:52+00:00** (= 20:47 PT / 23:47 ET Sept 6), `commit` **e76d00ac7** — identical to the 08:00 read, re-checked at 08:49 and 08:53 PT. Nothing deployed since the 08:00 audit, so every ORDER item is graded against e76d00ac7.
- Scheduler note: this run fired 08:49 PT, which CADENCE.md lists as the expected jitter for the 08:40 slot — not late. The builder's 08:20 slot leaving no file is the second day running a slot fired silently (09-06: auditor 08:00 and builder 09:00).

## ORDER of 08:00 — PASS/FAIL, live, e76d00ac7
| # | item | verdict | live evidence (fetched 08:49–08:53 PT) |
|---|---|---|---|
| 1 | C1 API cache policy: SWR ≤ 300 s, purge on deploy | **FAIL — unchanged** | `curl -sI /api/v1/events?limit=500` → `cache-control: s-maxage=1800, stale-while-revalidate=86400, stale-if-error=604800` (same on `cdn-cache-control`). First GET of this run: `x-vercel-cache: STALE`, `age: 2843` — a 47-minute-old copy served past its 1,800 s freshness on the SWR path, exactly the mechanism in C1. Payload happened to be current (`as_of` 2026-09-07, `total` 456); second fetch 30 s later HIT/age 50, identical `as_of`/`total`. The two-fetch sub-check passes today; the header check fails. |
| 2 | C2 stampers via `site_dates.eastern_stamp()` + one date per page | **FAIL — unchanged** | Eastern date of the build is **Sept 6**. `/fda-this-month` header "Updated September 7, 2026"; `/drug/camizestrant` "Updated September 7, 2026"; `/runup-by-year` "Updated Sep 7, 2026". `/calendar` header "Updated September 6, 2026", lede "updated September 6, 2026" ×8, JSON-LD "as of September 6, 2026" ×2; `/pdufa/GILD-bictegravir-and-lenacapavi` "Updated September 6, 2026". Same build, two dates across pages. **See correction below on the /calendar header.** |
| 3 | C3 NRXP sentence | **FAIL — unchanged** | `/pdufa/NRXP`: "no public decision" ×3 (story sentence: "was under FDA review, with a goal date of July 29, 2026 that has passed with no public decision"; description and og text repeat it); "July 30, 2026" ×0; "major deficiency" ×1 (the contradicting lower sentence is still there). |
| 4 | C4 titles + guard | **FAIL — unchanged** | `<title>GILD PDUFA date: Bictegravir and Lenacapavir, Aug 27 2026</title>`; `<title>RARE PDUFA date: DTX401 AAV gene therapy, Aug 23 2026</title>`. Neither contains "FDA decision" or "Approved". Guard unverifiable (no ack). |
| 5 | SRRK index page caveat | **FAIL — unchanged** | `/pdufa/SRRK`: "Catalent" ×0, "Catalent Indiana" ×0, "fill-finish" ×0. `/pdufa/SRRK-apitegromab`: "Catalent" ×1, "fill-finish" ×1 (as at 08:00). |

**Score: 0 of 5 shipped.** No ack to spot-check; no pushback to test.

## Fast currency gates (API `/api/v1/events?limit=500`, 456 rows; `/calendar`; `/fda-this-month`)
- `meta.as_of` **2026-09-07**; max `updated_at` 2026-09-07T01:50:05Z. Equals today in all three zones → **cannot fail today, not credited.**
- PDUFA rows 85 (53 Upcoming, 32 Decided). Rows with `date_precision = day`, `date < 2026-09-07`, status ≠ Decided: **0** — PASS. Next day-precision goal dates: TLX 09-11, RARE 09-19, MRK 09-21, INCY + MIRM 09-26, BFRI 09-28, NVO + SRRK 09-30 (SRRK apitegromab 2026-09-30 Upcoming present on this fetch).
- Guided readouts 57; past-date Guided without outcome: **0** — PASS, but no Guided row has day precision (all month/quarter), so the gate is weak today — **credited lightly.**
- `/calendar` lede "97 FDA decision dates … 48 are still ahead, and 49 have been decided"; month sentences 23 + 11 + 9 + 13 + 7 + 13 + 21 = **97** ✓; decided 23 + 11 + 9 + 6 = **49** ✓; ahead 7 + 7 + 13 + 21 = **48** ✓; links 48 `/pdufa/` (47 unique) + 49 `/fda-decision/` ✓. `/fda-this-month` "13 tracked PDUFA events fall in September 2026: 6 decided so far and 7 still ahead" = `/calendar` September 13/6 ✓.
- ItemList/sitemap/FDA-surface sweeps not re-run: same build as 08:00, results would be identical by construction.

## NEW findings this slot
- **N1 (process, P1):** builder 08:20 slot silent for the second time in two days. Builder prompt should write its own stub first (asked in 09-06 diag; still not evidenced). Until an ack exists, every 08:40 is a re-grade of the same build.
- **N2 (C1 evidence):** `x-vercel-cache: STALE` / `age: 2843` on the API's first GET is the SWR path observed again on a fresh run — the policy, not a one-off. Content was current this time; it was not at 15:01Z.
- **N3 (observation, not credited):** per-page `last-modified` differs on one build — `/calendar` 04:17:07Z (age 41,563 s, HIT, against `s-maxage=300, stale-while-revalidate=600`), `/fda-this-month` 15:02:58Z (= 08:02 PT, during the 08:00 audit). Static output on Vercel is cached until redeploy, so an age past s-maxage is expected there; recorded because it means the declared cache-control on HTML pages is not what governs staleness — the deploy is. Which layer held the Sept 5 calendar at 15:01Z remains **unverified from this evidence.**
- SERP read (carry-forward 1) skipped again — Chrome not opened this run; queued for 09:20.

## Corrections I owe
- The 08:00 note (same auditor role) recorded the `/calendar` page-header stamp as "Updated September 7, 2026" beside a lede of "September 6". At 08:49–08:53 PT on the **same build** the header reads "Updated September 6, 2026" (three fetches, all HIT, age ≈ 41,600 s). I cannot reproduce the two-dates-on-one-page claim for `/calendar`; either the 08:00 run read a different cached generation (it had just been served a Sept 5 generation minutes earlier) or it misread. C2 itself stands on `/fda-this-month`, `/drug/camizestrant` and `/runup-by-year` — but the "one page, two dates" framing for `/calendar` is **unverified from this evidence**, and I withdraw it until a fetch shows it.
- Nothing else to correct: the builder made no claims this slot.

## ORDER for the 09:00 slot — five items, all carried FAILs, P1 first (each with the 09:20 acceptance check)
1. **C1 cache policy** (carried). Cut `stale-while-revalidate` on `/api/v1/*` to ≤ 300 s and `stale-if-error` to ≤ 3600 s; purge/revalidate API + `/calendar` on deploy; say which layer served the 87/49/38 calendar if you can find it. *09:20 check:* `curl -sI https://www.pdufa.bio/api/v1/events?limit=500` shows `stale-while-revalidate` ≤ 300; two GETs 30 s apart return identical `as_of`/`total`; `build-info.built` has moved past 03:47:52Z.
2. **C2 stampers** (carried). Route the header "Updated" stamper, `/drug/*` and `build_runup_by_year.py` (`TODAY`) through `site_dates.eastern_stamp()`; guard renders with a planted 03:00Z clock and requires one date per page. *09:20 check:* `/calendar`, `/fda-this-month`, `/drug/camizestrant`, `/runup-by-year` all print the same date = Eastern date of `build-info.built`.
3. **C3 NRXP** (carried). Replace "has passed with no public decision" (×3, including meta description) with what NRx filed: first-cycle review complete July 30, 2026, one major deficiency (container closure / Luer lock), attestation submitted — sourced to the Q2 10-Q / Aug 17 release. *09:20 check:* `/pdufa/NRXP` contains "July 30, 2026" and "major deficiency"; "no public decision" ×0.
4. **C4 titles + guard** (carried). Retitle `/pdufa/GILD-bictegravir-and-lenacapavi` and `/pdufa/RARE-dtx401-aav-gene` to "FDA decision: … Approved <date>"; extend `test_no_past_target_pending_pages.py` to fail a "PDUFA date:" title with a past date over an Approved/CRL body; prove 0→1→0. *09:20 check:* both `<title>`s contain "FDA decision" and "Approved"; guard count and the 0→1→0 line in the ack.
5. **SRRK index page** (carried). Catalent Indiana / second fill-finish facility caveat with the Aug 21 release linked on `/pdufa/SRRK`. *09:20 check:* `/pdufa/SRRK` contains "Catalent Indiana" and "fill-finish".

**Ack hygiene:** write `2026-09-07_BUILDER_ACK_0900.md` as a stub ("RUN STARTED HH:MM PT") before doing anything, then overwrite. If a push lands, put the new commit SHA in the ack so 09:20 can match it to `build-info.commit`.

## CARRY-FORWARD (unchanged order from 08:00, plus N1)
1. Builder stub-first prompt + confirm the 08:20 scheduler actually fired (N1). 2. SERP read (Bing "pdufa calendar", "pdufa dates 2026") at 09:20. 3. NEW-4 API `source_url`/`page_url` split. 4. NEW-5 JUVÉDERM PMA ruling. 5. Torque item 7 dual-anchor + the 90.2%-vs-76.7% readout sentence — David's call. 6. 09-06f UNCY case-study ORDER (publish, link both FDA letters, vocabulary guard incl. em dash, 1,845 de-dup). 7. 09-06b Gemini keepers (CRL reason taxonomy as counts, shares-outstanding deltas) + /terms /privacy 404. 8. 13F / Form 4 blocks (09-05c). 9. Daily gates — same-day builds cannot fail as_of; sums can.

## Bottom line
Both inputs were checked: the 08:00 audit is complete, the 08:20 ack never landed, and the live build is still e76d00ac7 from 23:47 ET last night, so all five ORDER items grade FAIL by non-delivery rather than by defect in the work. The site itself is current — every gate green on a Labor Day, next goal date TLX Sept 11 — and the API's first response again came off the stale-while-revalidate path, which is the P1 to fix first. One correction on my side: the "two dates on /calendar" claim does not reproduce; C2 stands on three other pages.

*Informational and educational only; not investment advice. Auditor, 08:55 PT.*
