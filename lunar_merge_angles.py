import json, os, re, sys
from datetime import datetime, timezone, timedelta

# — helpers —
def parse_iso(s):
    s = str(s or '').strip()
    if not s: return None
    if s.endswith('Z'): s = s[:-1] + '+00:00'
    if 'T' not in s and ' ' in s: s = s.replace(' ', 'T', 1)
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
    else: dt = dt.astimezone(timezone.utc)
    return dt

def iso_z(dt): return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def is_angle_event(ssum: str) -> bool:
    ssum = ssum or ''
    return ('ASC/DSC' in ssum) or ('MC/IC' in ssum) or ('к горизонтали' in ssum) or ('к вертикали' in ssum)

def axis_of_target(tg: str):
    tg = (tg or '').upper()
    if tg in ('ASC','DSC','DESC'): return 'HOR'
    if tg in ('MC','IC'):          return 'VERT'
    return None

def axis_label(axis: str) -> str:
    return 'горизонтали (ASC/DSC)' if axis=='HOR' else 'вертикали (MC/IC)'

def axis_houses(axis: str) -> str:
    return 'H1/H7' if axis=='HOR' else 'H10/H4'

def strip_last_bracket(summary: str) -> str:
    if not summary: return summary
    r = max(summary.rfind(')'), summary.rfind('）'))
    if r == -1: return summary
    l = max(summary.rfind('(',0,r), summary.rfind('（',0,r))
    if l == -1 or l >= r: return summary
    return summary[:l].rstrip()

def sanitize_desc(desc: str) -> str:
    if not desc: return desc
    d = desc
    # «Стиль — … фокус — …» -> «Стиль — …; фокус — …»
    d = re.sub(r'(Стиль\s+—[^\n]*?)\s+фокус\s+—', r'\1; фокус —', d)
    # явный мусор из старого рендера: «\ фокус — …»
    d = d.replace('\\ фокус —', '; фокус —')
    # любые одиночные backslash перед пробелами — убираем
    d = re.sub(r'\\\s+', ' ', d)
    return d

def glyph(x): return x  # глифы оставляем как есть (они уже в for_ics)

# — core —
def merge_axes(input_path, output_path):
    raw = json.load(open(input_path, encoding='utf-8'))
    events = raw.get('events', raw)

    # Группируем осевые по (axis, transit), остальные — как есть
    idx_rest = []
    groups = {}
    for i, e in enumerate(events):
        tg = (e.get('target') or '').upper()
        ax = axis_of_target(tg)
        if not ax:
            idx_rest.append(i)
            continue
        tr = (e.get('transit') or '').upper()
        groups.setdefault((ax, tr), []).append(i)

    # Кластеризация по пересечению интервалов (с подушкой 6ч)
    def pdt(e):
        return parse_iso(e.get('start') or e.get('peak') or '')
    def pend(e):
        return parse_iso(e.get('end') or e.get('peak') or '')
    def overlap(a0,a1,b0,b1, pad=timedelta(hours=6)):
        if not a0 or not b0: return False
        A0, A1 = (a0, a1 or a0)
        B0, B1 = (b0, b1 or b0)
        return max(A0,B0) <= (min(A1,B1) + pad)

    merged = []

    for (axis, tr), idxs in groups.items():
        items = []
        for i in idxs:
            e = events[i]
            asp_raw = e.get('aspect') or ''
            asp_g = asp_raw if asp_raw in ('☌','☍','□','△','✶') else (e.get('aspect') or '')
            items.append({
                'i': i,
                'asp': asp_g,
                'tg': (e.get('target') or '').upper(),
                't0': pdt(e),
                't1': pend(e),
                'e':  e,
            })
        items.sort(key=lambda x: x['t0'] or datetime.max.replace(tzinfo=timezone.utc))
        # кластеризуем
        clusters, cur = [], []
        for it in items:
            if not cur:
                cur = [it]; continue
            a0,a1 = cur[-1]['t0'], (cur[-1]['t1'] or cur[-1]['t0'])
            b0,b1 = it['t0'],     (it['t1'] or it['t0'])
            if overlap(a0,a1,b0,b1): cur.append(it)
            else: clusters.append(cur); cur=[it]
        if cur: clusters.append(cur)

        # соберём осмысленные пары: должны присутствовать обе точки оси
        for cl in clusters:
            tgts = {x['tg'] for x in cl}
            if axis=='HOR' and not ('ASC' in tgts and ('DSC' in tgts or 'DESC' in tgts)): continue
            if axis=='VERT' and not ('MC' in tgts and 'IC' in tgts): continue

            # окно и середина
            c_t0 = min(x['t0'] for x in cl if x['t0'])
            c_t1 = max((x['t1'] or x['t0']) for x in cl if (x['t1'] or x['t0']))
            peak_dt = c_t0 + (c_t1 - c_t0)/2 if (c_t0 and c_t1) else (c_t0 or c_t1)

            # итоговый аспект: если один — берём его, если два — «☍/☌» или что ближе по порядку
            order = {'□':0,'☍':1,'△':2,'✶':3,'☌':4}
            asp_set = sorted({x['asp'] for x in cl}, key=lambda z: order.get(z,9))
            asp_str = asp_set[0] if len(asp_set)==1 else '/'.join(asp_set)

            # базовое событие (для описания)
            base = sorted(cl, key=lambda x: (order.get(x['asp'],9), x['t0'] or datetime.max.replace(tzinfo=timezone.utc)))[0]['e']
            base_desc = (base.get('description') or '').strip()

            # заголовок склейки
            hdr = ["Склейка по " + axis_label(axis) + ":"] + [
                f"• {x['asp']} {x['tg']}: {x['t0'].isoformat().replace('+00:00','Z')} → {(x['t1'] or x['t0']).isoformat().replace('+00:00','Z')}"
                for x in cl
            ]

            # знаки: берём по целям и транзиту
            def glyph_sign(v):
                g = str(v or '').upper()
                table = {'ARIES':'♈','TAURUS':'♉','GEMINI':'♊','CANCER':'♋','LEO':'♌','VIRGO':'♍','LIBRA':'♎',
                         'SCORPIO':'♏','SAGITTARIUS':'♐','CAPRICORN':'♑','AQUARIUS':'♒','PISCES':'♓'}
                return table.get(g, v or '')
            tr_sign = None
            asc_sign = None
            dsc_sign = None
            mc_sign  = None
            ic_sign  = None
            for x in cl:
                sg = x['e'].get('signs') or {}
                if sg.get('tr') and not tr_sign: tr_sign = glyph_sign(sg.get('tr'))
                tgt = x['tg']
                if axis=='HOR':
                    if tgt=='ASC' and not asc_sign: asc_sign = glyph_sign(sg.get('nat'))
                    if tgt in ('DSC','DESC') and not dsc_sign: dsc_sign = glyph_sign(sg.get('nat'))
                else:
                    if tgt=='MC' and not mc_sign: mc_sign = glyph_sign(sg.get('nat'))
                    if tgt=='IC' and not ic_sign: ic_sign = glyph_sign(sg.get('nat'))

            # описание: берём базовое и чистим
            base_lines = [ln for ln in base_desc.splitlines() if not re.match(r'^\s*(Знаки|Дома|Совет)\s*:', ln)]
            body = "\n".join([ln for ln in base_lines if ln.strip()])
            body = sanitize_desc(body)

            parts = ["\n".join(hdr)]
            if body: parts += ["", body]

            # Контекст: знаки/дома в явном формате
            if axis=='HOR':
                z = []
                if tr_sign:  z.append(f"☽={tr_sign}")
                if asc_sign: z.append(f"ASC={asc_sign}")
                if dsc_sign: z.append(f"DSC={dsc_sign}")
                if z: parts.append("Знаки: " + "; ".join(z))
                parts.append("Дома: Ось=H1/H7")
            else:
                z = []
                if tr_sign: z.append(f"☽={tr_sign}")
                if mc_sign: z.append(f"MC={mc_sign}")
                if ic_sign: z.append(f"IC={ic_sign}")
                if z: parts.append("Знаки: " + "; ".join(z))
                parts.append("Дома: Ось=H10/H4")

            desc = "\n".join(parts).strip()

            # Итоговый summary: без скобок «(из H…/Луна в H…)»
            sum_base = strip_last_bracket(base.get('summary') or '')
            # Пересобираем лаконично: оставляем только «к горизонтали/вертикали»
            if axis=='HOR':
                summary = f"☽ {asp_str} к горизонтали (ASC/DSC)"
            else:
                summary = f"☽ {asp_str} к вертикали (MC/IC)"

            merged.append({
                "summary": summary,
                "start": iso_z(c_t0) if c_t0 else None,
                "end":   iso_z(c_t1) if c_t1 else None,
                "peak":  iso_z(peak_dt) if peak_dt else (base.get('peak') or base.get('start') or ''),
                "description": desc,
                # houses: ось — не числовой дом; поле опускаем, чтобы не путать
            })

    # Все неосевые — как есть
    for i in idx_rest:
        merged.append(events[i])

    # Сортируем по времени
    def ev_t(e):
        return parse_iso(e.get('peak') or e.get('start') or '') or datetime.max.replace(tzinfo=timezone.utc)
    merged.sort(key=ev_t)

    json.dump({"events": merged}, open(output_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f"[merge-axes] {os.path.basename(input_path)} -> {os.path.basename(output_path)}; events={len(merged)}")

def main():
    if len(sys.argv) < 3:
        print("Usage: lunar_merge_angles.py input_for_ics.json output_merged.json"); sys.exit(2)
    merge_axes(sys.argv[1], sys.argv[2])

if __name__ == '__main__':
    main()
