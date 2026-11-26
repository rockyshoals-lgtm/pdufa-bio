# -*- coding: utf-8 -*-
"""apply_1126_census_fda_days.py -- 2025 decision pages take the FDA's own action day from the decision-timing census.

2026-11-26 (David: "Continue"; the coordinator's note asked to fix the decision pages dated to the announcement
instead of the FDA action). The 2024-2025 census (decision_timing_2024_2025.json, /research/fda-decision-timing/
since-2024) read the FDA's own record of each action: Drugs@FDA's action date for the named submission, the FDA's
approval letter or notice, or the Complete Response Letter file the FDA released. 86 of its actions match a
2025 decision page (same ticker, page day within 4 days of the FDA action, one candidate page). 11 of those pages
already carried the FDA's day in _fda_action_archive.json, and agree with the census on every one. This records the
FDA day for the rest, so inject_fda_action_record.py, build_decision_faq.py, fix_decision_kv_action_date.py and
fix_decision_h1_action_date.py state it on the page (title, h1, key facts, FAQ), with the announcement day kept as
"Announced" where they differ.

Left out: split actions (approval of one strength or indication and a CRL for another: the page's single outcome
cannot name one action), rows whose action day comes from a sponsor document rather than an FDA record, and any row
whose record is not on an fda.gov host. sync_archive_fda_dates.py never overwrites an entry carrying a basis.
Idempotent. Facts only, not investment advice.

    python apply_1126_census_fda_days.py [--dry-run]
"""
import argparse
import html
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_decision_timing_since_2024 as census  # noqa: E402

TODAY = "2026-11-26"
BASIS = "decision-timing census 2026-11-26: FDA record read"
OUT = os.path.join(HERE, "_fda_action_archive.json")
# Drug rows too short to name the drug the FDA acted on (no word in common with the FDA record's name), given the
# name from the census (each checked against the FDA's letter, 2026-11-26).
DRUG_ROW = {"RARE-2025-07-11": "UX111 (rebisufligene etisparvovec, ABO-102)",
            "TLX-2025-04-28": "TLX101-CDx (Pixclara, floretyrosine F 18)"}
FDA_HOST = re.compile(r"^https://(?:www\.|download\.open\.)?(?:accessdata\.)?fda\.gov/")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    _doc, rows, _dropped = census.load_2024_2025()
    arch = json.load(io.open(OUT, encoding="utf-8"))
    k = kept = skipped = 0
    for r in rows:
        if not r.get("page"):
            continue
        slug = r["page"].rsplit("/", 1)[-1]
        cur = arch.get(slug) or {}
        if cur.get("date") and (cur.get("basis") or "") != BASIS:
            kept += 1
            if cur["date"] != r["action"]:
                raise SystemExit(f"{slug}: archive says {cur['date']}, census says {r['action']}; resolve by hand")
            continue
        if (r["outcome"] not in ("Approved", "CRL") or r["action_basis"] != "fda_record"
                or not FDA_HOST.match(r["action_url"] or "")):
            skipped += 1
            print(f"  skip {slug}: {r['outcome']}, {r['action_basis']}, {r['action_url'][:60]}")
            continue
        want = {"basis": BASIS, "checked": TODAY, "cid": r["cid"], "date": r["action"], "name": r["drug"],
                "oc": r["outcome"], "record": r["application"], "source_url": r["action_url"]}
        if cur != want:
            arch[slug] = want
            k += 1
    for slug, drug in DRUG_ROW.items():
        p = os.path.join(HERE, "pdufa_site_src", "fda-decision", slug, "index.html")
        doc = io.open(p, encoding="utf-8").read()
        new = re.sub(r'(<div class="kv"><span>Drug(?: / candidate)?</span><b>)[^<]*(</b></div>)',
                     lambda g: g.group(1) + html.escape(drug) + g.group(2), doc, count=1)
        if html.escape(drug) not in new:
            raise SystemExit(f"{slug}: drug row not found")
        if new != doc and not a.dry_run:
            io.open(p, "w", encoding="utf-8", newline="").write(new)
    if not a.dry_run:
        io.open(OUT, "w", encoding="utf-8", newline="\n").write(
            json.dumps(dict(sorted(arch.items())), indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    print(f"_fda_action_archive.json: {k} FDA action day(s) recorded from the census; {kept} already held "
          f"(all agree); {skipped} left out" + (" [dry run]" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
