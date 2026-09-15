# -*- coding: utf-8 -*-
"""The WebPage schema `name` must equal the page's own <title>. Audit 09-14 item 5.

A page can disagree with ITSELF. rewrite_decision_snippets corrected the <title> of
/fda-decision/BAYRY-2026-09-09 to drop "82 Days Early", but the WebPage JSON-LD node inside the
same file still carried

    "name":"HYRNUO (sevabertinib) Approved Sep 9, 2026, 82 Days Early | BAYRY FDA Decision"

because build_date_modified writes that block from the title it saw when it last ran, and
nothing re-derives it afterwards. Structured data is what an AI answer reads FIRST, so the
corrected title was the version humans saw and the stale one was the version machines got.

Two surfaces, one truth, inside a single HTML file. This makes the schema name follow the title
on every page that has both.

    python sync_jsonld_name_to_title.py [--dry-run]
"""
import argparse
import glob
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

SITE = "pdufa_site_src"
LD = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    n_files = n_nodes = 0
    for p in sorted(glob.glob(os.path.join(SITE, "**", "index.html"), recursive=True)):
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        tm = re.search(r"<title>(.*?)</title>", doc, re.S)
        if not tm:
            continue
        title = html.unescape(re.sub(r"\s+", " ", tm.group(1)).strip())
        changed_here = 0

        def one(m):
            nonlocal changed_here
            head, body, tail = m.groups()
            try:
                data = json.loads(body)
            except Exception:  # noqa: BLE001
                return m.group(0)

            def walk(node):
                nonlocal changed_here
                if isinstance(node, dict):
                    # only the node that means "this page"
                    if node.get("@type") in ("WebPage", "CollectionPage", "ItemPage") \
                            and isinstance(node.get("name"), str) \
                            and node["name"] != title:
                        node["name"] = title
                        changed_here += 1
                    for v in node.values():
                        walk(v)
                elif isinstance(node, list):
                    for v in node:
                        walk(v)
            walk(data)
            if not changed_here:
                return m.group(0)
            return head + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + tail

        new = LD.sub(one, doc)
        if changed_here and new != doc:
            n_files += 1
            n_nodes += changed_here
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8").write(new)

    print(f"schema name -> title: {n_nodes} node(s) on {n_files} page(s)"
          + ("   (--dry-run)" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
