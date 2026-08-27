#!/usr/bin/env python3
HTML="/Users/sunyoung/korea-dulle-gil/index.html"
KEY="2c014f51c0251eb88b3c1ecb9cd9f18d"
src=open(HTML,encoding="utf-8").read()
def rep(old,new,n=1):
    global src
    assert old in src, "NOT FOUND:\n"+old[:160]
    src=src.replace(old,new,n)

# 1) remove Leaflet CSS
rep('<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />\n','')

# 2) Leaflet JS -> Kakao SDK
rep('<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>',
    f'<script src="//dapi.kakao.com/v2/maps/sdk.js?appkey={KEY}&autoload=false"></script>')

# 3) map state vars
rep('let map, meMarker, meCircle, liveLine;',
    'let map, meMarker, meCircle, liveLine, courseIW=null, meOverlay=null;')

# 4) initMap
rep('''function initMap(){
  map = L.map('map',{zoomControl:false, attributionControl:true}).setView([36.5,127.9], 7);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{
    maxZoom:19, attribution:'© OpenStreetMap'
  }).addTo(map);
  map.on('zoomend', updateLabels);
  drawRoutes();       // 코스별 실측 경로 (선택 구간만)
  drawSavedTracks();  // GPS로 걸은 실제 경로
  fitToFilter();      // 선택 구간에 맞춰 화면 이동
}''',
'''function initMap(){
  map = new kakao.maps.Map(document.getElementById('map'), {
    center: new kakao.maps.LatLng(36.5, 127.9), level: 13
  });
  kakao.maps.event.addListener(map, 'zoom_changed', updateLabels);
  drawRoutes();       // 코스별 실측 경로 (선택 구간만)
  fitToFilter();      // 선택 구간에 맞춰 화면 이동
}''')

# 5) fitToFilter
rep('''function fitToFilter(){
  const secs = SECTIONS.filter(s=>viewFilter==='all'||s.id===viewFilter);
  const pts=[];
  secs.forEach(s=>(REAL_ROUTES[s.id]||[]).forEach(c=>{
    if(c.start&&c.end){ pts.push(c.start, c.end); }
  }));
  if(pts.length) map.fitBounds(L.latLngBounds(pts),{padding:[28,28]});
}
function applyFilter(){ drawRoutes(); drawSavedTracks(); fitToFilter(); }''',
'''function fitToFilter(){
  const secs = SECTIONS.filter(s=>viewFilter==='all'||s.id===viewFilter);
  const bounds = new kakao.maps.LatLngBounds();
  let n=0;
  secs.forEach(s=>(REAL_ROUTES[s.id]||[]).forEach(c=>{
    if(c.start){ bounds.extend(new kakao.maps.LatLng(c.start[0],c.start[1])); n++; }
    if(c.end){ bounds.extend(new kakao.maps.LatLng(c.end[0],c.end[1])); n++; }
  }));
  if(n) map.setBounds(bounds, 28, 28, 28, 28);
  updateLabels();
}
function applyFilter(){ drawRoutes(); fitToFilter(); }''')

# 6) drawRoutes + updateLabels
a=src.index("function drawRoutes(){")
b=src.index("// 내가 걸은 길 — 진하게(opacity 1.0)")
new_dr='''function drawRoutes(){
  [...refLayers,...boundaryLayers,...labelLayers].forEach(o=>o.setMap(null));
  refLayers=[]; boundaryLayers=[]; labelLayers=[];
  SECTIONS.filter(s=>viewFilter==='all'||s.id===viewFilter).forEach(s=>{
    const done = progress[s.id] || [];
    const list = REAL_ROUTES[s.id]||[];
    const dot = pos => new kakao.maps.CustomOverlay({
      position:new kakao.maps.LatLng(pos[0],pos[1]), xAnchor:0.5, yAnchor:0.5, clickable:false,
      content:`<span class="bdot" style="border-color:${s.color}"></span>`
    });
    list.forEach(c=>{
      if(!c.segs || !c.segs.length) return;
      const walked = done.includes(c.id);
      c.segs.forEach(sg=>{
        const line = new kakao.maps.Polyline({
          path: sg.map(p=>new kakao.maps.LatLng(p[0],p[1])),
          strokeWeight: walked?6:4, strokeColor: s.color,
          strokeOpacity: walked?1:0.55, strokeStyle:'solid'
        });
        line.setMap(map);
        kakao.maps.event.addListener(line,'mousedown',()=>{
          if(selectMode){
            toggleCourse(s.id,c.id);
            const on=(progress[s.id]||[]).includes(c.id);
            toast(`${c.name} ${on?'기록됨 ✓':'해제'}`);
          } else toast(`${c.name} · ${c.km}km`);
        });
        refLayers.push(line);
      });
      boundaryLayers.push(dot(c.start));
      labelLayers.push(new kakao.maps.CustomOverlay({
        position:new kakao.maps.LatLng(c.mid[0],c.mid[1]), xAnchor:0.5, yAnchor:0.5, clickable:false,
        content:`<span class="crs-num-pill" style="border-color:${s.color};color:${s.color}">${c.no}</span>`
      }));
    });
    const last=list[list.length-1];
    if(last&&last.end) boundaryLayers.push(dot(last.end));
  });
  updateLabels();
}
function updateLabels(){
  if(!map) return;
  const lvl = map.getLevel();
  const showNum = lvl<=6, showDot = lvl<=9;
  labelLayers.forEach(o=>o.setMap(showNum?map:null));
  boundaryLayers.forEach(o=>o.setMap(showDot?map:null));
}
'''
src=src[:a]+new_dr+src[b:]

# 7) drawSavedTracks -> no-op
rep('''function drawSavedTracks(){
  savedLayers.forEach(l=>map.removeLayer(l));
  savedLayers=[];
  walks.filter(w=>viewFilter==='all'||w.secId===viewFilter).forEach(w=>{
    if(w.path && w.path.length>1){
      const c = secById(w.secId)?.color || '#333';
      const l = L.polyline(w.path,{color:c,weight:6,opacity:1,lineCap:'round',lineJoin:'round'}).addTo(map);
      savedLayers.push(l);
    }
  });
}''',
'function drawSavedTracks(){ /* GPS 경로 기록 미사용 (수동 코스 기록 방식) */ }')

# 8) tab relayout
rep("if(btn.dataset.tab==='p-map' && map) setTimeout(()=>map.invalidateSize(),120);",
    "if(btn.dataset.tab==='p-map' && map) setTimeout(()=>map.relayout(),120);")

# 9) locate button -> Kakao
rep('''/* ============ 내 위치 버튼 ============ */
document.getElementById('locateBtn').onclick=()=>{
  if(!('geolocation' in navigator)){toast('GPS 미지원');return;}
  navigator.geolocation.getCurrentPosition(p=>{
    const ll=[p.coords.latitude,p.coords.longitude];
    map.setView(ll,16); onPos(p);
  }, onPosErr, {enableHighAccuracy:true,timeout:12000});
};''',
'''/* ============ 내 위치 버튼 ============ */
function showMyLocation(lat,lng){
  const pos=new kakao.maps.LatLng(lat,lng);
  if(!meOverlay){
    meOverlay=new kakao.maps.CustomOverlay({position:pos, xAnchor:0.5, yAnchor:0.5, zIndex:5, content:'<span class="me-dot"></span>'});
  } else meOverlay.setPosition(pos);
  meOverlay.setMap(map);
  map.setCenter(pos); map.setLevel(4);
}
document.getElementById('locateBtn').onclick=()=>{
  if(!('geolocation' in navigator)){toast('GPS 미지원');return;}
  navigator.geolocation.getCurrentPosition(
    p=>showMyLocation(p.coords.latitude,p.coords.longitude),
    e=>toast('위치 접근 불가: '+(e.code===1?'권한 거부됨':'HTTPS 환경 필요')),
    {enableHighAccuracy:true,timeout:12000}
  );
};''')

# 10) focusCourse -> Kakao
rep('''function focusCourse(secId,c){
  viewFilter=secId; save(LS_SEC,viewFilter);
  document.getElementById('secFilter').value=secId;
  drawRoutes(); drawSavedTracks();
  const pts=[].concat(...c.segs);
  if(pts.length){ map.fitBounds(L.latLngBounds(pts),{padding:[50,50], maxZoom:15}); }
  L.popup({closeButton:true}).setLatLng(c.mid).setContent(`<b>${c.name}</b><br>${c.km}km`).openOn(map);
}''',
'''function focusCourse(secId,c){
  viewFilter=secId; save(LS_SEC,viewFilter);
  document.getElementById('secFilter').value=secId;
  drawRoutes();
  const bounds=new kakao.maps.LatLngBounds();
  c.segs.forEach(sg=>sg.forEach(p=>bounds.extend(new kakao.maps.LatLng(p[0],p[1]))));
  map.setBounds(bounds, 60,60,60,60);
  if(map.getLevel()<3) map.setLevel(3);
  updateLabels();
  if(courseIW) courseIW.close();
  courseIW=new kakao.maps.InfoWindow({
    position:new kakao.maps.LatLng(c.mid[0],c.mid[1]), removable:true,
    content:`<div style="padding:6px 10px;font-size:12px;font-weight:700;color:#1c2530;white-space:nowrap">${c.name} · ${c.km}km</div>`
  });
  courseIW.open(map);
}''')

# 11) init inside kakao.maps.load
rep('/* ============ 시작 ============ */\ninitMap();',
    '/* ============ 시작 ============ */\nkakao.maps.load(function(){ initMap(); });')

# 12) CSS: dot / number pill / me-dot / selmode cursor
rep('  body.selmode .leaflet-interactive{cursor:pointer}',
'''  body.selmode #map{cursor:pointer}
  .bdot{display:block; width:8px; height:8px; border-radius:50%; background:#fff;
    border:2px solid #888; box-shadow:0 0 0 1px rgba(0,0,0,.06)}
  .crs-num-pill{display:inline-flex; align-items:center; justify-content:center; background:#fff;
    border:1.5px solid; border-radius:7px; font-size:10px; font-weight:800; line-height:1;
    padding:1px 5px; box-shadow:0 1px 3px rgba(0,0,0,.28); white-space:nowrap}
  .me-dot{display:block; width:16px; height:16px; border-radius:50%; background:var(--green);
    border:3px solid #fff; box-shadow:0 0 0 2px rgba(31,122,77,.4), 0 2px 6px rgba(0,0,0,.3)}''')

open(HTML,"w",encoding="utf-8").write(src)
print("patched; bytes:",len(src))
