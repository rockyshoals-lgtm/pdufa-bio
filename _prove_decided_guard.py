# -*- coding: utf-8 -*-
"""Prove tests/test_decided_rows_marked_on_calendar.py: clean 0 -> plant the 09-19 TLX shape
(Awaiting badge on a decided row) -> guard 1 -> mark_calendar_decided heals -> guard 0."""
import io, os, re, shutil, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
P = "pdufa_site_src/calendar/2026/september/index.html"; B = P + ".provebak"
G = ["tests/test_decided_rows_marked_on_calendar.py"]
def guard():
    r = subprocess.run([sys.executable, "-X", "utf8"] + G, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout.strip().splitlines()[-1][:150]
BADGE = ('<span class="awaiting" style="color:#e3ba5e;font-weight:700" '
         'title="The PDUFA goal date has passed and no decision has been announced">Awaiting</span>')
print("clean   :", guard())
shutil.copy2(P, B)
try:
    t = io.open(P, encoding="utf-8").read()
    t2, n = re.subn(r'<a class="row" data-dec="1" href="/fda-decision/TLX-2026-09-14">\s*<div class="t">TLX &middot; 2026-09-11 <span[^>]*>✓</span></div>'
                    r'<div class="d"><span[^>]*>Approved</span>: ',
                    f'<a class="row" href="/pdufa/TLX"><div class="t">TLX · 2026-09-11 {BADGE}</div><div class="d">', t)
    assert n == 1, f"plant failed ({n})"
    io.open(P, "w", encoding="utf-8").write(t2)
    print("planted :", guard())
    subprocess.run([sys.executable, "-X", "utf8", "mark_calendar_decided.py"], capture_output=True)
    print("healed  :", guard())
    healed = io.open(P, encoding="utf-8").read()
    print("row after heal:", re.search(r'<a class="row"[^>]*>\s*<div class="t">TLX[^<]*<span[^>]*>[^<]*</span></div>', healed).group(0)[:140])
finally:
    shutil.copy2(B, P); os.remove(B)
print("restored:", guard())
