# -*- coding: utf-8 -*-
"""apply_1117d_date_redteam.py -- every open PDUFA date and upcoming readout date, re-checked 2026-11-17 (Eastern).

David 2026-11-17 (Eastern; 2026-11-18 UTC): "Red team the readout and pdufa dates again, let's build our moat here too as the most
accurate." Then: "Go live after red team".

Input: odin_cowork_dropbox/2026-11-17_date_redteam.json. All 55 open PDUFA rows, all 236 company-guided
readouts with a window still ahead and all 154 upcoming Estimated readouts were checked against the company's
newest release / SEC filing / ClinicalTrials.gov record. No FDA decision, extension or withdrawal was found
on an open PDUFA row. The changing items:

  re_source     PDUFA date unchanged; source, link and the sponsor's own sentence replaced with the newest
                one that states it (CAPR had no quote at all; MLYS quoted raw EDGAR wrapper text).
  novo_window   Novo rows whose goal date is not announced: sort key / precision follow the 6-K milestones
                table (CagriSema US decision Q4 2026; Mim8 review extended, US decision H1 2027).
  to_day        a readout keyed to a conference window gets the day the company's own release gives.
  to_half       "by mid-year 2027" is a first-half window, not a 2027 year window (VXRT).
  quote         quote replaced with the release's exact words (ASND).
  date_quote    `_d.date_quote` = the release's own date words for a listing whose quote is a title.
  reported      data released before the scheduled presentation (INBX Ewing sarcoma, Nov 17 after close).
  remove        a duplicate row (SLS ASH poster was listed twice).
  est_add_nct   an Estimated row with no trial behind it gets the one ClinicalTrials.gov record that matches
                its drug, sponsor and month; the row links that record.
  est_rename    the row named a drug the linked trial does not test (comparator or another asset): the
                name becomes the trial's own experimental drug.
  est_remove    an Estimated row with no registry record for its drug in its month, or whose record is
                another company's or another drug's trial, leaves the dataset: a date nobody can trace is
                not published.

It also writes _date_checks.json: one entry per checked PDUFA / guided row (tests/test_date_checks_current.py).
Idempotent. Facts only, not investment advice. RULE 1: dates are the companies' own calendar dates; "today" is
the Eastern date.

    python apply_1117d_date_redteam.py [--dry-run] [--ledger <rows.json>]
"""
import argparse
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
SPEC = os.path.join(HERE, "odin_cowork_dropbox", "2026-11-17_date_redteam.json")
ACK = os.path.join(HERE, "_readout_watch_ack.json")
from site_dates import eastern_today  # noqa: E402
CHECKED = eastern_today().isoformat()
RT = f"{CHECKED}: date red team; source re-opened and checked against the company's newest disclosure. "


def short(s, n):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "…"


def move(r, new_d, why):
    dd = r.setdefault("_d", {})
    old = str(r.get("d") or "")[:10]
    if old == new_d:
        return
    hist = dd.get("date_history") or []
    if not hist:
        hist.append({"date": old, "note": "date the row showed before this check"})
    hist.append({"date": new_d, "changed": CHECKED, "why": short(why, 300)})
    dd["date_history"] = hist
    r["d"] = new_d


def src_label(url, date):
    kind = "SEC filing" if "sec.gov" in url else "company release"
    return f"company guidance ({kind})"


def apply(rows, spec):
    by = {r.get("id"): r for r in rows}
    remove, n, missing = set(), {}, []
    for it in spec["items"]:
        act, rid = it["action"], it["id"]
        r = by.get(rid)
        if r is None:
            missing.append(rid)
            continue
        dd = r.setdefault("_d", {})
        if act == "re_source":
            dd["source"], dd["source_url"], dd["source_quote"] = it["source"], it["source_url"], it["source_quote"]
            if it.get("name"):
                r["name"] = it["name"]
            if it.get("indication"):
                dd["indication"] = it["indication"]
            for h in dd.get("date_history") or []:
                if it.get("fix_history_url") and h.get("url") == it["fix_history_url"][0]:
                    h["url"] = it["fix_history_url"][1]
            dd["red_team"] = RT + short(it["why"], 300)
        elif act == "novo_window":
            move(r, it["d"], it["why"])
            r["dp"] = it["dp"]
            r.pop("dm", None)
            dd["date_note"] = it["date_note"]
            dd["red_team"] = RT + short(it["why"], 300)
        elif act == "to_day":
            move(r, it["d"], it["why"])
            r.update({"dp": "day", "url": it["source_url"]})
            r.pop("dm", None)
            dd.update({"guided_precision": "day", "guided_window": it["d"], "guided_label": short(it["label"], 60),
                       "guided_form": "press release", "guided_filed": it["source_date"],
                       "guidance_text": short(it["quote"], 600), "source_url": it["source_url"],
                       "source": src_label(it["source_url"], it["source_date"]),
                       "red_team": RT + short(it["why"], 300) + (" " + it["note"] if it.get("note") else "")})
            dd.pop("date_quote", None)
        elif act == "to_half":
            move(r, it["d"], it["why"])
            r["dp"] = "year"           # house convention: half windows carry dp "year" + guided_precision "half"
            r.pop("dm", None)
            dd.update({"guided_precision": "half", "guided_window": it["window"], "guided_label": it["label"],
                       "red_team": RT + short(it["why"], 300)})
        elif act == "quote":
            dd["guidance_text"] = it["quote"]
            dd["red_team"] = RT + short(it["why"], 300)
        elif act == "date_quote":
            dd["date_quote"] = it["date_quote"]
        elif act == "reported":
            move(r, it["d"], "the company released the data on this date, ahead of the scheduled presentation")
            r.update({"st": "Reported", "dp": "day", "url": it["url"]})
            r.pop("dm", None)
            dd.update({"review": it["review"], "reported_source_url": it["url"], "reported_quote": it["quote"],
                       "red_team": RT + short(it["why"], 300)})
        elif act in ("remove", "est_remove"):
            remove.add(rid)
        elif act == "est_add_nct":
            dd["nct_id"] = {"nct": it["nct"], "status": it.get("status") or "", "pcd": it["pcd"],
                            "pcd_type": it.get("pcd_type") or "estimated", "updated": CHECKED, "ongoing": True}
            link = f"https://clinicaltrials.gov/study/{it['nct']}"
            dd["source_url"] = link
            r["url"] = link
            if it["pcd"][:7] != str(r.get("d"))[:7]:
                move(r, it["pcd"][:7] + "-15", f"ClinicalTrials.gov primary completion for {it['nct']} is {it['pcd']}")
                r["dm"] = it["pcd"][:7]
            if it.get("name"):
                r["name"] = it["name"]
            dd["registry_match"] = {"checked": CHECKED, "sponsor": it.get("sponsor"), "basis": short(it["why"], 300)}
        elif act == "est_rename":
            r["name"] = it["name"]
            dd["name_fix"] = {"checked": CHECKED, "was": it["old"],
                              "why": "the linked ClinicalTrials.gov record tests " + it["name"] + ", not " + str(it["old"])}
        else:
            raise SystemExit(f"unknown action {act}")
        n[act] = n.get(act, 0) + 1
    rows[:] = [r for r in rows if r.get("id") not in remove]
    return n, remove, missing


def write_ledger(ledger_rows):
    from record_date_check import load, record, save
    j = load()
    j["_comment"] = ("Re-checks of open dates against their sources (tests/test_date_checks_current.py). One entry "
                     "per row: date checked, verdict, newest source looked at. Write with record_date_check.py.")
    for x in ledger_rows:
        record(j, x["id"], x["verdict"], x["source"], short(x.get("note"), 200), checked=CHECKED,
               by=f"red team {CHECKED}")
    save(j)
    return len(ledger_rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--ledger", help="JSON list of {id, verdict, source, note} from the red-team verdicts")
    a = ap.parse_args()
    spec = json.load(io.open(SPEC, encoding="utf-8"))
    src = io.open(DATASET, encoding="utf-8").read()
    i, j = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[i:j])
    n, remove, missing = apply(rows, spec)
    acks = json.load(io.open(ACK, encoding="utf-8"))
    acks["acks"] = [x for x in acks.get("acks", []) if x.get("id") not in remove]
    print("applied:", n, "| removed", len(remove), "| not found", missing)
    if a.dry_run:
        return
    io.open(DATASET, "w", encoding="utf-8", newline="").write(src[:i] + json.dumps(rows, ensure_ascii=False, indent=1) + src[j:])
    io.open(ACK, "w", encoding="utf-8", newline="").write(json.dumps(acks, ensure_ascii=False, indent=1) + "\n")
    if a.ledger:
        led = [x for x in json.load(io.open(a.ledger, encoding="utf-8")) if x["id"] not in remove]
        print("ledger entries:", write_ledger(led))


if __name__ == "__main__":
    main()
