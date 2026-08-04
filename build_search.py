# -*- coding: utf-8 -*-
"""build_search.py -- instant search over our own data. No model, no API, no hallucination surface.

Most retail visitors arrive looking for exactly one thing: a ticker. Until now the only way to find
it was to guess a URL or scroll a calendar, which is a poor experience and quietly wastes the
deepest asset on the site, the 209 ticker hubs and 449 decision pages that most visitors never
discover.

This is deliberately NOT an AI box. The whole value of this site is that every number traces to a
primary source, and a language model on the front page is a machine for generating confident
sentences that do not. A retrieval index cannot invent a PDUFA date, because it can only return rows
that exist. It is also instant, free to run, and works when any third-party API is down.

The index is built from the same dataset the pages are generated from, so search results can never
disagree with the pages they point at. It is fetched lazily on first keystroke, so it costs nothing
on page load.

Matching is prefix-and-substring across ticker, drug, company and condition, with ticker matches
ranked first because that is what people type. Dates are matched loosely enough that "august" and
"2026-08" both work.

    python build_search.py [--dry-run]
"""
import argparse, glob, html, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
INDEX = os.path.join(SITE, "search-index.json")
B, E = "<!--SEARCH:BEGIN-->", "<!--SEARCH:END-->"

# Entry points where a search box earns its place. Deliberately not all 846 pages: a deep page's
# job is to answer the question the visitor already had.
TARGETS = ["index.html", os.path.join("calendar", "index.html"),
           os.path.join("tickers", "index.html"), os.path.join("decisions", "index.html")]

MONTHS = {"january": "01", "february": "02", "march": "03", "april": "04", "may": "05",
          "june": "06", "july": "07", "august": "08", "september": "09", "october": "10",
          "november": "11", "december": "12"}


def build_index():
    rows, seen = [], set()

    if os.path.exists(DATASET):
        m = re.search(r"export default (\[.*\])",
                      open(DATASET, encoding="utf-8", errors="replace").read(), re.S)
        for e in (json.loads(m.group(1)) if m else []):
            t = (e.get("t") or "").upper()
            url = e.get("url") or ""
            if not url.startswith("/"):
                url = f"/ticker/{t}" if t else ""
            if not url:
                continue
            key = (t, e.get("name"), url)
            if key in seen:
                continue
            seen.add(key)
            d = e.get("d") or ""
            month = ""
            if re.match(r"^\d{4}-\d{2}", d):
                month = d[:7]
            # The therapeutic area is coarse ("Other" on 131 rows) and the indication is populated
            # on only 68 of 419. Both go into the searchable text so a disease word has something
            # to match, rather than silently returning nothing.
            area = " ".join(x for x in (e.get("ta") or "",
                                        ((e.get("_d") or {}).get("indication") or "")) if x)
            rows.append({"t": t, "n": e.get("name") or "", "c": e.get("company") or "",
                         "a": area, "u": url, "d": d, "m": month,
                         "y": e.get("type") or "", "s": e.get("st") or "",
                         "p": e.get("dp") or ""})

    # Ticker hubs, so a bare ticker always resolves even with no forward catalyst.
    #
    # Read the whole file, not a prefix. The first version read 2,600 characters to save time, but
    # the <h1> on a ticker hub sits at offset ~7,000 behind the JSON-LD, so every hub silently fell
    # back to naming itself after its own ticker: searching "moderna" found nothing.
    for p in sorted(glob.glob(os.path.join(SITE, "ticker", "*", "index.html"))):
        t = os.path.basename(os.path.dirname(p))
        doc = open(p, encoding="utf-8", errors="replace").read()
        mt = re.search(r"<h1[^>]*>(.*?)</h1>", doc, re.S)
        name = re.sub(r"<[^>]+>", " ", mt.group(1)) if mt else t
        name = html.unescape(re.sub(r"\s+", " ", name)).strip()[:90] or t
        rows.append({"t": t, "n": name, "c": "", "a": "", "u": f"/ticker/{t}",
                     "d": "", "m": "", "y": "Ticker", "s": "", "p": ""})

    # Condition hubs, with the lay words people actually type. A reader looking for obesity drugs
    # types "obesity", not "Metabolic". These are navigational aliases pointing at a page we
    # publish, not claims about any drug.
    aliases = {
        "cancer": "cancer oncology tumour tumor carcinoma lymphoma leukemia myeloma solid tumor",
        "obesity-metabolic": "obesity weight loss glp-1 glp1 diabetes metabolic nash mash",
        "cns-neurology": "cns neurology brain alzheimer parkinson epilepsy migraine als multiple "
                         "sclerosis depression schizophrenia narcolepsy",
        "rare-disease": "rare disease orphan duchenne dmd muscular dystrophy gene therapy "
                        "cystic fibrosis huntington",
        "hematology": "blood haematology hematology sickle cell anaemia anemia haemophilia "
                      "hemophilia thalassemia",
        "immunology": "immunology autoimmune lupus psoriasis eczema atopic dermatitis colitis "
                      "crohn arthritis",
        "infectious-disease": "infection infectious antibiotic antiviral vaccine flu influenza "
                              "covid rsv hiv",
        "cardiovascular": "heart cardiovascular cardiac cholesterol hypertension blood pressure",
        "ophthalmology": "eye ophthalmology retina macular vision blindness",
    }
    for p in sorted(glob.glob(os.path.join(SITE, "condition", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        doc = open(p, encoding="utf-8", errors="replace").read()
        mt = re.search(r"<h1[^>]*>(.*?)</h1>", doc, re.S)
        name = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ",
                                                        mt.group(1)))).strip() if mt else slug
        rows.append({"t": "AREA", "n": name[:90] or slug.replace("-", " ").title(),
                     "c": "", "a": aliases.get(slug, slug.replace("-", " ")),
                     "u": f"/condition/{slug}", "d": "", "m": "", "y": "Condition",
                     "s": "", "p": ""})

    return rows


WIDGET = """<!--SEARCH:BEGIN--><div class="pdsearch" style="margin:14px 0 18px;position:relative">
<label for="pdq" style="position:absolute;left:-9999px">Search catalysts by ticker, drug or condition</label>
<input id="pdq" type="search" autocomplete="off" spellcheck="false"
 placeholder="Search a ticker, drug or condition. Try MRNA, or obesity"
 style="width:100%;box-sizing:border-box;padding:13px 15px;font-size:15px;border-radius:12px;
 border:1px solid var(--line);background:var(--card);color:#eef4fc;min-height:46px"
 aria-controls="pdres" aria-expanded="false" role="combobox">
<div id="pdres" role="listbox" style="display:none;position:absolute;z-index:60;left:0;right:0;
 margin-top:6px;background:#0b1626;border:1px solid #294d80;border-radius:12px;
 box-shadow:0 18px 44px rgba(0,0,0,.55);max-height:60vh;overflow:auto"></div></div>
<script>
(function(){var q=document.getElementById('pdq'),r=document.getElementById('pdres'),IX=null,sel=-1;
if(!q)return;
function load(){if(IX)return Promise.resolve(IX);
 return fetch('/search-index.json').then(function(x){return x.json()}).then(function(j){IX=j;return j})
 .catch(function(){IX=[];return IX})}
var M={january:'01',february:'02',march:'03',april:'04',may:'05',june:'06',july:'07',
 august:'08',september:'09',october:'10',november:'11',december:'12'};
function score(row,s){var t=(row.t||'').toLowerCase(),n=(row.n||'').toLowerCase(),
 c=(row.c||'').toLowerCase(),a=(row.a||'').toLowerCase();
 if(t===s)return 100; if(t.indexOf(s)===0)return 90;
 if(n.indexOf(s)===0)return 70; if(n.indexOf(s)>0)return 55;
 if(c.indexOf(s)>-1)return 45; if(a.indexOf(s)>-1)return 35;
 if((row.m||'').indexOf(s)===0)return 30;
 if(M[s]&&(row.m||'').slice(5)===M[s])return 28;
 return 0}
function esc(x){return String(x||'').replace(/[&<>"]/g,function(m){
 return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]})}
function draw(list){ if(!list.length){r.style.display='none';q.setAttribute('aria-expanded','false');return}
 r.innerHTML=list.map(function(x,i){
  var meta=[x.y,x.d?(x.p==='day'?x.d:'~'+x.d.slice(0,7)):'',x.a].filter(Boolean).join(' \\u00b7 ');
  return '<a role="option" href="'+esc(x.u)+'" data-i="'+i+'" style="display:flex;gap:10px;'+
   'align-items:baseline;padding:10px 13px;border-bottom:1px solid #14263f;text-decoration:none">'+
   '<b class="lit" style="color:#f0c86a;min-width:58px">'+esc(x.t)+'</b>'+
   '<span style="flex:1;color:#dce7f7;font-size:14px">'+esc(x.n)+
   '<span style="display:block;color:#7c93b6;font-size:11.5px">'+esc(meta)+'</span></span></a>'}).join('');
 r.style.display='block';q.setAttribute('aria-expanded','true');sel=-1}
function run(){var s=q.value.trim().toLowerCase(); if(s.length<1){r.style.display='none';return}
 load().then(function(ix){var out=[];
  for(var i=0;i<ix.length;i++){var sc=score(ix[i],s); if(sc)out.push([sc,ix[i]])}
  out.sort(function(a,b){return b[0]-a[0]});
  draw(out.slice(0,12).map(function(x){return x[1]}))})}
q.addEventListener('input',run); q.addEventListener('focus',function(){load();if(q.value)run()});
q.addEventListener('keydown',function(e){var opts=r.querySelectorAll('a');
 if(e.key==='Escape'){r.style.display='none';q.blur();return}
 if(!opts.length)return;
 if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();
  sel+=(e.key==='ArrowDown'?1:-1); if(sel<0)sel=opts.length-1; if(sel>=opts.length)sel=0;
  for(var i=0;i<opts.length;i++)opts[i].style.background=(i===sel?'#132745':'transparent');
  opts[sel].scrollIntoView({block:'nearest'})}
 else if(e.key==='Enter'){e.preventDefault();(opts[sel>-1?sel:0]).click()}});
document.addEventListener('click',function(e){if(!r.contains(e.target)&&e.target!==q)r.style.display='none'});
document.addEventListener('keydown',function(e){
 if(e.key==='/'&&document.activeElement!==q&&!/input|textarea/i.test((document.activeElement||{}).tagName||'')){
  e.preventDefault();q.focus()}});
})();
</script><!--SEARCH:END-->"""


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    rows = build_index()
    if not rows:
        print("no rows; refusing to publish an empty search index")
        return
    payload = json.dumps(rows, separators=(",", ":"), ensure_ascii=False)

    placed = 0
    for rel in TARGETS:
        p = os.path.join(SITE, rel)
        if not os.path.exists(p):
            continue
        doc = open(p, encoding="utf-8", errors="replace").read()
        if B in doc:
            doc = re.sub(re.escape(B) + ".*?" + re.escape(E), lambda _: WIDGET, doc, flags=re.S)
        else:
            m = re.search(r"</h1>", doc)
            if not m:
                continue
            # Directly under the page heading: the first thing after "what is this page".
            nxt = doc.find("</div>", m.end())
            at = m.end()
            doc = doc[:at] + WIDGET + doc[at:]
        if not a.dry_run:
            open(p, "w", encoding="utf-8").write(doc)
        placed += 1

    if not a.dry_run:
        open(INDEX, "w", encoding="utf-8").write(payload)

    print(f"search: {len(rows):,} indexed rows ({len(payload)/1024:.0f} KB), box on {placed} page(s)"
          + (" [dry run]" if a.dry_run else ""))


if __name__ == "__main__":
    main()
