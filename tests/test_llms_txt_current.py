# -*- coding: utf-8 -*-
"""CI guard: /llms.txt carries the owners' current numbers (build_llms_txt.py renders it).

2026-09-23: the file we ask AI assistants to quote said n=1,792 and 73.5% while the study
said n=1,852 and 71.3%. Re-rendering must be a no-op; if it is not, the file is stale.

    python tests/test_llms_txt_current.py
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)


def main():
    import build_llms_txt as B
    cur = io.open(B.OUT, encoding="utf-8").read()
    want = B.render(B.facts())
    if cur != want:
        import difflib
        print("FAIL: /llms.txt differs from its owners' numbers. Run build_llms_txt.py.")
        for l in list(difflib.unified_diff(cur.splitlines(), want.splitlines(), "llms.txt", "owners", lineterm=""))[:20]:
            print("   " + l)
        return 1
    f = B.facts()
    print(f"OK -- /llms.txt current: n={f['n_pdufa']:,}, {f['approval_rate']}%, readouts {f['n_readouts']}, "
          f"timing {f['t_early']}/{f['t_on']}/{f['t_late']} of {f['t_n']}, CRL {f['crl_total']}/{f['crl_approved']}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
