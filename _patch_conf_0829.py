"""Gap-fill from the fresh-BPC compare (2026-08-29): aliases + registry dates.

Two gap classes found by _bpc_compare_0829.py:
  A. ESC and EASD had OBSERVED 2026 registry dates but ZERO aliases — the extractor could
     not even NAME them. That is how we missed AZN/IONS/ALNY/BAYRY/EWTX presenting at ESC
     the very weekend it was running.
  B. EADV / EURETINA / ASBMR / Retina Society had no registry entry at all, and ERS had an
     alias but no 2026 date — so even a perfect extraction died at resolve_date (we never
     guess a date we don't have).

Registry dates below come from BPC's conference-dated rows (published congress agendas —
externally checkable, the same trust class as the rest of the registry).
"""
import io, json, sys, os

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))

# ---- A. aliases ------------------------------------------------------------------
p = os.path.join(HERE, "conference_presentations.py")
t = io.open(p, encoding="utf-8").read()
old = '''    "eortc-nci-aacr": "ENA",
    "molecular targets and cancer therapeutics": "ENA",
}'''
new = '''    "eortc-nci-aacr": "ENA",
    "molecular targets and cancer therapeutics": "ENA",
    # 2026-08-29 gap fill, from the fresh-BPC compare (_bpc_compare_0829.py). ESC and EASD
    # had OBSERVED 2026 dates in the registry but ZERO aliases -- the extractor could not
    # even NAME them, which is how we missed AZN/IONS/ALNY/BAYRY/EWTX presenting at ESC the
    # very weekend it was running. The rest are congresses BPC dates that the registry
    # lacked. No bare ambiguous short aliases ("esc" is escape, "ers" is common prose) --
    # full names or clearly-scoped forms only.
    "european society of cardiology": "ESC",
    "esc congress": "ESC",
    "european association for the study of diabetes": "EASD",
    "easd annual meeting": "EASD", "easd": "EASD",
    "european academy of dermatology and venereology": "EADV",
    "eadv congress": "EADV", "eadv": "EADV",
    "euretina congress": "EURETINA", "euretina": "EURETINA",
    "american society for bone and mineral research": "ASBMR",
    "asbmr annual meeting": "ASBMR", "asbmr": "ASBMR",
    "retina society scientific meeting": "RETSOC",
    "annual retina society": "RETSOC", "retina society": "RETSOC",
    "ers international congress": "ERS", "ers congress": "ERS",
    "iaslc world conference on lung cancer": "WCLC",
}'''
assert old in t, "ALIASES anchor missing"
io.open(p, "w", encoding="utf-8").write(t.replace(old, new))
print("aliases: patched")

# ---- B. registry -----------------------------------------------------------------
rp = os.path.join(HERE, "conf_registry.json")
reg = json.load(io.open(rp, encoding="utf-8"))
ADD = {
    # code: (2026 date from BPC's conference-dated rows, day-of-year approx)
    "EADV":     ("2026-10-01", 274),
    "EURETINA": ("2026-09-18", 261),
    "ASBMR":    ("2026-10-09", 282),
    "RETSOC":   ("2026-09-23", 266),
    "ERS":      ("2026-09-06", 249),
}
for code, (d, doy) in ADD.items():
    e = reg.setdefault(code, {"dates": {}, "doy": doy})
    e.setdefault("dates", {})
    if "2026" not in e["dates"]:
        e["dates"]["2026"] = d
        print(f"registry: {code} 2026 -> {d}")
    else:
        print(f"registry: {code} already has 2026 = {e['dates']['2026']}")
json.dump(reg, io.open(rp, "w", encoding="utf-8"), indent=1, sort_keys=True)
print(f"registry: {len(reg)} congresses total")
