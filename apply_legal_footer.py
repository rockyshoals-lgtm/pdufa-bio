# -*- coding: utf-8 -*-
"""apply_legal_footer.py -- one canonical legal footer on every page.

The site had 35 hand-drifted variants of the same disclaimer. None of them named the operating
entity, which is the point of having one: a reader (or a regulator, or opposing counsel) should be
able to tell from any page who publishes it. This makes every footer state, in the same words:

  * who publishes the site (Odin Catalyst LLC)
  * that it has no affiliation with or endorsement from the FDA or any government agency
  * that third-party marks are used descriptively and stay with their owners
  * that nothing here is investment / legal / tax / medical advice, and Odin Catalyst LLC is not a
    registered investment adviser or broker-dealer
  * that data carries no warranty and should be verified against primary filings

Page-specific language is PRESERVED, not flattened. The script strips the sentences it recognises as
boilerplate and re-attaches whatever is left over (for example the conference pages' "Not affiliated
with ESMO or its organizer", or a page's "Last computed 2026-08-02"). Run with --preview first: it
prints every distinct leftover so you can confirm nothing meaningful was swallowed.

    python apply_legal_footer.py --preview
    python apply_legal_footer.py
"""
import argparse, os, re, sys, collections

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")

ENTITY = "Odin Catalyst LLC"
SKIP = {"index_redesign.html", "preview.html", "ping.html", "holding.html", "app.html"}

# Sentences that are pure boilerplate. Anything NOT matched here is page-specific and is kept.
BOILER = [
    r"Not affiliated with[^.<]*\.",
    r"pdufabio is an independent service[.;]?",
    r"pdufabio is owned and operated by Odin Catalyst LLC[^.<]*\.",
    r"pdufabio is published by[^.<]*\.",
    r"Owned and operated by Odin Catalyst LLC\.?",
    r"Informational and educational only[^.<]*(?:advice)?\.?",
    r"[Nn]ot investment(?:,| ) ?(?:legal[^.<]*)?advice[^.<]*\.?",
    r"Nothing here is investment[^.<]*\.",
    r"Odin Catalyst LLC is not a registered[^.<]*\.",
    r"[\"“]FDA[\"”],?\s*[\"“]PDUFA[\"”][^.<]*\.",
    # The canonical sentences this script itself writes. Without these the script is not
    # idempotent: a second run fails to recognise its own output, treats it as page-specific
    # language, and appends a duplicate copy of the whole disclaimer.
    r"&?ldquo;FDA&rdquo;,?\s*&ldquo;PDUFA&rdquo;[^.<]*\.",
    r"Informational and educational purposes only\.?",
    r"Nothing on this page is investment[^.<]*\.",
    r"does not recommend trades or publish individual-drug approval probabilities\.?",
    r"an independent company that is not affiliated[^.<]*\.",
    r"Verify (?:every date and outcome |against |every figure )?[^.<]*\.",
    r"Data and historical statistics only[^.<]*\.",
    r"Data is provided as is[^.<]*\.",
    r"No individual-drug approval probabilities[^.<]*\.",
    r"no trade recommendations[^.<]*\.",
    r"(?:&copy;|©) ?2026 (?:pdufabio|Odin Catalyst LLC)\.?",
    r"All rights reserved\.?",
    r"pdufabio provides data and historical statistics[^.<]*\.",
    r"Dates from organizer announcements[^.<]*\.",
]
AFFIL_RE = re.compile(r"Not affiliated with[^.<]*\.")

# Sentence splitting on "." breaks inside "pdufa.bio" and "U.S. Food and Drug Administration",
# which left fragments like a bare "bio" in the preserved text. Mask those dots first.
DOTS = [("pdufa.bio", "pdufabio"), ("U.S.", "US")]


def mask(t):
    for a, b in DOTS:
        t = t.replace(a, b)
    return t


def unmask(t):
    for a, b in DOTS:
        t = t.replace(b, a)
    return t


def canonical(affil, extra):
    """affil: the page's own 'Not affiliated with X.' sentence. extra: preserved page-specific text."""
    ex = (" " + extra.strip()) if extra.strip() else ""
    return (
        f"<b>{affil}</b> pdufa.bio is published by <b>{ENTITY}</b>, an independent company that is "
        f"not affiliated with, endorsed by, sponsored by, or connected to the U.S. Food and Drug "
        f"Administration or any other government agency. &ldquo;FDA&rdquo;, &ldquo;PDUFA&rdquo; and "
        f"all company, drug and ticker names are used descriptively and remain the property of their "
        f"respective owners.<br><br>"
        f"<b>Informational and educational purposes only. Not investment advice.</b> Nothing on this "
        f"page is investment, legal, tax or medical advice, or an offer or solicitation to buy or "
        f"sell any security. {ENTITY} is not a registered investment adviser or broker-dealer and "
        f"does not recommend trades or publish individual-drug approval probabilities.{ex} "
        f"Verify every date and outcome against primary FDA, SEC or company filings. Data is provided "
        f"as is, without warranty of any kind, and past behaviour does not predict future outcomes."
        f"<br><br>&copy; 2026 {ENTITY}. All rights reserved."
    )


def split_body(inner):
    """-> (prefix_html, boilerplate_body). prefix is the nav-link row, kept as-is."""
    m = re.search(r"<b>\s*(?:Not affiliated|Informational)", inner)
    if not m:
        m2 = re.search(r"(?:Not affiliated|Informational and educational)", inner)
        if not m2:
            return None, None
        return inner[:m2.start()], inner[m2.start():]
    return inner[:m.start()], inner[m.start():]


LINK_RE = re.compile(r'<a\s[^>]*href="(/[^"]*)"[^>]*>([^<]{1,40})</a>')


def trailing_links(body):
    """Footer nav links living inside the boilerplate (the homepage keeps Sources / Methodology
    links after the copyright). Stripping to text would silently delete them, so re-attach them."""
    out = []
    for href, label in LINK_RE.findall(body):
        lab = label.strip()
        if lab and href not in [h for h, _ in out]:
            out.append((href, lab))
    return out


def leftover(body):
    """Strip recognised boilerplate; return the page-specific remainder as clean text."""
    t = mask(body)
    t = LINK_RE.sub(" ", t)       # anchors are re-attached separately by trailing_links()
    t = re.sub(r"</?b>|</?strong>", " ", t)
    for pat in BOILER:
        t = re.sub(pat, " ", t)
    t = re.sub(r"<br\s*/?>", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = t.replace("&copy;", " ").replace("&mdash;", " ").replace("&ndash;", " ")
    t = re.sub(r"&middot;?|&[lr]dquo;|&nbsp;", " ", t)   # link separators are not page copy
    t = re.sub(r"[\s ]+", " ", t).strip(" .;,&-—")
    t = unmask(t)
    if len(t) <= 20:
        return ""
    if t[-1] not in ".!?":
        t += "."
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    a = ap.parse_args()

    legal_re = re.compile(r'(<div class="legal"[^>]*>)(.*?)(</div>)', re.S)
    footer_re = re.compile(r"(<footer[^>]*>)(.*?)(</footer>)", re.S)

    extras = collections.Counter()
    affils = collections.Counter()
    changed = 0
    scanned = 0
    inserted = [0]

    for root, _, fs in os.walk(SITE):
        for f in fs:
            if not f.endswith(".html"):
                continue
            if f.startswith("_") or f in SKIP:
                continue          # scratch / backup pages, not live routes
            p = os.path.join(root, f)
            html = open(p, encoding="utf-8", errors="replace").read()
            orig = html
            scanned += 1

            def repl(m):
                open_t, inner, close_t = m.group(1), m.group(2), m.group(3)
                prefix, body = split_body(inner)
                if body is None:
                    return m.group(0)
                am = AFFIL_RE.search(mask(body))
                affil = unmask(am.group(0).strip()) if am else "Not affiliated with or endorsed by the FDA."
                ex = leftover(body)
                links = trailing_links(body)
                affils[affil] += 1
                if ex:
                    extras[ex] += 1
                tail = ""
                if links and not prefix.strip():
                    tail = "<br>" + " &middot; ".join(
                        f'<a href="{h}" style="color:#8aa0bf">{l}</a>' for h, l in links)
                return open_t + prefix + canonical(affil, ex) + tail + close_t

            html = legal_re.sub(repl, html)
            html = footer_re.sub(repl, html)

            # Some pages were built without any footer block at all, so there was nothing to
            # rewrite and they silently shipped with no disclaimer. Give them one.
            if ENTITY not in html and "</body>" in html:
                affil = "Not affiliated with or endorsed by the FDA."
                affils[affil] += 1
                block = ('<div class="legal" style="border-top:1px solid #1e3a63;margin-top:32px;'
                         'padding-top:14px;font-size:11.5px;color:#8aa0bf;line-height:1.6">'
                         '<a href="/about" style="color:#8aa0bf">About</a> &middot; '
                         '<a href="/corrections" style="color:#8aa0bf">Corrections</a> &middot; '
                         '<a href="/methodology" style="color:#8aa0bf">Methodology</a><br><br>'
                         + canonical(affil, "") + "</div>")
                html = html.replace("</body>", block + "</body>", 1)
                inserted[0] += 1
            if html != orig:
                changed += 1
                if not a.preview:
                    open(p, "w", encoding="utf-8").write(html)

    print(f"scanned {scanned:,} html files; {'would rewrite' if a.preview else 'rewrote'} {changed:,} footers "
          f"({inserted[0]} inserted on pages that had none)\n")
    print("AFFILIATION SENTENCES PRESERVED:")
    for k, v in affils.most_common():
        print(f"  {v:5d}  {k}")
    print(f"\nPAGE-SPECIFIC TEXT PRESERVED ({len(extras)} distinct):")
    for k, v in extras.most_common():
        print(f"  {v:5d}  {k[:220]}")


if __name__ == "__main__":
    main()
