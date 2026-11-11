"""Build static/atlas.html from the group's dashboard (tools/atlas_source.html).

Run again whenever the dashboard source changes:
    py tools/build_atlas.py
Changes made to the dashboard:
  * GFA becomes its own map layer (height = GFA intensity, colour = one switchable variable)
  * map falls back to built-in building outlines when online tiles are blocked
  * links to the Story page and the Collector; data-source switch (sample / collector database)
  * static/theme.css (the shared Story look) and static/daynight.js (day / night) are inlined;
    edit those files, then rebuild
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'atlas_source.html')
OUT = os.path.join(os.path.dirname(HERE), 'static', 'atlas.html')
s = open(SRC, encoding='utf-8').read()


def rep(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        sys.exit(f'build_atlas: expected {count} got {n}: {old[:90]!r}')
    s = s.replace(old, new)


rep('<title>Temporal City — 2D/3D Urban Time Atlas</title>', '<title>Temporal City Atlas</title>')
css = open(os.path.join(HERE, 'maplibre-gl.css'), encoding='utf-8').read()
rep('<link rel="stylesheet" href="https://unpkg.com/maplibre-gl@5.8.0/dist/maplibre-gl.css"/>',
    '<style>/* maplibre-gl 5.8.0 */' + css + '</style>')

# ---------- header: brand links home; right side links to the other two parts of the app
rep('<div class="brand">TC<span style="color:#c4a56e">.</span><small>TEMPORAL CITY / NUS</small></div>',
    '<a class="brand" href="index.html">TC<i>.</i><small>Temporal City</small></a>')
rep('<div class="right-top">URBAN TIME ATLAS &nbsp; / &nbsp; 2026</div>',
    '<div id="dnSwitch"></div><nav class="right-top app-links" aria-label="App"><a href="index.html">Story</a><a href="collector.html" data-needs-app>Collector</a><a class="here" href="atlas.html" aria-current="page">Atlas</a><a href="information.html">Information</a></nav>')

# REVEAL and METHOD now live on the Information page (one place for method, data quality and limits)
rep('<button data-view="reveal">REVEAL</button><button data-view="method">METHOD</button>',
    '<a class="nav-info" href="information.html">METHOD &amp; LIMITS →</a>')

# ---------- same fonts as the Story page
rep('<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet">',
    '<link href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&family=Instrument+Serif:ital@0;1&family=Manrope:wght@500;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">')

# ---------- data source switch under the hero stat
rep('<span>IN-CATCHMENT POIs · THREE DISTRICTS</span>',
    '<span>IN-CATCHMENT POIs · THREE DISTRICTS</span><div class="src-switch src-cards" id="srcSwitch" hidden><a href="atlas.html?source=sample" data-src="sample"><b>Google Places sample</b><span>Case-study data · the three study areas</span></a><a href="atlas.html?source=collector" data-src="collector"><b>Collector database</b><span>New areas you collect yourself</span></a></div>')
rep('<main class="wrap">', '<main class="wrap"><div class="src-banner" id="srcBanner" hidden></div>')

# ---------- GFA button
rep('>GFA × TIME<', '>GFA LAYER<')

# ---------- REVEAL process cards now point to the collector
rep('<h4>Human review</h4><p>Pending: verify categories, public accessibility and weekly schedules against reliable source records.</p>',
    '<h4>Audit tool built</h4><p>Quality labels, cross-source agreement and a stratified manual audit are implemented in the Collector. Audit results for this sample are pending.</p>')
rep('<h4>Not yet implemented</h4><p>Future AI extraction from permitted public text sources, with accuracy checked against verified records.</p>',
    '<h4>Implemented in the Collector</h4><p>Rules read common formats first; an AI model reads the remaining unstructured web text and must quote its source sentence. Accuracy will be reported from the audit.</p>')

extra = '''<style>
.app-links{display:flex;gap:6px;align-items:center}
.app-links a{color:#6f7f75;text-decoration:none;font-weight:700;letter-spacing:1px;padding:7px 11px;border-radius:999px}
.app-links a:hover{background:#eef1e8}
.app-links a.here{background:var(--ink);color:#fff}

.hero-stat .src-switch.src-cards{display:grid!important;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px;border:0!important;border-radius:0;overflow:visible;max-width:380px;margin-left:auto}.src-cards[hidden]{display:grid!important}.hero-stat .src-cards a{display:block!important;text-align:left;padding:10px 12px!important;border:1px solid var(--tc-line,#dcdee2)!important;border-radius:12px;background:transparent!important;color:var(--tc-ink-2,#5b6577)!important;opacity:.7;transition:transform .2s,box-shadow .2s,opacity .2s,background .2s;letter-spacing:0!important;font:400 11px/1.4 var(--tc-body,"DM Sans",sans-serif)!important}.hero-stat .src-cards a b{display:block;font:700 13px/1.25 var(--tc-display,Manrope,sans-serif)!important;letter-spacing:-.01em!important;color:inherit!important;margin:0 0 3px}.hero-stat .src-cards a span{display:block;font:400 11px/1.35 var(--tc-body,"DM Sans",sans-serif)!important;letter-spacing:0!important;color:inherit!important;opacity:.85;margin:0}.hero-stat .src-cards a:hover{opacity:1}.hero-stat .src-cards a.on{background:var(--tc-ink,#1a2439)!important;border-color:var(--tc-ink,#1a2439)!important;color:var(--tc-paper,#fff)!important;opacity:1;transform:scale(1.04);box-shadow:0 8px 22px rgba(20,30,60,.18)}html .hero-stat .src-cards a.on b,html.tc-night .hero-stat .src-cards a.on b,html.tc-twilight .hero-stat .src-cards a.on b{color:var(--tc-paper,#fff)!important}html.tc-night .hero-stat .src-cards a:not(.on) b,html.tc-twilight .hero-stat .src-cards a:not(.on) b{color:var(--tc-ink-2,#c9cde0)!important}@media(max-width:650px){.hero-stat .src-switch.src-cards{margin-left:0}}.src-switch{display:inline-flex;margin-top:10px;border:1px solid var(--line);border-radius:999px;overflow:hidden}
.src-switch a{font-size:9px;font-weight:700;letter-spacing:1px;padding:6px 10px;color:#6f7f75;text-decoration:none}
.src-switch a.on{background:var(--ink);color:#fff}
.src-banner{margin:0 0 14px;padding:10px 14px;background:#fbf3e2;border-left:3px solid var(--accent);font-size:12px;color:#5f5232;line-height:1.6}
.gfa-switch{display:flex;flex-wrap:wrap;gap:4px;margin:6px 0 8px}
.gfa-switch button{font:700 9px 'DM Sans',sans-serif;letter-spacing:.4px;padding:4px 7px;border:1px solid #dbe4da;background:#fff;color:#496b58;cursor:pointer;border-radius:2px}
.gfa-switch button.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.gfa-switch button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.map-parcel-legend .grad.gfa{background:linear-gradient(90deg,#efe6d2,#e2c99a,#c9a16a,#9c7444,#5e4127)}
.use-key{display:grid;grid-template-columns:1fr 1fr;gap:3px 8px;margin-top:4px}
.use-key span{display:flex;align-items:center;gap:5px;font-size:9px}
.use-key i{width:9px;height:9px;border-radius:2px;display:inline-block;flex:none}
@media(max-width:850px){.nav{min-width:0;max-width:100%;overflow-x:auto;scrollbar-width:none;flex-wrap:nowrap}.nav::-webkit-scrollbar{display:none}.nav button{flex:none}.app-links a{padding:5px 7px;font-size:9px}}
@media(max-width:650px){.app-links{display:none}}
</style>'''
# shared theme (static/theme.css) goes last so the Atlas matches the Story page and the Collector
theme = open(os.path.join(os.path.dirname(HERE), 'static', 'theme.css'), encoding='utf-8').read()
daynight = open(os.path.join(os.path.dirname(HERE), 'static', 'daynight.js'), encoding='utf-8').read()
rep('</head>', extra + '<style>/* static/theme.css */' + theme + '</style><script>/* static/daynight.js */' + daynight + '</script></head>')

# ---------- day / night: page theme and basemap follow the selected hour (whole-week view = day)
rep("function update(){let a=all()", "function update(){if(window.TCDayNight)TCDayNight.setHour(day==='Whole week'?null:hour);let a=all()")
rep("mapReady=true;drawMap();setTimeout(rebuildBuildingFootprints,500)})}",
    "mapReady=true;if(window.TCDayNight)TCDayNight.addMap(map,{ownSources:['catchment','pois','parcels-gfa','context-tiles'],night:["
    "['catchment-line','line-color','#ad91ed'],['catchment-fill','fill-color','#ad91ed'],"
    "['poi-points','circle-stroke-color','#0e1423'],"
    "['open-heat','heatmap-color',['interpolate',['linear'],['heatmap-density'],0,'rgba(71,40,103,0)',0.15,TC_PALETTE.nightHeat[0],0.4,TC_PALETTE.nightHeat[1],0.7,TC_PALETTE.nightHeat[3],1,TC_PALETTE.nightHeat[4]]],"
    "['open-heat','heatmap-opacity',['interpolate',['linear'],['zoom'],13,0.9,16,0.6]],"
    "['all-buildings-3d','fill-extrusion-color',d=>JSON.parse(JSON.stringify(d).replace('\"#b8b9b8\"','\"#293145\"'))]"
    "]});drawMap();setTimeout(rebuildBuildingFootprints,500)})}")

# ---------- JS: GFA layer + basemap fallback
gfa_js = '''
let gfaColorBy='gfa',OFFLINE_BASE=false;
const GFA_COLOR_LABEL={gfa:'GFA',use:'land use',open:'open POI share'};
function gfaNum(){return ['to-number',['get','gfa_m2'],0]}
function gfaColorExpr(){
 if(gfaColorBy==='use'){const pairs=[];for(const [k,v] of Object.entries(PARCEL_USE_COLORS))pairs.push(k,v);return ['match',['get','land_use'],...pairs,TC_PALETTE.landUse.Other]}
 if(gfaColorBy==='open')return ['case',['==',['get','poi_total'],0],'#e4e6ed',['==',['get','known_count'],0],'#bec3cf',['interpolate',['linear'],['get','availability'],0,TC_PALETTE.opening[0],25,TC_PALETTE.opening[1],50,TC_PALETTE.opening[2],75,TC_PALETTE.opening[3],100,TC_PALETTE.opening[4]]];
 return ['case',['<=',gfaNum(),0],'#e4e6ed',['interpolate',['linear'],['log10',['max',gfaNum(),1]],2,TC_PALETTE.gfa[0],3,TC_PALETTE.gfa[1],4,TC_PALETTE.gfa[2],4.7,TC_PALETTE.gfa[3],5.4,TC_PALETTE.gfa[4]]];
}
function gfaStatus(){return 'GFA layer · height = GPR floor-area intensity · colour = '+GFA_COLOR_LABEL[gfaColorBy]}
function setGfaColor(k){gfaColorBy=k;if(mapReady&&map.getLayer('parcel-gfa-time'))map.setPaintProperty('parcel-gfa-time','fill-extrusion-color',gfaColorExpr());$('#mapLegend').innerHTML=parcelLegendHtml();$('#buildingStatus').textContent=gfaStatus()}
function fallbackStyle(){return {version:8,sources:{bldg:{type:'geojson',data:OSM_BUILDINGS}},layers:[{id:'bg',type:'background',paint:{'background-color':'#f3f5f8'}},{id:'bldg-fill',type:'fill',source:'bldg',paint:{'fill-color':'#e2e6ed','fill-outline-color':'#c6ced9'}}]}}
function setupMap(){if(!window.maplibregl)return setupMapWith(null);const url='https://tiles.openfreemap.org/styles/positron',ctrl=new AbortController(),t=setTimeout(()=>ctrl.abort(),5000);
 fetch(url,{signal:ctrl.signal}).then(r=>{clearTimeout(t);if(!r.ok)throw Error('style');return r.json()}).then(st=>setupMapWith(st)).catch(()=>{OFFLINE_BASE=true;setupMapWith(fallbackStyle())})}
'''
rep("function setupMap(){$('#mapLegend').innerHTML=heatLegend();",
    gfa_js + "function setupMapWith(BASE_STYLE){$('#mapLegend').innerHTML=heatLegend();")
rep("style:'https://tiles.openfreemap.org/styles/positron',", "style:BASE_STYLE,")
rep("map.addSource('context-tiles',{type:'vector',url:'https://tiles.openfreemap.org/planet'});",
    "if(OFFLINE_BASE)map.on('error',()=>{});if(!OFFLINE_BASE)map.addSource('context-tiles',{type:'vector',url:'https://tiles.openfreemap.org/planet'});")
rep("map.addLayer({id:'all-buildings-3d',", "if(!OFFLINE_BASE)map.addLayer({id:'all-buildings-3d',")
rep("map.addLayer({id:'parcel-gfa-time',type:'fill-extrusion',source:'parcels-gfa',paint:{'fill-extrusion-color':['case',['==',['get','poi_total'],0],'#e8e8e2',['==',['get','known_count'],0],'#c4c8c1',['interpolate',['linear'],['get','availability'],0,'#c87958',25,'#dca56e',50,'#e6ce91',75,'#8ca98b',100,'#376f59']],",
    "map.addLayer({id:'parcel-gfa-time',type:'fill-extrusion',source:'parcels-gfa',paint:{'fill-extrusion-color':gfaColorExpr(),")
rep("  $('#mapLegend').innerHTML=mode==='3d'?buildingCountLegend():heatLegend();",
    "  $('#mapLegend').innerHTML=mode==='3d'?buildingCountLegend():mode==='parcel'?parcelLegendHtml():heatLegend();")
rep("  $('#buildingStatus').textContent=(district==='Overview'?'Three 400 m areas':'400 m study circle')+' · '+counts.length+' buildings with POI data · all surrounding buildings visible';",
    "  $('#buildingStatus').textContent=mode==='parcel'?gfaStatus():OFFLINE_BASE&&mode==='3d'?'3D building tiles are not available in this online version; use GFA LAYER for 3D':(district==='Overview'?'Three 400 m areas':'400 m study circle')+' · '+counts.length+' buildings with POI data · all surrounding buildings visible';")
rep("function setMode(next){closeBuildingCallout();hidePoiHover();mode=next;",
    "function setMode(next){closeBuildingCallout();hidePoiHover();const prevMode=mode;mode=next;if(next==='parcel'&&prevMode!=='parcel')showPoints=false;else if(prevMode==='parcel'&&next!=='parcel')showPoints=true;$('#togglePoints').classList.toggle('active',showPoints);")
rep("if(mode==='parcel')$('#buildingStatus').textContent='Parcel height = GPR intensity · colour = open POI share';",
    "if(mode==='parcel')$('#buildingStatus').textContent=gfaStatus();")
rep("duration:700});drawMap();",
    "duration:700});drawMap();if(mode==='parcel'&&map.getLayer('parcel-gfa-time'))map.setPaintProperty('parcel-gfa-time','fill-extrusion-color',gfaColorExpr());")
i, j = s.index('function parcelLegendHtml(){'), s.index('function showParcelPopup(')
s = s[:i] + '''function parcelLegendHtml(){
 const btn=(k,t)=>`<button type="button" class="${gfaColorBy===k?'on':''}" onclick="setGfaColor('${k}')">${t}</button>`;
 const useName={Residential:'Residential',Mixed:'Mixed',Commercial:'Commercial',Hotel:'Hotel',Civic_Edu:'Civic / Edu.',Open_Space:'Open space',Other:'Other'};
 let body;
 if(gfaColorBy==='use')body=`<b>COLOUR · LAND USE</b><div class="use-key">${Object.entries(PARCEL_USE_COLORS).filter(([k])=>k!=='EXCLUDE').map(([k,v])=>`<span><i style="background:${v}"></i>${useName[k]||k}</span>`).join('')}</div>`;
 else if(gfaColorBy==='open')body=`<b>COLOUR · OPEN POI SHARE AT SELECTED HOUR</b><div class="grad"></div><div class="grad-labels"><span>0% open</span><span>100% open</span></div><div class="legend-note">Grey = no POIs / no known schedule.</div>`;
 else body=`<b>COLOUR · ESTIMATED GFA (m²)</b><div class="grad gfa"></div><div class="grad-labels"><span>100</span><span>1k</span><span>10k</span><span>250k</span></div><div class="legend-note">Grey = no numeric GPR (GFA not imputed).</div>`;
 return `<div class="map-parcel-legend"><b>GFA LAYER · PAIR WITH</b><div class="gfa-switch">${btn('gfa','GFA only')}${btn('use','Land use')}${btn('open','Open share')}</div>${body}<div class="legend-note">Height = GPR-based floor-area intensity (visual scale, not building height). POI points are hidden here; use POI POINTS to show them.</div></div>`}
''' + s[j:]

# ---------- app glue: data-source switch, collector link when the app is not running
glue = '''<script>
(function(){
 const src=window.ATLAS_SOURCE||'sample';
 // hero: how many of the POIs actually have opening hours (the denominator of every availability figure)
 const hsBox=document.querySelector('.hero-stat'),cap=hsBox&&hsBox.querySelector(':scope > span');
 if(cap){const K=DATA.filter(p=>p.v).length,n=DATA.length,pct=n?Math.round(K/n*100):0,el=document.createElement('span');
  el.className='hero-known'+(n&&pct<50?' low':'');el.innerHTML='<b>'+K+'</b> WITH OPENING HOURS · '+pct+'%';
  el.title=(n-K)+' POIs have no usable opening hours and count as Unknown, not closed';cap.after(el)}
 document.querySelectorAll('#srcSwitch a').forEach(a=>a.classList.toggle('on',a.dataset.src===src));
 // A restored browser page must redraw from this page's immutable DATA,
 // especially after visiting the live Collector dataset.
 window.addEventListener('pageshow',e=>{if(e.persisted&&typeof update==='function')update()});
 if(src==='collector'){const b=document.getElementById('srcBanner');b.hidden=false;
  const K=DATA.filter(p=>p.v).length;
  b.innerHTML='<b>Collector database</b> · '+DATA.length+' POIs in the three case-study areas, '+K+' with usable hours (verified, observed or retrieved). The map, the 3D and GFA layers and every COMPARE chart and table are computed from these records. Land use and GFA come from URA parcels as before; <a href="information.html">Method &amp; limits</a> · <a href="atlas.html?source=sample">Back to the sample</a>';
  const ct=document.getElementById('ccTotal');if(ct){ct.textContent=DATA.length;document.getElementById('ccWhat').textContent='Collector dataset'}
  const I=window.TC_AREA_INFO;
  function areaPicker(I,esc){if(!I.choices||I.choices.length<2)return '';const shown=new Set(I.areas.map(a=>a.id));
   return '<details class="area-pick"><summary>Choose study areas ('+I.areas.length+' of '+I.choices.length+' shown)</summary><div class="ap-list">'
    +I.choices.map(c=>'<label><input type="checkbox" value="'+c.id+'"'+(shown.has(c.id)?' checked':'')+'> '+esc(c.name)+' <small>'+c.n+'</small></label>').join('')
    +'</div><div class="ap-btns"><button type="button" class="btn" data-ap="none">Clear</button><button type="button" class="btn primary" data-ap="go">Show selected</button> <small>Up to '+I.max+' areas</small></div></details>'}
  document.addEventListener('click',e=>{const b=e.target.closest('[data-ap]');if(!b)return;const box=b.closest('.area-pick');
   if(b.dataset.ap==='none'){box.querySelectorAll('input').forEach(i=>i.checked=false);return}
   const ids=[...box.querySelectorAll('input:checked')].map(i=>i.value);if(!ids.length)return;location.href='atlas.html?source=collector&areas='+ids.join(',')});
  if(I&&DATA.length){const esc=t=>String(t).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
   const names=I.areas.map(a=>esc(a.name)+' ('+DATA.filter(p=>p.d===a.name).length+')').join(', '),noParcel=I.areas.filter(a=>!a.case).map(a=>esc(a.name));
   b.innerHTML='<b>Collector database</b> · '+DATA.length+' POIs, '+K+' with usable hours (verified, observed or retrieved), in '+I.areas.length+' study area'+(I.areas.length>1?'s':'')+': '+names+'. The map and every COMPARE chart and table are computed from these records.'
    +' Land use and GFA: '+esc(I.landuse)+(/case studies only/.test(I.landuse)&&noParcel.length?' — not available for '+noParcel.join(', '):'')+'.'
    +(I.dropped?' '+I.dropped+' POIs in further areas are not shown (up to '+I.max+' areas at a time).':'')
    +' <a href="information.html">Method &amp; limits</a> · <a href="atlas.html?source=sample">Back to the sample</a>'
    +areaPicker(I,esc);
   const n=I.areas.length,word=['','One study area','Two study areas','Three study areas'][n]||n+' study areas';
   const hp=document.querySelector('.hero p');if(hp)hp.textContent=hp.textContent.replace('across three Singapore districts',n===1?'in '+I.areas[0].name:'across '+n+' study areas');
   const hs=document.querySelector('.hero-stat > span');if(hs)hs.firstChild.nodeValue='IN-CATCHMENT POIs · '+(n===1?'ONE STUDY AREA':n+' STUDY AREAS');
   document.querySelectorAll('h2').forEach(h=>{if(h.textContent.trim()==='Three districts. Different urban rhythms.')h.textContent=word+'. '+(n>1?'Different urban rhythms.':'One urban rhythm.')});
   const sel=document.getElementById('gtaDistrict');if(sel){sel.innerHTML='<option value="All">All study areas</option>'+I.areas.map(a=>'<option value="'+esc(a.name)+'">'+esc(a.name)+'</option>').join('')}}
  const G=window.COLLECTOR_DIAG;
  if(!DATA.length&&G){const esc=t=>String(t).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
   const areas=G.areas.length?G.areas.map(a=>esc(a.name)+' ('+a.n+' POIs)').join(', '):'none';
   b.innerHTML='<b>No Collector POIs in the three case-study areas.</b> The Atlas is reading <code>'+esc(G.path)+'</code>, which holds <b>'+G.pois+' POIs</b>. Study areas in it: '+areas+'.<br>'
    +(G.pois===0?'This database is empty. If you collected data, it is in a different copy of the project folder (each copy has its own <code>data/temporal_city.db</code>), or the file was replaced when a new version was unzipped over it. Start <code>py app.py</code> from the folder where you collected, or copy that folder’s <code>data/temporal_city.db</code> here.'
     :'POIs count when their study area is named Bencoolen, Tanjong Pagar or Promenade, or when they lie within 400 m of those stations. Run DISCOVER for the three case studies in the Collector, then reload.')
    +' <a href="atlas.html?source=sample">Back to the sample</a>'}
  const hs=document.querySelector('.hero-stat b');if(hs)hs.firstChild.nodeValue=String(DATA.length)}
 fetch('api/meta',{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject()).then(()=>{document.getElementById('srcSwitch').hidden=false}).catch(()=>{
  document.querySelectorAll('[data-needs-app]').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();alertBox()}))});
 function alertBox(){const b=document.getElementById('srcBanner');b.hidden=false;b.textContent='The Collector runs in the local app: start it with "py app.py" and open the address it prints.';window.scrollTo({top:0,behavior:'smooth'})}
})();
</script>'''
glue = glue.replace('<script>\n(function(){', '<script>\nTCDayNight.mountSwitch(document.getElementById("dnSwitch"));\n(function(){', 1)
# COMPARE join KPIs: computed from ANALYSIS.meta when the server provides the numbers (Collector),
# otherwise the figures of the shipped Google Places sample
rep('<strong>574 / 595</strong><small>96.5% matched to URA land-use polygons</small><div class="kpi-foot">21 points have no parcel match</div>',
    '${joinKpi(m.parcel_joined??574,m.in_scope_pois,"matched to URA land-use polygons","have no parcel match")}')
rep('<strong>514 / 595</strong><small>86.4% matched to supplied building footprints</small><div class="kpi-foot">81 points have no footprint match</div>',
    '${joinKpi(m.building_joined??514,m.in_scope_pois,"matched to supplied building footprints","have no footprint match")}')
rep('<small>466 known · 129 unknown</small>', '<small>${m.in_scope_known_hours} known · ${m.in_scope_missing_hours} unknown</small>')
rep(' function drawJoins(){',
    ' function joinKpi(k,n,what,miss){return `<strong>${k} / ${n}</strong><small>${n?fmt(k/n*100,1):"0.0"}% ${what}</small><div class="kpi-foot">${n-k} points ${miss}</div>`}\n function drawJoins(){')
rep('Known and unknown schedules within the 595-POI in-catchment sample',
    'Known and unknown schedules within the <span id="ccTotal">595</span>-POI in-catchment <span id="ccWhat">sample</span>')
# ---------- any Collector study area can be a district (server sets window.TC_AREAS; the sample keeps its three)
rep("const districts=['Bencoolen','Tanjong Pagar','Promenade'];const centers={'Overview':[1.2895,103.8521],'Bencoolen':[1.2983646,103.8498919],'Tanjong Pagar':[1.2765063,103.8464332],'Promenade':[1.2932255,103.8603490]};",
    "const districts=window.TC_AREAS?TC_AREAS.map(a=>a.name):['Bencoolen','Tanjong Pagar','Promenade'];"
    "const centers=window.TC_AREAS?Object.fromEntries([['Overview',TC_OVERVIEW]].concat(TC_AREAS.map(a=>[a.name,[a.lat,a.lon,a.r]]))):{'Overview':[1.2895,103.8521],'Bencoolen':[1.2983646,103.8498919],'Tanjong Pagar':[1.2765063,103.8464332],'Promenade':[1.2932255,103.8603490]};"
    "const OV_ZOOM=window.TC_OV_ZOOM||13.8;")
rep(".map(d=>circleFeature(centers[d]))", ".map(d=>circleFeature(centers[d],centers[d][2]||400))")
rep("return dx*dx+dy*dy<=400*400}", "const r=c[2]||400;return dx*dx+dy*dy<=r*r}")
rep("zoom:district==='Overview'?13.8:15.4", "zoom:district==='Overview'?OV_ZOOM:15.4")
rep("zoom:d==='Overview'?(mode==='3d'?14.2:13.8):15.4", "zoom:d==='Overview'?(mode==='3d'?Math.min(14.2,OV_ZOOM+.4):OV_ZOOM):15.4")
rep("Math.max(14.2,map.getZoom())", "Math.max(Math.min(14.2,OV_ZOOM+.4),map.getZoom())")
rep("'Three 400 m areas'", "(districts.length===3&&!window.TC_AREAS?'Three 400 m areas':districts.length+(districts.length===1?' study area':' study areas'))")
rep("const areas=['Bencoolen','Tanjong Pagar','Promenade'];", "const areas=window.TC_AREAS?TC_AREAS.map(a=>a.name):['Bencoolen','Tanjong Pagar','Promenade'];", 2)
rep("const colors={'Bencoolen':'#24634f','Tanjong Pagar':'#c18e4f','Promenade':'#8a6da8'};",
    "const colors=(()=>{const base=TC_PALETTE.district,pal=TC_PALETTE.fallbackDistrict;let j=0;const o={};areas.forEach(d=>{o[d]=base[d]||pal[j++%pal.length]});return o})();")
rep("const fmt=(v,n=1)=>Number(v).toFixed(n);", "const fmt=(v,n=1)=>v==null||!isFinite(v)?'—':Number(v).toFixed(n);")
rep("const fmt=v=>Number(v).toLocaleString('en-SG',{maximumFractionDigits:0});", "const fmt=v=>v==null||!isFinite(v)?'—':Number(v).toLocaleString('en-SG',{maximumFractionDigits:0});")
rep("const GTA_DISTRICTS=['Bencoolen','Tanjong Pagar','Promenade'];", "const GTA_DISTRICTS=window.TC_AREAS?TC_AREAS.map(a=>a.name):['Bencoolen','Tanjong Pagar','Promenade'];")
rep("'the three study areas together'", "(window.TC_AREAS?'all study areas together':'the three study areas together')")
rep('</body>', glue + '</body>')
# ---------- COMPARE reads as questions: heading = research question, finding (computed) below it,
# method/data notes at the bottom of each section; a question index at the top of the page
story_js = """<script>
(function(){
 const A=ANALYSIS,names=Object.keys(A.temporal),n=names.length,I=window.TC_AREA_INFO;
 const per=()=>document.getElementById('analysisPeriod')?.value||'weekday';
 const PER={weekday:'weekdays',weekend:'weekends',all_days:'the whole week'};
 const pc=v=>v==null||!isFinite(v)?'—':(Math.round(v*10)/10)+'%';
 const h3=v=>v==null||!isFinite(v)?'—':v.toFixed(2);
 const esc=t=>String(t).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
 const b=t=>'<b>'+esc(t)+'</b>';
 const by=(arr,f)=>arr.slice().sort((x,y)=>f(y)-f(x));
 const late=d=>A.temporal[d].summary[per()].late_night_22_05_mean_availability_pct, day=d=>A.temporal[d].summary[per()].daytime_09_18_mean_availability_pct;
 const H=d=>A.spatial[d]?.land_area_entropy;
 const CAT={'Food & Beverage':'food & beverage places','Retail':'shops','Services':'services','Education':'education places','Community & Civic':'community & civic places','Culture & Recreation':'culture & recreation places'};
 const USE={Residential:'residential',Mixed:'mixed use',Commercial:'commercial',Hotel:'hotel',Civic_Edu:'civic & education',Open_Space:'open space'};
 const S=[
  {anchor:'comparison',q:n===1?'How much of '+names[0]+' stays open after dark?':'Which area keeps its amenities open after dark?',
   f:()=>{if(n===1){const d=names[0];return 'On '+PER[per()]+' from 22:00 to 05:00, '+b(pc(late(d)))+' of '+esc(d)+'’s amenities with known hours are open, against '+pc(day(d))+' in the daytime (09:00–18:00).'}
     const r=by(names,late),dd=names.map(day);return 'On '+PER[per()]+' from 22:00 to 05:00, '+b(r[0])+' keeps the largest share of its amenities open ('+pc(late(r[0]))+'), '+b(r[r.length-1])+' the smallest ('+pc(late(r[r.length-1]))+'). In the daytime (09:00–18:00) the areas range from '+pc(Math.min(...dd))+' to '+pc(Math.max(...dd))+'.'},
   note:'Shares use POIs with known opening hours; POIs without hours are Unknown, not closed.'},
  {anchor:'gtaKpis',q:'Does floor-area intensity stay active after hours?',
   f:()=>{const el=document.getElementById('gtaInterpretation');if(!el)return '';const c=el.cloneNode(true);const t=c.querySelector('strong,b');if(t)t.remove();return esc(c.textContent.trim())},watch:'gtaInterpretation'},
  {anchor:'heatmaps',q:'Which kinds of amenity keep the night going?',
   f:()=>{const L=[22,23,0,1,2,3,4,5],D=[9,10,11,12,13,14,15,16,17,18],sum=hs=>{const o={};for(const d of names)for(const h of hs)for(const [c,v] of Object.entries(A.temporal[d].profiles[per()][h].open_by_category_avg))o[c]=(o[c]||0)+v;return o};
     const nt=sum(L),dt=sum(D),tn=Object.values(nt).reduce((a,v)=>a+v,0),td=Object.values(dt).reduce((a,v)=>a+v,0);
     if(!tn)return 'No amenity with known hours is open between 22:00 and 05:00 on '+PER[per()]+'.';
     const r=by(Object.keys(nt),c=>nt[c]);const sh=c=>pc(nt[c]/tn*100),shd=c=>td?pc(dt[c]/td*100):'—';
     return 'Between 22:00 and 05:00 on '+PER[per()]+', '+b(CAT[r[0]]||r[0])+' make up '+sh(r[0])+' of the amenities still open (against '+shd(r[0])+' by day), followed by '+esc(CAT[r[1]]||r[1])+' ('+sh(r[1])+').'},
   note:''},
  {anchor:'spatialKpis',q:n===1?'How mixed is '+names[0]+'’s land use?':'How mixed is each area’s land use?',
   f:()=>{const w=names.filter(d=>H(d)!=null);if(!w.length)return 'No land-use parcels are available for these areas.';
     const big=d=>{const p=A.spatial[d].land_area_by_class_pct||{};const k=by(Object.keys(p),c=>p[c])[0];return k?USE[k]+' at '+pc(p[k])+' of its land':'—'};
     const miss=names.filter(d=>H(d)==null),mtxt=miss.length?' No parcel data for '+miss.map(esc).join(', ')+'.':'';
     if(w.length===1)return esc(w[0])+' has a land-use entropy of '+b('H = '+h3(H(w[0])))+' (0 = one use, 1 = an even mix of six); its largest use is '+big(w[0])+'.'+mtxt;
     const r=by(w,H);return b(r[0])+' has the most mixed land use ('+b('H = '+h3(H(r[0])))+'), '+b(r[r.length-1])+' the least ('+h3(H(r[r.length-1]))+', mostly '+big(r[r.length-1])+').'+mtxt},
   note:'Land use and GPR: '+(I?I.landuse:'URA Master Plan 2019 (amended), clipped in GIS to the official 400 m catchments')+'. GFA = clipped parcel area × numeric GPR; parcels without a numeric GPR (e.g. landed housing, EVA) add no GFA.'},
  {anchor:'temporalKpis',q:'Does more land-use mix mean more amenities open at night?',
   f:()=>{const w=names.filter(d=>H(d)!=null);if(w.length<2)return 'This needs at least two areas with land-use data. Add another study area in the Collector to compare.';
     const mix=by(w,H)[0],night=by(w,late)[0];
     if(mix===night)return 'In this selection, yes: '+b(mix)+' is both the most mixed (H = '+h3(H(mix))+') and the most open at night ('+pc(late(mix))+' on '+PER[per()]+', 22:00–05:00).';
     if(Math.abs(late(night)-late(mix))<1)return 'Barely: '+b(mix)+' has the most mixed land use (H = '+h3(H(mix))+'), while '+b(night)+' is only just ahead at night ('+pc(late(night))+' vs '+pc(late(mix))+', '+PER[per()]+' 22:00–05:00) — a near tie.';
     return 'Not in this selection: '+b(mix)+' has the most mixed land use (H = '+h3(H(mix))+'), but '+b(night)+' keeps the most amenities open at night ('+pc(late(night))+' vs '+pc(late(mix))+', '+PER[per()]+' 22:00–05:00).'},
   note:''},
  {anchor:'joinSummary',q:'How complete is the data behind these charts?',
   f:()=>{const m=A.meta,N=m.in_scope_pois,K=m.in_scope_known_hours;return b(K+' of '+N)+' POIs ('+pc(N?K/N*100:null)+') have opening hours; '+(m.parcel_joined??574)+' lie on a land-use parcel and '+(m.building_joined??514)+' inside a building footprint.'},
   note:''}];
 const view=document.getElementById('compare');if(!view)return;
 const idx=document.createElement('nav');idx.className='tc-qindex';idx.setAttribute('aria-label','Questions on this page');
 idx.innerHTML='<span class="eyebrow">Questions on this page</span>';
 S.forEach((s,k)=>{const el=document.getElementById(s.anchor);const panel=el&&el.closest('.panel');if(!panel)return;
  const head=panel.querySelector(':scope > h2, :scope > h3');if(!head)return;
  panel.id=panel.id||('q'+(k+1));panel.classList.add('tc-q');head.textContent=s.q;
  const f=document.createElement('p');f.className='tc-finding';head.after(f);
  const notes=[];let sub=f.nextElementSibling;if(sub&&sub.matches('p.sub')){notes.push(sub.innerHTML);sub.remove()}
  if(s.note)notes.push(s.note);
  if(notes.length){const dn=document.createElement('div');dn.className='tc-datanote';dn.innerHTML='<span>Data note</span>'+notes.map(x=>'<p>'+x+'</p>').join('');panel.appendChild(dn)}
  const draw=()=>{f.innerHTML='<span class="tc-flabel">Finding</span>'+s.f()};draw();s.draw=draw;
  if(s.watch){const w=document.getElementById(s.watch);if(w)new MutationObserver(draw).observe(w,{childList:true,subtree:true,characterData:true})}
  const a=document.createElement('a');a.href='#'+panel.id;a.innerHTML='<i>'+(k+1)+'</i>'+esc(s.q);a.onclick=e=>{e.preventDefault();panel.scrollIntoView({behavior:'smooth',block:'start'})};idx.appendChild(a)});
 view.prepend(idx);
 document.getElementById('analysisPeriod')?.addEventListener('change',()=>S.forEach(s=>s.draw&&s.draw()));
})();
</script>"""
rep('</body>', story_js + '</body>')

rep('<script>const DATA=', '<script>window.ATLAS_SOURCE="sample";</script><script>const DATA=')
# Shared cartographic palette. Numeric opening activity stays coral; estimated GFA
# uses a separate blue scale. Category colours retain their established mapping.
rep("'fill-color':'#66977b','fill-opacity':0.035", "'fill-color':'#9f91c9','fill-opacity':0.035")
rep("'line-color':'#2e6b55','line-width':1.5", "'line-color':'#8572ba','line-width':1.5")
# Semantic colours are shared with Story, Collector and Information. Keep the
# original data, labels and chart structure; only replace colour expressions.
rep("const amenityColors={'Food & Beverage':'#d16750','Retail':'#2d8987','Services':'#5076ae','Education':'#7868a9','Community & Civic':'#7b8e4e','Culture & Recreation':'#ad5f94'};",
    "const amenityColors=TC_PALETTE.category;")
rep("const useColors={'Residential':'#8b9c83','Mixed':'#c7a76b','Commercial':'#4f8074','Hotel':'#b87959','Civic_Edu':'#7887a9','Open_Space':'#a7b68a'};",
    "const useColors=TC_PALETTE.landUse;")
rep("const PARCEL_USE_COLORS={Residential:'#829b89',Mixed:'#c9a86f',Commercial:'#3f7668',Hotel:'#b67b5e',Civic_Edu:'#818eae',Open_Space:'#a7b88e',Other:'#b5b9b1',EXCLUDE:'#d9d9d2'};",
    "const PARCEL_USE_COLORS=TC_PALETTE.landUse;")
rep("['match',['get','category'],'Food & Beverage','#d16750','Retail','#2d8987','Services','#5076ae','Education','#7868a9','Community & Civic','#7b8e4e','Culture & Recreation','#ad5f94','#647b77']",
    "['match',['get','category'],...Object.entries(TC_PALETTE.category).filter(([k])=>k!=='All').flat(),'#8c98ac']")
for old, new in [('#fff0e8', 'TC_PALETTE.opening[0]'),('#f6bba8', 'TC_PALETTE.opening[1]'),('#e98774', 'TC_PALETTE.opening[2]'),('#c9544f', 'TC_PALETTE.opening[3]'),('#91363e', 'TC_PALETTE.opening[4]')]:
    # JS literals only: CSS gradients remain handled by shared future.css.
    s = s.replace("'" + old + "'", new)
rep("draw(result.gfa,'#bd965c');draw(result.poi,'#315f50');",
    "draw(result.gfa,TC_PALETTE.gfaLine);draw(result.poi,TC_PALETTE.poiLine);")
rep('fill="#dcebe2" opacity=".6"', 'fill="${TC_PALETTE.poiLine}" opacity=".16"')
rep('stroke="#27664e" stroke-width="2.5"', 'stroke="${TC_PALETTE.poiLine}" stroke-width="3"')
rep('stroke="#27664e" stroke-width="2"', 'stroke="${TC_PALETTE.poiLine}" stroke-width="3"')
rep('stroke="#c4a16b" stroke-dasharray="4 4"', 'stroke="${TC_PALETTE.hourLine}" stroke-dasharray="4 4"')
rep('fill="#c4a16b" stroke="white"', 'fill="${TC_PALETTE.hourLine}" stroke="white"')
rep('stroke="#9b7650" stroke-dasharray="4 4"', 'stroke="${TC_PALETTE.hourLine}" stroke-dasharray="4 4"')
rep('style="background:#bd965c"', 'style="background:var(--tc-gfa-line)"')
rep('style="background:#315f50"', 'style="background:var(--tc-poi-line)"')
rep("const bg=val===null?'#eef0ec':`rgba(35,100,78,${0.12+val*.76})`;",
    "const bg=val===null?'#eef0ec':`color-mix(in srgb,${TC_PALETTE.nightHeat[3]} ${Math.round((.16+val*.84)*100)}%,transparent)`;")

# The temporal profile uses the same open/known slots as the live selection.
# Whole week uses seven-day averages for absolute counts and the ratio of
# seven-day totals for relative availability. Unknown schedules are excluded.
rep('<svg id="linechart" class="chart"',
    '<div class="profile-mode" role="group" aria-label="Temporal profile metric">'
    '<button type="button" data-profile-metric="absolute" aria-pressed="true">ABSOLUTE</button>'
    '<button type="button" data-profile-metric="relative" aria-pressed="false">RELATIVE %</button>'
    '</div><svg id="linechart" class="chart"')
rep('</svg></div><div class="panel chartpanel"><div class="eyebrow">03 / DISTRICT SNAPSHOT',
    '</svg><div id="profileLegend" class="profile-legend" aria-label="Study area curves"></div></div><div class="panel chartpanel"><div class="eyebrow">03 / DISTRICT SNAPSHOT')
s = s.replace("slots.filter(x=>x!==null).length/divisor", "slots.filter(x=>x===0||x===1).length/divisor", 1)
chart_start = s.index('function drawChart(){')
chart_end = s.index('function update(){', chart_start)
s = s[:chart_start] + '''let profileMetric='absolute';
function drawChart(){
  const weekly=day==='Whole week', relative=profileMetric==='relative';
  const palette=TC_PALETTE.district;
  const curves=districts.map((name,i)=>({
    name,color:palette[name]||TC_PALETTE.fallbackDistrict[i%TC_PALETTE.fallbackDistrict.length],
    values:profile(name,[...enabled]).map(v=>relative?(v.known>0?100*v.open/v.known:null):v.open)
  }));
  const max=relative?100:Math.max(1,...curves.flatMap(c=>c.values).filter(Number.isFinite));
  const x=h=>34+h/23*608, y=v=>159-v/max*130;
  const axis=relative?v=>Math.round(v)+'%':v=>String(Math.round(v));
  $('#profileSubtitle').textContent=relative
    ? (weekly?'Average share of POIs with known hours open by hour across seven days · study area comparison'
      :'Share of POIs with known hours open · study area comparison')
    : (weekly?'Average open POIs by hour across seven days · study area comparison'
      :'Absolute open POI counts · study area comparison');
  let svg='';
  for(let i=0;i<=4;i++){
    const v=max*i/4, yy=y(v);
    svg+=`<line x1="34" y1="${yy}" x2="642" y2="${yy}" stroke="#e5ebe2"/>`
      +`<text x="26" y="${yy+4}" text-anchor="end" font-size="10" fill="#9aa99b">${axis(v)}</text>`;
  }
  for(const i of [0,6,12,18,23]) svg+=`<text x="${x(i)}" y="185" text-anchor="middle" font-size="10" fill="#9aa99b">${String(i).padStart(2,'0')}:00</text>`;
  if(!weekly){
    svg+=`<line x1="${x(hour)}" y1="18" x2="${x(hour)}" y2="159" stroke="${TC_PALETTE.hourLine}" stroke-dasharray="4 4"/>`;
  }
  for(const c of curves){
    let line='',segment=false;
    c.values.forEach((v,h)=>{
      if(v===null||!Number.isFinite(v)){segment=false;return;}
      line+=(segment?' L':' M')+x(h).toFixed(1)+' '+y(v).toFixed(1);segment=true;
    });
    const selected=district==='Overview'||district===c.name;
    svg+=`<path d="${line}" fill="none" stroke="${c.color}" stroke-width="${selected?3.3:2.2}" stroke-opacity="${selected?1:.55}" stroke-linejoin="round" stroke-linecap="round"/>`;
    if(!weekly&&Number.isFinite(c.values[hour]))svg+=`<circle cx="${x(hour)}" cy="${y(c.values[hour])}" r="${selected?4.5:3.3}" fill="${c.color}" stroke="var(--card)" stroke-width="1.5"/>`;
  }
  $('#linechart').innerHTML=svg;
  const legend=$('#profileLegend');
  if(legend)legend.replaceChildren(...curves.map(c=>{
    const item=document.createElement('span'),dot=document.createElement('i');
    dot.style.background=c.color;item.append(dot,document.createTextNode(c.name));
    item.className=district==='Overview'||district===c.name?'':'muted';return item;
  }));
}
''' + s[chart_end:]
rep('function build(){for(const d of',
    "function build(){document.querySelectorAll('[data-profile-metric]').forEach(b=>b.onclick=()=>{profileMetric=b.dataset.profileMetric;document.querySelectorAll('[data-profile-metric]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));drawChart()});for(const d of")
assert s.count('</head>') == 1
s = s.replace('</head>', '<script src="/static/palette.js?v22"></script>'
              '<link rel="stylesheet" href="/static/future.css?v22">'
              '<script src="/static/lens-nav.js?v22" defer></script></head>', 1)
open(OUT, 'w', encoding='utf-8').write(s)
print('wrote', OUT, len(s))
