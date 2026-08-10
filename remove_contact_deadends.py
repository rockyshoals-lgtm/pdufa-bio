# -*- coding: utf-8 -*-
"""remove_contact_deadends.py -- TEMPORARY sweep: strip every contact invitation.

Owner decision 2026-08-10: no mailbox or sender exists, so every mailto:, address and email form
on the site was a dead end. This applies the removals idempotently; test_no_contact_deadends.py
enforces the result. Both are temporary and get deleted together when communication launches.

Scripted (rather than one-off edits) because daily-refresh rebases kept forcing reapplication.

    python remove_contact_deadends.py
"""
import os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")


def edit(rel, fn):
    p = os.path.join(SITE, rel)
    if not os.path.exists(p):
        print(f"  skip {rel}: missing"); return
    d = open(p, encoding="utf-8", errors="replace").read()
    d2 = fn(d)
    if d2 != d:
        open(p, "w", encoding="utf-8").write(d2)
        print(f"  cleaned {rel}")


def main():
    edit("about/index.html", lambda d: re.sub(
        r'<p><b>Contact:</b> <a href="mailto:[^"]+"[^>]*>[^<]*</a>[^<]*</p>', "", d.replace(
            '"email":"data@pdufa.bio",', "")))

    edit("corrections/index.html", lambda d: re.sub(
        r"\s*If you find an error, email <a[^>]*mailto:[^>]*>[^<]*</a>\.\s*", " ", d))

    def login(d):
        d = re.sub(r"\s*Trouble signing in\? Email <a[^>]*mailto:[^>]*>[^<]*</a>\.?", "", d)
        d = re.sub(r"\s*Enter the email you subscribed with\.[^<]*leak\.", "", d)
        m = re.search(r"<form.*?</form>", d, re.S)
        if m and 'type="email"' in m.group(0):
            d = d[:m.start()] + (
                '<!--LOGIN-PARKED: form removed 2026-08-10 until email delivery exists; restore '
                'from git when communication is set up--><div style="background:#081426;border:'
                '1px solid #294d80;border-radius:10px;padding:14px;color:#9db3d4;font-size:14px;'
                'line-height:1.6">Sign-in is temporarily unavailable while we finish setting up '
                'email delivery. If you already have an API key from checkout, it continues to '
                'work unchanged.</div>') + d[m.end():]
        return d
    edit("login/index.html", login)

    def success(d):
        d = re.sub(r"Lose it and you.{0,10}ll need a new one:\s*email <a[^>]*mailto:[^>]*>"
                   r"[^<]*</a>\.?", "Keep it safe; it is shown only once.", d, flags=re.S)
        d = d.replace("If you just paid, check your email for the receipt and contact "
                      "support@pdufa.bio.",
                      "If you just paid, keep your receipt; retry from the link in it.")
        d = d.replace("Email support@pdufa.bio with your receipt.",
                      "Keep your receipt and retry shortly.")
        return d
    edit("pricing/success/index.html", success)

    for rel in ("research/conference-runup/index.html",
                "research/pdufa-stock-run-up-by-market-cap/index.html",
                "research/readout-reaction/index.html",
                "research/short-interest-fda/index.html"):
        edit(rel, lambda d: re.sub(
            r"\s*Journalists\s*&(?:amp;)?\s*researchers:\s*(?:email\s*)?<a[^>]*mailto:[^>]*>"
            r"[^<]*</a>[^<.]*\.?", "", d))

    left = 0
    import glob
    for p in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
        if re.search(r'mailto:|[A-Za-z0-9._%+-]+@pdufa\.bio|type="email"',
                     open(p, encoding="utf-8", errors="replace").read()):
            left += 1
            print(f"  STILL DIRTY: {p}")
    print(f"residual contact points: {left}")
    return 1 if left else 0


if __name__ == "__main__":
    sys.exit(main())
