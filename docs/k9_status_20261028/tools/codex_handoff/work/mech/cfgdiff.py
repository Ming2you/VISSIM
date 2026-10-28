import json, csv, hashlib, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = "D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff"
CX = W + "/diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native413_adopted355/optimized_config.json"
OU = "D:/VISSIM-merge/sim3-n31-k8/diagnostics/sdmpc_n31_20260924/config_n31_v2.json"
OUT = "C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/mech/"
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
def esc(k): return str(k).replace('~','~0').replace('/','~1')
def flat(o, p=''):
    out = {}
    if isinstance(o, dict) and o:
        for k, v in o.items(): out.update(flat(v, p + '/' + esc(k)))
    elif isinstance(o, list) and o and any(isinstance(x,(dict,list)) for x in o):
        for i, v in enumerate(o): out.update(flat(v, p + '/' + str(i)))
    else:
        out[p] = json.dumps(o, ensure_ascii=False, sort_keys=True)
    return out
cx = json.load(open(CX, encoding='utf-8')); ou = json.load(open(OU, encoding='utf-8'))
print('codex sha', sha(CX)); print('ours sha', sha(OU))
fc = flat(cx); fo = flat(ou)
print('leaves codex', len(fc), 'ours', len(fo))
only_c = sorted(set(fc) - set(fo)); only_o = sorted(set(fo) - set(fc))
both = sorted(set(fc) & set(fo)); diff = [k for k in both if fc[k] != fo[k]]
print('only codex', len(only_c), 'only ours', len(only_o), 'both', len(both), 'diff values', len(diff))
# group by top 2 levels
from collections import Counter
def grp(k, n=2): return '/'.join(k.split('/')[:n+1])
for name, lst in [('only_codex', only_c), ('only_ours', only_o), ('diff', diff)]:
    c = Counter(grp(k) for k in lst)
    print('==', name)
    for g, n in sorted(c.items(), key=lambda x: -x[1]): print(f'  {n:6d} {g}')
with open(OUT + 'cfg_leaf_diff.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f); w.writerow(['kind', 'pointer', 'codex', 'ours'])
    for k in only_c: w.writerow(['only_codex', k, fc[k][:500], ''])
    for k in only_o: w.writerow(['only_ours', k, '', fo[k][:500]])
    for k in diff: w.writerow(['diff', k, fc[k][:500], fo[k][:500]])
# compare against effective_config_fields.csv
eff = {}
with open(W + '/handoff/evidence/effective_config_fields.csv', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f): eff[r['json_pointer']] = r['value']
print('effective csv rows', len(eff))
miss = [k for k in fc if k not in eff]; extra = [k for k in eff if k not in fc]
print('flat codex not in eff', len(miss), miss[:5]); print('eff not in flat', len(extra), extra[:5])
