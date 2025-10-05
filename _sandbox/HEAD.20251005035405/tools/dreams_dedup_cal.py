#!/usr/bin/env python3
from pathlib import Path
import argparse, datetime as dt, time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def min_str(sd: dict) -> str:
    if not isinstance(sd, dict): return ""
    s = sd.get("dateTime") or sd.get("date") or ""
    s = s.replace("T"," "); s = s.split(".")[0]
    if len(s) >= 16: return s[:16]
    if len(s) == 10: return s + " 00:00"
    return s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cal", required=True)
    ap.add_argument("--days", type=int, default=7)
    args = ap.parse_args()

    creds = Credentials.from_authorized_user_file(str(Path.home()/".gcal"/"token.json"),
             ["https://www.googleapis.com/auth/calendar"])
    svc = build("calendar","v3",credentials=creds, cache_discovery=False)

    # resolve calendar id
    cid=None
    for c in svc.calendarList().list().execute().get("items",[]):
        if c.get("summary")==args.cal: cid=c["id"]; break
    if not cid:
        print("Calendar not found:", args.cal); return

    now=dt.datetime.utcnow()
    tmin=(now-dt.timedelta(days=args.days)).strftime("%Y-%m-%dT00:00:00Z")
    tmax=(now+dt.timedelta(days=args.days)).strftime("%Y-%m-%dT23:59:59Z")

    # fetch
    items=[]; page=None
    while True:
        r=svc.events().list(calendarId=cid,timeMin=tmin,timeMax=tmax,singleEvents=True,maxResults=2500,
                            orderBy="startTime",pageToken=page).execute()
        items+=r.get("items",[]); page=r.get("nextPageToken")
        if not page: break

    # group by minute start/end
    from collections import defaultdict
    grp=defaultdict(list)
    for e in items:
        k=(min_str(e.get("start") or {}), min_str(e.get("end") or {}))
        if k[0] and k[1]:
            grp[k].append(e)

    deleted=0
    for k,arr in grp.items():
        if len(arr) <= 1: continue
        arr.sort(key=lambda x:x.get("updated",""))
        keep=arr[-1]; rm=arr[:-1]
        for e in rm:
            svc.events().delete(calendarId=cid, eventId=e["id"]).execute()
            deleted += 1
            time.sleep(0.02)
    print(f"dedup window [{tmin}..{tmax}] -> deleted {deleted}")
if __name__=="__main__":
    main()
