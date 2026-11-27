# -*- coding: utf-8 -*-
"""CI guard: a decision dated from the FDA's notice is upgraded to the approval letter once Drugs@FDA posts it.

WHY (2026-11-27): GSK neladalkib, IBRX Anktiva and RHHBY Tecentriq were dated from the FDA's approval notice with the
record "... (letter not yet on Drugs@FDA)". sync_fda_action_dates.py counted those rows as sourced and never looked
again, so weeks after the FDA posted each letter the pages still said it was missing, right above a card that linked
it. The sync now re-checks such rows every run. This test runs the sync offline on a small made-up dataset, with
openFDA answers built in the test, and holds its four rules:

  1. waiting row + same-day approval with a letter  -> record and source become that letter;
  2. waiting row + approval listed without a letter -> nothing changes, the record still says it is waiting;
  3. waiting row + approval on another day          -> a conflict, nothing is written;
  4. two applications approved the same day          -> the one whose product carries the row's brand wins.

Plants (each must FAIL): PLANT=skip (waiting rows are skipped again, as before the fix),
PLANT=brand (the brand tie-break is turned off).

    python tests/test_action_record_letter_posted.py
"""
import io
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import sync_fda_action_dates as S  # noqa: E402

NOT_YET = "letter not yet on Drugs@FDA"   # spelled out here, so PLANT=skip cannot move it
LET = "https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/{}ltr.pdf"
NOTICE = "https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-{}"


def row(rid, t, brand, name, day, rec):
    return {"id": rid, "t": t, "type": "PDUFA", "st": "Decided", "oc": "Approved", "dcd": day, "name": name,
            "_d": {"brand": brand, "fda_action_date": day, "fda_action_source_url": NOTICE.format(brand.lower()),
                   "fda_action_record": rec}}


ROWS = [
    row("r_posted", "AAA", "Zelvora", "Zelvora (testinib)", "2026-11-17",
        "FDA accelerated approval notification, November 17, 2026 (letter not yet on Drugs@FDA)"),
    row("r_noletter", "BBB", "Quintara", "Quintara (sampimab)", "2026-11-20",
        "FDA approval notification (sBLA; letter not yet on Drugs@FDA)"),
    row("r_otherday", "CCC", "Morvexa", "Morvexa (demolisib)", "2026-11-10",
        "FDA approval notification (letter not yet on Drugs@FDA)"),
    row("r_twins", "DDD", "Tecentra", "Tecentra (fakelizumab)", "2026-10-08",
        "FDA approval notification (sBLA; letter not yet on Drugs@FDA)"),
]


def app(appl, brand, generic, day, typ, num, letter=True):
    sub = {"submission_status": "AP", "submission_status_date": day.replace("-", ""), "submission_type": typ,
           "submission_number": num,
           "application_docs": [{"type": "letter", "url": LET.format(appl[-6:] + "s" + num)}] if letter else []}
    return {"application_number": appl, "sponsor_name": "Test", "products": [{"brand_name": brand}],
            "openfda": {"generic_name": [generic]}, "submissions": [sub]}


APPS = [
    app("NDA299001", "ZELVORA", "TESTINIB", "2026-11-17", "ORIG", "1"),
    app("BLA799002", "QUINTARA", "SAMPIMAB", "2026-11-20", "SUPPL", "4", letter=False),
    app("NDA299003", "MORVEXA", "DEMOLISIB", "2026-11-08", "ORIG", "1"),
    # same day, same ingredient: the IV brand (the row's) and a subcutaneous brand with a higher application number
    app("BLA799004", "TECENTRA", "FAKELIZUMAB", "2026-10-08", "SUPPL", "65"),
    app("BLA799099", "TECENTRA HYBRIZA", "FAKELIZUMAB AND HYALURONIDASE", "2026-10-08", "SUPPL", "11"),
]


def fake_query(term):
    return [a for a in APPS if term in (" ".join(p["brand_name"] for p in a["products"]) + " "
                                        + " ".join(a["openfda"]["generic_name"])).upper()]


def test_action_record_letter_posted():
    tmp = tempfile.mkdtemp()
    try:
        S.DATASET = os.path.join(tmp, "dataset.mjs")
        S.STATE = os.path.join(tmp, "state.json")
        S.MANUAL = os.path.join(tmp, "manual.json")
        io.open(S.DATASET, "w", encoding="utf-8").write("export default " + json.dumps(ROWS, indent=1) + ";\n")
        S.query = fake_query
        S.time.sleep = lambda *_: None
        plant = os.environ.get("PLANT", "")
        if plant == "skip":
            S.NOT_YET = "\x00never matches\x00"
        argv = sys.argv
        sys.argv = ["sync_fda_action_dates.py", "--since", "2026-01-01"]
        try:
            if plant == "brand":
                src = io.open(S.__file__, encoding="utf-8").read().replace("if len(pick) == 1:", "if False:")
                ns = {"__file__": S.__file__, "__name__": "sync_planted"}
                exec(compile(src, S.__file__, "exec"), ns)
                ns["DATASET"], ns["STATE"], ns["MANUAL"] = S.DATASET, S.STATE, S.MANUAL
                ns["query"] = fake_query
                ns["time"].sleep = lambda *_: None
                ns["main"]()
            else:
                S.main()
        finally:
            sys.argv = argv
        src = io.open(S.DATASET, encoding="utf-8").read()
        got = {r["id"]: r["_d"] for r in json.loads(src[src.index("["):src.rindex("]") + 1])}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    bad = []
    d = got["r_posted"]
    if d["fda_action_record"] != "NDA 299001 ORIG-1" or d["fda_action_source_url"] != LET.format("299001s1"):
        bad.append(f"rule 1: a same-day letter was not taken up: {d['fda_action_record']!r} {d['fda_action_source_url']}")
    d = got["r_noletter"]
    if NOT_YET not in d["fda_action_record"] or "fda.gov/drugs/resources" not in d["fda_action_source_url"]:
        bad.append(f"rule 2: a listing without a letter changed the record: {d['fda_action_record']!r}")
    d = got["r_otherday"]
    if NOT_YET not in d["fda_action_record"] or d["fda_action_date"] != "2026-11-10":
        bad.append(f"rule 3: an approval on another day was written: {d['fda_action_record']!r} {d['fda_action_date']}")
    d = got["r_twins"]
    if d["fda_action_record"] != "BLA 799004 S-065":
        bad.append(f"rule 4: the same-day application without the row's brand won: {d['fda_action_record']!r}")
    assert not bad, "sync_fda_action_dates.py letter upgrade:\n  " + "\n  ".join(bad)


if __name__ == "__main__":
    test_action_record_letter_posted()
    print("OK")
