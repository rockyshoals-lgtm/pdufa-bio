# -*- coding: utf-8 -*-
"""test_no_contact_deadends.py -- TEMPORARY: no contact invitations until one actually works.

2026-08-10, owner decision: the site invited contact eight ways (mailto: on /about, /corrections,
/login, /pricing/success and four research pages) and offered a magic-link sign-in form, while no
mailbox and no email sender existed behind any of it. An invitation that goes nowhere is worse
than none: the reader who emails a correction and hears nothing concludes the accountability page
is theater, which costs the exact trust it was built to earn.

All of it was removed in one sweep. This guard keeps the state honest until communication is set
up because the removal is spread across static pages AND one JS error string, and any template
edit or restored backup could quietly reintroduce an address.

DELETE THIS GUARD when email is live and contact points return deliberately. It is a fence around
a temporary state, not a permanent rule.
"""
import glob, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "pdufa_site_src")

BAD = re.compile(r'mailto:|[A-Za-z0-9._%+-]+@pdufa\.bio|type="email"')


def main():
    hits = []
    for p in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
        doc = open(p, encoding="utf-8", errors="replace").read()
        for m in BAD.finditer(doc):
            rel = "/" + os.path.relpath(p, SITE).replace("\\", "/")
            hits.append((rel, m.group(0), doc[max(0, m.start() - 60):m.start() + 60]
                         .replace("\n", " ")))
            break
    if hits:
        print(f"FAIL: {len(hits)} page(s) reintroduce a contact point while none works.")
        for rel, what, ctx in hits[:8]:
            print(f"   {rel}: {what!r}  ...{ctx.strip()[:90]}...")
        print("\n   Communication is not set up yet (owner, 2026-08-10). Remove the contact")
        print("   point, or -- if email is now live -- delete this guard deliberately.")
        return 1
    print("  PASS: no mailto:, no @pdufa.bio address, no email input anywhere on the site")
    return 0


if __name__ == "__main__":
    sys.exit(main())
