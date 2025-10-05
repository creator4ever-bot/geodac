# ~/astro/tools/lunar_enrich_from_dedup.py
from pathlib import Path
import json, re, hashlib

p_in  = Path.home()/ "astro"/ "lunar_natal_forpush.dedup.json"
p_out = Path.home()/ "astro"/ "lunar_natal_forpush.json"

ASPECT = {
  "☌": ("Соединение","переключение, усиление темы"),
  "☍": ("Оппозиция","растяжка, балансировка"),
  "□": ("Квадрат","напряжение, задача к решению"),
  "△": ("Трин","синхронизация, облегчение"),
  "✶": ("Секстиль","возможность, лёгкий проход"),
}
AXIS = {
  "горизонтали": "контакты/взаимодействия/договорённости (ASC/DSC)",
  "вертикали":   "статус/роль vs комфорт/дом (MC/IC)",
}

rx_asp = re.compile(r"(?:Moon|☽)\s+([☌☍□△✶])\s+([A-Za-zА-Яа-я]+)")

def parse_kind(e):
    s = e.get("summary","")
    if "к горизонтали" in s: return ("AXIS","горизонтали",None)
    if "к вертикали"   in s: return ("AXIS","вертикали",None)
    m = rx_asp.search(s)
    if m: return ("ASP", m.group(1), m.group(2))
    return (None,None,None)

def desc_axis(kind):
    head = f"Осевая фигура: к {kind}"
    body = AXIS.get(kind,"Осевая фигура")
    adv  = "Совет: использовать окно для осознанной коррекции баланса."
    return head, "\n".join([body, adv])

def desc_aspect(sym, tgt):
    name, gist = ASPECT.get(sym,("Аспект",""))
    head = f"{name}: Луна {sym} {tgt}"
    body = f"Темы аспекта: {gist}\nРоль цели: {tgt} — по натальной теме."
    adv  = "Совет: отлавливать маркеры в быту/коммуникациях; идти по сигналам, не форсировать."
    return head, "\n".join([body, adv])

def ensure_id(e):
    priv = e.setdefault("extendedProperties",{}).setdefault("private",{})
    if "gd_id" not in priv:
        basis = f"{e.get('summary','')}|{e.get('start','')}"
        priv["gd_id"] = "gd"+hashlib.sha1(basis.encode("utf-8")).hexdigest()
    priv.setdefault("src","geodac")
    priv["pack"]="lunar_aspect_v1"
    priv["text_ver"]="1"

def main():
    data = json.loads(p_in.read_text(encoding="utf-8"))
    evs  = data.get("events",[])
    chg=0
    for e in evs:
        kind,a,b = parse_kind(e)
        if not kind: 
            continue
        if kind=="AXIS":
            h, t = desc_axis(a)
        else:
            h, t = desc_aspect(a,b)
        base = e.get("description") or ""
        # добавляем аккуратно, не дублируя заголовок
        if h not in base:
            e["description"] = ((h+"\n\n"+t) if not base else (base+"\n\n"+h+"\n\n"+t))
            ensure_id(e); chg+=1
    p_out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"enriched: {chg} of {len(evs)} -> {p_out}")

if __name__=="__main__":
    main()
