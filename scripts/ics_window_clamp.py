#!/usr/bin/env python3
import sys,re
from datetime import datetime,timezone,timedelta
def pdt(v):
  v=v.strip()
  if v.endswith('Z'): return datetime.strptime(v,'%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
  if 'T' in v:        return datetime.strptime(v,'%Y%m%dT%H%M%S').replace(tzinfo=timezone.utc)
  return datetime.strptime(v,'%Y%m%d').replace(tzinfo=timezone.utc)
def fmt(dt): return dt.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
def read(lines):
  ev=None
  for ln in lines:
    if ln.startswith('BEGIN:VEVENT'): ev={'raw':[],'s':None,'e':None,'sum':''}
    if ev is not None:
      ev['raw'].append(ln)
      if ln.startswith('SUMMARY:'): ev['sum']=ln[8:].strip()
      if ln.startswith('DTSTART'):  ev['s']=pdt(ln.split(':',1)[1])
      if ln.startswith('DTEND'):    ev['e']=pdt(ln.split(':',1)[1])
      if ln.startswith('END:VEVENT'): yield ev; ev=None
def main():
  if len(sys.argv)<3:
    print("usage: ics_window_clamp.py in.ics out.ics [days=28]", file=sys.stderr); sys.exit(2)
  src,dst=sys.argv[1],sys.argv[2]; days=int(sys.argv[3]) if len(sys.argv)>3 else 28
  L=open(src,'r',encoding='utf-8',errors='ignore').readlines()
  now=datetime.utcnow().replace(tzinfo=timezone.utc)
  w0=now-timedelta(days=days); w1=now+timedelta(days=days)
  out=['BEGIN:VCALENDAR\n','VERSION:2.0\n','PRODID:-//GeoDAC//ICS-WINDOW//EN\n']; seen=set()
  for e in read(L):
    s=e['s']; t=e['e'] or (s+timedelta(minutes=30))
    if t<w0 or s>w1: continue
    s=max(s,w0); t=min(t,w1)
    if ('\u263D' in e['sum']) or re.search(r'\bMoon\b', e['sum'], re.I):
      if (t-s)>timedelta(minutes=90): t=s+timedelta(minutes=90)
    if (t-s)>timedelta(days=3): t=min(s+timedelta(hours=2), w1)
    key=(e['sum'],fmt(s))
    if key in seen: continue
    seen.add(key)
    out+=['BEGIN:VEVENT\n',f'UID:clamp-{len(seen)}@local\n',f'DTSTAMP:{fmt(now)}\n',
          f'DTSTART:{fmt(s)}\n',f'DTEND:{fmt(t)}\n',f'SUMMARY:{e["sum"]}\n','END:VEVENT\n']
  out.append('END:VCALENDAR\n')
  open(dst,'w',encoding='utf-8').writelines(out)
  print(f'written:{dst} events:{len(seen)}')
if __name__=='__main__': main()
