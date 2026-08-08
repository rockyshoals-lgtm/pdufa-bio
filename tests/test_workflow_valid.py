# -*- coding: utf-8 -*-
"""test_workflow_valid.py -- the GitHub Actions workflow must actually parse.

Origin: I added steps named "Run-up study: fold in newly decided PDUFAs" and "SLS: verify the ...
claim against EDGAR". An unquoted colon-space inside a YAML scalar ends the scalar, so those names
made the whole file invalid. GitHub cannot run a workflow it cannot parse, which means the daily
rebuild was silently dead from the moment those steps were added, and nothing on the site would
have told us: the site just quietly stops updating.

Every other guard in this directory protects the data. This one protects the thing that runs the
guards.

Checks:
  1. the workflow is valid YAML
  2. every step has a name and something to run
  3. any secret referenced in an env block is one we expect (typo in a secret name silently yields
     an empty string, which is how a credential appears to "not work" with no error)
  4. every `python X.py` step refers to a script that exists

    python tests/test_workflow_valid.py
"""
import glob, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF_DIR = os.path.join(HERE, ".github", "workflows")

KNOWN_SECRETS = {"POLYGON_API_KEY", "FMP_API_KEY", "SEC_USER_AGENT",
                 # Bing is the engine we actually rank on and the one GSC cannot see. The reporter
                 # exits 0 when this is unset, so an unconfigured key degrades to no data rather
                 # than a failed build.
                 "BING_WEBMASTER_API_KEY",
                 "GSC_SERVICE_ACCOUNT_JSON", "GITHUB_TOKEN"}


def main():
    try:
        import yaml
    except ImportError:
        print("SKIP: pyyaml not installed in this environment")
        sys.exit(0)

    ok = True
    files = sorted(glob.glob(os.path.join(WF_DIR, "*.yml")) +
                   glob.glob(os.path.join(WF_DIR, "*.yaml")))
    if not files:
        print("FAIL: no workflow files found")
        sys.exit(1)

    for f in files:
        rel = os.path.relpath(f, HERE)
        raw = open(f, encoding="utf-8").read()
        try:
            doc = yaml.safe_load(raw)
        except Exception as e:
            ok = False
            print(f"\nFAIL: {rel} is not valid YAML")
            print(f"   {type(e).__name__}: {str(e)[:300]}")
            print("   GitHub cannot run a workflow it cannot parse, so the daily rebuild would be "
                  "dead with no visible symptom on the site.")
            print("   Most common cause here: a step name containing an unquoted ': '. Quote it.")
            continue

        steps = ((doc or {}).get("jobs", {}).get("rebuild", {}) or {}).get("steps", [])
        print(f"{rel}: parses OK, {len(steps)} step(s)")

        for i, s in enumerate(steps, 1):
            if not isinstance(s, dict):
                ok = False
                print(f"  FAIL: step {i} is not a mapping")
                continue
            if not (s.get("name") or s.get("uses")):
                ok = False
                print(f"  FAIL: step {i} has no name and no uses")
            if not (s.get("run") or s.get("uses")):
                ok = False
                print(f"  FAIL: step {i} ({s.get('name')}) has nothing to run")

            for name in re.findall(r"secrets\.([A-Z_0-9]+)", str(s.get("env", ""))):
                if name not in KNOWN_SECRETS:
                    ok = False
                    print(f"  FAIL: step '{s.get('name')}' references unknown secret {name!r}. "
                          f"A typo'd secret resolves to an empty string with no error.")

            for script in re.findall(r"python\s+([A-Za-z0-9_./-]+\.py)", str(s.get("run", ""))):
                if not os.path.exists(os.path.join(HERE, script)):
                    ok = False
                    print(f"  FAIL: step '{s.get('name')}' runs {script}, which does not exist")

    print("\n  PASS: workflows parse and every step is runnable" if ok else "\n  see failures above")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
