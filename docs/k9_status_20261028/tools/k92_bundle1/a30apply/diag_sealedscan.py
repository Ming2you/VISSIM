"""Gates A30 failure diagnosis of STOP_a30_post (after the J / F values are fixed).  Step 1: the judge output
sealed_records.json (paths and reason strings only).  Step 2 (--records): for every k92_record.json under the sealed
root, the 'seed' field, whether the 'vissim' field is null, the 'vissim_reason' string, and whether the path has an
s47 segment below the sealed root (the root's own name 'sealed_s47' excluded).  No VISSIM or model value is printed."""
import collections
import json
import os
import re
import sys
from pathlib import Path

OK2 = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1')
SEALED = OK2 / 'sealed_s47'


def seg47(parts):
    return any(p == 's47' or p.endswith('_s47') or '_s47_' in p or p.startswith('s47_') for p in parts)


def step1():
    d = json.loads((OK2 / 'k92t' / 'judge' / 'sealed_records.json').read_text(encoding='utf-8'))
    print('ok', d['ok'], 'n_bad', d['n_bad'], 'sealed', d['sealed_records'], 'notes', d['notes'])
    c = collections.Counter()
    for p, why in d['bad']:
        rel = p.replace('\\', '/').split('/sealed_s47/')[-1]
        c[(rel.split('/')[0], why)] += 1
    print('bad listed (first 50) by top folder:', dict(c))


def step2():
    rows = collections.Counter()
    for base, dirs, names in os.walk(SEALED):
        dirs.sort()
        for n in sorted(names):
            if n != 'k92_record.json':
                continue
            full = Path(base) / n
            rel = full.relative_to(SEALED).as_posix()
            parts = [p.lower() for p in re.split(r'[\\/]', rel)]
            d = json.loads(full.read_text(encoding='utf-8'))
            seed = str(d.get('seed'))
            blind = d.get('vissim') is None and d.get('vissim_reason') == 'k92_blind_s47'
            rows[(parts[0], 'seed=' + seed, 's47_seg_below_root=%s' % seg47(parts),
                  'vissim_null=%s' % (d.get('vissim') is None), 'reason=%s' % d.get('vissim_reason'),
                  'blind=%s' % blind)] += 1
    for k, v in sorted(rows.items()):
        print(v, k)
    print('total', sum(rows.values()))


if __name__ == '__main__':
    step1()
    if '--records' in sys.argv:
        step2()
