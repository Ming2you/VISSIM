# A0 step 1b: check provenance-recorded controller sources / files against the code copy
import json, hashlib, os
RAW = 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc'
CODE = 'D:/VISSIM_handoff/20261024/code'
FROZEN = 'D:\\VISSIM_runtime\\20261012_adopted355_vsl_three\\frozen\\sdmpc31_ca181e84_202610121132'.replace('\\\\', '\\')
BS = chr(92)
prov = json.load(open(RAW + '/run_provenance_sdmpc31_sdmpc8100_s29.json', encoding='utf-8'))


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def rel(p):
    q = p.replace(BS, '/')
    fz = FROZEN.replace(BS, '/')
    if q.lower().startswith(fz.lower()):
        return q[len(fz) + 1:]
    return None


out = {'files': {}, 'controller_sources': {'ok': 0, 'bad': [], 'missing': [], 'outside': []}, 'signal_programs': {'ok': 0, 'bad': [], 'missing': [], 'outside': []}}
for k, v in prov['files'].items():
    r = rel(v['path'])
    if r is None:
        out['files'][k] = 'outside_frozen:' + v['path']
        continue
    p = CODE + '/' + r
    if not os.path.exists(p):
        out['files'][k] = 'missing:' + r
    else:
        out['files'][k] = 'ok' if sha(p) == v['sha256'] else 'BAD:' + r
print(json.dumps(out['files'], ensure_ascii=False, indent=0))
for key in ('controller_sources', 'signal_programs'):
    lst = prov.get(key, [])
    if lst:
        print(key, 'example', json.dumps(lst[0], ensure_ascii=False)[:300])
    for e in lst:
        path = e.get('path') if isinstance(e, dict) else e
        want = e.get('sha256') if isinstance(e, dict) else None
        r = rel(path)
        if r is None:
            out[key]['outside'].append(path)
            continue
        p = CODE + '/' + r
        if not os.path.exists(p):
            out[key]['missing'].append(r)
        elif want and sha(p) != want:
            out[key]['bad'].append(r)
        else:
            out[key]['ok'] += 1
    print(key, 'n', len(lst), 'ok', out[key]['ok'], 'bad', len(out[key]['bad']), 'missing', len(out[key]['missing']), out[key]['missing'][:10], 'outside', len(out[key]['outside']), out[key]['outside'][:3])
json.dump(out, open('C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/a0/s1b_provenance_sources.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
