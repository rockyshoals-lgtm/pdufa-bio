import json, subprocess, sys
rid = sys.argv[1]
j = json.loads(subprocess.run(["gh", "run", "view", rid, "--json", "status,conclusion,jobs"], capture_output=True, text=True).stdout)
print(j["status"], j.get("conclusion"))
for s in j["jobs"][0]["steps"]:
    if s["status"] == "in_progress" or s.get("conclusion") == "failure":
        print("  ", s["status"], s.get("conclusion"), s["name"])
