# ~/astro/tools/mundane_normalize.py
from pathlib import Path
import json, hashlib, sys

def to_str(x, is_end=False):
    if isinstance(x, str):
        s = x
    elif isinstance(x, dict):
        s = x.get("dateTime") or x.get("date")
    else:
        s = None
    if not s:
        return None
    s = s.replace("T"," ").replace("Z","").split(".")[0]
    if len(s) == 10:
        s = f"{s} {'23:59' if is_end else '00:00'}"
    return s[:16]

def main(src: Path, out: Path):
    d = json.loads(src.read_text(encoding="utf-8"))
    evs = d.get("events") or d.get("items") or (d if isinstance(d, list) else [])
    out_e = []
    for e in (evs or []):
        s  = e.get("summary") or ""
        st = to_str(e.get("start"), False) or to_str(e.get("originalStartTime"), False)
        en = to_str(e.get("end"), True) or st
        if not s or not st:
            continue
        basis = f"{s}|{st}|{en}"
        gd    = "gd" + hashlib.sha1(basis.encode("utf-8")).hexdigest()
        out_e.append({
            "summary": s,
            "description": e.get("description") or "",
            "start": st,
            "end": en,
            "extendedProperties": {"private": {"src":"geodac", "gd_id": gd}}
        })
    out.write_text(json.dumps({"events": out_e}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"normalized -> {out} events:{len(out_e)}")

if __name__ == "__main__":
    home = Path.home()
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else sorted((home/"astro"/"backups").glob("*Mundane*json"))[-1]
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else home/"astro"/"mundane_forpush.normalized.json"
    main(src, out)
