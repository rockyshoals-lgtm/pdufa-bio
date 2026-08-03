# -*- coding: utf-8 -*-
"""strip_dashes_generators.py -- keep em dashes from coming BACK on the next rebuild.

Sweeping the built HTML is only half the job: the daily GitHub Action regenerates most of those
pages from Python templates, so any em dash left in a generator would reappear within 24 hours.

This edits only the dashes that end up in HTML. A dash on a line with no HTML marker is a code
comment or a docstring (there are hundreds of those in the modelling scripts) and is left alone,
because rewriting comments risks breaking code for zero reader benefit.

    python strip_dashes_generators.py --preview
    python strip_dashes_generators.py
"""
import argparse, collections, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strip_dashes import PHRASES, RANGES, choose, EM, EN   # one rule set, not two

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))

# A line is "HTML-bearing" if it opens a tag, closes one, or carries an HTML entity.
HTML_LINE = re.compile(r"</?[a-zA-Z][^>]*>|&[a-z]+;|class=|href=|<br|content=")

# These files manipulate dashes as DATA (they are the sweep tooling itself). Rewriting their
# literals would corrupt the rules that do the sweeping.
SELF = {"strip_dashes.py", "strip_dashes_generators.py", "apply_legal_footer.py"}

# A dash that is the whole string literal is a missing-value fallback, not punctuation.
LONE_LITERAL = re.compile(r"(['\"])\s*(?:&mdash;|" + "—" + r")\s*\1")
# A spaced en dash between two numeric expressions is a range.
NUM_RANGE = re.compile(r"(\}|\d) " + "–" + r" (\$|\{|\d)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    a = ap.parse_args()

    log = collections.Counter()
    touched = 0
    for f in sorted(os.listdir(HERE)):
        if not f.endswith(".py") or f in SELF:
            continue
        p = os.path.join(HERE, f)
        src = open(p, encoding="utf-8", errors="replace").read()
        if "pdufa_site_src" not in src:
            continue                      # not a site generator
        lines = src.split("\n")
        out, n = [], 0
        for ln in lines:
            if not HTML_LINE.search(ln) or not re.search("&mdash;|&ndash;|[" + EM + EN + "]", ln):
                out.append(ln); continue
            new = LONE_LITERAL.sub(r"\1n/a\1", ln)
            new = new.replace("&mdash;", EM).replace("&ndash;", EN)
            new = LONE_LITERAL.sub(r"\1n/a\1", new)
            new = NUM_RANGE.sub(r"\1 to \2", new)
            for rx, rep in RANGES:
                new = rx.sub(rep, new)
            for x, y in PHRASES:
                new = new.replace(x, y)
            new = re.sub(r"(\w)" + EN + r"(\w)", r"\1-\2", new)
            while True:
                m = re.search("[" + EM + EN + "]", new)
                if not m:
                    break
                rep = choose(new[m.end():m.end() + 120])
                log[(f, re.sub(r"\s+", " ", new[max(0, m.start() - 40):m.start() + 40]), rep.strip())] += 1
                new = new[:m.start()].rstrip(" ") + rep + new[m.end():].lstrip(" ")
            n += 1
            out.append(new)
        if n:
            touched += 1
            if not a.preview:
                open(p, "w", encoding="utf-8").write("\n".join(out))
            print(f"  {f}: {n} HTML line(s) cleaned")

    print(f"\n{'would clean' if a.preview else 'cleaned'} {touched} generator(s); "
          f"{sum(log.values())} dash replacements")
    for (f, ctx, rep), v in log.most_common(30):
        print(f"   {f:26s} {ctx[:80]}  ==> {rep}")


if __name__ == "__main__":
    main()
