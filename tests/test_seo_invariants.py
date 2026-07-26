"""CI guard (SEO-1): no public <title> or social/description meta ever ADVERTISES a score.

Google is still serving stale index entries that title us with "ODIN Scores", "AI Approval
Scores", and an AI summary quoting "93.6% approval rate" -- which is the leaked ODIN v14 metric
(HO AUC 0.9363) that the MCP itself flags KNOWN LEAKED. The live pages are already clean; this
test makes sure a future edit can never re-introduce the off-brand language that /about and
/why-no-approval-probability promise we never use.

    python tests/test_seo_invariants.py

NEGATION IS NOT A VIOLATION. /about's meta says "No approval probabilities, no win rates" and
holding.html says "no individual-drug approval probabilities". Those are the brand PROMISE, the
literal opposite of the offence. So a match is only a violation when it is NOT immediately
preceded by a negation cue (no/without/never/zero/refuse/don't). Advertising the thing fails;
disavowing it passes.
"""
import os, re, sys

ROOT = "pdufa_site_src"
# the banned claims, as whole-word/phrase patterns
BANNED = re.compile(
    r"\b(ODIN"
    r"|AI[- ](?:approval[- ])?scor\w+"
    r"|approval[- ]probabilit\w+"
    r"|win[- ]rate\w*"
    r"|TIER[_ ]?1"
    r"|\d{2}(?:\.\d)?%\s+approval\s+rate)\b", re.I)
# a negation immediately before the claim flips it from advertisement to disavowal
NEG = re.compile(r"\b(no|without|never|zero|not|refuse\w*|don'?t|doesn'?t|won'?t)\b[\s\w,'-]{0,40}$", re.I)
# "Odin Catalyst LLC" is the operating COMPANY, not the model. The ban is on the scoring engine.
LEGAL_ENTITY = re.compile(r"Odin\s+Catalyst", re.I)

# only fields a searcher/social-card actually sees
FIELD = re.compile(
    r"<title>(.*?)</title>"
    r'|<meta[^>]+(?:name|property)="(?:description|og:title|og:description|twitter:title|twitter:description)"[^>]*content="([^"]*)"',
    re.I | re.S)


def violations_in(html):
    out = []
    for m in FIELD.finditer(html):
        text = m.group(1) or m.group(2) or ""
        for b in BANNED.finditer(text):
            pre = text[:b.start()]
            if NEG.search(pre):          # "No approval probabilities" -> the promise, not a breach
                continue
            # "Odin Catalyst [LLC]" is the company name, not the ODIN scoring model
            if b.group(0).lower() == "odin" and LEGAL_ENTITY.match(text[b.start():b.start() + 14]):
                continue
            out.append((text.strip()[:90], b.group(0)))
    return out


def main():
    if not os.path.isdir(ROOT):
        print(f"  SKIP {ROOT} not present"); return 0
    fail = 0
    checked = 0
    for dp, _, fns in os.walk(ROOT):
        # skip backups and retired copies
        if any(seg.startswith(("_", ".")) or seg.endswith("_bak8") for seg in dp.split(os.sep)):
            continue
        for fn in fns:
            if not fn.endswith(".html"):
                continue
            p = os.path.join(dp, fn)
            try:
                html = open(p, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            checked += 1
            for text, hit in violations_in(html):
                print(f"  FAIL {p}: public meta advertises '{hit}' -> \"{text}\"")
                fail += 1
    if fail:
        print(f"\n{fail} SEO-invariant violation(s). Public titles/meta must not advertise scores. DO NOT PUBLISH.")
        return 1
    print(f"OK -- {checked} HTML files, no public title/meta advertises ODIN / AI score / "
          f"approval probability / win rate / TIER_1.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
