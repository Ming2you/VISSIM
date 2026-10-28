import json, hashlib
p = r'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31/decisions_sdmpc31_v3c3_k92va_s31/action_001950.json'
raw = open(p, 'rb').read()
print('sha', hashlib.sha256(raw).hexdigest())
d = json.loads(raw)
md = d.get('metadata', {})
ks = [k for k in md if 'capacity' in k.lower() or 'per_lane' in k.lower()]
print(len(md), ks[:40])
for k in ks:
    v = md[k]
    if not isinstance(v, (dict, list)):
        print(k, v)
def find(o, key, path='', out=None, depth=0):
    if out is None: out = []
    if depth > 6: return out
    if isinstance(o, dict):
        for k, v in o.items():
            if k == key: out.append(path + '/' + k)
            find(v, key, path + '/' + k, out, depth + 1)
    return out
print(find(d, 'movement_capacity_by_movement_veh_h')[:5])
print(find(d, 'SC1004_S_to_W')[:10])
