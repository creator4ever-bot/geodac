#!/usr/bin/env python3
import os,sys,json
from datetime import datetime,timedelta,timezone
try: import yaml
except: yaml=None
import swisseph as swe

ASPECTS=[('☌',0),('✶',60),('□',90),('△',120),('☍',180)]
CLAMP_DEG=30.0      # бракет должен быть ближе к аспекту, чем 30°
CONFIRM_DEG=0.1     # финальная проверка корня: |Δ| < 0.1°

try:
  from zoneinfo import ZoneInfo
  TZ=ZoneInfo(os.environ.get('TZ','Europe/Moscow'))
except: TZ=timezone.utc

def diff180(x): return (x+180.0)%360.0-180.0
def moon_lon(jd): return swe.calc_ut(jd, swe.MOON)[0][0]

def has_root(a,b,target_deg):
  fa=diff180(moon_lon(a)-target_deg)
  fb=diff180(moon_lon(b)-target_deg)
  # отбраковываем ложные «корни» возле разрыва ±180°
  if min(abs(fa),abs(fb))>CLAMP_DEG: return False,fa,fb
  return (fa==0.0) or (fa*fb<0.0), fa, fb

def bisect(a,b,target_deg):
  ok,fa,fb=has_root(a,b,target_deg)
  if not ok: return None
  for _ in range(32):
    m=(a+b)/2.0
    fm=diff180(moon_lon(m)-target_deg)
    if abs(fm)<1e-6 or (b-a)<(1.0/1440.0):  # точность ~1 мин
      # финальная валидация корня — близость к нужному аспекту
      if abs(diff180(moon_lon(m)-target_deg))<=CONFIRM_DEG: return m
      return None
    if fa*fm<=0.0: b=m; fb=fm
    else: a=m; fa=fm
  return None

def jd_range(dt0,dt1,step_h=3):
  j0=swe.julday(dt0.year,dt0.month,dt0.day, dt0.hour+dt0.minute/60)
  j1=swe.julday(dt1.year,dt1.month,dt1.day, dt1.hour+dt1.minute/60)
  step=step_h/24.0; t=j0
  while t<j1:
    yield t, min(t+step, j1); t+=step

def fmt_local(dt_utc): return dt_utc.astimezone(TZ).strftime("%Y-%m-%d %H:%M")

def minutes_from_orb(sym, cfg):
  mcfg=cfg.get('moon',{}) if isinstance(cfg,dict) else {}
  mapn={'☌':'conj','☍':'opp','□':'square','△':'trine','✶':'sextile'}
  deg=float(mcfg.get(mapn[sym], 0.40 if sym in ('☌','☍','□') else 0.30))
  m=int(round(2*abs(deg)*109))  # ~109 мин/градус
  return max(int(mcfg.get('min_minutes',45)), min(m, int(mcfg.get('max_minutes',150))))

def main():
  if len(sys.argv)<2:
    print("usage: lunar_refine_peaks.py lunar_natal_for_ics.json [natal.yaml] [orbs.yaml]", file=sys.stderr); sys.exit(2)
  src=sys.argv[1]
  natp=os.path.expanduser(sys.argv[2]) if len(sys.argv)>2 else os.path.expanduser('~/astro/config/natal_positions.yaml')
  orbp=os.path.expanduser(sys.argv[3]) if len(sys.argv)>3 else os.path.expanduser('~/astro/config/orbs_moon.yaml')
  nat=(yaml.safe_load(open(natp)) if yaml and os.path.exists(natp) else {}) or {}
  orb=(yaml.safe_load(open(orbp)) if yaml and os.path.exists(orbp) else {}) or {}

  data=json.load(open(src))
  items=data['events'] if isinstance(data,dict) and 'events' in data else data

  # окно дат по данным (±1 день)
  def pdt(s):
    s=str(s).strip()
    if 'T' in s:
      if s.endswith('Z'): s=s[:-1]+'+00:00'
      dt=datetime.fromisoformat(s)
    else:
      for fmt in ("%Y-%m-%d %H:%M:%S","%Y-%m-%d %H:%M"):
        try: dt=datetime.strptime(s,fmt); break
        except: dt=None
      if dt is None: raise ValueError(s)
    return dt.replace(tzinfo=TZ).astimezone(timezone.utc)

  times=[pdt(e.get('start')) for e in items if e.get('start')]
  if times:
    dt0=min(times)-timedelta(days=1); dt1=max(times)+timedelta(days=1)
  else:
    now=datetime.utcnow().replace(tzinfo=timezone.utc); dt0=now-timedelta(days=14); dt1=now+timedelta(days=14)

  have=set((str(e.get('target') or ''), str(e.get('aspect') or ''), str(e.get('start') or '')[:10]) for e in items)
  add=[]

  for tgt,lon in nat.items():
    try: lon=float(lon)
    except: continue
    for sym,deg in ASPECTS:
      target_deg=(lon+deg)%360.0
      for a,b in jd_range(dt0,dt1,3):
        m=bisect(a,b,target_deg)
        if m is None: continue
        epoch=datetime(2000,1,1,tzinfo=timezone.utc)
        peak=epoch+timedelta(days=m-2451544.5)
        mins=minutes_from_orb(sym, orb)
        s_local=fmt_local(peak-timedelta(minutes=mins/2))
        e_local=fmt_local(peak+timedelta(minutes=mins/2))
        key=(tgt,sym,s_local[:10])
        if key in have: continue
        have.add(key)
        summ=f"Moon {sym} {tgt}"
        add.append({"peak":fmt_local(peak),"start":s_local,"end":e_local,
                    "category":"Astro","transit":"Moon","aspect":sym,"target":tgt,
                    "summary":summ,"description":summ})
  out=items+add
  print(f"[refine] added={len(add)} total={len(out)}")
  json.dump(out, open("lunar_natal_for_ics.refined.json","w"), ensure_ascii=False, indent=2)
  print("written: lunar_natal_for_ics.refined.json")
if __name__=="__main__": main()
