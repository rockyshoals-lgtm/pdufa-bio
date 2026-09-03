# -*- coding: utf-8 -*-
"""A company-Guided readout may not sit past its date with no outcome.

Audit 2026-09-02e: TENX's Phase 3 topline landed Aug 10 and MPLT's Phase 2 on Jul 27;
both rows still said Guided/pending weeks later -- the same failure class as REGN's
early approval, on the half of the calendar the PDUFA watcher does not cover. A Guided
date is a company's own statement: when it passes, either the outcome is recorded or a
human writes down why not (in _readout_watch_ack.json, which shrinks, never silently
grows). Estimated rows are OUR guesses and are a different problem -- not this guard's.

Grace period 10 days past the guided date (month/quarter precision means "by the end
of"; companies report within days of a topline, not weeks).
"""
import datetime as dt
import io
import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")
ACK = os.path.join(HERE, "_readout_watch_ack.json")
GRACE_DAYS = 10


def test_guided_readouts_resolve_or_ack():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8",
                  errors="replace").read().replace("\x00", "")
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    acks = set()
    if os.path.exists(ACK):
        acks = {(a["id"]) for a in
                json.load(io.open(ACK, encoding="utf-8")).get("acks", [])}
    cutoff = (dt.date.today() - dt.timedelta(days=GRACE_DAYS)).isoformat()
    bad = []
    for r in rows:
        if r.get("type") != "Readout" or str(r.get("st", "")) != "Guided":
            continue
        d = str(r.get("d") or "")[:10]
        if d and d < cutoff and r.get("id") not in acks:
            bad.append(f"{r.get('id')} ({r.get('t')} {str(r.get('name'))[:40]}, "
                       f"guided {d})")
    assert not bad, (
        "company-Guided readouts sit past their date with no outcome -- the TENX/MPLT "
        "failure class. Verify each against the company's release, record the outcome "
        "(st=Reported + source), or ack with a reason in _readout_watch_ack.json:\n  "
        + "\n  ".join(bad))


if __name__ == "__main__":
    test_guided_readouts_resolve_or_ack()
    print("OK")
