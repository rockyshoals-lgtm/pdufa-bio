# -*- coding: utf-8 -*-
"""apply_1010_two_pending_rows.py -- audit 2026-10-10 item 2: one event page per pending application.

Giredestrant has two pending NDAs (lidERA, goal 2026-11-30; evERA with everolimus, goal 2026-12-18) and
bezuclastinib two (PEAK/GIST 2026-11-30; SUMMIT/NonAdvSM 2026-12-30). Each drug had one slug, so the
later row resolved to the earlier row's page. The Dec 18 giredestrant page did exist, under a slug cut
mid-word (/pdufa/RHHBY-giredestrant-in-combinatio, title ending in an ellipsis) that nothing linked.

  * both later rows get a hand-assigned _d.event_slug and _d.trial;
  * the cut-slug page is moved to /pdufa/RHHBY-giredestrant-evera with a title that names the drug, the
    trial and the date; vercel.json gains a 301 from the old slug;
  * build_pdufa_event_pages.py (patched) writes /pdufa/COGT-bezuclastinib-summit;
  * enrich_event_pages.py names each sibling on both pages.
Facts only; not investment advice.
"""
import io, json, os, re, shutil, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
P = os.path.join(SITE, "api", "v1", "dataset.mjs")
VJ = os.path.join(SITE, "vercel.json")
s = io.open(P, encoding="utf-8", errors="replace").read().replace("\x00", "")
i, j = s.index("["), s.rindex("]") + 1
rows = json.loads(s[i:j])
by = {r["id"]: r for r in rows}
r = by["pdufa_rhhby_2026-12-18"]
r["_d"].update({"event_slug": "RHHBY-giredestrant-evera", "trial": "evERA"})
r = by["pdufa_cogt_2026-12-30"]
r["_d"].update({"event_slug": "COGT-bezuclastinib-summit", "trial": "SUMMIT"})
by["pdufa_rhhby_2026-11-30"]["_d"].setdefault("trial", "lidERA")
by["pdufa_cogt_2026-11-30"]["_d"].setdefault("trial", "PEAK")
io.open(P, "w", encoding="utf-8").write(s[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + s[j:])
print("  event_slug set: RHHBY-giredestrant-evera, COGT-bezuclastinib-summit")

old = os.path.join(SITE, "pdufa", "RHHBY-giredestrant-in-combinatio")
new = os.path.join(SITE, "pdufa", "RHHBY-giredestrant-evera")
if os.path.isdir(old) and not os.path.isdir(new):
    shutil.move(old, new)
    print("  moved /pdufa/RHHBY-giredestrant-in-combinatio -> /pdufa/RHHBY-giredestrant-evera")
pp = os.path.join(new, "index.html")
if os.path.exists(pp):
    doc = io.open(pp, encoding="utf-8").read()
    title = "RHHBY PDUFA date: Giredestrant (evERA, with everolimus), Dec 18, 2026 | pdufa.bio"
    desc = ("Roche's giredestrant NDA with everolimus (evERA) for ER-positive, HER2-negative, ESR1-mutated advanced "
            "breast cancer has an FDA goal date of December 18, 2026, per Genentech's February 19, 2026 release.")
    doc = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", doc, count=1, flags=re.S)
    doc = doc.replace("/pdufa/RHHBY-giredestrant-in-combinatio", "/pdufa/RHHBY-giredestrant-evera")
    for pat in (r'(<meta property="og:title" content=")[^"]*(")', r'(<meta name="twitter:title" content=")[^"]*(")'):
        doc = re.sub(pat, lambda m: m.group(1) + title + m.group(2), doc, count=1)
    for pat in (r'(<meta name="description" content=")[^"]*(")', r'(<meta property="og:description" content=")[^"]*(")',
                r'(<meta name="twitter:description" content=")[^"]*(")'):
        doc = re.sub(pat, lambda m: m.group(1) + desc + m.group(2), doc, count=1)
    doc = doc.replace('<h1>RHHBY PDUFA Date: <span class="g">Giredestrant in combination with everolimus</span></h1>',
                      '<h1>RHHBY PDUFA Date: <span class="g">Giredestrant (evERA, with everolimus)</span></h1>', 1)
    io.open(pp, "w", encoding="utf-8", newline="\n").write(doc)
    print(f"  title/canonical/og rewritten on /pdufa/RHHBY-giredestrant-evera ({len(desc)} char desc)")
cfg = json.load(io.open(VJ, encoding="utf-8"))
src_ = "/pdufa/RHHBY-giredestrant-in-combinatio"
if not any(x.get("source") == src_ for x in cfg.get("redirects", [])):
    cfg.setdefault("redirects", []).insert(0, {"source": src_, "destination": "/pdufa/RHHBY-giredestrant-evera", "permanent": True})
    io.open(VJ, "w", encoding="utf-8", newline="\n").write(json.dumps(cfg, indent=1) + "\n")
    print("  vercel.json: 301 added for the cut slug")
