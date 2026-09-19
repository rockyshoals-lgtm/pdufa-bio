# -*- coding: utf-8 -*-
import io, re, sys
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
for page in ("readouts", "calendar", "adcomm"):
    t = io.open(f"pdufa_site_src/{page}/index.html", encoding="utf-8").read()
    evs = re.findall(r'\{"@type":"Event"(?:[^{}]|\{[^{}]*\})*\}', t)
    c = Counter()
    for e in evs:
        m = re.search(r'"startDate":"([^"]*)"', e)
        sd = m.group(1) if m else "none"
        c["month-only" if re.match(r"^\d{4}-\d{2}$", sd) else (sd[8:10] if len(sd) >= 10 else sd)] += 1
    print(f"/{page}: {len(evs)} Events; startDate day-of-month census: {c.most_common(10)}")
    wp = len(re.findall(r'\{"@type":"WebPage","name"', t))
    print(f"   WebPage (demoted) items: {wp}")
