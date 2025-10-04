#!/usr/bin/env python3
import os, sys, json, re, argparse, datetime as dt
from zoneinfo import ZoneInfo
try:
    import swisseph as swe
except Exception:
    print("ERR: install pyswisseph in astroenv (pip install pyswisseph)", file=sys.stderr); sys.exit(2)

ASP = {0:"☌",60:"✶",90:"□",120:"△",180:"☍"}
P2S = {"Sun":swe.SUN,"Moon":swe.MOON,"Mercury":swe.MERCURY,"Venus":swe.VENUS,"Mars":swe.MARS,"Jupiter":swe.JUPITER,"Saturn":swe.SATURN,"Uranus":swe.URANUS,"Neptune":swe.NEPTUNE,"Pluto":swe.PLUTO}
TARGETS = ["Sun","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto","NNode","ASC","MC","DSC","IC"]

def tz_hint_to_offset(s: str|None) -> str:
    if not s: return "+00:00"
    s=s.strip()
    if s.startswith("UTC"):
        tail=s[3:].strip() or "+0"
        m=re.match(r'([+\-]?\d{1,2})(?::?(\d{2}))?$', tail)
        if m: 
            h=int(m.group(1)); mm=int(m.group(2) or 0)
            return f"{h:+03d}:{mm:02d}"
    if s.startswith("Etc/GMT"):
        m=re.match(r'Etc/GMT([+\-]\d{1,2})', s)
        if m:
            h=int(m.group(1)); h=-h
            return f"{h:+03d}:00"
    return "+00:00"

def jd_iso(s: str) -> float:
    s=s.replace("Z","+00:00")
    if "T" not in s: s+="T12:00:00+00:00"
    t=dt.datetime.fromisoformat(s); u=t.astimezone(dt.timezone.utc)
    return swe.julday(u.year,u.month,u.day,u.hour+u.minute/60.0+u.second/3600.0)

def jd_from_local_iso(date_s: str, tz_hint: str|None) -> float:
    if "T" in date_s and ("+" in date_s or "Z" in date_s):
        return jd_iso(date_s)
    off=tz_hint_to_offset(tz_hint)
    if "T" not in date_s: date_s+="T12:00:00"
    return jd_iso(date_s+off)

def iso_utc_from_jd(jd: float) -> str:
    y,m,d,fr = swe.revjul(jd, swe.GREG_CAL)
    base = dt.datetime(y,m,d,tzinfo=dt.timezone.utc)
    dt_utc = base + dt.timedelta(seconds=fr*86400.0)
    return dt_utc.replace(second=0, microsecond=0).isoformat()

def houses_axes(jd: float, lat: float, lon: float):
    _h = swe.houses_ex2(jd, lat, lon, b'T')  # Topocentric
    return _h[0], _h[1]

def lon_ut(jd: float, name: str, lat: float, lon: float) -> float|None:
    flag = swe.FLG_SWIEPH|swe.FLG_TOPOCTR|swe.FLG_SPEED
    if name in P2S:
        return swe.calc_ut(jd, P2S[name], flag)[0][0]%360.0
    cusps, ascmc = houses_axes(jd, lat, lon)
    if name=="ASC": return ascmc[swe.ASC]%360.0
    if name=="MC":  return ascmc[swe.MC]%360.0
    if name=="DSC": return (ascmc[swe.ASC]+180.0)%360.0
    if name=="IC":  return (ascmc[swe.MC]+180.0)%360.0
    if name=="NNode": return swe.calc_ut(jd, swe.MEAN_NODE, flag)[0][0]%360.0
    return None

def norm180(x: float) -> float: return (x+180.0)%360.0 - 180.0

def read_forpush_seen(path: str) -> set[tuple[str,int]]:
    try:
        j=json.load(open(path,'r',encoding='utf-8'))
    except Exception:
        return set()
    ev=j if isinstance(j,list) else j.get('events') or []
    seen=set()
    for e in ev:
        a = next((k for k,v in ASP.items() if v==e.get('aspect')), None)
        if a is None: continue
        t=e.get('target'); 
        if t: seen.add((t,a))
        for t2 in (e.get('targets') or []):
            seen.add((t2,a))
    return seen

def load_natal(path: str, birth_o=None, lat_o=None, lon_o=None, tz_o=None):
    if birth_o and lat_o is not None and lon_o is not None:
        return str(birth_o), str(tz_o or "UTC"), float(lat_o), float(lon_o)
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
                r=walk_num(v,keys)
                if r: return r
        if isinstance(d,list):
            for it in d:
                r=walk_num(it,keys)
                if r: return r
        return {}
    birth = pick(j,'birth','birth_iso','birth_dt') or pick(j.get('meta',{}),'birth','datetime','date')
    tz = pick(j,'tz','timezone') or pick(j.get('meta',{}),'tz','timezone') or "UTC"
    nums = walk_num(j, ['lat','latitude','lon','lng','longitude'])
    lat = nums.get('lat') or nums.get('latitude')
    lon = nums.get('lon') or nums.get('lng') or nums.get('longitude')
    if not (birth and lat and lon):
        raise ValueError("natal loader: missing birth/lat/lon")
    return str(birth), str(tz), float(lat), float(lon)

if __name__=="__main__":
    ap=argparse.ArgumentParser(description="QA lunar angle-coverage (offline, topo)")
    ap.add_argument("--natal", default=os.environ.get("NATAL_JSON") or os.path.expanduser("~/astro/.state/natal_frame.json"))
    ap.add_argument("--birth"); ap.add_argument("--lat", type=float); ap.add_argument("--lon", type=float); ap.add_argument("--tzhint")
    ap.add_argument("--from", dest="FROM", required=True); ap.add_argument("--to", dest="TO", required=True)
    ap.add_argument("--orb_conj", type=float, default=float(os.environ.get("ORB_CONJ","2.0")))
    ap.add_argument("--orb_other", type=float, default=float(os.environ.get("ORB_OTHER","1.0")))
    ap.add_argument("--aspects", default=os.environ.get("ASPECTS","0,60,90,120,180"))
    ap.add_argument("--step_min", type=int, default=int(os.environ.get("STEP_MIN","2")))
    ap.add_argument("--forpush", default=os.path.expanduser("~/astro/lunar_natal_forpush.json"))
    args=ap.parse_args()

    birth, tz_hint, LAT, LON = load_natal(args.natal, args.birth, args.lat, args.lon, args.tzhint)
    swe.set_ephe_path(os.environ.get("SWEPH","")); swe.set_topo(LON, LAT, 0.0)

    jd_b = jd_from_local_iso(birth, tz_hint)
    jd0 = jd_iso(args.FROM); jd1 = jd_iso(args.TO); step = args.step_min/1440.0
    aspects = [int(x) for x in re.split(r"[,\s]+", args.aspects) if x]
    seen = read_forpush_seen(args.forpush)

    # nat longitudes (topo)
    natal_lon = {t: lon_ut(jd_b, t, LAT, LON) for t in TARGETS if t!="Moon"}

    # scan
    min_d={}; jd=jd0
    while jd<=jd1+1e-9:
        m = lon_ut(jd, "Moon", LAT, LON)
        for t, nt in natal_lon.items():
            if nt is None: continue
            for a in aspects:
                d = abs(norm180((m - nt) - a))
                key=(t,a)
                if key not in min_d or d<min_d[key][0]: min_d[key]=(d,jd)
        jd+=step

    miss=[]
    for (t,a),(d,jd) in sorted(min_d.items()):
        need = args.orb_conj if a==0 else args.orb_other
        if d<=need and (t,a) not in seen:
            miss.append((t, ASP[a], d, iso_utc_from_jd(jd)))
    print(f"QA: {'PASS' if not miss else 'FAIL'} | window {args.FROM}..{args.TO}")
    if miss:
        for t,ch,d,t_utc in miss[:20]:
            print(f"- MISSING {ch} Moon–{t}: minΔ={d:.2f}° near {t_utc}")
