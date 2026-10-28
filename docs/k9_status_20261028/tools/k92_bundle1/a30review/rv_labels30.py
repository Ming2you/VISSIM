"""ReviewDeclare A30: which OUTK files outside the closed F data list (amendment 30 section 4.2) mention an F primary
label TL3_<T>_s47_SAF_OBS_H3 or a primary capture tag <T:06d>_s47 in their bytes, and whether such a file also holds
a value key form ("objective", "m1_", "horizon", "objective_repr").  Paths and counts only; no content.

    python -B rv_labels30.py <dest.json>
"""
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rv_leak30 as R  # noqa: E402

LAB = re.compile((r'TL3_(?:%s)_s47_SAF_OBS_H3|(?<![0-9])0*(?:%s)_s47(?![0-9A-Za-z])' % (R.ALT, R.ALT)).encode())
VALKEYS = (b'objective', b'"m1_', b'"horizon"', b'objective_repr', b'"m2_', b'"m3_')


def main():
    t0 = time.time()
    rows, n, nb = {}, 0, 0
    for base, dirs, names in os.walk(str(R.OUTK)):
        dirs.sort()
        for nm in sorted(names):
            full = os.path.join(base, nm)
            rel = os.path.relpath(full, str(R.OUTK)).replace('\\', '/')
            if rel in R.EXCL_LOGS or R.EXCL_RE.match(rel):
                continue
            n += 1
            with open(full, 'rb') as f:
                data = f.read()
            nb += len(data)
            if b's47' not in data:
                continue
            k = len(LAB.findall(data))
            if k:
                rows[rel] = {'label_mentions': k, 'value_keys': [v.decode() for v in VALKEYS if v in data]}
    groups = {}
    for rel, r in rows.items():
        g = re.sub(r'\d{6}', 'N6', rel)
        g = re.sub(r'TL3_\d+', 'TL3_N', g)
        e = groups.setdefault(g, {'files': 0, 'with_value_keys': 0, 'value_keys': set()})
        e['files'] += 1
        if r['value_keys']:
            e['with_value_keys'] += 1
            e['value_keys'] |= set(r['value_keys'])
    out = {'schema': 'rv30-labels/v1', 'files_scanned': n, 'bytes': nb, 'files_with_primary_label': len(rows),
           'groups': {g: dict(v, value_keys=sorted(v['value_keys'])) for g, v in sorted(groups.items())},
           'sec': round(time.time() - t0, 1)}
    Path(sys.argv[1]).write_text(json.dumps(out, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    print('RV30_LABELS files=%d with_label=%d sec=%s' % (n, len(rows), out['sec']), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
