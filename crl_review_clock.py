# -*- coding: utf-8 -*-
"""crl_review_clock.py -- read the dates a Complete Response Letter prints about its own review.

Shared by build_crl_review_clock.py (the page and CSV). Most CRLs open with the same FDA form sentence:

    "Please refer to your new drug application (NDA) dated and received March 10, 2017, and your amendments,
     submitted pursuant to section 505(b)(2) of the Federal Food, Drug, and Cosmetic Act for ..."

and a letter on a resubmission adds:

    "We acknowledge receipt of your amendment dated February 26, 2021, which constituted a complete response to our
     November 27, 2020 action letter."

This module reads, from the text openFDA released for each letter, only what the letter prints:

  * received:  the date the opening sentence says the application was received ("received", or "dated and
               received"); where it prints only "dated" or "submitted" (or the date before the noun, "your May 16,
               2023, new drug application"), that date, flagged "dated" or "submitted"
  * pathway:   the statute section(s) the opening sentence names, as printed: 505(b), 505(b)(1), 505(b)(2), 351(a),
               351(k); more than one is joined with "; "
  * earlier:   whether the letter, before "completed our review", names an earlier FDA action on the application
               (an action letter it answers, a refuse-to-file letter, a resubmission, a tentative approval, a
               rescinded approval)
  * resub / answers:  for a letter that says an amendment "constituted a complete response to our <date> ...
               letter", the amendment's date and the earlier letter's date (the latest pair, when it lists several),
               and answer_kind, the earlier letter's kind as printed (action, complete response, tentative approval,
               approvable, not approvable, refuse to file)
  * rtf:       whether the text before "completed our review" names a refuse-to-file letter
  * heading:   "corrected complete response" or "acknowledge incomplete response" when the FDA heads the letter so
  * major:     whether it says a submission extended the goal date ("a major amendment ... extended the goal date",
               "submission of which extended the NDA review goal date") or the review clock

Dates the FDA redacted or the scan garbled are not guessed: the field is None. Nothing here reads why a letter was
sent.
"""
import datetime as dt
import re

MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
D = r"(?:" + "|".join(MONTHS) + r")\s+\d{1,2}\s*,\s*(?:19|20)\d{2}"
DLIST = D + r"(?:\s*,?\s*(?:and\s+)?" + D + r")*"
RECEIVED = re.compile(r"\b(?:received|recieved|feceived)\s*,?\s*(?:on\s+)?(" + D + ")", re.I)
DATED = re.compile(r"\b(?:dated|submitted)\s*,?\s*(?:and\s+)?(?:on\s+)?(" + D + ")", re.I)
PATHWAY = re.compile(r"section\s*(505\s*\(\s*b\s*\)(?:\s*\(\s*[12]\s*\))?|351\s*\(\s*[ak]\s*\))", re.I)
KIND = r"(?:action|complete\s+response|tentative\s+approval|approvable|not\s+approvable|refus\w*[\s-]+to[\s-]+file)"
# "responses to our [dates, or scan noise] action letters": anything but a full stop may stand between "our" and the kind
EARLIER = re.compile(r"responses?\s+to\s+our\s+[^.]{0,80}?" + KIND + r"\s+letters?|refus\w*[\s-]+to[\s-]+file"
                     r"|resubmi|rescind|tentative(?:ly)?\s+approv|not\s+approvable|(?<!this )approvable\s+letter"
                     r"|(?<!this )complete\s+response\s+letter", re.I)
# an amendment (or resubmission, or submission) and the earlier FDA letter it answered, as the letter pairs them
NOUN = r"(?:amendments?|resubmissions?|submissions?)"
ANSWERS = [
    # "your amendment dated D[, received D], which constituted a complete response to our D action letter"
    re.compile(NOUN + r"\s*,?\s+dated\s*:?\s+(" + DLIST + r")\s*,?\s*(?:received\s+" + D + r"\s*,?\s*)?which\s+constitut\w+"
               r"\s+(?:a\s+|your\s+)?(?:complete\s+)?responses?\s+to\s+our\s+(" + DLIST + r")\s*,?\s*(" + KIND + r")\s+letters?",
               re.I),
    # "The April 9, 2015, submission constituted a complete response to our November 24, 2014, action letter", and
    # "your September 20, 2024, and January 23, 2026, amendments, which constituted complete responses to our May 16,
    # 2024, and March 20, 2025, action letters"
    re.compile(r"\b(" + DLIST + r")\s*,?\s*" + NOUN + r"\s*,?\s+(?:which\s+)?constitut\w+\s+(?:a\s+|your\s+)?(?:complete\s+)?"
               r"responses?\s+to\s+our\s+(" + DLIST + r")\s*,?\s*(" + KIND + r")\s+letters?", re.I),
    # "The July 30, 2012, submission constituted a complete response to our action letter dated April 22, 2010"
    re.compile(r"\b(" + D + r")\s*,?\s*" + NOUN + r"\s+constitut\w+\s+(?:a\s+|your\s+)?(?:complete\s+)?responses?\s+to\s+our"
               r"\s+(" + KIND + r")\s+letter\s+dated\s+(" + D + ")", re.I),
    # "your resubmission dated March 10, 2025, after our September 25, 2022, Refusal to File letter"
    re.compile(NOUN + r"\s+dated\s+(" + D + r")\s*,?\s*after\s+our\s+(" + D + r")\s*,?\s*(" + KIND + r")\s+letter", re.I),
]
# the letter says a submission extended the goal date: "a major amendment ... extended the goal date", or (NDA 202293,
# 2012) "The updated clinical trial data, submission of which extended the NDA review goal date"
MAJOR = re.compile(r"(?:major\s+amendment.{0,120}?|submission\s+of\s+which\s+)extended\s+the\s+(?:\w+\s+){0,3}"
                   r"(?:goal\s+date|review\s+clock|action\s+date)", re.I | re.S)
RTF = re.compile(r"refus\w*[\s-]+to[\s-]+file", re.I)
# a letter the FDA heads as something other than a plain CRL: a corrected reissue, or an acknowledgement
HEADING = re.compile(r"\b(CORRECTED\s+COMPLETE\s+RESPONSE|ACKNOWLEDGE\s+INCOMPLETE\s+RESPONSE)\b")
# the date the application is dated, printed before the noun: "your May 16, 2023, new drug application"
APPDATE = re.compile(r"refer\s+to\s+your\s+(" + D + r")\s*,?\s*(?:new\s+drug|biologics?\s+license|abbreviated\s+new\s+drug)"
                     r"\s+application", re.I)
OPEN = re.compile(r"refer\s+to\s+your\b", re.I)
REVIEWED = re.compile(r"completed\s+(?:our|its|the)\s+review|cannot\s+(?:tentatively\s+)?approve", re.I)


def day(s):
    return dt.datetime.strptime(re.sub(r"\s*,\s*", ", ", re.sub(r"\s+", " ", s.strip())), "%B %d, %Y").date()


def dates(s):
    return [day(x) for x in re.findall(D, s)]


def norm(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def parts(text):
    """(opening sentence, the text before 'completed our review'). Empty strings when the letter has no opening."""
    t = norm(text)
    m = OPEN.search(t)
    if not m:
        return "", ""
    rest = t[m.start():]
    e = REVIEWED.search(rest)
    pre = rest[:e.start()] if e else rest[:1500]
    # the opening sentence ends at the statute ("submitted under/pursuant to") or the next "We"
    s = re.search(r"\bsubmitted\s+(?:under|pursuant)|\bunder\s+section|\bWe\s", pre[12:])
    opening = pre[:12 + s.start()] if s else pre[:400]
    return opening, pre


def read(text):
    opening, pre = parts(text)
    t = norm(text)
    h = HEADING.search(t[:800])
    out = {"received": None, "rword": None, "pathway": None, "earlier": False, "resub": None, "answers": None,
           "major": bool(MAJOR.search(t[:6000])), "opening": bool(opening), "answer_kind": None,
           "rtf": bool(RTF.search(pre)), "heading": re.sub(r"\s+", " ", h.group(1)).lower() if h else None}
    if not opening:
        return out
    m = RECEIVED.search(opening)
    if m:
        out["received"], out["rword"] = day(m.group(1)), "received"
    else:
        m = DATED.search(opening)
        if m:
            out["received"], out["rword"] = day(m.group(1)), m.group(0).split()[0].strip(",").lower()
        else:
            m = APPDATE.search(opening)
            if m:
                out["received"], out["rword"] = day(m.group(1)), "dated"
    # the statute is named right after the opening sentence ("submitted pursuant to section 505(b)(2) ..."); a letter
    # that prints more than one section (NDA 218258: "section 505(b)/pursuant to section 505(b)(2)") keeps them all
    secs = []
    for m in PATHWAY.finditer(pre[:len(opening) + 200]):
        k = re.sub(r"\s+", "", m.group(1)).lower()
        if k not in secs:
            secs.append(k)
    out["pathway"] = "; ".join(secs) or None
    out["earlier"] = bool(EARLIER.search(pre))
    best = None
    for i, rx in enumerate(ANSWERS):
        for m in rx.finditer(pre):
            if i == 2:
                a, b, kind = dates(m.group(1)), dates(m.group(3)), m.group(2)
            else:
                a, b, kind = dates(m.group(1)), dates(m.group(2)), m.group(3)
            if a and b and (best is None or a[-1] > best[0]):
                k = re.sub(r"\s+", " ", kind).lower()
                best = (a[-1], b[-1], "refuse to file" if k.startswith("refus") else k)
    if best:
        out["resub"], out["answers"], out["answer_kind"] = best
    return out
