"""CI guard (P1-2): no public page renders an absurd raw days-to-cover.

19% of short-interest rows have days-to-cover > 100 -- legitimate for an illiquid nano-cap,
credibility-destroying on a page ("Short interest: 4,200 days to cover"). The rule:
  * DTC > 60 must render as "very illiquid", never a raw number.
  * a raw DTC > 30 must never appear without context.
  * always print the settlement date.

STATUS AT WRITE TIME (2026-07-17): not yet a live defect. app.html renders zero short interest
and the data feed exposes no per-ticker DTC; the only SI surface is /research/short-interest-fda,
which already excludes DTC>60 and shows sane medians (2.2-6.8 days). This guard exists so the cap
is enforced the moment per-ticker DTC DOES render -- i.e. when SI-at-catalyst (P1-5) ships --
rather than discovered after "4,200 days to cover" is already public.

    python tests/test_si_display_cap.py

Heuristic: find "<number> days to cover" in rendered text. If the number exceeds 60 it must be
accompanied by "very illiquid" nearby; a bare number over 60 fails. Prose thresholds like
"days-to-cover (>60) were excluded" are methodology, not a rendered value, and are ignored.
"""
import os, re, sys

ROOT = "pdufa_site_src"
CAP_HARD = 60
# "<n> days to cover" or "<n> days-to-cover" as a RENDERED value (not "(>60)", not "> 60")
RENDERED = re.compile(r"(?<![>(\-])\b(\d{1,5}(?:\.\d+)?)\s*days[\s\-]*to[\s\-]*cover", re.I)
CONTEXT_OK = re.compile(r"very\s+illiquid", re.I)


def visible_text(html):
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.I | re.S)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html)


def main():
    if not os.path.isdir(ROOT):
        print(f"  SKIP {ROOT} not present"); return 0
    fail = checked = 0
    for dp, _, fns in os.walk(ROOT):
        if any(seg.startswith(("_", ".")) for seg in dp.split(os.sep)):
            continue
        for fn in fns:
            if not fn.endswith(".html"):
                continue
            p = os.path.join(dp, fn)
            try:
                txt = visible_text(open(p, encoding="utf-8", errors="replace").read())
            except Exception:
                continue
            checked += 1
            for m in RENDERED.finditer(txt):
                val = float(m.group(1))
                if val <= CAP_HARD:
                    continue
                window = txt[max(0, m.start() - 60): m.end() + 60]
                if CONTEXT_OK.search(window):
                    continue
                print(f"  FAIL {p}: renders '{m.group(0)}' (>{CAP_HARD}) without 'very illiquid' context")
                fail += 1
    if fail:
        print(f"\n{fail} SI-display violation(s). DTC>{CAP_HARD} must render as 'very illiquid'. DO NOT PUBLISH.")
        return 1
    print(f"OK -- {checked} HTML files, no raw days-to-cover over {CAP_HARD} rendered without context.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
