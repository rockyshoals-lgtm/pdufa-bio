# -*- coding: utf-8 -*-
"""test_plain_language.py -- the spec's 'never say' rules, the mechanical ones, enforced in CI.

Red team standing spec 2026-08-12, section 2.4: 'Automate what's mechanical so my review is
spent on judgement, not spellcheck.' These are the rules a regex can hold without judgement:

  1. A CRL is never described as a rejection or denial. 'Declined in current form' is the
     house phrasing; a CRL is not final and many drugs are approved after one. The homepage
     shipped 'a CRL, which is a rejection' for weeks before the spec landed -- this guard
     exists because that happened.
  2. 'FDA rejected/denied' never appears as an assertion. The FDA issues CRLs and refusals to
     file; 'rejected' is the tabloid verb that makes us wrong.
  3. 'Cure rate' never appears. Response is not cure and is not survival.
  4. Any page describing an accelerated approval carries the conditional language (confirm /
     withdraw / conditional) -- the conditionality IS the fact.
  5. Patent-cliff/LOE claims carry the 'earliest date, not a guarantee' framing. Dormant until
     that surface ships; armed the day it does.

Deliberate allowances, each proven necessary by the pre-guard sweep:
  - NEGATED didactic forms pass: 'Is a CRL a rejection? Not permanently.' answers the exact
    question searchers ask, and the answer is no.
  - 'refused to file' passes: Refuse-to-File is a real FDA action, precisely named (MRNA page).
  - 'success rate' passes only on /clinical-trial-success-rates, where phase-transition success
    rates are the page's subject and the industry's own term.

What stays HUMAN judgement, not regex: cross-trial comparisons, n-adjacency on statistical
claims, source-actually-says-it verification. A regex confident enough to hold those would lie.
"""
import glob, html, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")

NEG = re.compile(r"\bnot\b|\bno\b|\bnever\b|\bisn't\b|\bnot a\b|\brather than\b", re.I)


def text_of(doc):
    t = re.sub(r"<script.*?</script>", " ", doc, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t)


def main():
    bad = []
    for p in glob.glob(os.path.join(SITE, "**", "index.html"), recursive=True):
        rel = "/" + os.path.relpath(os.path.dirname(p), SITE).replace("\\", "/")
        rel = "/" if rel == "/." else rel
        txt = text_of(open(p, encoding="utf-8", errors="replace").read())

        # 1. CRL described as rejection/denial. The negation must live in the SAME clause
        #    (backward window + matched span) -- 'A CRL is not final' one sentence later does
        #    not excuse 'a CRL, which is a rejection' (the homepage shipped exactly that, and
        #    the first version of this guard excused it with a forward-looking window).
        #    Didactic question forms ('Is a CRL a rejection?') pass when the ANSWER that
        #    follows negates.
        for m in re.finditer(r"(?:CRL|Complete Response Letter)[^.?!]{0,90}"
                             r"\b(?:rejection|rejected|denial|denied)\b"
                             r"|\b(?:rejection|rejected|denial|denied)\b[^.?!]{0,90}"
                             r"(?:CRL|Complete Response Letter)", txt, re.I):
            if "?" in txt[m.start():m.end() + 3]:
                if NEG.search(txt[m.end():m.end() + 80]):
                    continue          # question asked, answer says no
            elif NEG.search(txt[max(0, m.start() - 40):m.end()]):
                continue              # negated in its own clause
            win = txt[max(0, m.start() - 40):m.end() + 40]
            bad.append((rel, "S3", f"CRL described as rejection: ...{win.strip()[:110]}..."))

        # 2. 'FDA rejected/denied' as assertion ('refused to file' = RTF, allowed)
        for m in re.finditer(r"\bFDA\s+(?:rejected|denied|refused)\b(?!\s+(?:even\s+)?to file)",
                             txt, re.I):
            win = txt[max(0, m.start() - 40):m.end() + 60]
            if not NEG.search(win):
                bad.append((rel, "S3", f"'FDA rejected/denied' assertion: "
                                       f"...{win.strip()[:110]}..."))

        # 3. cure rate anywhere; success rate off its own subject page
        if re.search(r"\bcure rate\b", txt, re.I):
            bad.append((rel, "S3", "'cure rate' -- response is not cure"))
        if re.search(r"\bsuccess rate\b", txt, re.I) \
                and rel != "/clinical-trial-success-rates":
            bad.append((rel, "S3", "'success rate' outside the phase-transition page"))

        # 4. accelerated approval without its conditional nature
        if re.search(r"\baccelerated approval\b", txt, re.I) \
                and not re.search(r"confirm|withdraw|conditional|verify", txt, re.I):
            bad.append((rel, "S4", "accelerated approval stated without conditional language"))

        # 5. patent cliff / LOE without the 'earliest date, not a guarantee' framing
        if re.search(r"\bloss of exclusivity\b|\bpatent cliff\b|\bloses its last patent\b",
                     txt, re.I) \
                and not re.search(r"earliest date|not a guarantee|settlement", txt, re.I):
            bad.append((rel, "S4", "LOE/cliff claim without the earliest-date disclosure"))

    if bad:
        print(f"FAIL: {len(bad)} plain-language violation(s) (spec 2026-08-12).")
        for rel, sev, msg in bad[:12]:
            print(f"   [{sev}] {rel}: {msg}")
        print("\n   House phrasing: a CRL 'declines to approve in its current form'; the FDA")
        print("   'issues a CRL', it does not 'reject'. See the plain-language spec, part 1.3.")
        return 1
    print("  PASS: no CRL-as-rejection, no 'FDA rejected' assertions, no cure/success-rate "
          "misuse, accelerated approvals conditional, LOE claims framed honestly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
