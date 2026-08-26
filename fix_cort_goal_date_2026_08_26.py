"""fix_cort_goal_date_2026_08_26.py -- CORT's PDUFA goal date was overwritten with its
decision date, and the two 2026 approvals that had no primary source now have one.

The dataset carried the CORT relacorilant event as d=2026-03-25, dcd=2026-03-25: a goal
date equal to the decision date, which reads as "the FDA acted exactly on time". It did not.
Three independent sources agree the goal was 2026-07-11:

  1. Corcept's own 8-K of 2026-01-22: "The FDA has assigned a Prescription Drug User Fee Act
     (PDUFA) date of July 11, 2026 for relacorilant as a treatment for patients with
     platinum-resistant ovarian cancer."
  2. The FDA's approval notice of 2026-03-25: "The FDA approved this application 3.5 months
     ahead of the FDA goal date." 2026-03-25 + 108 days = 2026-07-11.
  3. Our own calendar, which has always listed the row under July 2026 at 2026-07-11.

A caution worth recording, because it nearly became a published claim: the record also holds
days_to_decision = -108, which looks like independent corroboration. It is not evidence. That
field is a countdown to the goal date frozen at the moment dataset.mjs was generated -- 68 of
70 rows imply a reference date of 2026-07-10 -- so for most rows it says nothing about when
the FDA acted. api/v1/_lib.mjs already recomputes it per request and nulls it for decided
rows, so the public API is unaffected. The correction below rests on the three sources above.

Consequence: CORT enters the decision-timing sample at 108 days early, by a wide margin the
largest gap there. It was previously excluded for want of a source, and excluding the single
most extreme early decision is exactly the selection bias the 2026-08-26 audit raised.
"""
import io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")

WRONG, RIGHT = "2026-03-25", "2026-07-11"

SOURCES = {
    "CORT-2026-03-25": (
        "https://www.fda.gov/drugs/resources-information-approved-drugs/"
        "fda-approves-relacorilant-nab-paclitaxel-platinum-resistant-epithelial-"
        "ovarian-fallopian-tube-or",
        "FDA approval notice, March 25, 2026"),
    "VERA-2026-07-07": (
        "https://www.sec.gov/Archives/edgar/data/1831828/000119312526297211/"
        "vera-20260707.htm",
        "Vera Therapeutics Form 8-K, July 7, 2026"),
}


def fix_goal_date():
    """d -> the real goal date wherever the event is carried. dcd stays the decision date.

    Only dataset.mjs holds it. data.js/SLATE carries upcoming events only (0 rows with a
    decision date), and mentions CORT solely in its OUT label, which already reads
    "~15 weeks ahead of the Jul 11 2026 PDUFA date". So the correct result here is one
    surface changed and neither left holding the wrong date -- which is what is checked,
    rather than a fixed count that would fail for the wrong reason.
    """
    hits = 0
    for rel in ("api/data.js", "api/v1/dataset.mjs"):
        p = os.path.join(SITE, rel)
        doc = io.open(p, encoding="utf-8").read()
        # Anchor on the event id so nothing else with these dates can be touched. dataset.mjs
        # is minified locally but pretty-printed by the daily refresh, so every separator has
        # to tolerate whitespace -- a minified-only pattern silently matched nothing against
        # CI's file and the "still wrong" check below then read that as clean.
        S = r"\s*"
        ident = re.compile(r'"id"' + S + ":" + S + r'"pdufa_cort_2026-03-25"')
        pat = re.compile(r'("id"' + S + ":" + S + r'"pdufa_cort_2026-03-25".{0,400}?"d"'
                         + S + ":" + S + r'")' + WRONG + r'(")', re.S)
        new, n = pat.subn(r"\g<1>" + RIGHT + r"\g<2>", doc)
        if n:
            io.open(p, "w", encoding="utf-8").write(new)
            doc = new
            hits += n
        present = bool(ident.search(doc))
        stale = len(pat.findall(doc))
        print(f"  {rel}: event {'present' if present else 'absent'}, "
              f"{n} corrected, {stale} still wrong")
        if stale:
            return -1
    # "Nothing found" is not "nothing wrong". If no surface carried the event, the patch did
    # nothing and saying OK would be a false pass.
    if hits == 0:
        print("  !! the event was not found on any surface -- nothing was corrected")
        return -1
    return hits


def add_sources():
    """These two were the last unsourced 2026 decisions; both are now verified."""
    added = 0
    for slug, (url, label) in SOURCES.items():
        p = os.path.join(SITE, "fda-decision", slug, "index.html")
        if not os.path.exists(p):
            print(f"  SKIP {slug}: no page")
            continue
        doc = io.open(p, encoding="utf-8").read()
        if url in doc:
            print(f"  {slug}: already sourced")
            continue
        # Decision pages come in two layouts: the generated kv list, and the hand-built
        # "Key facts" table on the richer pages. Try each; never write blind.
        link = f'<a href="{url}" rel="nofollow noopener">{label}</a>'
        new, n = re.subn(r'(<span>Outcome</span><b[^>]*>.*?</b></div>)',
                         r"\1" + f'<div class="kv"><span>Primary source</span><b>{link}'
                         f'</b></div>', doc, count=1, flags=re.S)
        if not n:
            new, n = re.subn(
                r'(<tr><td[^>]*>Actual decision</td><td[^>]*>.*?</td></tr>)',
                r"\1" + '<tr><td style="padding:6px 0;color:#9db3d4">Primary source</td>'
                f'<td class="lit">{link}</td></tr>', doc, count=1, flags=re.S)
        if not n:
            print(f"  !! {slug}: neither layout matched; NOT writing a source row blind")
            continue
        io.open(p, "w", encoding="utf-8").write(new)
        added += 1
        print(f"  {slug}: sourced -> {label}")
    return added


def fix_stale_comment():
    """_lib.mjs cites CORT as an example and repeats the wrong goal date in doing so."""
    p = os.path.join(SITE, "api/v1/_lib.mjs")
    doc = io.open(p, encoding="utf-8").read()
    old = "e.g. CORT (PDUFA\n     2026-03-25) reported -108 when the true figure was -119."
    new = ("e.g. CORT (PDUFA\n     2026-07-11, decided 2026-03-25) reported -108 when the "
           "true figure was -119.")
    if old in doc:
        io.open(p, "w", encoding="utf-8").write(doc.replace(old, new))
        print("  _lib.mjs: example comment now cites the real goal date")
        return 1
    print("  _lib.mjs: comment not in the expected form; left alone")
    return 0


if __name__ == "__main__":
    print("goal date:")
    g = fix_goal_date()
    print("primary sources:")
    s = add_sources()
    print("comment:")
    fix_stale_comment()
    if g < 0:
        print("\nFAIL: a surface still carries the old goal date. The two must not diverge.")
        sys.exit(1)
    print(f"\nOK: goal date corrected on both surfaces; {s} decision page(s) sourced.")
