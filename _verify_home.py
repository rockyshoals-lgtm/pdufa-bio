import re, sys, datetime as dt
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
h = open(r'pdufa_site_src\index.html', encoding='utf-8').read()
TODAY = dt.date.today()
print('today:', TODAY)

# Parse ROW BY ROW. The earlier version used one regex with `.*?PDUFA (date)` across the whole
# block, so for a row lacking its own date the non-greedy run crossed into the NEXT row and
# paired the wrong countdown with the wrong date. Isolate each row first.
a = h.find('<div class="list">'); b = h.find('</div>\n  </section>', a)
rows = re.findall(r'<a class="row" href="/pdufa/[^"]+">.*?</a>', h[a:b], re.S)
print('\n=== Next FDA decisions — countdown vs truth (%d rows) ===' % len(rows))
ok = True
for r in rows:
    href = re.search(r'href="/pdufa/([^"]+)"', r).group(1)
    cd = re.search(r'<span class="cd"><b>(\d+)</b><i>(\w+)</i></span>', r)
    pd_ = re.search(r'PDUFA (\d{4}-\d{2}-\d{2})', r)
    if not cd or not pd_:
        print('  %-24s (no countdown/date to check)' % href); continue
    shown = int(cd.group(1)); real = max((dt.date.fromisoformat(pd_.group(1)) - TODAY).days, 0)
    good = shown == real
    ok &= good
    print('  %-24s shows %3d %-5s | PDUFA %s | actual %3d  %s'
          % (href, shown, cd.group(2), pd_.group(1), real, 'ok' if good else '<-- WRONG'))
print('\nALL COUNTDOWNS CORRECT' if ok else '*** SOME WRONG ***')
print('CELC still in pending list:', 'pdufa/CELC' in h[a:b], '(expect False)')

c = h.find('<div class="decs">')
print('\n=== Recently decided (top 4 of %d) ===' % len(re.findall(r'<a class="dec ', h[c:])))
for m in list(re.finditer(r'<a class="dec (\w+)" href="/fda-decision/([^"]+)".*?<span class="dd">([^<]*)</span>', h[c:], re.S))[:4]:
    print('  %-4s %-22s %s' % (m.group(1), m.group(2), m.group(3)))
