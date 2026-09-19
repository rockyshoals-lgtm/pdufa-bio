# -*- coding: utf-8 -*-
import json, os, re, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
H = {"User-Agent": "pdufa-verify/1.0", "Cache-Control": "no-cache"}


def get(p):
    return urllib.request.urlopen(urllib.request.Request("https://www.pdufa.bio" + p, headers=H),
                                  timeout=90).read().decode("utf-8", "replace")


# which /learn page carries the timing numbers locally?
learn = [d for d in os.listdir("pdufa_site_src/learn") if "early" in d or "decide" in d]
print("learn candidates:", learn)
paths = ["/research/fda-decision-timing"] + [f"/learn/{d}" for d in learn]
for p in paths:
    try:
        t = get(p)
    except Exception as e:
        print(f"{p}: {e}")
        continue
    nums = re.findall(r"\b(\d+)\s+(?:FDA decisions?|of them came|came before|landed on it|came after)", t)
    m = re.search(r"[^.]{0,120}came before the goal date[^.]{0,90}\.", t)
    print(f"\n{p}")
    print("   ", (m.group(0).strip()[:210] if m else "timing sentence not found"))
    print("    mentions 30/9:", bool(re.search(r"\b30 FDA decisions|9 landed on it", t)),
          "| mentions 28/7:", bool(re.search(r"\b28 FDA decisions|7 landed on it", t)))

t = get("/decisions/approvals")
dead = [h for h in ("/fda-decision/AZN-2026-06-30", "/fda-decision/GSK-2026-06-18",
                    "/fda-decision/SPRO-2026-06-18", "/fda-decision/VRDN-2026-06-29",
                    "/fda-decision/VRDN-2026-06-30") if f'href="{h}"' in t]
print("\n/decisions/approvals still links the 5 dead targets:", dead or "none")

nav = get("/")
print('/ nav links /pricing:', 'href="/pricing"' in nav,
      '| links /developers#tiers:', 'href="/developers#tiers"' in nav)
print("\nbuild-info:", json.loads(get("/build-info.json")))
