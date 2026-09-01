import json,glob,os,csv
def peek(p,label):
    try: d=json.load(open(p,encoding="utf-8",errors="replace"))
    except Exception as e: print(label,"ERR",e); return
    print(f"--- {label} :: {p}")
    if isinstance(d,dict):
        print("  keys:",list(d)[:8],"n=",len(d))
        k=list(d)[0]; print("  sample:",json.dumps(d[k])[:300])
    else:
        print("  list n=",len(d)); print("  sample:",json.dumps(d[0])[:300])
for pat,lab in (("**/pdufa_calendar.json","PDUFA CAL"),("**/pdufa_done.json","PDUFA DONE"),
                ("**/readout_calendar.json","READOUT CAL")):
    g=glob.glob(pat,recursive=True)
    if g: peek(g[0],lab)
