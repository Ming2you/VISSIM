"""ReviewDeclare A31: basename counts of sealed files whose name contains 'record' (seal indexes outside the sealed
root; names only, no path, no value)."""
import collections
import json
import sys
sys.dont_write_bytecode = True
c = collections.Counter()
for t in ('K9-2-0', 'K9-2-1', 'K9-2-2', 'K9-2-3'):
    d = json.load(open(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/commit/%s/sealed_s47_index.json' % t,
                       encoding='utf-8'))
    for rel in d['inventory']:
        n = rel.replace(chr(92), '/').split('/')[-1]
        if 'record' in n.lower():
            c[n] += 1
print(json.dumps(dict(sorted(c.items()))))
