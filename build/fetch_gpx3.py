#!/usr/bin/env python3
import json, re, urllib.request, urllib.parse, math, sys
from concurrent.futures import ThreadPoolExecutor

UA="Mozilla/5.0 Chrome/126 Safari/537.36"
SITE="https://www.durunubi.kr"
FLAGS=[("HE","haeparang"),("NA","nampara"),("SEO","seohaerang"),("DMZ","dmz")]
SPLIT_M=700       # 원본에서 이보다 큰 점프면 선을 끊음 (페리/다리/글리치)
EPS=0.00015       # RDP 단순화 (~16m) — 해안 곡선 유지
MIN_SEG_M=40      # 이보다 짧은 조각은 버림

def get(url,timeout=45,binary=True):
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Referer":SITE+"/main.do"})
    data=urllib.request.urlopen(req,timeout=timeout).read()
    return data if binary else data.decode("utf-8","ignore")

def list_courses(flag):
    url=f"{SITE}/api/course/list?type=DNWW&serviceFlag={flag}&offset=0&size=2000&orderBy=4"
    return json.loads(get(url,binary=False))["response"]

def hav(a,b):
    R=6371000.0; dlat=math.radians(b[0]-a[0]); dlon=math.radians(b[1]-a[1])
    x=math.sin(dlat/2)**2+math.cos(math.radians(a[0]))*math.cos(math.radians(b[0]))*math.sin(dlon/2)**2
    return 2*R*math.asin(math.sqrt(x))

def seglen(sg):
    return sum(hav(sg[i],sg[i+1]) for i in range(len(sg)-1))

def perp(p,a,b):
    (x,y),(x1,y1),(x2,y2)=p,a,b
    dx,dy=x2-x1,y2-y1
    if dx==0 and dy==0: return math.hypot(x-x1,y-y1)
    t=((x-x1)*dx+(y-y1)*dy)/(dx*dx+dy*dy); t=max(0,min(1,t))
    return math.hypot(x-(x1+t*dx),y-(y1+t*dy))
def rdp(pts,eps):
    if len(pts)<3: return pts
    dmax,idx=0,0
    for i in range(1,len(pts)-1):
        d=perp(pts[i],pts[0],pts[-1])
        if d>dmax: dmax,idx=d,i
    if dmax>eps: return rdp(pts[:idx+1],eps)[:-1]+rdp(pts[idx+1:],eps)
    return [pts[0],pts[-1]]

TRKPT=re.compile(r'<(?:trkpt|rtept)\s+lat="([-\d.]+)"\s+lon="([-\d.]+)"')

def process(job):
    sec,c=job
    nm=c.get("crs_Kor_Nm","")
    m=re.search(r'(\d+)\s*코스',nm); no=int(m.group(1)) if m else 0
    try: km=float(c.get("crs_Dstnc") or 0)
    except: km=0
    src=c.get("gpx_src")
    if not src: return None
    url=f"{SITE}/editImgUp.do?filePath={urllib.parse.quote(src)}"
    try: raw=get(url).decode("utf-8","ignore")
    except Exception as e: sys.stderr.write(f"FAIL {nm}: {e}\n"); return None
    pts=[(float(a),float(b)) for a,b in TRKPT.findall(raw)]
    if len(pts)<2: return None
    # 1) 큰 점프에서 분할
    segs=[]; cur=[pts[0]]
    for i in range(1,len(pts)):
        if hav(pts[i-1],pts[i])>SPLIT_M:
            if len(cur)>=2: segs.append(cur)
            cur=[pts[i]]
        else: cur.append(pts[i])
    if len(cur)>=2: segs.append(cur)
    # 2) 각 조각 단순화 + 너무 짧은 조각 제거
    out=[]
    for sg in segs:
        if seglen(sg)<MIN_SEG_M: continue
        s2=rdp(sg,EPS)
        if len(s2)>=2: out.append([[round(a,5),round(b,5)] for a,b in s2])
    if not out: return None
    start=out[0][0]; end=out[-1][-1]
    longest=max(out,key=len); mid=longest[len(longest)//2]
    return {"sec":sec,"no":no,"name":nm,"km":km,"segs":out,
            "start":start,"mid":mid,"end":end,
            "npts":sum(len(s) for s in out),"nseg":len(out)}

def main():
    jobs=[]
    for flag,sid in FLAGS:
        cs=list_courses(flag); sys.stderr.write(f"{sid}: {len(cs)}\n")
        for c in cs: jobs.append((sid,c))
    results=[]
    with ThreadPoolExecutor(max_workers=10) as ex:
        for r in ex.map(process,jobs):
            if r: results.append(r)
    data={sid:[] for _,sid in FLAGS}
    for r in results: data[r["sec"]].append(r)
    for sid in data: data[sid].sort(key=lambda x:x["no"])
    tot=0; segtot=0
    for _,sid in FLAGS:
        arr=data[sid]; km=sum(r["km"] for r in arr)
        p=sum(r["npts"] for r in arr); sg=sum(r["nseg"] for r in arr); tot+=p; segtot+=sg
        sys.stderr.write(f"{sid}: {len(arr)} courses, {km:.0f}km, {p} pts, {sg} segs\n")
    sys.stderr.write(f"TOTAL {tot} pts, {segtot} segs\n")
    slim={sid:[{"id":i,"no":r["no"],"name":r["name"],"km":r["km"],
                "segs":r["segs"],"start":r["start"],"mid":r["mid"],"end":r["end"]}
               for i,r in enumerate(data[sid])] for sid in data}
    out="/private/tmp/claude-501/-Users-sunyoung/71dd15e2-08ee-4e14-8a9a-29986dc21730/scratchpad/real_routes.json"
    json.dump(slim,open(out,"w"),ensure_ascii=False,separators=(",",":"))
    sys.stderr.write("wrote "+out+"\n")

main()
