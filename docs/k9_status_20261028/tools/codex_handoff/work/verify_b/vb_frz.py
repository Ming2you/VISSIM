# vb_frz.py — FRZ_B0 와 FRZ_B1 을 새로 비교 (읽기만): (1) 두 FREEZE.json 의 files 표, (2) 두 트리의 실제 파일을 모두 다시 해시,
# (3) 바뀐 파일의 줄 단위 diff. 출력 out/frz.json, out/frz_runner.diff
import hashlib, json, os, difflib
V = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(V, 'out')
B0 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/b0/frozen/sdmpc31_a49981ff_202610260258'
B1 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/b1/frozen/sdmpc31_a49981ff_202610261410'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for ch in iter(lambda: fh.read(1 << 20), b''):
            h.update(ch)
    return h.hexdigest()


def walk(root):
    out = {}
    root = '\\\\?\\' + root.replace('/', '\\')  # 긴 경로(>260자) 허용
    for dp, dn, fn in os.walk(root):
        for f in fn:
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, root).replace('\\', '/')
            out[rel] = (sha(p), os.path.getsize(p))
    return out


F0 = json.load(open(B0 + '/FREEZE.json', encoding='utf-8'))
F1 = json.load(open(B1 + '/FREEZE.json', encoding='utf-8'))
res = {'freeze_sha': {'b0': sha(B0 + '/FREEZE.json'), 'b1': sha(B1 + '/FREEZE.json')}}
f0, f1 = F0['files'], F1['files']
res['manifest'] = {'n0': len(f0), 'n1': len(f1),
                   'changed': sorted(k for k in f0 if k in f1 and f0[k] != f1[k]),
                   'only0': sorted(set(f0) - set(f1)), 'only1': sorted(set(f1) - set(f0)),
                   'bytes': [F0.get('total_bytes'), F1.get('total_bytes')],
                   'git_head': [F0['git']['head'], F1['git']['head']],
                   'git_status_sha': [F0['git']['status_sha256'], F1['git']['status_sha256']],
                   'other_top_keys_differ': sorted(k for k in F0 if k not in ('files', 'created_at', 'source', 'frozen', 'tree_sha256', 'total_bytes') and F0.get(k) != F1.get(k))}
W0 = walk(B0); W1 = walk(B1)
W0.pop('FREEZE.json', None); W1.pop('FREEZE.json', None)
res['disk'] = {'n0': len(W0), 'n1': len(W1),
               'changed': sorted(k for k in W0 if k in W1 and W0[k][0] != W1[k][0]),
               'only0': sorted(set(W0) - set(W1)), 'only1': sorted(set(W1) - set(W0)),
               'bytes': [sum(v[1] for v in W0.values()), sum(v[1] for v in W1.values())]}
# disk vs own manifest
res['disk_vs_manifest'] = {
    'b0_mismatch': sorted(k for k in f0 if W0.get(k, (None,))[0] != f0[k])[:20],
    'b0_extra_on_disk': sorted(set(W0) - set(f0))[:20],
    'b1_mismatch': sorted(k for k in f1 if W1.get(k, (None,))[0] != f1[k])[:20],
    'b1_extra_on_disk': sorted(set(W1) - set(f1))[:20]}
diffs = []
LP = lambda r, k: '\\\\?\\' + (r + '/' + k).replace('/', '\\')
for k in res['disk']['changed']:
    a = open(LP(B0, k), 'r', encoding='utf-8-sig', errors='replace').read().splitlines()
    b = open(LP(B1, k), 'r', encoding='utf-8-sig', errors='replace').read().splitlines()
    res.setdefault('changed_files', {})[k] = {'sha0': W0[k][0], 'sha1': W1[k][0], 'lines0': len(a), 'lines1': len(b)}
    diffs += list(difflib.unified_diff(a, b, fromfile='B0/' + k, tofile='B1/' + k, lineterm='', n=0))
open(os.path.join(OUT, 'frz_runner.diff'), 'w', encoding='utf-8').write('\n'.join(diffs) + '\n')
json.dump(res, open(os.path.join(OUT, 'frz.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('ALL_DONE', flush=True)
