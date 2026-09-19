"""Wrap CP.extract to count what the REAL newswire_events() actually asks it."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import conference_presentations as CP
import conference_miner as CM

calls = {"n": 0, "hits": 0, "sample": []}
_real = CP.extract


def spy(text, filed_dt=None, registry=None):
    calls["n"] += 1
    r = _real(text, filed_dt=filed_dt, registry=registry)
    if r:
        calls["hits"] += 1
        if len(calls["sample"]) < 5:
            calls["sample"].append((r["conference"], text[:70]))
    elif calls["n"] <= 3:
        calls["sample"].append(("MISS", f"reg={type(registry).__name__}:"
                                        f"{len(registry) if registry else 0} | {text[:60]}"))
    return r


CP.extract = spy
CM.CP.extract = spy                      # the module holds its own reference
rows = CM.newswire_events(CP.load_registry(), days=75)
print(f"extract called {calls['n']} times, {calls['hits']} hits, returned {len(rows)} rows")
for a, b in calls["sample"]:
    print(f"   [{a}] {b}")
