# Missing diagnostics data: original-freeze files absent from a0/code whose basename appears as a
# string token in a subset .py file of the same 3-level diagnostics subtree. Token-set based (fast).
import csv, json, os, re, collections
BS = chr(92)
LP = BS + BS + '?' + BS + 'D:' + BS + 'VISSIM-merge' + BS + 'k8_gate_trees' + BS + 'codexhandoff' + BS + 'a0' + BS + 'code' + BS


def lp(rel):
    return LP + rel.replace('/', BS)


FRZ = json.load(open('D:/VISSIM_handoff/20261024/evidence/original_FREEZE.json', encoding='utf-8'))['files']
SUB = [r['path'] for r in csv.DictReader(open('D:/VISSIM_handoff/20261024/code/handoff/SOURCE_FILES.csv', encoding='utf-8-sig'))]
subpy = [p for p in SUB if p.startswith('diagnostics/') and p.endswith('.py')]
roots = sorted({'/'.join(p.split('/')[:3]) for p in subpy})
tok = re.compile(r'[A-Za-z0-9_\-.]+\.[A-Za-z0-9]{2,6}')
tokens = collections.defaultdict(lambda: collections.defaultdict(set))
for p in subpy:
    r = '/'.join(p.split('/')[:3])
    for t in set(tok.findall(open(lp(p), encoding='utf-8', errors='ignore').read())):
        tokens[r][t].add(p)
out = []
nmiss = 0
for m, h in FRZ.items():
    if not m.startswith('diagnostics/'):
        continue
    r = '/'.join(m.split('/')[:3])
    if r not in tokens:
        continue
    if os.path.exists(lp(m)):
        continue
    nmiss += 1
    base = m.rsplit('/', 1)[-1]
    if base in tokens[r]:
        out.append({'path': m, 'sha256': h, 'refs': sorted(tokens[r][base])[:5]})
json.dump(out, open('C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/a0/s9_diag_missing.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('subset diag py', len(subpy), 'roots', roots)
print('missing diag files under those roots', nmiss, 'basename-referenced', len(out))
c = collections.Counter(o['path'].rsplit('/', 1)[-1] for o in out)
print('top basenames', c.most_common(25))
for o in out:
    if 'urban_rm269/aggregate270' in o['path'] and o['path'].count('/') <= 6:
        print(o['path'], '<-', o['refs'][:2])
