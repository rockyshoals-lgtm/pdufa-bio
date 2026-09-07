# -*- coding: utf-8 -*-
"""No public page may carry trading-strategy vocabulary.

Red team 2026-09-06d, Layer 2 hard boundary: the internal conference torque tool speaks in
entry windows, exit windows, torque scores, tier boosts, IV-cheapness skip rules and
position sizes. The site's entire position is that it does none of that -- the manifesto
bans approval probabilities, buy/sell/sizing calls and composite scores by name, and the
two clones that copied us this month would frame a screenshot of pdufa.bio saying
"the runup is the trade". Nothing from that tool may be imported by any site build step;
this guard asserts the RENDER so it cannot happen by accident either.

BANNED TOKENS (case-insensitive, whole-phrase):
  "entry window", "exit window", "torque", "position size", "position sizing",
  "the runup is the trade", "the run-up is the trade", "never hold through",
  "am i too late", "sell volatility", "buy calls", "buy puts", "sniper",
  "ALPHA/BETA/GAMMA" used as tiers (regex below), "kelly", "half-kelly",
  "optimal entry", "best day to buy", "sizing multiplier".
Historical measurements stay allowed; a measurement with a verb does not.
"""
import glob
import io
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")

BANNED = [
    r"\bentry window", r"\bexit window", r"\btorque\b", r"\bposition siz(?:e|ing)\b",
    r"\bthe run-?up is the trade\b", r"\bnever hold through\b", r"\bam i too late\b",
    r"\bsell volatility\b", r"\bbuy (?:calls|puts)\b", r"\bsniper\b",
    r"\b(?:half-)?kelly\b", r"\boptimal entry\b", r"\bbest day to buy\b",
    r"\bsizing multiplier\b",
    # tier names used as an investment grade ("ALPHA 5% / BETA 4% / GAMMA 2%")
    r"\b(?:ALPHA|BETA|GAMMA|DELTA|OMEGA)\s*(?:tier|\d+(?:\.\d+)?\s*%)",
]
SKIP = re.compile(r"[\\/](?:node_modules|_backup|\.git)[\\/]")


def _visible_text(doc):
    doc = re.sub(r"<script[\s\S]*?</script>", " ", doc, flags=re.I)
    doc = re.sub(r"<style[\s\S]*?</style>", " ", doc, flags=re.I)
    doc = re.sub(r"<!--[\s\S]*?-->", " ", doc)
    return re.sub(r"<[^>]+>", " ", doc)


def test_no_strategy_vocabulary_on_public_pages():
    pats = [re.compile(p, re.I) for p in BANNED]
    bad = []
    for p in sorted(glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True)):
        if SKIP.search(p):
            continue
        text = _visible_text(io.open(p, encoding="utf-8", errors="replace").read())
        for pat in pats:
            m = None
            for cand in pat.finditer(text):
                # A disclaimer that NAMES the thing we do not do is the opposite of a
                # violation ("no entry or exit signals, no position sizing" on /about).
                # Negated within the preceding few words = allowed.
                before = text[max(0, cand.start() - 40):cand.start()].lower()
                if re.search(r"\b(?:no|not|never|without|nor)\b[^.]{0,30}$", before):
                    continue
                m = cand
                break
            if m:
                rel = os.path.relpath(p, SITE).replace("\\", "/")
                ctx = re.sub(r"\s+", " ", text[max(0, m.start() - 40):m.end() + 40]).strip()
                bad.append(f"/{rel}: {m.group(0)!r} ... {ctx!r}")
                break
    assert not bad, ("strategy vocabulary on public page(s) -- the Layer 2 boundary:\n  "
                     + "\n  ".join(bad[:25]))


if __name__ == "__main__":
    test_no_strategy_vocabulary_on_public_pages()
    print("OK")
