#!/usr/bin/env python3
from pathlib import Path
import json, argparse, datetime as dt, re

# -------- helpers --------
def _read_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _events_from(obj):
    if isinstance(obj, dict):
        return obj.get("events") or obj.get("items") or []
    if isinstance(obj, list):
        return obj
    return []

def _parse_dt(s):
    if not s:
        return None
    s = s.replace("T", " ").replace("Z", "")
    s = s[:16]
    try:
        return dt.datetime.fromisoformat(s)
    except Exception:
        return None

def ev_start(e):
    sd = e.get("start")
    if isinstance(sd, dict):
        return _parse_dt(sd.get("dateTime") or sd.get("date"))
    return _parse_dt(e.get("start") or e.get("peak") or e.get("end"))

def ev_end(e):
    ed = e.get("end")
    if isinstance(ed, dict):
        return _parse_dt(ed.get("dateTime") or ed.get("date"))
    return _parse_dt(e.get("end") or e.get("peak") or e.get("start"))

def overlaps(e, t0, t1):
    st = ev_start(e)
    en = ev_end(e) or st
    if not st:
        return False
    if en < st:
        en = st
    return not (en < t0 or st > t1)

# -------- loaders --------
def load_lunar():
    home = Path.home()/ "astro"
    for name in ("lunar_natal_forpush.json",
                 "lunar_natal_forpush.dedup.json",
                 "lunar_natal_merged.json",
                 "lunar_natal_for_ics.json"):
        p = home/name
        if p.exists():
            return _events_from(_read_json(p))
    return []

def load_medium():
    home = Path.home()/ "astro"
    for name in ("transits_medium_for_ics.json", "transits_medium.json"):
        p = home/name
        if p.exists():
            return _events_from(_read_json(p))
    return []

def load_long():
    home = Path.home()/ "astro"
    for name in ("transits_long_for_ics.json", "transits_long.json"):
        p = home/name
        if p.exists():
            return _events_from(_read_json(p))
    return []

# -------- classifier --------
FAST  = {"Sun","Mercury","Venus","Mars","Солнце","Меркурий","Венера","Марс"}
OUTER = {"Uranus","Neptune","Pluto","Уран","Нептун","Плутон"}
LIGHT = {"Sun","Moon","Солнце","Луна","Asc","ASC","Асц","MC"}

RX_OUTER = re.compile(r"(Uranus|Neptune|Pluto|Уран|Нептун|Плутон)", re.I)

def is_hard_aspect(e):
    deg = e.get("aspect_deg")
    if isinstance(deg,(int,float)) and int(round(deg)) in (90,180):
        return True
    s = (e.get("summary") or "")
    return ("□" in s) or ("☍" in s)

def is_soft_aspect(e):
    deg = e.get("aspect_deg")
    if isinstance(deg,(int,float)) and int(round(deg)) in (60,120):
        return True
    s = (e.get("summary") or "")
    return ("△" in s) or ("✶" in s)

def is_conj(e):
    deg = e.get("aspect_deg")
    if isinstance(deg,(int,float)) and int(round(deg)) == 0:
        return True
    s = (e.get("summary") or "")
    return ("☌" in s)

def classify_interval(t0, t1):
    evs_l = [e for e in load_lunar()  if overlaps(e, t0, t1)]
    evs_m = [e for e in load_medium() if overlaps(e, t0, t1)]
    evs_g = [e for e in load_long()   if overlaps(e, t0, t1)]

    cats, triggers, flags = [], [], []

    if not (evs_l or evs_m or evs_g):
        return [("garbage", 0.6)], triggers, flags

    # signals (medium/long по полям + lunar по summary)
    fast_to_inner = any((e.get("transit") in FAST) for e in evs_m)
    fast_to_outer = any((e.get("transit") in FAST) and (e.get("target") in OUTER) for e in evs_m)
    outer_to_lights = any((e.get("transit") in OUTER) and (e.get("target") in LIGHT) for e in (evs_m+evs_g))

    s_l = [ (e.get("summary") or "") for e in evs_l ]
    if any(RX_OUTER.search(s) for s in s_l):
        outer_to_lights = True

    # эвристические флаги
    # кошмар: жёсткие (□/☍) к Mars/Saturn/Neptune/Pluto либо много жёстких в окне
    hard_targets = {"Mars","Saturn","Neptune","Pluto","Марс","Сатурн","Нептун","Плутон"}
    hard_hits = any(is_hard_aspect(e) and any(w==e.get("target") or w in (e.get("summary") or "") for w in hard_targets) for e in evs_m) \
                or sum(1 for e in evs_l if is_hard_aspect(e)) >= 2
    if hard_hits:
        flags.append("nightmare")

    # инсайт: мягкие (△/✶) к Uranus/Neptune/Mercury или конъюнкция с ними
    soft_hits = any(is_soft_aspect(e) and (e.get("target") in {"Uranus","Neptune","Mercury","Уран","Нептун","Меркурий"}) for e in evs_m) \
                or any((("△" in s or "✶" in s or "☌" in s) and any(k in s for k in ("Uranus","Neptune","Mercury","Уран","Нептун","Меркурий"))) for s in s_l)
    if soft_hits:
        flags.append("insight")

    # запоминаемость: множественность или конъюнкция с ME/UR/NE/outer_to_lights
    if (len(evs_l)+len(evs_m)+len(evs_g) >= 3) or outer_to_lights or \
       any(is_conj(e) and (e.get("target") in {"Mercury","Uranus","Neptune","Меркурий","Уран","Нептун"}) for e in evs_m):
        flags.append("recall_high")

    # категории (как раньше)
    if outer_to_lights or fast_to_outer:
        cats.append(("archetypal", 0.7 if outer_to_lights else 0.65))
        triggers.append("outer→lights" if outer_to_lights else "fast→outer")
    if fast_to_inner or any(any(w in s for w in FAST) for s in s_l):
        cats.append(("repressed", 0.6))
        triggers.append("fast→inner")
    if not cats:
        cats.append(("garbage", 0.5))
        triggers.append("no strong trig")

    if len(evs_l)+len(evs_m)+len(evs_g) >= 2:
        triggers.append(f"multiplicity:{len(evs_l)+len(evs_m)+len(evs_g)}")

    return cats, triggers, flags

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end",   required=True)
    args = ap.parse_args()
    t0 = dt.datetime.fromisoformat(args.start)
    t1 = dt.datetime.fromisoformat(args.end)
    cats, trg, flags = classify_interval(t0, t1)
    print(json.dumps({"start": args.start, "end": args.end,
                      "categories": cats, "triggers": trg, "flags": flags},
                     ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
