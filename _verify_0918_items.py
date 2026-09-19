# -*- coding: utf-8 -*-
import io, json, re, sys, urllib.parse, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "pdufa.bio builder rockyshoals@gmail.com"}


def get(u, t=45):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t).read().decode("utf-8", "replace")


def text(u):
    return re.sub(r"\s+", " ", re.sub(r"&#?\w+;", " ", re.sub(r"<[^>]+>", " ", get(u))))


print("== 1. openFDA NDA218881 (INLURIYO) full submission history ==")
j = json.loads(get("https://api.fda.gov/drug/drugsfda.json?search=application_number:%22NDA218881%22&limit=1"))
for r in j.get("results", []):
    of = r.get("openfda") or {}
    print("   brand:", of.get("brand_name"), "| generic:", of.get("generic_name"), "| sponsor:", r.get("sponsor_name"))
    for s in sorted(r.get("submissions") or [], key=lambda s: str(s.get("submission_status_date"))):
        print("   ", s.get("submission_type"), s.get("submission_number"), s.get("submission_status"),
              s.get("submission_status_date"), "|", (s.get("submission_class_code_description") or "")[:60])

print("\n== 2. our /drug/inluriyo page: what does it currently say ==")
d = io.open("pdufa_site_src/drug/inluriyo/index.html", encoding="utf-8", errors="replace").read()
ti = re.search(r"<title>(.*?)</title>", d, re.S)
print("   title:", ti.group(1) if ti else "?")
for m in list(re.finditer(r"approv", d, re.I))[:6]:
    print("   ...", re.sub(r"<[^>]+>", " ", d[max(0, m.start() - 170): m.start() + 170]).strip()[:300])
print("   mentions abemaciclib:", "abemaciclib" in d.lower(), "| combination:", "combination" in d.lower())

print("\n== 3. FDA oncology announcement 2026-09-18 ==")
try:
    t = text("https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-imlunestrant-combination-abemaciclib-er-positive-her2-negative-esr1-mutated-advanced")
    i = t.lower().find("imlunestrant")
    print("   ", t[max(0, i - 100): i + 900])
except Exception as e:
    print("   fetch failed:", e)
