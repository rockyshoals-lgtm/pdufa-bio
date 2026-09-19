# -*- coding: utf-8 -*-
import io, json, os, re, sys, importlib.util
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
spec = importlib.util.spec_from_file_location("b", "build_pdufa_event_pages.py")
b = importlib.util.module_from_spec(spec); sys.argv = ["x"]; spec.loader.exec_module(b)
src = io.open("pdufa_site_src/api/v1/dataset.mjs", encoding="utf-8", errors="replace").read().replace("\x00", "")
rows, _ = json.JSONDecoder().raw_decode(src[src.find("["):])
for r in rows:
    if r["id"] in ("pdufa_cogt_2026-11-30", "pdufa_prax_2027-01-29", "pdufa_gild_2027-02-02", "pdufa_rhhby_2026-10-15"):
        drug = b.clean_name(r.get("name"))
        slug = f"{r['t']}-{b.slugify(drug.split('(')[0].strip())}" if drug else None
        print(r["id"], "| clean_name ->", repr(drug), "| slug", slug, "| exists", slug and os.path.isdir(f"pdufa_site_src/pdufa/{slug}"))
        tk = r["t"].lower()
        print("   existing for ticker:", [n for n in os.listdir("pdufa_site_src/pdufa") if n.lower().startswith(tk + "-") or n.lower() == tk])
