# -*- coding: utf-8 -*-
import os, sys, json, hashlib, importlib.util, re
from datetime import datetime, timezone

try:
    import yaml
except Exception:
    yaml = None

ASTRO = os.path.expanduser('~/astro')

def load_yaml(path, default=None):
    try:
        p = os.path.expanduser(path)
        if not os.path.exists(p): return default or {}
        import yaml as _yaml
        return _yaml.safe_load(open(p, 'r', encoding='utf-8')) or {}
    except Exception:
        return default or {}

CFG = load_yaml('~/astro/config.yaml', {})
GL  = load_yaml('~/astro/data/glyphs.yaml', {})
GL_B = (GL.get('bodies')  or {})
GL_A = (GL.get('aspects') or {})

# Глифы знаков
ZODIAC_GLYPH = {
  'ARIES':'♈','TAURUS':'♉','GEMINI':'♊','CANCER':'♋','LEO':'♌','VIRGO':'♍',
  'LIBRA':'♎','SCORPIO':'♏','SAGITTARIUS':'♐','CAPRICORN':'♑','AQUARIUS':'♒','PISCES':'♓'
}
def sign_glyph(name: str):
    if not name: return ''
    return ZODIAC_GLYPH.get((name or '').upper(), (name or '').title())

AXES_SKIP = {'ASC','DSC','DESC','MC','IC'}
ASPECT_FALLBACK = {
    # Пары-подсказки для fallback по аспекту
    '☍': 'баланс/перекалибровка',
    'opp': 'баланс/перекалибровка',
    '□' : 'напряжение/требует действия',
    'sqr': 'напряжение/требует действия',
    '△' : 'поддержка/поток',
    'tri': 'поддержка/поток',
    '✶' : 'возможность/шанс',
    'sex': 'возможность/шанс',
    '☌': 'фокус/сборка темы',
    'conj': 'фокус/сборка темы',
}
PAIR_FALLBACK = {
  ('MERCURY','MERCURY','□'): 'Сбои коммуникаций и суета; сузьте каналы, проверяйте факты.',
  ('SUN','MARS','△'):        'Поддержка действия; энергия течёт — продвиньте задачу.',
  ('MARS','MARS','□'):       'Внутренний конфликт импульсов; перенаправьте энергию в конкретную задачу.',
  ('MERCURY','MARS','□'):    'Споры/резкость в словах; дышите, формулируйте короче.',
}

def pair_fallback(ev, asp_sym):
    tr = (ev.get('transit') or '').upper()
    tg = (ev.get('target')  or '').upper()
    key = (tr, tg, asp_sym)
    if key in PAIR_FALLBACK:
        return PAIR_FALLBACK[key]
    # Общая подстраховка по домам
    hs = ev.get('houses') or {}
    fr, to = hs.get('tr'), hs.get('nat') or hs.get('tg')
    if asp_sym in ('□','☍') and (fr or to):
        return f'Напряжение между темами домов H{fr or "?"} и H{to or "?"}.'
    if asp_sym in ('△','✶') and (fr or to):
        return f'Поддержка между темами домов H{fr or "?"} и H{to or "?"}.'
    return None


def glyph_body(name: str) -> str:
    if not (CFG.get('glyphs',{}).get('enable', True)): return name or ''
    key = (name or '').upper()
    return GL_B.get(key, name or '')

def glyph_aspect(aspect: str) -> str:
    if not (CFG.get('glyphs',{}).get('enable', True)): return aspect or ''
    key = (aspect or '')
    if key in GL_A: return GL_A[key]
    low = key.lower()
    return GL_A.get(low, key)

def stable_id(ev):
    kind = (ev.get('type') or ev.get('category') or 'ASPECT').upper()
    tr   = (ev.get('transit') or '').upper()
    asp  = (ev.get('aspect') or '').lower()
    tg   = (ev.get('target') or '').upper()
    peak = (ev.get('peak') or '')
    if tr and asp and tg and peak:
        base = f"{kind}|{tr}|{asp}|{tg}|{peak}"
    else:
        base = json.dumps(ev, ensure_ascii=False, sort_keys=True)
    return "gd" + hashlib.sha1(base.encode('utf-8')).hexdigest()

def load_composer():
    p = os.path.join(ASTRO, 'compose_aspect_text.py')
    if not os.path.exists(p): return None
    spec = importlib.util.spec_from_file_location('composer', p)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

# NOTE (transit-to-natal overlay):
# - Интерпретация домов (houses.tr/houses.nat) относится к транзитам по наталу.
# - Для синастрий/хораров/соляров потребуются отдельные правила — не переносить эту логику как есть.
# - Коррекция houses.tr по аспекту (☍+6, □+3, △+4, ✶+2 от houses.nat) — эвристика для overlay.
def _houses_text(ev):
    hs = ev.get('houses')
    if not isinstance(hs, dict): return ''
    tg = (ev.get('target') or '').upper()
    if tg in AXES_SKIP: return ''
    htr = hs.get('tr'); htg = hs.get('nat') or hs.get('tg')
    if not (htr or htg): return ''
    return f"Дома: из H{htr or '?'} к H{htg or '?'}"

def make_glyph_summary(ev):
    tr = ev.get('transit'); tg = ev.get('target'); asp = ev.get('aspect')
    if not (tr and tg and asp):
        return ev.get('summary') or ''
    hs = ev.get('houses') if isinstance(ev.get('houses'), dict) else {}
    htr = hs.get('tr'); htg = hs.get('nat') or hs.get('tg')
    ssum = f"{glyph_body(tr)} {glyph_aspect(asp)} {glyph_body(tg)}"
    if str((tg or '').upper()) not in AXES_SKIP and (htr or htg):
        ssum += f" (из H{htr or '?'} к H{htg or '?'})"
    return ssum

def _normalize_desc(text: str) -> str:
    if not text: return ''
    t = text
    t = re.sub(r'([^\.\!\?])\s+(Фокус\s+—)', r'\1. \2', t)
    repl = {
        'Фактчек': 'Проверка информации',
        'Опростите': 'Упростите',
        'сервис': 'служение',
        'выходит на лицо': 'становится заметным',
    }
    for a,b in repl.items(): t = t.replace(a,b)
    lines = [x.strip() for x in re.split(r'\n+', t) if x.strip()]
    uniq=[]; seen=set()
    for line in lines:
        key = re.sub(r'\s+', ' ', line.lower())
        if key in seen: continue
        seen.add(key); uniq.append(line)
    return '\n'.join(uniq)

def _axis_square_preface(ev):
    axis = (ev.get('axis') or '').upper()
    asp  = str(ev.get('aspect') or '')
    if asp not in ('□','sqr','SQR'): return ''
    hs = ev.get('houses') or {}
    htr = hs.get('tr')
    if axis == 'VERT':
        return f"Квадрат к вертикали: напряжение между H{htr or '?'} и осью профессии/базы (H10/H4)."
    if axis in ('HOR','ASC','DSC','DESC'):
        return f"Квадрат к горизонтали: напряжение между H{htr or '?'} и осью личного/партнёрского (H1/H7)."
    return ''

def make_description_with_composer(ev, composer, dcts):
    try:
        tr = (ev.get('transit') or '').upper()
        tg = (ev.get('target')  or '').upper()
        r = composer.compose(
            transit={'planet': tr,
                     'sign': (ev.get('signs',{}) or {}).get('tr',''),
                     'house': str((ev.get('houses',{}) or {}).get('tr',''))},
            aspect=ev.get('aspect'),
            natal={'target': tg,
                   'sign': (ev.get('signs',{}) or {}).get('nat',''),
                   'house': str((ev.get('houses',{}) or {}).get('nat',''))},
            dcts=dcts
        )
        parts=[]
        axp = _axis_square_preface(ev)
        if axp: parts.append(axp)
        if (r.get('summary') or '').strip(): parts.append(r['summary'].strip())
        if (r.get('advice')  or '').strip(): parts.append("Совет: " + r['advice'].strip())
        ctx=[]
        hline = _houses_text(ev)
        if hline: ctx.append(hline)
        sg = ev.get('signs',{}) or {}
        if sg.get('tr') or sg.get('nat'): ctx.append(f"Знаки: {sign_glyph(sg.get('tr','?'))}→{sign_glyph(sg.get('nat','?'))}")
        if ctx: parts.append("; ".join(ctx))
        desc = "\n".join([p for p in parts if p])
        if desc: return desc
    except Exception:
        pass
    asp_raw = ev.get('aspect') or ''
    asp_sym = asp_raw if asp_raw in ('☌','☍','□','△','✶') else glyph_aspect(asp_raw)
    tr_g = glyph_body(ev.get('transit') or '')
    tg_g = glyph_body(ev.get('target')  or '')
    phrase = ASPECT_FALLBACK.get(asp_sym, 'взаимодействие')
    axp = _axis_square_preface(ev)
    fb = (axp + ("\n" if axp else "")) + f"{tr_g} {asp_sym} {tg_g} — {phrase}."
    ctx=[]
    hline = _houses_text(ev)
    if hline: ctx.append(hline)
    sg = ev.get('signs',{}) or {}
    if sg.get('tr') or sg.get('nat'): ctx.append(f"Знаки: {sign_glyph(sg.get('tr','?'))}→{sign_glyph(sg.get('nat','?'))}")
    if ctx: fb += "\n" + "; ".join(ctx)
    return fb

# Встроенная склейка осей (MC/IC и ASC/DSC)
def axis_unify_events(events, composer=None, dcts=None, tzname='Europe/Moscow'):
    try:
        from zoneinfo import ZoneInfo
    except Exception:
        ZoneInfo = None
    AX_VERT = {'MC','IC'}
    AX_HOR  = {'ASC','DSC','DESC'}
    ASPS_ORDER = {'□':0,'☍':1,'△':2,'✶':3}
    def pdt(x):
        if x is None: return None
        if isinstance(x, dict): x = x.get('dateTime') or x.get('date') or x
        s=str(x).strip()
        if not s: return None
        s=s.replace('Z','+00:00')
        for cand in (s, s.replace(' ','T')):
            try:
                d=datetime.fromisoformat(cand)
                if d.tzinfo is None and ZoneInfo:
                    d=d.replace(tzinfo=ZoneInfo(tzname))
                if d.tzinfo is None:
                    d=d.replace(tzinfo=timezone.utc)
                return d.astimezone(timezone.utc)
            except: pass
        return None
    def tstr(d): return d.isoformat().replace('+00:00','Z') if d else ''
    from datetime import timedelta
    def overlap(a0,a1,b0,b1, pad=timedelta(hours=6)):
        if not a0 or not b0: return False
        A0, A1 = (a0, a1 or a0); B0, B1 = (b0, b1 or b0)
        return max(A0,B0) <= (min(A1,B1) + pad)
    groups = {}; rest_idx=[]
    for i,e in enumerate(events):
        tgt = (e.get('target') or '').upper()
        if tgt in AX_VERT:
            key=('VERT', (e.get('transit') or '').upper()); groups.setdefault(key, []).append(i)
        elif tgt in AX_HOR:
            key=('HOR',  (e.get('transit') or '').upper()); groups.setdefault(key, []).append(i)
        else:
            rest_idx.append(i)
    to_remove=set(); new_events=[]
    def compose_desc(ev0):
        if composer and dcts:
            try:
                return make_description_with_composer(ev0, composer, dcts) or ''
            except Exception:
                return ''
        return ''
    for key, idxs in groups.items():
        axis, tr = key
        if len(idxs) < 2: continue
        items=[]
        for i in idxs:
            e=events[i]
            asp_raw = e.get('aspect') or ''
            asp_g = asp_raw if asp_raw in ('☌','☍','□','△','✶') else glyph_aspect(asp_raw)
            items.append({'i': i,'asp': asp_g,'tgt': (e.get('target') or '').upper(),
                          't0': pdt(e.get('start') or e.get('peak')),
                          't1': pdt(e.get('end')   or e.get('peak')),
                          'e' : e})
        items.sort(key=lambda x: x['t0'] or datetime.max.replace(tzinfo=timezone.utc))
        clusters=[]; cur=[]
        for it in items:
            if not cur: cur=[it]; continue
            a0,a1 = cur[-1]['t0'], (cur[-1]['t1'] or cur[-1]['t0'])
            b0,b1 = it['t0'],     (it['t1'] or it['t0'])
            if overlap(a0,a1,b0,b1): cur.append(it)
            else: clusters.append(cur); cur=[it]
        if cur: clusters.append(cur)
        for cl in clusters:
            tgts = {x['tgt'] for x in cl}
            if not (('MC' in tgts and 'IC' in tgts) or ('ASC' in tgts and ('DSC' in tgts or 'DESC' in tgts))): continue
            c_t0 = min(x['t0'] for x in cl if x['t0'])
            c_t1 = max((x['t1'] or x['t0']) for x in cl if (x['t1'] or x['t0']))
            aspects = sorted({x['asp'] for x in cl}, key=lambda z: ASPS_ORDER.get(z,9))
            asp_str = aspects[0] if len(aspects)==1 else '/'.join(aspects)
            axis_label = 'вертикали (MC/IC)' if axis=='VERT' else 'горизонтали (ASC/DSC)'
            from collections import Counter
            h_tr_vals=[]; nat_sign_vals=set(); tr_sign_vals=[]
            for x in cl:
                h=(x['e'].get('houses') or {})
                s=(x['e'].get('signs')  or {})
                if isinstance(h,dict) and h.get('tr') is not None: h_tr_vals.append(h.get('tr'))
                if isinstance(s,dict):
                    if s.get('tr'):  tr_sign_vals.append(s.get('tr'))
                    if s.get('nat'): nat_sign_vals.add(s.get('nat'))
            htr = Counter(h_tr_vals).most_common(1)[0][0] if h_tr_vals else None
            tr_sign = Counter(tr_sign_vals).most_common(1)[0][0] if tr_sign_vals else None
            homes_to = 'H10/H4' if axis=='VERT' else 'H1/H7'
            signs_line = None
            if tr_sign and nat_sign_vals:
                signs_line = f"{sign_glyph(tr_sign)}→" + "/".join(sign_glyph(z) for z in sorted(nat_sign_vals))
            def asp_weight(a): return ASPS_ORDER.get(a, 9)
            base_ev = sorted([x for x in cl], key=lambda x: (asp_weight(x['asp']), x['t0'] or datetime.max.replace(tzinfo=timezone.utc)))[0]['e']
            base_desc = compose_desc(base_ev) or (base_ev.get('description') or '')
            base_lines=[ln for ln in (base_desc or '').splitlines() if not re.match(r'^\s*(Знаки|Дома|Совет)\s*:', ln)]
            base_norm = "\n".join([ln for ln in base_lines if ln.strip()]).strip()
            hdr = ["Склейка по " + axis_label + ":"] + [
                f"• {x['asp']} {x['tgt']}: {x['t0'].isoformat().replace('+00:00','Z')} → {(x['t1'] or x['t0']).isoformat().replace('+00:00','Z')}" for x in cl
            ]
            parts = ["\n".join(hdr)]
            if base_norm: parts += ["", base_norm]
            extras=[]
            if signs_line: extras.append(f"Знаки: {signs_line}")
            if htr is not None: extras.append(f"Дома: H{htr} → {homes_to}")
            if extras: parts += [""] + extras
            summary = f"{glyph_body(tr)} {asp_str} к {axis_label}" + (f" (H{htr})" if htr is not None else "")
            new_e = {'summary': summary,'start': c_t0.isoformat().replace('+00:00','Z'),
                     'end': c_t1.isoformat().replace('+00:00','Z'),
                     'description': "\n".join(parts).strip(),
                     'axis_unify': '1','axis': axis}
            new_events.append(new_e)
            for x in cl: to_remove.add(x['i'])
    out=[]
    for i,e in enumerate(events):
        if i in to_remove: continue
        out.append(e)
    out.extend(new_events)
    return out

# Корректировка домов транзита по типу аспекта (если нужно)
# NOTE (transit-to-natal overlay):
# - Интерпретация домов (houses.tr/houses.nat) относится к транзитам по наталу.
# - Для синастрий/хораров/соляров потребуются отдельные правила — не переносить эту логику как есть.
# - Коррекция houses.tr по аспекту (☍+6, □+3, △+4, ✶+2 от houses.nat) — эвристика для overlay.

def adjust_houses_for_aspect(ev):
    """Disabled for natal pipeline: do nothing."""
    return None

def _parse_iso_z(s):
    from datetime import datetime, timezone
    s = str(s or '').strip()
    if not s: return None
    if s.endswith('Z'): s = s[:-1] + '+00:00'
    if 'T' not in s and ' ' in s: s = s.replace(' ', 'T', 1)
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
    else: dt = dt.astimezone(timezone.utc)
    return dt

def _iso_z(dt):
    from datetime import timezone
    return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def normalize_axis_event(ev: dict) -> dict:
    # Только для осевых событий
    axis = (ev.get('axis') or '').upper()
    if axis not in ('HOR','VERT'):
        return ev

    # 1) peak = середина окна (если можно)
    t0 = _parse_iso_z(ev.get('start') or ev.get('peak'))
    t1 = _parse_iso_z(ev.get('end')   or ev.get('peak'))
    mid = None
    if t0 and t1:
        mid = t0 + (t1 - t0)/2
    elif t0 or t1:
        mid = t0 or t1
    if mid:
        ev['peak'] = _iso_z(mid)

    # 2) summary: убрать любые скобки "(…)" и собрать лаконично
    import re as _re
    asp = ev.get('aspect') or ''
    # если аспект типа "opp" — оставим как есть; часто уже глиф "☍/☌"
    lab = "к горизонтали (ASC/DSC)" if axis=='HOR' else "к вертикали (MC/IC)"
    ssum = ev.get('summary') or ''
    # сносим финальные скобки
    ssum = _re.sub(r'\s*KATEX_INLINE_OPEN[^)]+?KATEX_INLINE_CLOSE\s*$', '', ssum).strip()
    # если в summary нет нашей фразы — пересоберём
    if 'к горизонтали' not in ssum and 'к вертикали' not in ssum:
        ssum = f"{(ev.get('transit') or '').upper()} {asp} {lab}"
    else:
        # заменим хвост на правильную подпись оси
        ssum = _re.sub(r'(к (горизонтали|вертикали).*?)$', lab, ssum)
    ev['summary'] = ssum

    # 3) description: нормализуем «Знаки/Дома» и пунктуацию
    desc = ev.get('description') or ''
    if desc:
        # «Стиль — … фокус — …» => «Стиль — …; фокус — …»
        desc = _re.sub(r'(Стиль\s+—[^\n]*?)\s+фокус\s+—', r'\1; фокус —', desc)
        # «Знаки: ♌→♒/♌» -> «Знаки: ☽=♌; ASC=♒; DSC=♌» (для гориз.) / «…; MC=…; IC=…» (для вертик.)
        if 'Знаки:' in desc and '→' in desc and '/' in desc:
            if axis=='HOR':
                desc = _re.sub(r'Знаки:\s*([^\s→]+)→([^\s/]+)/([^\s]+)',
                               r'Знаки: ☽=\1; ASC=\2; DSC=\3', desc)
            else:
                desc = _re.sub(r'Знаки:\s*([^\s→]+)→([^\s/]+)/([^\s]+)',
                               r'Знаки: ☽=\1; MC=\2; IC=\3', desc)
        # «Дома: H5 → H1/H7» -> «Дома: Ось=H1/H7» (или H10/H4)
        homes = 'H1/H7' if axis=='HOR' else 'H10/H4'
        desc = _re.sub(r'Дома:\s*H\d+\s*→\s*H\d+/H\d+', f'Дома: Ось={homes}', desc)
        # артефакт «\ фокус —» -> «; фокус —»
        desc = desc.replace('\ фокус —', '; фокус —')
        # любой одиночный backslash перед пробелами — убираем
        desc = _re.sub(r'\\s+', ' ', desc)
        ev['description'] = desc

    # 4) houses: для осевых не указываем числовой дом (ось ≠ дом)
    if isinstance(ev.get('houses'), dict):
        ev.pop('houses', None)

    return ev
def transform(in_path, out_path):
    composer = load_composer()
    dcts = composer.load_dicts() if composer and hasattr(composer,'load_dicts') else None
    data = json.load(open(os.path.expanduser(in_path), 'r', encoding='utf-8'))
    events = data.get('events') if isinstance(data, dict) else data
    # Склейка осей до рендера
    events = axis_unify_events(events, composer, dcts)
    events = [normalize_axis_event(e) for e in events]
    out = {'events': []}
    for ev in events:
        # Корректируем дом транзита по аспекту (если нужно)
        # pass  # adjust_houses_for_aspect disabled for natal pipeline  # disabled for natal pipeline
        new_ev = {}
        for k in ('peak','start','end','type'):
            if ev.get(k): new_ev[k] = ev[k]
        new_ev['category'] = str(ev.get('category') or 'Astro')
        new_ev['alarm'] = ev.get('alarm') if isinstance(ev.get('alarm'), str) else (str(ev.get('alarm')) if ev.get('alarm') is not None else '')
        for k in ('transit','aspect','target','signs','houses','axis'):
            if k in ev: new_ev[k] = ev[k]
        axis = (ev.get('axis') or '').upper()
        if axis in ('HOR','VERT'):
            lab = 'к горизонтали (ASC/DSC)' if axis=='HOR' else 'к вертикали (MC/IC)'
            s_in = ev.get('summary') or ''
            import re as _re
            m = _re.search(r'(☌/☍|☍/☌|☌|☍|□|△|✶)', s_in)
            asp = m.group(1) if m else ''
            if asp:
                new_ev['summary'] = f"☽ {asp} {lab}"
            else:
                s2 = _re.sub(r'^\s*(MOON|ЛУНА)\s+', '☽ ', s_in, flags=_re.I)
                s2 = _re.sub(r'\s*\KATEX_INLINE_OPEN[^)]+?\KATEX_INLINE_CLOSE\s*$', '', s2).strip()
                new_ev['summary'] = s2 if s2 else f"☽ {lab}"
        else:
            new_ev['summary'] = make_glyph_summary(ev) or ev.get('summary') or 'Event'
        desc = ev.get('description') or ''
        if (not desc) and composer and dcts and ev.get('transit') and ev.get('aspect') and ev.get('target'):
            desc = make_description_with_composer(ev, composer, dcts)
        if not desc:
            desc = make_description_with_composer(ev, None, None)
        new_ev['description'] = _normalize_desc(desc)
        new_ev['gd_id'] = ev.get('gd_id') or stable_id({**ev, **new_ev})
        out['events'].append(new_ev)
    with open(os.path.expanduser(out_path), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"OK: wrote {len(out['events'])} events -> {out_path}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python render_for_ics.py IN.json OUT.json")
        sys.exit(1)
    transform(sys.argv[1], sys.argv[2])
