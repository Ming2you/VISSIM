"""VerifyGates 2 — J-b reproduction: the TREE's own gate calculator (sa_gates.py, unchanged) run again on a byte copy
of the jb output root, so OUTK is never written.  Copy = OK2/vg3t/jbcopy (OUTK/jb copied whole, then the copied
sa/gates/gates_k92t.json and .md removed); call = the k92t jb_gates argv with the copy as --out, --unit-log and
--leader-review (env as the k92t step: K8G_ROOT = TREE, K8G_OUT = the copy, PYTHONHASHSEED 0, python -B).
Comparison (fixed here, before the run): the 45 judged items (pass_ not null in gates_k91t.json, 9 gates) value
canonical JSON of the reproduced file = that of OUTK/jb/sa/gates/gates_k92t.json, and pass_ equal.  Declared
path-dependent by construction (not part of the equality): G-EB-14 unit_T9b and unit_T9c (sa_gates captured_provenance
compares the printed capture root with <out>/sa/cap/k92t); for those two the value without the 'provenance' key is
compared and reported.  Gate verdicts reported.  Output OUTV/jb_repro.json.

    python -B vg3_jbrepro.py run     (detached)"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vg3lib as V  # noqa: E402

SA = V.TREE / V.SA_REL
COPY = V.OK2 / 'vg3t' / 'jbcopy'
GATES = 'G-EB-2,G-EB-3,G-EB-4,G-EB-5,G-EB-6,G-EB-7,G-EB-8,G-EB-13,G-EB-14'
PATH_DEP = ('G-EB-14/unit_T9b', 'G-EB-14/unit_T9c')
OLD = V.V4 / 'sa' / 'gates' / 'gates_k91t.json'


def judged(doc):
    out = {}
    for g in GATES.split(','):
        for k, it in ((((doc or {}).get('gates') or {}).get(g) or {}).get('items') or {}).items():
            out['%s/%s' % (g, k)] = it
    return out


def run():
    if COPY.exists():
        raise SystemExit('%s exists' % COPY)
    t0 = time.time()
    shutil.copytree(V.lp(V.OUTK / 'jb'), V.lp(COPY))
    t_copy = round(time.time() - t0, 1)
    for n in ('gates_k92t.json', 'gates_k92t.md'):
        p = COPY / 'sa' / 'gates' / n
        if p.exists():
            os.remove(V.lp(p))
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(('RW_', 'K8_', 'K8G_', 'K92A_'))}
    env.update(PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', K8G_ROOT=str(V.TREE),
               K8G_OUT=str(COPY))
    argv = [V.PY, '-B', str(SA / 'sa_gates.py'), '--root', str(V.TREE), '--out', str(COPY), '--tree', V.LABEL,
            '--base-tree', 'k84v3', '--unit-log', str(COPY / 'sa' / 'unit_k92t.log'), '--leader-review',
            str(COPY / 'sa' / 'gates' / 'leader_review_k91t.json'), '--only', GATES]
    logp = V.OK2 / 'vg3t' / 'jbrepro_gates.log'
    t1 = time.time()
    with open(logp, 'w', encoding='utf-8', errors='replace') as f:
        rc = subprocess.run(argv, cwd=str(SA), env=env, stdout=f, stderr=subprocess.STDOUT,
                            creationflags=0x00004000).returncode
    new = V.rjson(COPY / 'sa' / 'gates' / 'gates_k92t.json')
    rec = V.rjson(V.OUTK / 'jb' / 'sa' / 'gates' / 'gates_k92t.json')
    old = V.rjson(OLD)
    oi, ni, ri = judged(old), judged(new), judged(rec)
    keys = sorted(k for k, it in oi.items() if it.get('pass_') is not None)
    rows, diff = {}, []
    for k in keys:
        a, b = ni.get(k), ri.get(k)
        if k in PATH_DEP:
            va = {x: y for x, y in ((a or {}).get('value') or {}).items() if x != 'provenance'}
            vb = {x: y for x, y in ((b or {}).get('value') or {}).items() if x != 'provenance'}
            rows[k] = {'path_dependent': True, 'value_without_provenance_equal': V.canon(va) == V.canon(vb),
                       'pass_': [None if a is None else a.get('pass_'), None if b is None else b.get('pass_')]}
            continue
        same = a is not None and b is not None and V.canon(a.get('value')) == V.canon(b.get('value')) and \
            a.get('pass_') == b.get('pass_')
        rows[k] = {'same': same}
        if not same:
            diff.append(k)
    out = {'schema': 'vg3-jb-repro/v1', 'when': V.now(), 'tool_sha256': V.sha_file(Path(__file__)), 'rc': rc,
           'copy_sec': t_copy, 'gates_sec': round(time.time() - t1, 1), 'n_judged': len(keys),
           'n_compared': len(keys) - len(PATH_DEP), 'n_same': sum(1 for r in rows.values() if r.get('same')),
           'differing': diff, 'rows': rows,
           'gate_verdicts_repro': {g: (((new or {}).get('gates') or {}).get(g) or {}).get('verdict')
                                   for g in GATES.split(',')},
           'gate_verdicts_k92t': {g: (((rec or {}).get('gates') or {}).get(g) or {}).get('verdict')
                                  for g in GATES.split(',')},
           'repro_sha256': V.sha_file(COPY / 'sa' / 'gates' / 'gates_k92t.json') if new is not None else None}
    out['ok'] = rc == 0 and new is not None and not diff and all(
        r.get('value_without_provenance_equal') for k, r in rows.items() if k in PATH_DEP)
    V.wjson(V.OUTV / 'jb_repro.json', out)
    print('VG3_JBREPRO rc=%s compared=%d same=%d diff=%s ok=%s' % (rc, out['n_compared'], out['n_same'], diff, out['ok']))
    return 0


if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] == 'run':
        raise SystemExit(run())
    print(__doc__)
    raise SystemExit(2)
