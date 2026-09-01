"""Is the conference name IN the filings we already fetch, and are we just throwing it away?

Our `context` column stores ~180 chars around the matched date. BPC extracted ESMO for 15
names out of the same public filings. If the conference name is in the document body but
outside our 180-char window, this is a CAPTURE bug, not missing signal -- and the fix costs
zero extra fetches because we already have the doc text in hand at stage 2.
"""
import csv, os, re, sys, time, urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
AGENT = os.environ.get("SEC_USER_AGENT", "David Moody rockyshoals@gmail.com")

CONFS = ["ESMO", "ASCO", "ASH", "AACR", "ESC", "AHA", "ACC", "EASD", "ADA", "AAN", "AAD",
         "EADV", "EULAR", "ACR", "ERS", "ATS", "WCLC", "SITC", "EHA", "ASTRO", "AASLD",
         "DDW", "ARVO", "AAO", "EURETINA", "ASRS", "CTAD", "AAIC", "ASGCT", "ASN", "CROI",
         "ECTRIMS", "SABCS", "IDWeek", "ISTH", "ASCO GU", "ASCO GI", "ADPD", "MDS", "OTS",
         "AAOS", "SLEEP", "ATTD", "ENDO", "ObesityWeek", "IAS", "ICAAC", "SNO", "NANS"]
RX = re.compile(r"\b(" + "|".join(sorted(set(CONFS), key=len, reverse=True)) + r")\b")
# the long-form names too -- many filings spell it out
LONG = re.compile(r"(American Society of Clinical Oncology|European Society for Medical "
                  r"Oncology|American Society of Hematology|American Association for Cancer "
                  r"Research|European Society of Cardiology|American Heart Association|"
                  r"American Academy of Neurology|European Respiratory Society|World "
                  r"Conference on Lung Cancer|Annual (?:Scientific )?(?:Meeting|Congress|"
                  r"Session)s?|Congress|Symposium)", re.I)

F = list(csv.DictReader(open(os.path.join(HERE, "readout_forward.csv"),
                             encoding="utf-8-sig", errors="replace")))
# sample vague rows that HAVE a url to re-fetch
vague = [r for r in F
         if (r.get("window_precision") or "") != "DAY"
         and (r.get("window_alt_precision") or "") != "DAY"
         and (r.get("url") or "").startswith("http")][:25]
print(f"re-fetching {len(vague)} undated filings to look INSIDE the full document\n")

hit_short = hit_long = 0
for r in vague:
    try:
        req = urllib.request.Request(r["url"], headers={"User-Agent": AGENT})
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read(900000).decode("utf-8", "replace")
    except Exception as e:
        print(f"  {r['ticker']:<7} fetch failed {type(e).__name__}")
        continue
    txt = re.sub(r"<[^>]+>", " ", raw)
    txt = re.sub(r"\s+", " ", txt)
    acr = sorted(set(RX.findall(txt)))
    lng = sorted(set(m.group(0)[:44] for m in LONG.finditer(txt)))[:3]
    if acr:
        hit_short += 1
    if lng:
        hit_long += 1
    ctx = (r.get("context") or "")
    in_ctx = bool(RX.search(ctx))
    print(f"  {r['ticker']:<7}win={str(r.get('window') or r.get('window_alt'))[:10]:<12}"
          f"acr={','.join(acr[:4]) or '-':<22}ctx_had_it={in_ctx}")
    if lng and not acr:
        print(f"          long-form: {lng}")
    time.sleep(0.12)

print(f"\n  {hit_short}/{len(vague)} documents contain a conference ACRONYM")
print(f"  {hit_long}/{len(vague)} contain conference-ish long-form language")
print("\n  -> if these are non-zero while `context` showed 0, the name is in the doc and our")
print("     180-char context window is simply cutting it off. Fix = scan the whole doc at")
print("     stage 2 (already in memory) and store the hit in its own column.")
