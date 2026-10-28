"""ReviewDeclare A31: the CAP manifest against the recorded J-b copy list (OUTK/jb_copies.json 'caps': path, size,
sha256) -- counts only."""
import json
import sys
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BS = chr(92)
m = json.loads((HERE / 'out' / 'cap_manifest.json').read_text(encoding='utf-8'))['files']
d = json.loads(Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/k92t/jb_copies.json').read_text(encoding='utf-8'))
cap = BS.join(['D:', 'VISSIM_runs', '20261001_v3c3', 'reports', 'k8', 'k92_b1', 'k92t', 'jb', 'sa', 'cap', 'k92t', ''])
same = diff = miss = 0
for p, sz, sh in d['caps']:
    rel = p[len(cap):].replace(BS, '/') if p.startswith(cap) else None
    if rel not in m:
        miss += 1
    elif m[rel][0] == int(sz) and m[rel][1] == sh:
        same += 1
    else:
        diff += 1
need = all(any(k.startswith(x) for k in m) for x in ('TL3/002700/SAF/', 'TL3/002700/BASE/', 'T9C/002700/BASE/'))
print(json.dumps({'jb_copies_caps': len(d['caps']), 'same': same, 'diff': diff, 'missing': miss,
                  'captured_test_inputs_present': need}))
