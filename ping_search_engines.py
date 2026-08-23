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
import argparse, datetime as dt, json, os, re, sys, urllib.error, urllib.request

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
    return [u for u, _ in picked], newest


def post_indexnow(key, urls, dry):
    body = json.dumps({"host": HOST, "key": key,
                       "keyLocation": f"https://{HOST}/{key}.txt",
                       "urlList": urls[:MAX_URLS]}).encode()
    if dry:
        print(f"  [dry-run] would POST {len(urls[:MAX_URLS])} URL(s) to IndexNow")
        return
    try:
        # Two endpoints on purpose. api.indexnow.org fans out to every participating engine, but
        # Bing Webmaster Tools' IndexNow panel showed ZERO submissions attributed to the property
        # despite weeks of HTTP 200s from the shared endpoint (key file verified live and
        # matching). Bing's own ingest endpoint is the one its console credits, so it gets a
        # direct copy. Duplicate notification is explicitly harmless under the protocol.
        for ep, label in (("https://api.indexnow.org/indexnow", "IndexNow (all engines)"),
                          ("https://www.bing.com/indexnow", "IndexNow (Bing direct)")):
            req = urllib.request.Request(ep, data=body, headers=UA, method="POST")
            r = urllib.request.urlopen(req, timeout=25)
            print(f"  {label}: HTTP {r.status} for {len(urls[:MAX_URLS])} URL(s)")
    except urllib.error.HTTPError as e:
        detail = {403: "key file not reachable yet -- it deploys with this commit, so the first "
                       "run after a fresh key can fail; the next run succeeds",
                  422: "URL/host mismatch"}.get(e.code, e.reason)
        print(f"  IndexNow: HTTP {e.code} ({detail})")
    except Exception as e:
        print(f"  IndexNow: {type(e).__name__}: {e}")


def submit_bing_batch(urls, dry):
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
        return
    batch = urls[:80]
    if not batch:
        print("  Bing SubmitUrlBatch: nothing changed; nothing to submit.")
        return
    body = json.dumps({"siteUrl": "https://www.pdufa.bio/", "urlList": batch}).encode()
    if dry:
        print(f"  [dry-run] would SubmitUrlBatch {len(batch)} URL(s) to Bing")
        return
    try:
        req = urllib.request.Request(
            "https://ssl.bing.com/webmaster/api.svc/json/SubmitUrlBatch?apikey=" + key,
            data=body, headers={**UA, "Content-Type": "application/json; charset=utf-8"},
            method="POST")
        r = urllib.request.urlopen(req, timeout=45)
        print(f"  Bing SubmitUrlBatch: HTTP {r.status} for {len(batch)} URL(s) "
              f"(quota-backed, console-attributed)")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:160]
        print(f"  Bing SubmitUrlBatch: HTTP {e.code} -- {detail}")
    except Exception as e:
        print(f"  Bing SubmitUrlBatch: {type(e).__name__}: {e}")


def submit_gsc(dry):
    """Google Search Console sitemaps.submit. Needs a service-account JSON in the
    GSC_SERVICE_ACCOUNT_JSON env var, and that account added as an owner of the property."""
    raw = os.environ.get("GSC_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        print("  Google Search Console: NOT CONFIGURED. This is the only real channel to Google; "
              "the old ping URL is gone. To enable: create a service account, add it as a user on "
              "the pdufa.bio GSC property, and put its JSON in the GSC_SERVICE_ACCOUNT_JSON secret.")
        return
    try:
        from google.oauth2 import service_account          # noqa
        from googleapiclient.discovery import build        # noqa
    except Exception:
        print("  Google Search Console: credential present but google-api-python-client is not "
              "installed in this environment; add it to the workflow's pip install step.")
        return
    if dry:
        print("  [dry-run] would call searchconsole sitemaps.submit"); return
    try:
        creds = service_account.Credentials.from_service_account_info(
            json.loads(raw), scopes=["https://www.googleapis.com/auth/webmasters"])
        svc = build("searchconsole", "v1", credentials=creds, cache_discovery=False)

        # A property is either URL-prefix ("https://www.pdufa.bio/") or Domain
        # ("sc-domain:pdufa.bio"), and sitemaps.submit needs the exact form. Rather than make the
        # owner work out which they have, ask Google which properties this account can see and use
        # those. If it can see none, the service account was not added to the property, which is
        # the step people miss.
        try:
            visible = [s["siteUrl"] for s in (svc.sites().list().execute().get("siteEntry") or [])]
        except Exception:
            visible = []
        wanted = [s for s in visible if HOST in s or s == f"sc-domain:{HOST.replace('www.', '')}"]
        if not wanted:
            print(f"  Google Search Console: the service account can see {len(visible)} propert(ies)"
                  f"{' (' + ', '.join(visible[:4]) + ')' if visible else ''}, none of them pdufa.bio. "
                  f"Add its client_email as an OWNER on the property in Search Console "
                  f"(Settings -> Users and permissions). That is the step that is usually missed.")
            return
        feed = f"https://{HOST}/sitemap.xml"
        for site in wanted:
            try:
                svc.sitemaps().submit(siteUrl=site, feedpath=feed).execute()
                # Read the state back. lastSubmitted and lastDownloaded are different things and
                # confusing them wastes an afternoon: submit is us telling Google the file changed
                # (updates immediately, always), lastDownloaded is Google choosing to fetch it
                # (their schedule, not ours). Search Console's "Last read" column shows the second
                # one, so a successful submit legitimately leaves "Last read" weeks in the past.
                # Logging both means this step can be judged from its own output.
                try:
                    d = svc.sitemaps().get(siteUrl=site, feedpath=feed).execute()
                    print(f"  Google Search Console: accepted for {site}\n"
                          f"      lastSubmitted (us)     {d.get('lastSubmitted')}\n"
                          f"      lastDownloaded (Google){d.get('lastDownloaded')}   "
                          f"warnings={d.get('warnings')} errors={d.get('errors')}")
                except Exception:
                    print(f"  Google Search Console: sitemap resubmitted for {site}")
            except Exception as e:
                msg = str(e)
                print(f"  Google Search Console: {site} failed -> {type(e).__name__}: {msg[:180]}")
                if "403" in msg:
                    print("      403 means the service account is not an Owner on this property. "
                          "sitemaps.submit is not available to a 'Full' user.")
    except Exception as e:
        print(f"  Google Search Console: {type(e).__name__}: {e}")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    urls, newest = changed_urls()
    # RULE 1, the timezone trap. The sitemap's lastmod values are stamped in UTC by
    # build_sitemap/build_date_modified, so the "is this in the future" test has to be made in
    # UTC too. Comparing a UTC date against this machine's LOCAL date (Pacific) made the check
    # cry wolf every evening after 5pm PT, when UTC has already rolled over: on 2026-08-22 at
    # 21:23 PT it warned that a lastmod of 2026-08-23 was "tomorrow" when it was simply today in
    # the zone that wrote it. CI never saw it (12:00 and 21:00 UTC land at 05:00 and 14:00 PT,
    # same calendar day), which is exactly how a warning like this survives unnoticed.
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    print(f"sitemap newest lastmod {newest} (today {today}); {len(urls)} URL(s) changed recently")
    if newest and newest > today:
        print(f"  WARNING: lastmod {newest} is in the future. A sitemap that claims tomorrow's date "
              f"is a reason for a crawler to distrust all of them.")

    key = indexnow_key()
    kf = os.path.join(SITE, f"{key}.txt")
    if not os.path.exists(kf) and not a.dry_run:
        open(kf, "w", encoding="utf-8").write(key)
        print(f"  wrote IndexNow key file -> /{key}.txt (deploys with this commit)")

    if urls:
        post_indexnow(key, urls, a.dry_run)
        submit_bing_batch(urls, a.dry_run)
    else:
        print("  nothing changed recently; no submission")
    submit_gsc(a.dry_run)


if __name__ == "__main__":
    main()
