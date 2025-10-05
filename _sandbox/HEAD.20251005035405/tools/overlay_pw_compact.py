# ~/astro/tools/overlay_pw_compact.py
from pathlib import Path
import json, sys
from datetime import datetime, timedelta

def to_dt(s: str) -> datetime:
    return datetime.strptime(s[:16], "%Y-%m-%d %H:%M")

def to_s(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M")

RU = {1:"января",2:"февраля",3:"марта",4:"апреля",5:"мая",6:"июня",
      7:"июля",8:"августа",9:"сентября",10:"октября",11:"ноября",12:"декабря"}

def rng(d1: datetime, d2: datetime) -> str:
    a = d1.date()
    b = (d2 - timedelta(minutes=1)).date()
    if a == b: return f"{a.day} {RU[a.month]} {a.year}"
    if a.year == b.year and a.month == b.month: return f"{a.day} – {b.day} {RU[a.month]} {a.year}"
    if a.year == b.year: return f"{a.day} {RU[a.month]} – {b.day} {RU[b.month]} {a.year}"
    return f"{a.day} {RU[a.month]} {a.year} – {b.day} {RU[b.month]} {b.year}"

def main(in_path: Path, out_path: Path):
    data = json.loads(in_path.read_text(encoding="utf-8"))
    evs  = data.get("events", [])
    ing_days = set()
    for e in evs:
        s = (e.get("summary") or "").lower()
        priv = e.get("extendedProperties",{}).get("private",{})
        if "ингресс" in s or "->" in s or priv.get("loop") == "ingress":
            try: ing_days.add(to_dt(e["start"]).date())
            except: pass

    out = []
    for e in evs:
        if e.get("summary") != "Планеты в домах (состояние)":
            out.append(e); continue
        try:
            st = to_dt(e["start"]); en = to_dt(e["end"])
        except:
            out.append(e); continue

        st2, en2 = st, en
        if st.date() in ing_days:
            st2 = datetime.combine(st.date() + timedelta(days=1), datetime.min.time())
        if en.date() in ing_days:
            en2 = datetime.combine(en.date(), datetime.min.time())

        if st2 >= en2:
            continue

        desc = e.get("description","")
        lines = desc.splitlines() if desc else []
        if len(lines) >= 2:
            lines[1] = rng(st2, en2)
            desc = "\n".join(lines)

        e2 = dict(e)
        e2["start"] = to_s(st2)
        e2["end"]   = to_s(en2)
        e2["description"] = desc
        out.append(e2)

    data["events"] = out
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"compact -> {out_path} events:{len(out)} ingress-days:{len(ing_days)}")

if __name__ == "__main__":
    home = Path.home()
    in_path  = Path(sys.argv[1]) if len(sys.argv) > 1 else home/"astro"/"overlay_houses_forpush.pw.json"
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else home/"astro"/"overlay_houses_forpush.pw_compact.json"
    main(in_path, out_path)
