import json
d = json.load(open(r'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31/decisions_sdmpc31_v3c3_k92va_s31/action_001950.json', encoding='utf-8'))
def walk(o, path=''):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ('SC1004_S_to_W', 'SC1004_N_SC1003_to_W') and isinstance(v, (int, float)):
                yield path + '/' + k, v
            else:
                yield from walk(v, path + '/' + k)
    elif isinstance(o, list):
        for i, v in enumerate(o[:40]):
            yield from walk(v, path + '/%d' % i)
hits = list(walk(d))
seen = {}
for p, v in hits:
    key = p.split('/')[-2] + '/' + p.split('/')[-1]
    seen.setdefault(key, set()).add(round(v, 6))
for k, v in sorted(seen.items()):
    print(k, sorted(v)[:8])
gt = d.get('green_times') or {}
print({k: v for k, v in gt.items() if k.startswith('SC1004')})
