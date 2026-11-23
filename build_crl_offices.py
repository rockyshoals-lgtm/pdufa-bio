# -*- coding: utf-8 -*-
"""build_crl_offices.py -- /crl/offices: which FDA office signed each released Complete Response Letter.

Every CRL ends with a signature block. In the FDA's release, the letters on applications openFDA marks Approved name
the review division and office that signed (for example "Division of Neurology 1, Office of Neuroscience, Center for
Drug Evaluation and Research"); the letters on applications it marks Unapproved name neither, and most print
"(b) (4)", the FOIA exemption 4 mark, in the signature. The split follows openFDA's status field, not the letter's
date: Unapproved letters of every year name none. Nobody else counts this.

The page counts, from the letters' own text (build_feeds.signature reads the block from the last "Sincerely" to the
electronic signature page legend, and the line after the legend), with openFDA's approver_center field adding a
division or office the scan missed:

  * by openFDA's approval_status field, and by letter year: letters that name a division or office, letters that
    name only the Center, letters that name neither, and letters whose signature shows (b) (4);
  * every office and every division named, as printed (OCR misreads included), with its letter count and dates;
  * the Approved letters whose signature text is too garbled to read, by name, so the count can be checked.

The same letters as /crl: one per distinct CRL (a repeat counted once), the 2 the FDA rescinded as issued in error
included and flagged on /crl/facts. Counts of documents only: no rates, no predictions, no reading of why.

    python build_crl_offices.py
"""
import collections
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
from build_crl_facts import CORPUS, esc, pretty  # noqa: E402
from build_crl_companies import page, pl  # noqa: E402
from build_feeds import crl_letters  # noqa: E402

OUT = os.path.join(SITE, "crl", "offices", "index.html")


def kind(L):
    g = L["sig"]
    return "unit" if (g["division"] or g["office"]) else ("center" if g["center"] else "none")


def tally(ls):
    c = collections.Counter(kind(L) for L in ls)
    return len(ls), c["unit"], c["center"], c["none"], sum(1 for L in ls if L["sig"]["withheld"])


def counts_row(label, ls):
    n, u, ce, no, wh = tally(ls)
    return f'<tr><td>{label}</td><td>{n}</td><td>{u}</td><td>{ce}</td><td>{no}</td><td>{wh}</td></tr>'


HEAD = ('<tr><th>{}</th><th>Letters</th><th>Name a division or office</th><th>Name only the Center</th>'
        '<th>Name neither</th><th>Signature shows (b) (4)</th></tr>')


def unit_table(title, key, letters):
    by = collections.defaultdict(list)
    for L in letters:
        if L["sig"][key]:
            by[L["sig"][key]].append(L)
    rows = sorted(by.items(), key=lambda kv: (-len(kv[1]), kv[0].lower()))
    B = [f'<h2>{esc(title)}</h2>', f'<table><tr><th>{"Division" if key == "division" else "Office"}, as printed'
         '</th><th>Letters</th><th>First letter</th><th>Latest letter</th></tr>']
    for name, ls in rows:
        ls.sort(key=lambda x: x["date"])
        last = ls[-1]
        lc = (f'<a href="{esc(last["url"])}" rel="noopener">{esc(pretty(last["date"]))}</a>' if last["url"]
              else esc(pretty(last["date"])))
        B.append(f'<tr><td>{esc(name)}</td><td>{len(ls)}</td><td class="dt">{esc(pretty(ls[0]["date"]))}</td>'
                 f'<td class="dt">{lc}</td></tr>')
    B.append('</table>')
    return B, len(rows)


def figures(letters):
    """Every number the page's prose states, recounted by tests/test_crl_offices.py the same way."""
    status = collections.defaultdict(list)
    for L in letters:
        status[L["status"] or "not given"].append(L)
    na, ua, _, _, _ = tally(status.get("Approved", []))
    nu, uu, _, _, whu = tally(status.get("Unapproved", []))
    return {"n": len(letters), "na": na, "ua": ua, "nu": nu, "uu": uu, "whu": whu,
            "cder": sum(1 for L in letters if L["sig"]["center"] == "CDER"),
            "cber": sum(1 for L in letters if L["sig"]["center"] == "CBER")}, status


def lede_text(f):
    return (f'Of the {pl(f["na"], "released letter", "released letters")} on applications openFDA marks Approved, '
            f'{f["ua"]} name the FDA division or office that signed {"it" if f["ua"] == 1 else "them"} in text this '
            f'page can read. Of the {f["nu"]} on applications it marks Unapproved, '
            f'{"none does" if f["uu"] == 0 else str(f["uu"]) + " do"}, and {f["whu"]} print "(b) (4)" in the '
            'signature.')


def centers_text(f):
    return (f'Of all {f["n"]} letters, {f["cder"]} name the Center for Drug Evaluation and Research and {f["cber"]} the Center for Biologics '
            'Evaluation and Research')


def main():
    letters, last_updated, n_resc = crl_letters(include_rescinded=True)
    snap = (re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(CORPUS)) or [None, ""])[1]
    n, u, ce, no, wh = tally(letters)
    f, status = figures(letters)
    st_rows = sorted(status.items(), key=lambda kv: -len(kv[1]))
    app_unread = sorted((L for L in status.get("Approved", []) if kind(L) != "unit"), key=lambda x: x["date"])

    title = f"Which FDA Office Signed Each CRL: {n} Released Letters | pdufa.bio"
    desc = (f"The FDA division and office named in each of {n} released Complete Response Letters, and how many "
            "name none, counted from the letters' own signature blocks.")
    B = ['<h1>Which FDA office <span class="g">signed each CRL</span></h1>',
         f'<p class="sub" data-crl-offices="lede">{esc(lede_text(f))}</p>',
         f'<p class="sub">Counted from the {n} distinct Complete Response Letters in the FDA\'s CRL release (openFDA '
         f'transparency/crl, last updated {esc(last_updated)}; snapshot read {esc(snap)}), the same letters as '
         '<a href="/crl">/crl</a>. Each count reads the letter\'s own signature block, from its last "Sincerely" to '
         'its electronic signature page, and the line after that page\'s legend; where openFDA\'s approver_center '
         'field names a division or office the scan missed, that is counted too. '
         f'<span data-crl-offices="centers">{esc(centers_text(f))}</span>. "(b) (4)" is the label for information '
         'withheld under exemption 4 of the Freedom of Information Act (trade secrets and confidential commercial or '
         'financial information); in these letters it stands where other letters print the signer, and on the '
         'electronic signature page the date and time still show. Where a letter names no division or office, this '
         'page cannot tell whether one was withheld or never printed. The split follows openFDA\'s status field, '
         'not the letter\'s date: Unapproved letters of every year name none. These are counts of what the letters '
         'print, not a reading of why.</p>',
         '<h2>By openFDA approval status</h2>', '<table>' + HEAD.format("openFDA status")]
    for s, ls in st_rows:
        B.append(counts_row(esc(s), ls))
    B.append(counts_row("<b>All letters</b>", letters) + '</table>')
    B += ['<h2>By letter year</h2>', '<table>' + HEAD.format("Year")]
    years = collections.defaultdict(list)
    for L in letters:
        years[L["date"].year].append(L)
    for y in sorted(years, reverse=True):
        B.append(counts_row(str(y), years[y]))
    B.append('</table>')
    ob, n_off = unit_table("Every office named", "office", letters)
    db, n_div = unit_table("Every division named", "division", letters)
    B += ob + db
    if app_unread:
        B.append('<p class="sub" data-crl-offices="unread">Letters on Approved applications counted here as naming no '
                 'division or office, because the scan of their signature is too garbled to read: ' + "; ".join(
                     (f'<a href="{esc(L["url"])}" rel="noopener">{esc(L["app_txt"])}, {esc(pretty(L["date"]))}</a>'
                      if L["url"] else f'{esc(L["app_txt"])}, {esc(pretty(L["date"]))}') for L in app_unread)
                 + '.</p>')
    B.append('<p class="sub">An office is the first "Office of" the block names, other than the Office of New Drugs '
             'when a narrower office is also named; a division is the first "Division of". Names are as printed, '
             'OCR misreads included ("Office of Drug Evaluation IT" and "Office of Drug Evaluation |" appear to be '
             'scans of II and I), so one office can appear under two names, and the FDA renamed its review offices in 2019 '
             'and 2020. The FDA releases letters selectively; a count here is what the release holds.</p>'
             '<p class="sub"><a href="/crl/facts">Facts from all released CRLs</a> &middot; '
             '<a href="/crl/companies">every CRL, by company</a> &middot; '
             '<a href="/crl/data/crl-letters.csv">the letters as data</a> &middot; <a href="/crl">every released '
             'letter, by year</a></p>')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(page(title, desc, "/crl/offices", B))
    print(f"/crl/offices: {n} letters, {u} name a division or office, {ce} only the Center, {no} neither, "
          f"{wh} with (b) (4); {n_off} offices, {n_div} divisions; {len(app_unread)} Approved letters unread")
    return 0


if __name__ == "__main__":
    sys.exit(main())
