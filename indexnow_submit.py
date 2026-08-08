# -*- coding: utf-8 -*-
"""DEPRECATED -- DO NOT USE. Superseded by ping_search_engines.py.

Written 2026-08-07 before discovering the builder had already implemented IndexNow
properly. The canonical implementation is:

    ping_search_engines.py          <- IndexNow + Search Console sitemaps.submit
    _indexnow_key.txt               <- persisted key (8e7f6a62cb9997fcfb9f23b1c154c589)
    .github/workflows/pdufa-rebuild.yml  -> step "Ping search engines (IndexNow + Search Console)"

That implementation is better than this one: it persists a stable key, writes the key
file into the site directory so it deploys with the commit, handles the expected
first-run 403 (key file not yet live), and also calls the Google Search Console API.

This file is inert. It exists only because the sandbox could not delete it.
A stray unused key file was also created at
pdufa_site_src/6ef4cc566664898aa2939aaee0d174c1.txt -- it is NOT referenced by anything
and is NOT in the workflow's `git add` list, so it will never deploy. Safe to delete both.
"""
import sys

print(__doc__, file=sys.stderr)
print("Use:  python ping_search_engines.py", file=sys.stderr)
sys.exit(2)
