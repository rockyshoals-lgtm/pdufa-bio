# Builder note — item 1.1 "Bing API migration" is a false positive. Please close it.

**2026-08-12 · from the builder · third and hopefully final statement of this**

The verification command the audits use is:

```bash
grep -c "api.svc/json" bing_rank_report.py    # audits expect 0 after "migration"
```

That test is checking for the wrong string. Per Microsoft's own protocol documentation:

- **What retires August 31, 2026:** the SOAP protocol (`api.svc/soap`) and the POX protocol.
- **What survives and is the designated migration TARGET:** the JSON/HTTP protocol, whose
  documented endpoint format is `https://ssl.bing.com/webmaster/api.svc/json/METHOD_NAME` —
  the exact base `bing_rank_report.py` has used since it was written. Microsoft's guidance
  for SOAP/POX users is to migrate TO this endpoint, with the same API key, quotas, rate
  limits and permissions.

Sources:
- Microsoft Learn, "Bing Webmaster Tools API Services":
  https://learn.microsoft.com/en-us/bingwebmaster/api-protocols
  (lists JSON as a supported protocol with the api.svc/json URL format)
- Search Engine Roundtable coverage of the retirement notice:
  https://www.seroundtable.com/bing-webmaster-tools-soap-pox-apis-retire-41805.html
  ("If you use these legacy APIs you should begin to migrate to the JSON/HTTP API version")

So `grep -c "api.svc/json"` returning 2 is evidence of **compliance**, not exposure. A
migrated-from-SOAP codebase would grep exactly the same.

**Requested audit change:** replace the verification with one that tests the actual risk:

```bash
grep -c "api.svc/soap\|api.svc/pox" bing_rank_report.py    # exposure = anything > 0; currently 0
```

If Aug 31 passes and the JSON endpoint breaks anyway, the daily rank snapshot step will fail
loudly in CI the same day and we will know within hours -- that is the correct canary, and it
already exists.

*This note self-destructs from relevance on September 1, 2026, when the empirical answer arrives
either way.*
