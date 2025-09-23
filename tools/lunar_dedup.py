# ~/astro/tools/lunar_dedup.py
from pathlib import Path
import json, re, sys

src = Path(sys.argv[1]) if len(sys.argv)>1 else Path.home()/ "astro"/ "lunar_natal_merged.json"
dst = Path(sys.argv[2]) if len(sys.argv)>2 else Path.home()/ "astro"/ "lunar_natal_forpush.json"

d = json.loads(src.read_text(encoding="utf-8"))
evs = d.get("events",[])

def norm_key(s):
    s = s or ""
    s = re.sub(r"\s*KATEX_INLINE_OPEN(ASC/DSC|MC/IC|Луна в H\d+)KATEX_INLINE_CLOSE\s*", "", s, flags=re.I)
    s = s.replace("ASC/DSC","").replace("MC/IC","")
    s = re.sub(r"\s+"," ",s).strip().lower()
    return s

def score(e):
    s = e.get("summary","")
    desc = e.get("description") or ""
    has_house = bool(re.search(r"Луна в H\d+", s))
    return (1 if has_house else 0, len(desc), len(s))

from collections import defaultdict
grp = defaultdict(list)
for e in evs:
    grp[norm_key(e.get("summary",""))].append(e)

out = []
for k,arr in grp.items():
    if len(arr)==1: out.append(arr[0]); continue
    best = sorted(arr, key=score, reverse=True)[0]
    out.append(best)

dst.write_text(json.dumps({"events":out}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"dedup -> {dst} events:{len(out)}")
