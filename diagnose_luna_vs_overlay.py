#!/usr/bin/env python3
import os, json, re
from datetime import datetime, timezone
import swisseph as swe

EPHE_CAND = (
    '/home/DAC/Zet9 GeoDAC/Swiss',
    os.path.expanduser('~/astro/ephe'),
)

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
        raise RuntimeError(f'Bad cusps length: {len(C)}')
    return C

def house_of(lon, C):
    lon = norm(lon)
    for i in range(12):
        a, b = C[i], C[(i+1)%12]
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
    # Наивное время трактуем как локальное (Europe/Moscow), как в пайплайне
    try:
        from zoneinfo import ZoneInfo
    except Exception:
        ZoneInfo = None
    if dt.tzinfo is None:
        if ZoneInfo:
            dt = dt.replace(tzinfo=ZoneInfo('Europe/Moscow'))
        else:
            # запасной вариант: ставим UTC (хуже, но детерминированно)
            dt = dt.replace(tzinfo=timezone.utc)
    return dt

def moon_lon(dt):
    # Переводим момент в UTC и считаем jd
    for ephe in EPHE_CAND:
        if os.path.exists(ephe):
            swe.set_ephe_path(ephe)
            break
    dt_utc = dt.astimezone(timezone.utc)
    y, m, d = dt_utc.year, dt_utc.month, dt_utc.day
    h = dt_utc.hour + dt_utc.minute/60 + dt_utc.second/3600
    jd = swe.julday(y, m, d, h)
    pos, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH)
    return norm(pos[0])

def reported_tr_house(ev):
    # 1) из поля houses.tr
    hs = ev.get('houses')
    if isinstance(hs, dict) and 'tr' in hs:
        try:
            return int(hs['tr'])
        except Exception:
            pass
    # 2) из summary "(из Hn ...)" — на случай старых событий
    s = ev.get('summary') or ''
    m = re.search(r'из\s*H(\d+)', s)
    if m:
        return int(m.group(1))
    return None

def main():
    C = load_cusps()
    p = os.path.expanduser('~/astro/lunar_natal_merged.json')
    data = json.load(open(p, encoding='utf-8'))
    evs = data.get('events', data)

    total = mism = 0
    mismlist = []

    for e in evs:
        # Пропускаем осевые события: у осей нет числового «дома Луны» (это про ось)
        axis = (e.get('axis') or '').upper()
        if axis in ('HOR','VERT'):
            continue

        # Берём только лунные транзиты
        trn = (e.get('transit') or '').upper()
        ssum = e.get('summary') or ''
        if trn:
            if trn not in ('MOON','ЛУНА'):
                continue
        else:
            if not (ssum.strip().startswith('☽') or re.search(r'\b(MOON|ЛУНА)\b', ssum, re.I)):
                continue

        # Время события
        peak = e.get('peak') or e.get('start') or e.get('end')
        dt = parse_iso(peak)
        if not dt:
            continue

        # Дом из события
        rep = reported_tr_house(e)
        if rep is None:
            continue

        # Дом по расчёту
        lon = moon_lon(dt)
        calc = house_of(lon, C)

        total += 1
        if rep != calc:
            mism += 1
            if len(mismlist) < 10:
                mismlist.append((ssum, peak, rep, calc))

    acc = (1.0 - (mism / total if total else 0.0)) * 100.0
    print(f"Total lunar aspects (non-axis): {total}; OK={total - mism}; MISM={mism}; ACC={acc:.1f}%")
    for s, t, rep, calc in mismlist:
        print(f"- {s} @ {t} | event H{rep} vs calc H{calc}")

if __name__ == '__main__':
    main()
