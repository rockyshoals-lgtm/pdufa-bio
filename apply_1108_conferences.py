# -*- coding: utf-8 -*-
"""apply_1108_conferences.py -- re-verify conferences.json (the guard blocked every run from Nov 7: stamp 63 days old).

2026-11-08: every upcoming row (ACAAI ... ADA 2027) re-checked against the organiser's own site; all dates and cities
stand (ESMO Asia, ESMO IO, ASCO GI/GU confirmed through the organisers' pages as indexed, their live pages being
JavaScript-rendered). J.P. Morgan has now published JPM 2027: "The 45th Annual Healthcare Conference will take place
on January 11-14, 2027 in San Francisco, California" (jpmorgan.com) -- moved from _unannounced to the feed.
ESMO Congress 2027 is not added: its organiser page could not be read directly.
"""
import io, json
P = "conferences.json"
d = json.load(io.open(P, encoding="utf-8"))
d["_verified_on"] = "2026-11-08"
d["_unannounced"] = [u for u in d.get("_unannounced", []) if u.get("code") != "JPM"]
if not any(c["code"] == "JPM" and c["start"].startswith("2027") for c in d["conferences"]):
    d["conferences"].append({"code": "JPM", "name": "J.P. Morgan Healthcare Conference", "start": "2027-01-11",
                             "end": "2027-01-14", "city": "San Francisco, US", "focus": "Healthcare investing (company presentations)",
                             "source": "https://www.jpmorgan.com/about-us/events-conferences/health-care-conference"})
    d["conferences"].sort(key=lambda c: c["start"])
io.open(P, "w", encoding="utf-8").write(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
print("conferences.json verified 2026-11-08; JPM 2027 added")
