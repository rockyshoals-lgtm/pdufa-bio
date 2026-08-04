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
    urls = [u for u, d in entries if d >= cutoff]
    return urls, newest


def post_indexnow(key, urls, dry):
    body = json.dumps({"host": HOST, "key": key,
                       "keyLocation": f"https://{HOST}/{key}.txt",
                       "urlList": urls[:MAX_URLS]}).encode()
    if dry:
        print(f"  [dry-run] would POST {len(urls[:MAX_URLS])} URL(s) to IndexNow")
        return
    try:
        req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                                     headers=UA, method="POST")
        r = urllib.request.urlopen(req, timeout=25)
        print(f"  IndexNow: HTTP {r.status} for {len(urls[:MAX_URLS])} URL(s) "
              f"(Bing, Yandex, Seznam, Naver)")
    except urllib.error.HTTPError as e:
        detail = {403: "key file not reachable yet -- it deploys with this commit, so the first "
                       "run after a fresh key can fail; the next run succeeds",
                  422: "URL/host mismatch"}.get(e.code, e.reason)
        print(f"  IndexNow: HTTP {e.code} ({detail})")
    except Exception as e:
        print(f"  IndexNow: {type(e).__name__}: {e}")


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
        svc.sitemaps().submit(siteUrl=f"https://{HOST}/",
                              feedpath=f"https://{HOST}/sitemap.xml").execute()
        print("  Google Search Console: sitemap resubmitted")
    except Exception as e:
        print(f"  Google Search Console: {type(e).__name__}: {e}")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    urls, newest = changed_urls()
    today = dt.date.today().isoformat()
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
    else:
        print("  nothing changed recently; no submission")
    submit_gsc(a.dry_run)


if __name__ == "__main__":
    main()
