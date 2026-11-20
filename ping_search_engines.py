# -*- coding: utf-8 -*-
"""ping_search_engines.py -- tell search engines the site changed, using the methods that still exist.

The backlog asks for a ping on every deploy, having found the real problem: Google last read
sitemap.xml on Jul 27 while every improvement since was invisible to it. The suggested fix,
GET google.com/ping?sitemap=..., no longer exists. Verified live, not assumed:

    google.com/ping?sitemap=...  ->  404  "Sitemaps ping is deprecated"   (Google removed it, 2023)
    bing.com/ping?sitemap=...    ->  410  Gone                            (Bing removed it too)

So this does the three things that do work:

  1. INDEXNOW. A real, live protocol. Submitting a URL list pushes it to Bing, Yandex, Seznam and
     Naver immediately. Google does not participate, so this does not solve the Google problem, but
     it is free and it is the only genuine push channel available.
  2. GOOGLE SEARCH CONSOLE API (sitemaps.submit). The supported replacement for the old ping. It
     needs a service-account credential with access to the property; without one this step reports
     that it is unconfigured rather than pretending to have run.
  3. ACCURATE <lastmod>. Google's own stated replacement for ping is a truthful lastmod, which the
     sitemap generator already sets from real file mtimes. This checks it and warns if it looks
     wrong, because a lastmod that lies is worse than no ping at all.

    python ping_search_engines.py [--dry-run]
"""
import argparse, datetime as dt, json, os, re, sys, time, urllib.error, urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
SITEMAP = os.path.join(SITE, "sitemap.xml")
HOST = "www.pdufa.bio"
KEYFILE_STATE = os.path.join(HERE, "_indexnow_key.txt")
UA = {"User-Agent": "pdufa.bio/1.0 (+https://www.pdufa.bio)", "Content-Type": "application/json"}
MAX_URLS = 8000


def indexnow_key():
    """A stable 32-hex key, also served at https://<host>/<key>.txt so the protocol can verify we
    control the domain."""
    if os.path.exists(KEYFILE_STATE):
        k = open(KEYFILE_STATE, encoding="utf-8").read().strip()
        if re.fullmatch(r"[0-9a-f]{32}", k):
            return k
    k = os.urandom(16).hex()
    open(KEYFILE_STATE, "w", encoding="utf-8").write(k)
    return k


def changed_urls(since_days=2):
    """URLs whose sitemap lastmod is recent. Submitting the whole sitemap every night trains the
    receiving engines to ignore us, so only what actually moved goes in."""
    if not os.path.exists(SITEMAP):
        return [], None
    xml = open(SITEMAP, encoding="utf-8", errors="replace").read()
    entries = re.findall(r"<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>", xml)
    if not entries:
        return [], None
    newest = max(d for _, d in entries)
    cutoff = (dt.date.today() - dt.timedelta(days=since_days)).isoformat()
    # Newest change first, and at equal dates the shallower URL first, so when a downstream cap
    # (IndexNow's 10k, SubmitUrlBatch's 80) truncates the list, what survives is today's changes
    # and the hub pages rather than an alphabetical run of ticker pages.
    picked = sorted(((u, d) for u, d in entries if d >= cutoff),
                    key=lambda x: (x[1], -x[0].count("/")), reverse=True)
    urls = [u for u, _ in picked]
    # Audit 2026-10-13 order 2: ORDER, not volume. Bing's AI answer for "fda approval decisions this
    # week" was built from a copy of our daily hubs taken before Oct 8 while the hubs themselves had
    # been right for five days, because the nightly batch was ~1,300 URLs with the 80-URL Bing
    # channel taking whichever came first. The daily hubs go first, then the pages whose decision or
    # status changed (the dataset's most recently updated rows), then everything else. The Bing batch
    # is the priority list; IndexNow gets the priority list followed by the rest.
    return prioritise(urls), newest


HUBS = ["https://www.pdufa.bio/", "https://www.pdufa.bio/fda-decisions-today",
        "https://www.pdufa.bio/fda-approval-decisions-this-week", "https://www.pdufa.bio/fda-this-month",
        "https://www.pdufa.bio/calendar", "https://www.pdufa.bio/decisions", "https://www.pdufa.bio/readouts",
        "https://www.pdufa.bio/fda-approval-letters", "https://www.pdufa.bio/conferences"]


def changed_event_urls(limit=60):
    """Pages of the dataset rows updated most recently (decision pages, event pages, drug pages of a row
    whose status or date moved), newest `ua` first. Read from the dataset, not the sitemap."""
    try:
        src = open(os.path.join(SITE, "api", "v1", "dataset.mjs"), encoding="utf-8", errors="replace").read()
        rows = json.loads(src[src.index("["):src.rindex("]") + 1])
    except Exception:
        return []
    # decisions first (the answer-box rows), then readouts, then conferences; newest update first within each
    order = {"PDUFA": 0, "AdComm": 1, "Readout": 2, "Conference": 3}
    def _ts(r):
        return -int(re.sub(r"\D", "", str(r.get("ua"))[:19]) or 0)
    rows = sorted((r for r in rows if r.get("ua")), key=lambda r: (order.get(str(r.get("type")), 9), _ts(r)))
    out = []
    for r in rows[:limit]:
        u = str(r.get("url") or "")
        if u.startswith("/"):
            u = "https://www.pdufa.bio" + u
        if u.startswith("https://www.pdufa.bio/") and u not in out:
            out.append(u)
        d = r.get("_d") or {}
        for k in ("decision_page", "event_slug"):
            v = d.get(k)
            if isinstance(v, str) and v:
                full = ("https://www.pdufa.bio" + v) if v.startswith("/") else ("https://www.pdufa.bio/pdufa/" + v)
                if full not in out:
                    out.append(full)
    return out


def prioritise(urls):
    changed = set(urls)
    first = [u for u in HUBS if u in changed]
    first += [u for u in changed_event_urls() if u in changed and u not in first]
    rest = [u for u in urls if u not in first]
    return first + rest


def post_indexnow(key, urls, dry):
    """True when every endpoint accepted the list (200/202), after up to 3 tries each."""
    import time
    body = json.dumps({"host": HOST, "key": key,
                       "keyLocation": f"https://{HOST}/{key}.txt",
                       "urlList": urls[:MAX_URLS]}).encode()
    if dry:
        print(f"  [dry-run] would POST {len(urls[:MAX_URLS])} URL(s) to IndexNow")
        return True
    ok = True
    # Two endpoints on purpose. api.indexnow.org fans out to every participating engine, but
    # Bing Webmaster Tools' IndexNow panel showed ZERO submissions attributed to the property
    # despite weeks of HTTP 200s from the shared endpoint (key file verified live and
    # matching). Bing's own ingest endpoint is the one its console credits, so it gets a
    # direct copy. Duplicate notification is explicitly harmless under the protocol.
    for ep, label in (("https://api.indexnow.org/indexnow", "IndexNow (all engines)"),
                      ("https://www.bing.com/indexnow", "IndexNow (Bing direct)")):
        for attempt in range(3):
            try:
                req = urllib.request.Request(ep, data=body, headers=UA, method="POST")
                r = urllib.request.urlopen(req, timeout=25)
                print(f"  {label}: HTTP {r.status} for {len(urls[:MAX_URLS])} URL(s)")
                break
            except urllib.error.HTTPError as e:
                detail = {403: "key file not reachable yet -- it deploys with this commit, so the first "
                               "run after a fresh key can fail; the next run succeeds",
                          422: "URL/host mismatch", 429: "too many requests"}.get(e.code, e.reason)
                print(f"  {label}: HTTP {e.code} ({detail}), try {attempt + 1} of 3")
            except Exception as e:
                print(f"  {label}: {type(e).__name__}: {e}, try {attempt + 1} of 3")
            time.sleep(10 * (attempt + 1))
        else:
            ok = False
    return ok


def submit_bing_batch(urls, dry, cap=40):
    """SubmitUrlBatch on the JSON protocol -- the quota-backed channel with real attribution.

    BWT showed 12 of ~100 daily submissions used while 418 pages sit unfetched on Google and Bing
    delivers 10x Google's impressions. This uses the rest of that quota on whatever actually
    changed today. JSON protocol deliberately: Microsoft's own protocol table lists JSON as a
    SUPPORTED protocol alongside the retiring SOAP/POX -- the Aug 31 retirement banner does not
    apply to this endpoint (learn.microsoft.com/bingwebmaster/api-protocols).

    Capped at 80 to leave headroom for manual submissions from the console. No key -> says so and
    moves on; a missing secret must never fail the build.
    """
    key = os.environ.get("BING_WEBMASTER_API_KEY", "").strip()
    if not key:
        print("  Bing SubmitUrlBatch: no BING_WEBMASTER_API_KEY in env; skipped.")
        return 0
    # Audit 2026-10-13 order 2, seen in the first ordered run (38506884875): the daily quota is shared by
    # the three scheduled runs and the console; a batch larger than what remains is REJECTED whole
    # ("Quota remaining for today: 20, Submitted: 80"), so the hubs at the front of the list were not
    # submitted at all. Submit 40 (three runs fit the quota), and on the quota error resubmit exactly
    # the remaining number, hubs first.
    batch = urls[:max(0, cap)]
    if not batch:
        print("  Bing SubmitUrlBatch: nothing to submit (nothing changed, or no quota left today).")
        return 0
    if dry:
        print(f"  [dry-run] would SubmitUrlBatch {len(batch)} URL(s) to Bing")
        return len(batch)
    for attempt in range(2):
        body = json.dumps({"siteUrl": "https://www.pdufa.bio/", "urlList": batch}).encode()
        try:
            req = urllib.request.Request(
                "https://ssl.bing.com/webmaster/api.svc/json/SubmitUrlBatch?apikey=" + key,
                data=body, headers={**UA, "Content-Type": "application/json; charset=utf-8"},
                method="POST")
            r = urllib.request.urlopen(req, timeout=45)
            print(f"  Bing SubmitUrlBatch: HTTP {r.status} for {len(batch)} URL(s) "
                  f"(quota-backed, console-attributed); first: {batch[0]}")
            return len(batch)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:160]
            print(f"  Bing SubmitUrlBatch: HTTP {e.code} -- {detail}")
            m = re.search(r"Quota remaining for today:\s*(\d+)", detail)
            if m and attempt == 0 and int(m.group(1)) > 0:
                batch = batch[:int(m.group(1))]
                print(f"  Bing SubmitUrlBatch: resubmitting the first {len(batch)} (the remaining quota), hubs first")
                continue
            return 0
        except Exception as e:
            print(f"  Bing SubmitUrlBatch: {type(e).__name__}: {e}")
            return 0


def submit_gsc(dry):
    """Google Search Console sitemaps.submit. Needs a service-account JSON in the
    GSC_SERVICE_ACCOUNT_JSON env var, and that account added as an owner of the property.
    Returns None when not configured, else True only if every sitemap was accepted."""
    raw = os.environ.get("GSC_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        print("  Google Search Console: NOT CONFIGURED. This is the only real channel to Google; "
              "the old ping URL is gone. To enable: create a service account, add it as a user on "
              "the pdufa.bio GSC property, and put its JSON in the GSC_SERVICE_ACCOUNT_JSON secret.")
        return None
    try:
        from google.oauth2 import service_account          # noqa
        from googleapiclient.discovery import build        # noqa
    except Exception:
        print("  Google Search Console: credential present but google-api-python-client is not "
              "installed in this environment; add it to the workflow's pip install step.")
        return False
    if dry:
        print("  [dry-run] would call searchconsole sitemaps.submit"); return True
    try:
        creds = service_account.Credentials.from_service_account_info(
            json.loads(raw), scopes=["https://www.googleapis.com/auth/webmasters"])
        svc = build("searchconsole", "v1", credentials=creds, cache_discovery=False)

        # A property is either URL-prefix ("https://www.pdufa.bio/") or Domain
        # ("sc-domain:pdufa.bio"), and sitemaps.submit needs the exact form. Rather than make the
        # owner work out which they have, ask Google which properties this account can see and use
        # those. If it can see none, the service account was not added to the property, which is
        # the step people miss.
        # Retried (red team, Nov 20): this step now fails the run, so a transient API error must not.
        def _retry(call, tries=3):
            for k in range(tries):
                try:
                    return call()
                except Exception:  # noqa: BLE001
                    if k == tries - 1:
                        raise
                    time.sleep(5 * (k + 1))
        try:
            visible = [s["siteUrl"] for s in (_retry(lambda: svc.sites().list().execute()).get("siteEntry") or [])]
        except Exception:
            visible = []
        wanted = [s for s in visible if HOST in s or s == f"sc-domain:{HOST.replace('www.', '')}"]
        if not wanted:
            print(f"  Google Search Console: the service account can see {len(visible)} propert(ies)"
                  f"{' (' + ', '.join(visible[:4]) + ')' if visible else ''}, none of them pdufa.bio. "
                  f"Add its client_email as an OWNER on the property in Search Console "
                  f"(Settings -> Users and permissions). That is the step that is usually missed.")
            return False
        ok = True
        # sitemap_index.xml (2026-11-20): Search Console lists each section sitemap under it with its own
        # submitted-vs-indexed count, which is how we see WHICH kind of page Google is not indexing.
        feeds = [f"https://{HOST}/sitemap.xml"]
        if os.path.exists(os.path.join(SITE, "sitemap_index.xml")):
            feeds.append(f"https://{HOST}/sitemap_index.xml")
        for site, feed in [(st, fd) for st in wanted for fd in feeds]:
            try:
                _retry(lambda: svc.sitemaps().submit(siteUrl=site, feedpath=feed).execute())
                # Read the state back. lastSubmitted and lastDownloaded are different things and
                # confusing them wastes an afternoon: submit is us telling Google the file changed
                # (updates immediately, always), lastDownloaded is Google choosing to fetch it
                # (their schedule, not ours). Search Console's "Last read" column shows the second
                # one, so a successful submit legitimately leaves "Last read" weeks in the past.
                # Logging both means this step can be judged from its own output.
                try:
                    d = svc.sitemaps().get(siteUrl=site, feedpath=feed).execute()
                    print(f"  Google Search Console: accepted {feed} for {site}\n"
                          f"      lastSubmitted (us)     {d.get('lastSubmitted')}\n"
                          f"      lastDownloaded (Google){d.get('lastDownloaded')}   "
                          f"warnings={d.get('warnings')} errors={d.get('errors')}")
                except Exception:
                    print(f"  Google Search Console: {feed} resubmitted for {site}")
            except Exception as e:
                ok = False
                msg = str(e)
                print(f"  Google Search Console: {site} {feed} failed -> {type(e).__name__}: {msg[:180]}")
                if "403" in msg:
                    print("      403 means the service account is not an Owner on this property. "
                          "sitemaps.submit is not available to a 'Full' user.")
        return ok
    except Exception as e:
        print(f"  Google Search Console: {type(e).__name__}: {e}")
        return False


# --------------------------------------------------------------------------------------------------------------
# 2026-11-20 (indexing round 3): submit exactly what changed, prove it went, fail loudly when it did not.
#
# The 2-day lastmod window above sent IndexNow 1,739 of 1,785 URLs on the morning of Nov 20, three times a day, and
# spent Bing's 100-a-day batch on the same hubs every run. Now the set is the pages whose content hash moved (or that
# entered the sitemap) since the last build whose submission succeeded: _sitemap_lastmod.json at that commit vs now.
# The workflow keeps that commit in the tag `indexed-ok`, moved only after a run whose submissions all landed, so a
# failed run's pages are carried into the next run instead of being lost.

def _git_show(ref, path):
    import subprocess
    try:
        r = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=HERE, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


def key_to_url(key):
    rel = key[len("pdufa_site_src/"):] if key.startswith("pdufa_site_src/") else key
    if rel == "index.html":
        return "https://www.pdufa.bio/"
    if rel.endswith("/index.html"):
        return "https://www.pdufa.bio/" + rel[:-len("/index.html")]
    if rel.endswith(".html") and "/" not in rel:
        return "https://www.pdufa.bio/" + rel[:-len(".html")]
    return None


def sitemap_urls(xml):
    return set(re.findall(r"<loc>([^<]+)</loc>", xml or ""))


def changed_since(old_state, new_state, old_sitemap, new_sitemap):
    """URLs in the current sitemap whose content hash or content date moved, or that are new to the sitemap."""
    live = sitemap_urls(new_sitemap)
    out = set(live - sitemap_urls(old_sitemap)) if old_sitemap is not None else set()
    for k, v in new_state.items():
        o = old_state.get(k)
        if o is None or o.get("hash") != v.get("hash") or o.get("date") != v.get("date"):
            u = key_to_url(k)
            if u and u in live:
                out.add(u)
    return out


def changed_this_build(refs):
    """(urls newest-first with hubs first, ref used) or (None, None) when no base commit is readable."""
    new_sm = open(SITEMAP, encoding="utf-8", errors="replace").read() if os.path.exists(SITEMAP) else ""
    st_f = os.path.join(HERE, "_sitemap_lastmod.json")
    new_state = json.load(open(st_f, encoding="utf-8")) if os.path.exists(st_f) else {}
    for ref in refs:
        if not ref:
            continue
        old_raw = _git_show(ref, "_sitemap_lastmod.json")
        if old_raw is None:
            print(f"  base {ref}: not readable here; trying the next")
            continue
        try:
            old_state = json.loads(old_raw)
        except Exception:
            continue
        old_sm = _git_show(ref, "pdufa_site_src/sitemap.xml")
        got = changed_since(old_state, new_state, old_sm, new_sm)
        dates = dict(re.findall(r"<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>", new_sm))
        ordered = sorted(got, key=lambda u: (dates.get(u, ""), -u.count("/")), reverse=True)
        return prioritise(ordered), ref
    return None, None


def bing_quota_left():
    key = os.environ.get("BING_WEBMASTER_API_KEY", "").strip()
    if not key:
        return None
    try:
        q = urllib.request.urlopen(urllib.request.Request(
            "https://ssl.bing.com/webmaster/api.svc/json/GetUrlSubmissionQuota?siteUrl=https%3A%2F%2Fwww.pdufa.bio%2F&apikey="
            + key, headers=UA), timeout=30)
        d = json.loads(q.read().decode("utf-8", "replace")).get("d") or {}
        return int(d.get("DailyQuota"))
    except Exception as e:
        print(f"  Bing quota: could not read ({type(e).__name__}); using the fixed batch of 40")
        return None


def summary(lines):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    # 2026-10-18: --only "url,url" submits exactly these (IndexNow + SubmitUrlBatch), the on-demand "request
    # indexing" path for bing-submit.yml. Nothing is read from the sitemap in that mode.
    ap.add_argument("--only", default="")
    # 2026-11-20: --since REF submits the pages that changed since that commit (the workflow passes the tag
    # indexed-ok, the last build whose submissions all landed). Without it, or if REF is unreadable, HEAD~1.
    ap.add_argument("--since", default="")
    a = ap.parse_args()

    if a.only.strip():
        only = [u.strip() for u in a.only.split(",") if u.strip().startswith("https://www.pdufa.bio/")]
        bad = [u.strip() for u in a.only.split(",") if u.strip() and not u.strip().startswith("https://www.pdufa.bio/")]
        if bad:
            print(f"  ignored {len(bad)} URL(s) not on https://www.pdufa.bio/: {bad[:3]}")
        print(f"on-demand submission of {len(only)} URL(s):")
        for u in only:
            print("    " + u)
        post_indexnow(indexnow_key(), only, a.dry_run)
        left = bing_quota_left()
        submit_bing_batch(only, a.dry_run, cap=40 if left is None else min(40, left))
        return 0

    # RULE 1, the timezone trap. The sitemap's lastmod values are stamped in UTC by
    # build_sitemap/build_date_modified, so the "is this in the future" test has to be made in
    # UTC too. Comparing a UTC date against this machine's LOCAL date (Pacific) made the check
    # cry wolf every evening after 5pm PT, when UTC has already rolled over: on 2026-08-22 at
    # 21:23 PT it warned that a lastmod of 2026-08-23 was "tomorrow" when it was simply today in
    # the zone that wrote it. CI never saw it (12:00 and 21:00 UTC land at 05:00 and 14:00 PT,
    # same calendar day), which is exactly how a warning like this survives unnoticed.
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    urls, base = changed_this_build([a.since, "HEAD~1"])
    if urls is None:
        urls, newest = changed_urls()
        base = "the 2-day lastmod window (no base commit readable)"
    else:
        newest = max(re.findall(r"<lastmod>([^<]+)</lastmod>", open(SITEMAP, encoding="utf-8").read()) or ["n/a"])
    print(f"sitemap newest lastmod {newest} (today {today}); {len(urls)} URL(s) changed since {base}")
    if newest and newest != "n/a" and newest > today:
        print(f"  WARNING: lastmod {newest} is in the future. A sitemap that claims tomorrow's date "
              f"is a reason for a crawler to distrust all of them.")

    key = indexnow_key()
    kf = os.path.join(SITE, f"{key}.txt")
    if not os.path.exists(kf) and not a.dry_run:
        open(kf, "w", encoding="utf-8").write(key)
        print(f"  wrote IndexNow key file -> /{key}.txt (deploys with this commit)")

    in_ok, sent_bing, left = True, 0, None
    if urls:
        print("  submission order, first 20:")
        for u in urls[:20]:
            print("    " + u)
        in_ok = post_indexnow(key, urls, a.dry_run)
        left = bing_quota_left()
        # Keep 5 of the day's quota for a by-hand submission from the console or bing-submit.yml.
        cap = 40 if left is None else max(0, left - 5)
        sent_bing = submit_bing_batch(urls, a.dry_run, cap=cap)
    else:
        print("  nothing changed since the last submitted build; no URL submission")
    gsc_ok = submit_gsc(a.dry_run)

    summary(["### Search engine submission",
             f"- Changed pages since {base}: **{len(urls)}**",
             f"- IndexNow (Bing, Yandex, Seznam, Naver): {'accepted' if in_ok else '**FAILED**'}"
             + (f" for {len(urls)} URL(s)" if urls else " (nothing to send)"),
             f"- Bing SubmitUrlBatch: {sent_bing} URL(s)" + ("" if left is None else f" (daily quota left before: {left})"),
             "- Google Search Console sitemaps: " + {None: "not configured", True: "accepted", False: "**FAILED**"}[gsc_ok]])
    # Loud on purpose (2026-11-20): a changed page that no engine was told about is the failure this step exists to
    # prevent. A failure leaves the tag indexed-ok where it was, so the next run sends these pages again.
    if not in_ok:
        print("FAIL: changed pages were not submitted (see above); the next run will resend them.")
        return 1
    # Exit 2: every changed URL went out, only the Search Console sitemap call failed. The workflow still moves
    # indexed-ok (the sitemap is resubmitted every run, so holding the tag would only resend URLs already sent and
    # grow the backlog every run) and still fails the step so the failure is seen.
    if gsc_ok is False:
        print("FAIL: the Search Console sitemap submission failed; changed URLs were sent to IndexNow and Bing.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
