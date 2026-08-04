# -*- coding: utf-8 -*-
"""ensure_calendar_rows.py -- every dated PDUFA we hold must appear on the calendar.

Replimune's RP1 had a confirmed 2 August 2026 action date, a published advisory committee page, an
entry in our own slate with the right drug and indication, and it appeared nowhere on the calendar.
A reader looking for it saw a calendar that simply did not know the catalyst existed. Nothing
reported this, because the calendar pages are maintained separately from the slate and nothing
compared the two.

Eight other dated PDUFAs were missing the same way, five of them in 2027, because the calendar is
organised by month pages that only exist for 2026. That is the same failure the conference calendar
had: a page scoped to one year quietly stops being a calendar when the year turns.

This reconciles the two. For every day-precision PDUFA in the slate, if there is no row for that
ticker and date on the matching month page, one is inserted in date order. Where the month page does
not exist at all, it says so loudly rather than dropping the catalyst on the floor, because creating
a page is a bigger decision than adding a row.

Rows are inserted in the same markup mark_calendar_decided.py expects, so a catalyst added here is
automatically marked with its outcome once one is published.

    python ensure_calendar_rows.py [--dry-run]
"""
import argparse, datetime as dt, glob, html, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
MONTHS = ["january", "february", "march", "april", "may", "june",
          "july", "august", "september", "october", "november", "december"]


def esc(s):
    return html.escape(str(s or ""), quote=True)


def load_pdufas():
    src = open(DATASET, encoding="utf-8", errors="replace").read()
    m = re.search(r"export default (\[.*\])", src, re.S)
    rows = json.loads(m.group(1)) if m else []
    out = []
    for r in rows:
        if r.get("type") != "PDUFA" or r.get("dp") != "day":
            continue
        d = str(r.get("d") or "")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", d):
            continue
        out.append(r)
    return sorted(out, key=lambda r: r["d"])


def internal_url(r):
    """Where a calendar row should point.

    Never at a third party. Replimune's slate row carried a link straight to an SEC exhibit, so even
    if the row had existed it would have sent the reader off the site. Prefer a /pdufa page, then
    the ticker hub, and keep the primary source in the data rather than in the click.
    """
    u = str(r.get("url") or "")
    t = (r.get("t") or "").upper()
    if u.startswith("/"):
        return u
    if t and os.path.isdir(os.path.join(SITE, "pdufa", t)):
        return f"/pdufa/{t}"
    if t and os.path.isdir(os.path.join(SITE, "ticker", t)):
        return f"/ticker/{t}"
    return "/calendar"


def row_html(r):
    t = (r.get("t") or "").upper()
    drug = (r.get("name") or "").strip()
    ta = (r.get("ta") or "").strip()
    desc = f"{drug}: {ta}" if ta and ta.lower() not in drug.lower() else drug
    return (f'<a class="row" href="{esc(internal_url(r))}">'
            f'<div class="t">{esc(t)} &middot; {esc(r["d"])}</div>'
            f'<div class="d">{esc(desc[:150])}</div></a>')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    pdufas = load_pdufas()
    added = missing_page = repointed = 0
    no_page = {}

    # Existing rows that link straight to a filing. Replimune's slate row carried an SEC exhibit
    # URL, and four other rows on the calendar already did the same. A calendar row is a promise to
    # show OUR page for that catalyst; sending the reader to sec.gov loses them and the click.
    by_key = {((r.get("t") or "").upper(), r["d"]): r for r in pdufas}
    for page in sorted(glob.glob(os.path.join(SITE, "calendar", "**", "index.html"),
                                 recursive=True)):
        doc = open(page, encoding="utf-8", errors="replace").read()
        orig = doc
        # Match the anchor loosely and read the ticker/date from the markup that follows, because
        # a row may carry other attributes (data-dec on a marked row) between class and href.
        for m in list(re.finditer(r'<a class="row"[^>]*href="(https?://[^"]+)"', doc)):
            url = m.group(1)
            if "pdufa.bio" in url:
                continue
            look = doc[m.end():m.end() + 160]
            mm = re.search(r'<div class="t">([A-Z]{1,6})\s*(?:&middot;|·)\s*(\d{4}-\d{2}-\d{2})',
                           look)
            tk, d = (mm.group(1), mm.group(2)) if mm else ("", "")
            dest = internal_url(by_key.get((tk, d), {"t": tk}))
            doc = doc.replace(f'href="{url}"', f'href="{dest}"')
            repointed += 1
            print(f"  repointed {tk or '?'} {d or '?'}: off-site -> {dest}")
        if doc != orig and not a.dry_run:
            open(page, "w", encoding="utf-8").write(doc)

    for r in pdufas:
        y, mo = r["d"][:4], int(r["d"][5:7])
        page = os.path.join(SITE, "calendar", y, MONTHS[mo - 1], "index.html")
        t = (r.get("t") or "").upper()
        if not os.path.exists(page):
            no_page.setdefault(f"{y}-{r['d'][5:7]}", []).append(t)
            missing_page += 1
            continue
        doc = open(page, encoding="utf-8", errors="replace").read()
        # Already present? Match ticker AND date, so a second PDUFA for the same issuer still lands.
        if re.search(r'<div class="t">' + re.escape(t) + r'\s*(?:&middot;|·)\s*'
                     + re.escape(r["d"]), doc):
            continue

        new = row_html(r)
        # Insert in date order: before the first existing row with a later date.
        anchor = None
        for m in re.finditer(r'<a class="row"[^>]*>\s*<div class="t">[A-Z./ ]+\s*(?:&middot;|·)\s*'
                             r'(\d{4}-\d{2}-\d{2})', doc):
            if m.group(1) > r["d"]:
                anchor = m.start(); break
        if anchor is None:
            last = None
            for m in re.finditer(r'<a class="row".*?</a>', doc, re.S):
                last = m
            if not last:
                print(f"  {t} {r['d']}: no rows on {os.path.relpath(page, SITE)} to anchor to")
                continue
            doc = doc[:last.end()] + new + doc[last.end():]
        else:
            doc = doc[:anchor] + new + doc[anchor:]

        if not a.dry_run:
            open(page, "w", encoding="utf-8").write(doc)
        added += 1
        print(f"  added {t} {r['d']} -> {os.path.relpath(page, SITE)}  ({internal_url(r)})")

    print(f"\n{added} calendar row(s) added, {repointed} repointed on-site"
          + (" [dry run]" if a.dry_run else "")
          + f"; {len(pdufas)} dated PDUFAs checked")
    if no_page:
        print(f"\n{missing_page} PDUFA(s) have no month page to live on:")
        for k in sorted(no_page):
            print(f"   {k}: {', '.join(sorted(set(no_page[k])))}")
        print("   The calendar only has month pages for 2026. Catalysts beyond that are invisible "
              "on the calendar no matter how well sourced they are.")


if __name__ == "__main__":
    main()
