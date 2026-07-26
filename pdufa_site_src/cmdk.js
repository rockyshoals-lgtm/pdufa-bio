(function(){
  if(window.__cmdk)return; window.__cmdk=1;
  var css='#cmdkBtn{position:fixed;right:16px;bottom:16px;z-index:9998;display:flex;align-items:center;gap:8px;background:#0e1c33;border:1px solid #294d80;color:#9db3d4;font:600 13px/1 -apple-system,Segoe UI,Roboto,sans-serif;padding:10px 13px;border-radius:22px;cursor:pointer;box-shadow:0 6px 20px rgba(0,0,0,.4);transition:.15s}#cmdkBtn:hover{color:#eef4fc;border-color:#f0c86a}#cmdkBtn kbd{font:700 11px ui-monospace,monospace;background:#081426;border:1px solid #294d80;border-radius:5px;padding:2px 6px;color:#f0c86a}'
   +'#cmdkO{position:fixed;inset:0;z-index:9999;background:rgba(2,6,13,.62);backdrop-filter:blur(3px);display:none;align-items:flex-start;justify-content:center}#cmdkO.on{display:flex}'
   +'#cmdkB{margin-top:11vh;width:min(620px,92vw);background:#0b1626;border:1px solid #294d80;border-radius:16px;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.6)}'
   +'#cmdkI{width:100%;box-sizing:border-box;background:#0b1626;border:0;border-bottom:1px solid #1e3a63;color:#eef4fc;font:500 17px -apple-system,Segoe UI,Roboto,sans-serif;padding:16px 18px;outline:none}'
   +'#cmdkR{max-height:56vh;overflow:auto;padding:6px}#cmdkR a{display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:10px;text-decoration:none;color:#eef4fc}#cmdkR a.sel,#cmdkR a:hover{background:#132745}'
   +'.ck-ty{font:800 10px ui-monospace,monospace;padding:2px 7px;border-radius:5px;min-width:70px;text-align:center}.ck-PDUFA{color:#f0c86a;background:rgba(240,200,106,.14)}.ck-Readout{color:#5aa9f0;background:rgba(90,169,240,.14)}.ck-Conference{color:#c58bff;background:rgba(197,139,255,.14)}.ck-AdComm{color:#46d17f;background:rgba(70,209,127,.14)}'
   +'.ck-tk{font:700 14px ui-monospace,monospace}.ck-nm{font-size:12.5px;color:#9db3d4;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.ck-dt{margin-left:auto;font:12px ui-monospace,monospace;color:#7c93b6}#cmdkR .ck-empty{padding:26px;text-align:center;color:#9db3d4}';
  // D3 tap targets + D9 motion/state polish
  css+=''
   +'@media (pointer:coarse){.hd nav a,.nav a{min-height:44px;display:inline-flex;align-items:center}.chip{min-height:40px;display:inline-flex;align-items:center}.row{padding-top:15px;padding-bottom:15px}#cmdkBtn{min-height:44px}}'
   +'a,button,.row,.chip,.card{transition:background .15s ease,border-color .15s ease,transform .15s ease,box-shadow .15s ease}'
   +'.row:hover{box-shadow:0 8px 24px rgba(0,0,0,.28)}'
   +'a:focus-visible,button:focus-visible,.row:focus-visible,.chip:focus-visible{outline:2px solid #f0c86a;outline-offset:2px;border-radius:8px}'
   +'@keyframes pdSkel{0%{background-position:-360px 0}100%{background-position:360px 0}}'
   +'.pd-skel{background:#0e1c33;background-image:linear-gradient(90deg,rgba(255,255,255,0) 0,rgba(157,179,212,.10) 50%,rgba(255,255,255,0) 100%);background-size:360px 100%;background-repeat:no-repeat;animation:pdSkel 1.1s infinite linear;border-radius:8px}'
   +'.pd-empty{padding:34px 18px;text-align:center;color:#9db3d4;border:1px dashed #294d80;border-radius:14px;background:rgba(14,28,51,.4)}.pd-empty b{color:#eef4fc;display:block;font-family:"Space Grotesk",sans-serif;font-size:15px;margin-bottom:4px}'
   +'@media (prefers-reduced-motion:reduce){*{animation-duration:.001ms!important;transition-duration:.001ms!important}}';
  var s=document.createElement('style');s.textContent=css;document.head.appendChild(s);
  var btn=document.createElement('div');btn.id='cmdkBtn';btn.innerHTML='<span>Search</span> <kbd>⌘K</kbd>';document.body.appendChild(btn);
  var o=document.createElement('div');o.id='cmdkO';o.innerHTML='<div id="cmdkB"><input id="cmdkI" placeholder="Search any ticker, drug, or catalyst…" autocomplete="off" spellcheck="false"><div id="cmdkR"></div></div>';document.body.appendChild(o);
  var inp=o.querySelector('#cmdkI'),res=o.querySelector('#cmdkR'),DATA=null,sel=0,rows=[];
  function esc(x){return (x||'').replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  function skel(){var r='';for(var i=0;i<6;i++){r+='<div style="display:flex;align-items:center;gap:10px;padding:9px 12px"><div class="pd-skel" style="width:70px;height:16px"></div><div class="pd-skel" style="width:44px;height:16px"></div><div class="pd-skel" style="flex:1;height:14px"></div></div>'}return r}
  function open(){o.classList.add('on');inp.value='';inp.focus();if(!DATA){res.innerHTML=skel();fetch('/api/v1/events?limit=1000').then(function(r){return r.json()}).then(function(j){DATA=j.data||[];render('')}).catch(function(){res.innerHTML='<div class="pd-empty"><b>Search is offline</b>Couldn’t reach the catalyst feed. Check your connection and try again.</div>'})}else render('')}
  function close(){o.classList.remove('on')}
  function render(q){q=q.trim().toLowerCase();if(!DATA)return;var out=DATA;if(q)out=DATA.filter(function(e){return e.ticker.toLowerCase().indexOf(q)>=0||(e.name||'').toLowerCase().indexOf(q)>=0||e.type.toLowerCase().indexOf(q)>=0});out=out.slice(0,60);sel=0;rows=out;
    res.innerHTML=out.length?out.map(function(e,i){return '<a href="'+esc(e.url)+'" class="'+(i===0?'sel':'')+'"><span class="ck-ty ck-'+e.type+'">'+e.type+'</span><span class="ck-tk">'+esc(e.ticker)+'</span><span class="ck-nm">'+esc(e.name)+'</span><span class="ck-dt">'+esc(e.date)+'</span></a>'}).join(''):'<div class="pd-empty"><b>No matches</b>Nothing matches “'+esc(q)+'”. Try a ticker, drug name, or catalyst type.</div>'}
  function move(d){var a=res.querySelectorAll('a');if(!a.length)return;a[sel]&&a[sel].classList.remove('sel');sel=(sel+d+a.length)%a.length;a[sel].classList.add('sel');a[sel].scrollIntoView({block:'nearest'})}
  inp.addEventListener('input',function(){render(inp.value)});
  document.addEventListener('keydown',function(e){if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();o.classList.contains('on')?close():open()}else if(e.key==='Escape')close();else if(o.classList.contains('on')){if(e.key==='ArrowDown'){e.preventDefault();move(1)}else if(e.key==='ArrowUp'){e.preventDefault();move(-1)}else if(e.key==='Enter'){var a=res.querySelectorAll('a');if(a[sel])window.location.href=a[sel].getAttribute('href')}}});
  btn.addEventListener('click',open);o.addEventListener('click',function(e){if(e.target===o)close()});
})();
