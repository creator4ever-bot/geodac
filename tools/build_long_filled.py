#!/usr/bin/env python3
# Build Long filled.json (topo, safe): добивает недостающие аспекты Jupiter..Pluto к наталу; завершает "внутри орба" на границе окна.
import os, sys, json, re, datetime as dt
from zoneinfo import ZoneInfo
try:
    import swisseph as swe
except Exception:
    print("ERR: install pyswisseph in astroenv (pip install pyswisseph)", file=sys.stderr); sys.exit(2)

ASP = {0:"☌",60:"✶",90:"□",120:"△",180:"☍"}
P2S = {"Jupiter":swe.JUPITER,"Saturn":swe.SATURN,"Uranus":swe.URANUS,"Neptune":swe.NEPTUNE,"Pluto":swe.PLUTO}
AXES = ["ASC","MC","DSC","IC"]
TARGETS = ["Sun","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto","NNode"] + AXES
EMO={"Sun":"☉","Mercury":"☿","Venus":"♀","Mars":"♂","Jupiter":"♃","Saturn":"♄","Uranus":"♅","Neptune":"♆","Pluto":"♇",
     "ASC":"ASC","MC":"MC","DSC":"DSC","IC":"IC","NNode":"☊"}

def norm180(x): return (x+180)%360-180
def tz_hint_to_offset(s):
    if not s: return "+00:00"
    s=s.strip()
    if s.startswith("UTC"):
        tail=s[3:].strip() or "+0"; m=re.match(r'([+\-]?\d{1,2})(?::?(\d{2}))?$', tail)
        if m: h=int(m.group(1)); mm=int(m.group(2) or 0); return f"{h:+03d}:{mm:02d}"
    if s.startswith("Etc/GMT"):
        m=re.match(r'Etc/GMT([+\-]\d{1,2})', s)
        if m: h=-int(m.group(1)); return f"{h:+03d}:00"
    return "+00:00"
def jd_iso(s):
    s=s.replace("Z","+00:00")
    if "T" not in s: s+="T12:00:00+00:00"
    t=dt.datetime.fromisoformat(s); u=t.astimezone(dt.timezone.utc)
    return swe.julday(u.year,u.month,u.day, u.hour+u.minute/60.0+u.second/3600.0)
def jd_from_local(birth,tz_hint):
    if "T" in birth and ("+" in birth or "Z" in birth): return jd_iso(birth)
    off=tz_hint_to_offset(tz_hint)
    if "T" not in birth: birth+="T12:00:00"
    return jd_iso(birth+off)
def iso_loc(jd, tz):
    y,m,d,fr=swe.revjul(jd, swe.GREG_CAL); base=dt.datetime(y,m,d,tzinfo=dt.timezone.utc)
    t=base+dt.timedelta(seconds=fr*86400.0); return t.astimezone(ZoneInfo(tz)).strftime("%Y-%m-%d %H:%M")

def lon_ut(jd, name, lat, lon):
    flag=swe.FLG_SWIEPH|swe.FLG_TOPOCTR|swe.FLG_SPEED
    if name in P2S: return swe.calc_ut(jd, P2S[name], flag)[0][0]%360.0
    h=swe.houses_ex2(jd, lat, lon, b'T'); ascmc=h[1]
    if name=="ASC": return ascmc[swe.ASC]%360.0
    if name=="DSC": return (ascmc[swe.ASC]+180.0)%360.0
    if name=="MC":  return ascmc[swe.MC]%360.0
    if name=="IC":  return (ascmc[swe.MC]+180.0)%360.0
    if name=="NNode": return swe.calc_ut(jd, swe.MEAN_NODE, flag)[0][0]%360.0
    return None

def load_natal(path):
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
                r=walk_num(v, keys); 
                if r: return r
        if isinstance(d,list):
            for it in d:
                r=walk_num(it, keys); 
                if r: return r
        return {}
    birth = pick(j,'birth','birth_iso','birth_dt') or pick(j.get('meta',{}),'birth','datetime','date')
    tz    = pick(j,'tz','timezone') or pick(j.get('meta',{}),'tz','timezone') or "UTC"
    nums  = walk_num(j, ['lat','latitude','lon','lng','longitude']) or {}
    lat   = nums.get('lat') or nums.get('latitude'); lon = nums.get('lon') or nums.get('lng') or nums.get('longitude')
    if not (birth and lat and lon): raise ValueError("natal loader: missing birth/lat/lon")
    return str(birth), str(tz), float(lat), float(lon)

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser(description="Build Long filled (topo, safe)")
    ap.add_argument("--from", dest="FROM", required=True); ap.add_argument("--to", dest="TO", required=True)
    ap.add_argument("--json_in", required=True); ap.add_argument("--json_out", required=True)
    ap.add_argument("--natal", default=os.path.expanduser("~/astro/.state/natal_frame.json"))
    ap.add_argument("--aspects", default="0,60,90,120,180")
    ap.add_argument("--orb_conj", type=float, default=1.0); ap.add_argument("--orb_other", type=float, default=1.0)
    ap.add_argument("--step_min", type=int, default=20)
    args=ap.parse_args()

    print("BEGIN build_long_filled", args.FROM, "->", args.TO)
    birth, tz_hint, LAT, LON = load_natal(args.natal)
    swe.set_ephe_path(os.environ.get("SWEPH","")); swe.set_topo(LON, LAT, 0.0)

    jd_b=jd_from_local(birth, tz_hint); jd0=jd_iso(args.FROM); jd1=jd_iso(args.TO); step=args.step_min/1440.0
    nat_lon={t: lon_ut(jd_b, t, LAT, LON) for t in TARGETS}

    # входные события (валидные)
    J=json.load(open(args.json_in,'r',encoding='utf-8'))
    EV0=J if isinstance(J,list) else J.get('events') or []
    EV=[e for e in EV0 if isinstance(e,dict) and e.get('transit') and e.get('target') and e.get('aspect')]
    print("IN events(valid):", len(EV), " / raw:", len(EV0))
    pkmap={}
    def parse_loc(s):
        try: return dt.datetime.fromisoformat(s+":00").replace(tzinfo=ZoneInfo("Europe/Moscow"))
        except: return None
    for e in EV:
        tr=e['transit']; tar=e['target']; a=next((k for k,v in ASP.items() if v==e['aspect']),None)
        if a is not None:
            pk=parse_loc(e.get('peak') or e.get('start'))
            if pk: pkmap.setdefault((tr,tar,a),[]).append(pk)

    need=[]; state={}
    jd=jd0
    while jd<=jd1+1e-9:
        for tr in ("Jupiter","Saturn","Uranus","Neptune","Pluto"):
            lt = lon_ut(jd, tr, LAT, LON); 
            if lt is None: continue
            for tar, nt in nat_lon.items():
                if tar=="Moon" or nt is None: continue
                for a in (0,60,90,120,180):
                    orb = args.orb_conj if a==0 else args.orb_other
                    d=abs(norm180((lt-nt)-a))
                    key=(tr,tar,a)
                    inside, st, best_jd, best_d = state.get(key,(False,None,None,999.0))
                    if inside:
                        if d<best_d: best_d=d; best_jd=jd
                        if d>orb:
                            pk_dt=parse_loc(iso_loc(best_jd or st,"Europe/Moscow"))
                            exists = pk_dt and any(abs((pk_dt-x).total_seconds())<=21600 for x in pkmap.get(key,[]))
                            if not exists:
                                # границы
                                def expand(_jd, dir):
                                    j=_jd
                                    while True:
                                        j2=j + dir*step
                                        d2=abs(norm180((lon_ut(j2,tr,LAT,LON)-nt)-a))
                                        if d2>orb: return j
                                        j=j2
                                jd_start=expand(best_jd or st,-1); jd_end=expand(best_jd or st,+1)
                                start=iso_loc(jd_start,"Europe/Moscow"); peak=iso_loc(best_jd or st,"Europe/Moscow"); end=iso_loc(jd_end,"Europe/Moscow")
                                if end<=start:
                                    t0=parse_loc(start); end=(t0+dt.timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M")
                                need.append({"transit":tr,"target":tar,"aspect":ASP[a],"aspect_deg":a,
                                             "orb_peak_deg":round(best_d,3),
                                             "houses":{"tr":None,"nat":None},"signs":{"tr":None,"nat":None},
                                             "start":start,"peak":peak,"end":end})
                            inside=False; st=None; best_jd=None; best_d=999.0
                    else:
                        if d<=orb: inside=True; st=jd; best_jd=jd; best_d=d
                    state[key]=(inside,st,best_jd,best_d)
        jd+=step

    # финализация "внутри орба" на границе окна
    for (tr,tar,a),(inside,st,best_jd,best_d) in state.items():
        if inside and st is not None:
            pk_dt=parse_loc(iso_loc(best_jd or st,"Europe/Moscow"))
            exists = pk_dt and any(abs((pk_dt-x).total_seconds())<=21600 for x in pkmap.get((tr,tar,a),[]))
            if not exists:
                start=iso_loc(st,"Europe/Moscow"); peak=iso_loc(best_jd or st,"Europe/Moscow"); end=iso_loc(jd1,"Europe/Moscow")
                if end<=start:
                    t0=parse_loc(start); end=(t0+dt.timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M")
                need.append({"transit":tr,"target":tar,"aspect":ASP[a],"aspect_deg":a,
                             "orb_peak_deg":round(best_d,3),
                             "houses":{"tr":None,"nat":None},"signs":{"tr":None,"nat":None},
                             "start":start,"peak":peak,"end":end})

    out = EV + need
    for e in out:
        tr=e.get("transit",""); tar=e.get("target",""); asp=e.get("aspect","")
        e["summary"]=f'{EMO.get(tr,tr)} {asp} {EMO.get(tar,tar)}'.strip()
        head=f'Профессиональный разбор: {tr} {asp} {tar}'
        desc=e.get("description") or ""
        if "Профессиональный разбор" not in desc: e["description"]=head + ("\n"+desc if desc else "")
    json.dump(out, open(args.json_out,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print("added events:", len(need), "| total:", len(out), "| OUT:", args.json_out)
