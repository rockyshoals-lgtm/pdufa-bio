"""FDA advisory committee votes, question by question, and whether the FDA's final action followed the vote.

Reads adcomm_votes_sourced.json (hand-sourced; each vote count read from the FDA's own minutes or, where the
FDA's minutes could not be reached, the sponsor's own release, and each FDA action from Drugs@FDA, an FDA letter
or press release, or the sponsor's filing) and writes:

  /adcomm/votes/index.html        one card per meeting and application, every voting question with its count
  /adcomm/votes/adcomm-votes.csv  one row per voting question, with the sources
  a short link block on /adcomm (between <!--ADCV:BEGIN--> and <!--ADCV:END-->)

"Followed the vote" is computed, never typed: the overall question (benefit-risk, effectiveness and safety, or
approvability; at most one per meeting, flagged is_overall) is favorable when more members voted yes than no and
unfavorable when more voted no. An approval follows a favorable vote; a Complete Response Letter follows an
unfavorable one. Withdrawn, pending and other actions, ties, and meetings with no overall question are not
counted either way. Facts only: no prediction for any pending application, nothing from any scoring model.
tests/test_adcomm_votes.py guards the data and the page.
"""
import csv
import datetime as dt
import html
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATA = os.path.join(HERE, "adcomm_votes_sourced.json")
OUT = os.path.join(SITE, "adcomm", "votes")
CSV_NAME = "adcomm-votes.csv"
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MONL = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
        "November", "December"]
ACTION_WORD = {"approved": "approved the application", "crl": "issued a Complete Response Letter",
               "withdrawn": "", "pending": "", "other": ""}
B, E = "<!--ADCV:BEGIN-->", "<!--ADCV:END-->"


def esc(s):
    return html.escape(str(s or ""), quote=True)


def pretty(iso):
    d = dt.date.fromisoformat(iso)
    return f"{MONL[d.month]} {d.day}, {d.year}"


def overall(m):
    qs = [q for q in m.get("questions") or [] if q.get("is_overall")]
    return qs[0] if len(qs) == 1 else None


def lean(q, m):
    """favorable / unfavorable / tie for the overall question, or None."""
    if not q:
        return None
    y, n = int(q.get("yes") or 0), int(q.get("no") or 0)
    if y == n:
        return "tie"
    fav = y > n
    if (m.get("yes_means") or "favorable") == "unfavorable":
        fav = not fav
    return "favorable" if fav else "unfavorable"


def followed(m):
    """True / False when the FDA's first action after the meeting can be set against the overall vote."""
    if m.get("follow_not_counted"):
        return None
    lv = lean(overall(m), m)
    a = m.get("fda_action")
    if lv not in ("favorable", "unfavorable") or a not in ("approved", "crl"):
        return None
    return (lv == "favorable") == (a == "approved")


def load():
    d = json.load(io.open(DATA, encoding="utf-8"))
    rows = []
    for m in d.get("meetings", []):
        if m.get("kind") != "product_vote" or not m.get("questions"):
            continue
        if not (str(m.get("vote_source_url", "")).startswith("http") and m.get("vote_source_quote")):
            continue
        if not ISO.match(m.get("meeting_date") or ""):
            continue
        rows.append(m)
    rows.sort(key=lambda m: (m["meeting_date"], m.get("product") or ""), reverse=True)
    return rows


def committee_short(c):
    c = re.sub(r"\s*\([A-Za-z&;,/\- ]+\)", "", c or "").strip()
    return c[:140]


def card(m, today):
    t = (m.get("ticker") or "").strip().upper()
    head = (f'<b>{esc(m.get("product"))}</b>'
            + (f' ({esc(m["application"])})' if m.get("application") else "")
            + (f' &middot; {esc(m.get("sponsor"))}' if m.get("sponsor") else "")
            + (f' &middot; <a href="/ticker/{esc(t)}">{esc(t)}</a>' if t and os.path.isdir(os.path.join(SITE, "ticker", t))
               else (f' &middot; {esc(t)}' if t else "")))
    sub = (f'{esc(pretty(m["meeting_date"]))} &middot; {esc(committee_short(m.get("committee")))}'
           + (f' &middot; for {esc(m["indication"][:1].lower() + m["indication"][1:])}' if m.get("indication") else ""))
    qrows = []
    for q in sorted(m["questions"], key=lambda q: q.get("n") or 0):
        mark = ' <span class="ov">overall question</span>' if q.get("is_overall") else ""
        ab = int(q.get("abstain") or 0)
        qrows.append(f'<tr><td class="qn">Q{esc(q.get("n"))}</td><td>{esc(q.get("text"))}{mark}</td>'
                     f'<td class="v">{int(q.get("yes") or 0)}</td><td class="v">{int(q.get("no") or 0)}</td>'
                     f'<td class="v">{ab}</td></tr>')
    table = ('<table class="qt"><tr><th></th><th>Voting question</th><th>Yes</th><th>No</th><th>Abst.</th></tr>'
             + "".join(qrows) + "</table>")
    a, ad = m.get("fda_action"), m.get("fda_action_date")
    act = ""
    if a in ("approved", "crl") and ad and ISO.match(ad):
        gap = (dt.date.fromisoformat(ad) - dt.date.fromisoformat(m["meeting_date"])).days
        who = "The FDA" if m.get("action_source_type") == "fda" else "The sponsor reported that the FDA"
        act = f'{who} {ACTION_WORD[a]} on {esc(pretty(ad))}, {gap} days after the meeting.'
    elif a == "withdrawn":
        act = "The application was withdrawn" + (f" ({esc(pretty(ad))})" if ad and ISO.match(ad) else "") + "."
    elif a == "pending":
        act = "No FDA action on record yet."
    elif a == "other" and m.get("action_label"):
        act = esc(m["action_label"]) + (f" ({esc(pretty(ad))})" if ad and ISO.match(ad) else "") + "."
    f = followed(m)
    lv = lean(overall(m), m)
    verdict = ""
    if f is True:
        verdict = f' <span class="fy">The FDA\'s action followed the committee\'s {lv} overall vote.</span>'
    elif f is False:
        verdict = f' <span class="fn">The FDA\'s action went against the committee\'s {lv} overall vote.</span>'
    elif lv == "tie":
        verdict = " The overall vote was tied."
    note = f' <span class="q">{esc(m["public_note"])}</span>' if m.get("public_note") else ""
    src = (f' Sources: <a href="{esc(m["vote_source_url"])}" rel="nofollow noopener">'
           f'{"FDA minutes" if m.get("vote_source_type") == "fda" else "sponsor release on the vote"}</a>'
           + (f' &middot; <a href="{esc(m["action_source_url"])}" rel="nofollow noopener">'
              f'{"FDA action" if m.get("action_source_type") == "fda" else "sponsor release on the action"}</a>'
              if str(m.get("action_source_url") or "").startswith("http") and act else "")
           + (f' &middot; <a href="{esc(m["meeting_url"])}" rel="nofollow noopener">FDA meeting page</a>'
              if str(m.get("meeting_url") or "").startswith("https://www.fda.gov") else "") + ".")
    dec = ""
    if t and a in ("approved", "crl") and ad and os.path.isdir(os.path.join(SITE, "fda-decision", f"{t}-{ad}")):
        dec = f' <a href="/fda-decision/{esc(t)}-{esc(ad)}">Decision page</a>.'
    return (f'<div class="row"><div class="t">{head}</div><div class="s">{sub}</div>{table}'
            f'<div class="d">{act}{verdict}{note}{src}{dec}</div></div>')


def main():
    rows = load()
    today = dt.date.today()
    stamp = f"{MONL[today.month]} {today.day}, {today.year}"
    n = len(rows)
    nq = sum(len(m["questions"]) for m in rows)
    with_ov = [m for m in rows if overall(m)]
    fav = sum(1 for m in with_ov if lean(overall(m), m) == "favorable")
    unf = sum(1 for m in with_ov if lean(overall(m), m) == "unfavorable")
    judged = [m for m in rows if followed(m) is not None]
    fol = sum(1 for m in judged if followed(m))
    app_after_neg = sum(1 for m in judged if not followed(m) and m["fda_action"] == "approved")
    crl_after_pos = sum(1 for m in judged if not followed(m) and m["fda_action"] == "crl")
    pend = sum(1 for m in rows if m.get("fda_action") == "pending")
    fda_votes = sum(1 for m in rows if m.get("vote_source_type") == "fda")
    years = sorted({m["meeting_date"][:4] for m in rows})
    span = f"{years[0]}-{years[-1]}" if years else ""

    facts = (f'<div class="card"><b>{n} committee vote{"s" if n != 1 else ""} on a specific application, '
             f'{nq} voting question{"s" if nq != 1 else ""}.</b> '
             + (f'Every count is read from the FDA\'s own minutes. ' if fda_votes == n else
                f'{fda_votes} of the counts are read from the FDA\'s own minutes, the rest from the sponsor\'s release. ')
             + 
             f'Where a meeting had one overall question ({len(with_ov)}), the committee voted favorably {fav} '
             f'time{"s" if fav != 1 else ""} and unfavorably {unf} time{"s" if unf != 1 else ""}. '
             + (f'Of the {len(judged)} that ended in an approval or a Complete Response Letter, the FDA\'s first action '
                f'followed the overall vote {fol} times; it approved after an unfavorable vote {app_after_neg} '
                f'time{"s" if app_after_neg != 1 else ""} and issued a Complete Response Letter after a favorable vote '
                f'{crl_after_pos} time{"s" if crl_after_pos != 1 else ""}. ' if judged else "")
             + (f'{pend} {"have" if pend != 1 else "has"} no FDA action on record yet. ' if pend else "")
             + 'Counts of the cards below, not a prediction for any pending application.</div>')

    by_year = {}
    for m in rows:
        by_year.setdefault(m["meeting_date"][:4], []).append(m)
    body = "".join(f'<h2 id="y{y}">{y}</h2>' + "".join(card(m, today) for m in by_year[y])
                   for y in sorted(by_year, reverse=True)) or "<p>No sourced vote is on record yet.</p>"
    jump = " &middot; ".join(f'<a href="#y{y}">{y}</a>' for y in sorted(by_year, reverse=True))

    os.makedirs(OUT, exist_ok=True)
    with io.open(os.path.join(OUT, CSV_NAME), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["meeting_date", "committee", "product", "application", "sponsor", "ticker", "indication",
                    "question_n", "question", "yes", "no", "abstain", "is_overall", "vote_source_type",
                    "vote_source_url", "fda_action", "fda_action_date", "action_source_type", "action_source_url",
                    "fda_followed_overall_vote"])
        for m in rows:
            f = followed(m)
            for q in sorted(m["questions"], key=lambda q: q.get("n") or 0):
                w.writerow([m["meeting_date"], m.get("committee"), m.get("product"), m.get("application"),
                            m.get("sponsor"), m.get("ticker") or "", m.get("indication"), q.get("n"), q.get("text"),
                            q.get("yes"), q.get("no"), q.get("abstain"), bool(q.get("is_overall")),
                            m.get("vote_source_type"), m.get("vote_source_url"), m.get("fda_action"),
                            m.get("fda_action_date") or "", m.get("action_source_type") or "",
                            m.get("action_source_url") or "", "" if f is None else ("yes" if f else "no")])

    title = f"FDA Advisory Committee Votes {span}: {n} Meetings and the FDA's Decisions | pdufa.bio"  # room for growth (max 100)
    desc = (f"{n} FDA advisory committee votes since {years[0] if years else ''}, each question's yes, no and abstain "
            f"count from the FDA's minutes, and whether the FDA's final action followed the vote.")
    if len(desc) > 158:
        desc = desc[:158].rsplit(" ", 1)[0].rstrip(",;:") + "."
    qa = [("Does the FDA have to follow an advisory committee vote?",
           "No. Advisory committees give the FDA independent advice, and the agency makes the final decision. "
           + (f"On this page the FDA's first action followed the committee's overall vote in {fol} of {len(judged)} "
              "cases that ended in an approval or a Complete Response Letter." if judged else "")),
          ("What does 'followed the vote' mean here?",
           "We take the one question on overall benefit-risk, effectiveness and safety, or approvability, as the FDA "
           "worded it. More yes than no votes is a favorable vote; more no than yes is unfavorable. An approval follows "
           "a favorable vote and a Complete Response Letter follows an unfavorable one. Ties, withdrawals, pending "
           "applications and meetings without such a question are not counted either way. An approval can still be "
           "narrower than what the committee voted on; the card says so where it is."),
          ("Where do the vote counts come from?",
           (f"From the FDA's own meeting minutes for {fda_votes} of the {n} meetings" if fda_votes < n else
            "From the FDA's own meeting minutes for every meeting") + ", quoted from the document "
           "linked on each card. Where the FDA's minutes could not be read, from the sponsor's own press release "
           "or SEC filing, and the card says so. A news report alone is never the source of a count."),
          ("Is this every advisory committee meeting?",
           "No. It lists meetings that voted on a specific drug or biologic application and whose counts we have "
           "read from a primary source. General-topic meetings, device panels and meetings without a vote are on "
           "the advisory committee calendar instead.")]
    jsonld = json.dumps({"@context": "https://schema.org", "@type": "FAQPage",
                         "mainEntity": [{"@type": "Question", "name": q,
                                         "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qa]},
                        ensure_ascii=False)
    dsld = json.dumps({"@context": "https://schema.org", "@type": "Dataset",
                       "name": "FDA advisory committee votes by question, with the FDA's final action",
                       "description": f"{n} FDA advisory committee meetings on specific applications, {nq} voting "
                                      "questions with yes, no and abstain counts, and the FDA's first action after "
                                      "each meeting, every count and action linked to its primary source.",
                       "url": "https://www.pdufa.bio/adcomm/votes", "isAccessibleForFree": True,
                       "license": "https://creativecommons.org/licenses/by/4.0/",
                       "creator": {"@type": "Organization", "name": "pdufa.bio", "url": "https://www.pdufa.bio/"},
                       "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv",
                                         "contentUrl": f"https://www.pdufa.bio/adcomm/votes/{CSV_NAME}"}]},
                      ensure_ascii=False)
    faq = "".join(f'<div class="card"><b>{esc(q)}</b><div style="color:#9db3d4;font-size:14px;margin-top:6px">'
                  f'{esc(a)}</div></div>' for q, a in qa)

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="https://www.pdufa.bio/adcomm/votes"><meta name="robots" content="index,follow,max-image-preview:large"><meta name="theme-color" content="#02060d"><link rel="icon" type="image/svg+xml" href="/favicon.svg"><meta property="og:type" content="article"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="https://www.pdufa.bio/adcomm/votes"><style>*{{box-sizing:border-box}}body{{margin:0;background:#02060d;color:#f2f6fc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;line-height:1.6}}a{{color:#6fb6ff;text-decoration:none}}a:hover{{text-decoration:underline}}.wrap{{max-width:860px;margin:0 auto;padding:22px 18px 60px}}.top{{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #1a3358;padding-bottom:12px}}.brand{{font-size:19px;font-weight:800}}.brand b{{color:#e3ba5e}}.nav a{{color:#a7bcd9;font-size:13px;margin-left:14px}}h1{{font-size:26px;line-height:1.2;margin:10px 0 6px}}h2{{font-size:18px;color:#e3ba5e;margin:26px 0 8px}}.bc{{font-size:12px;color:#94a9c9;margin:16px 0 4px}}.bc a{{color:#94a9c9}}.sub{{color:#a7bcd9;font-size:15px}}p{{max-width:78ch}}.card{{background:#0c1d38;border:1px solid #1e3a63;border-radius:12px;padding:14px 16px;margin:14px 0;color:#cfe0f5;font-size:14.5px}}.row{{background:#0c1d38;border:1px solid #1e3a63;border-radius:10px;padding:11px 13px;margin:10px 0}}.row .t{{font-size:14.5px}}.row .s{{color:#94a9c9;font-size:12.5px;margin-top:2px}}.row .d{{color:#9db3d4;font-size:13.5px;margin-top:6px}}.row .q{{color:#cfe0f5}}.qt{{width:100%;border-collapse:collapse;margin-top:8px;font-size:13px;color:#cfe0f5}}.qt th{{text-align:left;color:#94a9c9;font-weight:600;border-bottom:1px solid #1e3a63;padding:4px}}.qt td{{border-bottom:1px solid #132a4a;padding:5px 4px;vertical-align:top}}.qt .v{{text-align:right;white-space:nowrap;width:44px}}.qt .qn{{color:#94a9c9;white-space:nowrap;width:30px}}.ov{{color:#e3ba5e;font-size:11.5px;white-space:nowrap}}.fy{{color:#8fd3a8}}.fn{{color:#f2b56b}}.note{{font-size:12px;color:#94a9c9;line-height:1.6}}footer{{border-top:1px solid #1a3358;margin-top:34px;padding-top:16px;font-size:11.5px;color:#94a9c9;line-height:1.6}}footer b{{color:#a7bcd9}}</style><script type="application/ld+json">{jsonld}</script><script type="application/ld+json">{dsld}</script></head><body><div class="wrap"><div class="top"><a class="brand" href="/">pdufa<b>.bio</b></a><div class="nav"><a href="/calendar">Calendar</a><a href="/decisions">Decisions</a><a href="/adcomm">AdComs</a><a href="/research">Research</a></div></div><div class="bc"><a href="/">Home</a> &rsaquo; <a href="/adcomm">Advisory committees</a> &rsaquo; Votes and outcomes</div><h1>FDA advisory committee votes and what the FDA decided</h1><div class="sub">Every FDA drug and biologic advisory committee vote on a specific application that we have read from a primary source since {esc(years[0] if years else '')}: each voting question as the FDA worded it, the yes, no and abstain count, and the FDA's first action on that application afterwards, with whether it followed the committee's overall vote.</div>{facts}<div class="sub" style="font-size:14px">Newest meeting first. Jump to {jump}. Download every question with its counts and links: <a href="/adcomm/votes/{CSV_NAME}">{CSV_NAME}</a>. The full meeting calendar, with every Federal Register notice since 2020, is on the <a href="/adcomm">advisory committee page</a>.</div>{body}<div class="note" style="margin-top:12px"><b>What this list is:</b> meetings that voted on a named application and whose counts we have read, not every meeting the FDA held. The FDA action shown is the first one after the meeting on that application. Updated {esc(stamp)}.</div><h2>Questions</h2>{faq}<p class="note">Historical record of committee votes and FDA actions, each linked to its source. Not a prediction about any pending application, and not investment advice.</p><footer><b>Not affiliated with or endorsed by the FDA.</b> pdufa.bio is an independent publication with no affiliation with, endorsement by, sponsorship by, or connection to the U.S. Food and Drug Administration. <b>Informational and educational purposes only. Not investment advice.</b> Verify every vote and date against primary FDA, SEC or company documents.<br><br>&copy; {today.year} pdufa.bio. All rights reserved.</footer></div><script src="/cmdk.js" defer></script></body></html>"""
    io.open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page)

    # one link block on /adcomm, above the Federal Register calendar section
    p = os.path.join(SITE, "adcomm", "index.html")
    if os.path.exists(p) and n:
        doc = io.open(p, encoding="utf-8", errors="replace").read()
        doc = re.sub(re.escape(B) + r".*?" + re.escape(E), "", doc, flags=re.S)
        blk = (f'{B}<div style="background:#0c1d38;border:1px solid #1e3a63;border-radius:12px;padding:14px 16px;'
               f'margin:18px 0"><b><a href="/adcomm/votes">Advisory committee votes and outcomes, {esc(span)}</a></b>'
               f'<div style="color:#9db3d4;font-size:14px;margin-top:4px">{n} votes on named applications, every '
               f'question\'s count from the FDA\'s minutes, and whether the FDA\'s final action followed the vote '
               + (f'({fol} of {len(judged)} times)' if judged else "") + f'.</div></div>{E}')
        i = doc.find("<!--ADCH:BEGIN-->")
        if i < 0:
            i = doc.find("<!--HUBFAQ:BEGIN-->")
        if i >= 0:
            doc = doc[:i] + blk + doc[i:]
            io.open(p, "w", encoding="utf-8", newline="").write(doc)
    print(f"wrote /adcomm/votes ({n} meetings, {nq} questions, followed {fol} of {len(judged)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
