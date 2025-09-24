#!/usr/bin/env python3
import argparse, sys, json, time
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = {
    "ro": ["https://www.googleapis.com/auth/calendar.readonly"],
    "rw": ["https://www.googleapis.com/auth/calendar"],
}

def svc(scope="ro"):
    tok = Path.home()/".gcal"/"token.json"
    creds = Credentials.from_authorized_user_file(str(tok), SCOPES[scope])
    return build("calendar", "v3", credentials=creds, cache_discovery=False)

def get_cid(s, name):
    items = s.calendarList().list().execute().get("items",[])
    for c in items:
        if c.get("summary")==name: return c["id"]
    return None

def cmd_list(args):
    s = svc("ro")
    items = s.calendarList().list().execute().get("items",[])
    for c in items:
        print("-", c.get("summary"), "|", c.get("id"))

def cmd_ensure(args):
    s = svc("rw")
    cid = get_cid(s, args.cal)
    if cid:
        print("exists:", cid); return
    body = {"summary": args.cal, "timeZone": args.tz}
    cid = s.calendars().insert(body=body).execute()["id"]
    s.calendarList().insert(body={"id": cid}).execute()
    print("created:", cid)

def cmd_share(args):
    s = svc("rw")
    cid = get_cid(s, args.cal)
    acl = s.acl().list(calendarId=cid).execute().get("items",[])
    have = {a.get("scope",{}).get("value") for a in acl if a.get("scope",{}).get("type")=="user"}
    for e in args.emails:
        if e in have: print("already:", e); continue
        rule = {"role":"reader","scope":{"type":"user","value": e}}
        s.acl().insert(calendarId=cid, body=rule).execute(); print("shared:", e)

def cmd_push(args):
    s = svc("rw")
    cid = get_cid(s, args.cal)
    data = json.loads(Path(args.json).read_text(encoding="utf-8"))
    evs = data.get("events", [])
    desired = {}
    for e in evs:
        priv = e.setdefault("extendedProperties",{}).setdefault("private",{})
        gid = priv.get("gd_id")
        if not gid:
            basis = (e.get("summary","")+"|"+e.get("start",""))
            import hashlib; gid = "gd"+hashlib.sha1(basis.encode()).hexdigest()
            priv["gd_id"] = gid
        desired[gid] = e

    # upsert
    print("[gcal-cli] upsert:", len(desired))
    # fetch existing
    page=None; existing={}
    while True:
        resp = s.events().list(calendarId=cid, maxResults=2500, pageToken=page, singleEvents=True).execute()
        for it in resp.get("items",[]):
            gid = it.get("extendedProperties",{}).get("private",{}).get("gd_id")
            if gid: existing[gid]=it
        page = resp.get("nextPageToken"); 
        if not page: break

    ins=upd=0
    for gid,e in desired.items():
        body = {
            "summary": e.get("summary",""),
            "description": e.get("description",""),
            "start": {"dateTime": e["start"].replace(" ","T")+":00+03:00", "timeZone": args.tz},
            "end":   {"dateTime": e["end"].replace(" ","T")+":00+03:00",   "timeZone": args.tz},
            "extendedProperties": e.get("extendedProperties",{})
        }
        if gid in existing:
            s.events().update(calendarId=cid, eventId=existing[gid]["id"], body=body).execute(); upd+=1
        else:
            s.events().insert(calendarId=cid, body=body).execute(); ins+=1
    print(f"upsert done: inserted={ins}, updated={upd}, total={len(desired)}")

    if args.replace:
        # delete extras
        delcnt=0
        for gid,it in existing.items():
            if gid not in desired:
                s.events().delete(calendarId=cid, eventId=it["id"]).execute(); delcnt+=1
        print("replace: deleted=", delcnt)

def cmd_wipe(args):
    if not args.yes:
        print("Add --yes to confirm wipe"); return
    s = svc("rw"); cid = get_cid(s,args.cal)
    delcnt=0; page=None
    while True:
        resp = s.events().list(calendarId=cid, maxResults=2500, pageToken=page, singleEvents=True).execute()
        items = resp.get("items",[])
        if not items and not resp.get("nextPageToken"): break
        for it in items:
            s.events().delete(calendarId=cid, eventId=it["id"]).execute(); delcnt+=1
        page = resp.get("nextPageToken")
        time.sleep(0.1)
    print("wiped:", delcnt)

def main():
    ap = argparse.ArgumentParser(prog="gcal-cli")
    sp = ap.add_subparsers(dest="cmd", required=True)

    p = sp.add_parser("list"); p.set_defaults(fn=cmd_list)

    p = sp.add_parser("ensure"); p.add_argument("--cal", required=True); p.add_argument("--tz", default="Europe/Moscow"); p.set_defaults(fn=cmd_ensure)

    p = sp.add_parser("share"); p.add_argument("--cal", required=True); p.add_argument("emails", nargs="+"); p.set_defaults(fn=cmd_share)

    p = sp.add_parser("push"); p.add_argument("--cal", required=True); p.add_argument("--json", required=True); p.add_argument("--tz", default="Europe/Moscow"); p.add_argument("--replace", action="store_true"); p.set_defaults(fn=cmd_push)

    p = sp.add_parser("wipe"); p.add_argument("--cal", required=True); p.add_argument("--yes", action="store_true"); p.set_defaults(fn=cmd_wipe)

    args = ap.parse_args(); args.fn(args)

if __name__ == "__main__":
    main()
