/* pdufa.bio "Just in": shows what the every-minute news watch posted (/api/v1/live) on the drug's PDUFA page and on
   the home page, within a minute of the source. Every word from the API is set as text, never as HTML. Times are
   US Eastern with the zone (RULE 1). Built by inject_live_banner.py; guard: tests/test_live_watch.py. */
(function () {
  if (!window.fetch || !document.querySelector) return;
  var path = location.pathname.replace(/\/index\.html$/, '').replace(/\/+$/, '') || '/';
  var ET = { timeZone: 'America/New_York', month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' };
  function et(iso) { var t = Date.parse(iso); return isFinite(t) ? new Intl.DateTimeFormat('en-US', ET).format(new Date(t)) + ' ET' : ''; }
  function gap(m) { return m < 60 ? m + ' min' : m < 2880 ? Math.floor(m / 60) + ' h ' + (m % 60) + ' min' : Math.floor(m / 1440) + ' d ' + Math.floor((m % 1440) / 60) + ' h'; }
  function el(tag, css, text) { var e = document.createElement(tag); if (css) e.style.cssText = css; if (text) e.textContent = text; return e; }
  function link(href, text) { var a = el('a', '', text); if (/^https:\/\//.test(href)) { a.href = href; a.rel = 'nofollow noopener'; } return a; }
  function card(p) {
    var retracted = p.status === 'retracted';
    var box = el('div', 'border:1px solid ' + (retracted ? '#c25b5b' : '#46d17f') + ';background:#0c1d38;border-radius:12px;padding:12px 14px;margin:12px 0;font-size:14px;line-height:1.5');
    box.setAttribute('data-live', p.id);
    box.setAttribute('role', 'status');
    var head = el('div', 'font-weight:700;color:' + (retracted ? '#ff9b9b' : '#46d17f') + ';margin-bottom:4px',
      retracted ? 'Retracted ' + et(p.retracted_at) : 'Just in');
    box.appendChild(head);
    box.appendChild(el('div', retracted ? 'text-decoration:line-through;color:#a7bcd9' : 'color:#f2f6fc', p.text));
    if (retracted) box.appendChild(el('div', 'color:#f2f6fc;margin-top:4px', p.retract_reason || ''));
    var src = el('div', 'color:#a7bcd9;font-size:12.5px;margin-top:6px');
    src.appendChild(document.createTextNode('Source: '));
    src.appendChild(link(p.source && p.source.url, (p.source && p.source.label) || 'source'));
    src.appendChild(document.createTextNode(', ' + et(p.source && p.source.published_at) + '. Posted on pdufa.bio ' +
      et(p.posted_at) + ', ' + gap(p.minutes_after_source) + ' after the source, by an automatic check of the source\'s headline. ' +
      (retracted ? '' : (p.rechecked_at ? 'Source read again ' + et(p.rechecked_at) + ': it still says this. ' : '') +
        (p.status === 'confirmed' ? 'The full review shows the same outcome.' : 'The rest of this page is updated after a full review.'))));
    box.appendChild(src);
    return box;
  }
  fetch('/api/v1/live', { credentials: 'omit' }).then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
    if (!j || !j.data || !j.data.length) return;
    var now = Date.now();
    var recent = j.data.filter(function (p) { return now - Date.parse(p.posted_at) < 14 * 86400000; });
    if (path === '/') {
      var home = recent.filter(function (p) { return now - Date.parse(p.posted_at) < 2 * 86400000; });
      var anchor = document.querySelector('h1');
      if (!home.length || !anchor) return;
      var wrap = el('div', 'margin:12px 0');
      wrap.setAttribute('data-live-home', '');
      home.slice(0, 3).forEach(function (p) {
        var c = card(p);
        if (/^\/[^/]/.test(p.page || '') && p.status !== 'retracted') { var more = el('div', 'font-size:12.5px;margin-top:4px'); more.appendChild(link('https://www.pdufa.bio' + p.page, 'Open the page')); c.appendChild(more); }
        wrap.appendChild(c);
      });
      anchor.parentNode.insertBefore(wrap, anchor.nextSibling);
      return;
    }
    var mine = recent.filter(function (p) { return p.page === path && p.status !== 'confirmed'; });
    var h1 = document.querySelector('h1');
    if (!mine.length || !h1) return;
    h1.parentNode.insertBefore(card(mine[0]), h1.nextSibling);
  }).catch(function () {});
})();
