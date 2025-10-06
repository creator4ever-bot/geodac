#!/usr/bin/env python3
import sys,json
from datetime import datetime,timezone
def dt(s):
    s=s.strip()
    if s.endswith('Z'): d=datetime.strptime(s,'%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
    else:               d=datetime.strptime(s,'%Y%m%dT%H%M%S').replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M')
evs=[]; cur=None
for ln in sys.stdin:
    if ln.startswith('BEGIN:VEVENT'): cur={}
    elif ln.startswith('DTSTART'):     cur['start']=dt(ln.split(':',1)[1])
    elif ln.startswith('DTEND'):       cur['end']=dt(ln.split(':',1)[1])
    elif ln.startswith('SUMMARY:'):    cur['summary']=ln[8:].strip()
    elif ln.startswith('END:VEVENT') and cur and 'start'in cur and 'end'in cur:
        evs.append(cur); cur=None
print(json.dumps({'events':evs}, ensure_ascii=False))
