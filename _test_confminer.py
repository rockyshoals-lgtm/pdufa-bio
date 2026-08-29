"""Smoke the conference brain on the headline shapes companies actually use."""
import sys, os, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import conference_presentations as CP

reg = CP.load_registry()
CASES = [
    # (text, expect_hit)
    ("XYZ Therapeutics to present Phase 2 data in an oral presentation at the "
     "ESMO Congress 2026", True),
    ("ABC Bio announces poster presentations at the American Society of Hematology "
     "(ASH) Annual Meeting 2026", True),
    ("GHI announces data presentations at the Society for Immunotherapy of Cancer "
     "(SITC) Annual Meeting 2026", True),
    ("MNO Pharma announces late-breaking presentation at the American Heart "
     "Association Scientific Sessions 2026", True),
    ("DEF reported results at AACR 2024", False),                   # past
    ("JKL to participate in the Jefferies Healthcare Conference", False),  # investor conf
    ("The presentation discussed our strategy for growth", False),  # noise
    ("PQR will present at the 44th Annual J.P. Morgan Healthcare Conference", False),
    # 2026-08-29 gap-fill congresses (from the fresh-BPC compare)
    ("IONS to present late-breaking data at the European Society of Cardiology "
     "(ESC) Congress 2026", True),
    ("LLY announces oral presentations at the European Academy of Dermatology and "
     "Venereology (EADV) Congress 2026", True),
    ("EYPT to present DURAVYU data at the Annual Retina Society Scientific Meeting 2026", True),
    ("BEAM to present at the ERS International Congress 2026", True),
    ("ENTX will present Phase 3 data at the American Society for Bone and Mineral "
     "Research (ASBMR) 2026 Annual Meeting", True),
    ("IRD to present at the EURETINA Congress 2026", True),
]
bad = 0
for t, want in CASES:
    r = CP.extract(t, filed_dt=dt.date(2026, 8, 25), registry=reg)
    got = r is not None
    ok = got == want
    bad += 0 if ok else 1
    tag = (f"{r['conference']} {r['catalyst_date']} {r['date_precision']}/"
           f"{r['date_basis']} {r['pres_type'] or '-'}") if r else "None"
    print(f"  {'OK  ' if ok else 'FAIL'} {tag:<44} <- {t[:58]}")
print(f"\n{len(CASES)-bad}/{len(CASES)} pass")
sys.exit(1 if bad else 0)
