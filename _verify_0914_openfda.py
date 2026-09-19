# -*- coding: utf-8 -*-
"""Pin the ACTUAL FDA action dates, and settle the two FDA-feed leads.

The sponsor press release and the FDA's action are not always the same day. Biofrontera's PR is
dated September 14 but the CI watcher saw an openFDA AP record on September 9 -- and `dcd` in
our dataset means the FDA's action date, not the announcement. So ask openFDA directly.

Also settles BAYRY sevabertinib, flagged by the feed watcher as AP 2026-09-09 SUPPL-1 against a
2026-11-30 goal. A SUPPL-1 means a supplement to an application that already exists, so this is
probably a different (earlier) approval than the November row, not an early decision on it.
Bayer is not an SEC registrant, so openFDA is the only primary source available here.
"""
import io
import json
import urllib.parse
import urllib.request

UA = "pdufa.bio builder rockyshoals@gmail.com"
BASE = "https://api.fda.gov/drug/drugsfda.json"

QUERIES = [
    ("BFRI Ameluz", 'openfda.brand_name:"AMELUZ"'),
    ("BFRI aminolevulinic", 'openfda.generic_name:"aminolevulinic+acid"'),
    ("SRRK apitegromab", 'openfda.generic_name:"apitegromab"'),
    ("BAYRY sevabertinib", 'openfda.generic_name:"sevabertinib"'),
    ("PHAR leniolisib", 'openfda.generic_name:"leniolisib"'),
]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))


o = io.open("_verify_0914_openfda.txt", "w", encoding="utf-8")
for label, q in QUERIES:
    url = f"{BASE}?search={urllib.parse.quote(q, safe=':+\"')}&limit=5"
    o.write(f"\n=== {label}\n  {url}\n")
    try:
        d = get(url)
    except Exception as e:  # noqa: BLE001
        o.write(f"  ERROR {e}\n")
        continue
    for r in d.get("results", [])[:5]:
        app = r.get("application_number")
        sponsor = r.get("sponsor_name")
        o.write(f"  {app}  {sponsor}\n")
        subs = sorted(r.get("submissions", []),
                      key=lambda s: str(s.get("submission_status_date") or ""),
                      reverse=True)
        for s in subs[:6]:
            if str(s.get("submission_status_date") or "") < "20260101":
                continue
            o.write(f"      {s.get('submission_type')}-{s.get('submission_number')} "
                    f"status={s.get('submission_status')} "
                    f"date={s.get('submission_status_date')} "
                    f"class={s.get('submission_class_code')} "
                    f"| {str(s.get('submission_class_code_description'))[:40]}\n")
o.close()
print("done")
