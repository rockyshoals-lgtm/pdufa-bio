# -*- coding: utf-8 -*-
"""Render the sponsor's own caveat, verbatim, on the event page that will rank for it.

Audit 2026-09-06 ORDER 2 residual: Scholar Rock's August 21 statement -- that Catalent
Indiana is being removed from the apitegromab BLA under FDA guidance and review will
progress solely with the second fill-finish facility -- sat in the dataset's
`_d.sponsor_caveat` and rendered nowhere. The slug page is the one that ranks for
"apitegromab pdufa date"; a reader arriving there deserves what the company itself said
about the review, in the company's words.

House rule, one owner per field: `sponsor_caveat` is written by the ingest scripts and
rendered ONLY here. Marker-bounded (<!--CAVEAT:BEGIN/END-->) and idempotent. The quote
is passed through verbatim -- never paraphrased, never summarised, never given a verb it
did not have.
"""
import html as _html
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
B, E = "<!--CAVEAT:BEGIN-->", "<!--CAVEAT:END-->"


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-")


def main():
    src = io.open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8",
                  errors="replace").read().replace("\x00", "")
    rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    n = 0
    for r in rows:
        d = r.get("_d") or {}
        caveat = str(d.get("sponsor_caveat") or "").strip()
        if not caveat or r.get("type") != "PDUFA":
            continue
        tk = str(r.get("t") or "").upper()
        company = str(r.get("company") or "the sponsor").strip()
        url = str(d.get("source_url_2") or d.get("source_url") or r.get("url") or "")
        label = str(d.get("source") or "the company's release")
        block = (
            f'{B}<div style="background:#0c1d38;border:1px solid #1e3a63;border-radius:12px;'
            f'padding:13px 15px;margin:12px 0"><b style="color:#e3ba5e">What the sponsor '
            f'said about the review</b><div style="color:#9db3d4;font-size:13.5px;'
            f'margin-top:6px;line-height:1.65">{_html.escape(company)}, in its own words: '
            f'&ldquo;{_html.escape(caveat)}&rdquo;'
            + (f' <a href="{_html.escape(url)}" rel="nofollow" style="color:#9ec5ff">'
               f'{_html.escape(label)}</a>.' if url.startswith("http") else "")
            + "</div></div>" + E)

        # every event page for this application: the bare ticker and the drug slug
        cands = [os.path.join(SITE, "pdufa", tk, "index.html")]
        nm = slugify(re.split(r"\s*[-(]", str(r.get("name") or ""))[0])
        if nm:
            cands.append(os.path.join(SITE, "pdufa", f"{tk}-{nm}", "index.html"))
        for p in cands:
            if not os.path.isfile(p):
                continue
            doc = io.open(p, encoding="utf-8", errors="replace").read()
            if B in doc:
                new = doc.split(B, 1)[0] + block + doc.split(E, 1)[1]
            else:
                anchor = ('<h2 id="the-story">' if '<h2 id="the-story">' in doc
                          else ("<!--FRESH:END-->" if "<!--FRESH:END-->" in doc else None))
                if not anchor:
                    continue
                new = (doc.replace(anchor, block + anchor, 1)
                       if anchor.startswith("<h2") else doc.replace(anchor, anchor + block, 1))
            if new != doc:
                io.open(p, "w", encoding="utf-8").write(new)
                n += 1
                print(f"  caveat rendered on {os.path.relpath(p, SITE)}")
    print(f"sponsor caveats: {n} page(s) updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
