import json
c=json.load(open("Momentum Scanner/pdufa_calendar.json",encoding="utf-8",errors="replace"))
e=c["events"]; print("PDUFA events n=",len(e)); print(json.dumps(e[0])[:420])
print("dates:",sorted({x.get("pdufa_date") or x.get("date") or "?" for x in e})[:12])
r=json.load(open("Momentum Scanner/readout_calendar.json",encoding="utf-8",errors="replace"))
ro=r["readouts"]; print("\nREADOUT n=",len(ro),type(ro))
if isinstance(ro,list): print(json.dumps(ro[0])[:420])
else:
    k=list(ro)[:4]; print("keys",k); print(json.dumps(ro[k[0]])[:420])
