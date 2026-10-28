# A0 step 1: which tree holds the exact executed bytes per SOURCE_FILES.csv?
import csv, hashlib, json, os
CODE = 'D:/VISSIM_handoff/20261024/code'
WT = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff'
OUT = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/a0/s1_source_files.json'
BS = chr(92)


def longp(p):
    return BS + BS + '?' + BS + os.path.abspath(p).replace('/', BS)


def sha(p):
    h = hashlib.sha256()
    with open(longp(p), 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


rows = list(csv.DictReader(open(CODE + '/handoff/SOURCE_FILES.csv', encoding='utf-8-sig')))
res = {'rows': len(rows), 'code': {'ok': 0, 'bad': [], 'missing': []}, 'wt': {'ok': 0, 'bad': [], 'missing': []}}
for r in rows:
    for key, root in (('code', CODE), ('wt', WT)):
        p = root + '/' + r['path']
        try:
            s = sha(p)
        except FileNotFoundError:
            res[key]['missing'].append(r['path'])
            continue
        if s == r['sha256']:
            res[key]['ok'] += 1
        else:
            res[key]['bad'].append(r['path'])
listed = set(r['path'] for r in rows)
extra = []
for dp, dn, fn in os.walk(CODE):
    if '.git' in dp.replace(BS, '/').split('/'):
        continue
    for f in fn:
        rel = os.path.relpath(os.path.join(dp, f), CODE).replace(BS, '/')
        if rel not in listed:
            extra.append(rel)
res['code_unlisted'] = sorted(extra)
for k in ('code', 'wt'):
    res[k]['bad_n'] = len(res[k]['bad'])
    res[k]['missing_n'] = len(res[k]['missing'])
json.dump(res, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for k in ('code', 'wt'):
    print(k, 'ok', res[k]['ok'], 'bad', res[k]['bad_n'], 'missing', res[k]['missing_n'], res[k]['bad'][:5], res[k]['missing'][:5])
print('rows', len(rows), 'code_unlisted', len(extra), extra[:40])
