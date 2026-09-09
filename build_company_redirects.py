# -*- coding: utf-8 -*-
"""/company/{slug} -> the sponsor's ticker hub, as permanent redirects in vercel.json.

Audit 2026-09-08c item 8: "pfizer pfe pdufa dates fda approval decisions 2026 2027" earns
82 Bing impressions at position 3.23 and 0 clicks, and /company/pfizer was a 404. The
entity page for a sponsor already exists: /ticker/{TK} aggregates every forward PDUFA,
past decision and readout for that company. A second page under /company/ would be a
duplicate of it; a 308 is one entity, one URL. The slug is the company's short name
(legal suffixes stripped), so /company/pfizer, /company/merck, /company/novo-nordisk all
resolve. Where two tickers share a name (ADR + ordinary), the hub with more events wins
and the other is skipped rather than guessed.

Managed as a deterministic block: every /company/* redirect in vercel.json is replaced
wholesale by the computed, sorted set (the same pattern build_drug_pages uses for /drug
aliases), so reruns cannot accumulate strays.
"""
import collections
import html
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
VJ = os.path.join(SITE, "vercel.json")
SUFFIX = re.compile(r",?\s+(?:inc\.?|corp\.?|corporation|ltd\.?|limited|plc|llc|n\.?v\.?|a/s|ag|"
                    r"s\.?a\.?|se|holdings?|holding ag|pharmaceuticals?|pharma|therapeutics|"
                    r"biosciences|biotherapeutics|biopharma|biopharmaceuticals?|sciences|"
                    r"medicines|company|co\.?|group|& co\.?,?)\b\.?", re.I)


def short_name(company):
    c = html.unescape(company).strip()
    c = re.sub(r"\s+A/S\b", "", c)                       # Danish "A/S" before the partner split
    c = re.split(r"\s*/\s*", c)[0]                       # "Roche/Genentech" -> "Roche"
    c = re.sub(r"\s*\(.*?\)\s*", " ", c)                 # drop parentheticals
    prev = None
    while prev != c:                                     # strip stacked suffixes
        prev = c
        c = SUFFIX.sub("", c).strip(" ,.")
    return c


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def main():
    cands = collections.defaultdict(list)                # slug -> [(events, tk, company)]
    for tk in sorted(os.listdir(os.path.join(SITE, "ticker"))):
        p = os.path.join(SITE, "ticker", tk, "index.html")
        if not re.match(r"^[A-Z]{1,6}$", tk) or not os.path.isfile(p):
            continue
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        m = re.search(r"<h1[^>]*>(.*?)\((?:[A-Z]{1,6})\)", doc, re.S)
        if not m:
            continue
        company = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        sn = short_name(company)
        slug = slugify(sn)
        if not slug or len(slug) < 3:
            continue
        events = len(re.findall(r'<a class="row"', doc))
        cands[slug].append((events, tk, company))
    redirects, skipped = [], []
    for slug, lst in sorted(cands.items()):
        lst.sort(reverse=True)
        if len(lst) > 1 and lst[0][0] == lst[1][0]:
            skipped.append((slug, [x[1] for x in lst]))
            continue
        redirects.append({"source": f"/company/{slug}", "destination": f"/ticker/{lst[0][1]}",
                          "permanent": True})
    cfg = json.load(io.open(VJ, encoding="utf-8"))
    kept = [r for r in cfg.get("redirects", []) if not str(r.get("source", "")).startswith("/company/")]
    cfg["redirects"] = kept + redirects
    io.open(VJ, "w", encoding="utf-8").write(json.dumps(cfg, indent=1, ensure_ascii=False) + "\n")
    print(f"company redirects: {len(redirects)} written, {len(skipped)} ambiguous skipped")
    for s in skipped[:10]:
        print("  ambiguous:", s)
    ex = [r for r in redirects if r["source"] in ("/company/pfizer", "/company/merck", "/company/novo-nordisk")]
    for r in ex:
        print("  ", r["source"], "->", r["destination"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
