# -*- coding: utf-8 -*-
"""fda_week_actions.py -- every decision-class FDA approval in Drugs@FDA for a date range, calendar or not.

Audit 2026-10-14 (David: "we are being quoted by Bing AI as the top source for many things"). The weekly and
today pages listed only decisions on rows we had tracked; Drugs@FDA (openFDA) recorded four more decision-class
approvals in the same week that no row covered: Teva's WELTRUZA (olanzapine, NDA 219007, original, 10-08),
AstraZeneca's BREZTRI new formulation (NDA 220290, original, 10-08), Genentech's TECENTRIQ HYBREZA efficacy
supplement (BLA 761347 S-011, 10-08, the companion to the Tecentriq approval we did publish), Pfizer/Seagen's
TUKYSA efficacy supplement (NDA 213411 S-010, 10-07) and Amgen's REPATHA efficacy supplement (BLA 125522 S-047,
10-09). An answer to "what did the FDA approve this week" built from us was incomplete.

This module is the one owner of that lookup: original NDA/BLA approvals and EFFICACY supplements (new
indications) with a status date in the range, from the FDA's own record, each with its approval letter where
openFDA carries one. Labeling, REMS, CMC and ANDA actions are excluded on purpose: they are not decisions a
reader asking that question means. CBER products are not in Drugs@FDA and are not here; the pages say so.
Cached in _fda_week_actions.json so a page can render without the network. Facts only; dates are the FDA's.
"""
import io
import json
import os
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "_fda_week_actions.json")
UA = {"User-Agent": "pdufa.bio builder rockyshoals@gmail.com"}
API = "https://api.fda.gov/drug/drugsfda.json"


def _load():
    try:
        return json.load(io.open(CACHE, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def fetch(start_iso, end_iso):
    """Decision-class AP submissions with status date in [start, end], as a list of dicts; None on failure."""
    a, b = start_iso.replace("-", ""), end_iso.replace("-", "")
    q = f"submissions.submission_status_date:[{a}+TO+{b}]+AND+submissions.submission_status:AP"
    out, skip = [], 0
    while True:
        url = f"{API}?search={q}&limit=100&skip={skip}"
        try:
            j = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45).read())
        except Exception:  # noqa: BLE001
            return None if not out else out
        res = j.get("results", [])
        for r in res:
            app = str(r.get("application_number") or "")
            if not (app.startswith("NDA") or app.startswith("BLA")):
                continue
            prods = r.get("products") or []
            brand = (prods[0].get("brand_name") if prods else "") or ""
            ingr = ", ".join(x.get("name", "") for x in (prods[0].get("active_ingredients") if prods else []) or [])
            for s in r.get("submissions") or []:
                d = str(s.get("submission_status_date") or "")
                if s.get("submission_status") != "AP" or not (a <= d <= b):
                    continue
                cls = str(s.get("submission_class_code_description") or "")
                typ = str(s.get("submission_type") or "")
                if not (typ == "ORIG" or (typ == "SUPPL" and "Efficacy" in cls)):
                    continue
                letter = next((x.get("url") for x in s.get("application_docs") or [] if "ltr" in str(x.get("url", "")).lower()), "")
                out.append({"date": f"{d[:4]}-{d[4:6]}-{d[6:8]}", "sponsor": r.get("sponsor_name") or "",
                            "brand": brand, "ingredient": ingr, "app": app, "type": typ,
                            "number": str(s.get("submission_number") or ""), "class": cls,
                            "letter": letter or "",
                            "overview": f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo={app[3:]}"})
        total = j.get("meta", {}).get("results", {}).get("total", 0)
        skip += 100
        if skip >= total or not res:
            break
    return out


def actions(start_iso, end_iso, refresh=True):
    """Cached list for the range; refreshed from openFDA when the network allows, else the last cache."""
    cache = _load()
    key = f"{start_iso}..{end_iso}"
    if refresh:
        got = fetch(start_iso, end_iso)
        if got is not None:
            cache[key] = {"fetched": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "actions": got}
            # keep the file small: only the newest 8 ranges
            for k in sorted(cache)[:-8]:
                cache.pop(k, None)
            io.open(CACHE, "w", encoding="utf-8").write(json.dumps(cache, indent=1, ensure_ascii=False))
    return (cache.get(key) or {}).get("actions", []), (cache.get(key) or {}).get("fetched")


def not_on_calendar(acts, rows):
    """Actions whose application number no tracked decided row already carries, and whose brand no decided
    row within 10 days names; the rest are the decisions our own rows already publish."""
    apps, names = set(), []
    for r in rows:
        if r.get("type") != "PDUFA":
            continue
        rec = str((r.get("_d") or {}).get("fda_action_record") or "")
        m = __import__("re").search(r"(NDA|BLA)\s*(\d{6})", rec)
        if m:
            apps.add(m.group(1) + m.group(2))
        if str(r.get("st") or "").lower() == "decided":
            names.append((str(r.get("name") or "").lower(), str(r.get("dcd") or "")))
    out = []
    for x in acts:
        if x["app"] in apps:
            continue
        b = x["brand"].lower()
        if b and any(b.split()[0] in n and dcd and abs((__import__("datetime").date.fromisoformat(x["date"]) - __import__("datetime").date.fromisoformat(dcd)).days) <= 10
                     for n, dcd in names if dcd):
            continue
        out.append(x)
    return out
