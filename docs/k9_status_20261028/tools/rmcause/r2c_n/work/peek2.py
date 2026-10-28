import json
p = r'D:\VISSIM_runs\20261001_v3c3\s31_v3c3rm\prepared\prepared.json'
raw = open(p, 'rb').read()
d = json.loads(raw.decode('utf-8'))
rt = json.dumps(d, indent=2, ensure_ascii=False).replace('\n', '\r\n').encode('utf-8')
print('prepared roundtrip identical:', rt == raw)
hits = []
def walk(o, path):
    if isinstance(o, dict):
        for k, v in o.items():
            if 's31_v3c3rm' in k:
                hits.append(('KEY', path + '/' + k[:90]))
            walk(v, path + '/' + (k if 's31_v3c3rm' not in k else '<pathkey>'))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            walk(v, path + '[%d]' % i)
    elif isinstance(o, str) and 's31_v3c3rm' in o:
        hits.append(('VAL', path, o[:200]))
walk(d, '')
from collections import Counter
print(Counter(h[1] if h[0] == 'VAL' else h[1].rsplit('/', 1)[0] for h in hits))
for h in hits:
    if h[0] == 'VAL':
        print(h)
for f in ('rule_policy.json', 'fixed_profile.json', 'fixed_profile_proof.json'):
    rp = r'D:\VISSIM_runs\20261001_v3c3\s31_v3c3rm\prepared' + '\\' + f
    raw = open(rp, 'rb').read()
    o = json.loads(raw.decode('utf-8'))
    for ea in (False, True):
        rt = json.dumps(o, indent=2, ensure_ascii=ea).replace('\n', '\r\n').encode('utf-8')
        print(f, 'ensure_ascii', ea, 'roundtrip', rt == raw, 'v3c3rm in text', b'v3c3rm' in raw)
