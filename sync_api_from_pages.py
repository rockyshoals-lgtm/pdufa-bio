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
        # drug text from the listing row ("Approved: {drug}" / "CRL: {drug}") -- the
        # evidence a wide-window match needs. Empty when the row states none.
        dm = re.search(r'(?:Approved|CRL)</span>:\s*([^<]{3,80})', html[m.end():m.end() + 260])
        out.setdefault((tk, date), (oc, (dm.group(1).strip() if dm else "")))
    return out


def _toks(s):
    return {w for w in re.findall(r"[a-z0-9]{4,}", str(s or "").lower())
            if w not in ("with", "combination", "priority", "review")}


def _lead_match(row_name, page_drug):
    """Wide-window evidence: the LEAD (brand/first) drug token of one side must appear
    in the other side's tokens. A single shared molecule token is NOT enough -- the
    Aug 27 'Bixlenvo (bictegravir/lenacapavir)' approval shares 'lenacapavir' with the
    2027 'Yeztugo (lenacapavir) once-weekly' row and they are different products; lead
    tokens ('bixlenvo' vs 'yeztugo') tell them apart. Additionally, if BOTH sides name
    a trial in parentheses and the trials differ, reject (relacorilant GRACE != ROSELLA).
    """
    rt, pt = _toks(row_name), _toks(page_drug)
    if not rt or not pt:
        return False
    rl = re.findall(r"[A-Za-z][A-Za-z0-9]{3,}", str(row_name or ""))
    pl = re.findall(r"[A-Za-z][A-Za-z0-9]{3,}", str(page_drug or ""))
    lead_ok = bool(rl and rl[0].lower() in pt) or bool(pl and pl[0].lower() in rt)
    if not lead_ok:
        return False
    tr_r = set(re.findall(r"\(([A-Z][A-Za-z]*[-_ ]?\d+[A-Za-z0-9-]*)\)", str(row_name or "")))
    tr_p = set(re.findall(r"\(([A-Z][A-Za-z]*[-_ ]?\d+[A-Za-z0-9-]*)\)", str(page_drug or "")))
    if tr_r and tr_p and not (tr_r & tr_p):
        return False
    return True


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
            # Match the published decision for this ticker. Two tiers:
            #   |gap| <= 14: ticker + proximity is evidence enough (unchanged behavior).
            #   wide window: the FDA decides EARLY as the norm (2026 sourced: 16 of 28
            #     before the goal date; REGN -12 barely fit the old 14-day cap, AZN -18,
            #     TAK -56, NUVL -58, CORT -108 never could). Approvals accepted
            #     -180..+45 days of goal, CRLs -14..+45 -- the same-review-cycle bounds
            #     mark_calendar_decided already uses -- but ONLY with a shared drug
            #     token, because ticker+date alone re-creates the relacorilant trap
            #     (same molecule, different application, 267 days apart).
            hit = None
            rtoks = _toks(r.get("name"))
            for (dtk, ddate), (oc, ddrug) in decs.items():
                if dtk != tk:
                    continue
                try:
                    sgap = (dt.date.fromisoformat(ddate) - dt.date.fromisoformat(d)).days
                except Exception:
                    continue
                gap = abs(sgap)
                if gap <= 14:
                    pass
                elif (-180 <= sgap <= 45 if oc == "Approved" else -14 <= sgap <= 45) \
                        and _lead_match(r.get("name"), ddrug):
                    pass
                else:
                    continue
                if hit is None or gap < hit[0]:
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
