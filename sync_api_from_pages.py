# -*- coding: utf-8 -*-
"""sync_api_from_pages.py -- make the machine-readable API mirror the published pages. Self-healing.

THE RECURRING BUG this kills: publishing a decision touches the PAGE side (decisions archive +
/fda-decision page + homepage board) but the API record in api/v1/dataset.mjs is edited by hand -- and
three times now it has been forgotten, leaving /api/v1/events contradicting the site (VTRS "Awaiting"
while the site said Approved, OTLK the same, CAPR AdComm "Scheduled" after it had voted). That feed is
what /llms.txt hands to AI assistants, so a stale record is actively misinforming.

The durable fix is not "remember to edit both" -- it is to DERIVE the API from the pages every run:

  decisions/index.html   (the canonical published archive)  -> PDUFA records: st=Decided, oc, dcd
  adcomm/<T>-<date>/     (published AdComm pages)           -> AdComm records: st=Held, vote outcome

Anything published on the site is reflected in the API on the next run. Nothing is invented: this only
copies outcomes that are already published, primary-source-verified, on a page.

Idempotent + safe: only writes when something actually changed; never touches records the pages don't
cover; keeps a .bak_apisync backup.

    python sync_api_from_pages.py [--dry-run]
"""
import argparse, glob, json, os, re
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
DECISIONS = os.path.join(SITE, "decisions", "index.html")
ADCOMM_DIR = os.path.join(SITE, "adcomm")
NOW = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def published_decisions():
    """{(TICKER, date): outcome} from the canonical decisions archive."""
    if not os.path.exists(DECISIONS):
        return {}
    html = open(DECISIONS, encoding="utf-8", errors="replace").read()
    out = {}
    for m in re.finditer(r'href="/fda-decision/([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})"', html):
        tk, date = m.group(1), m.group(2)
        tail = html[m.end():m.end() + 260].lower()
        if "crl" in tail or "complete response" in tail:
            oc = "CRL"
        elif "withdraw" in tail:
            oc = "Withdrawn"
        else:
            oc = "Approved"
        out.setdefault((tk, date), oc)
    return out


VOTE = re.compile(r'(\d+)\s*(?:for|yes)\b.{0,24}?(\d+)\s*(?:against|no)\b', re.I | re.S)


def published_adcomms():
    """{(TICKER, date): 'voted N-M favorable|against'} from published AdComm pages."""
    out = {}
    for page in sorted(glob.glob(os.path.join(ADCOMM_DIR, "*", "index.html"))):
        base = os.path.basename(os.path.dirname(page))
        m = re.match(r'^([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})$', base)
        if not m:
            continue
        html = open(page, encoding="utf-8", errors="replace").read()
        v = VOTE.search(html)
        if not v:
            continue
        f, a = int(v.group(1)), int(v.group(2))
        out[(m.group(1), m.group(2))] = (f"{f}-{a} favorable" if f > a else f"{f}-{a} against", f, a)
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = open(DATASET, encoding="utf-8", errors="replace").read().replace("\x00", "")
    i = src.find("[")
    prefix, arr_txt = src[:i], src[i:]
    arr, end = json.JSONDecoder().raw_decode(arr_txt)
    suffix = arr_txt[end:]

    decs, adcs = published_decisions(), published_adcomms()
    changes = []

    for r in arr:
        tk, d, typ = r.get("t"), str(r.get("d") or "")[:10], r.get("type")
        if typ == "PDUFA":
            # match the published decision for this ticker within 14 days of the listed PDUFA date
            hit = None
            for (dtk, ddate), oc in decs.items():
                if dtk != tk:
                    continue
                try:
                    gap = abs((dt.date.fromisoformat(ddate) - dt.date.fromisoformat(d)).days)
                except Exception:
                    continue
                if gap <= 14 and (hit is None or gap < hit[0]):
                    hit = (gap, ddate, oc)
            if hit and (r.get("st") != "Decided" or r.get("oc") != hit[2] or r.get("dcd") != hit[1]):
                changes.append(f"PDUFA {tk} {d}: st={r.get('st')}->Decided oc={r.get('oc')}->{hit[2]} dcd->{hit[1]}")
                r["st"], r["oc"], r["dcd"], r["ua"] = "Decided", hit[2], hit[1], NOW
        elif typ == "AdComm":
            hit = adcs.get((tk, d))
            if hit and (r.get("st") != "Held" or r.get("oc") != hit[0]):
                changes.append(f"AdComm {tk} {d}: st={r.get('st')}->Held oc->{hit[0]}")
                r["st"], r["oc"], r["ua"] = "Held", hit[0], NOW

    print(f"decisions archive: {len(decs)} published | adcomm pages with a vote: {len(adcs)}")
    if not changes:
        print("API already mirrors the pages -- no changes.")
        return
    print(f"{len(changes)} record(s) to sync:")
    for c in changes:
        print("  ", c)
    if args.dry_run:
        print("DRY RUN -- not written."); return
    open(DATASET + ".bak_apisync", "w", encoding="utf-8").write(src)
    open(DATASET, "w", encoding="utf-8").write(prefix + json.dumps(arr, separators=(",", ":"), ensure_ascii=False) + suffix)
    print("wrote dataset.mjs (backup: dataset.mjs.bak_apisync)")


if __name__ == "__main__":
    main()
