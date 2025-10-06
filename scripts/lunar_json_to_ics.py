#!/usr/bin/env python3
import os,sys,json
from datetime import datetime,timedelta,timezone
try: from zoneinfo import ZoneInfo
except: ZoneInfo=None
try:
  import yaml; CFG=yaml.safe_load(open(os.path.expanduser('~/astro/config/orbs_moon.yaml'))) or {}
except: CFG={}
MOON=CFG.get('moon',{}); DEF={'conj':0.40,'opp':0.40,'square':0.40,'trine':0.30,'sextile':0.25}
MINM=int(MOON.get('min_minutes',45)); MAXM=int(MOON.get('max_minutes',150))
SYM={'☌':'conj','☍':'opp','□':'square','△':'trine','✶':'sextile',
     'conjunction':'conj','opposition':'opp','square':'square','trine':'trine','sextile':'sextile'}
TZNAME=os.environ.get('TZ','Europe/Moscow'); TZ=ZoneInfo(TZNAME) if ZoneInfo else timezone.utc
def to_utc(dt): return (dt if dt.tzinfo else dt.replace(tzinfo=TZ)).astimezone(timezone.utc)
def parse_any(s):
  s=str(s).strip()
  if s.endswith('Z'): s=s[:-1]+'+00:00'
  if 'T' in s: dt=datetime.fromisoformat(s)
  else:
    for f in ('%Y-%m-%d %H:%M:%S','%Y-%m-%d %H:%M'):
      try: dt=datetime.strptime(s,f); break
      except: dt=None
    if dt is None: raise ValueError(s)
  return to_utc(dt)
def fmt(dt): return dt.strftime('%Y%m%dT%H%M%SZ')
def asp_key(e):
  a=str(e.get('aspect','') or '').lower()
  for k,v in SYM.items():
    if k in a or k in e.get('summary',''): return v
  return 'conj'
def orb_minutes(e, ak):
  pk=e.get('peak',{})
  orb=None
  if isinstance(pk,dict): orb=pk.get('orb_peak_deg')
  elif isinstance(pk,(int,float,str)):
    try: orb=float(pk)
    except: orb=None
  if orb in (None,0,'0','0.0'): orb = MOON.get(ak, DEF.get(ak,0.4))
  m=int(round(2*abs(float(orb))*109))
  return max(MINM, min(m, MAXM))
def main():
  if len(sys.argv)<3:
    print('usage: lunar_json_to_ics.py in.json out.ics [days=14]', file=sys.stderr); sys.exit(2)
  src,dst=sys.argv[1],sys.argv[2]; days=int(sys.argv[3]) if len(sys.argv)>3 else 14
  data=json.load(open(src))
  items=data['events'] if isinstance(data,dict) and 'events' in data else data
  now=datetime.utcnow().replace(tzinfo=timezone.utc); w0=now-timedelta(days=days); w1=now+timedelta(days=days)
  out=['BEGIN:VCALENDAR\n','VERSION:2.0\n','PRODID:-//GeoDAC//LUNAR-JSON//EN\n']; seen=set(); n=0
  for e in items:
    s=parse_any(e['start']); ak=asp_key(e)
    t=s+timedelta(minutes=orb_minutes(e, ak))
    if e.get('end'):
      tend=parse_any(e['end'])
      if tend < t: t = tend
    if t<w0 or s>w1: continue
    s=max(s,w0); t=min(t,w1)
    summ=str(e.get('summary','Lunar event')).strip()
    key=(summ,fmt(s))
    if key in seen: continue
    seen.add(key)
    out+=['BEGIN:VEVENT\n',f'UID:lunar-{n}@local\n',f'DTSTAMP:{fmt(now)}\n',
          f'DTSTART:{fmt(s)}\n',f'DTEND:{fmt(t)}\n',f'SUMMARY:{summ}\n','END:VEVENT\n']
    n+=1
  out.append('END:VCALENDAR\n'); open(dst,'w',encoding='utf-8').writelines(out)
  print(f'written:{dst} events:{n}')
if __name__=='__main__': main()
