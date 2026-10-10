# -*- coding: utf-8 -*-
"""site_style.py -- the one hub stylesheet (audit 2026-10-04 UX P0: /patent-cliff/exclusivity shipped a stub).

HUB_STYLE is the /patent-cliff block, the header rules every hub template must carry (.top, .brand, .nav a),
plus table rules. A new hub template imports this instead of writing its own <style>; tests/test_header_styled.py
fails any indexable page whose header markup is not styled by its own inline CSS.
"""
HUB_STYLE = (
    ':root{--bg:#0b1017;--line:#1f2a3c;--mut2:#8fa3bd;--gold:#e8b44c}'
    '*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#dfe9f7;'
    'font:15px/1.65 "IBM Plex Mono",ui-monospace,monospace}'
    '.wrap{max-width:1000px;margin:0 auto;padding:18px 16px 60px}'
    '.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:22px}'
    '.brand{font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:20px;color:#fff;text-decoration:none}'
    '.brand b{color:var(--gold)}'
    '.nav a{color:var(--mut2);text-decoration:none;margin-left:14px;font-size:13px}'
    'h1{font-family:"Space Grotesk",sans-serif;font-size:26px;margin:0 0 6px}'
    'h2{font-family:"Space Grotesk",sans-serif;font-size:17px;margin:26px 0 8px;color:var(--gold)}'
    'p{max-width:74ch}a{color:#6fb6ff}a.lit{color:#9ec5ff;text-decoration:none}'
    'table{border-collapse:collapse;width:100%;font-size:13.5px}'
    'th{color:var(--gold);font-size:12px;text-align:left;border-bottom:1px solid #294d80;padding:6px 4px}'
    'td{border-bottom:1px solid #14263f;color:#a7bcd9;padding:6px 4px;vertical-align:top}'
    '.chip{display:inline-block;border:1px solid #2a496f;border-radius:16px;padding:3px 11px;'
    'margin:3px 6px 3px 0;font-size:12.5px;color:#a7bcd9;text-decoration:none}'
    '.legal{margin-top:40px;padding-top:14px;border-top:1px solid var(--line);color:var(--mut2);font-size:12px;line-height:1.7}'
    '@media (max-width:520px){.wrap{padding:14px 12px 50px}h1{font-size:22px}table{font-size:12.5px}}'
)
FONTS_LINK = '<link rel="stylesheet" href="/fonts/fonts.css">'
