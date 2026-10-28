"""VerifyGates bit-identity check of the two reruns (vg_rerun.py) against the k92t outputs.  Own code, no harness.
Rule (fixed before the rerun data):
  * compared folders (original OUTK/<arm> vs rerun OK2/vg2t/<arm>):
      J: replays/000900, sa/tuning, sa/cap/k92t/TL3/000900/SAF, sa/jobs/k92t/TL3_900_SAF_OBS_H3
      F: replays/s43/001050, sa/tuning, sa/cap/k92t/TL3/001050_s43/SAF, sa/jobs/k92t/TL3_1050_s43_SAF_OBS_H3
  * root substitution in the rerun bytes only: 'k92_b1' + sep + 'vg2t' -> 'k92_b1' + sep + 'k92t' for sep in
    '\\', '\\\\' (JSON escape), '/' (same length, so pickles keep their framing).
  * file sets equal; a file is IDENTICAL when its substituted bytes equal the original bytes.
  * otherwise it is EXPLAINED only when every differing leaf is volatile: JSON leaves / stub-unpickled pickle leaves
    whose last key (trailing [i] removed) is in VOLATILE = the 55 L_T names of amendment 21 section 6.3 plus
    capture_wall_sec, start, end, invocation, seq; .npz arrays must be equal (np.array_equal, NaN = NaN, same dtype);
    any other difference = DIFFERENT.
  * verdict per rerun: SAME iff file sets equal and no DIFFERENT file.
Output: names, sha, leaf paths, counts (no values).

    python -B vg_cmp.py --dest <json>
"""
import argparse
import io
import json
import os
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vglib as V  # noqa: E402

OK2 = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1')
OUTK = OK2 / 'k92t'
VG = OK2 / 'vg2t'
L_T = ('candidate_elapsed_sec', 'candidate_time_overrun_sec', 'compile_or_load_sec', 'cpu_sec', 'cpu_started',
       'created_at', 'cyclic_gc_cleanup_cpu_sec', 'cyclic_gc_cleanup_wall_sec', 'deadline_monotonic',
       'decision_deadline_monotonic', 'decision_time_remaining_sec', 'decision_wall_sec', 'elapsed_sec',
       'elapsed_since_start_sec', 'endpoint_cpu_sec', 'endpoint_sec', 'finished_at', 'first_call_sec',
       'initializer_cpu_sec', 'initializer_generation_wall_sec', 'initializer_wall_sec',
       'leader_time_budget_overrun_sec', 'local_score_cpu_sec', 'local_score_sec', 'overrun_sec',
       'pool_started_monotonic', 'post_guard_pfo_wall_sec', 'prediction_wall_sec', 'preparation_copy_cpu_sec',
       'preparation_copy_wall_sec', 'preparation_cpu_sec', 'preparation_serialization_cpu_sec',
       'preparation_serialization_wall_sec', 'preparation_wall_sec', 'ready_monotonic', 'reverse_sec',
       'scalar_export_sec', 'scalar_load_sec', 'scalar_sec', 'sdmpc_after_pfo_seconds', 'seconds',
       'serialization_cpu_sec', 'serialization_wall_sec', 'solve_wall_sec', 'started', 'started_at',
       'state_check_sec', 'sweep_sec', 'tangent_sec', 'task_cpu_sec', 'task_wall_sec', 'waiting_after_hold_sec',
       'waiting_after_trials_sec', 'wall_sec', 'wall_sec_including_spawn')
assert len(L_T) == 55
VOLATILE = set(L_T) | {'capture_wall_sec', 'start', 'end', 'invocation', 'seq'}
SUBS = [(b'k92_b1' + s + b'vg2t', b'k92_b1' + s + b'k92t') for s in (b'\\\\', b'\\', b'/')]
PAIRS = {
    'J': ('jb', ['replays/000900', 'sa/tuning', 'sa/cap/k92t/TL3/000900/SAF',
                 'sa/jobs/k92t/TL3_900_SAF_OBS_H3']),
    'F': ('f_b1', ['replays/s43/001050', 'sa/tuning', 'sa/cap/k92t/TL3/001050_s43/SAF',
                   'sa/jobs/k92t/TL3_1050_s43_SAF_OBS_H3']),
}


def files(d):
    out = {}
    for base, dirs, names in os.walk(V.lp(d)):
        for n in names:
            full = os.path.join(base, n)
            out[os.path.relpath(full, V.lp(d)).replace('\\', '/')] = full
    return out


def sub(b):
    for a, c in SUBS:
        b = b.replace(a, c)
    return b


def last_key(path):
    k = path.rsplit('/', 1)[-1]
    while k.endswith(']') and '[' in k:
        k = k[:k.rindex('[')]
    return k


def to_tree(o, depth=0):
    """stub-unpickled object -> plain JSON-like tree (dicts, lists, scalars, repr for the rest)."""
    if depth > 60:
        return repr(o)[:200]
    if isinstance(o, V.Stub):
        d = {'__class__': o._vg_name}
        for k, v in o.__dict__.items():
            d[str(k)] = to_tree(v, depth + 1)
        return d
    if isinstance(o, dict):
        return {str(k): to_tree(v, depth + 1) for k, v in o.items()}
    if isinstance(o, (list, tuple, set, frozenset)):
        seq = sorted(o, key=repr) if isinstance(o, (set, frozenset)) else o
        return [to_tree(v, depth + 1) for v in seq]
    try:
        import numpy as np
        if isinstance(o, np.ndarray):
            return {'__ndarray__': str(o.dtype), 'shape': list(o.shape), 'sha': V.sha_bytes(o.tobytes())}
        if isinstance(o, np.generic):
            return o.item()
    except ImportError:
        pass
    if isinstance(o, (str, int, float, bool)) or o is None:
        return o
    if isinstance(o, bytes):
        return {'__bytes__': V.sha_bytes(o)}
    return repr(o)[:300]


def leaf_diff(a, b):
    la, lb = V.leaves(a), V.leaves(b)
    diff = []
    for k in sorted(set(la) | set(lb)):
        if k not in la or k not in lb:
            diff.append((k, 'one-sided'))
        else:
            x, y = la[k], lb[k]
            if type(x) is not type(y) or (x != y and not (isinstance(x, float) and x != x and y != y)):
                diff.append((k, 'value'))
    return diff


def npz_equal(pa, pb_bytes):
    import numpy as np
    za = np.load(V.lp(pa), allow_pickle=False)
    zb = np.load(io.BytesIO(pb_bytes), allow_pickle=False)
    if sorted(za.files) != sorted(zb.files):
        return False, ['array set differs']
    bad = []
    for k in za.files:
        x, y = za[k], zb[k]
        if x.dtype != y.dtype or x.shape != y.shape or not np.array_equal(x, y, equal_nan=x.dtype.kind in 'fc'):
            bad.append(k)
    return not bad, bad


def compare_file(rel, pa, pb):
    ba = open(V.lp(pa), 'rb').read()
    bb_raw = open(V.lp(pb), 'rb').read()
    bb = sub(bb_raw)
    row = {'file': rel, 'sha_orig': V.sha_bytes(ba), 'sha_rerun_raw': V.sha_bytes(bb_raw),
           'sha_rerun_sub': V.sha_bytes(bb), 'root_substituted': bb != bb_raw}
    if ba == bb:
        row['result'] = 'IDENTICAL'
        return row
    ext = rel.rsplit('.', 1)[-1].lower()
    try:
        if ext == 'json' or ext == 'jsonl':
            if ext == 'json':
                a, b = json.loads(ba.decode('utf-8-sig')), json.loads(bb.decode('utf-8-sig'))
            else:
                a = [json.loads(x) for x in ba.decode('utf-8').splitlines() if x.strip()]
                b = [json.loads(x) for x in bb.decode('utf-8').splitlines() if x.strip()]
            d = leaf_diff(a, b)
        elif ext == 'pickle':
            import pickle
            a = to_tree(V.StubUnpickler(io.BytesIO(ba)).load())
            b = to_tree(V.StubUnpickler(io.BytesIO(bb)).load())
            d = leaf_diff(a, b)
        elif ext == 'npz':
            ok, bad = npz_equal(pa, bb)
            row['npz_bad_arrays'] = bad
            row['result'] = 'EXPLAINED' if ok else 'DIFFERENT'
            row['why'] = 'arrays equal (zip container bytes differ)' if ok else 'arrays differ'
            return row
        else:
            la, lb = ba.decode('utf-8', 'replace').splitlines(), bb.decode('utf-8', 'replace').splitlines()
            row['text_lines'] = [len(la), len(lb)]
            row['text_lines_differing'] = sum(1 for x, y in zip(la, lb) if x != y) + abs(len(la) - len(lb))
            row['result'] = 'DIFFERENT'
            return row
    except Exception as exc:  # noqa: BLE001
        row['result'] = 'DIFFERENT'
        row['error'] = repr(exc)[:300]
        return row
    vol = [k for k, why in d if last_key(k) in VOLATILE and why == 'value']
    other = [(k, why) for k, why in d if not (last_key(k) in VOLATILE and why == 'value')]
    row['volatile_leaves'] = vol[:40]
    row['n_volatile'] = len(vol)
    row['other_leaves'] = other[:40]
    row['n_other'] = len(other)
    row['result'] = 'EXPLAINED' if not other else 'DIFFERENT'
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dest', required=True)
    args = ap.parse_args()
    res = {'schema': 'vgates-rerun-cmp/v1', 'rule': __doc__.split('Output:')[0], 'pairs': {}}
    allok = True
    for key, (arm, folders) in PAIRS.items():
        prow = {'arm': arm, 'folders': {}}
        ok = True
        for rel in folders:
            da, db = OUTK / arm / rel, VG / arm / rel
            fa, fb = files(da), files(db)
            frow = {'n_orig': len(fa), 'n_rerun': len(fb), 'only_orig': sorted(set(fa) - set(fb)),
                    'only_rerun': sorted(set(fb) - set(fa)), 'files': []}
            if not fa or not fb:
                frow['problem'] = 'folder missing or empty'
                ok = False
            for r in sorted(set(fa) & set(fb)):
                frow['files'].append(compare_file(r, fa[r], fb[r]))
            frow['counts'] = {x: sum(1 for f in frow['files'] if f['result'] == x)
                              for x in ('IDENTICAL', 'EXPLAINED', 'DIFFERENT')}
            if frow['only_orig'] or frow['only_rerun'] or frow['counts']['DIFFERENT']:
                ok = False
            prow['folders'][rel] = frow
        prow['verdict'] = 'SAME' if ok else 'DIFFERENT'
        allok &= ok
        res['pairs'][key] = prow
    res['verdict'] = 'SAME' if allok else 'DIFFERENT'
    V.wjson(args.dest, res)
    print('VG_CMP %s %s' % (res['verdict'], {k: v['verdict'] for k, v in res['pairs'].items()}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
