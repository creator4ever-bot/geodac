import json, os, re
from datetime import datetime, timezone

# Простая нормализация
def norm(x): 
    x = x % 360.0
    return x + 360.0 if x < 0 else x

# Берём cusps из активной натальной сетки
af = json.load(open(os.path.expanduser('~/astro/.state/natal_frame.json'), encoding='utf-8'))
cusps = af.get('cusps') or []
# ожидаем [None, cusp1..cusp12]
if cusps and cusps[0] is None:
    cusps = cusps[1:]
cusps = [norm(float(c or 0.0)) for c in cusps]
if len(cusps) != 12:
    raise SystemExit(f"Bad cusps length: {len(cusps)}")

def house_of(lon, cusps):
    lon = norm(lon)
    # Последовательно проверяем интервалы [c_k, c_{k+1})
    for i in range(12):
        a = cusps[i]
        b = cusps[(i+1) % 12]
        if b < a:  # переход через 360
            b += 360.0
        L = lon
        if L < a: 
            L += 360.0
        if a <= L < b:
            return i+1
    return 12

def jd_from_iso(s):
    # '2025-09-07T04:59:00Z' или '2025-09-07 04:59'
    s = str(s).strip()
    if not s:
        return None
    if s.endswith('Z'):
        s = s[:-1] + '+00:00'
    if 'T' not in s and ' ' in s:
        s = s.replace(' ', 'T', 1)
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    y, m, d = dt.year, dt.month, dt.day
    h = dt.hour + dt.minute/60 + dt.second/3600
    # швейцарский юлианский день
    import swisseph as swe
    return swe.julday(y, m, d, h)

def moon_lon_jd(jd):
    import swisseph as swe, os
    swe.set_ephe_path(os.path.expanduser('~/astro/ephe'))
    pos, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH)
    return norm(pos[0])

def is_angle_event(s):
    return any(k in s for k in ('ASC/DSC','MC/IC','к горизонтали','к вертикали'))

def fix_file(path):
    data = json.load(open(path, encoding='utf-8'))
    evs = data.get('events', data)
    changed = mism = 0
    for e in evs:
        s = (e.get('summary') or '')
        if not is_angle_event(s):
            continue
        peak = e.get('peak') or e.get('start') or e.get('end')
        if not peak:
            continue
        jd = jd_from_iso(peak)
        if not jd:
            continue
        try:
            lon = moon_lon_jd(jd)
        except Exception:
            continue
        tr = house_of(lon, cusps)
        houses = e.get('houses') if isinstance(e.get('houses'), dict) else {}
        if houses.get('tr') != tr:
            houses['tr'] = tr
            e['houses'] = houses
            changed += 1
    if changed:
        json.dump(data, open(path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f"[rehouse] {os.path.basename(path)} changed={changed}")
    return changed

total = 0
for p in (os.path.expanduser('~/astro/lunar_natal_for_ics.json'),
          os.path.expanduser('~/astro/lunar_natal_merged.json')):
    total += fix_file(p)
print(f"[total changes] {total}")
