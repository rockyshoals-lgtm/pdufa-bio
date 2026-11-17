# Note for the pdufa builder (2026-11-17): homepage board lags one run behind a same-day decision

Observed (all times UTC): PR 104 published Nelkarmi (neladalkib, GSK/Nuvalent) as Decided/Approved on 2026-11-17.
Rebuild 430 (run 44178742121, started 21:20 UTC = 16:20 ET = 13:20 PT) passed every guard and committed 0cefab516d,
but the homepage "Next FDA decisions" board still showed GSK neladalkib at 10 days (PDUFA 2026-11-27), and
"Recently decided" lacked GSK. The stats/lede in the same file did update (18 upcoming, 183 decided).

Cause: in .github/workflows/pdufa-rebuild.yml, "Regenerate homepage board" (python build_home_board.py, ~line 147)
reads api/data.js (slate) and the /decisions listing, but runs BEFORE
  - "Decision pages -> /decisions listing" (~step 16) and
  - "Sweep decided events off the homepage slate" (build_slate_from_crawl.py --sweep-only, ~line 211).
So the board is built from the pre-sweep slate and the pre-update listing. Re-running build_home_board.py on the
committed tree (data.js already swept) produces the correct board. Rebuild 431 was dispatched to correct it live.

Suggested fix (yours to make; not committed by me): run build_home_board.py again after the slate sweep and the
/decisions listing step, keeping it before the two index.html post-writers noted at ~line 633 ("MUST run after
build_home_board regenerates it"). No guard caught this: a guard that fails when a board row's id is st=Decided
in dataset.mjs would.
