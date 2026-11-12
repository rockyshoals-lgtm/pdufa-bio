import io, json, os, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = json.load(io.open("_fda_approvals_months.json", encoding="utf-8"))
have = set(os.listdir("pdufa_site_src/drug"))
slug = lambda s: re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")
new = {}
for k, v in c.items():
    for x in v["items"]:
        if x["kind"] == "new application":
            new.setdefault(x["app"], x)
miss = [x for x in new.values() if slug(x["generic"].split(",")[0]) not in have and slug(x["brand"]) not in have]
nme = [x for x in miss if "Type 1" in x.get("class", "")]
print(f"2025-2026 new-application approvals (openFDA): {len(new)}; without a /drug/ page: {len(miss)}; of those Type 1 NMEs: {len(nme)}")
