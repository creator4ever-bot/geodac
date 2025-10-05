#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# GeoDAC: Lunar angles postfix (stub)
# Назначение: оставить файл пайплайна неизменным, лишь подтверждать вызов.
# Если позже потребуется логика — заменим этот стаб на реальную реализацию.

import os, sys, json

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/astro/lunar_natal_merged.json')
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            evs = data.get('events', [])
        elif isinstance(data, list):
            evs = data
        else:
            evs = []
        # Ничего не меняем — чистый стаб
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[postfix] lunar_angles_postfix: {path}; events={len(evs)}; changes=0 (stub)")
    except Exception as e:
        print(f"[postfix] lunar_angles_postfix error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
