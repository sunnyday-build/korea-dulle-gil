#!/usr/bin/env python3
import json
HTML="/Users/sunyoung/korea-dulle-gil/index.html"
JSONF="/private/tmp/claude-501/-Users-sunyoung/71dd15e2-08ee-4e14-8a9a-29986dc21730/scratchpad/real_routes.json"
routes_js=json.dumps(json.load(open(JSONF,encoding="utf-8")),ensure_ascii=False,separators=(",",":"))
src=open(HTML,encoding="utf-8").read()

def rep(old,new,n=1):
    global src
    assert old in src, "NOT FOUND:\n"+old[:200]
    src=src.replace(old,new,n)

# R1: swap REAL_ROUTES data (segmented)
a=src.index("const REAL_ROUTES = ")
b=src.index(";\n\nconst SECMETA",a)
src=src[:a]+"const REAL_ROUTES = "+routes_js+src[b:]

# R2: SECTIONS start from c.start
rep("  const start = (arr[0] && arr[0].pts && arr[0].pts[0]) || [36.5,127.8];",
    "  const start = (arr[0] && arr[0].start) || [36.5,127.8];")

# R3: rewrite drawRoutes (multiline + boundary dots + number labels)
old_dr_start=src.index("function drawRoutes(){")
old_dr_end=src.index("\n// 내가 걸은 길", old_dr_start)
new_dr='''function drawRoutes(){
  [...refLayers,...boundaryLayers,...labelLayers].forEach(l=>map.removeLayer(l));
  refLayers=[]; boundaryLayers=[]; labelLayers=[];
  SECTIONS.filter(s=>viewFilter==='all'||s.id===viewFilter).forEach(s=>{
    const done = progress[s.id] || [];
    const list = REAL_ROUTES[s.id]||[];
    list.forEach(c=>{
      if(!c.segs || !c.segs.length) return;
      const walked = done.includes(c.id);
      const l=L.polyline(c.segs,{
        color: s.color, weight: walked?6:4, opacity: walked?1:.55,
        lineCap:'round', lineJoin:'round'
      }).addTo(map);
      l.on('click',()=>{
        if(selectMode){
          toggleCourse(s.id,c.id);
          const on=(progress[s.id]||[]).includes(c.id);
          toast(`${c.name} ${on?'기록됨 ✓':'해제'}`);
        }else toast(`${c.name} · ${c.km}km`);
      });
      refLayers.push(l);
      // 코스 시작점 = 코스 경계
      boundaryLayers.push(L.circleMarker(c.start,{radius:3.5,color:s.color,weight:2,fillColor:'#fff',fillOpacity:1,interactive:false}).addTo(map));
      // 코스 번호 라벨 (확대 시에만)
      labelLayers.push(L.marker(c.mid,{interactive:false,keyboard:false,icon:L.divIcon({
        className:'crs-num', iconSize:[26,18], iconAnchor:[13,9],
        html:`<span style="border-color:${s.color};color:${s.color}">${c.no}</span>`
      })}));
    });
    const last=list[list.length-1];
    if(last&&last.end) boundaryLayers.push(L.circleMarker(last.end,{radius:3.5,color:s.color,weight:2,fillColor:'#fff',fillOpacity:1,interactive:false}).addTo(map));
  });
  updateLabels();
}
function updateLabels(){
  if(!map) return;
  const show = map.getZoom() >= 11;
  labelLayers.forEach(l=>{
    const on=map.hasLayer(l);
    if(show&&!on) l.addTo(map);
    else if(!show&&on) map.removeLayer(l);
  });
}'''
src=src[:old_dr_start]+new_dr+src[old_dr_end:]

# R4: fitToFilter uses start/end
rep('''  secs.forEach(s=>(REAL_ROUTES[s.id]||[]).forEach(c=>{
    if(c.pts&&c.pts.length){ pts.push(c.pts[0], c.pts[c.pts.length-1]); }
  }));''',
'''  secs.forEach(s=>(REAL_ROUTES[s.id]||[]).forEach(c=>{
    if(c.start&&c.end){ pts.push(c.start, c.end); }
  }));''')

# R5: initMap zoomend -> updateLabels
rep("  }).addTo(map);\n  drawRoutes();       // 코스별 실측 경로 (선택 구간만)",
    "  }).addTo(map);\n  map.on('zoomend', updateLabels);\n  drawRoutes();       // 코스별 실측 경로 (선택 구간만)")

# R6: locate button icon -> inline crosshair SVG
rep('<button class="locate-btn" id="locateBtn" title="내 위치">◎</button>',
    '<button class="locate-btn" id="locateBtn" title="내 위치" aria-label="내 위치">'
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">'
    '<circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2.2" fill="currentColor" stroke="none"/>'
    '<line x1="12" y1="1.5" x2="12" y2="4.5"/><line x1="12" y1="19.5" x2="12" y2="22.5"/>'
    '<line x1="1.5" y1="12" x2="4.5" y2="12"/><line x1="19.5" y1="12" x2="22.5" y2="12"/></svg></button>')

# R7a: legend down to clear 2-row overlay
rep("position:absolute; left:12px; top:calc(56px + var(--safe-t)); z-index:500;",
    "position:absolute; left:12px; top:calc(96px + var(--safe-t)); z-index:500;")

# R7b: append CSS (labels, locate svg, search)
rep("  body.selmode .leaflet-interactive{cursor:pointer}",
'''  body.selmode .leaflet-interactive{cursor:pointer}
  .locate-btn svg{width:24px;height:24px;color:var(--green);display:block}
  .crs-num{background:none;border:none}
  .crs-num span{display:inline-flex;align-items:center;justify-content:center;background:#fff;
    border:1.5px solid; border-radius:7px; font-size:10px; font-weight:800; line-height:1;
    padding:1px 5px; box-shadow:0 1px 3px rgba(0,0,0,.28); white-space:nowrap}
  .search-wrap{position:relative; flex:1; min-width:110px; pointer-events:auto}
  .search-input{width:100%; border:1px solid var(--line); border-radius:999px; padding:8px 14px;
    font-size:13px; font-family:inherit; background:rgba(255,255,255,.94); color:var(--ink);
    box-shadow:0 2px 10px rgba(0,0,0,.1); -webkit-appearance:none; appearance:none}
  .search-results{position:absolute; top:calc(100% + 6px); left:0; right:0; background:#fff;
    border:1px solid var(--line); border-radius:12px; box-shadow:0 8px 26px rgba(0,0,0,.18);
    max-height:46vh; overflow-y:auto; display:none; z-index:600}
  .sr-item{display:flex; align-items:center; gap:8px; padding:11px 13px; font-size:13px;
    font-weight:600; cursor:pointer; border-bottom:1px solid var(--line)}
  .sr-item:last-child{border-bottom:none}
  .sr-item i{width:9px; height:9px; border-radius:50%; flex:0 0 auto}
  .sr-item span{margin-left:auto; color:var(--muted); font-weight:700; font-size:11px}
  .sr-empty{padding:16px; text-align:center; color:var(--muted); font-size:12px}''')

# R8a: add search box HTML after the filter dropdown
rep('''        </select>
        <div class="chip rec" id="recChip" style="display:none">''',
'''        </select>
        <div class="search-wrap">
          <input id="searchInput" class="search-input" type="search" placeholder="걸은 코스 검색" autocomplete="off" />
          <div class="search-results" id="searchResults"></div>
        </div>
        <div class="chip rec" id="recChip" style="display:none">''')

# R8b: add search JS (walked-course search -> focus one course)
rep("/* ============ 시작 ============ */",
'''/* ============ 걸은 코스 검색 ============ */
function walkedCourses(){
  const res=[];
  SECTIONS.forEach(s=>{
    const done=progress[s.id]||[];
    (REAL_ROUTES[s.id]||[]).forEach(c=>{ if(done.includes(c.id)) res.push({s,c}); });
  });
  return res;
}
function focusCourse(secId,c){
  viewFilter=secId; save(LS_SEC,viewFilter);
  document.getElementById('secFilter').value=secId;
  drawRoutes(); drawSavedTracks();
  const pts=[].concat(...c.segs);
  if(pts.length){ map.fitBounds(L.latLngBounds(pts),{padding:[50,50], maxZoom:15}); }
  L.popup({closeButton:true}).setLatLng(c.mid).setContent(`<b>${c.name}</b><br>${c.km}km`).openOn(map);
}
(function setupSearch(){
  const si=document.getElementById('searchInput'), sr=document.getElementById('searchResults');
  si.oninput=()=>{
    const q=si.value.trim().toLowerCase();
    if(!q){ sr.style.display='none'; sr.innerHTML=''; return; }
    const list=walkedCourses().filter(({s,c})=>(s.name+' '+c.no+'코스 '+c.name).toLowerCase().includes(q));
    if(!list.length){ sr.innerHTML='<div class="sr-empty">걸은 코스 중 검색 결과가 없어요</div>'; sr.style.display=''; return; }
    sr.innerHTML=list.slice(0,25).map(({s,c})=>
      `<div class="sr-item" data-s="${s.id}" data-c="${c.id}"><i style="background:${s.color}"></i>${s.name} ${c.no}코스<span>${c.km}km</span></div>`).join('');
    sr.style.display='';
    sr.querySelectorAll('.sr-item').forEach(el=>el.onclick=()=>{
      const s=secById(el.dataset.s);
      const c=(REAL_ROUTES[s.id]||[]).find(x=>String(x.id)===el.dataset.c);
      if(c) focusCourse(s.id,c);
      sr.style.display='none'; si.value=''; si.blur();
    });
  };
  document.addEventListener('click',e=>{ if(!e.target.closest('.search-wrap')) sr.style.display='none'; });
})();

/* ============ 시작 ============ */''')

open(HTML,"w",encoding="utf-8").write(src)
print("patched; bytes:",len(src))
