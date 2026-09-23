r"""Bit-identity of the pruned central Jacobian against the deployed full sweep.

Two real tapes saved by the 2026-09-23 review agents, each with the matrix the
deployed kernel produced from it. For each tape this checks:
  * new _forward_columns == saved reference matrix, bitwise (array_equal AND the raw
    bytes, so -0.0 vs +0.0 would show)
  * new == a fresh full sweep with the unchanged _forward_column kernel
  * the non-finite fallback: poison one ancestor weight with inf and require the new
    path to reproduce the full sweep's NaN pattern exactly
and reports wall time for full vs pruned at 8 workers.
"""
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(r'D:\VISSIM-merge\sim3')
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor' / 'NumSim-mine')]
from evaluation.controllers import sdmpc_tangent_constraints as c  # noqa: E402

SC = Path('C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/'
          '491ef689-f002-4605-9dc5-e6d363495788/scratchpad')
TAPES = [(SC / 'axes_angle' / 'ax_tape.npz', SC / 'axes_angle' / 'ax_central_matrix_ref.npy'),
         (SC / 'plumb5' / 'tape.npz', SC / 'plumb5' / 'central_matrix_ref.npy')]


def load(path):
    t = np.load(path)
    keys = set(t.files)
    get = lambda *names: next(np.ascontiguousarray(t[k]) for k in names if k in keys)
    arrays = (get('p1').astype(np.int64), get('p2').astype(np.int64),
              get('w1').astype(np.float64), get('w2').astype(np.float64),
              get('sn', 'seed_nodes').astype(np.int64), get('sa', 'seed_axes').astype(np.int64),
              get('sw', 'seed_weights').astype(np.float64))
    nodes = get('nodes', 'outputs').astype(np.int64)
    n = int(np.asarray(t['steps']).item()) if 'steps' in keys else int(arrays[5].max()) + 1
    return arrays, nodes, n, sorted(keys)


def full_sweep(arrays, unique, n, workers):
    import numba
    k = numba.njit(cache=False, nogil=True, fastmath=False)(c._forward_column)
    k(*(a[:1] if i < 4 else a[:0] for i, a in enumerate(arrays)), np.zeros(1, dtype=np.int64), 0)
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        cols = list(pool.map(lambda j: k(*arrays, unique, j), range(n)))
    return np.asarray(cols).T, time.perf_counter() - t0


def main():
    ok = True
    for tape, ref_path in TAPES:
        if not tape.exists():
            print('missing', tape); continue
        arrays, nodes, n, keys = load(tape)
        ref = np.load(ref_path)
        unique, inverse = np.unique(nodes, return_inverse=True)
        print('=== %s   nodes=%d axes=%d outputs=%d unique=%d  keys=%s'
              % (tape.parent.name + '/' + tape.name, len(arrays[0]) - 1, n, len(nodes), len(unique), keys))

        t0 = time.perf_counter()
        cols, stats = c._forward_columns(arrays, unique, n, 8)
        t_new = time.perf_counter() - t0
        new = cols[inverse]
        full_cols, t_full = full_sweep(arrays, unique, n, 8)
        full = full_cols[inverse]

        ref_m = ref if ref.shape == new.shape else (ref[inverse] if ref.shape[0] == len(unique) else ref)
        eq_ref = ref_m.shape == new.shape and np.array_equal(ref_m, new) and ref_m.tobytes() == new.tobytes()
        eq_full = np.array_equal(full, new) and full.tobytes() == new.tobytes()
        print('  bitwise == saved deployed matrix : %s   (ref shape %s, new %s)' % (eq_ref, ref.shape, new.shape))
        print('  bitwise == fresh full sweep      : %s' % eq_full)
        print('  stats %s' % stats)
        print('  wall full %.2f s  ->  pruned %.2f s  (x%.2f, pruned includes compaction prep)'
              % (t_full, t_new, t_full / max(t_new, 1e-9)))
        ok &= eq_ref and eq_full

        # Non-finite fallback: put inf on the weight of an ancestor node that has a
        # nonzero parent, then both paths must agree bitwise (NaN positions included).
        live = np.zeros(len(arrays[0]), dtype=np.uint8); live[unique] = 1
        c._mark_ancestors.__wrapped__ if hasattr(c._mark_ancestors, '__wrapped__') else None
        import numba
        numba.njit(cache=False)(c._mark_ancestors)(arrays[0], arrays[1], live)
        cand = np.flatnonzero(live[1:] & (arrays[0][1:] > 0)) + 1
        if len(cand):
            victim = int(cand[len(cand) // 2])
            poisoned = list(arrays); w1 = arrays[2].copy(); w1[victim] = np.inf; poisoned[2] = w1
            poisoned = tuple(poisoned)
            pc, pstats = c._forward_columns(poisoned, unique, n, 8)
            fc, _ = full_sweep(poisoned, unique, n, 8)
            same = np.array_equal(pc, fc, equal_nan=True) and np.array_equal(np.isnan(pc), np.isnan(fc))
            print('  inf-weight fallback (node %d): finite_weights=%s  NaN pattern identical: %s  (NaN cells %d)'
                  % (victim, pstats['finite_weights'], same, int(np.isnan(fc).sum())))
            ok &= same
    print('\nALL BIT-IDENTICAL' if ok else '\nMISMATCH')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
