# -*- coding: utf-8 -*-
"""build_crl_phrases.py -- /crl/phrases and /crl/phrase/<slug>: which released CRLs contain which words.

The FDA's CRL release gives every letter's text (openFDA's extraction from the PDF). This counts, for a fixed list of
regulatory terms, the letters whose released text contains the term, and lists those letters, each linked to its
/crl/letter page. Nobody else publishes this: a searchable count of what the FDA's own letters say.

Method, stated on the page: a letter counts when its text contains one of the term's forms (PHRASES below), with case
ignored and any spaces, hyphens or slashes between a form's words ignored; the patterns are built from the forms. Text the FDA redacted ("(b) (4)") or that the scan
misread is not matched, so a count is the number of letters whose released text holds the words, not the number of
letters about the subject. The pages state the counts, the letters' years and openFDA's status field; they say
nothing about why a letter was sent or what an application's outcome will be.

The release's own make-up is stated once, on the index, because it shapes the year columns: almost every letter dated
2023 or earlier is on an application openFDA marks Approved, and almost every letter dated 2024 or later on one it
marks Unapproved (the counts are computed, not typed).

The same letters as /crl and /crl/letter: one per distinct CRL, the 2 the FDA rescinded included and flagged.

    python build_crl_phrases.py
"""
import collections
import io
import os
import re
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
from build_crl_facts import CORPUS, esc, pretty  # noqa: E402
from build_crl_companies import page  # noqa: E402
from build_feeds import crl_letters  # noqa: E402

INDEX = os.path.join(SITE, "crl", "phrases", "index.html")
ROOT = os.path.join(SITE, "crl", "phrase")
SPLIT = 2024              # letters dated before this year, and from it on (the release's make-up)

# (slug, the term as the page names it, the forms a letter's text must contain). The patterns are built from the
# forms (form_pattern), so the forms the page states and the forms matched cannot drift apart. Matching ignores case,
# and ignores any spaces, hyphens or slashes between a form's words ("pre-approval" also matches "preapproval" and
# "pre approval"). A word ending in "..." in a form also matches any longer word that begins with it.
PHRASES = [
    ("form-fda-483", "Form FDA 483", ["Form FDA 483", "FDA Form 483", "Form 483", "FDA 483"]),
    ("pre-approval-inspection", "pre-approval or pre-license inspection",
     ["pre-approval inspection", "pre-license inspection", "pre-licensure inspection", "PAI", "PLI"]),
    ("adequate-and-well-controlled", "adequate and well-controlled", ["adequate and well-controlled"]),
    ("substantial-evidence-of-effectiveness", "substantial evidence of effectiveness",
     ["substantial evidence of effectiveness"]),
    ("post-hoc", "post hoc", ["post hoc"]),
    ("statistical-analysis-plan", "statistical analysis plan", ["statistical analysis plan"]),
    ("bioequivalence", "bioequivalence", ["bioequivalen..."]),
    ("human-factors", "human factors", ["human factor..."]),
    ("rems", "REMS (Risk Evaluation and Mitigation Strategy)",
     ["Risk Evaluation and Mitigation Strateg...", "REMS"]),
    ("carcinogenicity", "carcinogenicity", ["carcinogenicity"]),
    ("immunogenicity", "immunogenicity", ["immunogenicity"]),
    ("qt", "QT interval or QTc", ["QTc", "QT interval", "thorough QT", "QT prolongation"]),
    ("liver-injury", "drug-induced liver injury or hepatotoxicity", ["drug-induced liver injury", "hepatotoxicity"]),
    ("stability-data", "stability data", ["stability data"]),
    ("impurities", "impurities", ["impurit..."]),
    ("container-closure", "container closure", ["container closure"]),
    ("extractables-and-leachables", "extractables and leachables",
     ["extractable... and leachable...", "leachable... and extractable..."]),
    ("sterility", "sterility", ["sterility"]),
    ("microbiology", "microbiology", ["microbiology"]),
    ("dissolution", "dissolution", ["dissolution"]),
    ("drug-master-file", "drug master file (DMF)", ["drug master file...", "DMF", "DMFs"]),
    ("device-constituent", "device constituent", ["device constituent..."]),
    ("biosimilar", "biosimilar or interchangeable", ["biosimilar...", "interchangeab..."]),
    ("comparability", "comparability", ["comparability"]),
    ("accelerated-approval", "accelerated approval", ["accelerated approval"]),
    ("confirmatory-trial", "confirmatory trial or study", ["confirmatory trial...", "confirmatory stud..."]),
    ("advisory-committee", "advisory committee", ["advisory committee"]),
    ("end-of-review-meeting", "end-of-review meeting or conference",
     ["end-of-review meeting", "end-of-review conference"]),
]


def form_pattern(form):
    """One form as a regex: its words (split at spaces and hyphens) in order, anything made of spaces, hyphens or
    slashes allowed between them, whole words except where a word ends in "..."."""
    out = []
    for w in re.split(r"[\s-]+", form.strip()):
        stem = w[:-3] if w.endswith("...") else w
        out.append(re.escape(stem) + (r"\w*" if w.endswith("...") else ""))
    tail = "" if form.endswith("...") else r"\b"
    return r"\b" + r"[\s/-]*".join(out) + tail


def forms_text(forms):
    q = ['"' + f.replace("...", "\u2026") + '"' for f in forms]
    return q[0] if len(q) == 1 else ", ".join(q[:-1]) + " or " + q[-1]


# a fact some terms need beside them (the plain-language rules: accelerated approval is stated as conditional)
NOTE = {"accelerated-approval": "Accelerated approval is conditional: the FDA can withdraw it if a confirmatory "
                                "trial does not verify the clinical benefit."}
METHOD = ("case ignored, and any spaces, hyphens or slashes between a form's words ignored; a word ending in "
          "\u2026 also matches any longer word that begins with it")
PAT = {s: re.compile("|".join(form_pattern(f) for f in forms), re.I) for s, _, forms in PHRASES}


def flat(text):
    return re.sub(r"\s+", " ", str(text or ""))


def matches(L):
    """The slugs of the terms this letter's released text contains."""
    t = flat(L["text"])
    return [s for s, _, _ in PHRASES if PAT[s].search(t)]


def make_up(letters):
    """[(label, letters, Approved, Unapproved, other)] for the letters before SPLIT and from it on."""
    out = []
    for label, ls in ((f"dated {SPLIT - 1} or earlier", [L for L in letters if L["date"].year < SPLIT]),
                      (f"dated {SPLIT} or later", [L for L in letters if L["date"].year >= SPLIT])):
        c = collections.Counter(L["status"] for L in ls)
        out.append((label, len(ls), c["Approved"], c["Unapproved"], len(ls) - c["Approved"] - c["Unapproved"]))
    return out


def make_up_text(letters):
    (l0, n0, a0, u0, _), (l1, n1, a1, u1, _) = make_up(letters)
    return (f"In the release, a letter's year and its openFDA status go together: of the {n0} letters {l0}, {a0} are "
            f"on applications openFDA marks Approved and {u0} on applications it marks Unapproved; of the {n1} "
            f"{l1}, {a1} are on applications marked Approved and {u1} on applications marked Unapproved.")


def row_counts(ls):
    return (len(ls), sum(1 for L in ls if L["date"].year < SPLIT), sum(1 for L in ls if L["date"].year >= SPLIT))


def name_of(L):
    return L["name"] if L["name"] and L["ckey"] else "name not readable in the release"


def phrase_lede(n_hit, n, forms):
    return (f"{n_hit} of the {n} released Complete Response Letters contain {forms_text(forms)} in their text as "
            f"the FDA released it.")


def title_desc(term, n, N):
    title = f"CRLs Containing {term}: {n} of {N} FDA Letters | pdufa.bio"
    desc = (f"{n} of {N} FDA Complete Response Letters in the FDA's release contain the term {term} in their text, "
            "each listed with its text and PDF.")
    if len(desc) > 158:
        desc = f"{n} of {N} released FDA Complete Response Letters contain the term {term} in their text, each listed."
    return title, desc


def letter_cell(L, sl):
    return (f'<a href="/crl/letter/{sl[L["key"]]}">its text</a>'
            + (f' &middot; <a href="{esc(L["url"])}" rel="noopener">PDF</a>' if L["url"] else '')
            + (f' &middot; the FDA rescinded this letter on {esc(pretty(L["resc_date"]))}' if L["rescinded"] else ''))


def write_phrase(slug, term, forms, hit, letters, sl, last_updated):
    n, n0, n1 = row_counts(hit)
    first = min(L["date"] for L in hit)
    last = max(L["date"] for L in hit)
    title, desc = title_desc(term, n, len(letters))
    B = [f'<h1>CRLs containing the term <span class="g">{esc(term)}</span></h1>',
         f'<p class="sub" data-crl-phrase="lede">{esc(phrase_lede(n, len(letters), forms))}</p>',
         f'<p class="sub" data-crl-phrase="sub">{n0} of them are dated {SPLIT - 1} or earlier and {n1} {SPLIT} or '
         f'later; the first is dated {esc(pretty(first))} and the latest {esc(pretty(last))}. Read from the FDA\'s '
         f'CRL release (openFDA transparency/crl, last updated {esc(last_updated)}), with {esc(METHOD)}. Text the '
         'FDA redacted or the scan misread is not matched, so this is the number of letters whose released text '
         'holds the words, not the number of letters about the subject.'
         + (f' {esc(NOTE[slug])}' if slug in NOTE else '') + '</p>',
         '<table data-crl-phrase="letters"><tr><th>Letter date</th><th>Application</th><th>Company (openFDA)</th>'
         '<th>openFDA status</th><th>Letter</th></tr>']
    for L in sorted(hit, key=lambda x: (x["date"], x["app_txt"]), reverse=True):
        B.append(f'<tr><td class="dt">{esc(pretty(L["date"]))}</td><td>{esc(L["app_txt"] or "not given")}</td>'
                 f'<td>{esc(name_of(L))}</td><td>{esc(L["status"] or "not given")}</td>'
                 f'<td>{letter_cell(L, sl)}</td></tr>')
    B.append('</table>')
    B.append('<p class="sub"><a href="/crl/phrases">Every term counted</a> &middot; <a href="/crl/offices">which FDA '
             'office signed each CRL</a> &middot; <a href="/crl/facts">facts from all released CRLs</a> &middot; '
             '<a href="/crl">every released letter, by year</a></p>')
    out = os.path.join(ROOT, slug, "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    io.open(out, "w", encoding="utf-8").write(page(title, desc, f"/crl/phrase/{slug}", B))


def top_text(hits):
    """The most frequent term, every term tied with it named."""
    most = max(len(hits[s]) for s, _, _ in PHRASES)
    tied = [t for s, t, _ in PHRASES if len(hits[s]) == most]
    names = tied[0] if len(tied) == 1 else ", ".join(tied[:-1]) + " and " + tied[-1]
    return (f"The most frequent of these is {names}, in {most} letters." if len(tied) == 1 else
            f"The most frequent of these are {names}, each in {most} letters.")


def main():
    from build_crl_letters import slugs
    letters, last_updated, _ = crl_letters(include_rescinded=True)
    sl = slugs(letters)
    hits = collections.defaultdict(list)
    for L in letters:
        for s in matches(L):
            hits[s].append(L)
    if os.path.isdir(ROOT):
        shutil.rmtree(ROOT)
    for s, term, forms in PHRASES:
        if hits[s]:                               # a term no letter contains gets a row, not an empty page
            write_phrase(s, term, forms, hits[s], letters, sl, last_updated)
    n = len(letters)
    title = f"What FDA Complete Response Letters Say: {len(PHRASES)} Terms in {n} Letters | pdufa.bio"
    desc = (f"How many of the {n} released FDA Complete Response Letters contain each of {len(PHRASES)} regulatory "
            "terms, counted from the letters' own text, each letter listed.")
    B = ['<h1>What the FDA\'s <span class="g">CRLs say</span></h1>',
         f'<p class="sub" data-crl-phrases="lede">For {len(PHRASES)} regulatory terms, how many of the {n} '
         f'Complete Response Letters in the FDA\'s release contain the term in their text. {esc(top_text(hits))}</p>',
         f'<p class="sub" data-crl-phrases="sub">Read from each letter\'s text as the FDA released it (openFDA '
         f'transparency/crl, last updated {esc(last_updated)}), the same letters as <a href="/crl">/crl</a>. A '
         f'letter counts for a term when its text contains one of the forms in the table, with {esc(METHOD)}. A '
         'letter counts once per term however often it uses the words. Text the FDA redacted or the scan misread is '
         'not matched, so a count is the number of letters whose released text holds the words, not the number of '
         'letters about the subject. These are counts of words in documents: they do not say why a letter was '
         f'sent. <span data-crl-phrases="makeup">{esc(make_up_text(letters))}</span></p>',
         '<table data-crl-phrases="terms"><tr><th>Term</th><th>Forms matched</th><th>Letters</th>'
         f'<th>Dated {SPLIT - 1} or earlier</th><th>Dated {SPLIT} or later</th></tr>']
    for s, term, forms in sorted(PHRASES, key=lambda p: (-len(hits[p[0]]), p[1])):
        a, b0, b1 = row_counts(hits[s])
        cell = f'<a href="/crl/phrase/{s}">{esc(term)}</a>' if hits[s] else esc(term)
        B.append(f'<tr><td>{cell}</td><td style="font-size:12.5px">{esc(forms_text(forms))}'
                 f'</td><td>{a}</td><td>{b0}</td><td>{b1}</td></tr>')
    B.append('</table>')
    B.append('<p class="sub">Each term links to its letters, and each letter to its own page with the FDA\'s full '
             'text. The terms are a fixed list; the forms each one matches are given in the table. '
             + ''.join(f'{esc(v)} ' for v in NOTE.values()) +
             '<a href="/crl/data/crl-letters.csv">The letters as data</a> &middot; <a href="/crl/offices">which FDA '
             'office signed each CRL</a> &middot; <a href="/crl/facts">facts from all released CRLs</a> &middot; '
             '<a href="/crl/companies">every CRL, by company</a></p>')
    os.makedirs(os.path.dirname(INDEX), exist_ok=True)
    io.open(INDEX, "w", encoding="utf-8").write(page(title, desc, "/crl/phrases", B))
    print(f"/crl/phrases: {len(PHRASES)} terms across {n} letters; "
          + ", ".join(f"{s} {len(hits[s])}" for s, _, _ in PHRASES[:6]) + f" ... (corpus {os.path.basename(CORPUS)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
