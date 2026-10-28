"""ReviewDeclare check 2 (read-only, light): which files does the adapter's joint_runtime_source_pins visit
(OU ADP `joint_runtime_source_pins`: every tuning string ending .json/.csv/.sig/.inpx/.vbs that resolves to a file,
followed recursively through JSON) for OUC (key off) and for the C1 deploy arm (11 pointers replaced as apply_tuning
would, c1_port added)?  D-K9-42 mechanism (K9-2 slowdown).  Prints counts, sizes, and the added/removed file names
relative to the repo root.  Files not yet in GWT8 (B0 batch, C1 declared evidence) are read from FRZ_B1 / C1D.
"""
import copy
import json
import sys
from pathlib import Path

BS = chr(92)
ROOT = Path('D:/VISSIM-merge/sim3-n31-k8')
B0F = Path('D:/VISSIM-merge/k8_gate_trees/codexhandoff/b1/frozen/sdmpc31_a49981ff_202610261410/diagnostics/b0_v3c3')
C1EV = Path(r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/c_port/c1/declared')
DIRS = {'omega701': 'diagnostics/b0_v3c3/omega701', 'pack': 'diagnostics/b0_v3c3/evidence', 'c1': 'diagnostics/sdmpc_n31_20260924/c1/evidence'}


def mapped(p):
    s = str(p).replace(BS, '/')
    low = s.lower()
    for key, base in (('diagnostics/b0_v3c3/', B0F), ('diagnostics/sdmpc_n31_20260924/c1/evidence/', C1EV)):
        i = low.find(key)
        if i >= 0:
            return base / s[i + len(key):], key + s[i + len(key):]
    return p, None


def pins(tuning):
    visited, out = set(), {}

    def visit(v):
        if isinstance(v, dict):
            for x in v.values():
                visit(x)
        elif isinstance(v, list):
            for x in v:
                visit(x)
        elif isinstance(v, str) and v.lower().endswith(('.json', '.csv', '.sig', '.inpx', '.vbs')):
            p = Path(v.replace(BS, '/'))
            p = p if p.is_absolute() else ROOT / p
            real, label = mapped(p)
            try:
                real = real.resolve()
            except OSError:
                return
            if real.is_file() and real not in visited:
                visited.add(real)
                name = label or str(real).replace(BS, '/').replace(str(ROOT).replace(BS, '/'), '<root>')
                out[name] = real.stat().st_size
                if real.suffix.lower() == '.json':
                    visit(json.loads(real.read_text(encoding='utf-8-sig')))
    visit(tuning)
    return out


def setp(d, ptr, val):
    ks = ptr.strip('/').split('/')
    for k in ks[:-1]:
        d = d[int(k)] if isinstance(d, list) else d[k]
    if isinstance(d, list):
        d[int(ks[-1])] = val
    else:
        d[ks[-1]] = val


ouc = json.loads((ROOT / 'diagnostics/sdmpc_n31_20260924/config_n31_v2.json').read_text(encoding='utf-8'))
bundle = json.loads((C1EV / 'omega701_v3c3_bundle.json').read_text(encoding='utf-8'))
c1 = copy.deepcopy(ouc)
for e in bundle['entries']:
    for ptr in e['tuning_pointers']:
        setp(c1, ptr, DIRS[e['dir']] + '/' + e['name'])
c1['c1_port'] = json.loads((C1EV / 'c1_port_section.json').read_text(encoding='utf-8'))['c1_port']
a, n = pins(ouc), pins(c1)
res = {'off': {'files': len(a), 'bytes': sum(a.values())}, 'c1': {'files': len(n), 'bytes': sum(n.values())},
       'added': {k: n[k] for k in sorted(set(n) - set(a))}, 'removed': sorted(set(a) - set(n))}
Path(sys.argv[1]).write_text(json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')
print(json.dumps({k: res[k] for k in ('off', 'c1')}), len(res['added']), len(res['removed']))
