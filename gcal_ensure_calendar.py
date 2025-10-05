#!/usr/bin/env python3
import os, sys
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
SCOPES=['https://www.googleapis.com/auth/calendar']
def get_service():
    cred=Credentials.from_authorized_user_file(os.path.expanduser('~/.gcal/token.json'), SCOPES)
    return build('calendar','v3', credentials=cred)
def find_id(svc, name):
    tok=None
    while True:
        r=svc.calendarList().list(pageToken=tok).execute()
        for it in r.get('items', []):
            if it.get('summary') == name:
                return it.get('id','')
        tok=r.get('nextPageToken')
        if not tok: break
    return ''
if __name__=='__main__':
    name = sys.argv[1] if len(sys.argv)>1 else ''
    if not name: print("[gcal] no calendar name", file=sys.stderr) or sys.exit(2)
    svc=get_service()
    cid=find_id(svc,name)
    if cid:
        print(cid); sys.exit(0)
    # create
    body={'summary': name, 'timeZone': os.environ.get('TZ','Europe/Moscow')}
    cal=svc.calendars().insert(body=body).execute()
    print(cal.get('id',''))
