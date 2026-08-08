import re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
h = open(r'pdufa_site_src\index.html', encoding='utf-8').read()
a = h.find('<div class="list">'); b = h.find('</div>\n  </section>', a)
rows = re.findall(r'<a class="row" href="/pdufa/[^"]+">.*?</a>', h[a:b], re.S)
print('rows in block:', len(rows), '\n')
for r in rows:
    tk = re.search(r'<span class="tk">([A-Z]+)\s', r)
    pd_ = re.search(r'PDUFA (\d{4}-\d{2}-\d{2})', r)
    cd = re.search(r'<span class="cd"><b>(\d+)</b>', r)
    href = re.search(r'href="([^"]+)"', r).group(1)
    tkspan = re.search(r'<span class="tk">(.*?)</span>', r, re.S)
    print('%-34s cd=%-4s pd=%-12s tk=%-6s tkspan=%r'
          % (href, cd.group(1) if cd else '-', pd_.group(1) if pd_ else 'NONE',
             tk.group(1) if tk else 'FAIL', (tkspan.group(1)[:38] if tkspan else 'NONE')))
