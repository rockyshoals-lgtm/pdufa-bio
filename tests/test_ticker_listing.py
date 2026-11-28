"""Guard (2026-11-28): a company whose listing changed keeps its original hub address, and the hub says so.

Karyopharm's Nov 17, 2026 release names it "Karyopharm Therapeutics Inc. (OTC Pink: KPTIQ)", while /ticker/KPTI kept
showing only KPTI. Each entry in ticker_listing.json must (1) cite an https company source, (2) have a permanent
/ticker/<current> -> /ticker/<key> redirect in pdufa_site_src/vercel.json, and (3) be stated on the hub the builder
renders. Renders one hub in memory; no network."""
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import build_ticker_hubs as B  # noqa: E402


def main():
    bad = []
    lst = B._listing()
    if "KPTI" not in lst or lst["KPTI"].get("current") != "KPTIQ":
        bad.append("ticker_listing.json must carry KPTI -> KPTIQ (Karyopharm release, Nov 17, 2026)")
    red = {(r.get("source"), r.get("destination"), r.get("permanent"))
           for r in json.load(open(os.path.join(HERE, "pdufa_site_src", "vercel.json"), encoding="utf-8"))["redirects"]}
    for tk, v in lst.items():
        if not str(v.get("source_url") or "").startswith("https://") or not v.get("source"):
            bad.append(f"{tk}: listing change needs the company's own source and https URL")
        if (f"/ticker/{v['current']}", f"/ticker/{tk}", True) not in red:
            bad.append(f"{tk}: /ticker/{v['current']} must redirect permanently to /ticker/{tk}")
        h = B.render(tk, {}, {}, {tk: "Test Co"}, {}, {}, {})
        if f'data-listing="{v["current"]}"' not in h or f"{v['current']}" not in h.split('name="description"')[1][:200]:
            bad.append(f"{tk}: hub must state the current listing {v['current']} in its text and description")
    # 2026-11-28 (live check): /ticker/SLGL said "no upcoming catalyst on file" above its own Nov 30 topline row.
    ro = {"ZZZQ": [dict(date="2099-11-30", drug="Test Phase 3 top-line", outcome=None, url="/readouts", precision="day",
                        label=None, status="Guided", resolution=None, res_date="", res_url=None, reg_status="",
                        drug_page=None)]}
    h = B.render("ZZZQ", {}, {}, {"ZZZQ": "Test Co"}, {}, ro, {})
    sub = h.split('<div class="sub">', 1)[1].split("</div>", 1)[0]
    if "no upcoming catalyst" in sub or "1 upcoming readout" not in sub:
        bad.append(f"a hub with a readout ahead must not say it has no upcoming catalyst: {sub}")

    if bad:
        print("FAIL -- a changed listing is not shown or not reachable:")
        for b in bad:
            print("  " + b)
        sys.exit(1)
    print(f"OK -- {len(lst)} changed listing(s) shown on their hubs, sourced, and redirected.")


if __name__ == "__main__":
    main()
