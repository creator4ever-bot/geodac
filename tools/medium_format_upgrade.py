#!/usr/bin/env python3
import os, json, re
INP=os.environ.get("IN_JSON", os.path.expanduser('~/astro/transits_medium_for_ics.json'))
OUT=os.environ.get("OUT_JSON", os.path.expanduser('~/astro/transits_medium_for_ics.formatted.json'))

EMO={"Sun":"☉","Moon":"☽","Mercury":"☿","Venus":"♀","Mars":"♂","Jupiter":"♃","Saturn":"♄","Uranus":"♅","Neptune":"♆","Pluto":"♇",
     "Солнце":"☉","Луна":"☽","Меркурий":"☿","Венера":"♀","Марс":"♂","Юпитер":"♃","Сатурн":"♄","Уран":"♅","Нептун":"♆","Плутон":"♇"}
def to_emoji(s):
    for k,v in EMO.items(): s=s.replace(k,v)
    return s
def fmt_summary(s, houses):
    s = s or ""
    s = re.sub(r"\s*KATEX_INLINE_OPEN.*?KATEX_INLINE_CLOSE\s*"," ", s).replace("—"," ").replace("–"," ")
    s = to_emoji(s)
    s = re.sub(r"\s+"," ", s).strip()
    tr = (houses or {}).get('tr'); nat = (houses or {}).get('nat')
    tail=""
    if tr is not None and nat is not None:
        tail = f" (из H{nat} к H{tr})" if nat!=tr else f" (H{tr})"
    return s+tail

with open(INP,'r',encoding='utf-8') as f:
    data=json.load(f)
ev = data if isinstance(data,list) else data.get('events') or data.get('data') or []
out=[]
for e in ev:
    e2=dict(e)
    e2['summary']=fmt_summary(e.get('summary'), e.get('houses'))
    desc=e.get('description') or ""
    if "Профессиональный разбор" not in desc:
        head=("Профессиональный разбор: "+(" ".join(x for x in [e.get('transit'), e.get('aspect'), e.get('target')] if x))).strip()
        desc = head + ("\n"+desc if desc else "")
    e2['description']=desc
    out.append(e2)

with open(OUT,'w',encoding='utf-8') as g:
    if isinstance(data,list): json.dump(out,g,ensure_ascii=False,indent=2)
    else:
        data2=dict(data); 
        if 'events'in data2: data2['events']=out
        else: data2['data']=out
        json.dump(data2,g,ensure_ascii=False,indent=2)
print(f"wrote {OUT}; events={len(out)}")
