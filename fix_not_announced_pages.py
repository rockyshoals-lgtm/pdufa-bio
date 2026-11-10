# -*- coding: utf-8 -*-
"""fix_not_announced_pages.py -- event pages for rows whose sponsor states NO FDA goal date say so on every surface.

2026-11-10 (David's ruling on NVO Mim8 and CagriSema): the rows carry _d.goal_date = "not announced". The event-page
builders still wrote a window into the meta description ("expected in Dec 2026"), the FAQ answer, the banner and an
Event JSON-LD with startDate/endDate, and one builder printed "expected in Not announced". This runs after them and
rewrites those surfaces from the row: no window, no Event schema, the sponsor's own sentence with its link.
Pages touched: the row's own /pdufa/ page and any /pdufa/ page whose canonical points at it. Idempotent.

    python fix_not_announced_pages.py [--dry-run]
"""
import argparse, glob, html, io, json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
BASE = "https://www.pdufa.bio"
esc = lambda s: html.escape(str(s or ""), quote=True)


def rows():
    s = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8").read()
    return [r for r in json.loads(s[s.index("["):s.rindex("]") + 1])
            if str((r.get("_d") or {}).get("goal_date") or "").lower() == "not announced"]


def fix(doc, r):
    d = r.get("_d") or {}
    drug = re.sub(r"\s*\(.*?\)\s*$", "", str(r.get("name") or "")).strip() or str(r.get("name") or "")
    sent = (f"No FDA goal date has been announced for {drug} ({r['t']}); the sponsor's latest filing states none.")
    desc = (f"{drug} ({r['t']}): no FDA goal date announced. The sponsor's latest filing gives none; "
            f"we add it when stated. Source-linked. Not advice.")[:158]
    for pat in (r'(<meta name="description" content=")[^"]*(")', r'(<meta property="og:description" content=")[^"]*(")',
                r'(<meta name="twitter:description" content=")[^"]*(")'):
        doc = re.sub(pat, lambda m: m.group(1) + esc(desc) + m.group(2), doc)
    doc = re.sub(r"FDA decision \(PDUFA\) target\s*<b>[^<]*</b>", "FDA goal date <b>not announced</b>", doc)
    doc = re.sub(r"FDA decision \(PDUFA\) target [A-Z][a-z]+ \d{4}", "FDA goal date not announced", doc)
    doc = re.sub(r"(<span>FDA PDUFA target date</span>\s*<b>)[^<]*(</b>)", r"\g<1>Not announced\g<2>", doc)
    doc = re.sub(r"All [A-Z][a-z]+ \d{4} PDUFA dates (&rarr;|→)", r"All upcoming PDUFA dates \1", doc)
    doc = re.sub(r'href="/calendar/\d{4}/[a-z]+"', 'href="/calendar"', doc)
    doc = re.sub(r"is expected in (?:Not announced|[A-Z][a-z]+ \d{4}|\d{4}|Q\d \d{4})", "has not been announced", doc)
    # JSON-LD: drop Event objects (a date-less event cannot be scheduled), restate FAQ answers
    def ld(m):
        try:
            j = json.loads(m.group(2))
        except ValueError:
            return m.group(0)
        def clean(o):
            if isinstance(o, dict):
                if o.get("@graph"):
                    o["@graph"] = [clean(x) for x in o["@graph"] if not (isinstance(x, dict) and x.get("@type") == "Event")]
                if o.get("@type") == "Answer" and re.search(r"PDUFA target date|expected in|goal date", str(o.get("text"))):
                    o["text"] = sent + " Dates are company/FDA-sourced; verify against the filing."
                for k, v in list(o.items()):
                    if isinstance(v, (dict, list)) and k != "@graph":
                        o[k] = clean(v)
            elif isinstance(o, list):
                return [clean(x) for x in o if not (isinstance(x, dict) and x.get("@type") == "Event")]
            return o
        j = clean(j)
        if isinstance(j, dict) and j.get("@type") == "Event":
            return ""
        return m.group(1) + json.dumps(j, ensure_ascii=False, separators=(",", ":")) + m.group(3)
    doc = re.sub(r'(<script type="application/ld\+json"[^>]*>)(.*?)(</script>)', ld, doc, flags=re.S)
    note = (f'<!--NOGOAL:BEGIN--><div class="card" style="margin:10px 0;border-color:#e3ba5e"><b>No FDA goal date has been '
            f'announced.</b> {esc(d.get("source") or "The sponsor")} (<a href="{esc(d.get("source_url"))}" rel="noopener">'
            f'source</a>) says: &ldquo;{esc(d.get("source_quote"))}&rdquo; That is not the FDA&#x27;s goal date, so this '
            f'application is not on the calendar. We add the date when the sponsor or the FDA states it.</div><!--NOGOAL:END-->')
    if "<!--NOGOAL:BEGIN-->" in doc:
        doc = re.sub(r"<!--NOGOAL:BEGIN-->.*?<!--NOGOAL:END-->", lambda _: note, doc, flags=re.S)
    else:
        doc = re.sub(r"(</h1>)", lambda m: m.group(1) + note, doc, count=1)
    doc = re.sub(r"<title>[^<]*</title>", lambda _: f"<title>{esc(drug)} FDA goal date: not announced ({esc(r['t'])}) | pdufa.bio</title>",
                 doc, count=1)
    doc = re.sub(r'(<meta (?:property="og:title"|name="twitter:title") content=")[^"]*(")',
                 lambda m: m.group(1) + esc(f"{drug} FDA goal date: not announced ({r['t']})") + m.group(2), doc)
    return doc


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    rs = rows(); n = 0
    pages = {p: io.open(p, encoding="utf-8").read() for p in glob.glob(os.path.join(SITE, "pdufa", "*", "index.html"))}
    for r in rs:
        url = str(r.get("url") or "")
        if not url.startswith("/pdufa/"):
            continue
        for p, doc in pages.items():
            rel = "/" + os.path.relpath(os.path.dirname(p), SITE).replace(os.sep, "/")
            canon = re.search(r'<link rel="canonical" href="([^"]+)"', doc)
            if rel != url and not (canon and canon.group(1) == BASE + url):
                continue
            new = fix(doc, r)
            if new != doc:
                n += 1
                print(f"  {rel}: rewritten (goal date not announced)")
                if not a.dry_run:
                    io.open(p, "w", encoding="utf-8").write(new)
                pages[p] = new
    print(f"not-announced pages: {len(rs)} row(s), {n} page(s) rewritten" + (" [dry run]" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
