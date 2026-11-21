# -*- coding: utf-8 -*-
"""apply_1121_currency.py -- the currency pass of 2026-11-21 (round 4): three decisions the site did not yet show.

Read 2026-11-21 between 13:00 and 14:30 UTC (08:00-09:30 Eastern, 05:00-06:30 Pacific; RULE 1), each page itself:

1. CAPR deramiocel: Capricor release on GlobeNewswire, dateline "SAN DIEGO, Nov. 20, 2026", header time 19:55 ET
   (00:55 UTC Nov 21). Capricor "today announced that it received a Complete Response Letter (CRL)" on its resubmitted
   BLA for deramiocel in Duchenne muscular dystrophy; the CRL "states that the FDA does not consider the data
   sufficient to establish substantial evidence of effectiveness and cites certain other clinical deficiencies."
   The release does not state the letter's own date: announcement day, no FDA day, no margin. Goal date was
   November 22, 2026 (moved from August 22 after a major amendment; Capricor, August 24, 2026, already on the row).
   Conference call Monday, November 23, 8:30 a.m. ET. Second CRL: the first is /fda-decision/CAPR-2025-07-11.
2. AZN Klygefa (gefurulimab-gaks): FDA approval letter BLA 761488, read in full: indicated for generalized
   myasthenia gravis in adults who are anti-AChR antibody positive; BLA received November 13, 2025; REMS approved
   (serious meningococcal infections); signed 11/13/2026. AstraZeneca release "PUBLISHED 16 November 2026"
   announced the US approval (once-weekly subcutaneous autoinjector; PREVAIL, 260 patients, MG-ADL treatment
   difference -1.6 at week 26, p<0.0001). The page is keyed on the announcement day (AZN-2026-11-13 is already the
   Imfinzi page) and carries the FDA's own day, November 13, as the decision date (the JUVMO and SMMT shape). No
   sponsor-disclosed goal date exists, so no margin. /pdufa/AZN-gefurulimab was bannered with an unrelated
   February 20 approval (Calquence) and its story described Truqap; a hand link now names Klygefa's decision.
3. SVRA molgramostim: Savara release on Business Wire, November 20, 2026 8:30 AM ET: the FDA informed Savara that it
   will not take action on the BLA by the November 22 PDUFA date and the review is ongoing. The goal-date ledger
   carries this as an announced miss; the row stays pending (it is pending).
Facts only; not investment advice.
"""
import datetime as dt
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
A = 'rel="noopener" style="color:#e3ba5e"'

CAPR_REL = ("https://www.globenewswire.com/news-release/2026/11/21/3407877/0/en/capricor-therapeutics-provides-"
            "regulatory-update-on-deramiocel-bla-for-duchenne-muscular-dystrophy.html")
CAPR_EXT = ("https://www.globenewswire.com/news-release/2026/08/24/3349793/0/en/capricor-therapeutics-announces-"
            "extension-of-pdufa-target-action-date-as-fda-continues-review-of-deramiocel-bla.html")
AZN_L = "https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/761488Orig1s000ltr.pdf"
AZN_R = "https://www.astrazeneca.com/media-centre/press-releases/2026/klygefa-gefurulimab-approved-in-the-US.html"
SVRA_R = ("https://www.businesswire.com/news/home/20261120300122/en/Savara-Informed-That-FDA-Will-Not-Take-Action-on-"
          "the-Molgramostim-BLA-for-Autoimmune-Pulmonary-Alveolar-Proteinosis-Autoimmune-PAP-by-the-PDUFA-Date/")

# FMP historical-price-eod, read 2026-11-21 ~13:30 UTC; Eastern trading days. Oct 15-16 match the cache (7.27, 6.71).
CAPR_CLOSES = {"2026-10-19": 6.65, "2026-10-20": 6.61, "2026-10-21": 5.88, "2026-10-22": 6.13, "2026-10-23": 5.93,
               "2026-10-26": 5.74, "2026-10-27": 6.1, "2026-10-28": 6.23, "2026-10-29": 6.63, "2026-10-30": 6.38,
               "2026-11-02": 7.24, "2026-11-03": 8.24, "2026-11-04": 8.92, "2026-11-05": 8.6, "2026-11-06": 9.0,
               "2026-11-09": 9.85, "2026-11-10": 8.87, "2026-11-11": 11.22, "2026-11-12": 10.24, "2026-11-13": 9.53,
               "2026-11-16": 8.3, "2026-11-17": 8.41, "2026-11-18": 8.03, "2026-11-19": 7.53, "2026-11-20": 7.59}


def jload(p, default=None):
    p = os.path.join(HERE, p)
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else default


def jsave(p, d):
    io.open(os.path.join(HERE, p), "w", encoding="utf-8").write(json.dumps(d, indent=1, ensure_ascii=False) + "\n")


def rd(p):
    return io.open(p, encoding="utf-8", errors="replace").read()


def wr(p, s):
    io.open(p, "w", encoding="utf-8").write(s)


# ---------------------------------------------------------------- 1. CAPR: dataset row -> Decided / CRL
src = rd(DATASET)
i, j = src.index("["), src.rindex("]") + 1
rows = json.loads(src[i:j])
asc = src[i:j] == json.dumps(rows, indent=1, ensure_ascii=True)
r = next(x for x in rows if x["id"] == "pdufa_capr_2026-08-22")
assert r.get("d") == "2026-11-22" and r.get("dp") == "day", "CAPR goal changed; re-verify before publishing"
if r.get("st") != "Decided":
    r.update({"st": "Decided", "oc": "CRL", "dcd": "2026-11-20", "url": "/fda-decision/CAPR-2026-11-20", "ua": NOW})
    d = r.setdefault("_d", {})
    d.update({
        "decision_source": "Capricor Therapeutics press release, November 20, 2026 (GlobeNewswire, 7:55 PM ET)",
        "decision_source_url": CAPR_REL, "decision_date_unsourced": True,
        "announcement": "Capricor Therapeutics press release, November 20, 2026 (GlobeNewswire, 7:55 PM ET)",
        "announcement_url": CAPR_REL,
        "decision_quote": ("Capricor Therapeutics (NASDAQ: CAPR) ... today announced that it received a Complete Response "
                           "Letter (CRL) from the U.S. Food and Drug Administration (FDA) for its resubmitted Biologics "
                           "License Application (BLA) for Deramiocel"),
        "decision_note": ("Per Capricor, the CRL states that the FDA does not consider the data sufficient to establish "
                          "substantial evidence of effectiveness and cites certain other clinical deficiencies. The "
                          "release does not state the letter's own date; the date shown is Capricor's announcement "
                          "(the evening of Friday November 20, two days before the November 22 goal date), so no early "
                          "or late margin is stated. This is the second CRL for deramiocel; the first was announced "
                          "July 11, 2025."),
    })
    print("  pdufa_capr_2026-08-22: Decided / CRL, announced 2026-11-20 -> /fda-decision/CAPR-2026-11-20")
wr(DATASET, src[:i] + json.dumps(rows, indent=1, ensure_ascii=asc) + src[j:])

# ---------------------------------------------------------------- 2. decision pages (CAPR CRL, AZN Klygefa)
SPECS = [
    {
        "ticker": "CAPR", "date": "2026-11-20", "outcome": "CRL",
        "drug": "Deramiocel (CAP-1002)",
        "indication": "Duchenne muscular dystrophy (resubmitted BLA; HOPE-3)",
        "company": "Capricor Therapeutics Inc.", "cap": "Small",
        "headline": ("Capricor announced on November 20, 2026 that it received a Complete Response Letter on its "
                     "resubmitted BLA for deramiocel in Duchenne muscular dystrophy; the goal date was November 22, and "
                     "the release does not date the letter."),
        "pdufa_note": (f'Capricor announced on the evening of November 20, 2026 (7:55 PM ET) that it received a Complete '
                       f'Response Letter for its resubmitted BLA for deramiocel, its cell therapy for Duchenne muscular '
                       f'dystrophy (<a href="{CAPR_REL}" {A}>Capricor\'s announcement</a>). Per Capricor, the letter '
                       f'states that the FDA does not consider the data sufficient to establish substantial evidence of '
                       f'effectiveness and cites certain other clinical deficiencies; Capricor said it is reviewing the '
                       f'letter and will share next steps after its evaluation. The PDUFA goal date was November 22, '
                       f'2026, moved from August 22 after a major amendment to the application (<a href="{CAPR_EXT}" {A}>'
                       f'Capricor, August 24, 2026</a>). The release does not state the letter\'s own date, so no early or '
                       f'late margin is given. This is deramiocel\'s second Complete Response Letter; the first was '
                       f'announced on July 11, 2025 (<a href="/fda-decision/CAPR-2025-07-11" style="color:#e3ba5e">'
                       f'CAPR, July 11, 2025</a>). A Complete Response Letter means the FDA will not approve the '
                       f'application in its present form; the sponsor can resubmit.'),
        "source": CAPR_REL, "source_label": "Capricor Therapeutics press release, November 20, 2026",
    },
    {
        "ticker": "AZN", "date": "2026-11-16", "fda_action_date": "2026-11-13", "outcome": "Approved",
        "drug": "Klygefa (gefurulimab-gaks)",
        "indication": "Generalized myasthenia gravis in adults who are anti-AChR antibody positive",
        "company": "AstraZeneca PLC (Alexion)", "cap": "Large",
        "headline": ("The FDA approved Klygefa (gefurulimab-gaks) on November 13, 2026 for adults with generalized "
                     "myasthenia gravis who are anti-acetylcholine receptor antibody positive; AstraZeneca announced "
                     "the approval on November 16."),
        "pdufa_note": (f'The FDA\'s approval letter for BLA 761488, signed November 13, 2026 (<a href="{AZN_L}" {A}>FDA '
                       f'letter</a>), covers Klygefa (gefurulimab-gaks) for adults with generalized myasthenia gravis who '
                       f'are anti-acetylcholine receptor (AChR) antibody positive. The letter states that the application '
                       f'was received on November 13, 2025, and it approves a REMS because of the risk of serious '
                       f'meningococcal infections. AstraZeneca announced the approval on November 16, 2026 and describes '
                       f'once-weekly subcutaneous self-administration by autoinjector (<a href="{AZN_R}" {A}>AstraZeneca, '
                       f'November 16, 2026</a>). Per AstraZeneca, in the Phase III PREVAIL trial (260 patients) the MG-ADL '
                       f'total score improved more than with placebo at week 26 (treatment difference -1.6, p&lt;0.0001). '
                       f'We hold no publicly disclosed PDUFA goal date for this application, so no early or late margin '
                       f'is given.'),
        "source": AZN_L, "source_label": "FDA approval letter, BLA 761488, November 13, 2026",
    },
]
jsave("decision_pages_2026_11_21_currency.json", SPECS)

faq = jload("_decision_extra_faq.json", {})
faq["CAPR-2026-11-20"] = [
    ["Was deramiocel approved by the FDA?",
     "No. Capricor announced on November 20, 2026 that the FDA issued a Complete Response Letter on its resubmitted BLA "
     "for deramiocel in Duchenne muscular dystrophy. Per Capricor, the FDA does not consider the data sufficient to "
     "establish substantial evidence of effectiveness and cites certain other clinical deficiencies."],
    ["Was the deramiocel decision before the PDUFA date?",
     "Capricor announced the letter on November 20, two days before the November 22, 2026 goal date. Its release does "
     "not state the letter's own date, so pdufa.bio does not state an early or late margin."],
    ["Is this the first CRL for deramiocel?",
     "No. Capricor announced an earlier Complete Response Letter for deramiocel on July 11, 2025, and then resubmitted "
     "the application."]]
faq["AZN-2026-11-16"] = [
    ["Is gefurulimab approved by the FDA?",
     "Yes. The FDA approved Klygefa (gefurulimab-gaks) on November 13, 2026 for adults with generalized myasthenia "
     "gravis who are anti-acetylcholine receptor antibody positive (BLA 761488). AstraZeneca announced it on November "
     "16, 2026."],
    ["How is Klygefa given?",
     "Per AstraZeneca, Klygefa is self-administered under the skin once a week with an autoinjector. The FDA letter "
     "approves a REMS because of the risk of serious meningococcal infections."],
    ["Was the Klygefa decision early or late?",
     "pdufa.bio holds no publicly disclosed PDUFA goal date for this application, so no margin is given. The FDA letter "
     "states that the application was received on November 13, 2025."]]
jsave("_decision_extra_faq.json", faq)

fa = jload("_fda_action_archive.json", {})
if not (fa.get("AZN-2026-11-16") or {}).get("date"):
    fa["AZN-2026-11-16"] = {"checked": "2026-11-21", "class": "TYPE 1", "date": "2026-11-13", "letter": AZN_L,
                            "name": "Klygefa (gefurulimab-gaks)", "record": "BLA 761488 ORIG-1", "source_url": AZN_L,
                            "terms": ["Klygefa", "gefurulimab"]}
jsave("_fda_action_archive.json", fa)

PX = os.path.join(HERE, "_chart_pxcache.json")
px = json.load(open(PX))
for dd, cl in CAPR_CLOSES.items():
    px.setdefault("CAPR", {}).setdefault(dd, cl)
json.dump(px, open(PX, "w"))
import build_decision_page as bdp  # noqa: E402
for e in SPECS:
    bdp.build(e, px)

# ---------------------------------------------------------------- 3. /pdufa/AZN-gefurulimab: hand link + true story
hl = jload("_event_page_decisions.json")
if not any(x.get("slug") == "AZN-gefurulimab" for x in hl["links"]):
    hl["links"].append({
        "slug": "AZN-gefurulimab", "decision": "AZN-2026-11-16", "fda_action_date": "2026-11-13", "brand": "Klygefa",
        "reviewer": "builder 2026-11-21",
        "why": ("The automatic archive fallback had bannered this page with AZN-2026-02-20 (CALQUENCE with venetoclax, an "
                "unrelated application). This page is gefurulimab in generalized myasthenia gravis; the FDA approved it "
                "as Klygefa on November 13, 2026 (BLA 761488 letter) and AstraZeneca announced it on November 16."),
        "source": AZN_L})
    jsave("_event_page_decisions.json", hl)
P = os.path.join(SITE, "pdufa", "AZN-gefurulimab", "index.html")
TRUQAP = "advanced breast and other PTEN-altered cancers (the AKT-inhibitor Truqap/capivasertib)"
# The wrong February 20 banner (daily refresh 1eccea1773, Nov 18) rewrote the title, key facts, story and FAQ with the
# decided-page phrasing for AZN-2026-02-20 (an unrelated application). Red team 2026-11-21: restoring the page from
# before that commit lost later site fixes (skip link, mobile rules, countdown fix, cohort figures), so the current
# page (main at 3fc6b096d1) is kept and only the wrong decision is replaced: every "February 20, 2026" carrier becomes
# Klygefa's announcement day (Nov 16), which mark_event_pages_decided.py then restates as the FDA's day (Nov 13) from
# the hand link above, the banner is rebuilt from that link, and the month chip points at November. The story's
# indication was wrong before that too (the one-off story generator's ticker-level AZN text, Truqap).
import subprocess  # noqa: E402
if "AZN-2026-02-20" in rd(P) or "February 20, 2026" in rd(P):
    doc = subprocess.run(["git", "show", "3fc6b096d148ff38aa1cf44420b95654f18ca66a:pdufa_site_src/pdufa/AZN-gefurulimab/index.html"],
                         cwd=HERE, capture_output=True, text=True, check=True).stdout
    assert "Generalised myasthenia gravis" in doc
    doc = re.sub(r"<!--DECBAN:BEGIN-->.*?<!--DECBAN:END-->", "", doc, flags=re.S)
    doc = doc.replace("February 20, 2026", "November 16, 2026").replace("/fda-decision/AZN-2026-02-20", "/fda-decision/AZN-2026-11-16")
    doc = doc.replace('<a href="/calendar/2026/december" style="font-size:13px;color:#cfe2ff;background:#0c1d38;border:1px solid '
                      '#2a496f;border-radius:20px;padding:5px 13px;text-decoration:none;display:inline-block">All December 2026 '
                      'PDUFA dates', '<a href="/calendar/2026/november" style="font-size:13px;color:#cfe2ff;background:#0c1d38;'
                      'border:1px solid #2a496f;border-radius:20px;padding:5px 13px;text-decoration:none;display:inline-block">'
                      'All November 2026 PDUFA dates')
    wr(P, doc)
doc = rd(P)
doc = doc.replace(TRUQAP, "generalized myasthenia gravis (gMG) in adults who are anti-AChR antibody positive")
wr(P, doc)
# the same one-off cross-link generator gave both AZN pages the ticker's oncology chip
CHIP = '<a href="/condition/cancer"'
for slug, cond, lab in (("AZN-gefurulimab", "cns-neurology", "CNS &amp; Neurology"),
                        ("AZN-ultomiris", "immunology", "Immunology &amp; Inflammation")):
    P = os.path.join(SITE, "pdufa", slug, "index.html")
    doc = rd(P)
    m = re.search(r'<a href="/condition/cancer"([^>]*)>More Cancer &amp; Oncology FDA decisions →</a>', doc)
    if m:
        wr(P, doc.replace(m.group(0), f'<a href="/condition/{cond}"{m.group(1)}>More {lab} FDA decisions →</a>'))
        print(f"  /pdufa/{slug}: condition chip -> /condition/{cond}")
P = os.path.join(SITE, "pdufa", "AZN-ultomiris", "index.html")
doc = rd(P)
if TRUQAP in doc:   # same one-off story generator, same ticker-level fallback; the decision page states the indication
    wr(P, doc.replace(TRUQAP, "primary IgA nephropathy in adults at risk of disease progression"))
    print("  /pdufa/AZN-ultomiris: story indication corrected (IgA nephropathy, per /fda-decision/AZN-2026-10-21)")

# calendar: the Q4 (est.) gefurulimab row is no longer a pending window; the decision gets a dated November row
ROW = re.compile(r'<a class="row" href="/pdufa/AZN-gefurulimab"><div class="t">AZN · Q4 2026 \(est\.\)</div>'
                 r'<div class="d">[^<]*</div></a>')
OK = '<span style="color:#5fd07a;font-weight:700">'
DEC = (f'<a class="row" data-dec="1" href="/fda-decision/AZN-2026-11-16"><div class="t">AZN &middot; 2026-11-16 {OK}✓'
       f'</span> &middot; FDA action Nov 13, 2026</div><div class="d">{OK}Approved</span>: Klygefa (gefurulimab-gaks): '
       f'generalized myasthenia gravis</div></a>')


def insert_dated(doc, row, d):
    for m in re.finditer(r'<a class="row"[^>]*>\s*<div class="t">[A-Z./ ]+\s*(?:&middot;|·)\s*(\d{4}-\d{2}-\d{2})', doc):
        if m.group(1) > d:
            return doc[:m.start()] + row + doc[m.start():]
    return doc


for rel in ("calendar/index.html", "calendar/2026/november/index.html"):
    p = os.path.join(SITE, rel)
    d0 = d = rd(p)
    d = ROW.sub("", d)
    if "/fda-decision/AZN-2026-11-16" not in d:
        d = insert_dated(d, DEC, "2026-11-16")
    if d != d0:
        wr(p, d)
        print(f"  {rel}: gefurulimab Q4 row retired, Klygefa decided row added")

UB = os.path.join(HERE, "_calendar_unbacked_q4_rows.json")
ub = json.load(io.open(UB, encoding="utf-8"))
ub["rows"] = [x for x in ub["rows"] if x.get("page") != "/pdufa/AZN-gefurulimab"]
if len(ub["rows"]) < ub.get("baseline_count", 99):
    ub["baseline_count"] = len(ub["rows"])
    ub["baseline_note"] += (f" Lowered to {len(ub['rows'])} on 2026-11-21: gefurulimab was approved (Klygefa, FDA letter "
                            "BLA 761488, November 13, 2026; AstraZeneca, November 16).")
io.open(UB, "w", encoding="utf-8").write(json.dumps(ub, indent=1, ensure_ascii=False) + "\n")

# ---------------------------------------------------------------- 4. SVRA: the FDA said it will not act by the goal
led = jload("_goal_date_passed.json")
if not any(e.get("slug") == "SVRA-molbreevi" for e in led["passed"]):
    led["passed"].append({
        "slug": "SVRA-molbreevi", "goal_date": "2026-11-22", "application_type": "BLA",
        "announced_miss_date": "2026-11-20",
        "announced_miss_text": ("Savara said the FDA informed it that the agency will not take action on the BLA for "
                                "MOLBREEVI (molgramostim) in autoimmune pulmonary alveolar proteinosis by that date, and "
                                "that the review is ongoing."),
        "source": SVRA_R, "source_label": "Savara release, November 20, 2026",
        "reviewer": "builder 2026-11-21 (release read 13:20 UTC)"})
    jsave("_goal_date_passed.json", led)
print("apply_1121_currency: done")

# CAPR event page: the Aug 24 extension note said "the application remains under review". The review has since ended
# in a CRL (Capricor, Nov 20, 2026), so the note is put in the past tense.
p = os.path.join(SITE, "pdufa", "CAPR-deramiocel", "index.html")
d0 = d = rd(p)
d = d.replace("<b>This is an extension, not a Complete Response Letter:</b> the application remains under review.",
              "<b>This was an extension, not a Complete Response Letter.</b> The review that followed ended in a "
              "Complete Response Letter, announced by Capricor on 2026-11-20.")
if d != d0:
    wr(p, d)
    print("  pdufa/CAPR-deramiocel: extension note set to past tense")
