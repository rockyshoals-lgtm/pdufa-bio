# -*- coding: utf-8 -*-
"""build_crl_review_clock.py -- /crl/review-clock: the days between the dates each released CRL prints.

David, 2026-11-22: "continue to build the moat, row the boat." Most Complete Response Letters open by naming the date
the FDA received the application, and a letter on a resubmission names the date of the response it answers and the
date of the earlier FDA letter. Nobody counts those dates across the release. This page does, from the letters' own
text (openFDA transparency/crl, read by crl_review_clock.py):

  * letters on an original application that name no earlier FDA action, and with no earlier CRL on the same
    application in the release: days from the received date the letter prints to the letter's date; median, 25th and
    75th percentiles, shortest, longest, with n; split by the statute section the letter names and by letter year; a
    count of those that say a submission extended the goal date
  * letters on a response to an earlier FDA letter: days from the response to this letter, and from the earlier FDA
    letter to the response
  * every letter left out, by reason, so the counts can be checked; the two whose dates are out of order, by name
  * one row per counted letter, linking its /crl/letter page and the FDA's PDF; a CSV of every letter

The same letters as /crl, less the 2 the FDA rescinded as issued in error. Calendar days between printed dates: not a
measure of FDA review time (the FDA's clock can stop and restart), no reading of why, no forecast.

    python build_crl_review_clock.py
"""
import collections
import csv
import io
import json
import os
import re
import statistics
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
from build_crl_facts import CORPUS, esc, is_supplement, pretty  # noqa: E402
from build_crl_companies import BASE, page  # noqa: E402
from build_crl_letters import name_of, slugs  # noqa: E402
from build_feeds import crl_letters  # noqa: E402
from crl_review_clock import read  # noqa: E402

OUT = os.path.join(SITE, "crl", "review-clock", "index.html")
CSV = os.path.join(SITE, "crl", "data", "crl-review-clock.csv")
COLUMNS = ["letter_date", "applications", "company", "openfda_status", "pdf_url", "letter_page", "supplement",
           "fda_heading", "statute_section_printed", "received_date_printed", "received_word",
           "earlier_fda_action_named", "refuse_to_file_named", "earlier_crl_in_release", "response_dated",
           "earlier_fda_letter_dated", "earlier_letter_kind", "earlier_letter_in_release", "says_goal_date_extended", "days_received_to_letter", "days_response_to_letter",
           "days_earlier_letter_to_response", "counted_in"]
YEARS = [("2025 to 2026", 2025, 2026), ("2023 to 2024", 2023, 2024), ("2020 to 2022", 2020, 2022),
         ("Before 2020", 0, 2019)]
SECTION_LABEL = {"505(b)": "505(b)", "505(b)(1)": "505(b)(1)", "505(b)(2)": "505(b)(2)",
                 "351(a)": "351(a) (biologic)", "351(k)": "351(k) (biosimilar)", "multi": "more than one printed"}
FIRST, RESP = "receipt to letter, no earlier action named", "response to an earlier FDA letter"


def stats(xs):
    """(n, median, 25th, 75th, shortest, longest); percentiles by statistics.quantiles, inclusive method."""
    xs = sorted(xs)
    if not xs:
        return None
    q = statistics.quantiles(xs, n=4, method="inclusive") if len(xs) > 1 else [xs[0]] * 3
    return len(xs), statistics.median(xs), q[0], q[2], xs[0], xs[-1]


def g(x):
    return f"{x:g}"


def rows():
    letters, last_updated, n_resc = crl_letters()
    sl = slugs(crl_letters(include_rescinded=True)[0])
    on_file = collections.defaultdict(set)       # (application number) -> every CRL date in the release
    for L in crl_letters(include_rescinded=True)[0]:
        for t, n, sfx in L["apps"]:
            on_file[(t, n)].add(L["date"])
    # the release's dates for an application, whatever the type prefix (the release prints "BL" and "BLA" both)
    on_num = collections.defaultdict(set)
    for (t, n), ds in on_file.items():
        on_num[n] |= ds
    out = []
    for L in letters:
        r = read(L["text"])
        sup = any(is_supplement(s) for _, _, s in L["apps"])
        e = {"L": L, "r": r, "sup": sup, "slug": sl.get(L["key"], ""), "group": "", "why": "",
             "days_rec": (L["date"] - r["received"]).days if r["received"] else None,
             "days_resp": (L["date"] - r["resub"]).days if r["resub"] else None,
             "days_gap": (r["resub"] - r["answers"]).days if r["resub"] else None,
             "in_release": (any(r["answers"] in on_file[(t, n)] for t, n, _ in L["apps"]) if r["answers"] else None),
             "earlier_crl": any(d < L["date"] for _, n, _ in L["apps"] for d in on_num[n])}
        if sup:
            e["why"] = "supplement"
        elif r["heading"]:
            e["why"] = "headed otherwise"
        elif r["answer_kind"] and r["answer_kind"] != "refuse to file":
            if e["days_resp"] is not None and e["days_resp"] >= 0 and e["days_gap"] >= 0:
                e["group"] = "response"
            else:
                e["why"] = "dates out of order"
        elif r["rtf"]:
            e["why"] = "refuse to file"
        elif r["earlier"]:
            e["why"] = "earlier action, dates not paired"
        elif not r["received"]:
            e["why"] = "no date" if r["opening"] else "no opening"
        elif e["days_rec"] < 0:
            e["why"] = "dates out of order"
        elif e["earlier_crl"]:
            e["why"] = "earlier CRL in the release"
        else:
            e["group"] = "first"
        out.append(e)
    return out, last_updated, n_resc


def tr_stats(label, s, attr=""):
    if not s:
        return ""
    n, med, q1, q3, lo, hi = s
    mid = f"{g(q1)} to {g(q3)}" if n >= 4 else "too few letters"
    return (f'<tr{attr}><td>{label}</td><td>{n}</td><td>{g(med)}</td><td>{mid}</td><td>{lo}</td>'
            f'<td>{hi}</td></tr>')


STATS_HEAD = ('<tr><th>{}</th><th>Letters</th><th>Median days</th><th>Middle half (25th to 75th percentile)</th>'
              '<th>Shortest</th><th>Longest</th></tr>')


def letter_cell(e):
    L = e["L"]
    a = (f'<a href="/crl/letter/{esc(e["slug"])}">{esc(pretty(L["date"]))}</a>' if e["slug"]
         else esc(pretty(L["date"])))
    return a + (f' &middot; <a href="{esc(L["url"])}" rel="noopener">PDF</a>' if L["url"] else "")


def figures(E):
    first = [e for e in E if e["group"] == "first"]
    resp = [e for e in E if e["group"] == "response"]
    left = collections.Counter(e["why"] for e in E if not e["group"])
    nodate = [e for e in E if e["why"] in ("no date", "no opening")]
    return {"n": len(E), "first": first, "resp": resp, "left": left,
            "s_first": stats([e["days_rec"] for e in first]), "s_resp": stats([e["days_resp"] for e in resp]),
            "s_gap": stats([e["days_gap"] for e in resp]),
            "nodate_status": collections.Counter(e["L"]["status"] or "not given" for e in nodate),
            "order": sorted((e for e in E if e["why"] == "dates out of order"), key=lambda e: e["L"]["date"]),
            "major": [e for e in first if e["r"]["major"]], "dated": [e for e in first if e["r"]["rword"] != "received"],
            "in_rel": sum(1 for e in resp if e["in_release"]),
            "kinds": collections.Counter(e["r"]["answer_kind"] for e in resp)}


def lede_text(f):
    n, med, q1, q3, lo, hi = f["s_first"]
    rn, rmed = f["s_resp"][0], f["s_resp"][1]
    k = len(f["dated"])
    return (f"Of the {f['n']} Complete Response Letters in the FDA's release (rescinded letters left out), {n} are on an "
            f"original application, name no earlier FDA action, and print the date the FDA received the application"
            + (f" (or, for {k}, only the date it was dated or submitted)" if k else "") +
            f". From that date to the letter: median {g(med)} calendar days, middle half {g(q1)} to {g(q3)}, shortest "
            f"{lo}, longest {hi}. {rn} letters answer a response to an earlier FDA letter and print both dates: median "
            f"{g(rmed)} days from the response to the letter. These are days between printed dates, not FDA review "
            f"time.")


def write_csv(E, path=CSV):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNS)
        for e in sorted(E, key=lambda e: (e["L"]["date"], e["L"]["app_txt"], e["L"]["key"])):
            L, r = e["L"], e["r"]
            d = lambda x: x.isoformat() if x else ""   # noqa: E731
            w.writerow([L["date"].isoformat(), L["app_txt"], name_of(L), L["status"], L["url"],
                        f'{BASE}/crl/letter/{e["slug"]}' if e["slug"] else "", "yes" if e["sup"] else "no",
                        r["heading"] or "", r["pathway"] or "", d(r["received"]), r["rword"] or "",
                        "yes" if r["earlier"] else "no", "yes" if r["rtf"] else "no", "yes" if e["earlier_crl"] else "no",
                        d(r["resub"]), d(r["answers"]), r["answer_kind"] or "",
                        "" if e["in_release"] is None else ("yes" if e["in_release"] else "no"),
                        "yes" if r["major"] else "no",
                        "" if e["days_rec"] is None else e["days_rec"],
                        "" if e["days_resp"] is None else e["days_resp"],
                        "" if e["days_gap"] is None else e["days_gap"],
                        {"first": FIRST, "response": RESP}.get(e["group"], "not counted: " + e["why"])])


WHY = {"no date": "the opening sentence prints no readable received date (withheld, blank or garbled in the scan)",
       "no opening": "the text has no readable opening sentence",
       "earlier action, dates not paired": "the letter names an earlier FDA action but does not pair a response date "
                                           "with an earlier letter's date in text this page can read",
       "refuse to file": "the letter names an earlier refuse-to-file letter on the application",
       "dates out of order": "openFDA's letter date is earlier than the received or response date the letter prints",
       "earlier CRL in the release": "the letter names no earlier FDA action, but the release holds an earlier CRL on "
                                     "the same application number",
       "headed otherwise": "the FDA heads the letter \"Corrected Complete Response\" or \"Acknowledge Incomplete "
                           "Response\", not a plain Complete Response",
       "supplement": "the letter is on a supplement (alone or with another application)"}
LEFT_ORDER = ("no date", "no opening", "earlier action, dates not paired", "refuse to file", "earlier CRL in the release",
              "dates out of order", "headed otherwise", "supplement")


def main():
    E, last_updated, n_resc = rows()
    snap = (re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(CORPUS)) or [None, ""])[1]
    f = figures(E)
    if not f["s_first"] or not f["s_resp"]:
        print("crl review clock: no receipt-to-letter or response letters read; nothing written")
        return 1
    n, med, q1, q3, lo, hi = f["s_first"]
    title = f"Days From Receipt to a CRL, as {f['n']} FDA Letters Print the Dates | pdufa.bio"
    desc = (f"Days from the received date {n} released FDA CRLs print to each letter's date (median {g(med)}), and "
            f"from a resubmission to the next CRL. Not FDA review time.")
    B = ['<h1>Days from receipt to a CRL, <span class="g">by the letters\' own dates</span></h1>',
         f'<p class="sub" data-crl-clock="lede">{esc(lede_text(f))}</p>',
         f'<p class="sub">Read from the text of the {f["n"]} distinct Complete Response Letters in the FDA\'s CRL release '
         f'(openFDA transparency/crl, last updated {esc(last_updated)}; snapshot read {esc(snap)}), the same letters as '
         '<a href="/crl">/crl</a> less the ' + str(n_resc) + ' the FDA rescinded as issued in error. Most CRLs open '
         'with a form sentence: "Please refer to your new drug application (NDA) dated and received [date] ...". A '
         'letter on a resubmission adds: "We acknowledge receipt of your amendment dated [date], which constituted a '
         'complete response to our [date] action letter." This page takes those printed dates and counts the calendar '
         'days between them and the letter\'s own date. That is not the FDA\'s review time: the FDA\'s clock can '
         'stop, restart or be extended, and the letters print only some of that (a letter that says a submission '
         'extended the goal date is counted below). Counts of dates only, and no reading of why.</p>',
         '<h2>From receipt to the letter, where no earlier FDA action is named</h2>',
         f'<p class="sub">Letters on an original application (not a supplement) that print the date the application '
         f'was received and name no earlier FDA action on it (no action letter answered, no refuse-to-file letter, '
         f'no resubmission, no tentative approval, no rescinded approval) before the words "completed our review", '
         f'and for whose application number the release holds no earlier CRL. A letter can still leave out an earlier '
         f'action it does not name. '
         + (f'{len(f["dated"])} of the {n} print no received date, only the date the application was dated or '
            f'submitted, used as printed. ' if f["dated"] else '')
         + f'Days are calendar days from that date to the letter\'s date.</p>',
         '<table>' + STATS_HEAD.format("Group") + tr_stats("<b>All of these letters</b>", f["s_first"],
                                                              ' data-clock-row="first-all"') + '</table>',
         '<h3>By the statute section the letter names</h3><table>' + STATS_HEAD.format("Section")]
    by_sec = collections.defaultdict(list)
    for e in f["first"]:
        p = e["r"]["pathway"] or ""
        by_sec["multi" if ";" in p else p].append(e["days_rec"])
    for k in sorted(by_sec, key=lambda k: (k == "", -len(by_sec[k]), k)):
        lab = SECTION_LABEL.get(k, k) if k else "not printed, or not readable"
        B.append(tr_stats(esc(lab), stats(by_sec[k]), f' data-clock-row="sec-{esc(k or "none")}"'))
    B.append('</table><p class="sub">The section as the letter prints it: 505 is the drug section of the Federal Food, '
             'Drug, and Cosmetic Act, 351(a) and 351(k) the biologics and biosimilar sections of the Public Health '
             'Service Act. A letter that prints "505(b)" with no (1) or (2) is counted under 505(b); one that prints two '
             'sections is counted under "more than one printed".</p>')
    B.append('<h3>By letter year</h3><table>' + STATS_HEAD.format("Letter year"))
    for lab, y0, y1 in YEARS:
        B.append(tr_stats(lab, stats([e["days_rec"] for e in f["first"] if y0 <= e["L"]["date"].year <= y1]),
                          f' data-clock-row="year-{y1}"'))
    B.append('</table>')
    B.append(f'<p class="sub" data-crl-clock="major">{len(f["major"])} of these {n} letters say a submission extended '
             'the goal date (most often "a major amendment ... extended the goal date"). Their days are in the counts '
             'above, from receipt to the letter like the rest.</p>')
    rn = f["s_resp"]
    gp = f["s_gap"]
    B += ['<h2>After a response to an earlier FDA letter</h2>',
          f'<p class="sub">Letters on an original application that print the date of a response ("amendment", '
          f'"resubmission" or "submission") and the date of the earlier FDA letter it answered (an action letter, a '
          f'Complete Response Letter, a tentative approval). Where a letter lists several, the latest dated response '
          f'is used, with the latest earlier letter it lists. The earlier letters, as the letters name them: '
          + "; ".join(f'{v} {esc(k)} letter{"s" if v != 1 else ""}' for k, v in
                      sorted(f["kinds"].items(), key=lambda kv: (-kv[1], kv[0]))) + '. '
          f'For {f["in_rel"]} of these {rn[0]} letters, the release also holds a Complete Response Letter of that '
          f'earlier date on the same application number; for the other {rn[0] - f["in_rel"]} it holds none of that date.</p>',
          '<table>' + STATS_HEAD.format("Days")
          + tr_stats("From the response to this letter", rn, ' data-clock-row="resp-letter"')
          + tr_stats("From the earlier FDA letter to the response", gp, ' data-clock-row="resp-gap"') + '</table>']
    left = f["left"]
    st = f["nodate_status"]
    B.append('<h2>Letters not counted</h2><table><tr><th>Reason</th><th>Letters</th></tr>')
    for k in LEFT_ORDER:
        if left[k]:
            B.append(f'<tr data-clock-left="{esc(k)}"><td>{esc(WHY[k][0].upper() + WHY[k][1:])}</td><td>{left[k]}</td></tr>')
    B.append('</table>')
    nd = left["no date"] + left["no opening"]
    if nd:
        B.append(f'<p class="sub" data-crl-clock="nodate">Of the {nd} letters with no readable received date, openFDA\'s '
                 'approval_status field marks ' + "; ".join(f'{v} {esc(k)}' for k, v in st.most_common())
                 + '. In those letters the opening sentence prints no date where other letters print one; in some, '
                 '"(b) (4)" stands there.</p>')
    if f["order"]:
        B.append('<p class="sub" data-crl-clock="order">Dates out of order (openFDA\'s letter date, and the date the '
                 'letter prints): '
                 + "; ".join(f'{letter_cell(e)} ({esc(e["L"]["app_txt"])}, prints '
                             + (f'received {esc(pretty(e["r"]["received"]))}' if e["r"]["received"] and (e["days_rec"] or 0) < 0
                                else f'a response dated {esc(pretty(e["r"]["resub"]))}' if e["r"]["resub"] else '')
                             + ')' for e in f["order"]) + '.</p>')
    counted = sorted((e for e in E if e["group"]), key=lambda e: (e["L"]["date"], e["L"]["app_txt"]), reverse=True)
    B += [f'<h2>Every counted letter ({len(counted)})</h2>',
          '<p class="sub">Newest first. The letter date links its page with the FDA\'s text; PDF is the FDA\'s file. '
          'Days run from the response where the letter prints one, otherwise from receipt.</p>',
          '<table><tr><th>Letter</th><th>Application</th><th>Company (openFDA)</th><th>Section</th>'
          '<th>Received or dated, as printed</th><th>Earlier FDA letter answered</th><th>Response dated</th><th>Days</th></tr>']
    for e in counted:
        L, r = e["L"], e["r"]
        resp = e["group"] == "response"
        rec = (esc(pretty(r["received"])) + ("" if r["rword"] == "received" else f' ({esc(r["rword"])})')
               if r["received"] else "not printed")
        B.append(f'<tr data-clock="{esc(e["slug"] or L["key"])}"><td>{letter_cell(e)}</td><td>{esc(L["app_txt"])}</td>'
                 f'<td>{esc(name_of(L))}</td><td>{esc(r["pathway"] or "")}</td><td>{rec}</td>'
                 f'<td>{esc(pretty(r["answers"])) if resp else "none named"}</td>'
                 f'<td>{esc(pretty(r["resub"])) if resp else ""}</td>'
                 f'<td>{e["days_resp"] if resp else e["days_rec"]}</td></tr>')
    B.append('</table>')
    write_csv(E)
    B.append(f'<p class="sub">Every one of the {f["n"]} letters, counted or not, with each date read and the reason a '
             'letter is left out: <a href="/crl/data/crl-review-clock.csv">crl-review-clock.csv</a> (CC BY 4.0, '
             'please credit pdufa.bio). The dates come from openFDA\'s text of each PDF, which is a scan: where the '
             'scan misreads a date, so does this page, and the PDF is the record. The FDA releases letters '
             'selectively; a count here is what the release holds.</p>'
             '<p class="sub"><a href="/crl/facts">Facts from all released CRLs</a> &middot; '
             '<a href="/crl/companies">every CRL, by company</a> &middot; '
             '<a href="/crl/offices">which FDA office signed each CRL</a> &middot; '
             '<a href="/crl/phrases">what the letters say, term by term</a> &middot; '
             '<a href="/crl">every released letter, by year</a></p>')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(page(title, desc, "/crl/review-clock", B))
    print(f"/crl/review-clock: {f['n']} letters; {n} receipt to letter (median {g(med)} days); {rn[0]} after a response "
          f"(median {g(rn[1])}); not counted {dict(left)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
