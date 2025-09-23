# ~/astro/tools/mundane_ingress_apply_composer.py
from pathlib import Path
import json, re, hashlib
try:
    import yaml
except Exception:
    yaml = None

SIGNS = {
    "♈":"Aries","Овен":"Aries","Aries":"Aries",
    "♉":"Taurus","Телец":"Taurus","Taurus":"Taurus",
    "♊":"Gemini","Близнецы":"Gemini","Gemini":"Gemini",
    "♋":"Cancer","Рак":"Cancer","Cancer":"Cancer",
    "♌":"Leo","Лев":"Leo","Leo":"Leo",
    "♍":"Virgo","Дева":"Virgo","Virgo":"Virgo",
    "♎":"Libra","Весы":"Libra","Libra":"Libra",
    "♏":"Scorpio","Скорпион":"Scorpio","Scorpio":"Scorpio",
    "♐":"Sagittarius","Стрелец":"Sagittarius","Sagittarius":"Sagittarius",
    "♑":"Capricorn","Козерог":"Capricorn","Capricorn":"Capricorn",
    "♒":"Aquarius","Водолей":"Aquarius","Aquarius":"Aquarius",
    "♓":"Pisces","Рыбы":"Pisces","Pisces":"Pisces",
}
PLANETS = {
    "☉":"Sun","Солнце":"Sun","Sun":"Sun",
    "☿":"Mercury","Меркурий":"Mercury","Mercury":"Mercury",
    "♀":"Venus","Венера":"Venus","Venus":"Venus",
    "♂":"Mars","Марс":"Mars","Mars":"Mars",
    "♃":"Jupiter","Юпитер":"Jupiter","Jupiter":"Jupiter",
    "♄":"Saturn","Сатурн":"Saturn","Saturn":"Saturn",
    "♅":"Uranus","Уран":"Uranus","Uranus":"Uranus",
    "♆":"Neptune","Нептун":"Neptune","Neptune":"Neptune",
    "♇":"Pluto","Плутон":"Pluto","Pluto":"Pluto",
}

rx_ing = re.compile(r'(ингресс|ingress|→)', re.I)

def detect_ingress(summary:str):
    if not rx_ing.search(summary or ""):
        return None
    # найдём планету и знак по символу/слову
    planet_key = None
    for k in PLANETS:
        if k in summary:
            planet_key = k; break
    sign_key = None
    for k in SIGNS:
        if k in summary:
            sign_key = k; break
    if not planet_key or not sign_key:
        return None
    return PLANETS[planet_key], SIGNS[sign_key]

def load_pack(ppath:Path):
    pack = {"signs":{}, "planets":{}, "template":{
        "header":"Ингресс: {planet} в {sign}",
        "body":"Ключ знака ({sign}): {sign_gist}\nРоль планеты: {planet_role}",
        "advice":"Совет: наблюдать маркеры по тематике знака."
    }}
    if yaml and ppath.exists():
        data = yaml.safe_load(ppath.read_text(encoding="utf-8"))
        pack["signs"]   = data.get("signs",{}) or {}
        pack["planets"] = data.get("planets",{}) or {}
        pack["template"]= data.get("template", pack["template"])
    return pack

def compose_text(planet:str, sign:str, pack:dict):
    s = pack["signs"].get(sign, {})
    p = pack["planets"].get(planet, "")
    tpl = pack["template"]
    header = tpl.get("header","").format(planet=planet, sign=s.get("title", sign))
    body   = tpl.get("body","").format(sign=s.get("title", sign), sign_gist=s.get("gist",""), planet_role=p)
    advice = tpl.get("advice","")
    return header, "\n".join([body, advice]).strip()

def enrich(in_path:Path, out_path:Path, pack_path:Path):
    data = json.loads(in_path.read_text(encoding="utf-8"))
    evs  = data.get("events", [])
    pack = load_pack(pack_path)
    changed = 0
    for e in evs:
        res = detect_ingress(e.get("summary",""))
        if not res: 
            continue
        planet, sign = res
        header, body = compose_text(planet, sign, pack)
        # если description пустая/шаблонная — заменим/добавим
        desc = e.get("description") or ""
        # Формируем многострочную, оставляя исходный summary как есть
        e["description"] = f"{header}\n\n{body}".strip()
        # пометим маркеры
        priv = e.setdefault("extendedProperties", {}).setdefault("private", {})
        priv.setdefault("src","geodac")
        priv["pack"] = "mundane_ingress_v1"
        priv["text_ver"] = "1"
        # стабилизируем gd_id если его нет
        if "gd_id" not in priv:
            basis = f"ingress|{e.get('summary','')}|{e.get('start','')}"
            priv["gd_id"] = "gd"+hashlib.sha1(basis.encode("utf-8")).hexdigest()
        changed += 1
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return changed, len(evs)

if __name__ == "__main__":
    import sys
    home = Path.home()
    in_path  = home/"astro"/"mundane_forpush.normalized.json"
    out_path = home/"astro"/"mundane_forpush.enriched.json"
    pack_path= home/"astro"/"packs"/"mundane_ingress.yaml"
    chg,total = enrich(in_path, out_path, pack_path)
    print(f"enriched: changed={chg} of {total} -> {out_path}")
