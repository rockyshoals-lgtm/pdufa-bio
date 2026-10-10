# -*- coding: utf-8 -*-
"""watch_drug_approvals.py -- approval watch over EVERY drug page, not just dated events.

THE GAP THIS CLOSES (strategy audit 2026-09-05b): camizestrant was approved September 4
and our drug page said "under FDA review" the next day -- while we were the single
most-cited AI source on 'camizestrant pdufa date' (32% share). The event watcher
(watch_fda_approvals.py) never looked, correctly per its design: camizestrant's PDUFA
date was extended in May and never re-disclosed, so there was no day-precision Upcoming
event to watch. A drug with a page but no event was invisible to every safeguard.

This watcher keys on the DRUG-PAGE CORPUS (every /drug/{slug}) and asks three FDA
surfaces, fastest first:

  1. FDA press-announcement RSS + item pages ......... same-day   (camizestrant's path:
     the RSS title named no drug; the item body says "camizestrant" -- so item bodies
     are fetched for the lookback window, not just titles)
  2. FDA oncology approval-notifications page ........ same-day   (every oncology
     approval, generic name, dated to the day)
  3. openFDA Drugs@FDA recent-AP range query ......... ~9-day lag (everything, one
     paged query per run -- not 559 per-drug queries)

A match against a tracked drug whose own page does not yet record an approval is a
LEAD, never an auto-publish (verify against the sponsor/FDA release, publish the
decision page, sync propagates; then add the verified approval to
_drug_approvals_confirmed.json so the render guard holds the state). Unreviewed leads
EXIT 1 so CI blocks. Reviewed non-events go in _drug_watch_ack.json with a reason.

    python watch_drug_approvals.py [--dry-run]
"""
import argparse
import datetime as dt
import html as html_
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
ACK = os.path.join(HERE, "_drug_watch_ack.json")
RSS = "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml"
ONC = ("https://www.fda.gov/drugs/resources-information-approved-drugs/"
       "oncology-cancer-hematologic-malignancies-approval-notifications")
API = "https://api.fda.gov/drug/drugsfda.json"
LOOKBACK_DAYS = 21          # RSS/oncology page scan window
OPENFDA_LOOKBACK = 45       # openFDA feed lag is ~9 days; 45 gives slack
# 2026-10-03 (Tier 2.5): CI run 37148030700 read 0 items from the FDA press RSS and the oncology page
# with this UA, while watch_fda_drugs_feed.py read 20 items from fda.gov in the same run with the
# UA below. Hypothesis, not proven: fda.gov refuses the anonymous UA. Same UA as the working pass.
UA = {"User-Agent": "pdufa.bio watcher rockyshoals@gmail.com"}
# Supplement classes that are not decisions on a program's pending application --
# same stoplist the event watcher proved on WINREVAIR's LABELING supplement.
SKIP_CLASS = ("LABELING", "MANUFACTURING (CMC)", "MANUF (CMC)", "MANUFACTURING",
              "REMS", "PACKAGE CHANGE")
# Audit 2026-10-03 Tier 2.5: "0 press items scanned" was a zero with no reason. Each pass now
# records what it actually read in _watch_health.json and the summary line says which pass was
# blind, so a zero means "nothing new" and never "could not read".
HEALTH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_watch_health.json")
# Generic-looking tokens that are common English or dosage words -- never match keys.
# The first sweep (2026-09-05) proved which ones flood: 'therapy'/'disease'/'muscle'
# etc. matched every press item, via junk slugs like /drug/ttfields-therapy and
# /drug/world-muscle that carry an English word as a token.
STOP = {"combination", "subcutaneous", "extension", "sublingual", "injection",
        "tablet", "tablets", "capsule", "capsules", "solution", "release",
        "estrogen", "insulin", "vaccine", "placebo", "generic", "approval",
        "weekly", "monthly", "intravenous", "topical", "inhaled", "prefilled",
        "therapy", "disease", "diseases", "autologous", "allogeneic", "single",
        "treated", "muscle", "hematology", "oncology", "digestive", "european",
        "american", "recombinant", "expanded", "pediatric", "adjuvant", "chronic",
        "advanced", "against", "receptor", "antibody", "inhibitor", "syndrome"}


def fetch(url, timeout=25):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception:
        return ""


def drug_universe():
    """slug -> set of match tokens (slug words >=6 chars, generic-looking)."""
    out = {}
    droot = os.path.join(SITE, "drug")
    if not os.path.isdir(droot):
        return out
    for slug in os.listdir(droot):
        if not os.path.isfile(os.path.join(droot, slug, "index.html")):
            continue
        toks = {w for w in slug.split("-")
                if len(w) >= 6 and w.isalpha() and w not in STOP}
        if toks:
            out[slug] = toks
    return out


def page_records_approval(slug):
    """True when the drug page already states an FDA approval (any), so a feed hit is
    not news. Checks the rendered artifact because the render is what AI systems
    ground on -- a fixed dataset with a stale page is still the failure."""
    p = os.path.join(SITE, "drug", slug, "index.html")
    try:
        t = io.open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        return False
    return bool(re.search(r"FDA approved|approved (?:it )?on|&#10003; Approved|"
                          r"granted accelerated approval", t, re.I))


def scan_text_for_drugs(text, universe, resolved, src_label, leads, seen_pairs):
    low = re.sub(r"\s+", " ", html_.unescape(text)).lower()
    for slug, toks in universe.items():
        if slug in resolved:
            continue
        for tok in toks:
            if re.search(rf"\b{re.escape(tok)}\b", low) and \
               re.search(rf"\b{re.escape(tok)}\b[^.]{{0,240}}approv|"
                         rf"approv[^.]{{0,240}}\b{re.escape(tok)}\b", low):
                key = (slug, src_label)
                if key not in seen_pairs:
                    seen_pairs.add(key)
                    leads.append((slug, src_label,
                                  f"'{tok}' appears with approval language"))
                break


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    universe = drug_universe()
    resolved = {s for s in universe if page_records_approval(s)}
    acks = {}
    if os.path.exists(ACK):
        acks = {(f["slug"], f["source"]): f.get("reason", "")
                for f in json.load(io.open(ACK, encoding="utf-8")).get("acks", [])}

    today = dt.date.today()
    floor_iso = (today - dt.timedelta(days=LOOKBACK_DAYS)).isoformat()
    leads, seen = [], set()

    # 1. Press-announcement RSS: titles rarely carry the drug name (camizestrant's
    #    didn't), so recent item pages are fetched and their bodies scanned.
    rss = fetch(RSS)
    items = re.findall(r"<item>(.*?)</item>", rss, re.S)
    n_items = 0
    n_window = 0
    n_body_fail = 0
    for it in items:
        mlink = re.search(r"<link>\s*([^<\s]+)\s*</link>", it)
        mdate = re.search(r"<pubDate>([^<]+)</pubDate>", it)
        when = ""
        if mdate:
            try:
                when = dt.datetime.strptime(
                    mdate.group(1).strip()[:16], "%a, %d %b %Y").date().isoformat()
            except Exception:
                when = ""
        if not mlink or (when and when < floor_iso):
            continue
        n_window += 1
        body = fetch(mlink.group(1))
        if not body:
            n_body_fail += 1
        if body:
            n_items += 1
            scan_text_for_drugs(body, universe, resolved,
                                f"fda-press:{mlink.group(1).rsplit('/', 1)[-1][:60]}",
                                leads, seen)
        time.sleep(0.3)

    # 2. Oncology approval notifications: one page, generic names, dated to the day.
    #    The page is CUMULATIVE (years of approvals), so only chunks carrying a date
    #    inside the lookback window are scanned -- the first sweep flagged
    #    temozolomide's historical entry as if it were news.
    onc = fetch(ONC)
    if onc:
        recent_chunks = []
        for chunk in re.split(r"<li|<tr|<p[ >]", onc):
            md = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", chunk)
            if md:
                try:
                    cd = dt.date(int(md.group(3)), int(md.group(1)), int(md.group(2)))
                    if cd.isoformat() >= floor_iso:
                        recent_chunks.append(chunk)
                except ValueError:
                    pass
        if recent_chunks:
            scan_text_for_drugs(" ".join(recent_chunks), universe, resolved,
                                "fda-oncology-notifications", leads, seen)

    # 2b. Sponsor newsrooms (audit 2026-10-10 item 1): the Rhapsido SD approval reached the site 2.5
    #     days after Novartis announced it, because the only pass that could hear it was openFDA (the
    #     FDA issued no notice; watch_sponsor_newswire only arms rows with a pending PDUFA date, and
    #     this supplement had none). Every feed in _sponsor_feeds.json is read here for ANY sponsor,
    #     armed or not, and headlines are scanned for tracked drug names with approval language.
    try:
        import watch_sponsor_newswire as W
        feeds = json.load(io.open(W.FEEDS, encoding="utf-8")) if os.path.exists(W.FEEDS) else {}
        n_sp_feeds = n_sp_items = 0
        for tk, ent in sorted(feeds.items()):
            for u in (ent or {}).get("feeds") or []:
                listing = u.startswith("html:")
                doc = W.fetch(u[5:] if listing else u)
                if not doc:
                    continue
                its = W.parse_listing(u[5:], doc) if listing else W.parse_items(doc)
                n_sp_feeds += 1
                for it in its:
                    if it["date"] and it["date"].isoformat() < floor_iso:
                        continue
                    n_sp_items += 1
                    scan_text_for_drugs(it["title"] + " " + it["desc"], universe, resolved,
                                        f"sponsor:{tk}:{(it['date'] or today).isoformat()}", leads, seen)
        print(f"drug-page watch: sponsor newsrooms read {n_sp_feeds}, {n_sp_items} item(s) in window")
    except Exception as e:  # noqa: BLE001 -- a newsroom pass must never block the others
        print(f"drug-page watch: sponsor newsroom pass skipped ({e})")

    # 3. openFDA recent-AP range query: one paged query, matched client-side.
    f8 = (today - dt.timedelta(days=OPENFDA_LOOKBACK)).strftime("%Y%m%d")
    t8 = today.strftime("%Y%m%d")
    tok2slug = {}
    for slug, toks in universe.items():
        if slug in resolved:
            continue
        for tok in toks:
            tok2slug.setdefault(tok.upper(), slug)
    openfda_ok = False
    for skip in range(0, 1000, 100):
        q = (f"submissions.submission_status:AP+AND+"
             f"submissions.submission_status_date:[{f8}+TO+{t8}]")
        page = fetch(f"{API}?search={q}&limit=100&skip={skip}")
        if not page:
            break
        try:
            results = json.loads(page).get("results", [])
            openfda_ok = True
        except Exception:
            break
        for res in results:
            # Rule 1.3(a), audit 2026-10-03: a generic (ANDA) is never the decision on a program.
            if str(res.get("application_number", "")).upper().startswith("ANDA"):
                continue
            names = set()
            for pr in res.get("products", []) or []:
                for ai in pr.get("active_ingredients", []) or []:
                    names.update(re.findall(r"[A-Z]{6,}", str(ai.get("name", "")).upper()))
            of = res.get("openfda", {}) or {}
            for k in ("generic_name", "brand_name"):
                for v in of.get(k, []) or []:
                    names.update(re.findall(r"[A-Z]{6,}", str(v).upper()))
            hit_slugs = {tok2slug[n] for n in names if n in tok2slug}
            if not hit_slugs:
                continue
            for s in res.get("submissions", []) or []:
                if s.get("submission_status") != "AP":
                    continue
                if any(k in str(s.get("submission_class_code", "")).upper() for k in SKIP_CLASS):
                    continue
                sd = str(s.get("submission_status_date", ""))
                if not (re.match(r"^\d{8}$", sd) and f8 <= sd <= t8):
                    continue
                for slug in hit_slugs:
                    key = (slug, f"openfda:{sd}")
                    if key not in seen:
                        seen.add(key)
                        leads.append((slug, f"openfda:{sd}",
                                      f"AP {sd} ({s.get('submission_type')}-"
                                      f"{s.get('submission_number')}, class "
                                      f"{s.get('submission_class_code') or 'unstated'})"))
        if len(results) < 100:
            break
        time.sleep(0.3)

    # per-pass health (Tier 2.5)
    passes = {"fda_press_rss": {"read": bool(items), "items": len(items), "in_window": n_window,
                                "bodies_read": n_items, "bodies_failed": n_body_fail},
              "fda_oncology_notifications": {"read": bool(onc)},
              "openfda_recent_ap": {"read": openfda_ok}}
    try:
        health = json.load(io.open(HEALTH, encoding="utf-8")) if os.path.exists(HEALTH) else {}
        for k, v in passes.items():
            ent = health.setdefault("drug_watch_" + k, {})
            ent["last_attempt"] = today.isoformat()
            ent.update({kk: vv for kk, vv in v.items() if kk != "read"})
            if v["read"]:
                ent["last_ok"] = today.isoformat()
        io.open(HEALTH, "w", encoding="utf-8", newline="\n").write(json.dumps(health, indent=1, sort_keys=True) + "\n")
    except Exception as e:  # noqa: BLE001
        print(f"   (health file not written: {e})")
    blind = [k for k, v in passes.items() if not v["read"]]
    print(f"drug-page watch passes: press RSS {len(items)} item(s), {n_window} in the {LOOKBACK_DAYS}-day "
          f"window, {n_items} bodies read, {n_body_fail} body fetch(es) failed; oncology page "
          f"{'read' if onc else 'BLIND'}; openFDA {'read' if openfda_ok else 'BLIND'}"
          + (f"  -- BLIND: {', '.join(blind)}" if blind else ""))

    new = [(sl, src, why) for sl, src, why in leads if (sl, src) not in acks]
    known = len(leads) - len(new)
    if new:
        print(f"DRUG-PAGE WATCH: {len(new)} unreviewed approval lead(s) on tracked "
              f"drug pages that do not yet record an approval:")
        for sl, src, why in new:
            print(f"   /drug/{sl}  [{src}]  {why}")
            _emit_lead("drug_pages", "drug:" + sl, f"{sl}|{src}", f"/drug/{sl} {src} {why}")
        print("\n   Each is a LEAD, not a fact: verify against the sponsor/FDA "
              "release, publish the decision page, add the verified entry to "
              "_drug_approvals_confirmed.json, and ack non-events in "
              "_drug_watch_ack.json with a reason.")
        return 0 if a.dry_run else 1
    print(f"drug-page watch: {len(universe)} drug pages ({len(resolved)} already "
          f"record an approval), {n_items} press items scanned, 0 unreviewed leads "
          f"({known} previously reviewed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
