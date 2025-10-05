#!/usr/bin/env python3
# Append house ingress events (topo) for given bodies into JSON
import os, sys, json, argparse, datetime as dt
from zoneinfo import ZoneInfo
try:
    import swisseph as swe
except Exception:
    print("ERR: pip install pyswisseph", file=sys.stderr); sys.exit(2)

def jd_iso(s):
    s=s.replace("Z","+00:00")
    if "T" not in s: s+="T12:00:00+00:00"
    t=dt.datetime.fromisoformat(s); u=t.astimezone(dt.timezone.utc)
    return swe.julday(u.year,u.month,u.day, u.hour+u.minute/60.0+u.second/3600.0)

def jd_from_local(birth,tz="UTC"):
    if "T" in birth and ("+" in birth or "Z" in birth): return jd_iso(birth)
    # fallback: local noon UTC
    return jd_iso(birth+"T12:00:00+00:00")

def iso_loc(jd, tz):
    y,m,d,fr=swe.revjul(jd, swe.GREG_CAL); base=dt.datetime(y,m,d,tzinfo=dt.timezone.utc)
    t=base+dt.timedelta(seconds=fr*86400.0); return t.astimezone(ZoneInfo(tz)).strftime("%Y-%m-%d %H:%M")

def normalize_cusps(raw):
    if len(raw)>=13:
        if abs(raw[0])<1e-9 and abs(raw[1])>1e-9:
            return [None]+[raw[i]%360.0 for i in range(1,13)]
        return [None]+[raw[i-1]%360.0 for i in range(1,13)]
    if len(raw)==12: return [None]+[x%360.0 for x in raw]
    return [None]+[i*30.0 for i in range(12)]

def house_index(lon, cusps):
    for i in range(1,13):
        a=cusps[i]; b=cusps[1] if i==12 else cusps[i+1]
        if a<=b:
            if a<=lon<b: return i
        else:
            if lon>=a or lon<b: return i
    return 12

def lon_ut(jd, code, lat, lon):
    flag=swe.FLG_SWIEPH|swe.FLG_TOPOCTR|swe.FLG_SPEED
    return swe.calc_ut(jd, code, flag)[0][0]%360.0

if __name__=="__main__":
    ap=argparse.ArgumentParser(description="Add house ingresses to JSON")
    ap.add_argument("--json_in", required=True); ap.add_argument("--json_out", required=True)
    ap.add_argument("--from", dest="FROM", required=True); ap.add_argument("--to", dest="TO", required=True)
    ap.add_argument("--natal", required=True)
    ap.add_argument("--bodies", required=True, help="comma: Sun,Mercury,... or Jupiter,...")
    ap.add_argument("--step_min", type=int, default=30)
    ap.add_argument("--tz", default="Europe/Moscow")
    args=ap.parse_args()

    swe.set_ephe_path(os.environ.get("SWEPH",""))

    # natal
    nf=json.load(open(args.natal,'r',encoding='utf-8'))
    birth=str(nf.get('birth') or nf.get('birth_iso') or nf.get('birth_dt'))
    lat=float(nf.get('lat') or nf.get('latitude')); lon=float(nf.get('lon') or nf.get('lng') or nf.get('longitude'))
    swe.set_topo(lon,lat,0.0)
    jd_b=jd_from_local(birth)
    # natal cusps (topo)
    h=swe.houses_ex2(jd_b, lat, lon, b'T'); cusps=normalize_cusps(h[0])

    # input
    J=json.load(open(args.json_in,'r',encoding='utf-8')); EV=J if isinstance(J,list) else J.get('events') or []
    out=list(EV)

    FROM_JD=jd_iso(args.FROM); TO_JD=jd_iso(args.TO); step=args.step_min/1440.0
    body_codes=[]
    for b in [x.strip() for x in args.bodies.split(",") if x.strip()]:
        code=getattr(swe, b.upper(), None)
        if code is None:
            print("WARN unknown body:", b, file=sys.stderr); continue
        body_codes.append((b,code))

    for name,code in body_codes:
        jd=FROM_JD; last=None
        while jd<=TO_JD+1e-9:
            lon_tr = lon_ut(jd, code, lat, lon); hnow = house_index(lon_tr, cusps)
            if last is None:
                last=hnow
            elif hnow!=last:
                t=iso_loc(jd, args.tz)
                # событие «ингресс»: 1 мин длительность
                from datetime import datetime, timedelta
                t0 = dt.datetime.fromisoformat(t+":00").replace(tzinfo=ZoneInfo(args.tz))
                tend=(t0+dt.timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M")
                out.append({
                    "transit": name, "target": f"H{hnow}",
                    "aspect": "∠", "aspect_deg": -1, "orb_peak_deg": 0.0,
                    "houses": {"tr": hnow, "nat": last},
                    "signs": {"tr": None, "nat": None},
                    "start": t, "peak": t, "end": tend,
                    "summary": f"{name} ∠ H{hnow} (из H{last} к H{hnow})",
                    "description": f"Профессиональный разбор: {name} ∠ H{hnow}\nИнгресс транзитного тела в натальный дом."
                })
                last=hnow
            jd+=step

    # write
    if isinstance(J,list): J=out
    else: J['events']=out
    json.dump(J, open(args.json_out,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print("ingresses added for", ",".join([n for n,_ in body_codes]), "| total events:", len(out))
