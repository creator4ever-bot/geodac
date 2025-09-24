#!/usr/bin/env python3
from pathlib import Path
import json, argparse, datetime as dt, re

def load_lunar():

def _load_json(path):
    import json
    try:
        return json.loads(Path(path).read_text(encoding="utf-8")).get("events",[])
    except Exception:
        return []
def load_medium():
    home = Path.home()/ "astro"
    for name in ("transits_medium_for_ics.json","transits_medium.json"):
        p = home/name
        if p.exists(): return _load_json(p)
    return []
def load_long():
    home = Path.home()/ "astro"
    for name in ("transits_long_for_ics.json","transits_long.json"):
        p = home/name
        if p.exists(): return _load_json(p)
    return []
def _to_dt(s):
    import datetime as dt
    if not s: return None
    s = s.replace("T"," ").replace("Z","")
    return dt.datetime.fromisoformat(s[:16])
def overlaps_ev(e,t0,t1):
    st = _to_dt(e.get("start") or e.get("peak") or e.get("end"))
    en = _to_dt(e.get("end") or e.get("start") or e.get("peak"))
    if not st: return False
    if en and en<st: en=st
    if not en: en=st
    return not (en < t0 or st > t1)

    home = Path.home()/ "astro"
    for name in ("lunar_natal_forpush.json","lunar_natal_forpush.dedup.json",
                 "lunar_natal_merged.json","lunar_natal_for_ics.json"):
        p = home/name
        if p.exists():
            try: return json.loads(p.read_text(encoding="utf-8")).get("events",[])
            except: pass
    return []

def overlaps(e, t0, t1):
    # старт/конец в строках/ISO/Z — приводим к минутам
    def to_dt(s):
        if not s: return None
        s = s.replace("T"," ").replace("Z","")
        return dt.datetime.fromisoformat(s[:16])
    start = to_dt(e.get("start")) or to_dt(e.get("peak")) or to_dt(e.get("end"))
    end   = to_dt(e.get("end")) or start
    if not start: return False
    if end < start: end = start
    return not (end < t0 or start > t1)

FAST_WORDS = ("Sun","Mercury","Venus","Mars","Солнце","Меркурий","Венера","Марс")
OUTER_WORDS= ("Uranus","Neptune","Pluto","Уран","Нептун","Плутон")

def classify_interval(t0, t1):
    evs = [e for e in load_lunar() if overlaps(e, t0, t1)]
    cats, triggers = [], []
    if not evs:
        return [("garbage",0.6)], triggers
    # простая эвристика: fast->inner, fast->outer, outer->lights
    s_list = [ (e.get("summary") or "") for e in evs ]
    fast_inner = any(any(w in s for w in FAST_WORDS) for s in s_list)
    fast_outer = any(any(w in s for w in OUTER_WORDS) for s in s_list)
    # очень грубо: outer к светилам/ASC
    outer_to_lights = any(re.search(r"(Uranus|Neptune|Pluto|Уран|Нептун|Плутон).*(Sun|Moon|Солнце|Луна|ASC|Asc|Асц)", s, re.I) for s in s_list)
    # «множественность» (два+ события в окне)
    multiplicity = len(evs) >= 2
    # сбор категорий
    if fast_outer or outer_to_lights:
        cats.append(("archetypal", 0.7))
        triggers.append("fast→outer / outer→lights")
    if fast_inner:
        cats.append(("repressed", 0.6))
        triggers.append("fast→inner")
    if not cats:
        cats.append(("garbage", 0.5))
        triggers.append("no strong fast aspects")
    # возможные флаги
    if multiplicity:
        triggers.append(f"multiplicity:{len(evs)}")
    return cats, triggers

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="YYYY-MM-DD HH:MM")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD HH:MM")
    args=ap.parse_args()
    t0 = dt.datetime.fromisoformat(args.start)
    t1 = dt.datetime.fromisoformat(args.end)
    cats,tr = classify_interval(t0,t1)
    print(json.dumps({"start":args.start,"end":args.end,
                      "categories":cats,"triggers":tr}, ensure_ascii=False, indent=2))

if __name__=="__main__":
    main()
