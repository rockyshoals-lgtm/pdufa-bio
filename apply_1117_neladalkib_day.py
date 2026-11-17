# -*- coding: utf-8 -*-
"""apply_1117_neladalkib_day.py -- 2026-11-17 currency audit: neladalkib's goal DAY is sourced; restore it.

The 2026-10-10 ruling (apply_1010_neladalkib_month.py) moved neladalkib to month precision because the
only day we held came second-hand (a Royalty Pharma 8-K quoting Nuvalent) and GSK's Q2 6-K said only
"anticipated in November 2026". The ledger rule is: a withdrawn day may come back, but only with a source.

The source is the applicant's own announcement, read 2026-11-17 (Nuvalent press release, 2026-05-27,
"Nuvalent Announces Key Program and Business Updates..."):
  "The application has been granted Priority Review and assigned a PDUFA target action date of
   November 27, 2026."
Nuvalent was the NDA applicant when the FDA assigned the date; a change of corporate owner does not
change an FDA goal date. GSK's later 6-K ("PDUFA date anticipated in November 2026") is consistent with it
and is kept as the current sponsor's confirmation. No newer statement moves the date. Facts only; not
investment advice. Idempotent.
"""
import io, json, os, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "pdufa_site_src", "api", "v1", "dataset.mjs")
NUV = ("https://investors.nuvalent.com/2026-05-27-Nuvalent-Announces-Key-Program-and-Business-Updates,"
       "-Strengthening-Foundation-for-Global-Leadership-in-ROS1-and-ALK-positive-NSCLC")
SIXK = "https://www.sec.gov/Archives/edgar/data/1131399/000165495426006949/a1493o.htm"
QUOTE = ("The application has been granted Priority Review and assigned a PDUFA target action date of "
         "November 27, 2026.")

s = io.open(P, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = s.index("["), s.rindex("]") + 1
rows = json.loads(s[i:j])
r = next(x for x in rows if x["id"] == "pdufa_nuvl_2026-11-27")
d = r["_d"]
if r.get("dp") != "day":
    d.setdefault("date_history", []).append({
        "date": "2026-11-27", "precision": "day", "changed": "2026-11-17",
        "source": "Nuvalent press release 2026-05-27 (NDA acceptance)", "source_url": NUV,
        "why": ("Day restored: the applicant's own announcement states 'assigned a PDUFA target action date of "
                "November 27, 2026'. GSK's 6-K 2026-07-28 lists neladalkib as 'PDUFA H2 2026', "
                "consistent with it, and is kept as the current sponsor's confirmation.")})
    r["d"], r["dp"] = "2026-11-27", "day"
    r.pop("dm", None)
    d["source"] = "Nuvalent press release 2026-05-27 (NDA acceptance; Nuvalent was the applicant, acquired by GSK 2026-07-15)"
    d["source_url"] = NUV
    d["source_quote"] = QUOTE
    d["confirming_source"] = "GSK plc 6-K 2026-07-28 (Q2 2026 results): neladalkib listed as 'PDUFA H2 2026'"
    d["confirming_source_url"] = SIXK
    d["source_note"] = ("Goal day from the applicant's own release; the current sponsor (GSK) lists the decision in H2 2026. "
                        "Month precision 2026-10-10 to 2026-11-17; see date_history.")
    d.pop("date_note", None)
    d.pop("runup_note", None)
    r["ua"] = "2026-11-17T12:00:00Z"
    print("  pdufa_nuvl_2026-11-27: day 2026-11-27 restored, source Nuvalent 2026-05-27 release")
else:
    print("  already day precision")
io.open(P, "w", encoding="utf-8").write(s[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + s[j:])

# ledger: the withdrawal stays on record, marked restored with its source (the guard requires a source_url)
LED = os.path.join(HERE, "_unsourced_day_dates.json")
led = json.load(io.open(LED, encoding="utf-8"))
for e in led["rows"]:
    if e.get("ticker") == "GSK" and e.get("was_date") == "2026-11-27" and not e.get("restored"):
        e["restored"] = {"on": "2026-11-17", "source_url": NUV,
                         "why": "applicant's own release states the day; row is day precision again with that source"}
        io.open(LED, "w", encoding="utf-8", newline="\n").write(json.dumps(led, indent=1, ensure_ascii=False) + "\n")
        print("  _unsourced_day_dates.json: GSK 2026-11-27 marked restored")

# homepage slate: the real day replaces the month-end sentinel
SL = os.path.join(HERE, "pdufa_site_src", "api", "data.js")
t = io.open(SL, encoding="utf-8").read()
k = t.find("const SLATE=") + len("const SLATE=")
slate, end = json.JSONDecoder().raw_decode(t[k:])
ch = 0
for c in slate["catalysts"]:
    if c.get("ticker") == "GSK" and "eladalkib" in json.dumps(c) and str(c.get("date")) != "2026-11-27":
        c["date"] = "2026-11-27"; c["t_minus"] = c.get("t_minus", 13) - 3; ch += 1
if ch:
    io.open(SL, "w", encoding="utf-8").write(t[:k] + json.dumps(slate, ensure_ascii=False, separators=(",", ":")) + t[k + end:])
    print("  api/data.js SLATE: GSK neladalkib date -> 2026-11-27")

# calendar: the "GSK · Nov 2026" neladalkib row becomes "GSK · 2026-11-27" (its own text kept) and moves into day order
ROWRE = re.compile(r'<a class="row"(?:(?!</a>).)*?<div class="t">GSK (?:&middot;|·) Nov 2026</div>\s*<div class="d">'
                   r'[^<]*[Nn]eladalkib(?:(?!</a>).)*</a>', re.S)
for cp in (os.path.join(HERE, "pdufa_site_src", "calendar", "index.html"),
           os.path.join(HERE, "pdufa_site_src", "calendar", "2026", "november", "index.html")):
    doc = io.open(cp, encoding="utf-8", errors="replace").read()
    m = ROWRE.search(doc)
    if not m:
        continue
    row = re.sub(r"GSK (&middot;|·) Nov 2026", r"GSK \1 2026-11-27", m.group(0), count=1)
    doc = doc[:m.start()] + doc[m.end():]
    nxt = next((x for x in re.finditer(r'<a class="row"[^>]*>\s*<div class="t">[A-Z./ ]+\s*(?:&middot;|·)\s*'
                                        r'(\d{4}-\d{2}-\d{2})', doc) if x.group(1) > "2026-11-27"), None)
    at = nxt.start() if nxt else m.start()
    doc = doc[:at] + row + doc[at:]
    io.open(cp, "w", encoding="utf-8", newline="").write(doc)
    print(f"  {os.path.relpath(cp, HERE)}: GSK neladalkib row -> 2026-11-27, placed in day order")
