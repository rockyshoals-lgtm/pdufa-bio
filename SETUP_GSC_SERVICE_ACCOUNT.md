# Connecting Google Search Console to the daily deploy

**Why:** the old `google.com/ping?sitemap=` URL is gone (it returns `404 Sitemaps ping is
deprecated`). The Search Console API is the only remaining way to tell Google the sitemap changed.
Right now Google reads our sitemap roughly weekly on its own schedule, which is why the red team
found it was six days stale and every improvement in between was invisible.

**Time:** about 10 minutes. **Cost:** free. You need to be an *Owner* of the pdufa.bio property in
Search Console (not just "Full user") to do step 4.

---

## 1. Create a Google Cloud project

1. Go to <https://console.cloud.google.com/projectcreate>
2. Project name: `pdufa-bio-seo` (anything is fine)
3. Create, then make sure it is the selected project in the top bar.

## 2. Turn on the Search Console API

1. Go to <https://console.cloud.google.com/apis/library/searchconsole.googleapis.com>
2. Check the project selector at the top still says `pdufa-bio-seo`
3. Click **Enable**

## 3. Create the service account and download its key

1. Go to <https://console.cloud.google.com/iam-admin/serviceaccounts>
2. **Create service account**
   - Name: `pdufa-sitemap-bot`
   - Click **Create and continue**
   - Skip the "grant this service account access to the project" step (it needs no project roles,
     only Search Console permission, which you grant in step 4). Click **Done**.
3. In the list, click the new account, open the **Keys** tab
4. **Add key -> Create new key -> JSON -> Create**. A `.json` file downloads. This is a credential:
   treat it like a password, and do not commit it to the repo.
5. Open that file and copy **the whole contents**, including the outer `{ }`. Also note the
   `client_email` value, which looks like
   `pdufa-sitemap-bot@pdufa-bio-seo.iam.gserviceaccount.com` — you need it next.

## 4. Give the service account access to the property

This is the step people miss: the account exists in Google Cloud but Search Console does not know
about it yet.

1. Go to <https://search.google.com/search-console> and select the **pdufa.bio** property
2. **Settings** (left sidebar, at the bottom) -> **Users and permissions**
3. **Add user**
   - Email address: the `client_email` from step 3.5
   - Permission: **Owner**
   - (Owner is required. `sitemaps.submit` is not available to a "Full" user.)
4. Add.

> If the property is a **Domain** property (`pdufa.bio`) rather than a **URL-prefix** property
> (`https://www.pdufa.bio/`), the API call in step 6 needs `siteUrl` to be `sc-domain:pdufa.bio`
> instead. Check which one you have at the top of Search Console; tell me and I will change the one
> line in `ping_search_engines.py`.

## 5. Put the key in the repo secrets

1. <https://github.com/rockyshoals-lgtm/pdufa-bio/settings/secrets/actions>
2. **New repository secret**
   - Name: `GSC_SERVICE_ACCOUNT_JSON`
   - Value: paste the entire JSON from step 3.5
3. Add secret.

## 6. Let the workflow use it

Add the Google client library to the workflow's install line. In
`.github/workflows/pdufa-rebuild.yml`, the `Install deps` step becomes:

```yaml
      - name: Install deps
        run: pip install --quiet requests pandas openpyxl python-dateutil \
             google-api-python-client google-auth
```

Tell me when the secret exists and I will make that edit and confirm it end to end.

---

## Checking it worked

Run the ping manually, or watch the last step of the next scheduled run. Success looks like:

```
  Google Search Console: sitemap resubmitted
```

Failure modes and what they mean:

| Message | Cause |
|---|---|
| `NOT CONFIGURED` | the `GSC_SERVICE_ACCOUNT_JSON` secret is missing or empty |
| `google-api-python-client is not installed` | step 6 not done |
| `HttpError 403` | the service account was not added as an **Owner** in step 4, or was added to a different property |
| `HttpError 404` | `siteUrl` does not match the property type; see the note in step 4 |

Then confirm in Search Console under **Sitemaps**: the "Last read" date for `sitemap.xml` should
start tracking the deploy date instead of drifting a week behind.

---

## What this does and does not fix

**Does:** stops the sitemap going stale between Google's own crawls, so newly published decisions
and readouts become discoverable the day they ship rather than up to a week later.

**Does not:** force indexing. Google decides what to index. The backlog's own diagnosis is that the
problem is crawl *demand*, not discovery — 478 URLs are "Discovered, currently not indexed", which
means Google already knows about them and has chosen not to crawl. Faster sitemap reads help the
newest pages; the demand problem is answered by internal linking, page depth and authority, which
is the B2/B3/B4 work still open in the backlog.

**Already working without any setup:** IndexNow, which pushes to Bing, Yandex, Seznam and Naver.
Verified live: `HTTP 200 for 430 URL(s)`. Google does not participate in IndexNow.
