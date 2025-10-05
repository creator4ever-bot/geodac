import json, os, re
from datetime import datetime, timezone, timedelta

def norm(x):
    x = x % 360.0
    return x + 360.0 if x < 0 else x

def load_cusps():
    af = json.load(open(os.path.expanduser('~/astro/.state/natal_frame.json'), encoding='utf-8'))
    cusps = af.get('cusps') or []
    if cusps and cusps[0] is None:
        cusps = cusps[1:]
    C = [norm(float(c or 0.0)) for c in cusps]
    if len(C) != 12:
        raise RuntimeError(f"Bad cusps length: {len(C)}")
    return C

def house_of(lon, C):
    lon = norm(lon)
    for i in range(12):
        a = C[i]; b = C[(i+1)%12]
        if b < a: b += 360.0
        L = lon
        if L < a: L += 360.0
        if a <= L < b:
            return i+1
    return 12

def parse_iso(s):
    s = str(s or '').strip()
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
    return dt

def iso_z(dt):
    return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def is_angle_event(txt: str) -> bool:
    txt = txt or ''
    return any(k in txt for k in ('ASC/DSC','MC/IC','к горизонтали','к вертикали'))

def axis_label(summary: str) -> str:
    s = summary or ''
    return 'H1/H7' if ('ASC/DSC' in s or 'к горизонтали' in s) else 'H10/H4'

def last_bracket_span(s: str):
    right = max(s.rfind(')'), s.rfind('）'))
    if right == -1: return None
    left = max(s.rfind('(', 0, right), s.rfind('（', 0, right))
    if left == -1 or left >= right: return None
    return left, right

def rewrite_summary(summary: str, hmoon: int) -> str:
    span = last_bracket_span(summary or '')
    if not span: 
        return summary or ''
    l, r = span
    return (summary or '')[:l] + f"(Луна в H{hmoon})" + (summary or '')[r+1:]

def fix_punctuation(desc: str) -> str:
    return re.sub(r'(Стиль\s+—[^\\n]*?)\s+фокус\s+—', r'\\1; фокус —', desc or '')

def fix_signs_line(line: str) -> str:
    m = re.match(r'^\s*Знаки:\s*(.+?)\s*$', line or '')
    if not m: return line
    val = m.group(1)
    if '→' in val and '/' in val:
        left, right = val.split('→',1)
        left = left.strip()
        parts = right.split('/',1)
        if len(parts)==2:
            asc, dsc = parts[0].strip(), parts[1].strip()
            return f"Знаки: ☽={left}; ASC={asc}; DSC={dsc}"
    return line

def fix_houses_line_force(line: str, hmoon: int, axis: str) -> str:
    if str(line or '').strip().startswith('Дома:'):
        return f"Дома: ☽=H{hmoon}; Ось={axis}"
    return line

def moon_lon_jd(jd):
    import swisseph as swe
    # Эфемериды: ZET Swiss, если есть; иначе локальная папка
    for cand in ('/home/DAC/Zet9 GeoDAC/Swiss', os.path.expanduser('~/astro/ephe')):
        if os.path.exists(cand):
            swe.set_ephe_path(cand)
            break
    pos, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH)
    return norm(pos[0])

def jd_from_dt(dt):
    import swisseph as swe
    y,m,d = dt.year, dt.month, dt.day
    h = dt.hour + dt.minute/60 + dt.second/3600
    return swe.julday(y,m,d,h)

def middle_dt(start, end):
    ds = parse_iso(start); de = parse_iso(end)
    if ds and de:
        return ds + (de - ds)/2
    return ds or de

def process_file(path, C):
    data = json.load(open(path, encoding='utf-8'))
    evs = data.get('events', data)
    changed = 0
    for e in evs:
        ssum = e.get('summary') or ''
        if not is_angle_event(ssum):
            continue
        # peak: середина окна, если возможно
        peak_dt = parse_iso(e.get('peak'))
        mid = middle_dt(e.get('start'), e.get('end'))
        use_dt = mid or peak_dt
        if use_dt is None:
            continue
        jd = jd_from_dt(use_dt)
        lon = moon_lon_jd(jd)
        hmoon = house_of(lon, C)

        # houses.tr
        houses = e.get('houses') if isinstance(e.get('houses'),dict) else {}
        if houses.get('tr') != hmoon:
            houses['tr'] = hmoon
            e['houses'] = houses
            changed += 1

        # summary
        new_summary = rewrite_summary(ssum, hmoon)
        if new_summary != ssum:
            e['summary'] = new_summary
            changed += 1

        # description: пунктуация + Знаки/Дома
        desc = e.get('description') or ''
        if desc:
            axis = axis_label(ssum)
            d2 = fix_punctuation(desc)
            lines = []
            for L in d2.splitlines():
                L = fix_houses_line_force(L, hmoon, axis)
                L = fix_signs_line(L)
                lines.append(L)
            d3 = "\n".join(lines)
            if d3 != desc:
                e['description'] = d3
                changed += 1

        # peak — записываем середину окна (чтобы диагностика была однозначной)
        new_peak = iso_z(use_dt)
        if (e.get('peak') or '') != new_peak:
            e['peak'] = new_peak
            changed += 1

    if changed:
        json.dump(data, open(path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
        print(f"[rehouse+] {os.path.basename(path)} changed={changed}")
    else:
        print(f"[ok] {os.path.basename(path)} no changes")
    return changed

def main():
    C = load_cusps()
    total = 0
    for p in (os.path.expanduser('~/astro/lunar_natal_for_ics.json'),
              os.path.expanduser('~/astro/lunar_natal_merged.json')):
        if os.path.exists(p):
            total += process_file(p, C)
        else:
            print(f"[skip] {p} missing")
    print(f"[total changes] {total}")

if __name__ == '__main__':
    main()
