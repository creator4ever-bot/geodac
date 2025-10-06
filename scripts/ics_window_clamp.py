#!/usr/bin/env python3
import sys,re
from datetime import datetime,timezone,timedelta
def parse_dt(v):
    v=v.strip()
    if v.endswith('Z'): return datetime.strptime(v,'%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
    if 'T' in v:        return datetime.strptime(v,'%Y%m%dT%H%M%S').replace(tzinfo=timezone.utc)
    return datetime.strptime(v,'%Y%m%d').replace(tzinfo=timezone.utc)
def fmt_dt(dt): return dt.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
def read_events(lines):
    ev=None
    for ln in lines:
        if ln.startswith('BEGIN:VEVENT'): ev={'raw':[],'dtstart':None,'dtend':None,'summary':''}
        if ev is not None:
            ev['raw'].append(ln)
            if ln.startswith('SUMMARY:'): ev['summary']=ln[8:].strip()
            if ln.startswith('DTSTART'):  ev['dtstart']=parse_dt(ln.split(':',1)[1])
            if ln.startswith('DTEND'):    ev['dtend']=parse_dt(ln.split(':',1)[1])
            if ln.startswith('END:VEVENT'): 
                yield ev; ev=None
def clamp(events, days=28, moon_max_min=90):
    now=datetime.utcnow().replace(tzinfo=timezone.utc)
    w0=now-timedelta(days=days); w1=now+timedelta(days=days)
    out=[]; seen=set()
    for e in events:
        s=e['dtstart']; t=e['dtend'] or (s+timedelta(minutes=30))
        if t<w0 or s>w1: continue
        s=max(s,w0); t=min(t,w1)
        summ=e['summary']
        if ('\u263D' in summ) or re.search(r'\bMoon\b',summ,re.I): # ☽ or Moon
            if (t-s)>timedelta(minutes=moon_max_min):
                t=s+timedelta(minutes=moon_max_min)
        if (t-s)>timedelta(days=3): t=min(s+timedelta(hours=2), w1)
        key=(summ,fmt_dt(s))
        if key in seen: continue
        seen.add(key)
        out.append((summ,s,t))
    return out
def write_ics(events, prodid='-//GeoDAC//ICS-WINDOW//EN'):
    yield 'BEGIN:VCALENDAR\n'; yield 'VERSION:2.0\n'; yield f'PRODID:{prodid}\n'
    ts=fmt_dt(datetime.utcnow().replace(tzinfo=timezone.utc))
    for summ,s,t in events:
        yield 'BEGIN:VEVENT\n'
        yield f'UID:{hash((summ,fmt_dt(s)))&((1<<64)-1)}@local\n'
        yield f'DTSTAMP:{ts}\n'
        yield f'DTSTART:{fmt_dt(s)}\n'
        yield f'DTEND:{fmt_dt(t)}\n'
        yield f'SUMMARY:{summ}\n'
        yield 'END:VEVENT\n'
    yield 'END:VCALENDAR\n'
def main():
    if len(sys.argv)<2:
        print("usage: ics_window_clamp.py <in.ics> [out.ics] [days]", file=sys.stderr); sys.exit(2)
    src=sys.argv[1]; dst=sys.argv[2] if len(sys.argv)>2 else None
    days=int(sys.argv[3]) if len(sys.argv)>3 else 28
    with open(src,'r',encoding='utf-8',errors='ignore') as f: lines=f.readlines()
    ev=list(read_events(lines)); ev2=clamp(ev,days=days)
    out=list(write_ics(ev2))
    if dst: open(dst,'w',encoding='utf-8').writelines(out)
    else: sys.stdout.writelines(out)
if __name__=='__main__': main()
