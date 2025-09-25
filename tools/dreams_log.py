#!/usr/bin/env python3
from pathlib import Path
import argparse, json, datetime as dt, hashlib
from subprocess import run, PIPE
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

DEF_CAL = "GeoDAC • Dreams (TEST)"

CATS_RU = {
    "garbage": "Мусорные",
    "repressed": "Вытесняемое",
    "archetypal": "Архетипическое",
    "precognitive": "Предвидение",
    "karmic": "Кармическое",
    "lucid": "Осознанные",
}

def classify(start: str, end: str):
    """Возвращает (categories:list[str], triggers:list[str], flags:list[str])"""
    p  = Path.home()/ "astro"/ "tools"/ "dreams_classify_interval.py"
    py = Path.home()/ "astroenv"/ "bin"/ "python"
    cp = run([str(py), str(p), "--start", start, "--end", end], stdout=PIPE, text=True)
    if cp.returncode != 0:
        return [], [], []
    try:
        d = json.loads(cp.stdout)
    except Exception:
        return [], [], []
    cats = [c[0] for c in d.get("categories", [])]
    trg  = d.get("triggers", [])
    flg  = d.get("flags", [])
    return cats, trg, flg

def to_rfc3339_local(s: str) -> str:
    # "YYYY-MM-DD HH:MM" -> "YYYY-MM-DDTHH:MM:00"
    return s.replace(" ", "T") + ":00"

def list_events(svc, cid: str, tmin: str, tmax: str):
    items, page = [], None
    while True:
        resp = svc.events().list(
            calendarId=cid, timeMin=tmin, timeMax=tmax,
            singleEvents=True, orderBy="startTime",
            maxResults=2500, pageToken=page
        ).execute()
        items += resp.get("items", [])
        page = resp.get("nextPageToken")
        if not page:
            break
    return items

def ev_min_str(sd: dict) -> str:
    """Нормализует start/end события GCal к строке 'YYYY-MM-DD HH:MM'."""
    if not isinstance(sd, dict):
        return ""
    s = sd.get("dateTime") or sd.get("date") or ""
    s = s.replace("T", " ")
    s = s.split(".")[0]
    if len(s) >= 16:
        return s[:16]
    if len(s) == 10:
        return s + " 00:00"
    return s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)  # "YYYY-MM-DD HH:MM"
    ap.add_argument("--end",   required=True)
    ap.add_argument("--note",  default="")
    ap.add_argument("--cal",   default=None)
    ap.add_argument("--tz",    default="Europe/Moscow")
    args = ap.parse_args()

    # Классификация
    cats, tr, fl = classify(args.start, args.end)
    cats_disp = ", ".join(CATS_RU.get(c, c) for c in cats) if cats else "Сон"
    summary = f"Сон — {cats_disp}"

    # Описание
    body_lines = []
    if cats:
        body_lines.append("Категории: " + ", ".join(cats_disp.split(", ")))
    if tr:
        body_lines.append("Триггеры: " + ", ".join(tr))
    if fl:
        body_lines.append("Флаги: " + ", ".join(fl))
    if args.note:
        body_lines.append("\nЗаметка:\n" + args.note)
    description = "\n".join(body_lines).strip()

    # Целевой календарь
    cal = args.cal
    if not cal:
        f = Path.home()/".gcal"/"dream_cal.txt"
        cal = f.read_text().strip() if f.exists() else DEF_CAL

    # Стабильный идентификатор интервала
    basis = f"{args.start}|{args.end}"
    gd_id = "dr" + hashlib.sha1(basis.encode("utf-8")).hexdigest()

    # GCal service
    creds = Credentials.from_authorized_user_file(
        str(Path.home()/".gcal"/"token.json"),
        ["https://www.googleapis.com/auth/calendar"]
    )
    svc = build("calendar", "v3", credentials=creds, cache_discovery=False)

    # Найти calendarId по summary
    cid = None
    for c in svc.calendarList().list().execute().get("items", []):
        if c.get("summary") == cal:
            cid = c["id"]
            break
    if not cid:
        raise SystemExit(f"Calendar not found: {cal}")

    # Окно поиска существующего события (±1 сутки)
    d0 = dt.datetime.fromisoformat(args.start)
    d1 = dt.datetime.fromisoformat(args.end)
    tmin = (d0 - dt.timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
    tmax = (d1 + dt.timedelta(days=1)).strftime("%Y-%m-%dT23:59:59Z")

    existing = None
    for e in list_events(svc, cid, tmin, tmax):
        priv = e.get("extendedProperties", {}).get("private", {})
        if priv.get("gd_id") == gd_id:
            existing = e
            break
        # Жёсткий fallback по минутам (локальное сравнение)
        st_min = ev_min_str(e.get("start") or {})
        en_min = ev_min_str(e.get("end") or {})
        if st_min == args.start and en_min == args.end:
            existing = e
            break

    # Событие для upsert
    body_ev = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": to_rfc3339_local(args.start), "timeZone": args.tz},
        "end":   {"dateTime": to_rfc3339_local(args.end),   "timeZone": args.tz},
        "extendedProperties": {
            "private": {
                "src": "geodac",
                "dream": "1",
                "gd_id": gd_id,
                "cats": ",".join(cats),
                "triggers": ",".join(tr),
                "flags": ",".join(fl),
            }
        }
    }

    # Upsert
    if existing:
        svc.events().update(calendarId=cid, eventId=existing["id"], body=body_ev).execute()
        print("upsert: updated |", cal, "|", summary)
    else:
        svc.events().insert(calendarId=cid, body=body_ev).execute()
        print("upsert: inserted |", cal, "|", summary)

if __name__ == "__main__":
    main()
