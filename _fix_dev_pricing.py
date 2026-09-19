# -*- coding: utf-8 -*-
"""/developers links /pricing twice in its body; no pricing page has ever existed. The tier
comparison it promises is on this same page under "Tiers", so both links point there. The prices
already stated in the copy are left exactly as they are -- that is a commercial decision, not
mine to invent or to remove."""
import io, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "pdufa_site_src/developers/index.html"
t = io.open(p, encoding="utf-8", errors="replace").read()
before = t.count('href="/pricing')
t = t.replace('href="/pricing/credits"', 'href="/developers#tiers"')
t = t.replace('href="/pricing?ref=developers"', 'href="/developers#tiers"')
t = t.replace('href="/pricing"', 'href="/developers#tiers"')
io.open(p, "w", encoding="utf-8").write(t)
print(f"{before} /pricing link(s) on /developers repointed to #tiers; {t.count('href=\"/pricing')} left")
