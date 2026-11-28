# -*- coding: utf-8 -*-
"""test_crl_company_announced.py -- company-announced CRLs and the /crl/{year}/{month}/{day} pages (2026-11-28).

crl_company_announced.json holds Complete Response Letters companies announced themselves, January 2024 on, each with
the company's own dated release, stock-exchange disclosure or SEC filing (re-read against it before it was added).
What this holds:

  * every record is well formed: ISO dates from 2024 on, a letter date (where given) on or before the announcement
    and within 30 days of it, an https source, a known application type, no record twice;
  * every record is on its own day page with its source link, and on the day page of its letter date if that differs;
  * a record that is one of the tracked decisions is not listed again in the month page's company table, and one that
    is not is listed there, with its source;
  * every Complete Response letter in the FDA's release dated 2024 on is on its day page (provisional determinations
    and other letter types are not CRLs and get none); every day page is backed by a record; every month page links
    each of its day pages; titles say the date and fit;
  * no decision page or source is listed twice on a day page (2026-11-28 red team: an announcement whose letter date
    was a tracked decision's date showed twice);
  * each announcement matches the tracked decision pinned below and no other (a wrong match hides a CRL from its
    month page); a month page's description counts the announcements its table lists.
"""
import collections, datetime as dt, glob, html, io, json, os, re, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
SITE = os.path.join(HERE, "pdufa_site_src")
APPS = {"NDA", "BLA", "sNDA", "sBLA", "biosimilar BLA", ""}
KINDS = {"press release", "SEC 8-K", "stock-exchange disclosure", "earnings release", "company statement",
         "company announcement"}


# announcement id -> the tracked decision it is (reviewed 2026-11-28); every other announcement matches none
PINNED = {
    "2025-01-16-atara-biotherapeutics-ebvallo": "/fda-decision/ATRA-2025-01-16",
    "2025-03-28-milestone-pharmaceutical-cardamyst": "/fda-decision/MIST-2025-03-28",
    "2025-04-03-aldeyra-therapeutics-reproxalap": "/fda-decision/ALDX-2025-04-03",
    "2025-04-18-regeneron-pharmaceutical-eylea-hd": "/fda-decision/REGN-2025-04-20",
    "2025-04-28-telix-pharmaceuticals-tlx101-cdx": "/fda-decision/TLX-2025-04-28",
    "2025-06-30-unicycive-therapeutics-oxylanthanum-carbonate": "/fda-decision/UNCY-2025-06-30",
    "2025-07-11-capricor-therapeutics-deramiocel": "/fda-decision/CAPR-2025-07-11",
    "2025-07-11-ultragenyx-pharmaceutica-ux111": "/fda-decision/RARE-2025-07-11",
    "2025-07-18-roche-columvi": "/fda-decision/RHHBY-2025-07-18",
    "2025-07-22-replimune-group-rp1": "/fda-decision/REPL-2025-07-22",
    "2025-08-01-regeneron-pharmaceutical-odronextamab": "/fda-decision/REGN-2025-07-30",
    "2025-08-19-ptc-therapeutics-vatiquinone": "/fda-decision/PTCT-2025-08-19",
    "2025-08-28-outlook-therapeutics-ons-5010-lytenava": "/fda-decision/OTLK-2025-08-28",
    "2025-08-28-telix-pharmaceuticals-tlx250-cdx": "/fda-decision/TLX-2025-08-28",
    "2025-09-23-biogen-nusinersen": "/fda-decision/BIIB-2025-09-23",
    "2025-09-23-scholar-rock-apitegromab": "/fda-decision/SRRK-2025-09-23",
    "2025-10-01-fortress-biotech-cutx-101": "/fda-decision/FBIO-2025-10-01",
    "2025-11-02-alvotech-avt05": "/fda-decision/ALVO-2025-11-02",
    "2025-11-04-biohaven-vyglxia": "/fda-decision/BHVN-2025-11-04",
    "2025-12-24-sanofi-tolebrutinib": "/fda-decision/SNY-2025-12-24",
    "2025-12-31-corcept-therapeutics-relacorilant": "/fda-decision/CORT-2025-12-31",
    "2025-12-31-dr-reddy-s-laboratories-avt03": "/fda-decision/RDY-2025-12-31",
    "2025-12-31-outlook-therapeutics-ons-5010-lytenava": "/fda-decision/OTLK-2025-12-31",
    "2026-01-12-atara-biotherapeutics-ebvallo": "/fda-decision/ATRA-2026-01-12",
    "2026-02-01-pharming-group-joenja": "/fda-decision/PHAR-2026-02-01",
    "2026-02-02-aquestive-therapeutics-anaphylm": "/fda-decision/AQST-2026-02-02",
    "2026-02-03-astrazeneca-saphnelo": "/fda-decision/AZN-2026-02-03",
    "2026-02-09-regenxbio-rgx-121": "/fda-decision/RGNX-2026-02-09",
    "2026-02-13-disc-medicine-bitopertin": "/fda-decision/IRON-2026-02-13",
    "2026-03-06-incyte-zynyz": "/fda-decision/INCY-2026-03-06",
    "2026-03-17-aldeyra-therapeutics-reproxalap": "/fda-decision/ALDX-2026-03-17",
    "2026-04-10-replimune-group-rp1": "/fda-decision/REPL-2026-04-10",
    "2026-04-23-abbvie-trenibotulinumtoxine": "/fda-decision/ABBV-2026-04-23",
    "2026-04-23-grace-therapeutics-gtx-104": "/fda-decision/GRCE-2026-04-23",
    "2026-06-02-cingulate-ctx-1301": "/fda-decision/CING-2026-06-02",
    "2026-06-22-achieve-life-sciences-cytisinicline": "/fda-decision/ACHV-2026-06-22",
    "2026-06-26-lantheus-holdings-lnth-2501": "/fda-decision/LNTH-2026-06-26",
    "2026-06-30-unicycive-therapeutics-oxylanthanum-carbonate": "/fda-decision/UNCY-2026-06-30",
    "2026-11-15-summit-therapeutics-ivonescimab": "/fda-decision/SMMT-2026-11-15",
    "2026-11-20-capricor-therapeutics-deramiocel": "/fda-decision/CAPR-2026-11-20",
}


def read(path):
    p = os.path.join(SITE, path.strip("/"), "index.html")
    return io.open(p, encoding="utf-8").read() if os.path.exists(p) else None


def main():
    import build_crl_months as b
    bad = []
    recs = b.announced()
    seen, keys = set(), set()
    for r in recs:
        i = r.get("id")
        if i in seen:
            bad.append(f"{i}: duplicate id")
        seen.add(i)
        k = (r["company_short"].lower(), r["drug_short"].lower(), r["announce_date"])
        if k in keys:
            bad.append(f"{i}: same company, drug and date twice")
        keys.add(k)
        if not ("2024-01-01" <= r["announce_date"] <= b.eastern_today().isoformat()):
            bad.append(f"{i}: announce_date {r['announce_date']} outside 2024-01-01..today")
        if r["crl_date"]:
            gap = (b._D(r["announce_date"]) - b._D(r["crl_date"])).days
            if not 0 <= gap <= 30:
                bad.append(f"{i}: letter dated {r['crl_date']} is not within 30 days before the announcement")
        if not r["source_url"].startswith("https://") or not r["source_label"]:
            bad.append(f"{i}: no https source")
        if r["application"] not in APPS:
            bad.append(f"{i}: application {r['application']!r}")
        if r["source_kind"] not in KINDS:
            bad.append(f"{i}: source_kind {r['source_kind']!r}")
        if not r["company_short"] or not r["drug_short"] or int(r.get("letters") or 0) < 1:
            bad.append(f"{i}: missing company, drug or letter count")

    ours, _ = b.tracked()
    trk = [o for v in ours.values() for o in v]
    letters, _ = b.corpus()
    got = b.match_all(recs, trk)
    for i, h in got.items():
        if h != PINNED.get(i, ""):
            bad.append(f"{i}: matched to {h or 'no tracked decision'}, reviewed match is {PINNED.get(i) or 'none'}")
    for r in recs:
        src = html.escape(r["source_url"], quote=True)
        day = read(b.day_href(r["announce_date"]))
        if day is None or src not in day:
            bad.append(f"{r['id']}: not on {b.day_href(r['announce_date'])} with its source")
        if r["crl_date"] and r["crl_date"] != r["announce_date"]:
            d2 = read(b.day_href(r["crl_date"]))
            if d2 is None or src not in d2:
                bad.append(f"{r['id']}: not on the day page of its letter date {r['crl_date']}")
        d = b._D(r["announce_date"])
        month = read(f"/crl/{d.year}/{b.MON[d.month - 1]}") or ""
        listed = src in month
        href = got[r["id"]]
        if href and listed:
            bad.append(f"{r['id']}: listed in its month page's company table and as tracked decision {href}")
        if not href and not listed:
            bad.append(f"{r['id']}: not listed on its month page")
        if href and day and f'href="{href}"' not in day:
            bad.append(f"{r['id']}: day page does not link its tracked decision {href}")

    days = {r["announce_date"] for r in recs} | {r["crl_date"] for r in recs if r["crl_date"]} | {o[0] for o in trk}
    for l in letters:
        if l["iso"] >= "2024-01-01" and l.get("cr"):
            days.add(l["iso"])
            doc = read(b.day_href(l["iso"]))
            if doc is None or html.escape(l["url"], quote=True) not in doc:
                bad.append(f"FDA letter {l['fn']} ({l['iso']}) not on its day page")
    days = {x for x in days if "2024-01-01" <= x <= b.eastern_today().isoformat()}
    want = {b.day_href(x) for x in days}
    have = set()
    for p in glob.glob(os.path.join(SITE, "crl", "20[0-9][0-9]", "*", "[0-9]*", "index.html")):
        y, mon, dd = p.split(os.sep)[-4:-1]
        have.add(f"/crl/{y}/{mon}/{dd}")
    for x in sorted(have - want):
        bad.append(f"{x}: day page with no record dated that day")
    for x in sorted(want - have):
        bad.append(f"{x}: record dated that day but no day page")

    by_month = collections.defaultdict(list)
    for x in want:
        by_month[x.rsplit("/", 1)[0]].append(x)
    for m, xs in by_month.items():
        doc = read(m) or ""
        for x in xs:
            if f'href="{x}"' not in doc:
                bad.append(f"{m}: no link to {x}")
    for x in sorted(have & want):
        doc = read(x)
        t = html.unescape(re.search(r"<title>(.*?)</title>", doc, re.S).group(1))
        y, mon, dd = x.split("/")[2:]
        when = f"{mon.capitalize()} {dd}, {y}"
        if not t.startswith("FDA Complete Response Letter") or when not in t or len(t) > 100:
            bad.append(f"{x}: title {t!r}")
        for blob in re.findall(r'<script type="application/ld\+json">(.*?)</script>', doc, re.S):
            json.loads(blob)
        tables = "".join(re.findall(r"<table>.*?</table>", doc, re.S))
        for h in re.findall(r'href="(/fda-decision/[^"]+|https://[^"]+)"', tables):
            if h.startswith("https://download.open.fda.gov/"):
                continue                 # the FDA's file can be dated twice in its own release; one row per record
            if tables.count(f'href="{h}"') > 1:
                bad.append(f"{x}: {h} listed twice"); break
    months = collections.defaultdict(list)
    for r in recs:
        if not got[r["id"]]:
            months[r["announce_date"][:7]].append(r)
    for k, rs in months.items():
        doc = read(f"/crl/{k[:4]}/{b.MON[int(k[5:]) - 1]}") or ""
        dm = re.search(r'<meta name="description" content="([^"]*)"', doc)
        n = b.nlet(rs)
        if not dm or not re.search(rf"\b{n} (?:more )?announced by companies", html.unescape(dm.group(1))):
            bad.append(f"/crl/{k}: description does not say {n} announced by companies")

    if bad:
        print(f"FAIL: {len(bad)} company-announced CRL problem(s)")
        for x in bad[:25]:
            print("   ", x)
        return 1
    print(f"  PASS: {len(recs)} company-announced CRLs, {len(have)} day pages, each record on its pages with its source")
    return 0


if __name__ == "__main__":
    sys.exit(main())
