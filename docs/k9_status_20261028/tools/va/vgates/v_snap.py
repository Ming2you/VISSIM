"""Read-only watch for the VerifyGates stage: path / size / mtime_ns listings (caches included) of the targets this
stage must not change.  python -B v_snap.py take <out.json> | python -B v_snap.py cmp <a.json> <b.json>
Targets: FRZ_K92, FRZ_K8b, D:/VISSIM-merge/frozen top entries, R-obs3, the four J1 run folders, RR top, RVA (whole),
OUTVA (whole gate output tree), GWT8 HEAD + status --porcelain --ignored + tangent-cache names, the gate harness folder
VA/gates.  VGO (this stage's own output) is not a target.  Prints counts and digests only."""
import json
import os
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v_lib as L  # noqa: E402

GATES = Path(__file__).resolve().parents[1] / 'gates'


def take():
    s = {'when': time.strftime('%Y-%m-%dT%H:%M:%S')}
    tg = {'frzn': L.FRZN, 'frz8': L.FRZ8, 'robs3': L.ROBS3, 'rva': L.RVA, 'outva': L.OUTVA, 'gates': GATES}
    tg.update({'j1_' + k: v for k, v in L.J1.items()})
    for k, p in tg.items():
        s[k] = L.listing(p)
    s['frozen_top'] = sorted(os.listdir(L.FROZEN))
    s['rr_top'] = sorted(os.listdir(L.RR))
    s['gwt8_head'] = L.git('rev-parse', 'HEAD').strip()
    s['gwt8_status_ignored'] = L.git('status', '--porcelain', '--ignored').splitlines()
    tc = L.WT / 'evaluation' / 'controllers' / '__tangentcache__'
    s['gwt8_tangentcache'] = sorted(os.listdir(tc)) if tc.is_dir() else []
    s['k8_branch'] = L.git('rev-parse', 'claude/k8-sc1001eb-defects-20261004').strip()
    return s


def brief(s):
    out = {}
    for k, v in s.items():
        if isinstance(v, dict):
            out[k] = {'files': len(v), 'digest': L.digest(v)}
        elif isinstance(v, list):
            out[k] = {'n': len(v), 'digest': L.digest(v)}
        else:
            out[k] = v
    return out


def cmp(a, b):
    res = {}
    for k in sorted(set(a) | set(b)):
        if k == 'when':
            continue
        x, y = a.get(k), b.get(k)
        if isinstance(x, dict) and isinstance(y, dict):
            ch = sorted(p for p in x.keys() & y.keys() if x[p] != y[p])
            res[k] = {'same': not ch and x.keys() == y.keys(), 'changed': ch[:10], 'added': sorted(y.keys() - x.keys())[:10],
                      'removed': sorted(x.keys() - y.keys())[:10]}
        else:
            res[k] = {'same': x == y}
    return res


if __name__ == '__main__':
    if sys.argv[1] == 'take':
        s = take()
        L.write_json(sys.argv[2], s)
        print('V_SNAP', json.dumps(brief(s))[:3000])
    else:
        r = cmp(L.read_json(sys.argv[2]), L.read_json(sys.argv[3]))
        bad = [k for k, v in r.items() if not v['same']]
        print('V_SNAP_CMP bad=%s' % bad)
        for k in bad:
            print('  ', k, json.dumps(r[k])[:600])
