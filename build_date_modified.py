# -*- coding: utf-8 -*-
"""build_date_modified.py -- give search engines the date they print next to our result.

The competitor now at #1 on Bing shows "1 hour ago" under its listing. Ours shows no date at all,
and the reason is not that our data is older: we rebuild daily and publish decisions the same week
they happen. The reason is that we never told the engines.

A visible date on the page (shipped already) is a weak hint. The signal engines actually read for
the timestamp in a result is structured: schema.org dateModified, plus the Open Graph and article
modified-time meta. We had dateModified on 3 pages out of 911 that carry JSON-LD, and no og or
article meta anywhere.

WHERE THE DATE COMES FROM, AND WHY IT IS NOT THE BUILD TIME

The date is each page's own content-change date, read from _sitemap_lastmod.json. That is the same
source the visible stamp and the sitemap's <lastmod> use, so all three agree by construction rather
than by luck. Three surfaces telling an engine three different dates is worse than telling it none.

It is deliberately NOT the build time. This codebase has twice shipped a freshness signal that
advanced every night regardless of whether anything changed, and both times it had to be undone:
a site claiming all 850 pages changed today, every day, teaches Google to ignore the field, which
costs us the ability to say anything at all about recency.

DATE ONLY, NO CLOCK TIME

We know the day a page's content changed. We do not know the hour, so we do not publish one. It
would be easy to emit the build timestamp and get a nicer-looking "2 hours ago" in the result, and
it would be a fabrication of precision we do not have, on a site whose entire pitch is that every
figure is traceable. A date renders as "Aug 7, 2026", which is the true answer.

THE FEEDBACK LOOP THIS AVOIDS

Writing the date into the page changes the page. If that change counted as a content change, the
next build would see a new hash, advance the date, write it again, and the date would climb every
night forever while nothing real changed. So build_sitemap.py strips dateModified and this block
from the content hash, exactly as it strips the nav and the freshness stamp. Verified by running
the sequence twice and diffing every page.

Runs AFTER build_sitemap.py, which is what computes the dates it reads.

    python build_date_modified.py [--dry-run]
"""
import argparse, glob, json, os, re, subprocess, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
STATE = os.path.join(HERE, "_sitemap_lastmod.json")
B, E = "<!--DMOD:BEGIN-->", "<!--DMOD:END-->"

NOINDEX = re.compile(r'name="robots"[^>]*content="[^"]*noindex', re.I)
LD = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)

# Nodes that legitimately carry a page-level modification date. Event and ItemList describe the
# things ON the page, not the page, so stamping those would be saying something we do not mean.
PAGE_TYPES = {"WebPage", "CollectionPage", "ItemPage", "Article", "NewsArticle", "Dataset",
              "FAQPage", "AboutPage"}


_FIRST = None


def first_published():
    """path -> ISO date of the commit that FIRST added it.

    A real publication date, not a guess. The audit asked for datePublished and the temptation is
    to reach for something plausible; the honest answer is already in git, which knows exactly when
    each page first appeared. One `git log --diff-filter=A` walk gets all of them.

    Pages never committed (a brand-new page in this very build) get nothing rather than today's
    date, because "published today" would be a claim we make about a file that has not shipped yet.
    """
    global _FIRST
    if _FIRST is not None:
        return _FIRST
    out = {}
    try:
        r = subprocess.run(["git", "log", "--diff-filter=A", "--format=@%h %cs", "--name-only",
                            "--", "pdufa_site_src"],
                           cwd=HERE, capture_output=True, text=True, timeout=180)
        rows, cur = [], None
        for line in r.stdout.splitlines():
            if line.startswith("@"):
                sha, _, day = line[1:].strip().partition(" ")
                cur = (sha, day)
            elif line.endswith(".html") and cur:
                rows.append((line, cur))

        # The repo's initial import added 461 pages in one commit ("pdufa.bio site + pipeline",
        # 2026-07-25). For those, git records when the REPOSITORY was created, not when the page
        # was published, and the site may well have been live before the import. Publishing that
        # date as datePublished would be asserting a fact about 461 pages that we cannot defend
        # from any source, which is the one thing this site does not do. Pages created after the
        # import have a real, checkable creation date, and only those get one.
        # Exclude by the repo's start DATE, not just its first commit. The import was spread over
        # several commits on 2026-07-25, so keying on one sha still left 188 pages claiming that
        # day. Any page whose git creation falls on the day the repository itself began has an
        # unknowable real publication date, and gets none.
        import_day = rows[-1][1][1] if rows else None
        for path, (sha, day) in rows:
            if day == import_day:
                out.pop(path, None)
                continue
            out[path] = day              # newest first, so the last write wins = the oldest add
    except Exception as e:
        print(f"  note: git history unavailable ({type(e).__name__}); no datePublished emitted.")
    _FIRST = out
    return out


def norm(u):
    return re.sub(r"/+$", "", str(u or "").strip().lower())


def stamp_nodes(obj, date, canon, changed, pub=None, depth=0, seen=None):
    """Stamp only nodes that mean THIS page.

    The first version stamped every page-type node it found, which on /calendar meant 14 nested
    ListItem entries describing OTHER urls (/pdufa/NVO-am833 and friends). That published a false
    claim: it told search engines those 14 pages were modified on the calendar's change date. A
    listing page knows when IT changed; it does not know when the pages it links to changed.

    So a node is stamped only if it identifies itself as this page, by url or @id matching the
    canonical. A node with no url at the top of its block is this page by convention and is
    stamped. Anything pointing elsewhere is left alone, and any wrong date we previously wrote
    there is removed.
    """
    if isinstance(obj, list):
        for o in obj:
            stamp_nodes(o, date, canon, changed, pub, depth + 1, seen)
        return
    if not isinstance(obj, dict):
        return

    t = obj.get("@type")
    types = {t} if isinstance(t, str) else set(t) if isinstance(t, list) else set()
    if types & PAGE_TYPES:
        u = obj.get("url") or obj.get("@id")
        if u is None:
            is_self = depth <= 1              # top of the block, or a @graph member
        else:
            is_self = norm(u) == norm(canon)

        if is_self:
            # Record that this page HAS a node of its own, separately from whether we had to
            # change it. Conflating the two meant a page whose node was already correct looked
            # like a page with no node, and got a second, duplicate one bolted on.
            if seen is not None:
                seen.append(True)
            if obj.get("dateModified") != date:
                obj["dateModified"] = date
                changed.append(True)
            if pub:
                if obj.get("datePublished") != pub:
                    obj["datePublished"] = pub
                    changed.append(True)
            elif "datePublished" in obj:
                # We can no longer defend this value, so it comes off. An earlier run wrote the
                # repo-import date onto 188 pages before that rule existed, and a writer with no
                # removal path leaves bad data on the page forever: the same omission that left 14
                # wrong dateModified stamps in place a few commits ago.
                del obj["datePublished"]
                changed.append(True)
        elif "dateModified" in obj:
            # A modification date on a node describing a DIFFERENT url. A listing page cannot know
            # when the pages it links to changed, so this is always a claim we are not entitled to
            # make, whoever wrote it. Removed unconditionally rather than only when it matches
            # today: an earlier run of this script stamped these under a different date (CI runs
            # UTC, a local run does not), and a date-matched cleanup silently left them behind.
            del obj["dateModified"]
            changed.append(True)

    for v in obj.values():
        if isinstance(v, (dict, list)):
            stamp_nodes(v, date, canon, changed, pub, depth + 1, seen)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    try:
        raw = json.load(open(STATE, encoding="utf-8"))
        # Prefer the exact moment the content changed, recorded by build_sitemap.py at the instant
        # the hash moved. Pages that have not changed since that was introduced have only a date,
        # and a date is what they get: back-filling a clock time we never observed would be
        # inventing precision, which is the one thing this site cannot do.
        state = {k: (v.get("ts") or v.get("date")) for k, v in raw.items()}
        day_of = {k: v.get("date") for k, v in raw.items()}
    except Exception:
        print("  no _sitemap_lastmod.json; run build_sitemap.py first."); return 0

    ld_done = meta_done = no_page_node = added_node = skipped = 0

    for p in sorted(glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True)):
        rel = "pdufa_site_src/" + os.path.relpath(p, SITE).replace("\\", "/")
        date = state.get(rel)
        pub = first_published().get(rel)
        # A page cannot have been published after it was last modified.
        if pub and day_of.get(rel) and pub > day_of[rel]:
            pub = None
        if not date:
            continue                      # not in the sitemap: noindex, or not a real page
        doc = open(p, encoding="utf-8", errors="replace").read()
        if NOINDEX.search(doc[:4000]):
            skipped += 1
            continue
        original = doc
        marker_payload = []

        # Work from the page WITHOUT our own block. The generated WebPage node lives inside DMOD,
        # so leaving it in place made the script eat its own output: the stamper would update that
        # node, count it as a hit, skip regenerating it, and then overwrite the whole block with an
        # empty payload -- deleting the only node carrying the date. /calendar and /decisions both
        # lost their dateModified exactly once this way. Stripping first means the decision below
        # is made about the page's real schema, not about what we wrote last night.
        doc = re.sub(re.escape(B) + ".*?" + re.escape(E), "", doc, flags=re.S)

        # 1. schema.org dateModified on the node that means this page
        canon_m = re.search(r'<link[^>]+rel="canonical"[^>]+href="([^"]+)"', doc)
        canon = canon_m.group(1) if canon_m else ""
        hit = []

        def repl(m):
            try:
                data = json.loads(m.group(2))
            except Exception:
                return m.group(0)         # leave anything unparseable exactly as it is
            changed = []
            stamp_nodes(data, date, canon, changed, pub, 0, hit)
            if not changed:
                return m.group(0)
            return m.group(1) + json.dumps(data, separators=(",", ":")) + m.group(3)

        doc = LD.sub(repl, doc)
        if hit:
            ld_done += 1
        else:
            # 134 of these carry no JSON-LD at all and another 46 describe only the events or the
            # breadcrumb, so there is no node that means "this page". Meta tags alone are the
            # weaker signal, so give them a real WebPage node. Everything in it is read off the
            # page itself: no invented titles, no guessed URLs.
            can = canon_m
            ttl = re.search(r"<title[^>]*>(.*?)</title>", doc, re.S)
            if can:
                node = {"@context": "https://schema.org", "@type": "WebPage",
                        "url": can.group(1), "dateModified": date,
                        **({"datePublished": pub} if pub else {}),
                        "isPartOf": {"@type": "WebSite", "name": "pdufa.bio",
                                     "url": "https://www.pdufa.bio/"}}
                if ttl:
                    import html as _h
                    node["name"] = _h.unescape(re.sub(r"\s+", " ", ttl.group(1))).strip()
                blk = ('<script type="application/ld+json">'
                       + json.dumps(node, separators=(",", ":")) + "</script>")
                # Inside the marked block so it is stripped from the content hash with the rest.
                marker_payload.append(blk)
                added_node += 1
            else:
                no_page_node += 1

        # 2. og:updated_time / article:modified_time, which some engines read in preference
        block = (B + f'<meta property="og:updated_time" content="{date}">'
                 + f'<meta property="article:modified_time" content="{date}">'
                 + "".join(marker_payload) + E)
        if "</head>" in doc:
            i = doc.index("</head>")
            doc = doc[:i] + block + doc[i:]
        if B in doc:
            meta_done += 1

        if doc != original and not a.dry_run:
            open(p, "w", encoding="utf-8").write(doc)

    print(f"dateModified in JSON-LD: {ld_done} page(s)")
    print(f"og:updated_time + article:modified_time: {meta_done} page(s)")
    if added_node:
        print(f"  {added_node} page(s) had no node meaning 'this page'; given a WebPage node built "
              f"from their own canonical URL and title")
    if no_page_node:
        print(f"  {no_page_node} page(s) have no canonical link, so no node was invented for them")
    print(f"  {skipped} noindex page(s) skipped -- a date on a page we asked not to index is noise")
    if a.dry_run:
        print("DRY RUN -- nothing written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
