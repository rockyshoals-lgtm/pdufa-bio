# -*- coding: utf-8 -*-
"""Confirm the 09-14 audit's four P0s against LIVE, from a non-browser client.

House rule: a supplied claim is a lead until I read it myself. The auditor says every finding
was re-confirmed from a non-browser client; this is my own independent read of the same four,
plus the exact strings I will need to fix them.
"""
import hashlib
import io
import json
import re
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = "https://www.pdufa.bio"
UA = "pdufa.bio builder rockyshoals@gmail.com"


def get(path):
    req = urllib.request.Request(BASE + path, headers={
        "User-Agent": UA, "Cache-Control": "no-cache", "Pragma": "no-cache"})
    r = urllib.request.urlopen(req, timeout=60)
    b = r.read()
    return b.decode("utf-8", "replace"), hashlib.md5(b).hexdigest()[:12]


def text(h):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))


out = io.open("_verify_audit_0914.txt", "w", encoding="utf-8")


def w(s=""):
    print(s)
    out.write(s + "\n")


bi, _ = get("/build-info.json")
w(f"build-info: {bi[:400]}")

w("\n" + "=" * 78)
w("P0-A  the timing statistic on three surfaces")
for path, pat in [
    ("/research/fda-decision-timing",
     r"Of the (\d+)[^.]{0,200}?(\d+) came\s*<?/?b?>?\s*before[^.]{0,80}?(\d+) landed on it,? and (\d+) came after"),
    ("/calendar", r"Of the (\d+) FDA decisions in 2026[^.]{0,220}"),
    ("/learn/what-is-a-pdufa-date", r"(\d+) sourced 2026 decisions[^.]{0,200}"),
]:
    h, md5 = get(path)
    t = text(h)
    m = re.search(pat, t, re.I)
    w(f"\n  {path}  md5={md5}")
    w(f"    {m.group(0)[:260] if m else '(pattern not found)'}")
    for n in re.findall(r"(\d+)\s+came\s+before|median[^.]{0,60}", t, re.I)[:3]:
        pass
    mm = re.search(r"median[^.]{0,90}", t, re.I)
    if mm:
        w(f"    median: {mm.group(0)[:110]}")

w("\n" + "=" * 78)
w("P0-B  twelve event pages that should no longer carry a day")
SLUGS = ["ABBV-tavapadon", "NVO-am833", "AZN-ultomiris", "BAYRY-kerendia", "ABBV-rinvoq",
         "RHHBY-lunsumio-polivy", "RHHBY-gazyva", "NVS", "LLY",
         "PFE-tukysa-trastuzumab-and", "AZN-gefurulimab", "GILD-trodelvy"]
for s in SLUGS:
    try:
        h, md5 = get(f"/pdufa/{s}")
    except Exception as e:  # noqa: BLE001
        w(f"  {s:<32} FETCH {e}")
        continue
    ti = re.search(r"<title>(.*?)</title>", h, re.S)
    n_day = len(re.findall(r"Dec 31,? 2026|2026-12-31", h))
    n_q = len(re.findall(r"Q4 2026", h))
    w(f"  /pdufa/{s:<30} day={n_day:<3} q4={n_q:<3} | {(ti.group(1) if ti else '')[:78]}")

w("\n" + "=" * 78)
w("P0-C  BAYRY earliness against a withdrawn goal date")
for p in ["/fda-decision/BAYRY-2026-09-09", "/pdufa/BAYRY-sevabertinib"]:
    try:
        h, md5 = get(p)
    except Exception as e:  # noqa: BLE001
        w(f"  {p}: FETCH {e}")
        continue
    ti = re.search(r"<title>(.*?)</title>", h, re.S)
    t = text(h)
    w(f"\n  {p}  md5={md5}")
    w(f"    title : {(ti.group(1) if ti else '')[:120]}")
    for pat in [r"\d+ [Dd]ays? [Ee]arly", r"\d+ days before its [^.]{0,60}",
                r"goal date[^.]{0,60}", r"November 2026 PDUFA"]:
        m = re.search(pat, t)
        if m:
            w(f"    {pat[:26]:<28} -> {m.group(0)[:100]}")

w("\n" + "=" * 78)
w("P0-D  build-info next pointer")
try:
    j = json.loads(bi)
    for k in ("next_ticker", "next_date", "next_days", "built"):
        w(f"  {k}: {j.get(k)}")
except Exception as e:  # noqa: BLE001
    w(f"  parse error {e}")

out.close()
