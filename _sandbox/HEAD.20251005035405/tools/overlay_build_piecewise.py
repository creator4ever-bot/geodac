# ~/astro/tools/overlay_build_piecewise.py
from pathlib import Path
import json, re, hashlib
from datetime import timedelta
from dateutil import parser as du

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Europe/Moscow")
except Exception:
    TZ = None

IN1 = Path.home()/ "astro"/ "overlay_houses_forpush.normalized.json"
IN2 = Path.home()/ "astro"/ "overlay_houses_forpush.json"
OUT = Path.home()/ "astro"/ "overlay_houses_forpush.pw.json"

if IN1.exists():
    src = IN1
elif IN2.exists():
    src = IN2
else:
    raise SystemExit("No input JSON found")

data = json.loads(src.read_text(encoding="utf-8"))
evs = data.get("events", [])

def is_ingress(summary: str) -> bool:
    s = (summary or "").lower()
    return ("ингресс" in s) or ("-> h" in s) or ("->" in s) or ("→ h" in s)

re_span = re.compile(r"\sв\sH(\d+)", re.I)

def parse_house(summary: str):
    m = re_span.search(summary or "")
    if m:
        try: return int(m.group(1))
        except: return None
    return None

def parse_planet(summary: str):
    # всё до "в"
    if not summary: return ""
    return summary.split("в")[0].strip()

def to_dt_local(v):
    # v: str | {"dateTime":..., "timeZone":...} | {"date":...}
    if isinstance(v, dict):
        s = v.get("dateTime") or v.get("date")
    else:
        s = v
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    dt = du.parse(s)
    if dt.tzinfo is None:
        if TZ: dt = dt.replace(tzinfo=TZ)
    else:
        if TZ: dt = dt.astimezone(TZ)
    return dt

def to_str_min(dt):
    return dt.strftime("%Y-%m-%d %H:%M")

RU_MONTHS = {
    1:"января",2:"февраля",3:"марта",4:"апреля",5:"мая",6:"июня",
    7:"июля",8:"августа",9:"сентября",10:"октября",11:"ноября",12:"декабря"
}

def format_range(d1, d2):
    # d1,d2 — datetime; подпись по датам, конец интервала считаем открытым
    a = d1.date()
    b = (d2 - timedelta(minutes=1)).date()
    if a == b:
        return f"{a.day} {RU_MONTHS[a.month]} {a.year}"
    if a.year == b.year and a.month == b.month:
        return f"{a.day} – {b.day} {RU_MONTHS[a.month]} {a.year}"
    if a.year == b.year:
        return f"{a.day} {RU_MONTHS[a.month]} – {b.day} {RU_MONTHS[b.month]} {a.year}"
    return f"{a.day} {RU_MONTHS[a.month]} {a.year} – {b.day} {RU_MONTHS[b.month]} {b.year}"

# Разбор: спаны и ингрессии
spans = []   # (planet, house, t1, t2)
ing   = []

for e in evs:
    s = e.get("summary") or ""
    if is_ingress(s):
        sdt = to_dt_local(e.get("start"))
        edt = to_dt_local(e.get("end")) or sdt
        if not sdt:
            continue
        priv = e.setdefault("extendedProperties", {}).setdefault("private", {})
        priv.setdefault("overlay", "houses")
        priv.setdefault("loop", "ingress")
        priv.setdefault("src", "geodac")
        if "gd_id" not in priv:
            basis = f"ing|{s}|{to_str_min(sdt)}"
            priv["gd_id"] = "gd" + hashlib.sha1(basis.encode("utf-8")).hexdigest()
        e["start"] = to_str_min(sdt)
        e["end"]   = to_str_min(edt)
        ing.append(e)
        continue
    h = parse_house(s)
    if h is None:
        continue
    t1 = to_dt_local(e.get("start"))
    t2 = to_dt_local(e.get("end")) or t1
    if not t1 or not t2:
        continue
    spans.append((parse_planet(s), h, t1, t2))

# Piecewise состояния: границы = все начала/концы спанов
bounds = sorted({t1 for _,_,t1,_ in spans} | {t2 for _,_,_,t2 in spans})
pw_states = []
for i in range(len(bounds)-1):
    b1, b2 = bounds[i], bounds[i+1]
    # состав в [b1, b2): постоянен
    houses = {}
    for planet, house, t1, t2 in spans:
        if t1 <= b1 and t2 >= b2:
            houses.setdefault(house, []).append(planet)
    if not houses:
        continue
    for h in list(houses.keys()):
        houses[h] = sorted(houses[h])
    lines = [
        "Планеты в домах (состояние)",
        format_range(b1, b2),
        "Состав домов:",
    ]
    for h in sorted(houses):
        lines.append(f"H{h}: " + " ".join(houses[h]))
    lines.append("GeoDAC • Overlay Houses")
    desc = "\n".join(lines)
    start_s = to_str_min(b1)
    end_s   = to_str_min(b2)
    basis = f"pw_state|{start_s}|{end_s}|{hashlib.sha1(desc.encode('utf-8')).hexdigest()}"
    gd_id = "gd" + hashlib.sha1(basis.encode("utf-8")).hexdigest()
    e = {
        "summary": "Планеты в домах (состояние)",
        "description": desc,
        "start": start_s,
        "end": end_s,
        "extendedProperties": {
            "private": {
                "overlay": "houses",
                "loop": "state",
                "src": "geodac",
                "gd_id": gd_id
            }
        }
    }
    pw_states.append(e)

# Итог: ингрессии + сквозные состояния
data["events"] = ing + pw_states
OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("written:", OUT, "ingress:", len(ing), "state_pw:", len(pw_states), "total:", len(data["events"]))
