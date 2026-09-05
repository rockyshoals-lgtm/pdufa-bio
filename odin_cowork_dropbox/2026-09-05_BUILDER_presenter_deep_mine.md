# Builder — conference presenter deep mine (all 41 upcoming conferences)
*2026-09-05 (Pacific). Facts and build mechanics only, not investment advice.*

## The haul: 31 new company-sourced presenter rows

Four parallel research agents swept every one of the 41 upcoming conferences for
company-primary-sourced presenter announcements (wire or IR releases only; abstract
portals and third-party roundups do not count). Verified and ingested via
`ingest_presenters_2026_09_05.py` (idempotent by ticker+conference):

- **WCLC (Sep 12)**: CGEM (Presidential Symposium), BNTX, NUVB, SMMT, ABBV
- **ESMO (Oct 23)**: NUVB, CMPX, IMTX, ZNTL, XNCR, IDYA, EIKN, ORIC, KTTA, IMMP, BLRX
- **ERS (Sep 5)**: BEAM, SVRA, GRI, TRVI, UTHR, KYMR, LQDA, INSM, RNTX
- **EASD (Sep 28)**: SANA, IPSC, IBIO · **ASTRO (Sep 26)**: CADL
- **ECTRIMS (Oct 21)**: TLSA · **AASLD (Nov 5)**: MNPR

PRECLINICAL rows are labeled on their face (BLRX, IPSC, IBIO, ORIC in part) so the
clinical-readout conference statistics cannot silently attach to them. Excluded: CAI
(diagnostics, not a therapeutics catalyst), non-US listings, private companies.
Dupes already in the store (EVAX/ESMO, CRVO/CTAD) skipped by the idempotency key.
Agents also confirmed EIKN is Nasdaq-listed (Feb 2026 IPO).

**/conferences now renders 41 sourced presenter rows, up from 15.**

## One guard earned its keep

`test_no_fabricated_conferences.py` rejected the first ingest — 22 future-dated rows
whose snippets lacked a forward-looking cue ("will present" / "to be presented").
The snippets were rewritten to state the announcement as an announcement ("Company
announced it will present at {conf} 2026") rather than reading like the data already
exists. That is exactly the fabrication class the guard was built for, and it caught
its own builder. All 60 guards green after the fix.

## Re-scan calendar (most meetings have no company PRs yet)

The agents recorded which meetings returned nothing because announcements simply
have not been made, not because nothing is coming:

- **~Sep 18**: ASTRO late-breakers, AACR-PANC, WMS
- **~Oct 1**: October US meetings (ASN Kidney Week, IDWeek, AHA, ACAAI, ACG, AAO, ASBMR)
- **~Nov 5**: ASH abstract drop (the big one) + December wave (SABCS, ESMO-IO, ESMO-Asia, ACR, AES, ObesityWeek)

## Mechanics

Rebase collision handled per the amended playbook: `git checkout origin/main --
pdufa_site_src _sitemap_lastmod.json` (exit code checked), all generators re-run on
CI's fresh base, marker count 0 before commit, push before CI trigger. The rebuilt
ticker hubs briefly dropped the legal footer; `apply_legal_footer.py` restored it and
`test_copy_standards.py` was the guard that noticed.
