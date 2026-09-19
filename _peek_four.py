# -*- coding: utf-8 -*-
import io, json, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
src = io.open("pdufa_site_src/api/v1/dataset.mjs", encoding="utf-8", errors="replace").read().replace("\x00", "")
rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
for r in rows:
    if r["id"] in ("pdufa_mirm_2026-09-26", "pdufa_nvcr_2026-11-15", "pdufa_axsm_2027-05-01", "pdufa_bbio_2027-05-08"):
        print(r["id"], "|", r["name"], "|", r["d"], r["dp"])
for s in ("MIRM-zilurgisertib", "NVCR-ttfields-therapy", "AXSM-axs-12", "BBIO-encaleret", "AXSM", "BBIO", "NVCR", "MIRM"):
    t = io.open(f"pdufa_site_src/pdufa/{s}/index.html", encoding="utf-8").read()
    ti = re.search(r"<title>(.*?)</title>", t, re.S)
    kv = re.search(r"<span>FDA (?:PDUFA target date|decision|goal date)</span><b>([^<]+)</b>", t)
    print(f"  /pdufa/{s:<24} {ti.group(1)[:70] if ti else '?'} | kv={kv.group(1) if kv else '?'}")
