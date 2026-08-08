import re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
h = open(r'pdufa_site_src\index.html', encoding='utf-8').read()

print('=== ONE "dec" row, verbatim (VERA = newest) ===')
i = h.find('<a class="dec ap" href="/fda-decision/VERA-2026-07-07"')
j = h.find('</a>', i) + 4
print(repr(h[i:j]))

print('\n=== ONE "row" from Next FDA decisions, verbatim (MNKD) ===')
i = h.find('<a class="row" href="/pdufa/MNKD"')
j = h.find('</a>', i) + 4
print(repr(h[i:j])[:900])

print('\n=== container boundaries ===')
a = h.find('<div class="list">')
b = h.find('</div>\n  </section>', a)
print('list  starts %d  ends ~%d' % (a, b))
c = h.find('<div class="decs">')
d = h.find('</div>', c)
print('decs  starts %d' % c)
