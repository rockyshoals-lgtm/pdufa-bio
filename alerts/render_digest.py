"""DRAFT: render the free weekly pdufa.bio alert email from the site's own published data.

Renders only. It sends nothing, reads no subscriber list and needs no API key.

    python alerts/render_digest.py [--as-of YYYY-MM-DD]

Writes alerts/preview/digest_<date>.html and .txt so the email can be reviewed in a browser.

Facts-only rules this renderer enforces (pdufa.bio's immutable FACTS-ONLY principle):
  * Every line is something the record shows: a date on the calendar, or a decision recorded.
  * Every decision line carries the primary source link found on its pdufa.bio decision page
    (FDA first, then SEC, then the company's own release). No source found -> the line is
    left out, not sent unsourced.
  * No probabilities, run-up statistics, price moves or buy/sell language. The calendar feed's
    run-up sentence is deliberately not copied into the email.
"""
import argparse, datetime as dt, html, os, re, string, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_SRC = os.path.join(ROOT, 'pdufa_site_src')
TPL = os.path.join(ROOT, 'alerts', 'templates')
OUT = os.path.join(ROOT, 'alerts', 'preview')
SITE = 'https://www.pdufa.bio'

BANNED = re.compile(r'\b(probabilit|odds|likely|expect|predict|forecast|buy|sell|target price|run-?up|upside|downside)', re.I)


def parse_ics(path):
    raw = open(path, encoding='utf-8').read().replace('\r\n ', '').replace('\n ', '')
    for block in re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', raw, re.S):
        f = {}
        for line in block.strip().splitlines():
            k, _, v = line.partition(':')
            f[k.split(';')[0]] = v.replace('\\,', ',').replace('\\;', ';')
        yield f


def source_for(decision_url):
    """Primary source link from the decision page itself (the page is built from sourced data)."""
    rel = decision_url.replace(SITE, '').strip('/')
    p = os.path.join(SITE_SRC, rel, 'index.html')
    if not os.path.exists(p):
        return None
    page = open(p, encoding='utf-8').read()
    links = re.findall(r'href="(https?://[^"]+)"[^>]*>([^<]{2,90})<', page)
    links = [(html.unescape(u), html.unescape(t.strip())) for u, t in links if 'pdufa.bio' not in u]
    for pref in ('fda.gov', 'sec.gov/Archives', ''):
        for u, t in links:
            if pref in u and not re.search(r'13[DG]|Capital|Advisors|Investments|Management', t):
                return u, t
    return None


def build(as_of):
    week_ago, week_ahead = as_of - dt.timedelta(days=7), as_of + dt.timedelta(days=7)
    decided, upcoming = [], []
    for e in parse_ics(os.path.join(SITE_SRC, 'calendar.ics')):
        uid, desc, url = e.get('UID', ''), e.get('DESCRIPTION', ''), e.get('URL', '')
        if not uid.startswith('pdufa_'):
            continue
        summ = e.get('SUMMARY', '')
        m = re.match(r'~?([A-Z.]{1,6}) PDUFA: (.+)', summ)
        if not m:
            continue
        ticker, drug = m.group(1), m.group(2).strip().replace(' - (', ' (').replace(' - ', ', ')
        status = (re.search(r'Status: ([^.]+)\.', desc) or [None, ''])[1]
        if status == 'Decided':
            dm = re.search(r'/fda-decision/[A-Z.]+-(\d{4}-\d{2}-\d{2})', url)
            outcome = (re.search(r'Outcome: ([^.]+)\.', desc) or [None, ''])[1]
            if not dm or not outcome:
                continue
            d = dt.date.fromisoformat(dm.group(1))
            if week_ago < d <= as_of:
                src = source_for(url)
                if src:
                    decided.append(dict(date=d, ticker=ticker, drug=drug, outcome=outcome, url=url, src=src))
        elif status == 'Upcoming':
            d = dt.datetime.strptime(e['DTSTART'], '%Y%m%d').date()
            if as_of <= d <= week_ahead:
                exact = desc.startswith('Confirmed date')
                upcoming.append(dict(date=d, ticker=ticker, drug=drug, url=url, exact=exact))
    decided.sort(key=lambda r: r['date']); upcoming.sort(key=lambda r: r['date'])
    return decided, upcoming


def fmt_day(d):
    return d.strftime('%a %b ') + str(d.day)


def render(as_of, decided, upcoming):
    esc = html.escape
    row = ('<tr><td style="padding:8px 0;border-bottom:1px solid #e4e9f0;vertical-align:top;width:92px;color:#556;font-size:13px">{d}</td>'
           '<td style="padding:8px 0;border-bottom:1px solid #e4e9f0;font-size:14px;line-height:1.45"><b>{t}</b> · {drug}<br>{extra}</td></tr>')
    dec_html = ''.join(row.format(
        d=fmt_day(r['date']), t=esc(r['ticker']), drug=esc(r['drug']),
        extra=(f'Outcome on record: <b>{esc(r["outcome"])}</b>. Source: <a href="{esc(r["src"][0])}" style="color:#1a5fb4">{esc(r["src"][1])}</a> · '
               f'<a href="{esc(r["url"])}" style="color:#1a5fb4">pdufa.bio page</a>')) for r in decided) \
        or '<tr><td style="padding:8px 0;color:#556;font-size:14px">No FDA decisions on tracked drugs were recorded this week.</td></tr>'
    up_html = ''.join(row.format(
        d=fmt_day(r['date']), t=esc(r['ticker']), drug=esc(r['drug']),
        extra=('Confirmed goal date' if r['exact'] else 'Estimated date') +
              f' · <a href="{esc(r["url"])}" style="color:#1a5fb4">dates and sources</a>') for r in upcoming) \
        or '<tr><td style="padding:8px 0;color:#556;font-size:14px">No PDUFA goal dates on the calendar in the next seven days.</td></tr>'

    dec_txt = '\n'.join(f'- {fmt_day(r["date"])}: {r["ticker"]} {r["drug"]}. Outcome on record: {r["outcome"]}. '
                        f'Source: {r["src"][1]} {r["src"][0]}' for r in decided) or '- No FDA decisions on tracked drugs were recorded this week.'
    up_txt = '\n'.join(f'- {fmt_day(r["date"])}: {r["ticker"]} {r["drug"]} ({"confirmed" if r["exact"] else "estimated"}) {r["url"]}'
                       for r in upcoming) or '- No PDUFA goal dates on the calendar in the next seven days.'

    vals = dict(
        date_long=as_of.strftime('%B ') + str(as_of.day) + as_of.strftime(', %Y'),
        n_dec=len(decided), n_up=len(upcoming),
        decided_rows=dec_html, upcoming_rows=up_html, decided_txt=dec_txt, upcoming_txt=up_txt,
        # Filled per recipient by the sender; left as a marker in previews.
        unsubscribe_url='{{UNSUBSCRIBE_URL}}',
        postal_address='[POSTAL ADDRESS: required by CAN-SPAM, David to supply]',
    )
    htm = string.Template(open(os.path.join(TPL, 'digest.html'), encoding='utf-8').read()).substitute(vals)
    txt = string.Template(open(os.path.join(TPL, 'digest.txt'), encoding='utf-8').read()).substitute(vals)

    # Facts-only guard: refuse to produce an email whose own words drift into prediction or advice.
    body = re.sub(r'<[^>]+>|https?://\S+', ' ', htm)
    bad = BANNED.findall(body.replace('not investment advice', '').replace('to buy or sell any security', ''))
    if bad:
        sys.exit(f'facts-only check failed, banned words in email: {sorted(set(bad))}')
    subject = f'pdufa.bio weekly: {len(decided)} FDA decision{"s" if len(decided) != 1 else ""} recorded, {len(upcoming)} goal date{"s" if len(upcoming) != 1 else ""} ahead'
    return subject, htm, txt


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--as-of', default=dt.date.today().isoformat())
    a = ap.parse_args()
    as_of = dt.date.fromisoformat(a.as_of)
    subject, htm, txt = render(as_of, *build(as_of))
    os.makedirs(OUT, exist_ok=True)
    for ext, s in (('html', htm), ('txt', f'Subject: {subject}\n\n{txt}')):
        open(os.path.join(OUT, f'digest_{as_of}.{ext}'), 'w', encoding='utf-8').write(s)
    print(subject)
