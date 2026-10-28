import json
d = json.load(open(r'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31/decisions_sdmpc31_v3c3_k92va_s31/action_001950.json', encoding='utf-8'))
out = {}
def walk(o, path='', depth=0):
    if depth > 14: return
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, dict) and 'SC1004_S_to_W' in v and isinstance(v['SC1004_S_to_W'], (int, float)):
                out.setdefault(k, set()).add((round(v['SC1004_S_to_W'], 4), round(float(v.get('SC1004_N_SC1003_to_W', -1)), 4)))
            walk(v, path + '/' + k, depth + 1)
    elif isinstance(o, list):
        for i, v in enumerate(o[:60]):
            walk(v, path + '/%d' % i, depth + 1)
walk(d)
for k, v in out.items():
    print(k, sorted(v)[:6])
