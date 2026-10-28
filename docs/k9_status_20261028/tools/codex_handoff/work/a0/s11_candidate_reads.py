# Static scan: runtime-imported diagnostics modules (from calibrated_urban_runtime.module(...) and their
# from-imports) -> path literals relative to HERE / A / ROOT / PREV etc. -> existence in a0/code.
import json, os, re
BS = chr(92)
CODE = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/code'
PKG = 'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270'
FRZ = json.load(open('D:/VISSIM_handoff/20261024/evidence/original_FREEZE.json', encoding='utf-8'))['files']
cur = open(CODE + '/evaluation/controllers/calibrated_urban_runtime.py', encoding='utf-8').read()
mods = set(re.findall(r"module\('([^']+)'\)", cur))
seen = set()
queue = [PKG + '/' + m.replace('.', '/') + '.py' for m in mods]
imp = re.compile(r'from (diagnostics\.[A-Za-z0-9_.]+) import')
imp2 = re.compile(r'import (diagnostics\.[A-Za-z0-9_.]+)')
# also any evaluation/controllers module that imports diagnostics.* at runtime
for f in os.listdir(CODE + '/evaluation/controllers'):
    if f.endswith('.py'):
        t = open(CODE + '/evaluation/controllers/' + f, encoding='utf-8', errors='ignore').read()
        for m in imp.findall(t) + imp2.findall(t):
            queue.append(m.replace('.', '/') + '.py')
pat = re.compile(r"\b([A-Z][A-Z0-9_]*|HERE|A|ROOT|PREV)\s*/\s*['\"]([^'\"]+)['\"]((?:\s*/\s*['\"][^'\"]+['\"])*)")
rows = []
while queue:
    p = queue.pop()
    if p in seen:
        continue
    seen.add(p)
    fp = CODE + '/' + p
    if not os.path.isfile(fp):
        rows.append(('MODULE_MISSING', p, '', p in FRZ))
        continue
    t = open(fp, encoding='utf-8', errors='ignore').read()
    for m in imp.findall(t) + imp2.findall(t):
        q = m.replace('.', '/') + '.py'
        if os.path.isfile(CODE + '/' + q) or q in FRZ:
            queue.append(q)
    here = os.path.dirname(p)
    base = {'HERE': here, 'A': os.path.dirname(here), 'ROOT': '', 'PREV': None}
    for var, lit, more in pat.findall(t):
        parts = [lit] + re.findall(r"['\"]([^'\"]+)['\"]", more)
        if var in base and base[var] is not None:
            rel = '/'.join([x for x in [base[var]] + parts if x])
        else:
            continue
        rel = os.path.normpath(rel).replace(BS, '/')
        if '.' not in rel.rsplit('/', 1)[-1]:
            continue
        if not os.path.exists(CODE + '/' + rel):
            rows.append(('DATA_MISSING', rel, p, rel in FRZ))
out = sorted(set(rows))
json.dump(out, open('C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/a0/s11_candidate_reads.json', 'w', encoding='utf-8'), indent=1)
print('modules scanned', len(seen))
for r in out:
    print(r[0], ('IN_FREEZE' if r[3] else 'not_in_freeze'), r[1], '<-', r[2])
