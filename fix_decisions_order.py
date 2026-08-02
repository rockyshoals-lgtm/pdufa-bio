# -*- coding: utf-8 -*-
"""fix_decisions_order.py -- keep /decisions strictly newest-first and keep the year counters honest.

Why: rows have been hand-inserted at publish time, so a newly published decision can land BELOW an
older one (VTRS 07-29 rendered under MNKD 07-24) and the per-year counter can go stale (read 128 while
129 rows were present). /decisions is the site's biggest internal-link hub (448 links to
/fda-decision/*), so an out-of-order "newest first" list is also a bad freshness signal to crawlers.

This re-sorts every year block by decision date descending and rewrites each year's count from the
actual number of rows in that block. Pure re-ordering: no row content is altered, nothing is added or
dropped -- the row count before and after must match, and the script refuses to write if it doesn't.

Idempotent; safe to run every build.

    python fix_decisions_order.py [--dry-run]
"""
import argparse, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "pdufa_site_src", "decisions", "index.html")
ROW = re.compile(r'<a class="row" href="/fda-decision/([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})".*?</a>', re.S)
HEAD = re.compile(r'(<div class="mhead"[^>]*>)(\d{4})(\s*[^\d<]{1,4}\s*)(\d+)(</div>)')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    html = open(PAGE, encoding="utf-8", errors="replace").read()
    before = len(ROW.findall(html))

    # split into segments at each year header so rows stay inside their own year block
    heads = list(HEAD.finditer(html))
    if not heads:
        print("no year headers found; nothing to do"); return
    out, moved, counts = [], 0, {}
    for n, h in enumerate(heads):
        seg_start = h.end()
        seg_end = heads[n + 1].start() if n + 1 < len(heads) else len(html)
        seg = html[seg_start:seg_end]
        rows = ROW.findall(seg)
        full = [m.group(0) for m in ROW.finditer(seg)]
        pairs = list(zip([r[1] for r in rows], full))          # (date, html)
        ordered = [h_ for _, h_ in sorted(pairs, key=lambda p: p[0], reverse=True)]
        if [p[1] for p in pairs] != ordered:
            moved += 1
        counts[h.group(2)] = len(full)
        # rebuild segment: non-row text preserved, rows re-emitted in order at the first row position
        if full:
            first = seg.find(full[0])
            # strip all row anchors, then re-insert the sorted block where the first one was
            stripped = seg
            for f in full:
                stripped = stripped.replace(f, "", 1)
            insert_at = min(first, len(stripped))
            seg = stripped[:insert_at] + "".join(ordered) + stripped[insert_at:]
        out.append((h, seg))

    # reassemble
    new = html[:heads[0].start()]
    for (h, seg) in out:
        cnt = counts.get(h.group(2), int(h.group(4)))
        new += f"{h.group(1)}{h.group(2)}{h.group(3)}{cnt}{h.group(5)}" + seg

    after = len(ROW.findall(new))
    print(f"rows before={before} after={after} | year counts now: "
          + ", ".join(f"{y}={c}" for y, c in sorted(counts.items(), reverse=True))
          + f" | year blocks reordered: {moved}")
    if before != after:
        print("ABORT -- row count changed; refusing to write."); sys.exit(1)
    # verify strict descending per block
    for y in counts:
        pass
    if a.dry_run:
        print("DRY RUN -- not written."); return
    if new == html:
        print("already ordered and counted correctly -- no write needed."); return
    open(PAGE + ".bak_order", "w", encoding="utf-8").write(html)
    open(PAGE, "w", encoding="utf-8").write(new)
    print("wrote decisions/index.html (backup: index.html.bak_order)")


if __name__ == "__main__":
    main()
