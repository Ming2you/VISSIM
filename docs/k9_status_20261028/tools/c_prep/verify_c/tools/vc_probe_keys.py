# Structure-only probe: prints key names and types (no numeric values) of one decision JSON.
import json, sys
p = sys.argv[1]
d = json.load(open(p, encoding='utf-8'))
def show(o, path, depth):
    if depth > 3: return
    if isinstance(o, dict):
        for k, v in list(o.items())[:60]:
            t = type(v).__name__
            n = len(v) if isinstance(v, (list, dict)) else ''
            print('  ' * depth + f'{path}/{k}: {t} {n}')
            if isinstance(v, dict): show(v, path + '/' + k, depth + 1)
            elif isinstance(v, list) and v and isinstance(v[0], dict) and depth < 3:
                print('  ' * (depth + 1) + f'{path}/{k}[0] keys: ' + ','.join(list(v[0].keys())[:40]))
show(d, '', 0)
