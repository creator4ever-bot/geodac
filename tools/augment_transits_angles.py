#!/usr/bin/env python3
# Augment Medium/Long JSON: офлайн добивает недостающие аспекты (topo), без дублей.
import os, sys, json, re, argparse, datetime as dt
from zoneinfo import ZoneInfo
try:
    import swisseph as swe
except Exception:
    print("ERR: install pyswisseph in astroenv (pip install pyswisseph)", file=sys.stderr); sys.exit(2)

ASP = {0:"☌",60:"✶",90:"□",120:"△",180:"☍"}; ASP_LIST=[0,60,90,120,180]
P2S={"Sun":swe.SUN,"Moon":swe.MOON,"Mercury":swe.MERCURY,"Venus":swe.VENUS,"Mars":swe.MARS,
     "Jupiter":swe.JUPITER,"Saturn":swe.SATURN,"Uranus":swe.URANUS,"Neptune":swe.NEPTUNE,"Pluto":swe.PLUTO}
TGT=["Sun","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto","NNode","ASC","MC","DSC","IC"]
SIGNS=["ARIES","TAURUS","GEMINI","CANCER","LEO","VIRGO","LIBRA","SCORPIO","SAGITTARIUS","CAPRICORN","AQUARIUS","PISCES"]
EMO={"Sun":"☉","Moon":"☽","Mercury":"☿","Venus":"♀","Mars":"♂","Jupiter":"♃","Saturn":"♄","Uranus":"♅","Neptune":"♆","Pluto":"♇",
     "ASC":"ASC","MC":"MC","DSC":"DSC","IC":"IC","NNode":"☊"}
def norm180(x): return (x+180)%360-180
def norm360(x): return x%360
def sign_name(lon): return SIGNS[int(norm360(lon)//30)%12]
def tz_hint_to_offset(s):
    if not s: return "+00:00"
    s=s.strip()
    if s.startswith("UTC"):
        tail=s[3:].strip() or "+0"; m=re.match(r'([+\-]?\d{1,2})(?::?(\d{2}))?$', tail)
        if m: h=int(m.group(1)); mm=int(m.group(2) or 0); return f"{h:+03d}:{mm:02d}"
    if s.startswith("Etc/GMT"):
        m=re.match(r'Etc/GMT([+\-]\d{1,2})', s); 
        if m: h=-int(m.group(1)); return f"{h:+03d}:00"
    return "+00:00"
def jd_iso(s):
    s=s.replace("Z","+00:00"); 
    if "T" not in s: s+="T12:00:00+00:00"
    t=dt.datetime.fromisoformat(s); u=t.astimezone(dt.timezone.utc)
    return swe.julday(u.year,u.month,u.day, u.hour+u.minute/60+u.second/3600)
def jd_from_local(birth,tzhint):
    if "T" in birth and ("+" in birth or "Z" in birth): return jd_iso(birth)
    off=tz_hint_to_offset(tzhint); 
    if "T" not in birth: birth+="T12:00:00"
    return jd_iso(birth+off)
def iso_loc(jd, tz):
    y,m,d,fr=swe.revjul(jd, swe.GREG_CAL); base=dt.datetime(y,m,d,tzinfo=dt.timezone.utc)
    t=base+dt.timedelta(seconds=fr*86400); return t.astimezone(ZoneInfo(tz)).strftime("%Y-%m-%d %H:%M")
def houses_axes(jd, lat, lon):
    h=swe.houses_ex2(jd, lat, lon, b'T'); ascmc=h[1]; 
    return ascmc[swe.ASC]%360, ascmc[swe.MC]%360
def lon_ut(jd,name,lat,lon):
    flag=swe.FLG_SWIEPH|swe.FLG_TOPOCTR|swe.FLG_SPEED
    if name in P2S: return swe.calc_ut(jd, P2S[name], flag)[0][0]%360
    asc,mc = houses_axes(jd, lat, lon)
    if name=="ASC": return asc
    if name=="DSC": return (asc+180)%360
    if name=="MC": return mc
    if name=="IC": return (mc+180)%360
    if name=="NNode": return swe.calc_ut(jd, swe.MEAN_NODE, flag)[0][0]%360
    return None
def det_id(style,tr,tar,adeg,s,e):
    import hashlib; key=f"{style}|{tr}|{tar}|{adeg}|{s}|{e}"; return hashlib.sha1(key.encode()).hexdigest()
def summarize(tr,adeg,tar,nh,trh):
    tail=f" (из H{nh} к H{trh})" if nh not in (None,trh) else (f" (H{trh})" if trh is not None else "")
    return f"{EMO.get(tr,tr)} {ASP[adeg]} {EMO.get(tar,tar)}{tail}"
def load_natal(path,birth_o=None,lat_o=None,lon_o=None,tz_o=None):
    if birth_o and lat_o is not None and lon_o is not None: return str(birth_o), str(tz_o or "UTC"), float(lat_o), float(lon_o)
    j=json.load(open(path,'r',encoding='utf-8'))
    def pick(d,*keys): 
        for k in keys:
            if isinstance(d,dict) and d.get(k) not in (None,""): return d[k]
        return None
    def walk_num(d, keys):
        if isinstance(d,dict):
            got={k:d.get(k) for k in keys if d.get(k) not in (None,"")}
            if got: return got
            for v in d.values():
                r=walk_num(v,keys); 
                if r: return r
        if isinstance(d,list):
            for it in d:
                r=walk_num(it,keys)
                if r: return r
        return {}
    birth = pick(j,'birth','birth_iso','birth_dt') or pick(j.get('meta',{}),'birth','datetime','date')
    tz = pick(j,'tz','timezone') or pick(j.get('meta',{}),'tz','timezone') or "UTC"
    nums = walk_num(j,['lat','latitude','lon','lng','longitude']) or {}
    lat = nums.get('lat') or nums.get('latitude'); lon= nums.get('lon') or nums.get('lng') or nums.get('longitude')
    if not (birth and lat and lon): raise ValueError("natal loader: missing birth/lat/lon")
    return str(birth), str(tz), float(lat), float(lon)

def main():
    ap=argparse.ArgumentParser(description="augment Medium/Long by geometry (offline, topo)")
    ap.add_argument("--natal", default=os.environ.get("NATAL_JSON") or os.path.expanduser("~/astro/.state/natal_frame.json"))
    ap.add_argument("--birth"); ap.add_argument("--lat", type=float); ap.add_argument("--lon", type=float); ap.add_argument("--tzhint")
    ap.add_argument("--from", dest="FROM", required=True); ap.add_argument("--to", dest="TO", required=True)
    ap.add_argument("--bodies", default="Sun,Mercury,Venus,Mars")
    ap.add_argument("--aspects", default="0,60,90,120,180")
    ap.add_argument("--orb_conj", type=float, default=1.5)
    ap.add_argument("--orb_other", type=float, default=1.0)
    ap.add_argument("--step_min", type=int, default=5)
    ap.add_argument("--json_in", required=True); ap.add_argument("--json_out", required=True)
    args=ap.parse_args()

    birth, tz_hint, LAT, LON = load_natal(args.natal, args.birth, args.lat, args.lon, args.tzhint)
    swe.set_ephe_path(os.environ.get("SWEPH","")); swe.set_topo(LON, LAT, 0.0)
    jd_b=jd_from_local(birth, tz_hint); 
    # натальные долготы
    natal_lon={}
    for t in TGT:
        if t in P2S: natal_lon[t]=lon_ut(jd_b,t,LAT,LON)
        elif t=="NNode": natal_lon[t]=lon_ut(jd_b,"NNode",LAT,LON)
        else: natal_lon[t]=lon_ut(jd_b,t,LAT,LON)
    bodies=[b.strip() for b in args.bodies.split(",") if b.strip()]
    aspects=[int(x) for x in re.split(r"[,\s]+", args.aspects) if x]
    jd0=jd_iso(args.FROM); jd1=jd_iso(args.TO); step=args.step_min/1440.0

    # текущие события (пики)
    J=json.load(open(args.json_in,'r',encoding='utf-8')); EV=J if isinstance(J,list) else J.get('events') or []
    def parse_loc(s): return dt.datetime.fromisoformat(s+":00").replace(tzinfo=ZoneInfo("Europe/Moscow"))
    peaks={}
    for e in EV:
        tr=e.get('transit'); tar=e.get('target') or ""
        a = next((k for k,v in ASP.items() if v==e.get('aspect')), None)
        if not tr or a is None: continue
        pk=parse_loc(e.get('peak') or e.get('start')); peaks.setdefault((tr,tar,a), []).append(pk)

    need_ev=[]
    state={}
    jd=jd0
    while jd<=jd1+1e-9:
        for tr in bodies:
            lt=lon_ut(jd,tr,LAT,LON); 
            if lt is None: continue
            for tar,nt in natal_lon.items():
                if tar=="Moon" or nt is None: continue
                for a in aspects:
                    orb = args.orb_conj if a==0 else args.orb_other
                    d=abs(norm180((lt-nt)-a))
                    key=(tr,tar,a)
                    inside, st, best_jd, best_d = state.get(key,(False,None,None,999.0))
                    if inside:
                        if d<best_d: best_d=d; best_jd=jd
                        if d>orb:
                            # finalize
                            pk = dt.datetime.fromisoformat(iso_loc(best_jd or st, "Europe/Moscow")+":00")
                            # если в исходном JSON уже есть пик +- 6ч — не добавляем
                            exists=any(abs((pk - x).total_seconds())<=21600 for x in peaks.get(key,[]))
                            if not exists:
                                # старт/конец вокруг пика — пройдёмся в обе стороны
                                def expand(from_jd, dir):
                                    j=from_jd
                                    while True:
                                        j2=j + dir*(args.step_min/1440.0)
                                        d2=abs(norm180((lon_ut(j2,tr,LAT,LON)-nt)-a))
                                        if d2>orb: return j
                                        j=j2
                                jd_start=expand(best_jd or st, -1); jd_end=expand(best_jd or st, +1)
                                start=iso_loc(jd_start, "Europe/Moscow"); end=iso_loc(jd_end, "Europe/Moscow"); peak=iso_loc(best_jd or st, "Europe/Moscow")
                                # дом транзитной планеты по натальной сетке
                                asc,mc=houses_axes(best_jd or st, LAT, LON); # только для осей; для домов возьмём приближённо H по asc,mc не критично
                                trh=None
                                # new event
                                e={"transit":tr,"target":tar,"aspect":ASP[a],"aspect_deg":a,
                                   "orb_peak_deg":round(best_d,3),
                                   "houses":{"tr":trh,"nat":None},
                                   "signs":{"tr":None,"nat":None},
                                   "start":start,"peak":peak,"end":end}
                                need_ev.append(e)
                            inside=False; st=None; best_jd=None; best_d=999.0
                    else:
                        if d<=orb: inside=True; st=jd; best_jd=jd; best_d=d
                    state[key]=(inside,st,best_jd,best_d)
        jd+=step

    # слить
    out = EV + need_ev
    # оформить newstyle
    for e in out:
        nh=None; trh=None
        e["summary"]=summarize(e["transit"], e["aspect_deg"], e["target"], nh, trh)
        head=f"Профессиональный разбор: {e['transit']} {e['aspect']} {e['target']}"
        desc=e.get("description") or ""; 
        if "Профессиональный разбор" not in desc: desc=head+("\n"+desc if desc else "")
        e["description"]=desc
        s=e["start"]; en=e["end"]
        if en<=s:
            # guard
            t0=dt.datetime.fromisoformat(s+":00").replace(tzinfo=ZoneInfo("Europe/Moscow"))
            e["end"]=(t0+dt.timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M")

    with open(args.json_out,'w',encoding='utf-8') as g:
        json.dump(out,g,ensure_ascii=False,indent=2)
    print("added events:", len(need_ev), " | total:", len(out))
