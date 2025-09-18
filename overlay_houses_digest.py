#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, json, re
from datetime import datetime, timedelta, timezone

# optional YAML (themes/roles), не обязателен
try:
    import yaml
except Exception:
    yaml = None

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

TZ = os.environ.get('TZ', 'Europe/Moscow')

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
        z = ZoneInfo(TZ) if ZoneInfo else timezone.utc
        dt = dt.replace(tzinfo=z)
    return dt

def day_bounds(now=None):
    z = ZoneInfo(TZ) if ZoneInfo else timezone.utc
    now = now or datetime.now(tz=z)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end

def load_json(path):
    p = os.path.expanduser(path)
    with open(p, encoding='utf-8') as f:
        data = json.load(f)
    return data.get('events', data)

def load_packs():
    packs = {}
    if not yaml:
        return packs
    p = os.path.expanduser('~/astro/packs/overlay_houses.yaml')
    if os.path.exists(p):
        try:
            with open(p, 'r', encoding='utf-8') as f:
                packs = yaml.safe_load(f) or {}
        except Exception:
            packs = {}
    return packs

def house_theme(packs, hnum):
    hmap = (packs.get('houses') or {})
    key = f"H{hnum}"
    entry = hmap.get(key) or hmap.get(hnum) or {}
    for k in ('title', 'name', 'theme'):
        if isinstance(entry, dict) and entry.get(k):
            return str(entry.get(k))
    if isinstance(entry, dict):
        th = entry.get('themes') or entry.get('topics') or []
        if isinstance(th, list) and th:
            return str(th[0])
    return ''

def planet_role(packs, glyph_or_name):
    planets = (packs.get('planets') or {})
    roles = planets.get('roles') or {}
    return roles.get(glyph_or_name) or ''

def main():
    CDIR = os.path.expanduser('~/astro')
    spans_path = os.path.join(CDIR, 'overlay_spans.json')
    forpush_path = os.path.join(CDIR, 'overlay_houses_forpush.json')
    if not os.path.exists(spans_path) or not os.path.exists(forpush_path):
        print("[digest] missing spans/forpush -> skip")
        return

    spans = load_json(spans_path)
    packs = load_packs()
    today_start, today_end = day_bounds()

    houses = {i: [] for i in range(1, 13)}
    for ev in spans:
        s = ev.get('summary') or ''
        m = re.search(r'([^\s]+)\s+в\s+H(\d+)', s)
        if not m:
            continue
        glyph, h = m.group(1), int(m.group(2))
        st = parse_iso(ev.get('start')); en = parse_iso(ev.get('end'))
        if not st and not en:
            continue
        A0, A1 = st or today_start, en or today_end
        if max(A0, today_start) <= min(A1, today_end):
            until = en.astimezone(today_start.tzinfo).strftime('%Y-%m-%d %H:%M') if en else ''
            role  = planet_role(packs, glyph) or ''
            houses[h].append((glyph, role, until))

    lines = []
    for h in range(1, 13):
        if not houses[h]:
            continue
        theme = house_theme(packs, h)
        head  = f"H{h}" + (f" (тема: {theme})" if theme else "")
        entries = []
        for g, role, until in sorted(houses[h], key=lambda x: x[2] or ''):
            item = f"{g}"
            if role:
                item += f" ({role})"
            if until:
                item += f" до {until}"
            entries.append(item)
        lines.append(f"{head}: " + "; ".join(entries))

    if not lines:
        print("[digest] nothing to report for today")
        return

    start_date, _ = day_bounds()
    title = f"Сводка: планеты в домах (сегодня, {start_date.date().isoformat()})"
    desc  = "Состояние на сегодня:\n" + "\n".join(lines)

    with open(forpush_path, encoding='utf-8') as f:
        fp = json.load(f)
    evs = fp.get('events', fp)

    start_date_str = start_date.date().isoformat()
    end_date_str   = (start_date + timedelta(days=1)).date().isoformat()

    digest = {
        "summary": title,
        "description": desc,
        "start": {"date": start_date_str},
        "end":   {"date": end_date_str},
        "extendedProperties": {"private": {"overlay": "houses", "digest": "1"}}
    }

    clean = []
    for e in evs:
        if (isinstance(e.get('summary'), str) and e['summary'].startswith("Сводка: планеты в домах")
            and (e.get('start', {}) or {}).get('date') == start_date_str):
            continue
        clean.append(e)
    clean.append(digest)

    out = {"events": clean}
    with open(forpush_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    houses_with_entries = sum(1 for v in houses.values() if v)
    print(f"[digest] appended daily summary -> {forpush_path}; houses_with_entries={houses_with_entries}")

if __name__ == '__main__':
    main()
