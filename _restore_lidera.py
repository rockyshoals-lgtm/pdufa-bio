import io, json
P = "pdufa_site_src/api/v1/dataset.mjs"
s = io.open(P, encoding="utf-8").read(); i, j = s.index("["), s.rindex("]") + 1
rows = json.loads(s[i:j])
for r in rows:
    if r["id"] == "pdufa_rhhby_2026-11-30":
        r["st"] = "Upcoming"; r.pop("oc", None); r.pop("dcd", None)
        print("restored lidERA:", r["st"], r.get("url"))
io.open(P, "w", encoding="utf-8").write(s[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + s[j:])
