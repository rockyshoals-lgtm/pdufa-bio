# -*- coding: utf-8 -*-
import importlib.util, statistics, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.argv = ["build_early_decisions.py"]
s = importlib.util.spec_from_file_location("b", "build_early_decisions.py")
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)
g = m.collect(2026)
e = sum(1 for x in g if x["delta"] < 0)
o = sum(1 for x in g if x["delta"] == 0)
la = sum(1 for x in g if x["delta"] > 0)
print(f"NEW statistic: n={len(g)}  early={e}  on-the-day={o}  late={la}")
print("median delta:", statistics.median([x["delta"] for x in g]))
print("on-the-day rows now:", [(x["ticker"], x["goal"]) for x in g if x["delta"] == 0])
print("largest early margin:", min(g, key=lambda x: x["delta"])["delta"],
      min(g, key=lambda x: x["delta"])["ticker"])
