#!/usr/bin/env python3
# QA transits angle-coverage (Medium/Long): офлайн, topo
import os, sys, json, re, argparse, datetime as dt
from zoneinfo import ZoneInfo
try:
    import swisseph as swe
except Exception:
    print("ERR: install pyswisseph in astroenv (pip install pyswisseph)", file=sys.stderr); sys.exit(2)

ASP = {0:"☌",60:"✶",90:"□",120:"△",180:"☍"}
P2S = {"Sun":swe.SUN,"Moon":swe.MOON,"Mercury":swe.MERCURY,"Venus":swe.VENUS,"Mars":swe.MARS,
       "Jupiter":swe.JUPITER,"Saturn":swe.SATURN,"Uranus":swe.URANUS,"Neptune":swe.NEPTUNE,"Pluto":swe.PLUTO}
TARGETS = ["Sun","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto","NNode","ASC","MC","DSC","IC"]

def tz_hint_to_offset(s):
    if not s: return "+00:00"
    s=s.strip()
    if s.startswith("UTC"):
        tail=s[3:].strip() or "+0"
        m=re.match(r'([+\-]?\d{1,2})(?::?(\d{2}))?$', tail)
        if m: 
            h=int(m.group(1)); mm=int(m.group(2) or 0); return f"{h:+03d}:{mm:02d}"
    if s.startswith("Etc/GMT"):
        m=re.match(r'Etc/GMT([+\-]\d{1,2})', s)
        if m: h=-int(m.group(1)); return f"{h:+03d}:00"
    return "+00:00"

def jd_iso(s):
    s=s.replace("Z","+00:00")
    if "T" not in s: s+="T12:00:00+00:00"
    t=dt.datetime.fromisoformat(s); u=t.astimezone(dt.timezone.utc)
    return swe.julday(u.year,u.month,u.day, u.hour+u.minute/60.0+u.second/3600.0)

def jd_from_local(birth, tz_hint):
    if "T" in birth and ("+" in birth or "Z" in birth): return jd_iso(birth)
    off=tz_hint_to_offset(tz_hint)
    if "T" not in birth: birth+="T12:00:00"
    return jd_iso(birth+off)

def iso_utc_from_jd(jd):
    y,m,d,fr = swe.revjul(jd, swe.GREG_CAL)
    base = dt.datetime(y,m,d,tzinfo=dt.timezone.utc)
    t_utc = base + dt.timedelta(seconds=fr*86400.0)
    return t_utc.replace(second=0, microsecond=0).isoformat()

def lon_ut(jd, name, lat, lon):
    flag=swe.FLG_SWIEPH|swe.FLG_TOPOCTR|swe.FLG_SPEED
    if name in P2S: return swe.calc_ut(jd,P2S[name],flag)[0][0]%360.0
    # Axes (Topocentric houses)
    h=swe.houses_ex2(jd, lat, lon, b'T'); ascmc=h[1]
    if name=="ASC": return ascmc[swe.ASC]%360.0
    if name=="MC":  return ascmc[swe.MC]%360.0
    if name=="DSC": return (ascmc[swe.ASC]+180.0)%360.0
    if name=="IC":  return (ascmc[swe.MC]+180.0)%360.0
    if name=="NNode": return swe.calc_ut(jd, swe.MEAN_NODE, flag)[0][0]%360.0
    return None

def norm180(x): return (x+180.0)%360.0 - 180.0

def load_natal(path, birth_o=None, lat_o=None, lon_o=None, tz_o=None):
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
                r=walk_num(v,keys); 
                if r: return r
        if isinstance(d,list):
            for it in d:
                r=walk_num(it,keys)
                if r: return r
        return {}
    birth = pick(j,'birth','birth_iso','birth_dt') or pick(j.get('meta',{}),'birth','datetime','date')
    tz    = pick(j,'tz','timezone') or pick(j.get('meta',{}),'tz','timezone') or "UTC"
    nums  = walk_num(j, ['lat','latitude','lon','lng','longitude']) or {}
    lat   = nums.get('lat') or nums.get('latitude')
    lon   = nums.get('lon') or nums.get('lng') or nums.get('longitude')
    if not (birth and lat and lon): raise ValueError("natal loader: missing birth/lat/lon")
    return str(birth), str(tz), float(lat), float(lon)

def read_seen(path):
    j=json.load(open(path,'r',encoding='utf-8'))
    ev=j if isinstance(j,list) else j.get('events') or []
    seen=set()
    for e in ev:
        tr=e.get('transit'); asp=e.get('aspect'); t=e.get('target'); tgs=e.get('targets') or []
        a = next((k for k,v in ASP.items() if v==asp), None)
        if tr and a is not None:
            if t: seen.add((tr,t,a))
            for t2 in tgs: seen.add((tr,t2,a))
    return seen

if __name__=="__main__":
    ap=argparse.ArgumentParser(description="QA Medium/Long: angle-coverage (offline, topo)")
    ap.add_argument("--natal", default=os.environ.get("NATAL_JSON") or os.path.expanduser("~/astro/.state/natal_frame.json"))
    ap.add_argument("--birth"); ap.add_argument("--lat", type=float); ap.add_argument("--lon", type=float); ap.add_argument("--tzhint")
    ap.add_argument("--from", dest="FROM", required=True); ap.add_argument("--to", dest="TO", required=True)
    ap.add_argument("--bodies", default="Sun,Mercury,Venus,Mars")   # Medium по умолчанию
    ap.add_argument("--aspects", default="0,60,90,120,180")
    ap.add_argument("--orb_conj", type=float, default=1.5)          # Medium дефолты
    ap.add_argument("--orb_other", type=float, default=1.0)
    ap.add_argument("--step_min", type=int, default=5)
    ap.add_argument("--json", required=True, help="events JSON (for_ics/forpush)")
    args=ap.parse_args()

    birth, tz_hint, LAT, LON = load_natal(args.natal, args.birth, args.lat, args.lon, args.tzhint)
    swe.set_ephe_path(os.environ.get("SWEPH","")); swe.set_topo(LON, LAT, 0.0)
    jd_b = jd_from_local(birth, tz_hint)
    jd0 = jd_iso(args.FROM); jd1 = jd_iso(args.TO); step = args.step_min/1440.0
    bodies=[b.strip() for b in args.bodies.split(",") if b.strip()]
    aspects=[int(x) for x in re.split(r"[,\s]+", args.aspects) if x]

    # nat longitudes (topo)
    natal_lon={t: lon_ut(jd_b, t, LAT, LON) for t in TARGETS if t!="Moon"}

    seen = read_seen(args.json)
    miss={}  # key=(tr,tar,a) -> (d,jd)
    jd = jd0
    while jd<=jd1+1e-9:
        for tr in bodies:
            lon_tr = lon_ut(jd, tr, LAT, LON)
            if lon_tr is None: continue
            for tar, nt in natal_lon.items():
                if nt is None: continue
                for a in aspects:
                    d = abs(norm180((lon_tr - nt) - a))
                    need = args.orb_conj if a==0 else args.orb_other
                    if d<=need and (tr,tar,a) not in seen:
                        if (tr,tar,a) not in miss or d < miss[(tr,tar,a)][0]:
                            miss[(tr,tar,a)] = (d,jd)
        jd+=step

    print(f"QA: {'PASS' if not miss else 'FAIL'} | {args.FROM}..{args.TO} | bodies={','.join(bodies)}")
    for (tr,tar,a),(d,jd) in list(miss.items())[:20]:
        print(f"- MISSING {tr} {ASP[a]} {tar}: minΔ={d:.2f}° near {iso_utc_from_jd(jd)}")
    if len(miss)>20: print(f"... and {len(miss)-20} more")
