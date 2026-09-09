# Vercel token setup, plus two things that change the plan
**2026-09-08 evening Pacific. Checked against Vercel's own docs (`/docs/cli/cache` and `/docs/caching/cdn-cache/purge`, both last updated 2026-09-03) and against the repo.**
*Facts and build mechanics only. Not investment advice.*

---

# 1. The token alone will not make the step work

`.gitignore` line 51 is `.vercel`. So `pdufa_site_src/.vercel/project.json` exists on David's machine and **is not in the repo**. In GitHub Actions the checkout has no `.vercel` directory, so `vercel cache purge` run from `pdufa_site_src` has no project to act on. It will fail to resolve the project even with a valid token.

The standard CI fix is to pass the two identifiers as environment variables, which is what Vercel's own CI guidance does. They are identifiers, not credentials, and they are already in the workflow in one case: the step passes `--scope team_HLoQLqGljk4BGwM2Recpsid5`, which is the org ID.

**Builder action:** add to the purge step's `env:` block

```yaml
VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}
```

Both values are in `pdufa_site_src/.vercel/project.json`. They can be repo secrets or plain `env:` values; they are not sensitive. Without them the step fails after David does the work of creating a token, which is the wrong order to discover it.

---

# 2. The purge may not be the fix for what we actually saw

From Vercel's purge documentation, verbatim:

> "Each request to Vercel's CDN has a cache key derived from the following: the request method, the request URL, the host domain, **the unique deployment URL**, the scheme."
>
> "**Since each deployment has a different cache key, you can promote a new deployment to production without affecting the cache of the previous deployment.**"

If each deployment carries its own cache key, then a fresh promotion cannot serve a previous deployment's body **through the cache key**. That is the opposite of what we observed twice: on 09-07 an edge node handed out bodies from two superseded deployments under the newest deployment's ETag, and on 09-08 at 11:24 PT a cache-busted `/calendar` returned a Sept 6 body two hours after a Sept 8 deploy.

So one of these is true, and I cannot tell which from here:

1. **The alias was still pointing at the older deployment** at the moment of those fetches, meaning the "deployment URL" component of the cache key was legitimately the old one and the site simply had not finished promoting. That would make this a promotion-timing question, not a caching question, and a purge would not address it.
2. **Something in the routing layer** is resolving the production alias inconsistently across edge nodes, in which case a purge might clear it but would be treating a symptom.

**What this does not change:** the purge is cheap, harmless, and worth having wired. **What it does change:** we should not record "CDN purge shipped" as closing the stale-body finding until a verifier run catches a mismatch and a purge demonstrably clears it. The verifier the builder already wrote is the instrument that settles this; the purge is a candidate remedy, not a proven one.

**Cheaper test before any token exists:** the Vercel dashboard can purge without a token (Project, then CDN in the sidebar, then Caches, then Purge, entering `*` for the whole project). Next time the verifier or an audit catches a stale body, purge by hand and re-fetch. If the stale body clears, the automation is worth it. If it does not, the diagnosis is promotion timing and the automation would have been noise.

---

# 3. Recommended order

1. Builder adds `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` to the purge step.
2. David creates the token and adds it as `VERCEL_TOKEN` (steps in the chat message accompanying this note).
3. First CI run after that: confirm the step logs a purge rather than the skip warning.
4. Do not mark the 09-07 CDN finding closed until a purge is observed to clear a real stale body.

---
*Vercel docs read 2026-09-08. Repo state: `.gitignore:51` is `.vercel`; `pdufa_site_src/.vercel/project.json` is present locally and untracked. Not investment advice.*
