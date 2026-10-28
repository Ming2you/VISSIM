# Compare speed/parallel related adapter keys: our V-A config (GWT8, read only) vs codex tuning (a0/code copy).
import json, re, sys
ours = json.load(open('D:/VISSIM-merge/sim3-n31-k8/diagnostics/sdmpc_n31_20260924/config_n31_v2.json', encoding='utf-8-sig'))
cx = json.load(open('D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/code/diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native413_adopted355/optimized_config.json', encoding='utf-8-sig'))
PAT = re.compile(r'(?i)(cache|parallel|worker|thread|overlap|reuse|hotpath|fast|prefetch|concurrent|shared_primal|lazy|array_|persistent|compact|backend|budget|time|reserve|ignore_wall|max_|audit|neighbor|candidate)')
def flat(x, p, out):
    if isinstance(x, dict):
        for k, v in x.items():
            flat(v, p + '/' + k, out)
    else:
        out[p] = x
fo, fc = {}, {}
flat(ours, '', fo); flat(cx, '', fc)
keys = sorted(k for k in set(fo) | set(fc) if PAT.search(k.split('/')[-1]) and not k.split('/')[-1].startswith('_'))
rows = []
for k in keys:
    a, b = fo.get(k, '<없음>'), fc.get(k, '<없음>')
    rows.append((k, a, b, a == b))
out = {'ours': 'diagnostics/sdmpc_n31_20260924/config_n31_v2.json (GWT8 c20aff1d)', 'codex': 'native413_adopted355/optimized_config.json', 'rows': rows}
json.dump(out, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for k, a, b, s in rows:
    if not s:
        print('DIFF', k, repr(a)[:60], '|', repr(b)[:60])
print('same', sum(1 for r in rows if r[3]), 'diff', sum(1 for r in rows if not r[3]))
