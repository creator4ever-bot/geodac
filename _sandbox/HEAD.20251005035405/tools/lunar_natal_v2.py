#!/usr/bin/env python3
# Lunar Natal v2 (clean, offline, topo)
import os, json, re, argparse, hashlib, datetime as dt
from zoneinfo import ZoneInfo
try:
    import swisseph as swe
except Exception:
    print("ERR: install pyswisseph in astroenv (pip install pyswisseph)", flush=True); raise

ASP_DEG = [0,60,90,120,180]
ASP_CHAR = {0:"☌",60:"✶",90:"□",120:"△",180:"☍"}
P2S = {"Sun":swe.SUN,"Moon":swe.MOON,"Mercury":swe.MERCURY,"Venus":swe.VENUS,"Mars":swe.MARS,
       "Jupiter":swe.JUPITER,"Saturn":swe.SATURN,"Uranus":swe.URANUS,"Neptune":swe.NEPTUNE,"Pluto":swe.PLUTO}
TARGETS = ["Sun","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto","NNode","ASC","MC","DSC","IC"]
SIGNS = ["ARIES","TAURUS","GEMINI","CANCER","LEO","VIRGO","LIBRA","SCORPIO","SAGITTARIUS","CAPRICORN","AQUARIUS","PISCES"]
EMO = {"Sun":"☉","Moon":"☽","Mercury":"☿","Venus":"♀","Mars":"♂","Jupiter":"♃","Saturn":"♄","Uranus":"♅","Neptune":"♆","Pluto":"♇",
       "ASC":"ASC","MC":"MC","DSC":"DSC","IC":"IC","NNode":"☊"}

def norm180(x): return (x+180.0)%360.0 - 180.0
def norm360(x): return x%360.0
def sign_name(lon): return SIGNS[int(norm360(lon)//30)%12]

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
    return swe.julday(u.year,u.month,u.day,u.hour+u.minute/60.0+u.second/3600.0)

def jd_from_local(birth, tz_hint):
    if "T" in birth and ("+" in birth or "Z" in birth): return jd_iso(birth)
    off=tz_hint_to_offset(tz_hint)
    if "T" not in birth: birth+="T12:00:00"
    return jd_iso(birth+off)

def iso_local(jd, tzname):
    y,m,d,fr = swe.revjul(jd, swe.GREG_CAL)
    base = dt.datetime(y,m,d,tzinfo=dt.timezone.utc)
    t = base + dt.timedelta(seconds=fr*86400.0)
    return t.astimezone(ZoneInfo(tzname)).strftime("%Y-%m-%d %H:%M")

def normalize_cusps(raw):
    # возвратить список длиной 13: [None, c1..c12]
    if len(raw) >= 13:
        # если raw[0]≈0 и raw[1] не 0 — значит 1-based в индексах 1..12
        if abs(raw[0]) < 1e-9 and abs(raw[1]) > 1e-9:
            arr = [None] + [norm360(raw[i]) for i in range(1,13)]
        else:
            # cusp1 находится в raw[0]
            arr = [None] + [norm360(raw[i-1]) for i in range(1,13)]
    elif len(raw) == 12:
        arr = [None] + [norm360(x) for x in raw]
    else:
        # fallback: заполним равномерным кругом, чтобы не падать
        arr = [None] + [i*30.0 for i in range(12)]
    return arr

def houses_axes(jd, lat, lon):
    h = swe.houses_ex2(jd, lat, lon, b'T')   # Topocentric
    raw_cusps, ascmc = h[0], h[1]
    cusps = normalize_cusps(raw_cusps)
    asc = norm360(ascmc[swe.ASC]); mc = norm360(ascmc[swe.MC])
    dsc = norm360(asc+180.0); ic = norm360(mc+180.0)
    return cusps, {"ASC":asc,"MC":mc,"DSC":dsc,"IC":ic}

def house_index_by_lon(lon, cusps):
    # ожидание: cusps длиной 13; если 12 — превратим
    if len(cusps)==12: cusps = [None] + list(cusps)
    for i in range(1,13):
        a=cusps[i]; b=cusps[1] if i==12 else cusps[i+1]
        if a<=b:
            if a<=lon<b: return i
        else:
            if lon>=a or lon<b: return i
    return 12

def lon_ut(jd, name, lat, lon):
    flag = swe.FLG_SWIEPH|swe.FLG_TOPOCTR|swe.FLG_SPEED
    if name in P2S:
        return swe.calc_ut(jd, P2S[name], flag)[0][0]%360.0
    # axes
    h = swe.houses_ex2(jd, lat, lon, b'T')
    ascmc = h[1]
    asc = norm360(ascmc[swe.ASC]); mc = norm360(ascmc[swe.MC])
    if name=="ASC": return asc
    if name=="DSC": return norm360(asc+180.0)
    if name=="MC":  return mc
    if name=="IC":  return norm360(mc+180.0)
    if name=="NNode": return swe.calc_ut(jd, swe.MEAN_NODE, flag)[0][0]%360.0
    return None

def det_id(style, transit, targets, aspect_deg, start_iso, end_iso):
    key=f"{style}|{transit}|{','.join(sorted(targets))}|{aspect_deg}|{start_iso}|{end_iso}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()

def summarize(ev):
    tr=ev["transit"]; asp=ev["aspect"]; tar=ev.get("target") or "/".join(ev.get("targets",[]))
    houses=ev.get("houses") or {}; nat=houses.get("nat"); trh=houses.get("tr")
    tail=""
    if trh is not None:
        tail = f" (из H{nat} к H{trh})" if (nat not in (None,trh)) else f" (H{trh})"
    return f"{EMO.get(tr,tr)} {asp} {EMO.get(tar,tar)}{tail}"

def prof_header(ev):
    tr=ev["transit"]; asp=ev["aspect"]; tar=ev.get("target") or "/".join(ev.get("targets",[]))
    return f"Профессиональный разбор: {tr} {asp} {tar}".strip()

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
    tz = pick(j,'tz','timezone') or pick(j.get('meta',{}),'tz','timezone') or "UTC"
    nums = walk_num(j, ['lat','latitude','lon','lng','longitude']) or {}
    lat = nums.get('lat') or nums.get('latitude'); lon = nums.get('lon') or nums.get('lng') or nums.get('longitude')
    if not (birth and lat and lon): raise ValueError("natal loader: missing birth/lat/lon")
    return str(birth), str(tz), float(lat), float(lon)

def parse_args():
    ap=argparse.ArgumentParser(description="Lunar Natal v2 (offline, topo)")
    ap.add_argument("--from", dest="from_utc"); ap.add_argument("--to", dest="to_utc")
    ap.add_argument("--tz", default=os.environ.get("TZ","Europe/Moscow"))
    ap.add_argument("--natal", default=os.environ.get("NATAL_JSON") or os.path.expanduser("~/astro/.state/natal_frame.json"))
    ap.add_argument("--birth"); ap.add_argument("--lat", type=float); ap.add_argument("--lon", type=float); ap.add_argument("--tzhint")
    ap.add_argument("--aspects", default=os.environ.get("ASPECTS","0,60,90,120,180"))
    ap.add_argument("--orb_conj", type=float, default=float(os.environ.get("ORB_CONJ","2.0")))
    ap.add_argument("--orb_other", type=float, default=float(os.environ.get("ORB_OTHER","1.0")))
    ap.add_argument("--step_min", type=int, default=int(os.environ.get("STEP_MIN","2")))
    ap.add_argument("--out_dir", default=os.path.expanduser("~/astro"))
    return ap.parse_args()

def run():
    a=parse_args()
    swe.set_ephe_path(os.environ.get("SWEPH",""))
    birth,tz_hint,lat,lon = load_natal(a.natal, a.birth, a.lat, a.lon, a.tzhint)
    swe.set_topo(lon,lat,0.0)

    if a.from_utc and a.to_utc: jd0=jd_iso(a.from_utc); jd1=jd_iso(a.to_utc)
    else:
        now=dt.datetime.now(dt.timezone.utc); a0=(now-dt.timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ"); a1=(now+dt.timedelta(days=35)).strftime("%Y-%m-%dT%H:%M:%SZ")
        jd0=jd_iso(a0); jd1=jd_iso(a1)
    jd_b=jd_from_local(birth,tz_hint)

    cusps, axes = houses_axes(jd_b, lat, lon)

    natal_lon={}
    for name, code in P2S.items():
        if name=="Moon": continue
        natal_lon[name] = swe.calc_ut(jd_b, code, swe.FLG_SWIEPH|swe.FLG_TOPOCTR|swe.FLG_SPEED)[0][0]%360.0
    natal_lon["NNode"] = swe.calc_ut(jd_b, swe.MEAN_NODE, swe.FLG_SWIEPH|swe.FLG_TOPOCTR|swe.FLG_SPEED)[0][0]%360.0
    natal_lon.update(axes)

    aspects=[int(x) for x in re.split(r"[,\s]+", a.aspects) if x]
    orb_conj=float(a.orb_conj); orb_other=float(a.orb_other)
    step=max(1,int(a.step_min))/1440.0

    events=[]; style="lunar"; state={}
    jd=jd0
    while jd<=jd1+1e-9:
        m = swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH|swe.FLG_TOPOCTR|swe.FLG_SPEED)[0][0]%360.0
        for tar, nlon in natal_lon.items():
            if tar=="Moon": continue
            for adeg in aspects:
                achar=ASP_CHAR.get(adeg,"∠"); orb=orb_conj if adeg==0 else orb_other
                d=abs(norm180((m-nlon)-adeg))
                inside, start_jd, min_jd, min_d = state.get((tar,adeg),(False,None,None,999.0))
                if inside:
                    if d<min_d: min_d=d; min_jd=jd
                    if d>orb:
                        # finalize (houses по фикс. натальной сетке)
                        peak_jd = min_jd or start_jd
                        start_iso=iso_local(start_jd, a.tz); end_iso=iso_local(jd, a.tz); peak_iso=iso_local(peak_jd, a.tz)
                        mlon_peak = swe.calc_ut(peak_jd, swe.MOON, swe.FLG_SWIEPH|swe.FLG_TOPOCTR|swe.FLG_SPEED)[0][0]%360.0
                        trh = house_index_by_lon(mlon_peak, cusps)
                        nat_h = house_index_by_lon(nlon, cusps) if tar in P2S else None
                        ev={"transit":"Moon","target":tar,"aspect":achar,"aspect_deg":adeg,
                            "orb_peak_deg":round(min_d,3),
                            "houses":{"tr":trh,"nat":nat_h},
                            "signs":{"tr":sign_name(mlon_peak),"nat":sign_name(nlon) if tar in P2S else None},
                            "start":start_iso,"peak":peak_iso,"end":end_iso,"style":style}
                        ev["id"]=det_id(style,"Moon",[tar],adeg,start_iso,end_iso)
                        events.append(ev)
                        inside=False; start_jd=None; min_jd=None; min_d=999.0
                else:
                    if d<=orb:
                        inside=True; start_jd=jd; min_jd=jd; min_d=d
                state[(tar,adeg)]=(inside,start_jd,min_jd,min_d)
        jd+=step

    # finalize незакрытые
    for (tar,adeg),(inside,start_jd,min_jd,min_d) in state.items():
        if inside and start_jd is not None:
            peak_jd=min_jd or start_jd
            start_iso=iso_local(start_jd, a.tz); end_iso=iso_local(jd1, a.tz); peak_iso=iso_local(peak_jd, a.tz)
            mlon_peak=swe.calc_ut(peak_jd, swe.MOON, swe.FLG_SWIEPH|swe.FLG_TOPOCTR|swe.FLG_SPEED)[0][0]%360.0
            trh = house_index_by_lon(mlon_peak, cusps)
            nat_h = house_index_by_lon(natal_lon.get(tar,0.0), cusps) if tar in P2S else None
            ev={"transit":"Moon","target":tar,"aspect":ASP_CHAR.get(adeg,"∠"),"aspect_deg":adeg,
                "orb_peak_deg":round(min_d,3),
                "houses":{"tr":trh,"nat":nat_h},
                "signs":{"tr":sign_name(mlon_peak),"nat":sign_name(natal_lon.get(tar,0.0)) if tar in P2S else None},
                "start":start_iso,"peak":peak_iso,"end":end_iso,"style":style}
            ev["id"]=det_id(style,"Moon",[tar],adeg,start_iso,end_iso)
            events.append(ev)

    # ингрессии домов
    jd=jd0; last_h=None
    while jd<=jd1+1e-9:
        mlon=swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH|swe.FLG_TOPOCTR|swe.FLG_SPEED)[0][0]%360.0
        h=house_index_by_lon(mlon, cusps)
        if last_h is None: last_h=h
        elif h!=last_h:
            iso=iso_local(jd, a.tz)
            ev={"transit":"Moon","target":f"H{h}","aspect":"∠","aspect_deg":-1,"orb_peak_deg":0.0,
                "houses":{"tr":h,"nat":last_h},"signs":{"tr":sign_name(mlon),"nat":None},
                "start":iso,"peak":iso,"end":iso,"style":"lunar"}
            ev["id"]=det_id("lunar","Moon",[f"H{h}"],-1,iso,iso)
            events.append(ev); last_h=h
        jd+=step

    # merge осей (только ☌) в пределах 2ч
    def to_dt_local(s): return dt.datetime.fromisoformat(s+":00").replace(tzinfo=ZoneInfo(a.tz))
    merged=[]; skip=set()
    evs=sorted(events, key=lambda e:(e["peak"], e.get("target",""), e["aspect_deg"]))
    for i,e in enumerate(evs):
        if i in skip: continue
        tar=e.get("target"); adeg=e.get("aspect_deg")
        if tar in ("ASC","DSC","MC","IC") and adeg==0:
            pair=("ASC","DSC") if tar in ("ASC","DSC") else ("MC","IC")
            t0=to_dt_local(e["peak"]); out=dict(e); out.pop("target",None); out["targets"]=list(pair)
            for j in range(i+1, min(i+60,len(evs))):
                f=evs[j]
                if f.get("aspect_deg")!=0: continue
                if f.get("target") in pair and f.get("target")!=tar:
                    t1=to_dt_local(f["peak"])
                    if abs((t1-t0).total_seconds())<=7200: skip.add(j); break
            merged.append(out)
        else:
            merged.append(e)

    # newstyle
    for e in merged:
        e["summary"]=f'{EMO.get(e["transit"],e["transit"])} {e["aspect"]} {EMO.get(e.get("target") or "/".join(e.get("targets",[])),"")}'.strip()
        houses=e.get("houses") or {}; nat=houses.get("nat"); trh=houses.get("tr")
        if trh is not None: e["summary"] += f' (из H{nat} к H{trh})' if (nat not in (None,trh)) else f' (H{trh})'
        desc=e.get("description") or ""; head=f'Профессиональный разбор: {e["transit"]} {e["aspect"]} {e.get("target") or "/".join(e.get("targets",[]))}'
        if "Профессиональный разбор" not in desc: desc=head+("\n"+desc if desc else "")
        e["description"]=re.sub(r"[A-Za-z0-9._%+-]+@group\.calendar\.google\.com","",desc).strip()

    out=os.path.expanduser(a.out_dir)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out,"lunar_natal_for_ics.json"),"w",encoding="utf-8") as g:
        json.dump({"events":merged}, g, ensure_ascii=False, indent=2)
    with open(os.path.join(out,"lunar_natal_forpush.json"),"w",encoding="utf-8") as g:
        json.dump({"events":merged}, g, ensure_ascii=False, indent=2)
    print(f"wrote: {out}/lunar_natal_for_ics.json; {out}/lunar_natal_forpush.json; events={len(merged)}")

if __name__=="__main__":
    run()
