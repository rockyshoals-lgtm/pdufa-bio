import requests
UA = "pdufa.bio research you@pdufa.bio"
h = {"User-Agent": UA, "Accept-Encoding": "gzip, deflate", "Accept": "*/*"}

# 1) ticker map (www.sec.gov)
r = requests.get("https://www.sec.gov/files/company_tickers.json", headers=h, timeout=30)
print("1) ticker map (www.sec.gov):", r.status_code)

# 2) full-text search (efts.sec.gov)
r = requests.get("https://efts.sec.gov/LATEST/search-index",
                 params={"q": '"PDUFA goal date"', "forms": "8-K"}, headers=h, timeout=30)
print("2) full-text search (efts.sec.gov):", r.status_code)
hit = None
if r.status_code == 200:
    hits = r.json().get("hits", {}).get("hits", [])
    print("   hits returned:", len(hits))
    if hits:
        hit = hits[0]
else:
    print("   body:", r.text[:160])

# 3) document fetch (www.sec.gov/Archives) -- the part most likely blocked
if hit:
    adsh, fn = hit["_id"].split(":", 1)
    cik = int(hit["_source"]["ciks"][0])
    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{adsh.replace('-','')}/{fn}"
    r = requests.get(url, headers=h, timeout=30)
    print("3) Archives document fetch:", r.status_code, "->", url)
    if r.status_code != 200:
        print("   body:", r.text[:160])
