# -*- coding: utf-8 -*-
"""diagnose_gsc.py -- find out exactly why Search Console is not accepting our sitemap submission.

"Last read" stuck on a date weeks in the past means sitemaps.submit is not landing. There are four
distinct causes and they are indistinguishable from the Search Console UI, so this asks the API
directly and reports which one it is:

  1. the credential does not authenticate at all (wrong/rotated key, API not enabled)
  2. it authenticates but can see no properties  -> not added as a user in Search Console
  3. it can see properties but not pdufa.bio     -> added to the wrong property
  4. it can see pdufa.bio but submit fails 403   -> added as "Full", not "Owner"

Cause 4 is the common one: sitemaps.submit requires Owner. "Full" looks correct in the UI and
silently cannot submit.

Prints the client_email (which you need in order to grant access) and never the private key.

    python diagnose_gsc.py path\\to\\service-account.json
"""
import json, sys

HOST = "www.pdufa.bio"
SITEMAP = f"https://{HOST}/sitemap.xml"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main():
    if len(sys.argv) < 2:
        print("usage: python diagnose_gsc.py <service-account.json>")
        sys.exit(2)

    info = json.load(open(sys.argv[1], encoding="utf-8"))
    print(f"service account : {info.get('client_email')}")
    print(f"project         : {info.get('project_id')}")
    print(f"key id          : ...{str(info.get('private_key_id'))[-6:]}  (key itself not printed)")
    print()

    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    try:
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/webmasters"])
        svc = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
    except Exception as e:
        print(f"CAUSE 1: the credential does not authenticate -> {type(e).__name__}: {e}")
        sys.exit(1)

    try:
        entries = svc.sites().list().execute().get("siteEntry") or []
    except Exception as e:
        print(f"CAUSE 1: authenticated but sites.list failed -> {type(e).__name__}: {e}")
        print("   Usually means the Search Console API is not enabled on the project.")
        sys.exit(1)

    print(f"properties visible to this account: {len(entries)}")
    for s in entries:
        print(f"   {s.get('siteUrl'):<40} permission={s.get('permissionLevel')}")
    print()

    if not entries:
        print("CAUSE 2: the account authenticates but Search Console has never heard of it.")
        print("   Add the client_email above under Settings -> Users and permissions, as Owner.")
        sys.exit(1)

    mine = [s for s in entries
            if HOST in s.get("siteUrl", "")
            or s.get("siteUrl") == f"sc-domain:{HOST.replace('www.', '')}"]
    if not mine:
        print("CAUSE 3: it can see properties, but none of them is pdufa.bio.")
        print("   It was added to the wrong property. Add it to the pdufa.bio one.")
        sys.exit(1)

    ok = False
    for s in mine:
        url, perm = s["siteUrl"], s.get("permissionLevel")
        print(f"attempting sitemaps.submit on {url}  (permission={perm})")
        try:
            svc.sitemaps().submit(siteUrl=url, feedpath=SITEMAP).execute()
            print("   SUCCESS: submission accepted.")
            ok = True
            try:
                d = svc.sitemaps().get(siteUrl=url, feedpath=SITEMAP).execute()
                print(f"   lastSubmitted={d.get('lastSubmitted')}  "
                      f"lastDownloaded={d.get('lastDownloaded')}  "
                      f"warnings={d.get('warnings')}  errors={d.get('errors')}")
            except Exception as e:
                print(f"   (could not read back status: {type(e).__name__}: {e})")
        except Exception as e:
            msg = str(e)
            print(f"   FAILED: {type(e).__name__}: {msg[:200]}")
            if "403" in msg:
                print("   CAUSE 4: permission is not Owner. sitemaps.submit requires Owner; "
                      "'Full' cannot submit. Change it in Settings -> Users and permissions.")
            elif "404" in msg:
                print("   The property exists but this feedpath is not registered on it. "
                      "Add the sitemap once by hand under Sitemaps, then this will work.")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
