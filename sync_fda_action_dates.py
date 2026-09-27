# -*- coding: utf-8 -*-
"""sync_fda_action_dates.py -- every decided approval's ACTION date from the FDA's own record.

Audit 2026-09-26 (items 3, 4, 5). The timing statistic compared goal dates against whatever
date the decision was published under -- usually the sponsor's press release. Three rows show
why that is not good enough:

  MRK WINREVAIR   published +1 day (Merck's release, 6:45 am ET on Sep 22). Drugs@FDA:
                  BLA 761363 S-012 approved 2026-09-21, letter signed 09/21/2026 04:46 PM.
                  An on-the-day decision counted as late.
  TLX Pixclara    excluded ("the filing does not state the day the FDA acted"). Drugs@FDA:
                  NDA 218592 approved 2026-09-11, the goal day; letter posted Sep 15, five days
                  BEFORE the exclusion was written, and nothing re-checked the row.
  LNTH TAUKLARIFY published +0 and right -- but its only cited source was an Aug 14 release
                  on an aggregator that never states Aug 13. Drugs@FDA NDA 220496: 2026-08-13.

openFDA's Drugs@FDA endpoint returns submission_status_date and the approval-letter URL for
every CDER approval, supplements included. This script is the one owner of that lookup:

  * for every Decided / Approved PDUFA row, find the Drugs@FDA submission the decision refers
    to and write _d.fda_action_date, _d.fda_action_source_url (the letter, else the Drugs@FDA
    overview) and _d.fda_action_record ("NDA 218592 ORIG-1");
  * a row excluded because its date was only an announcement (_d.decision_date_unsourced) is
    RE-ADMITTED the moment the FDA record appears -- re-checked every run, which is what
    tests/test_excluded_rows_rechecked.py asserts via _fda_action_state.json;
  * CBER products (gene therapies, oncolytic viruses) are not in Drugs@FDA; their dated FDA
    approval notices are hand-verified into _fda_action_manual.json and applied the same way.

MATCH RULE (conservative; a wrong date is worse than none). Candidate submissions are AP
records for a brand / ingredient named on the row whose status date is ON OR BEFORE the date
we hold (an announcement cannot precede the action) and no more than 10 days before it. The
latest such date wins. Anything else is printed as a lead and nothing is written. An existing
fda_action_date that disagrees (e.g. one read from a CRL letter) is never overwritten; the
conflict is printed.

    python sync_fda_action_dates.py [--dry-run] [--only TICKER]
"""
import argparse
import datetime as dt
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
STATE = os.path.join(HERE, "_fda_action_state.json")
MANUAL = os.path.join(HERE, "_fda_action_manual.json")
API = "https://api.fda.gov/drug/drugsfda.json"
UA = {"User-Agent": "pdufa.bio builder (data@pdufa.bio)"}
MAX_LAG = 10          # days an announcement may trail the FDA action
STOP = {"TABLETS", "TABLET", "INJECTION", "CAPSULES", "CAPSULE", "ORAL", "SOLUTION", "LABEL",
        "UPDATE", "SNDA", "SBLA", "NDA", "BLA", "PLUS", "WITH", "AND", "FOR", "THE", "CREAM",
        "TYPE", "CKD", "T1D", "APDS", "PDUFA", "RESUBMISSION", "PEDIATRIC", "PAEDIATRIC",
        "SUBCUTANEOUS", "INTRAVENOUS", "EXTENDED", "RELEASE", "COMBINATION", "LOWER", "DOSE",
        "DOSES", "PHASE", "TRIAL", "STUDY", "ADULT", "ADULTS", "CHILDREN", "PATIENTS", "THERAPY",
        "GENE", "VACCINE", "INFLUENZA", "ESTROGEN", "WEEKLY", "PATCH", "AUTOINJECTOR", "HYDROCHLORIDE",
        "SODIUM", "ACETATE", "DECANOATE", "BEVACIZUMAB", "ADALIMUMAB", "USTEKINUMAB", "DENOSUMAB",
        "AFLIBERCEPT", "TRASTUZUMAB", "INSULIN", "FULVESTRANT", "NIVOLUMAB", "PEMBROLIZUMAB",
        "DARATUMUMAB", "DEXAMETHASONE", "PACLITAXEL", "ABEMACICLIB", "ETHINYL", "ESTRADIOL"}


def eastern_today():
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("America/New_York")).date()
    except Exception:
        return (dt.datetime.utcnow() - dt.timedelta(hours=4)).date()


def load_rows():
    src = io.open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    i, j = src.index("["), src.rindex("]") + 1
    return src, i, j, json.loads(src[i:j])


def terms_for(r):
    """Brand / ingredient candidates named on the row, most specific first."""
    d = r.get("_d") or {}
    out = []
    def add(s):
        s = re.sub(r"[^A-Za-z0-9\- ]", " ", str(s or "")).strip()
        for w in re.split(r"\s+", s):
            w = w.strip("-").upper()
            if len(w) >= 5 and not re.match(r"^[A-Z]{1,4}-?\d", w) and w not in STOP and w not in out:
                out.append(w)
    add(d.get("brand"))
    name = str(r.get("name") or "")
    add(re.split(r"[(\-;,]", name)[0])
    for inner in re.findall(r"\(([^)]*)\)", name):
        for part in re.split(r"[;,]", inner):
            add(part)
    return out[:5]


def query(term):
    q = (f'products.brand_name:"{term}"+openfda.brand_name:"{term}"+'
         f'products.active_ingredients.name:"{term}"+openfda.generic_name:"{term}"')
    url = f"{API}?search={urllib.parse.quote(q, safe=':+')}&limit=20"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as resp:
                return json.load(resp).get("results", [])
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return []
            time.sleep(2 + attempt * 3)
        except Exception:
            time.sleep(2 + attempt * 3)
    return None                                   # unknown (network), distinct from "none"


def candidates(results, lo, hi):
    """AP submissions dated in [lo, hi] -> [(date, appl, sub_type, sub_no, letter_url)]."""
    out = []
    for res in results or []:
        appl = res.get("application_number", "")
        for s in res.get("submissions", []):
            if s.get("submission_status") != "AP":
                continue
            ds = str(s.get("submission_status_date") or "")
            if not re.match(r"^\d{8}$", ds):
                continue
            d = dt.date(int(ds[:4]), int(ds[4:6]), int(ds[6:]))
            if not (lo <= d <= hi):
                continue
            letter = next((x.get("url") for x in s.get("application_docs", [])
                           if (x.get("type") or "").lower() == "letter" and x.get("url")), None)
            out.append((d, appl, s.get("submission_type", ""), s.get("submission_number", ""), letter,
                        res.get("sponsor_name", "")))
    return out


def overview_url(appl):
    num = re.sub(r"\D", "", appl)
    return f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo={num}"


def record_label(appl, st, sn):
    kind = re.match(r"[A-Z]+", appl).group(0) if re.match(r"[A-Z]+", appl) else ""
    num = re.sub(r"\D", "", appl)
    return f"{kind} {num} " + ("ORIG-1" if st == "ORIG" else f"S-{int(sn):03d}" if str(sn).isdigit() else f"{st}-{sn}")


def apply_found(r, date, url, label, how):
    d = r.setdefault("_d", {})
    changed = []
    if d.get("fda_action_date") != date:
        d["fda_action_date"] = date; changed.append("fda_action_date")
    if d.get("fda_action_source_url") != url:
        d["fda_action_source_url"] = url; changed.append("source")
    if d.get("fda_action_record") != label:
        d["fda_action_record"] = label; changed.append("record")
    if d.get("decision_date_unsourced"):
        d.pop("decision_date_unsourced", None)
        pretty = dt.date.fromisoformat(date).strftime("%B %-d, %Y") if os.name != "nt" else \
            dt.date.fromisoformat(date).strftime("%B %#d, %Y")
        d["decision_date_note"] = (f"The FDA's action date, {pretty}, is from {how} ({label}). "
                                   f"{r.get('dcd')} is the day the sponsor announced it.")
        changed.append("re-admitted")
    elif date != str(r.get("dcd")) and d.get("decision_date_note", "").find("not yet in Drugs@FDA") >= 0:
        pretty = dt.date.fromisoformat(date).strftime("%B %#d, %Y" if os.name == "nt" else "%B %-d, %Y")
        d["decision_date_note"] = (f"The FDA's action date, {pretty}, is from {how} ({label}). "
                                   f"{r.get('dcd')} is the day the sponsor announced it.")
        changed.append("note")
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--since", default="2025-01-01", help="decision dates on or after this")
    a = ap.parse_args()

    src, i, j, rows = load_rows()
    state = json.load(io.open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {}
    manual = json.load(io.open(MANUAL, encoding="utf-8")).get("records", {}) if os.path.exists(MANUAL) else {}
    today = eastern_today()
    n_found = n_new = n_none = n_conf = n_skip = 0
    cache = {}

    for r in rows:
        if r.get("type") != "PDUFA" or str(r.get("st", "")).lower() != "decided":
            continue
        if r.get("oc") != "Approved":
            # Drugs@FDA lists approvals only. A CRL's action date comes from the FDA's released
            # letter (link_crl_letters.py writes fda_action_date + the openFDA PDF); record that
            # letter as the action-date source so every surface cites it the same way.
            d = r.get("_d") or {}
            u = str(d.get("decision_source_url") or "")
            if (d.get("fda_action_date") and re.match(r"https://download\.open\.fda\.gov/crl/", u)
                    and not a.dry_run):
                lab = "CRL letter " + re.sub(r"\.pdf$", "", os.path.basename(u), flags=re.I)
                if d.get("fda_action_source_url") != u or d.get("fda_action_record") != lab:
                    d["fda_action_source_url"] = u
                    d["fda_action_record"] = lab     # unique per letter: the merge key in build_early_decisions
                    print(f"  {r['id']}: CRL letter recorded as action-date source ({d['fda_action_date']})")
                if d.get("decision_date_unsourced"):          # re-admit: the letter states the day
                    d.pop("decision_date_unsourced", None)
                    print(f"  {r['id']}: re-admitted -- the FDA's released CRL is dated {d['fda_action_date']}")
            elif d.get("decision_date_unsourced"):
                state[r["id"]] = {"checked": today.isoformat(), "result": "crl-no-letter"}
            continue
        dcd = str(r.get("dcd") or "")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", dcd) or dcd < a.since:
            continue
        tk = str(r.get("t") or "").upper()
        if a.only and tk != a.only.upper():
            continue
        d = r.get("_d") or {}
        rid = r["id"]
        hi = dt.date.fromisoformat(dcd)
        lo = hi - dt.timedelta(days=MAX_LAG)

        # already sourced to an FDA record and nothing to re-check
        if d.get("fda_action_source_url") and not d.get("decision_date_unsourced"):
            n_found += 1
            continue

        if rid in manual:
            m = manual[rid]
            ch = [] if a.dry_run else apply_found(r, m["date"], m["url"], m["label"], m.get("how", "the FDA's approval notice"))
            print(f"  {rid}: FDA notice {m['date']} ({m['label']}) {'-> ' + ','.join(ch) if ch else ''}")
            state[rid] = {"checked": today.isoformat(), "result": "manual", "date": m["date"]}
            n_found += 1; n_new += bool(ch)
            continue

        # rows that do not need a look today: old, never matched, checked in the last 14 days
        st = state.get(rid) or {}
        recent = (hi >= today - dt.timedelta(days=120))
        if (not d.get("decision_date_unsourced") and not recent and st.get("result") == "none"
                and st.get("checked", "") >= (today - dt.timedelta(days=14)).isoformat()):
            n_skip += 1
            continue

        found = []
        unknown = False
        for term in terms_for(r):
            if term not in cache:
                cache[term] = query(term)
                time.sleep(0.3)
            res = cache[term]
            if res is None:
                unknown = True
                continue
            found += candidates(res, lo, hi)
        found = sorted(set(found), reverse=True)
        if not found:
            state[rid] = {"checked": today.isoformat(), "result": "unknown" if unknown else "none",
                          "terms": terms_for(r)}
            n_none += 1
            if d.get("decision_date_unsourced"):
                print(f"  {rid}: still no Drugs@FDA record (terms {terms_for(r)}); stays excluded")
            continue
        date_, appl, stype, sno, letter, sponsor = found[0]
        iso = date_.isoformat()
        label = record_label(appl, stype, sno)
        url = letter or overview_url(appl)
        old = d.get("fda_action_date")
        if old and old != iso:
            print(f"  CONFLICT {rid}: held fda_action_date {old}, Drugs@FDA {label} says {iso} -- not overwritten")
            state[rid] = {"checked": today.isoformat(), "result": "conflict", "date": iso, "label": label}
            n_conf += 1
            continue
        ch = [] if a.dry_run else apply_found(r, iso, url, label, "Drugs@FDA")
        state[rid] = {"checked": today.isoformat(), "result": "found", "date": iso, "label": label}
        n_found += 1; n_new += bool(ch)
        flag = f"{(dt.date.fromisoformat(dcd) - date_).days:+d}d vs held {dcd}" if iso != dcd else "= held date"
        print(f"  {rid}: {label} AP {iso} ({flag}) sponsor={sponsor}{' -> ' + ','.join(ch) if ch else ''}")

    if not a.dry_run:
        io.open(DATASET, "w", encoding="utf-8").write(src[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + src[j:])
        io.open(STATE, "w", encoding="utf-8", newline="\n").write(json.dumps(state, indent=1, sort_keys=True) + "\n")
    print(f"fda action dates: {n_found} approval row(s) sourced to an FDA record ({n_new} changed this run), "
          f"{n_none} without one, {n_conf} conflict(s), {n_skip} skipped (checked recently)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
