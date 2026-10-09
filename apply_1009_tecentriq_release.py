# -*- coding: utf-8 -*-
"""apply_1009_tecentriq_release.py -- correction to the 10-08 Tecentriq publish.

The 10-08 builder note said Genentech had posted no approval release. It had: gene.com's press-release
listing (read 2026-10-09 with the watcher UA) carries "FDA Approves Genentech's Tecentriq in Combination
With a Fluoropyrimidine and Oxaliplatin for The Adjuvant Treatment of a Certain Type of Stage III Colon
Cancer", dated 2026-10-08. Recorded as the row's announcement_url. The FDA notification remains the
decision source. Facts only; not investment advice.
"""
import io, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
URL = "https://www.gene.com/media/press-releases/15135/2026-10-08/fda-approves-genentechs-tecentriq-in-com"
s = io.open(P, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = s.index("["), s.rindex("]") + 1
rows = json.loads(s[i:j])
r = next(x for x in rows if x["id"] == "pdufa_rhhby_2026-10-09")
r["_d"]["announcement_url"] = URL
r["_d"]["announcement"] = "Genentech press release, October 8, 2026"
io.open(P, "w", encoding="utf-8").write(s[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + s[j:])
print("  pdufa_rhhby_2026-10-09: announcement_url = Genentech 2026-10-08 release")
