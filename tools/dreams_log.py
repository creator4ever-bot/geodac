#!/usr/bin/env python3
from pathlib import Path
import argparse, json, datetime as dt
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from subprocess import run, PIPE
import sys

def classify(start, end):
    p = Path.home()/ "astro"/ "tools"/ "dreams_classify_interval.py"
    cp = run([str(Path.home()/ "astroenv"/ "bin"/ "python"), str(p), "--start", start, "--end", end], stdout=PIPE, text=True)
    if cp.returncode!=0:
        return [], []
    d = json.loads(cp.stdout)
    cats = [c[0] for c in d.get("categories",[])]
    trg  = d.get("triggers",[])
    return cats, trg

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)   # "YYYY-MM-DD HH:MM"
    ap.add_argument("--end", required=True)
    ap.add_argument("--note", default="")
    ap.add_argument("--cal", default=None)      # если None -> из ENV DREAM_CAL или Lunar Natal Managed
    ap.add_argument("--tz",  default="Europe/Moscow")
    args = ap.parse_args()

    cats,tr = classify(args.start, args.end)
    cats_ru = {
      "garbage":"Мусорные", "repressed":"Вытесняемое",
      "archetypal":"Архетипическое", "precognitive":"Предвидение",
      "karmic":"Кармическое", "lucid":"Осознанные"
    }
    cats_disp = ", ".join(cats_ru.get(c,c) for c in cats) if cats else "Сон"
    summary = f"Сон — {cats_disp}"
    body = []
    if cats:
        body.append("Категории: " + ", ".join(cats_disp.split(", ")))
    if tr: body.append("Триггеры: " + ", ".join(tr))
    if args.note: body.append("\nЗаметка:\n" + args.note)
    description = "\n".join(body).strip()

    cal = args.cal or (sys.argv and None)
    if not cal:
        cal = (Path.home()/".gcal"/"dream_cal.txt").read_text().strip() if (Path.home()/".gcal"/"dream_cal.txt").exists() else "Astro — Lunar Natal (Managed)"

    creds = Credentials.from_authorized_user_file(str(Path.home()/".gcal"/"token.json"), ["https://www.googleapis.com/auth/calendar"])
    svc = build("calendar","v3",credentials=creds, cache_discovery=False)
    # find calendar id
    cid=None
    for c in svc.calendarList().list().execute().get("items",[]):
        if c.get("summary")==cal: cid=c["id"]; break
    if not cid:
        print("Calendar not found:", cal); sys.exit(2)

    body_ev = {
      "summary": summary,
      "description": description,
      "start": {"dateTime": args.start.replace(" ","T")+":00", "timeZone": args.tz},
      "end":   {"dateTime": args.end.replace(" ","T")+":00",   "timeZone": args.tz},
      "extendedProperties": {
        "private": {
          "src":"geodac","dream":"1",
          "cats": ",".join(cats), "triggers": ",".join(tr)
        }
      }
    }
    svc.events().insert(calendarId=cid, body=body_ev).execute()
    print("logged to:", cal, "|", summary)

if __name__=="__main__":
    main()
