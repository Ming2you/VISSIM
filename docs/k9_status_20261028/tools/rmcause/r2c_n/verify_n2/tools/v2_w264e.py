import json
def find(o, key, path='', depth=0, out=None):
    if out is None: out = []
    if depth > 8 or len(out) > 6: return out
    if isinstance(o, dict):
        for k, v in o.items():
            if k == key: out.append((path + '/' + k, v))
            find(v, key, path + '/' + k, depth + 1, out)
    elif isinstance(o, list):
        for i, v in enumerate(o[:5]):
            find(v, key, path + '/%d' % i, depth + 1, out)
    return out
for T in (1500, 1650):
    d = json.load(open(r'D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc/decisions_sdmpc31_sdmpc9000_s29/action_%06d.json' % T, encoding='utf-8'))
    hits = find(d, 'sdmpc_prediction_sequence')
    for p, v in hits[:2]:
        if isinstance(v, list):
            print(T, p, [ (b.get('vsl') or {}).get('FW_E__seg13') if isinstance(b, dict) else None for b in v[:3]], [list(b.keys())[:6] for b in v[:1] if isinstance(b, dict)])
        else:
            print(T, p, type(v).__name__, (list(v.keys())[:10] if isinstance(v, dict) else v))
