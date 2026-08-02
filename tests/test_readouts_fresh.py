# -*- coding: utf-8 -*-
"""Guard: the /readouts UPCOMING sections must not contain a month/quarter/half whose window is already
in the past. build_readout_results.py prunes these daily; this locks it in so June/July can't linger.
The 'Recently reported' results block is exempt (it is intentionally about past readouts)."""
import os, re, sys
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "..", "pdufa_site_src", "readouts", "index.html")
TODAY = dt.date.today()
MON = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], 1)}


def is_past(label):
    s = label.replace("(est.)", "").strip()
    for pat, endm in ((r'^([A-Za-z]+)\s+(\d{4})$', None), (r'^Q([1-4])\s+(\d{4})$', 3), (r'^H([12])\s+(\d{4})$', 6)):
        m = re.match(pat, s)
        if not m:
            continue
        if endm is None:
            if m.group(1) not in MON:
                return False
            return (int(m.group(2)), MON[m.group(1)]) < (TODAY.year, TODAY.month)
        return (int(m.group(2)), int(m.group(1)) * endm) < (TODAY.year, TODAY.month)
    return False


h = open(PAGE, encoding="utf-8", errors="replace").read()
labels = [l for l in re.findall(r'<div class="mhead"[^>]*>([^<]+)</div>', h)
          if "Recently reported" not in l]
stale = [l.strip() for l in labels if is_past(l)]
if stale:
    print("FAIL -- /readouts still shows past window section(s):", stale)
    sys.exit(1)
print(f"OK -- /readouts upcoming sections are all current/future ({len(labels)} sections, 0 stale).")
