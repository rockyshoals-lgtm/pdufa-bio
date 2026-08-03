# -*- coding: utf-8 -*-
"""sls_daily.py -- collect everything that happened to SELLAS today, from primary sources only.

/sls is meant to be the record for this name, and a record that updates once a month is not a
record. This runs nightly and gathers, in order of trust:

  1. SEC EDGAR filings (CIK 1390478). The authoritative source: nothing is more primary than the
     document the company filed. 8-K/6-K exhibits are fetched so the actual press-release text is
     read, not just the form type.
  2. SELLAS's own IR press-release feed. First-party company statements, including releases that
     never get 8-K'd (biotechs 8-K only what is material, so the feed catches the rest).
  3. Executive quotes, pulled VERBATIM out of those two sources and stored with the speaker and a
     link. Never paraphrased: a paraphrased CEO quote is an invented one.
  4. Price from Polygon: last close, day move, volume against its own 20-day average, 52-week range.

Deliberately NOT collected: third-party aggregator headlines. Most "SLS news" on the wires is a
listicle that merely mentions the ticker, and the whole premise of this page is that everything on
it traces to the company or the SEC.

Output is an append-only log, _sls_activity.json, so the page can show a dated timeline and so
nothing already recorded is ever silently rewritten.

    python sls_daily.py            # collect and append
    python sls_daily.py --dry-run  # show what it found, write nothing
"""
import argparse, json, os, re, sys, time
import datetime as dt
import urllib.request, urllib.error

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "_sls_activity.json")
TICKER = "SLS"
CIK = 1390478                      # SELLAS Life Sciences Group, Inc.
IR_RSS = "https://ir.sellaslifesciences.com/rss/pressrelease.aspx"
SEC_UA = {"User-Agent": os.environ.get("SEC_USER_AGENT", "pdufa.bio research contact@pdufa.bio")}
WEB_UA = {"User-Agent": "Mozilla/5.0 (compatible; pdufa.bio/1.0; +https://www.pdufa.bio)"}

# Forms that can carry something that matters to the REGAL story or the corporate situation.
MATERIAL = {"8-K", "8-K/A", "6-K", "10-Q", "10-K", "S-4", "SC 13D", "SC 13D/A", "SC 13E3",
            "DEFM14A", "425", "SC TO-T", "SC 14D9"}


def get(url, headers=None, tries=3, timeout=25):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=headers or SEC_UA)
            return urllib.request.urlopen(req, timeout=timeout).read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                return b""
            time.sleep(1.5 * (i + 1))
        except Exception:
            time.sleep(1.5 * (i + 1))
    return b""


def strip_html(raw):
    t = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
    t = re.sub(r"<(script|style)\b.*?</\1>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = (t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#8217;", "'")
          .replace("&#8220;", '"').replace("&#8221;", '"').replace("&quot;", '"')
          .replace("&#39;", "'").replace("&rsquo;", "'").replace("&ldquo;", '"')
          .replace("&rdquo;", '"').replace("&mdash;", ", "))
    t = re.sub(r"&#\d+;", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# An executive quote is a quoted passage sitting next to an attribution verb and a person. Both
# orders occur: '"...," said Dr. Stergiou' and 'Dr. Stergiou said, "..."'.
SAY = r"(?:said|stated|commented|added|noted|explained|continued)"
PERSON = r"((?:Dr\.|Mr\.|Ms\.)?\s*[A-Z][a-zA-Z.\-]+(?:\s+[A-Z][a-zA-Z.\-]+){0,3})"
Q_AFTER = re.compile(r"[\"“]([^\"”]{40,600})[\"”][,\s]*" + SAY + r"\s+" + PERSON, re.S)
Q_BEFORE = re.compile(PERSON + r"[^.]{0,80}?\b" + SAY + r"[,:]?\s*[\"“]([^\"”]{40,600})[\"”]", re.S)
# Longest-first, and the compound form is captured whole. A bare "President" alternative matched
# inside "Senior Vice President" and so billed SELLAS's Chief Development Officer as President.
_R = (r"Chief [A-Z][a-z]+ Officer|Senior Vice President|Executive Vice President|Vice President|"
      r"President|Chairman|Founder|CEO|CMO|CFO|COO|CSO")
ROLE = re.compile(rf"((?:{_R})(?:\s+and\s+(?:{_R}))?)")
QUOTE_CAP = 400        # keep excerpts short; the link carries the reader to the full text


def extract_quotes(text, context_window=260):
    """[(speaker, quote)] verbatim. Conservative: requires an attribution verb AND a capitalised
    name, so ordinary quoted phrases in a filing are not mistaken for executive commentary."""
    out, seen = [], set()
    for rx, order in ((Q_AFTER, "qp"), (Q_BEFORE, "pq")):
        for m in rx.finditer(text):
            quote, person = (m.group(1), m.group(2)) if order == "qp" else (m.group(2), m.group(1))
            quote = re.sub(r"\s+", " ", quote).strip()
            person = re.sub(r"\s+", " ", person).strip(" ,.")
            if not person or len(person) < 4 or person.lower() in ("the company", "the board"):
                continue
            # Take the role ONLY from the text immediately following the name, which is where a
            # press release puts it ("said Angelos Stergiou, M.D., President and CEO of SELLAS").
            # A wider window picks up whoever was quoted in the previous paragraph: it labelled
            # SELLAS's CMO as "President" on the first pass. No adjacent role means no role.
            tail_start = m.end(2) if order == "qp" else m.end(1)
            role = ROLE.search(text[tail_start: tail_start + 110])
            key = quote[:80].lower()
            if key in seen:
                continue
            seen.add(key)
            out.append({"speaker": person,
                        "role": (role.group(1) if role else ""),
                        "quote": quote[:QUOTE_CAP] + ("..." if len(quote) > QUOTE_CAP else "")})
    return out[:3]


# ------------------------------------------------------------------ sources
def edgar_filings(since):
    raw = get(f"https://data.sec.gov/submissions/CIK{CIK:010d}.json")
    if not raw:
        return []
    d = json.loads(raw)
    r = d.get("filings", {}).get("recent", {})
    items = []
    for form, filed, acc, doc, desc in zip(
            r.get("form", []), r.get("filingDate", []), r.get("accessionNumber", []),
            r.get("primaryDocument", []), r.get("primaryDocDescription", [])):
        if filed <= since:
            continue
        base = f"https://www.sec.gov/Archives/edgar/data/{CIK}/{acc.replace('-', '')}"
        item = {"kind": "filing", "date": filed, "form": form, "accession": acc,
                "title": desc or form, "url": f"{base}/{doc}", "material": form in MATERIAL,
                "quotes": [], "excerpt": ""}
        # For 8-K/6-K read the actual content, not just the form type. Preference order matters:
        # an EX-99 press release is the most readable, but plenty of material 8-Ks have no press
        # release at all -- SELLAS's June 25 change-of-control filing carried only EX-10 agreements
        # -- so fall back to the 8-K body, which is where the Item narrative lives.
        if form in ("8-K", "8-K/A", "6-K"):
            idx = get(base + "/index.json")
            if idx:
                try:
                    files = [f["name"] for f in json.loads(idx)["directory"]["item"]
                             if f["name"].lower().endswith((".htm", ".txt"))]
                    ex99 = [n for n in files if "ex99" in n.lower().replace("-", "").replace("_", "")]
                    exhibits = sorted({re.sub(r"^.*?(ex\d+)[-_]?(\d+).*$", r"EX-\1.\2", n, flags=re.I)
                                       .upper().replace("EX-EX", "EX-")
                                       for n in files if re.search(r"ex\d", n, re.I)})
                    body = [n for n in files if n.lower().endswith("8k.htm") or "_8k" in n.lower()]
                    pick = (ex99 or body or [None])[0]
                    if pick:
                        txt = strip_html(get(base + "/" + pick))
                        if txt:
                            item["url"] = base + "/" + pick
                            item["quotes"] = extract_quotes(txt)
                            items_hit = re.findall(r"Item\s+(\d\.\d\d)\.?\s+([A-Z][^.]{6,90})", txt)
                            if ex99:
                                hd = re.search(r"Exhibit 99\.\d\s+(.{20,180}?)"
                                               r"(?:\s+[A-Z]{3,}, |\s+\d{1,2}, 20)", txt)
                                if hd:
                                    item["title"] = hd.group(1).strip()
                                item["excerpt"] = txt[:300]
                            elif items_hit:
                                # "Item 5.02 Departure of Directors..." is the real headline here
                                item["title"] = "; ".join(f"Item {n} {d.strip()}"
                                                          for n, d in items_hit[:2])[:200]
                                k = txt.find("Item")
                                item["excerpt"] = txt[k:k + 300] if k >= 0 else txt[:300]
                            else:
                                item["excerpt"] = txt[:300]
                        if exhibits:
                            item["exhibits"] = exhibits[:6]
                except Exception:
                    pass
        items.append(item)
        time.sleep(0.12)
    return items


def ir_press_releases(since):
    raw = get(IR_RSS, headers=WEB_UA)
    if not raw:
        return []
    xml = raw.decode("utf-8", "replace")
    out = []
    for m in re.finditer(r"<item>(.*?)</item>", xml, re.S):
        blk = m.group(1)

        def tag(t):
            mm = re.search(rf"<{t}[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{t}>", blk, re.S)
            return re.sub(r"\s+", " ", mm.group(1)).strip() if mm else ""
        pub, title, link = tag("pubDate"), tag("title"), tag("link")
        d = ""
        for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z", "%d %b %Y %H:%M:%S %Z"):
            try:
                d = dt.datetime.strptime(pub.strip(), fmt).date().isoformat(); break
            except Exception:
                continue
        if not d or d <= since:
            continue
        rec = {"kind": "press_release", "date": d, "form": "IR press release",
               "title": strip_html(title)[:220], "url": link, "material": True,
               "excerpt": strip_html(tag("description"))[:300], "quotes": []}
        # Fetch the release body: the RSS description is a stub, and the executive commentary the
        # page is meant to surface only exists in the full text.
        if link:
            body = strip_html(get(link, headers=WEB_UA))
            if body:
                rec["quotes"] = extract_quotes(body)
                if not rec["excerpt"]:
                    rec["excerpt"] = body[:300]
            time.sleep(0.3)
        out.append(rec)
    return out


def price_block():
    key = None
    for p in (os.path.join(HERE, "Odin Perfection", ".env_master"), os.path.join(HERE, ".env")):
        if os.path.exists(p):
            for line in open(p, encoding="utf-8", errors="ignore"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    key = os.environ.get("POLYGON_API_KEY")
    if not key:
        return {}
    end = dt.date.today()
    start = end - dt.timedelta(days=400)
    raw = get(f"https://api.polygon.io/v2/aggs/ticker/{TICKER}/range/1/day/"
              f"{start}/{end}?adjusted=true&sort=asc&limit=50000&apiKey={key}",
              headers=WEB_UA)
    if not raw:
        return {}
    res = (json.loads(raw) or {}).get("results") or []
    if len(res) < 2:
        return {}
    bars = [(dt.datetime.fromtimestamp(x["t"] / 1000, dt.timezone.utc).date().isoformat(),
             x["c"], x.get("v") or 0) for x in res if x.get("c")]
    last, prev = bars[-1], bars[-2]
    vol20 = [b[2] for b in bars[-21:-1] if b[2]]
    closes52 = [b[1] for b in bars if b[0] >= (end - dt.timedelta(days=365)).isoformat()]
    return {
        "as_of": last[0],
        "close": round(last[1], 4),
        "prev_close": round(prev[1], 4),
        "change_pct": round((last[1] / prev[1] - 1) * 100, 2) if prev[1] else None,
        "volume": int(last[2]),
        "rel_volume": round(last[2] / (sum(vol20) / len(vol20)), 2) if vol20 else None,
        "low_52w": round(min(closes52), 4) if closes52 else None,
        "high_52w": round(max(closes52), 4) if closes52 else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--since", default="", help="override the cursor (YYYY-MM-DD)")
    a = ap.parse_args()

    state = {"events": [], "cursor": "2026-06-01", "price": {}, "last_run": ""}
    if os.path.exists(LOG):
        try:
            state.update(json.load(open(LOG, encoding="utf-8")))
        except Exception:
            pass
    since = a.since or state.get("cursor") or "2026-06-01"
    print(f"SELLAS daily collect  |  looking for anything after {since}")

    filings = edgar_filings(since)
    prs = ir_press_releases(since)
    price = price_block()

    known = {(e.get("kind"), e.get("url")) for e in state["events"]}
    new = [e for e in (filings + prs) if (e.get("kind"), e.get("url")) not in known]
    new.sort(key=lambda e: e["date"])

    print(f"  EDGAR filings since cursor : {len(filings)}")
    print(f"  IR press releases          : {len(prs)}")
    print(f"  new (not already logged)   : {len(new)}")
    if price:
        chg = price.get("change_pct")
        print(f"  price {price['as_of']}: ${price['close']} "
              f"({chg:+.2f}%)  vol {price['volume']:,} ({price.get('rel_volume')}x 20d avg)")
    for e in new:
        star = " *MATERIAL*" if e["material"] else ""
        print(f"    {e['date']}  {e['form']:<18}{e['title'][:70]}{star}")
        for q in e["quotes"]:
            print(f"       quote - {q['speaker']} ({q['role'] or 'role n/a'}): {q['quote'][:110]}")

    if a.dry_run:
        print("\nDRY RUN. nothing written.")
        return 0

    state["events"] = (state["events"] + new)[-400:]
    state["price"] = price
    state["last_run"] = dt.date.today().isoformat()
    if new:
        state["cursor"] = max(e["date"] for e in new)
    tmp = LOG + ".tmp"
    json.dump(state, open(tmp, "w", encoding="utf-8"), indent=1)
    os.replace(tmp, LOG)
    print(f"\nwrote {os.path.basename(LOG)}  ({len(state['events'])} logged events, "
          f"cursor {state['cursor']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
