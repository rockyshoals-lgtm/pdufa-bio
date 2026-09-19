# -*- coding: utf-8 -*-
import io, json, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
for page in sys.argv[1:] or ["readouts", "calendar", "adcomm"]:
    t = io.open(f"pdufa_site_src/{page}/index.html", encoding="utf-8").read()
    ok = bad = 0
    for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', t, re.S):
        try:
            json.loads(b); ok += 1
        except Exception as e:
            bad += 1; print(f"/{page}: BAD json-ld: {e}; {b[:160]!r}")
    print(f"/{page}: json-ld blocks ok={ok} bad={bad}")
