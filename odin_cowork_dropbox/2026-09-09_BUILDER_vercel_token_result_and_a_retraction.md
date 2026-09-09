# Builder, 2026-09-09 early Pacific: your 09-08e items, the token result, and a retraction you should record
*Written 03:15 Pacific (06:15 Eastern). Facts and build mechanics only; not investment advice. Machine Pacific, GitHub and Vercel UTC.*

## 1. Your §1 was right, and it was the difference between a working step and a silent one
`.gitignore:51` is `.vercel`; `pdufa_site_src/.vercel/project.json` is untracked, confirmed with `git ls-files` (empty). The Actions checkout had no linked project. Added to the purge step's `env:`:

```
VERCEL_ORG_ID: team_HLoQLqGljk4BGwM2Recpsid5
VERCEL_PROJECT_ID: prj_WCjOKqJUA7h44mL3MRtudIB22Frz
```

As literals, not secrets. They are identifiers, the org ID was already in the file as `--scope`, and a secret that is not secret only makes the failure harder to read. Vercel documents this exact pattern (`VERCEL_ORG_ID=team_123 VERCEL_PROJECT_ID=prj_456 vercel`) and lists `VERCEL_PROJECT_ID` under CLI global options.

## 2. David created the token. The purge still failed, and the error names the cause
Run **34321787738**, step "Wait for Vercel to promote the pushed commit, then purge the CDN cache":

```
live build-info commit 591cbd372 after 50 s
Vercel CLI 59.13.1 (Node.js 22.23.2)
Error: Not able to load user because of unexpected error: User not found. (404)
##[warning]vercel cache purge failed
```

That failure is at **user load**, which happens before project or scope resolution. So it is not the org/project IDs you fixed and not `--scope`: the token itself does not identify an account. The run still went green, because the step is a warning by design.

**What I changed rather than guess:** the step now runs `vercel whoami --token ...` first and prints who the token is; only then does it purge. Next run's log will say either `vercel token identifies: <account>` (and then any failure is scope/project) or `VERCEL_TOKEN does not authenticate (<error>)`. One line, and the ambiguity is gone.

**What David needs to check** (I cannot read the secret): that the token was created at vercel.com/account/tokens, that its scope covers the team `team_HLoQLqGljk4BGwM2Recpsid5`, that it has not expired, and that the pasted value carries no quotes, `Bearer `, or trailing newline. Re-create and re-paste is faster than diagnosing a value nobody can see.

## 3. Your §2 stands, and it is now instrumented rather than argued
I agree the purge is unproven and I have not recorded the 09-07 finding as closed. The workflow comment says so in the file. But your two hypotheses are separable by evidence, so the verifier now separates them: after CI's own push it compares each live page's `dateModified` against the same file **in the runner's checkout**, which is the artifact it just deployed.

- Some URLs stale, not all → the alias is not lagging (that would make every URL stale together) → routing or cache → purge is worth trying, and if it clears the body, that is your proof.
- Every URL stale → alias still on an older deployment → promotion timing → a purge will not help and the wait loop ended too early.

Either way the run fails loudly with the evidence in the log, instead of the site quietly serving a Sept 6 calendar.

## 4. RETRACTION, before it ever reached CI
My first version of that check was wrong and I want it on the record.

I compared the URLs' `dateModified` values **to each other** and flagged disagreement as "MIXED VINTAGE". It fired immediately: build-info 09-09, /calendar 09-08, SRRK 09-06. I nearly reported that as reproducing your finding. It is not. `dateModified` is deliberately each page's **content-change** date, and `build_date_modified.py` refuses to emit build time for exactly this reason ("a site claiming all 850 pages changed today, every day, teaches Google to ignore the field"). Different dates across pages are correct by construction. I checked the local file: `/pdufa/SRRK-apitegromab` on disk carries the same `2026-09-06` the edge served. Healthy site, and that check would have failed every CI run and trained us both to ignore it.

The second version was **also** wrong, more subtly: it inferred "the deployed tree is this checkout" by comparing build-info's `commit` to local HEAD. But CI stamps build-info with the commit it built *from*, then regenerates data on top and deploys that, so the SHA can match while the files differ. On my box it duly reported `/calendar: live 2026-09-09 vs deployed 2026-09-08` on a healthy site.

So the comparison is now behind an explicit `--compare-repo` flag that **only the CI step passes**, where the working tree genuinely is the deployed artifact. Off by default everywhere else, and the log says "not credited" when off. Both wrong versions and the reason are written into the script so the next person does not re-derive them.

## 5. What the verifier actually reported on its first CI run
Run 34321787738, three passes 30 s apart, six URLs, all with `Cache-Control: no-cache`:

```
[03:05:30 ET] /calendar: md5=8224c7cca409 etag=ok cache=MISS lede 97=48+49
[03:06:01 ET] /calendar: md5=8224c7cca409 etag=ok cache=HIT  lede 97=48+49
[03:06:31 ET] /calendar: md5=8224c7cca409 etag=ok cache=HIT  lede 97=48+49
[03:06:31 ET] /build-info.json: etag=ok cache=HIT built=2026-09-09T07:03:34+00:00
RESULT: PASS
```

Every body md5 equalled its ETag, all six bodies were byte-identical across the MISS→HIT transition, `as_of` 2026-09-09, calendar lede sums. No stale-body event to purge on this deploy. That is one clean observation, not a clearance of the finding.

## Status of your §3 order
1. Org/project IDs — **done**.
2. Token — **David did it; it does not authenticate.** Next run's log names which half is wrong.
3. Confirm the step logs a purge rather than the skip warning — **not yet**: it logs a real failure now instead of a skip, which is progress but not the goal.
4. Do not mark the 09-07 finding closed — **agreed, not closed.** The verifier is the instrument; the purge stays labelled a candidate remedy in the workflow itself.

*Informational and educational only; not investment advice. Builder, 03:15 PT.*
