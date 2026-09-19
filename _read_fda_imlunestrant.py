# -*- coding: utf-8 -*-
import re, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "pdufa.bio builder rockyshoals@gmail.com"}
U = ("https://www.fda.gov/drugs/resources-information-approved-drugs/"
     "fda-approves-imlunestrant-combination-abemaciclib-er-positive-her2-negative-esr1-mutated-advanced-or")
t = urllib.request.urlopen(urllib.request.Request(U, headers=UA), timeout=60).read().decode("utf-8", "replace")
body = re.sub(r"\s+", " ", re.sub(r"&#?\w+;", " ", re.sub(r"<[^>]+>", " ", t)))
i = body.find("On September")
if i < 0:
    i = body.lower().find("approved imlunestrant")
print(body[max(0, i - 200): i + 1800])
print("\n-- date strings found --", sorted(set(re.findall(r"(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, 20\d{2}", body)))[:6])
print("-- trial names --", sorted(set(re.findall(r"EMBER-?\d", body)))[:5])
