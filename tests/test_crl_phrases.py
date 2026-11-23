# -*- coding: utf-8 -*-
"""CI guard: /crl/phrases and /crl/phrase/<slug> (build_crl_phrases.py) count what the released CRLs' text says.

  * The terms and their forms are the list below (EXPECTED), written out here by hand, and each term's pattern here is
    also written by hand (OWN), not taken from the builder. Known snippets from real letters must hit or miss.
  * For every term, the letters counted are exactly the letters whose released text (read here from the raw corpus)
    matches OWN: the index row's counts and the term page's rows.
  * The index: one row per term, keyed by its link, no unknown or repeated rows; each row's term, forms and counts;
    the lede, the most-frequent sentence and the release make-up sentence recounted.
  * Each term page: title, description, h1, lede and second sentence exact; every row's date, application, company,
    status, letter link (to a page that exists), PDF and rescinded mark; the canonical.
  * Each letter page's "terms" line names exactly the terms its text contains, by link and by label.
  * No forecast words and no words that give a reason or an outcome in the pages' own words (head and body).

PLANT=1 drops one letter from the recount and must FAIL; PLANT=2 widens one term's pattern and must FAIL.

    python tests/test_crl_phrases.py      (fix: python build_crl_phrases.py, then build_crl_letters.py)
"""
import collections
import datetime as dt
import hashlib
import html
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")
MONTHS = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
BAD = re.compile(r"\b(probabilit|odds\b|chances?\b|likel[yi]|predict|forecast|because|caused?\b|due to|led to"
                 r"|reject|reason|fail|deficien|signal|will be approved)", re.I)
S = r"[\s/-]*"          # what may stand between a form's words

# (slug, term, forms as the page states them, the pattern written by hand)
EXPECTED = [
    ("form-fda-483", "Form FDA 483", ["Form FDA 483", "FDA Form 483", "Form 483", "FDA 483"],
     rf"\bform{S}fda{S}483\b|\bfda{S}form{S}483\b|\bform{S}483\b|\bfda{S}483\b"),
    ("pre-approval-inspection", "pre-approval or pre-license inspection",
     ["pre-approval inspection", "pre-license inspection", "pre-licensure inspection", "PAI", "PLI"],
     rf"\bpre{S}(?:approval|license|licensure){S}inspection\b|\bPAI\b|\bPLI\b"),
    ("adequate-and-well-controlled", "adequate and well-controlled", ["adequate and well-controlled"],
     rf"\badequate{S}and{S}well{S}controlled\b"),
    ("substantial-evidence-of-effectiveness", "substantial evidence of effectiveness",
     ["substantial evidence of effectiveness"], rf"\bsubstantial{S}evidence{S}of{S}effectiveness\b"),
    ("post-hoc", "post hoc", ["post hoc"], rf"\bpost{S}hoc\b"),
    ("statistical-analysis-plan", "statistical analysis plan", ["statistical analysis plan"],
     rf"\bstatistical{S}analysis{S}plan\b"),
    ("bioequivalence", "bioequivalence", ["bioequivalen..."], r"\bbioequivalen"),
    ("human-factors", "human factors", ["human factor..."], rf"\bhuman{S}factor"),
    ("rems", "REMS (Risk Evaluation and Mitigation Strategy)", ["Risk Evaluation and Mitigation Strateg...", "REMS"],
     rf"\brisk{S}evaluation{S}and{S}mitigation{S}strateg|\bREMS\b"),
    ("carcinogenicity", "carcinogenicity", ["carcinogenicity"], r"\bcarcinogenicity\b"),
    ("immunogenicity", "immunogenicity", ["immunogenicity"], r"\bimmunogenicity\b"),
    ("qt", "QT interval or QTc", ["QTc", "QT interval", "thorough QT", "QT prolongation"],
     rf"\bQTc\b|\bQT{S}interval\b|\bthorough{S}QT\b|\bQT{S}prolongation\b"),
    ("liver-injury", "drug-induced liver injury or hepatotoxicity", ["drug-induced liver injury", "hepatotoxicity"],
     rf"\bdrug{S}induced{S}liver{S}injury\b|\bhepatotoxicity\b"),
    ("stability-data", "stability data", ["stability data"], rf"\bstability{S}data\b"),
    ("impurities", "impurities", ["impurit..."], r"\bimpurit"),
    ("container-closure", "container closure", ["container closure"], rf"\bcontainer{S}closure\b"),
    ("extractables-and-leachables", "extractables and leachables",
     ["extractable... and leachable...", "leachable... and extractable..."],
     rf"\bextractable\w*{S}and{S}leachable|\bleachable\w*{S}and{S}extractable"),
    ("sterility", "sterility", ["sterility"], r"\bsterility\b"),
    ("microbiology", "microbiology", ["microbiology"], r"\bmicrobiology\b"),
    ("dissolution", "dissolution", ["dissolution"], r"\bdissolution\b"),
    ("drug-master-file", "drug master file (DMF)", ["drug master file...", "DMF", "DMFs"],
     rf"\bdrug{S}master{S}file|\bDMFs?\b"),
    ("device-constituent", "device constituent", ["device constituent..."], rf"\bdevice{S}constituent"),
    ("biosimilar", "biosimilar or interchangeable", ["biosimilar...", "interchangeab..."],
     r"\bbiosimilar|\binterchangeab"),
    ("comparability", "comparability", ["comparability"], r"\bcomparability\b"),
    ("accelerated-approval", "accelerated approval", ["accelerated approval"], rf"\baccelerated{S}approval\b"),
    ("confirmatory-trial", "confirmatory trial or study", ["confirmatory trial...", "confirmatory stud..."],
     rf"\bconfirmatory{S}(?:trial|stud)"),
    ("advisory-committee", "advisory committee", ["advisory committee"], rf"\badvisory{S}committee\b"),
    ("end-of-review-meeting", "end-of-review meeting or conference",
     ["end-of-review meeting", "end-of-review conference"], rf"\bend{S}of{S}review{S}(?:meeting|conference)\b"),
]
# snippets from real released letters (red team 2026-11-23): (slug, text, should it count)
KNOWN = [
    ("form-fda-483", "Response to the March 5, 2019, FDA-483 that FDA issued", True),
    ("form-fda-483", "indicated on the form FDA-483 prior to", True),
    ("form-fda-483", "deficiencies to the FDA office indicated on the FDA Form 483", True),
    ("post-hoc", "results from the posthoc analysis", True),
    ("pre-approval-inspection", "a follow up Pre approval inspection may be needed", True),
    ("pre-approval-inspection", "FDA may need to conduct a PAI/PLI of the facility", True),
    ("pre-approval-inspection", "a pre-approval of the inspection plan", False),
    ("stability-data", "the photostability data were", False),
    ("stability-data", "submit 12 months of stability data", True),
    ("device-constituent", "control of device-constituents", True),
    ("human-factors", "Labeling and Human Factor comments", True),
    ("container-closure", "the container/closure system", True),
    ("extractables-and-leachables", "Leachables and extractables data", True),
    ("qt", "subjects experienced QT prolongation after", True),
    ("qt", "the QTI score", False),
    ("end-of-review-meeting", "you may request an End of Review meeting", True),
    ("drug-master-file", "the referenced DMFs", True),
    ("drug-master-file", "dimethylformamide", False),
    ("rems", "the items of the remsp", False),
    ("biosimilar", "the proposed biosimilarity", True),
]


def text_of(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def pretty(d):
    return f"{MONTHS[d.month]} {d.day}, {d.year}"


def forms_text(forms):
    q = ['"' + f.replace("...", "…") + '"' for f in forms]
    return q[0] if len(q) == 1 else ", ".join(q[:-1]) + " or " + q[-1]


def raw_letters():
    """[(key, date, apps, status, text)] for each distinct CRL in the raw corpus (the /crl repeat rule)."""
    import build_crl_facts as F
    raw = json.load(io.open(F.CORPUS, encoding="utf-8"))
    out, seen = [], set()
    for r in (raw.get("results") if isinstance(raw, dict) else raw):
        m = re.match(r"(\d{2})/(\d{2})/(\d{4})$", str(r.get("letter_date") or ""))
        if not m or str(r.get("letter_type") or "") != "COMPLETE RESPONSE":
            continue
        d = dt.date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
        appn = tuple(sorted(str(x).strip() for x in (r.get("application_number") or [])))
        txt = re.sub(r"\s+", " ", str(r.get("text") or "")).strip()
        k = (d, appn, txt.lower())
        if k in seen:
            continue
        seen.add(k)
        key = f"{str(r.get('file_name') or '').strip()}|{d.isoformat()}|{','.join(appn)}|" \
              f"{hashlib.sha1(txt.lower().encode('utf-8')).hexdigest()[:8]}"
        out.append((key, d, ", ".join(appn), str(r.get("approval_status") or "").strip(), txt))
    return out


def own_words(doc):
    """The page's own words: h1 to the legal footer, without the table of letters (company names are openFDA's)."""
    body = doc[doc.find("<h1"):(doc.find('<div class="legal"') if '<div class="legal"' in doc else None)]
    return text_of(re.sub(r"<table.*?</table>", " ", body, flags=re.S))


def head_words(doc):
    return html.unescape(" ".join(re.findall(r"<title>(.*?)</title>", doc)
                                  + re.findall(r'name="description" content="([^"]*)"', doc)))


def grab(doc, attr):
    m = re.search(r'data-crl-phrases?="' + attr + r'">(.*?)</p>', doc, re.S)
    return text_of(m.group(1)) if m else ""


def main():
    import build_crl_phrases as P
    import build_crl_letters as C
    from build_feeds import crl_letters
    letters, last_updated, _ = crl_letters(include_rescinded=True)
    by_key = {L["key"]: L for L in letters}
    sl = C.slugs(letters)
    raw = raw_letters()
    phrases = list(EXPECTED)
    plant = os.environ.get("PLANT")
    if plant == "1":
        raw = raw[1:]
    if plant == "2":
        phrases[0] = phrases[0][:3] + (phrases[0][3] + r"|inspection",)
    fails = []

    # the builder's list is this list; its patterns behave as this list's on real snippets
    if [p[:3] for p in P.PHRASES] != [(s, t, f) for s, t, f, _ in EXPECTED]:
        fails.append("build_crl_phrases.PHRASES is not the list written out in this test (terms or forms differ)")
    own = {s: re.compile(p, re.I) for s, _, _, p in phrases}
    for s, snip, want in KNOWN:
        if bool(P.PAT[s].search(snip)) != want or bool(own[s].search(snip)) != want:
            fails.append(f"{s}: {snip!r} should {'count' if want else 'not count'}")
    if len(raw) != len(letters):
        fails.append(f"the raw corpus holds {len(raw)} distinct CRLs, the build {len(letters)}")
    want = {s: [x for x in raw if own[s].search(x[4])] for s, _, _, _ in phrases}
    N = len(raw)

    # the index
    idx_p = os.path.join(SITE, "crl", "phrases", "index.html")
    idx = io.open(idx_p, encoding="utf-8", errors="replace").read() if os.path.exists(idx_p) else ""
    if not idx:
        fails.append("/crl/phrases is missing")
    tab = re.search(r'<table data-crl-phrases="terms">(.*?)</table>', idx, re.S)
    got_rows = collections.Counter()
    rows_by = {}
    terms = {s: t for s, t, _, _ in phrases}
    for row in re.findall(r"<tr>(.*?)</tr>", tab.group(1) if tab else "", re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        if not tds:
            continue
        m = re.search(r'href="/crl/phrase/([a-z0-9-]+)"', tds[0])
        key = m.group(1) if m else next((s for s, t in terms.items() if t == text_of(tds[0])), "?" + text_of(tds[0]))
        got_rows[key] += 1
        rows_by[key] = [text_of(c) for c in tds]
    for k, c in got_rows.items():
        if k not in terms or c > 1:
            fails.append(f"/crl/phrases: row {k!r} is {'unknown' if k not in terms else 'repeated'}")
    for s, term, forms, _ in phrases:
        w = want[s]
        exp = [term, forms_text(forms), str(len(w)), str(sum(1 for x in w if x[1].year < P.SPLIT)),
               str(sum(1 for x in w if x[1].year >= P.SPLIT))]
        if rows_by.get(s) != exp:
            fails.append(f"/crl/phrases row {s}: {rows_by.get(s)} is not {exp}")
        linked = bool(re.search(rf'href="/crl/phrase/{re.escape(s)}"', tab.group(1) if tab else ""))
        if linked != bool(w):
            fails.append(f"/crl/phrases row {s}: {'links' if linked else 'does not link'} with {len(w)} letters")
    most = max(len(w) for w in want.values())
    tied = [t for s, t, _, _ in phrases if len(want[s]) == most]
    names = tied[0] if len(tied) == 1 else ", ".join(tied[:-1]) + " and " + tied[-1]
    top = (f"The most frequent of these is {names}, in {most} letters." if len(tied) == 1 else
           f"The most frequent of these are {names}, each in {most} letters.")
    if grab(idx, "lede") != f"For {len(phrases)} regulatory terms, how many of the {N} Complete Response Letters " \
                            f"in the FDA's release contain the term in their text. {top}":
        fails.append(f"/crl/phrases: the lede is not the recount ({grab(idx, 'lede')[:90]!r})")
    old = [x for x in raw if x[1].year < P.SPLIT]
    new = [x for x in raw if x[1].year >= P.SPLIT]
    cnt = lambda xs, st: sum(1 for x in xs if x[3] == st)  # noqa: E731
    mk = (f"In the release, a letter's year and its openFDA status go together: of the {len(old)} letters dated "
          f"{P.SPLIT - 1} or earlier, {cnt(old, 'Approved')} are on applications openFDA marks Approved and "
          f"{cnt(old, 'Unapproved')} on applications it marks Unapproved; of the {len(new)} dated {P.SPLIT} or "
          f"later, {cnt(new, 'Approved')} are on applications marked Approved and {cnt(new, 'Unapproved')} on "
          f"applications marked Unapproved.")
    if not grab(idx, "sub").endswith(mk):
        fails.append("/crl/phrases: the make-up sentence is not a raw recount")
    if BAD.search(own_words(idx)) or BAD.search(head_words(idx)):
        fails.append("/crl/phrases: the page's own words carry a forecast or reason word")

    # each term page
    for s, term, forms, _ in phrases:
        w = want[s]
        pp = os.path.join(SITE, "crl", "phrase", s, "index.html")
        if not w:
            if os.path.exists(pp):
                fails.append(f"/crl/phrase/{s} exists for a term no letter contains")
            continue
        if not os.path.exists(pp):
            fails.append(f"/crl/phrase/{s} is missing")
            continue
        doc = io.open(pp, encoding="utf-8", errors="replace").read()
        n0 = sum(1 for x in w if x[1].year < P.SPLIT)
        title, desc = P.title_desc(term, len(w), N)
        if f"<title>{html.escape(title, quote=False)}</title>" not in doc.replace("&#x27;", "'") \
                or not title.startswith(f"CRLs Containing {term}: {len(w)} of {N} FDA Letters"):
            fails.append(f"/crl/phrase/{s}: the title is not the term and the recount {len(w)}")
        if not re.search(r'name="description" content="' + re.escape(html.escape(desc)) + '"', doc) \
                or not desc.startswith(f"{len(w)} of {N} "):
            fails.append(f"/crl/phrase/{s}: the description is not the recount")
        h1 = re.search(r"<h1>(.*?)</h1>", doc, re.S)
        if not h1 or text_of(h1.group(1)) != f"CRLs containing the term {term}":
            fails.append(f"/crl/phrase/{s}: the h1 does not name the term")
        if grab(doc, "lede") != f"{len(w)} of the {N} released Complete Response Letters contain " \
                                f"{forms_text(forms)} in their text as the FDA released it.":
            fails.append(f"/crl/phrase/{s}: the lede {grab(doc, 'lede')[:70]!r} is not the recount {len(w)} of {N}")
        first, last = min(x[1] for x in w), max(x[1] for x in w)
        if not grab(doc, "sub").startswith(f"{n0} of them are dated {P.SPLIT - 1} or earlier and {len(w) - n0} "
                                           f"{P.SPLIT} or later; the first is dated {pretty(first)} and the latest "
                                           f"{pretty(last)}. Read from the FDA's CRL release (openFDA "
                                           f"transparency/crl, last updated {last_updated}), with case ignored"):
            fails.append(f"/crl/phrase/{s}: the second sentence is not the recount")
        if f'<link rel="canonical" href="https://www.pdufa.bio/crl/phrase/{s}"' not in doc:
            fails.append(f"/crl/phrase/{s}: the canonical is not its own address")
        t = re.search(r'<table data-crl-phrase="letters">(.*?)</table>', doc, re.S)
        rows = [r for r in re.findall(r"<tr>(.*?)</tr>", t.group(1) if t else "", re.S) if "<td" in r]
        if len(rows) != len(w):
            fails.append(f"/crl/phrase/{s}: lists {len(rows)} letters, the recount {len(w)}")
        listed = collections.Counter(re.findall(r'href="/crl/letter/([a-z0-9-]+)"', t.group(1) if t else ""))
        exp_slugs = collections.Counter(sl.get(x[0]) for x in w)
        if listed != exp_slugs:
            fails.append(f"/crl/phrase/{s}: the letters linked are not the letters whose text holds the term "
                         f"({sorted((exp_slugs - listed) + (listed - exp_slugs))[:3]})")
        by_slug = {sl.get(x[0]): x for x in w}
        for r in rows:
            m = re.search(r'href="/crl/letter/([a-z0-9-]+)"', r)
            x = by_slug.get(m.group(1)) if m else None
            if not x:
                continue
            L = by_key[x[0]]
            if not os.path.exists(os.path.join(SITE, "crl", "letter", m.group(1), "index.html")):
                fails.append(f"/crl/phrase/{s}: links /crl/letter/{m.group(1)}, which does not exist")
            cells = [text_of(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
            name = L["name"] if L["name"] and L["ckey"] else "name not readable in the release"
            exp = [pretty(x[1]), x[2] or "not given", name, x[3] or "not given"]
            if cells[:4] != exp:
                fails.append(f"/crl/phrase/{s}: row {cells[:4]} is not the release's {exp}")
            pdf = re.findall(r'<a href="([^"]+)" rel="noopener">PDF</a>', r)
            if [html.unescape(u) for u in pdf] != ([L["url"]] if L["url"] else []):
                fails.append(f"/crl/phrase/{s}: row {exp[0]} {exp[1]} has PDF {pdf}, the release {L['url']!r}")
            resc = "the FDA rescinded this letter" in cells[4]
            if resc != L["rescinded"] or (resc and pretty(L["resc_date"]) not in cells[4]):
                fails.append(f"/crl/phrase/{s}: row {exp[0]} {exp[1]} rescinded mark is wrong")
        if BAD.search(own_words(doc)) or BAD.search(head_words(doc)):
            fails.append(f"/crl/phrase/{s}: the page's own words carry a forecast or reason word")

    # each letter page names exactly the terms its text holds, by link and label
    for x in raw:
        slug = sl.get(x[0])
        lp = os.path.join(SITE, "crl", "letter", slug or "-", "index.html")
        if not slug or not os.path.exists(lp):
            fails.append(f"letter {x[1]} {x[2]}: no /crl/letter page")
            continue
        doc = io.open(lp, encoding="utf-8", errors="replace").read()
        m = re.search(r'data-crl-letter="terms">(.*?)</p>', doc, re.S)
        got = re.findall(r'<a href="/crl/phrase/([a-z0-9-]+)">(.*?)</a>', m.group(1)) if m else []
        got = [(a, html.unescape(b)) for a, b in got]
        exp = [(s, terms[s]) for s, _, _, _ in phrases if own[s].search(x[4])]
        if got != exp:
            fails.append(f"/crl/letter/{slug}: names terms {got}, its text holds {exp}")
        elif m and not text_of(m.group(1)).startswith("Terms from /crl/phrases that this letter's released text "
                                                       "contains:"):
            fails.append(f"/crl/letter/{slug}: the terms line is reworded")
        if len(fails) > 40:
            break
    if fails:
        print(f"FAIL test_crl_phrases: {len(fails)} problem(s); fix: python build_crl_phrases.py "
              "(and build_crl_letters.py)")
        for f in fails[:20]:
            print("  " + f)
        return 1
    print(f"PASS test_crl_phrases: {len(phrases)} terms recounted by hand-written patterns across {len(raw)} letters; "
          f"every term page and letter page agrees")
    return 0


if __name__ == "__main__":
    sys.exit(main())
