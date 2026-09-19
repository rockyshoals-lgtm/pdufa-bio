# -*- coding: utf-8 -*-
"""BAYRY sevabertinib: is the 2026-09-09 SUPPL-1 our 2026-11-30 row, or a different action?

The CI feed watcher flagged NDA219972 SUPPL-1 approved 2026-09-09 against our 2026-11-30
sevabertinib row. A SUPPL-1 is a supplement to an application that ALREADY EXISTS, so the base
NDA must have been approved earlier -- which means our November row is probably a second
indication and the September action is not an early decision on it. That is a guess until the
submission history says so, and Bayer is not an SEC registrant, so openFDA is the only primary
source available. Print every submission on the application.
"""
import io
import json
import urllib.parse
import urllib.request

UA = "pdufa.bio builder rockyshoals@gmail.com"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))


o = io.open("_verify_bayry_seva.txt", "w", encoding="utf-8")

for q in ['openfda.generic_name:"sevabertinib"', 'application_number:"NDA219972"']:
    url = ("https://api.fda.gov/drug/drugsfda.json?search="
           + urllib.parse.quote(q, safe=':+"') + "&limit=5")
    o.write(f"\n=== {q}\n  {url}\n")
    try:
        d = get(url)
    except Exception as e:  # noqa: BLE001
        o.write(f"  ERROR {e}\n")
        continue
    for r in d.get("results", []):
        o.write(f"  app={r.get('application_number')}  sponsor={r.get('sponsor_name')}\n")
        for p in r.get("products", []):
            o.write(f"    product: {p.get('brand_name')} / {p.get('active_ingredients')}\n")
        for s in sorted(r.get("submissions", []),
                        key=lambda s: str(s.get("submission_status_date") or "")):
            o.write(f"    {s.get('submission_type')}-{s.get('submission_number')} "
                    f"status={s.get('submission_status')} "
                    f"date={s.get('submission_status_date')} "
                    f"class={s.get('submission_class_code')} "
                    f"({s.get('submission_class_code_description')})\n")
            for d2 in s.get("application_docs", [])[:2]:
                o.write(f"        doc {d2.get('type')} {d2.get('date')} {d2.get('url')}\n")
o.close()
print("done")
