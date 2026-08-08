# -*- coding: utf-8 -*-
"""fix_meta_lengths.py -- make titles and meta descriptions the length search engines will show.

Bing Webmaster Tools inspected /sls and returned exactly two errors: "Title too long" and "Meta
Description too long or too short". Checking the rest of the site, those are not one page's
problem: 264 of 473 indexable pages have a description over 160 characters and 188 have a title
over 65. Everything past the limit is cut off in the result, so the part that would persuade
someone to click is the part nobody sees.

All 264 are too LONG. None are too short and none are missing, which matters: this script only ever
removes or rewrites text. It never pads a description to reach a minimum, because padding means
writing sentences to hit a character count, and those sentences would be filler on a site that
sells facts.

THREE CLASSES, HANDLED DIFFERENTLY

  * TICKER HUBS (148). Rebuilt from the dataset. These were the worst offenders at up to 376
    characters, and length was not their only problem: OTLK's description contained the fragment
    "- (NO, LYTENAVA (bevacizumab-vikg, ONS-5010), bevacizumab in ..." where a data field had
    leaked into prose. Rebuilding from structured fields removes the junk rather than truncating
    around it. Company names also get the legal boilerplate trimmed, so "Takeda Pharmaceutical
    Company Limited American Depositary Shares (each representing 1/2 of a share of)" becomes
    "Takeda Pharmaceutical Company Limited" -- still the company's real name, minus the ADS clause
    that was eating the whole description.

  * DECISION PAGES (95). Rebuilt from ticker, date, outcome and drug, which is what the page is.

  * EVERYTHING ELSE (21). Trimmed at a word boundary. These are hand-written and mostly good; they
    just run long, so cutting is safer than rewriting.

TITLES ARE TREATED MORE CAUTIOUSLY THAN THE LIMIT SUGGESTS. Only titles over 100 characters are
shortened. /calendar currently ranks #3 on Bing at 35 characters and is fine, but several pages sit
just over 65, and rewriting the title of a page that already ranks is the single edit most likely
to go backwards. The 140-character decision-page titles are indefensible at any threshold and get
fixed; the marginal ones are left alone deliberately.

    python fix_meta_lengths.py [--dry-run]
"""
import argparse, glob, html, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
STATE = os.path.join(HERE, "_sitemap_lastmod.json")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")

DESC_MAX, TITLE_HARD = 158, 100
D_RE = re.compile(r'(<meta name="description" content=")([^"]*)(")', re.I)
OG_RE = re.compile(r'(<meta property="og:description" content=")([^"]*)(")', re.I)
T_RE = re.compile(r"(<title[^>]*>)(.*?)(</title>)", re.S)

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Legal-entity boilerplate that carries no search value and devours the character budget.
BOILER = re.compile(
    r"\s*(American Depositary Shares?.*$|ADSs?.*$|\(each representing.*$"
    r"|, Inc\.?$|,? Incorporated$|,? Corporation$|,? Corp\.?$|,? Ltd\.?$|,? Limited$|,? plc$"
    r"|,? S\.A\.?$|,? N\.V\.?$|,? AG$|,? Co\.,? Ltd\.?$)", re.I)


def short_company(name, ticker):
    n = re.sub(r"\s+", " ", str(name or "")).strip()
    prev = None
    while n and n != prev:            # strip repeatedly: "X Company Limited American Depositary…"
        prev = n
        n = BOILER.sub("", n).strip(" ,")
    return n or ticker


def trim(s, limit=DESC_MAX):
    """Cut at a word boundary. No ellipsis: a truncated sentence reads as broken, and the string
    is a summary rather than a quotation, so it does not need to signal omission."""
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) <= limit:
        return s
    cut = s[:limit]
    # Prefer the last complete sentence. Cutting at a word boundary still leaves "...Sourced from"
    # dangling, which reads as a broken page rather than a summary; 22 descriptions ended that way
    # on the first pass.
    dot = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    if dot > limit * 0.5:
        return cut[:dot + 1]
    # No sentence break in range: fall back to the last clause break and close it. Ending at a
    # word boundary alone leaves "...with dates, locations, and presenting", which reads as a
    # truncated page; ending at the comma gives "...with dates, locations." which reads finished.
    com = max(cut.rfind(", "), cut.rfind("; "))
    if com > limit * 0.5:
        return cut[:com] + "."
    sp = cut.rfind(" ")
    if sp > limit * 0.6:
        cut = cut[:sp]
    cut = cut.rstrip(" ,;:-\u00b7")
    # Close, or drop, a parenthesis the cut left hanging. "(Inoperable (unresectable) locally
    # advanced" reads as a broken string rather than a shortened one.
    return balance(cut)


def balance(s):
    """Close a description left hanging on an open parenthesis.

    Six pages already shipped like this before today, e.g. "Learn the common reasons (efficacy,
    safety." -- whatever generated them cut inside a parenthetical. They were under the length
    limit so nothing flagged them, but an unclosed bracket in a search result reads as a broken
    page, which is the opposite of the impression this site needs to make."""
    s = s.rstrip()
    need = s.count("(") - s.count(")")
    if need > 0:
        # CLOSE the bracket rather than delete back to it. Deleting cost AZN's description 100 of
        # its 153 characters -- the unmatched "(" was near the front, so cutting to it threw away
        # the entire indication and left "AZN's FDA PDUFA date is Dec 31 2026 for Camizestrant."
        # Closing keeps every fact that was already there.
        body = s[:-1] if s.endswith((".", "!", "?")) else s
        tail = s[-1] if s.endswith((".", "!", "?")) else "."
        closed = body.rstrip(" ,;:-") + ")" * need + tail
        if len(closed) <= DESC_MAX:
            return closed
        while s.count("(") > s.count(")"):      # no room: fall back to cutting
            i = s.rfind("(")
            if i < 0:
                break
            s = s[:i].rstrip(" ,;:-")
    if s and not s.endswith((".", "!", "?")):
        s += "."
    return s


def clean_clause(s, limit):
    """A fragment safe to put in front of a searcher.

    Two failures this exists to prevent, both seen in the first pass:
    "KEYTRUDA (pembrolizumab) plus Padcev (enfortumab." -- cut inside a parenthesis, so the drug
    name is wrong rather than merely short; and "Complete Response Letter. treatment of ..." --
    a clause starting lower-case after a full stop.
    """
    s = re.sub(r"\s+", " ", str(s or "")).strip(" :;,-")
    if not s:
        return ""
    if len(s) > limit:
        cut = s[:limit]
        sp = cut.rfind(" ")
        s = cut[:sp] if sp > limit * 0.5 else cut
    # Drop a dangling open parenthesis and anything after it.
    if s.count("(") > s.count(")"):
        s = s[:s.rfind("(")]
    s = s.strip(" :;,-")
    return (s[0].upper() + s[1:]) if s else ""


def pretty(d, dp="day"):
    y, m, day = int(d[:4]), int(d[5:7]), int(d[8:10])
    if dp == "day":
        return f"{MONTHS[m - 1]} {day}, {y}"
    if dp == "month":
        return f"{MONTHS[m - 1]} {y}"
    return f"Q{(m - 1) // 3 + 1} {y}"


ARCHIVE = re.compile(
    r'<a class="row" href="/fda-decision/([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})"[^>]*>(.*?)</a>', re.S)


def decision_facts():
    """(ticker, date) -> (outcome, drug-and-indication), read from /decisions.

    Not from the page's own h1, which is only "MRK FDA decision : Jul 10, 2026" and never carried
    the drug or the outcome. The first version read the h1, found nothing, and published decision
    descriptions with the single most useful word -- Approved -- missing.
    """
    out = {}
    f = os.path.join(SITE, "decisions", "index.html")
    if not os.path.exists(f):
        return out
    doc = open(f, encoding="utf-8", errors="replace").read()
    for tk, day, frag in ARCHIVE.findall(doc):
        txt = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", frag))).strip()
        outcome = ("Approved" if re.search(r"\bapproved\b", txt, re.I)
                   else "Complete Response Letter"
                   if re.search(r"\bcrl\b|complete response", txt, re.I) else "")
        body = re.split(r"(?:Approved|CRL|Complete Response Letter)\s*:?\s*", txt, maxsplit=1)
        drug = body[1].strip(" :") if len(body) > 1 else ""
        out[(tk, day)] = (outcome, drug)
    return out


def load_rows():
    src = open(DATASET, encoding="utf-8", errors="replace").read()
    return json.loads(re.search(r"export default (\[.*\])", src, re.S).group(1))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    state = json.load(open(STATE, encoding="utf-8"))
    rows = load_rows()
    by_tk, name_of = {}, {}
    for r in rows:
        tk = str(r.get("t") or "").upper()
        if not tk:
            continue
        by_tk.setdefault(tk, []).append(r)
        if r.get("company") and tk not in name_of:
            name_of[tk] = r["company"]

    import datetime as dt
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()

    def fit(parts, limit=DESC_MAX):
        """Assemble from clauses in priority order, dropping any that will not fit whole.

        The first version built one long sentence and trimmed it, which produced descriptions
        ending "...and the run-up we" -- a sentence cut mid-phrase, in the one string a searcher
        reads before deciding whether to click. Dropping a whole clause always leaves grammatical
        text; cutting a string never does.
        """
        out = ""
        for s in parts:
            if not s:
                continue
            if len(out) + len(s) <= limit:
                out += s
        return out.strip()

    def ticker_desc(tk):
        co = short_company(name_of.get(tk, ""), tk)
        up = sorted([r for r in by_tk.get(tk, [])
                     if (r.get("d") or "") >= today
                     and str(r.get("st") or "").lower() != "decided"],
                    key=lambda r: r["d"])
        dec = sum(1 for r in by_tk.get(tk, []) if str(r.get("st") or "").lower() == "decided")

        nxt = ""
        if up:
            n = up[0]
            drug = trim(str(n.get("name") or "").strip(), 46) or "an undisclosed program"
            nxt = (f" Next: {n.get('type', 'catalyst')} "
                   f"{pretty(n['d'], n.get('dp') or 'day')} for {drug}.")
        else:
            nxt = " No dated catalyst on our calendar right now."

        hist = f" {dec} FDA decision{'s' if dec != 1 else ''} on record." if dec else ""
        return fit([f"{co} ({tk}) FDA catalysts.", nxt, hist,
                    " Source document and measured run-up on every one."])

    facts = decision_facts()

    def decision_desc(tk, date, doc):
        co = short_company(name_of.get(tk, ""), tk)
        outcome, drug = facts.get((tk, date), ("", ""))
        head = f"{co} ({tk}) FDA decision {pretty(date)}"
        head += f": {outcome}." if outcome else "."
        clause = clean_clause(drug, 62)
        return fit([head,
                    f" {clause}." if clause else "",
                    " With the 120-trading-day run-up into the date and the source document."])

    def decision_title(tk, date):
        """Rebuilt so the outcome survives.

        Trimming the old 140-character title cut ": Approved" off the end of five of them, which
        removed the one word a searcher most needs. Composing from the facts puts the outcome
        early, where no length limit can reach it.
        """
        outcome, drug = facts.get((tk, date), ("", ""))
        if not outcome:
            return None
        head = f"{tk} FDA Decision {pretty(date)}: {outcome}"
        suffix = " | pdufa.bio"
        room = TITLE_HARD - len(head) - len(suffix) - 3
        name = re.split(r":", drug)[0].strip() if drug else ""
        clause = clean_clause(name, room) if (name and room > 12) else ""
        if clause:
            head += f" - {clause}"
        return head + suffix

    d_fixed = t_fixed = 0
    for p in sorted(glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True)):
        rel = "pdufa_site_src/" + os.path.relpath(p, SITE).replace("\\", "/")
        if rel not in state:
            continue
        doc = open(p, encoding="utf-8", errors="replace").read()
        original = doc

        dm = D_RE.search(doc)
        if dm:
            url = "/" + os.path.relpath(os.path.dirname(p), SITE).replace("\\", "/")
            cur = html.unescape(dm.group(2))
            mt = re.match(r"^/ticker/([A-Z]{1,6})$", url)
            md = re.match(r"^/fda-decision/([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})$", url)
            # Generated pages are REGENERATED every run, not patched when they exceed a limit.
            # Length-gating meant a description this script had already shortened could never be
            # corrected again: the first pass produced several that fit but read badly, and the
            # gate then locked them in.
            if mt:
                new = ticker_desc(mt.group(1))
            elif md:
                new = decision_desc(md.group(1), md.group(2), doc)
            else:
                # Repair when it is too long OR when it is already broken: an unbalanced
                # parenthesis is a defect at any length, and length-gating alone left six of them
                # on the site untouched.
                new = (trim(cur) if len(cur) > 160
                       else balance(cur) if cur.count("(") != cur.count(")") else None)
            if new and new != cur:
                esc = html.escape(new, quote=True)
                doc = D_RE.sub(lambda m: m.group(1) + esc + m.group(3), doc, count=1)
                doc = OG_RE.sub(lambda m: m.group(1) + esc + m.group(3), doc, count=1)
                d_fixed += 1

        tm = T_RE.search(doc)
        if tm:
            cur_t = html.unescape(re.sub(r"\s+", " ", tm.group(2))).strip()
            md2 = re.match(r"^/fda-decision/([A-Z]{1,6})-(\d{4}-\d{2}-\d{2})$",
                           "/" + os.path.relpath(os.path.dirname(p), SITE).replace("\\", "/"))
            nt = decision_title(md2.group(1), md2.group(2)) if md2 else None

            # A ticker title carrying legal boilerplate is broken regardless of length. TAK's read
            # "Takeda Pharmaceutical Company Limited American Depositary Shar | pdufa.bio" -- cut
            # mid-word at 74 characters, under the threshold, so nothing touched it. A visibly
            # truncated word on a public page is a defect, not a length preference, so these are
            # rebuilt from the short company name even though they are short enough to pass.
            mt2 = re.match(r"^/ticker/([A-Z]{1,6})$",
                           "/" + os.path.relpath(os.path.dirname(p), SITE).replace("\\", "/"))
            if not nt and mt2 and re.search(r"American Depositary|\(each representing|Shar \|", cur_t):
                tk2 = mt2.group(1)
                co2 = short_company(name_of.get(tk2, ""), tk2)
                nt = f"{co2} ({tk2}) FDA Catalysts | pdufa.bio"

            if not nt and len(cur_t) > TITLE_HARD:
                suffix = " | pdufa.bio"
                body = cur_t[:-len(suffix)] if cur_t.endswith(suffix) else cur_t
                # trim() ends a description with a full stop, which is right for prose and
                # wrong inside a title: "...REGAL 80th Event. | pdufa.bio" reads like a typo.
                nt = trim(body, TITLE_HARD - len(suffix) - 2).rstrip(".") + suffix
            if nt and nt != cur_t:
                esc = html.escape(nt, quote=False)
                doc = T_RE.sub(lambda m: m.group(1) + esc + m.group(3), doc, count=1)
                t_fixed += 1

        if doc != original and not a.dry_run:
            open(p, "w", encoding="utf-8").write(doc)

    print(f"descriptions rewritten/trimmed: {d_fixed}")
    print(f"titles shortened (only those over {TITLE_HARD} chars): {t_fixed}")
    if a.dry_run:
        print("DRY RUN -- nothing written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
