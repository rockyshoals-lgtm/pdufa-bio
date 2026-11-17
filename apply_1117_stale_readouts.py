# -*- coding: utf-8 -*-
"""apply_1117_stale_readouts.py -- stale readout windows, checked against primary sources 2026-11-17.

David 2026-11-17: "Please correct any dates that are old or stale for readout window".

Input: odin_cowork_dropbox/2026-11-17_stale_readout_windows.json. 29 readout rows whose window had passed with
no checked outcome, whose "Sponsor release" link pointed at another trial, or whose company guidance predated
October. Each was researched against the company's newest release / SEC filing / ClinicalTrials.gov record and
the changing items were re-opened by an independent red-team pass. Only rt_verdict CONFIRMED / FIX items with a
changing action are applied; DROP items touch nothing and are listed in the dropbox note.

Actions:
  re_guide / re_source -> st Guided, window and label in the company's own words, newest source and quote;
                          date_history entry when the date moves; any old resolution and ack removed.
  release              -> _d.resolution sponsor_release pointed at the right release (date, url, headline).
  no_topline           -> _d.resolution no_topline, dated, with what was read.
  stopped              -> _d.resolution company_stopped (date, url, quote): served "Stopped per company {date}".
  remove               -> the row leaves the dataset (no company basis); its ack goes with it.
  confirm_release / still_current -> a dated `reviewed` note; nothing a reader sees changes.
Every resolution written here carries reviewed=<date>, which resolve_past_readouts.py keeps (a human-checked
outcome is never re-matched by headline). Idempotent. Facts only, not investment advice. RULE 1: dates are the
companies' own calendar dates; "today" is the Eastern date.

    python apply_1117_stale_readouts.py [--dry-run]
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
from site_dates import eastern_today  # noqa: E402

DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
SPEC = os.path.join(HERE, "odin_cowork_dropbox", "2026-11-17_stale_readout_windows.json")
ACK = os.path.join(HERE, "_readout_watch_ack.json")
CHECKED = "2026-11-17"
TODAY = eastern_today().isoformat()
CHANGING = {"re_guide", "re_source", "release", "no_topline", "stopped", "remove"}


def short(s, n):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "…"


def window(it):
    we, p = it["window_end"], it["precision"]
    y = we[:4]
    if p == "month":
        return we, "month", we[:7], "month", we[:7]
    if p == "quarter":
        return we, "quarter", we[:7], "quarter", f"{y}-Q{(int(we[5:7]) - 1) // 3 + 1}"
    return we, "year", None, "year", y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    spec = json.load(io.open(SPEC, encoding="utf-8"))
    src = io.open(DATASET, encoding="utf-8").read()
    i, j = src.index("["), src.rindex("]") + 1
    rows = json.loads(src[i:j])
    by = {r.get("id"): r for r in rows}
    acks = json.load(io.open(ACK, encoding="utf-8"))
    drop_ack, remove, n = set(), set(), {}
    for it in spec["items"]:
        verdict = it.get("rt_verdict")
        act = it["action"]
        if act in CHANGING and verdict not in ("CONFIRMED", "FIX"):
            n["held"] = n.get("held", 0) + 1
            continue
        it = dict(it, **(it.get("rt_fix") or {}))
        r = by.get(it["id"])
        if r is None:
            n["missing"] = n.get("missing", 0) + 1
            continue
        dd = r.setdefault("_d", {})
        if act in ("re_guide", "re_source"):
            d, dp, dm, gp, gw = window(it)
            old = str(r.get("d") or "")[:10]
            if old != d:
                hist = dd.get("date_history") or []
                if not hist:
                    hist.append({"date": old, "note": "date the row showed before this check"})
                hist.append({"date": d, "changed": CHECKED, "why": short(it["why"], 300)})
                dd["date_history"] = hist
            r.update({"d": d, "dp": dp, "st": "Guided", "url": it["source_url"]})
            if dm:
                r["dm"] = dm
            else:
                r.pop("dm", None)
            if it.get("name"):
                r["name"] = it["name"]
            dd.update({"guided_precision": gp, "guided_window": gw, "guided_label": short(it["label"], 60),
                       "guided_form": it.get("source_type"), "guided_filed": it["source_date"],
                       "guidance_text": short(it["quote"], 600), "source_url": it["source_url"],
                       "source": ("company guidance (SEC filing)" if "sec.gov" in it["source_url"]
                                  else "company guidance (company release)"),
                       "red_team": f"{CHECKED}: stale-window check; source re-opened by an independent red-team "
                                   f"pass. {short(it.get('rt_reason'), 300)}"})
            dd.pop("resolution", None)
            drop_ack.add(r["id"])
        elif act == "release":
            dd["resolution"] = {"state": "sponsor_release", "date": it["date"], "headline": short(it["headline"], 200),
                                "url": it["url"], "checked": CHECKED, "reviewed": CHECKED,
                                "basis": "company release for this trial, checked by hand: " + short(it["why"], 240)}
        elif act == "no_topline":
            dd["resolution"] = {"state": "no_topline", "checked": CHECKED, "reviewed": CHECKED,
                                "searched": short(it["searched"], 300), "basis": short(it["why"], 240)}
        elif act == "stopped":
            dd["resolution"] = {"state": "company_stopped", "date": it["date"], "url": it["url"],
                                "quote": short(it["quote"], 300), "checked": CHECKED, "reviewed": CHECKED}
            if it.get("name"):
                r["name"] = it["name"]
        elif act == "remove":
            remove.add(r["id"])
            drop_ack.add(r["id"])
        elif act in ("confirm_release", "still_current"):
            res = dd.get("resolution")
            if act == "confirm_release" and isinstance(res, dict):
                res["reviewed"] = CHECKED
            dd["guidance_checked"] = {"date": CHECKED, "note": short(it["why"], 240)}
        n[act] = n.get(act, 0) + 1
    rows = [r for r in rows if r.get("id") not in remove]
    acks["acks"] = [x for x in acks.get("acks", []) if x.get("id") not in drop_ack]
    print("applied:", n, "| removed", sorted(remove), "| acks dropped", sorted(drop_ack))
    if a.dry_run:
        return
    out = src[:i] + json.dumps(rows, ensure_ascii=False, indent=1) + src[j:]
    io.open(DATASET, "w", encoding="utf-8", newline="").write(out)
    io.open(ACK, "w", encoding="utf-8", newline="").write(json.dumps(acks, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main()
