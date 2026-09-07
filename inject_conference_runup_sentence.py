# -*- coding: utf-8 -*-
"""The overall conference run-up finding, as one sourced sentence, on every conference page.

Red team 2026-09-06d, Layer 1: conference pages earn impressions and convert at zero
because they have dates and no sentences. The finding underneath the whole conference
stack -- across 1,425 presentations the median presenter is flat before the meeting and
down after -- is original, countable, and shaped like the sentences AI answer boxes lift.
It goes on every /conference/{code} page (above the per-meeting CRUN block, which stays)
and into the /conferences hub lede. Numbers come from conference_runup_facts.load() at
build time, never typed. Marker-bounded (CRUNALL / CONFLEDE), idempotent.

Vocabulary: measurement only. The anchor caveat and "not a forecast" travel in the block.
"""
import glob
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
import conference_runup_facts as crf  # noqa: E402

B, E = "<!--CRUNALL:BEGIN-->", "<!--CRUNALL:END-->"
LB, LE = "<!--CONFLEDE:BEGIN-->", "<!--CONFLEDE:END-->"


def main():
    f = crf.load()
    sentence = crf.block_sentence(f)
    block = (f'{B}<div style="background:#0c1d38;border:1px solid #1e3a63;border-radius:12px;'
             f'padding:13px 15px;margin:12px 0"><b style="color:#e3ba5e">What presenting '
             f'companies\' shares did, across the whole study</b>'
             f'<div style="color:#9db3d4;font-size:13.5px;margin-top:6px;line-height:1.65">'
             f'{sentence} <a class="lit" href="/research/conference-runup">Full study, with the '
             f'method and its limits</a>.</div></div>{E}')
    n = 0
    for p in sorted(glob.glob(os.path.join(SITE, "conference", "*", "index.html"))):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        if B in doc:
            new = doc.split(B, 1)[0] + block + doc.split(E, 1)[1]
        else:
            anchor = "<!--CRUN:BEGIN-->" if "<!--CRUN:BEGIN-->" in doc else (
                "<!--FRESH:END-->" if "<!--FRESH:END-->" in doc else None)
            if not anchor:
                continue
            new = (doc.replace(anchor, block + anchor, 1) if anchor.startswith("<!--CRUN")
                   else doc.replace(anchor, anchor + block, 1))
        if new != doc:
            io.open(p, "w", encoding="utf-8").write(new)
            n += 1

    # /conferences hub lede: one sentence after the presenter-discipline paragraph.
    o = f["overall"]
    lede = (f'{LB}<p style="max-width:74ch">The FDA does not run these meetings, and the study '
            f'behind this site finds no reliable pre-conference run-up: across {f["n"]:,} '
            f'presentations the median presenter moved {crf._fmt(o["runup_30d"]["median"])} in '
            f'the 30 trading days before the meeting and {crf._fmt(o["post_5d"]["median"])} in '
            f'the 5 days after. Every date below comes from the organiser; every presenter '
            f'below links the filing or release that named the meeting. '
            f'<a class="lit" href="/research/conference-runup">The study</a>.</p>{LE}')
    hp = os.path.join(SITE, "conferences", "index.html")
    if os.path.isfile(hp):
        doc = io.open(hp, encoding="utf-8", errors="replace").read()
        if LB in doc:
            new = doc.split(LB, 1)[0] + lede + doc.split(LE, 1)[1]
        else:
            anchor = "<!--PRESDISC-->"
            new = doc.replace(anchor, lede + anchor, 1) if anchor in doc else doc
        if new != doc:
            io.open(hp, "w", encoding="utf-8").write(new)
            n += 1
    print(f"conference run-up sentence: {n} page(s) updated (n={f['n']:,}, "
          f"30d median {o['runup_30d']['median']}, post-5d {o['post_5d']['median']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
