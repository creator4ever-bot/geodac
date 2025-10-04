#!/usr/bin/env python3
import os, sys, json, datetime as dt, time
from zoneinfo import ZoneInfo
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

def parse_local(s, tzname):
    return dt.datetime.fromisoformat(s+":00").replace(tzinfo=ZoneInfo(tzname))
def to_rfc3339(s, tzname):
    return parse_local(s, tzname).isoformat(timespec='seconds')

def load_events(path):
    j=json.load(open(path,'r',encoding='utf-8'))
    return j if isinstance(j,list) else j.get('events') or []

def window_from_events(ev, tzname):
    t0=min(parse_local(e['start'], tzname) for e in ev if e.get('start'))
    t1=max(parse_local(e['end'], tzname)   for e in ev if e.get('end'))
    # запас по краям
    return (t0 - dt.timedelta(hours=12)).isoformat(timespec='seconds'), (t1 + dt.timedelta(hours=12)).isoformat(timespec='seconds')

def main():
    if len(sys.argv)<4:
        print("Usage: gcal_push_replace_simple.py <json> <calendarId> <tz>", file=sys.stderr); sys.exit(2)
    path, cal_id, tzname = sys.argv[1], sys.argv[2], sys.argv[3]
    tok = os.path.expanduser("~/.gcal/token.json")
    if not os.path.isfile(tok):
        print("ERR: token.json not found in ~/.gcal", file=sys.stderr); sys.exit(2)
    creds = Credentials.from_authorized_user_file(tok, ["https://www.googleapis.com/auth/calendar"])
    svc = build("calendar","v3",credentials=creds, cache_discovery=False)

    ev = load_events(path)
    if not ev: print("No events", file=sys.stderr); sys.exit(2)

    tmin, tmax = window_from_events(ev, tzname)
    print("Replace window:", tmin, "->", tmax)

    # удалить старые
    to_del=[]; page=None
    while True:
        r=svc.events().list(calendarId=cal_id, timeMin=tmin, timeMax=tmax,
                            singleEvents=True, showDeleted=False, maxResults=2500, pageToken=page).execute()
        to_del += r.get('items',[])
        page = r.get('nextPageToken')
        if not page: break
    print("Found to delete:", len(to_del))
    for it in to_del:
        try: svc.events().delete(calendarId=cal_id, eventId=it['id']).execute()
        except Exception as e: print("WARN delete:", it.get('summary',''), e, file=sys.stderr)
        time.sleep(0.02)

    # вставить новые
    ins=0
    for e in ev:
        body={"summary": e.get("summary") or "",
              "description": e.get("description") or "",
              "start": {"dateTime": to_rfc3339(e["start"], tzname), "timeZone": tzname},
              "end":   {"dateTime": to_rfc3339(e["end"],   tzname), "timeZone": tzname}}
        try:
            svc.events().insert(calendarId=cal_id, body=body).execute(); ins+=1
        except Exception as ex:
            print("ERR insert:", body["summary"], ex, file=sys.stderr); sys.exit(3)
        time.sleep(0.05)
    print("Inserted:", ins)
if __name__=="__main__":
    main()
