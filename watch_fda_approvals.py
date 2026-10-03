# -*- coding: utf-8 -*-
"""watch_fda_approvals.py -- independent early-approval watch against FDA's own data.

THE GAP THIS CLOSES (David, 2026-09-01): every safeguard we had was downstream of our
own news crawl -- if nobody told us about an approval, nothing looked for it. But the
FDA deciding EARLY is the norm (16 of 28 sourced 2026 decisions came before the goal
date; CORT was 108 days early), and the crawl's attention keys off the goal date.

This watcher asks FDA directly. Daily, for every Upcoming day-precision PDUFA event, it
queries the openFDA Drugs@FDA endpoint by drug name and flags any AP (approved)
submission dated within the last 60 days that falls in the same-review-cycle window of
the event's goal date (-180..+45). Probe results 2026-09-01: garetosmab's Aug 19
approval appeared in the feed by Aug 28 (~9-day lag); capivasertib's Jun 12 approval is
recorded to the exact day. So this is a SAFETY NET measured in days, not a same-day
detector -- the crawl stays the fast path.

Discipline:
  - A hit is a LEAD, never an auto-publish. Verify against the sponsor/FDA release,
    publish the decision page, and the sync propagates it (verify-then-publish).
  - NEW unacknowledged hits EXIT 1 so CI blocks and the lead gets looked at.
    Reviewed hits go in _fda_watch_ack.json (with a reason) and stop alerting --
    same pattern as _calendar_flags_known.json. Shrink it; never grow it silently.
  - ~55 events -> ~55 requests/day, well inside openFDA's unkeyed limits.

    python watch_fda_approvals.py [--dry-run]   (dry-run: report, never exit 1)
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
sys.path.insert(0, HERE)
try:  # audit 2026-10-03 Tier 1.1: leads are also written for quarantine_leads.py (held row, not held site)
    from quarantine_leads import emit as _emit_lead
except Exception:  # noqa: BLE001
    def _emit_lead(*_a, **_k):
        return None

SITE = os.path.join(HERE, "pdufa_site_src")
ACK = os.path.join(HERE, "_fda_watch_ack.json")
API = "https://api.fda.gov/drug/drugsfda.json"
LOOKBACK_DAYS = 60
# Rule 1.3(d), audit 2026-10-03: a lone organ/tissue word is never a disease match ("thyroid"
# matched an MCT8-deficiency notice to Enspryng's thyroid eye disease filing).
ORGAN_WORDS = {"thyroid", "liver", "hepatic", "kidney", "renal", "heart", "cardiac", "lung", "lungs",
               "pulmonary", "brain", "cerebral", "skin", "dermal", "bone", "bones", "blood", "ocular",
               "retina", "retinal", "breast", "prostate", "bladder", "colon", "colorectal", "gastric",
               "stomach", "pancreas", "pancreatic", "ovarian", "uterine", "cervical", "spinal", "nerve",
               "muscle", "joint", "joints", "airway", "bowel", "intestinal", "adrenal", "pituitary",
               "immune", "vascular", "arterial", "venous", "neural", "plasma", "marrow"}


def search_terms(name):
    """Best query candidates from an event name: parenthetical generic first (it is the
    INN openFDA indexes), then the lead brand/code token. 'Mim8 (denecimig)' ->
    ['denecimig', 'Mim8']."""
    s = str(name or "")
    out = []
    STOP = {"combination", "subcutaneous", "extension", "sublingual", "injection",
            "tablet", "tablets", "capsule", "capsules", "solution", "release",
            "weekly", "monthly", "intravenous", "topical", "inhaled", "prefilled"}
    for par in re.findall(r"\(([^)]+)\)", s):
        # Rule 1.3(c), audit 2026-10-03: on a combination row match the INVESTIGATIONAL drug
        # only. "Giredestrant (+ everolimus)" queried everolimus and raised Novitium's generic
        # everolimus ANDA (approved 2026-09-21) as a lead on Roche's giredestrant NDA.
        if re.match(r"\s*(\+|plus\b|with\b|and\b|in combination\b|combined\b)", par, re.I):
            continue
        for w in re.findall(r"[A-Za-z][a-z]{5,}", par):   # generic-looking, lowercase-ish
            if w.lower() not in STOP:   # dosage-form words query the wrong universe:
                out.append(w)           # 'sublingual' hit an unrelated dexmedetomidine
    lead = re.search(r"[A-Za-z][A-Za-z0-9]{3,}", s)
    if lead and lead.group(0) not in out:
        out.append(lead.group(0))
    return out[:2]


# Rule 1.3(b), audit 2026-10-03: supplement classes that are never the decision on an efficacy
# filing. openFDA spells them "MANUF (CMC)" and "LABELING" -- the 09-01 list said
# "MANUFACTURING (CMC)", which openFDA never emits, so AGIO's PYRUKYND SUPPL-7 (MANUF (CMC),
# approved 2026-09-28) walked straight through and blocked CI. Matched by substring now.
NON_DECISION_CLASS = ("LABEL", "MANUF", "CMC", "REMS", "PACKAG", "BIOEQUIV")


def is_decision_submission(app_number, sub):
    """True when an openFDA submission can be the decision on an armed (NDA/BLA, efficacy) event.
    Rule 1.3(a): an ANDA (a generic) never matches an NDA/BLA event. Rule 1.3(b): administrative
    supplement classes never match. Unknown classes stay IN (fail loud, not silent)."""
    if str(app_number or "").upper().startswith("ANDA"):
        return False
    if sub.get("submission_status") != "AP":
        return False
    cls = str(sub.get("submission_class_code", "")).upper()
    return not any(k in cls for k in NON_DECISION_CLASS)


def query(term):
    # openFDA needs EXPLICIT +OR+ between clauses; bare '+' returns NOT_FOUND
    # (proven 2026-09-01: the first version silently found nothing for garetosmab).
    t = urllib.parse.quote(f'"{term}"')
    q = (f"products.active_ingredients.name:{t}+OR+openfda.generic_name:{t}"
         f"+OR+openfda.brand_name:{t}")
    url = f"{API}?search={q}&limit=5"
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return json.load(r).get("results", [])
    except Exception:
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8",
                  errors="replace").read().replace("\x00", "")
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    up = [r for r in rows if r.get("type") == "PDUFA" and r.get("dp") == "day"
          and str(r.get("st", "")).lower() != "decided" and r.get("d")]

    acks = {}
    if os.path.exists(ACK):
        acks = {(f["ticker"], f["ap_date"]): f.get("reason", "")
                for f in json.load(io.open(ACK, encoding="utf-8")).get("acks", [])}

    today = dt.date.today()
    floor = (today - dt.timedelta(days=LOOKBACK_DAYS)).strftime("%Y%m%d")
    new_hits, known = [], 0
    for r in up:
        tk, goal, name = str(r.get("t", "")).upper(), str(r.get("d"))[:10], r.get("name")
        gdate = dt.date.fromisoformat(goal)
        for term in search_terms(name):
            for res in query(term):
                for s in res.get("submissions", []) or []:
                    if not is_decision_submission(res.get("application_number"), s):
                        continue
                    # Administrative supplements are not decisions on our tracked
                    # applications: WINREVAIR's SUPPL-13 AP 2026-08-12 was LABELING
                    # while the HYPERION efficacy sBLA (goal 09-21) was still pending.
                    # A PDUFA event resolves as an ORIG or an EFFICACY/TYPE-coded
                    # supplement; unknown class codes stay IN (fail loud, not silent).
                    cls = str(s.get("submission_class_code", "")).upper()
                    sd = str(s.get("submission_status_date", ""))
                    if not (sd >= floor and re.match(r"^\d{8}$", sd)):
                        continue
                    ad = dt.date(int(sd[:4]), int(sd[4:6]), int(sd[6:8]))
                    if not (-180 <= (ad - gdate).days <= 45):
                        continue
                    key = (tk, ad.isoformat())
                    if key in acks:
                        known += 1
                        continue
                    _emit_lead("drugs_at_fda", r["id"], f"{tk}|{ad.isoformat()}",
                               f"AP {ad.isoformat()} on '{term}' ({res.get('application_number')} "
                               f"{s.get('submission_type')}-{s.get('submission_number')}, class {cls or 'unstated'})")
                    new_hits.append(
                        f"{tk} {str(name)[:40]} (goal {goal}): FDA feed shows AP "
                        f"{ad.isoformat()} on '{term}' "
                        f"({s.get('submission_type')}-{s.get('submission_number')}, "
                        f"class {cls or 'unstated'}) "
                        f"-- VERIFY against the sponsor/FDA release, then publish")
            time.sleep(0.3)

    # SECOND PASS: the FDA press-release feed, matched on SPONSOR and INDICATION, not drug name.
    # 2026-09-19: the FDA approved UX111 on 09-17 under a brand assigned at approval, FAYUVI,
    # and the press release named neither "UX111" nor "ABO-102". Drugs@FDA never saw it either:
    # a gene therapy is a CBER BLA and that endpoint is CDER's. The one thing the release DID
    # carry was the disease ("Sanfilippo syndrome type A") and, in the body, the sponsor. For
    # each armed event the press feed is scanned for the company's name or two indication
    # tokens; a hit is a lead with the same verify-then-publish rule as the first pass.
    STOPW = {"with", "type", "syndrome", "disease", "patients", "adult", "adults", "pediatric",
             "advanced", "metastatic", "cancer", "treatment", "therapy", "chronic", "first"} | ORGAN_WORDS

    def itoks(s):
        return {w for w in re.findall(r"[a-z][a-z0-9]{4,}", str(s or "").lower()) if w not in STOPW}

    def ctoks(company):
        return {w for w in re.findall(r"[a-z]{5,}", str(company or "").lower())
                if w not in {"pharmaceuticals", "pharmaceutical", "therapeutics", "holdings",
                             "biosciences", "sciences", "medicines", "limited", "company"}}

    press = []
    try:
        feed = urllib.request.urlopen(urllib.request.Request(
            "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml",
            headers={"User-Agent": "pdufa.bio watcher rockyshoals@gmail.com"}), timeout=40).read().decode("utf-8", "replace")
        for it in re.findall(r"<item>(.*?)</item>", feed, re.S):
            ti = re.search(r"<title>(.*?)</title>", it, re.S)
            ds = re.search(r"<description>(.*?)</description>", it, re.S)
            ln = re.search(r"<link>(.*?)</link>", it, re.S)
            pd = re.search(r"<pubDate>(.*?)</pubDate>", it)
            body = re.sub(r"<[^>]+>", " ", ((ti.group(1) if ti else "") + " " + (ds.group(1) if ds else "")))
            if re.search(r"\bapprov", body, re.I):
                press.append((pd.group(1)[:16] if pd else "", (ti.group(1) if ti else "")[:110],
                              (ln.group(1).strip() if ln else ""), body.lower()))
    except Exception as e:  # noqa: BLE001
        print(f"  (press feed unavailable: {e})")
    for r in up:
        tk, goal, name = str(r.get("t", "")).upper(), str(r.get("d"))[:10], r.get("name")
        gdate = dt.date.fromisoformat(goal)
        if abs((gdate - today).days) > 45:
            continue
        ind = itoks((r.get("_d") or {}).get("indication"))
        comp = ctoks(r.get("company"))
        for pdate, title, link, body in press:
            hit_c = [w for w in comp if w in body]
            hit_i = [w for w in ind if w in body]
            # one long, distinctive disease word is enough for a LEAD ("sanfilippo" alone
            # identifies the event; the sponsor sat in the release body, not the summary)
            if hit_c or len(hit_i) >= 2 or any(len(w) >= 9 for w in hit_i):
                key = (tk, "press:" + link)
                if key in acks or (tk, "press") in acks:
                    known += 1
                    continue
                _emit_lead("fda_press", r["id"], "press:" + link, f"{pdate} '{title}' {link}")
                new_hits.append(f"{tk} {str(name)[:40]} (goal {goal}): FDA press release {pdate} "
                                f"'{title}' matches {'sponsor ' + ','.join(hit_c) if hit_c else 'indication ' + ','.join(hit_i)} "
                                f"-- {link} -- VERIFY, then publish")

    # THIRD PASS: the sponsor's own SEC filings. 2026-09-19: Telix announced Pixclara's approval
    # in a 6-K on 09-14 and the site said "awaiting" for five days, because a diagnostic imaging
    # agent gets no FDA press release, no prompt Drugs@FDA row, and the company's newsroom
    # returns 403 to a script. The 6-K was in EDGAR full-text from the day it was filed. For each
    # armed event within 45 days of its goal date, search 8-K/6-K filed in the last 14 days for
    # the drug's lead token together with "approved"/"approval", restricted to filings that name
    # the sponsor. A hit is a lead, same rule as the other two passes.
    def edgar_recent(term, company_tok, days=14):
        start = (today - dt.timedelta(days=days)).isoformat()
        q = urllib.parse.quote(f'"{term}" "approval"')
        u = (f"https://efts.sec.gov/LATEST/search-index?q={q}&forms=8-K,6-K"
             f"&dateRange=custom&startdt={start}&enddt={today.isoformat()}")
        try:
            j = json.load(urllib.request.urlopen(urllib.request.Request(
                u, headers={"User-Agent": "pdufa.bio watcher rockyshoals@gmail.com"}), timeout=30))
        except Exception:
            return []
        out = []
        for h in j.get("hits", {}).get("hits", [])[:6]:
            s = h["_source"]
            filer = str(s.get("display_names", [""])[0]).lower()
            if company_tok and not any(w in filer for w in company_tok):
                continue
            adsh, fn = h["_id"].split(":", 1)
            m = re.search(r"CIK (\d+)", s.get("display_names", [""])[0])
            url = (f"https://www.sec.gov/Archives/edgar/data/{int(m.group(1))}/"
                   f"{adsh.replace('-', '')}/{fn}") if m else ""
            out.append((s.get("file_date"), s.get("form"), url))
        return out

    for r in up:
        tk, goal, name = str(r.get("t", "")).upper(), str(r.get("d"))[:10], r.get("name")
        gdate = dt.date.fromisoformat(goal)
        if abs((gdate - today).days) > 45:
            continue
        terms = search_terms(name)
        if not terms:
            continue
        term = terms[0]               # the INN / lead code, never a parenthetical disease word
        comp = ctoks(r.get("company"))
        for fdate, form, url in edgar_recent(term, comp):
            key = (tk, "edgar:" + url)
            if key in acks or (tk, "edgar") in acks:
                known += 1
                continue
            # A pipeline deck says "potential approval" next to every asset. The lead needs a
            # SENTENCE that says the FDA approved this drug: "FDA ... approved ... <term>",
            # "<term> ... (has been|was|is) approved", or "approval of ... <term>".
            try:
                body = urllib.request.urlopen(urllib.request.Request(
                    url, headers={"User-Agent": "pdufa.bio watcher rockyshoals@gmail.com"}), timeout=40).read().decode("utf-8", "replace")
                body = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))
            except Exception:
                continue
            t_ = re.escape(term)
            said = re.search(rf"(?:FDA|Food and Drug Administration)[^.]{{0,160}}\bapproved\b[^.]{{0,160}}{t_}"
                             rf"|{t_}[^.]{{0,160}}\b(?:has been|was|is|been)\s+approved\b"
                             rf"|\bapproval of\b[^.]{{0,80}}{t_}"
                             rf"|(?:FDA|Food and Drug Administration)\s+(?:has\s+)?approved\s+(?:its|the|our)?\s*[^.]{{0,60}}{t_}",
                             body, re.I)
            if not said:
                continue
            _emit_lead("edgar", r["id"], "edgar:" + url, f"{form} filed {fdate} states an approval of '{term}' {url}")
            new_hits.append(f"{tk} {str(name)[:40]} (goal {goal}): sponsor {form} filed {fdate} "
                            f"states an FDA approval of '{term}' -- {url} -- VERIFY, then publish")
        time.sleep(0.4)

    if new_hits:
        print(f"EARLY-APPROVAL WATCH: {len(new_hits)} unreviewed FDA-feed approval(s) "
              f"on armed events:")
        seen = set()
        for h in new_hits:
            if h not in seen:
                print(f"   {h}")
                seen.add(h)
        print(f"\n   Each is a LEAD, not a fact: verify, publish the decision page, and "
              f"the sync propagates it. Reviewed non-events go in _fda_watch_ack.json.")
        return 0 if a.dry_run else 1
    print(f"early-approval watch: {len(up)} armed events checked against FDA's feed, "
          f"0 unreviewed approvals ({known} previously reviewed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
