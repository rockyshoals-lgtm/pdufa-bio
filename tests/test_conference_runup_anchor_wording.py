"""CI guard (red team 2026-11-26): the conference run-up study must describe its anchor truthfully.

The study said every figure was "anchored on the meeting start date". The rows say otherwise: each
anchor is the day that row's data became public for the meeting, the abstract release for some
meetings and the presentation day for others. This guard keeps the false wording off every page and
checks that the study page states the audit counts computed from the CSV (never typed).

PLANT=1 puts the old sentence back into a copy of a page and must make this guard fail.
"""
import glob, io, os, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import conference_runup_facts as crf  # noqa: E402

SITE = os.path.join(HERE, "pdufa_site_src")
BANNED = ("anchored on the meeting start date", "anchored on the conference start date",
          "last daily close before the conference start date",
          # the anchor is not always the meeting or the presentation (red team 2026-11-26, round 2)
          "trading days before the meeting", "price move on the presentation day",
          ">presentation day</span>", "presentation day itself",
          # the study does not show this pattern (30-day median about flat, nano caps negative)
          "drift up into these meetings", "drifted <b>up into</b>")
fail = []

pages = {}
for p in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
    t = io.open(p, encoding="utf-8", errors="replace").read()
    if "conference" in p or "research" in p or "anchored" in t:
        pages[p] = t
csvp = os.path.join(SITE, "research", "conference-runup", "conference-runup-study.csv")
if os.path.exists(csvp):
    pages[csvp] = io.open(csvp, encoding="utf-8", errors="replace").read(600)

study = os.path.join(SITE, "research", "conference-runup", "index.html")
if os.environ.get("PLANT") == "1":
    pages[study] = pages.get(study, "") + " The study is anchored on the meeting start date."
    conf_page = next((p for p in pages if os.sep + "conference" + os.sep in p), None)
    if conf_page:
        pages[conf_page] += " Stocks drift up into these meetings."

for p, t in pages.items():
    low = t.lower()
    for b in BANNED:
        if b in low:
            fail.append(f"{os.path.relpath(p, HERE)} still says '{b}'")

a = crf.anchor_audit()
s = pages.get(study, "")
if crf.ANCHOR_CAVEAT not in s:
    fail.append("study page lacks the current anchor caveat (run augment_conference_study.py)")
if crf.audit_sentence(a) not in s:
    fail.append("study page lacks the computed anchor-audit sentence (run augment_conference_study.py)")

if fail:
    for f in fail[:20]:
        print("  FAIL", f)
    print(f"FAIL: {len(fail)} anchor-wording problem(s)")
    sys.exit(1)
print(f"OK -- anchor described as the catalyst-history date; audit: {a['far']} far rows, {a['unknown']} unnamed, "
      f"{len(pages)} files checked")
