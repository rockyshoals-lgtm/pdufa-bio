"""publish_to_dropbox.py — final step of READOUT_RESEARCH.bat (added 2026-08-29).

Copies the pipeline's outputs to ONE STABLE PATH the pdufa.bio builder always reads:

    odin_cowork_dropbox\\latest\\

Why: the dated `data_2026-08-29/` drops went stale the moment the chain re-ran, and keeping
them fresh required a human (me) to remember to copy files. A feed the builder can trust has
to refresh itself. This runs at the end of every chain run, copies whatever exists, and
writes `manifest.json` (run stamp, per-file row counts, gold/conflict/drift summary) so the
builder can tell at a glance whether the data is fresh and whether anything needs review.

Never fails the chain: every copy is best-effort, a locked file is skipped with a note.
"""
import csv, io, json, os, shutil, sys, datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
DST = os.path.join(HERE, "odin_cowork_dropbox", "latest")
os.makedirs(DST, exist_ok=True)

FILES = ["readout_gold_dates.csv", "readout_calendar.csv", "readout_forward.csv",
         "ctgov_readouts.csv", "conference_presenters.csv", "readout_date_drift.csv",
         "conf_registry.json"]

man = {"published_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
       "note": "written by publish_to_dropbox.py as the final step of READOUT_RESEARCH.bat; "
               "timestamps are LOCAL PACIFIC (machine time). Read README_LATEST.md first.",
       "files": {}}

for f in FILES:
    src = os.path.join(HERE, f)
    if not os.path.exists(src):
        man["files"][f] = {"status": "missing this run"}
        continue
    try:
        shutil.copy2(src, os.path.join(DST, f))
    except Exception as e:
        man["files"][f] = {"status": f"copy failed: {e}"}
        continue
    info = {"status": "ok",
            "modified": datetime.datetime.fromtimestamp(
                os.path.getmtime(src)).isoformat(timespec="seconds")}
    if f.endswith(".csv"):
        try:
            rows = list(csv.DictReader(io.open(src, encoding="utf-8-sig",
                                               errors="replace", newline="")))
            info["rows"] = len(rows)
            if f == "readout_gold_dates.csv":
                conf = {}
                for r in rows:
                    conf[r.get("confidence", "?")] = conf.get(r.get("confidence", "?"), 0) + 1
                info["confidence"] = conf
                info["conflicts_for_review"] = sum(1 for r in rows if (r.get("conflict") or "").strip())
            if f == "readout_date_drift.csv":
                info["pulled_earlier"] = sum(1 for r in rows if r.get("moved") == "EARLIER")
        except Exception:
            pass
    man["files"][f] = info

# STALENESS CHECK (2026-08-29): a crashed forward scan can hide behind the smart-money
# enricher, which rewrites readout_forward.csv and refreshes its mtime (this exact sequence
# happened on the 13:50 run — deep pass died silently at 60/120, chain shipped stale rows).
# readout_scan.py only writes readout_forward.ok on a COMPLETED scan; if that stamp is
# meaningfully older than the csv's mtime, the csv was rewritten by something that is NOT
# the scanner and the scan itself likely died. Flag it where the builder will see it.
try:
    _ok = io.open(os.path.join(HERE, "readout_forward.ok"), encoding="utf-8").read().strip()
    _ok_t = datetime.datetime.fromisoformat(_ok.split()[0])
    _csv_t = datetime.datetime.fromtimestamp(
        os.path.getmtime(os.path.join(HERE, "readout_forward.csv"))).astimezone()
    lag_min = (_csv_t - _ok_t).total_seconds() / 60
    fwd = man["files"].get("readout_forward.csv", {})
    fwd["scan_completed_at"] = _ok
    if lag_min > 30:
        fwd["WARNING"] = (f"csv rewritten {lag_min:.0f} min AFTER the last completed scan — "
                          "the forward scan likely DIED this run; rows may be stale")
        print(f"[publish] !! {fwd['WARNING']}")
except FileNotFoundError:
    man["files"].setdefault("readout_forward.csv", {})["WARNING"] = \
        "no readout_forward.ok stamp — cannot verify the scan completed"
except Exception:
    pass

json.dump(man, io.open(os.path.join(DST, "manifest.json"), "w", encoding="utf-8"), indent=1)
ok = sum(1 for v in man["files"].values() if v.get("status") == "ok")
print(f"[publish] {ok}/{len(FILES)} files -> odin_cowork_dropbox\\latest\\  "
      f"(manifest.json has row counts + conflict/drift summary)")
