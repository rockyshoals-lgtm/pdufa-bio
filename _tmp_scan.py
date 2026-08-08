s = open(r"C:\Users\dcmoo\Documents\Python\9realms\pdufa_site_src\decisions\index.html", encoding="utf-8").read()
idx = s.find("CELC-2026-07-14")
start = max(0, idx-4000)
end = idx+100
with open(r"C:\Users\dcmoo\Documents\Python\9realms\_tmp_scan_out3.txt", "w", encoding="utf-8") as f:
    f.write(s[start:end])
