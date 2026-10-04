"""K8-5 (S9 moving-count speed weighting) gate judge with the strict merge gate (diagnostics only; reads outputs,
runs nothing).

    python -B k85_gate.py --out <gates_out/k84> --unit-log <pytest -v log> [--unit-log ...] [--json <verdict.json>]
                          [--root <code root for unpickling and the delay-step function>]

Declared: K8_PREDECLARATION_AMENDMENT_1.md r2 §1 / §2 K8-5 row and §2.1 (D-K8-3, strict; N13: the record-partition
path ADP:6346-6347 is out of scope), amendment 2 N-A6 (report only), amendment 9 (the 59 capturable R-obs3 states
T = 300 ... 9000 stand for "61"; report starts 300-750 and 1800 / 2700 / 4950; the K8-4 captures are reused).
Prototype values: DEFECTS.md §8.2-8.3. All fixed here, in a tool commit, before any K8-5 gate run.
Comparison: K8-5 tree (S9) - K8-4 tree (ce8fe806, the runtime commit just before), both without SA keys.

Layout under --out (one output root, so the replay paths are the same in both arms):
  replays/<T>/                 prep.py copies of the 61 R-obs3 decision states (K8-4 gate)
  out/<T>/cap_k84/             K8-4 captures (K8-4 gate, reused; T = 1 / 150 cannot be captured in either tree)
  out/<T>/cap_k85/             K8-5 captures (unpatched cap_child 'base', capture.py --cap-label k85, K8-5 code root)
  out/<T>/jobs/g85_k84_REF/    REFERENCE 3-block (450 s) scalar rollout of cap_k84 with the K8-4 code root
  out/<T>/jobs/g85_k85_REF/    the same of cap_k85 with the K8-5 code root

Judged (all must pass; an exception inside an item fails that item):
  (a) only the S9 field changes, every capturable state: every TrafficState attribute other than urban_link_speed_kph
      and local_observation_summary is equal (same structure, numbers +-1e-9); in local_observation_summary the key
      sets are equal and only urban_link_speed_kph and its two derived diagnostics differ (tau_diagnostics, the tau
      summary of the same speeds; projection_diagnostics.urban_link_speed_observed_count = its length); the K8-5 speed
      keys (summary and state) are a subset of the K8-4 ones (S9 only removes samples)
  (b) prototype reproduction at 2700 (summary urban_link_speed_kph, K8-4 -> K8-5): 56 storages change by more than 1 %
      of the K8-4 value and 8 storages lose their entry (-> nominal speed)
  (c) prototype reproduction, delay-step sum over all storages (vendor _link_delay_steps of the captured state, the
      an_proj.py method) at 1800 / 2700 / 4950: (K8-5 - K8-4) / K8-4 rounded to 0.1 % lies in [-7.1, -6.4] %
  (d) unchanged (declared "occupancy, queues, seeds", |difference| <= 1e-9), every capturable state: movement queues
      (state urban_movement_queue, summary urban_movement_queue), occupancy (state urban_link_storage, summary
      urban_link_storage_occupancy, urban_link_storage_stopped), seeds (urban_arrival_buffer and
      urban_storage_release_buffer cells, summary urban_arrival_seed, projection_diagnostics.storage_seed_split_by_link)
  (e) captures: K8-5 and K8-4 captures exist for all 59 capturable states (capture.json meta = template.pickle sha256)
  (f) strict merge gate (§2.1). Target of (T, k) = the K8-4 capture of T + 150k: queue = owned[1].urban_movement_queue
      (all keys), occupancy = cfg.network.urban_link_storage_veh[s] - state.urban_link_storage[s] (all storages);
      prediction = the arm's job summary.blocks[k-1] (an_fid.py:13-33 with block k-1 for block 0).
      q_MAE = mean_356 |q^ - q|, s_MAE = mean_241 |o^ - o|, C = q_MAE + s_MAE.
      Samples: starts {900, 1050, ..., 8850} minus {1800, 2700, 4950}; block k keeps T + 150k <= 9000 and
      T + 150k not in {1950, 2850, 5100}; sizes 51 / 47 / 46.
      STOP (not pass) when: a sample size differs, a job is missing / failed, a block-end time is not T + 150k, the key
      counts are not 356 / 241, or a target differs between the K8-5 and K8-4 captures by more than 1e-9.
      R1: sum_S C85 <= sum_S C84 (no margin). R2: W = #{C85 - C84 > 1e-9}; |S| - W > |S| / 2 (ties are non-worse).
      Merge <=> R1 and R2 in all three blocks.
  (g) unit tests diagnostics/test_k8_s9_moving_speed_weight.py: every declared test PASSED and none FAILED / ERROR /
      SKIPPED / SUBFAILED in the pytest 9 -v lines or the short summary (amendment 6 §1 rule)
Reported (not judged): N-A6 per block for both trees (597-key joint MAE sample mean and ratio, q_MAE / s_MAE ratios,
joint R1 / R2 equivalents), the three biases and ratios, W_k and ties, per-state table, report-sample values
(starts 300-750, 1800 / 2700 / 4950), REFERENCE owner cost deltas (B6-5; amendment 1 §H.3 S9 prototype values beside),
K8-4 rollout determinism against the K8-4 gate's k84_REF_scalar, K8-5 speeds against the prototype S9_speed_fixed of the
K8-4 capture records, tau (delay-step) changes per state with the largest storages, the K8-5 T = 1 / 150 capture
failures beside the K8-4 ones, template-level differences.
"""
import argparse
import hashlib
import json
import math
import pickle
import re
import sys
import traceback
from pathlib import Path

GATES = Path(__file__).resolve().parent
STATES = [1] + list(range(150, 9001, 150))                      # the 61 R-obs3 decisions
CAPTURABLE = list(range(300, 9001, 150))                        # amendment 9: 59 states
SEEN_STARTS = (1800, 2700, 4950)                                # D-K8-3: already-seen states
SEEN_TARGETS = (1950, 2850, 5100)                               # their T+150 targets
JUDGE_STARTS = [T for T in range(900, 8851, 150) if T not in SEEN_STARTS]
BLOCKS = (1, 2, 3)
BLOCK_SEC = 150
END_SEC = 9000
SIZES = {1: 51, 2: 47, 3: 46}
REPORT_STARTS = (300, 450, 600, 750, 1800, 2700, 4950)
N_MOV, N_STO = 356, 241
TOL = 1e-9
ARM84, ARM85 = 'k84', 'k85'
JOB84, JOB85 = 'g85_k84_REF', 'g85_k85_REF'
PROTO_2700 = {'changed_gt_1pct': 56, 'to_nominal': 8}
DELAY_STATES = (1800, 2700, 4950)
DELAY_RANGE_PCT = (-7.1, -6.4)
DELAY_PROTO = {1800: (17134, 16045), 2700: (17345, 16110), 4950: (16974, 15850)}   # DEFECTS §8.2 (report)
H3_S9 = {1800: {'PASSIVE_OMEGA': -4.749, 'SC12': 1.000, 'SC101': 0.676, 'Omega': -0.916},   # amendment 1 §H.3
         2700: {'PASSIVE_OMEGA': -3.639, 'SC1': 1.226, 'SC12': 0.431, 'Omega': 0.005},     # (K7 vs K7 + S9 only)
         4950: {'PASSIVE_OMEGA': -3.487, 'SC1': 0.584, 'SC101': 0.362, 'Omega': -0.981}}
K84_REF_OBJECTIVE = {1800: '469.38121231196607', 2700: '506.06244747863195', 4950: '380.7999577094864'}  # K84_GATE §5.1
ALLOWED_STATE = {'urban_link_speed_kph', 'local_observation_summary'}
ALLOWED_SUMMARY = {'urban_link_speed_kph', 'tau_diagnostics', 'projection_diagnostics'}
ALLOWED_DIAG = {'urban_link_speed_observed_count'}
UNIT_FILE = 'diagnostics/test_k8_s9_moving_speed_weight.py'
UNIT_TESTS = {
    'MovingWeightTests': ('test_mixed_link_is_weighted_by_its_moving_count',
                          'test_all_stopped_link_adds_no_zero_speed_sample',
                          'test_moving_count_below_half_is_no_sample',
                          'test_weight_reads_the_instant_counts_not_the_window',
                          'test_moving_only_off_keeps_the_count_weighting_bit_for_bit',
                          'test_only_the_storage_speed_depends_on_the_weighting'),
    'RecordPathTests': ('test_record_partition_path_keeps_its_weighting',)}
BAD_STATES = {'FAILED', 'ERROR', 'SKIPPED', 'XFAIL', 'XPASS', 'SUBFAILED', 'SUBSKIPPED'}


def block_sample(k):
    return [T for T in JUDGE_STARTS if T + BLOCK_SEC * k <= END_SEC and T + BLOCK_SEC * k not in SEEN_TARGETS]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pk(x):
    return pickle.dumps(x, protocol=5)


def cap_dir(out, T, arm):
    return Path(out) / 'out' / f'{T:06d}' / f'cap_{arm}'


def capture_status(out, T, arm):
    d = cap_dir(out, T, arm)
    cj, tp = d / 'capture.json', d / 'template.pickle'
    if cj.is_file() and tp.is_file():
        rec = json.loads(cj.read_text(encoding='utf-8'))
        if rec.get('meta', {}).get('template_sha256') == sha(tp):
            return {'ok': True, 'template_sha256': rec['meta']['template_sha256'], 'record': rec}
        return {'ok': False, 'why': 'capture.json meta does not match template.pickle'}
    failed = d / 'capture_failed.json'
    why = 'missing capture'
    rec = {}
    if failed.is_file():
        rec = json.loads(failed.read_text(encoding='utf-8'))
        why = 'capture_failed.json'
    err = sorted(d.glob('action_*.error.txt')) if d.is_dir() else []
    last = ''
    if err:
        lines = [x for x in err[0].read_text(encoding='utf-8', errors='replace').splitlines() if x.strip()]
        last = lines[-1] if lines else ''
    return {'ok': False, 'why': why, 'error_last_line': last, 'record': rec}


def load_template(out, T, arm):
    return pickle.loads((cap_dir(out, T, arm) / 'template.pickle').read_bytes())


def close(x, y, tol=TOL):
    """Same structure; numbers within tol; anything else by pickle bytes."""
    if isinstance(x, dict) and isinstance(y, dict):
        return set(x) == set(y) and all(close(x[k], y[k], tol) for k in x)
    if isinstance(x, (list, tuple)) and isinstance(y, (list, tuple)):
        return type(x) is type(y) and len(x) == len(y) and all(close(a, b, tol) for a, b in zip(x, y))
    if isinstance(x, bool) or isinstance(y, bool):
        return x is y
    if isinstance(x, (int, float)) and isinstance(y, (int, float)):
        if math.isnan(float(x)) or math.isnan(float(y)):
            return math.isnan(float(x)) and math.isnan(float(y))
        return abs(float(x) - float(y)) <= tol
    return pk(x) == pk(y)


def max_abs_diff(x, y):
    """Largest |difference| over the numbers of two same-shaped mappings (inf when the shapes differ)."""
    if isinstance(x, dict) and isinstance(y, dict):
        if set(x) != set(y):
            return math.inf
        return max((max_abs_diff(x[k], y[k]) for k in x), default=0.0)
    if isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool):
        return abs(float(x) - float(y))
    return 0.0 if pk(x) == pk(y) else math.inf


def targets(t):
    """an_fid.py:20-23 for one captured state: (cap, queue, occupancy)."""
    cfg = t['owned'][0].cfg
    sn = t['owned'][1]
    cap = cfg.network.urban_link_storage_veh
    q = {k: float(v) for k, v in sn.urban_movement_queue.items()}
    occ = {k: float(cap[k]) - float(sn.urban_link_storage.get(k, cap[k])) for k in cap}
    return cap, q, occ


def compare_state(t84, t85):
    """Items (a) and (d) for one state captured by both trees."""
    s84, s85 = t84['owned'][1], t85['owned'][1]
    r = {}
    keys = set(vars(s84)) | set(vars(s85))
    r['state_attr_diff'] = sorted(k for k in keys if k not in ALLOWED_STATE
                                  and not close(getattr(s84, k, None), getattr(s85, k, None)))
    r['report_state_attr_bytes_diff'] = sorted(k for k in keys if k not in ALLOWED_STATE
                                               and pk(getattr(s84, k, None)) != pk(getattr(s85, k, None)))
    la, lb = s84.local_observation_summary, s85.local_observation_summary
    r['summary_new_keys'] = sorted(set(lb) - set(la))
    r['summary_missing_keys'] = sorted(set(la) - set(lb))
    r['summary_diff'] = sorted(k for k in set(la) & set(lb) if k not in ALLOWED_SUMMARY and not close(la[k], lb[k]))
    da, db = la.get('projection_diagnostics', {}), lb.get('projection_diagnostics', {})
    r['diag_new_keys'] = sorted(set(db) - set(da))
    r['diag_missing_keys'] = sorted(set(da) - set(db))
    r['diag_diff'] = sorted(k for k in set(da) & set(db) if k not in ALLOWED_DIAG and not close(da[k], db[k]))
    sp84, sp85 = la.get('urban_link_speed_kph', {}), lb.get('urban_link_speed_kph', {})
    r['speed_summary_extra_keys'] = sorted(set(sp85) - set(sp84))
    r['speed_state_extra_keys'] = sorted(set(s85.urban_link_speed_kph) - set(s84.urban_link_speed_kph))
    r['pass_a'] = (not r['state_attr_diff'] and not r['summary_new_keys'] and not r['summary_missing_keys']
                   and not r['summary_diff'] and not r['diag_new_keys'] and not r['diag_missing_keys']
                   and not r['diag_diff'] and not r['speed_summary_extra_keys'] and not r['speed_state_extra_keys'])
    # (d) declared unchanged quantities
    pairs = {
        'state.urban_movement_queue': (s84.urban_movement_queue, s85.urban_movement_queue),
        'summary.urban_movement_queue': (la.get('urban_movement_queue'), lb.get('urban_movement_queue')),
        'state.urban_link_storage': (s84.urban_link_storage, s85.urban_link_storage),
        'summary.urban_link_storage_occupancy': (la.get('urban_link_storage_occupancy'),
                                                 lb.get('urban_link_storage_occupancy')),
        'summary.urban_link_storage_stopped': (la.get('urban_link_storage_stopped'), lb.get('urban_link_storage_stopped')),
        'state.urban_arrival_buffer': (s84.urban_arrival_buffer, s85.urban_arrival_buffer),
        'state.urban_storage_release_buffer': (s84.urban_storage_release_buffer, s85.urban_storage_release_buffer),
        'summary.urban_arrival_seed': (la.get('urban_arrival_seed'), lb.get('urban_arrival_seed')),
        'diag.storage_seed_split_by_link': (da.get('storage_seed_split_by_link'), db.get('storage_seed_split_by_link')),
    }
    r['unchanged_max_abs'] = {k: max_abs_diff(*v) for k, v in pairs.items()}
    r['unchanged_present'] = {k: v[0] is not None and v[1] is not None for k, v in pairs.items()}
    r['pass_d'] = all(r['unchanged_present'].values()) and all(x <= TOL for x in r['unchanged_max_abs'].values())
    # report
    r['template_key_diff'] = sorted(k for k in set(t84) | set(t85) if k != 'owned' and pk(t84.get(k)) != pk(t85.get(k)))
    r['owned_diff'] = [i for i in (0, 2, 3) if pk(t84['owned'][i]) != pk(t85['owned'][i])]
    return r


def speed_change(sp84, sp85):
    common = [k for k in sp84 if k in sp85]
    gt1 = [k for k in common if abs(sp85[k] - sp84[k]) > 0.01 * max(sp84[k], 1e-9)]
    nominal = sorted(k for k in sp84 if k not in sp85)
    top = sorted(((abs(sp85[k] - sp84[k]), k, sp84[k], sp85[k]) for k in common), reverse=True)[:10]
    return {'observed_k84': len(sp84), 'observed_k85': len(sp85), 'changed_gt_1pct': len(gt1), 'to_nominal': len(nominal),
            'to_nominal_list': nominal, 'extra_keys': sorted(set(sp85) - set(sp84)),
            'changed_any': sum(1 for k in common if sp85[k] != sp84[k]),
            'top': [[k, round(a, 3), round(b, 3)] for _, k, a, b in top]}


def delays(uqm, t):
    cfg = t['owned'][0].cfg
    s = t['owned'][1]
    return {k: int(uqm._link_delay_steps(s, cfg, k)) for k in cfg.network.urban_link_storage_veh}


def prototype_speed_check(rec84, sp85):
    """K8-5 summary speeds against the prototype S9_speed_fixed recorded by cap_child on the K8-4 capture."""
    fixed = ((rec84 or {}).get('projection') or {}).get('S9_speed_fixed')
    if not isinstance(fixed, dict):
        return {'available': False}
    keys_equal = set(fixed) == set(sp85)
    worst_abs = max((abs(float(fixed[k]) - float(sp85[k])) for k in fixed if k in sp85), default=0.0)
    worst_rel = max((abs(float(fixed[k]) - float(sp85[k])) / max(abs(float(fixed[k])), 1e-9) for k in fixed if k in sp85),
                    default=0.0)
    return {'available': True, 'keys_equal': keys_equal, 'worst_abs_kph': worst_abs, 'worst_rel': worst_rel,
            'prototype_changed_gt_1pct': ((rec84 or {}).get('projection') or {}).get('S9_storages_changed_gt1pct'),
            'prototype_to_nominal': len(((rec84 or {}).get('projection') or {}).get('S9_storages_to_nominal') or [])}


def job(out, T, label):
    p = Path(out) / 'out' / f'{T:06d}' / 'jobs' / label / 'result.pickle'
    if not p.is_file():
        return {'error': f'missing {p}'}
    return pickle.loads(p.read_bytes())


def block_metrics(res, T, k, cap, obs_q, obs_occ):
    """an_fid.py:26-33 with block k-1; returns (metrics, stop reason or None)."""
    if res.get('error'):
        return None, f'job error at start {T}: {str(res["error"])[-300:]}'
    blocks = (res.get('summary') or {}).get('blocks') or []
    if len(blocks) < k:
        return None, f'start {T}: {len(blocks)} blocks in the job summary, need {k}'
    b = blocks[k - 1]
    if float(b['time_sec']) != float(T + BLOCK_SEC * k):
        return None, f'start {T} block {k}: block-end time {b["time_sec"]} != {T + BLOCK_SEC * k}'
    q = b['movement_queue']
    occ = {s: float(cap[s]) - b['storage_available'].get(s, cap[s]) for s in cap}
    eq = [q.get(m, 0.0) - v for m, v in obs_q.items()]
    eo = [occ[s] - v for s, v in obs_occ.items()]
    if len(eq) != N_MOV or len(eo) != N_STO:
        return None, f'start {T} block {k}: key counts {len(eq)} / {len(eo)} != {N_MOV} / {N_STO}'
    abs_q, abs_o = sum(map(abs, eq)), sum(map(abs, eo))
    m = {'q_mae': abs_q / len(eq), 's_mae': abs_o / len(eo), 'q_bias': sum(eq), 's_bias': sum(eo),
         'joint_mae': (abs_q + abs_o) / (N_MOV + N_STO), 't': float(b['time_sec'])}
    m['C'] = m['q_mae'] + m['s_mae']
    m['bias'] = m['q_bias'] + m['s_bias']
    return m, None


def owner_delta(r84, r85):
    if r84.get('error') or r85.get('error'):
        return None
    order = r85.get('costs_order') or r84.get('costs_order')
    if not order or len(r84.get('costs') or []) != len(order) or len(r85.get('costs') or []) != len(order):
        return None
    return {'objective': [repr(r84.get('objective_veh_h')), repr(r85.get('objective_veh_h'))],
            'omega_delta': r85['objective_veh_h'] - r84['objective_veh_h'],
            'owner_delta': {order[i]: q - p for i, (p, q) in enumerate(zip(r84['costs'], r85['costs']))}}


def unit_results(logs):
    """pytest 9 -v lines '<nodeid> STATE' and short-summary '(SUB)FAILED|ERROR <nodeid>[ - message]' lines -> states."""
    seen = {}
    for log in logs:
        raw = Path(log).read_bytes()
        text = raw.decode('utf-16') if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else raw.decode('utf-8', errors='replace')
        for m in re.finditer(r'^(\S+?::\S+?)\s+(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS|SUBPASSED|SUBFAILED|SUBSKIPPED)\b',
                             text, re.M):
            seen.setdefault(m.group(1), set()).add(m.group(2))
        for m in re.finditer(r'^(FAILED|ERROR|SUBFAILED)(?:\[[^\]]*\]|\(.*?\))? (\S+?::\S+?)(?:\s+-\s.*)?\s*$', text, re.M):
            seen.setdefault(m.group(2), set()).add('FAILED')
    return seen


def item_unit(logs):
    seen = unit_results(logs)
    rows, ok = [], True
    for cls, names in UNIT_TESTS.items():
        for name in names:
            node = f'{UNIT_FILE}::{cls}::{name}'
            states = set(seen.get(node, set()))
            good = 'PASSED' in states and not (states & BAD_STATES)
            rows.append({'test': node, 'states': sorted(states), 'pass': good})
            ok &= good
    return {'pass': ok, 'rows': rows, 'logs': [str(x) for x in logs],
            'n_declared': sum(len(v) for v in UNIT_TESTS.values())}


def fsum(xs):
    return math.fsum(xs)


def strict_gate(out, tgt84, tgt85):
    """Item (f) and the N-A6 report. tgt* = {T': (cap, q, occ)} from the captures."""
    stop, per, blocks = [], {}, {}
    for k in BLOCKS:
        if len(block_sample(k)) != SIZES[k]:
            stop.append(f'block {k}: sample size {len(block_sample(k))} != declared {SIZES[k]}')
    starts = sorted(set(JUDGE_STARTS) | set(REPORT_STARTS))
    jobs = {}
    for T in starts:
        jobs[T] = (job(out, T, JOB84), job(out, T, JOB85))
    for T in starts:
        r84, r85 = jobs[T]
        for k in BLOCKS:
            T2 = T + BLOCK_SEC * k
            if T2 > END_SEC:
                continue
            judged = T in block_sample(k)
            if T2 not in tgt84 or T2 not in tgt85:
                if judged:
                    stop.append(f'target {T2} missing in a capture arm')
                continue
            cap, q, occ = tgt84[T2]
            m84, e84 = block_metrics(r84, T, k, cap, q, occ)
            m85, e85 = block_metrics(r85, T, k, cap, q, occ)
            if e84 or e85:
                if judged:
                    stop.extend(x for x in (e84, e85) if x)
                per[f'{T}|{k}'] = {'T': T, 'k': k, 'judged': judged, 'error': [e84, e85]}
                continue
            row = {'T': T, 'k': k, 'target': T2, 'judged': judged, 'k84': m84, 'k85': m85,
                   'dC': m85['C'] - m84['C'], 'djoint': m85['joint_mae'] - m84['joint_mae']}
            row['worse'] = row['dC'] > TOL
            row['tie'] = abs(row['dC']) <= TOL
            per[f'{T}|{k}'] = row
    for k in BLOCKS:
        S = block_sample(k)
        rows = [per.get(f'{T}|{k}') for T in S]
        if any(r is None or 'k84' not in r for r in rows):
            blocks[k] = {'n': len(S), 'complete': False}
            continue
        c84 = fsum(r['k84']['C'] for r in rows)
        c85 = fsum(r['k85']['C'] for r in rows)
        W = sum(1 for r in rows if r['worse'])
        ties = sum(1 for r in rows if r['tie'])
        n = len(rows)
        R1 = c85 <= c84
        R2 = (n - W) > n / 2
        j84 = fsum(r['k84']['joint_mae'] for r in rows)
        j85 = fsum(r['k85']['joint_mae'] for r in rows)
        Wj = sum(1 for r in rows if r['djoint'] > TOL)
        q84, q85 = fsum(r['k84']['q_mae'] for r in rows), fsum(r['k85']['q_mae'] for r in rows)
        s84, s85 = fsum(r['k84']['s_mae'] for r in rows), fsum(r['k85']['s_mae'] for r in rows)
        bias = {}
        for name in ('q_bias', 's_bias', 'bias'):
            b84, b85 = fsum(r['k84'][name] for r in rows), fsum(r['k85'][name] for r in rows)
            bias[name] = {'mean_k84': b84 / n, 'mean_k85': b85 / n, 'ratio': b85 / b84 if b84 else None,
                          'sum_abs_k84': fsum(abs(r['k84'][name]) for r in rows),
                          'sum_abs_k85': fsum(abs(r['k85'][name]) for r in rows)}
        blocks[k] = {'n': n, 'complete': True, 'sum_C_k84': c84, 'sum_C_k85': c85, 'ratio_C': c85 / c84,
                     'mean_C_k84': c84 / n, 'mean_C_k85': c85 / n, 'W': W, 'ties': ties, 'non_worse': n - W,
                     'R1': R1, 'R2': R2, 'pass': R1 and R2,
                     'report_q_mae': {'mean_k84': q84 / n, 'mean_k85': q85 / n, 'ratio': q85 / q84},
                     'report_s_mae': {'mean_k84': s84 / n, 'mean_k85': s85 / n, 'ratio': s85 / s84},
                     'report_joint_mae': {'mean_k84': j84 / n, 'mean_k85': j85 / n, 'ratio': j85 / j84,
                                          'R1_equivalent': j85 <= j84, 'W': Wj, 'non_worse': n - Wj,
                                          'R2_equivalent': (n - Wj) > n / 2},
                     'report_bias': bias,
                     'worse_starts': [r['T'] for r in rows if r['worse']]}
    complete = all(blocks.get(k, {}).get('complete') for k in BLOCKS)
    if not complete:
        stop.append('a block sample is incomplete')
    merge = not stop and complete and all(blocks[k]['pass'] for k in BLOCKS)
    report = {T: {k: per.get(f'{T}|{k}') for k in BLOCKS if T + BLOCK_SEC * k <= END_SEC} for T in REPORT_STARTS}
    owners = {T: owner_delta(*jobs[T]) for T in starts}
    return {'pass': merge, 'stop': stop, 'blocks': blocks,
            'samples': {k: block_sample(k) for k in BLOCKS}, 'per_state': per, 'report_sample': report}, owners


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True, help='gate output root (gates_out/k84: K8-4 captures reused)')
    ap.add_argument('--unit-log', action='append', required=True)
    ap.add_argument('--json')
    ap.add_argument('--root', default=str(GATES.parents[2]), help='code root for unpickling (default: this worktree)')
    a = ap.parse_args()
    root = Path(a.root)
    sys.path[:0] = [str(root), str(root / 'vendor/NumSim-mine'), str(root / 'evaluation/controllers')]
    from src.models import urban_queue_model as uqm
    v = {'items': {}, 'report': {}}
    items, rep = v['items'], v['report']
    caps = {ARM84: {}, ARM85: {}}
    cmp_rows, tgt84, tgt85, spd, dly, proto = {}, {}, {}, {}, {}, {}
    for T in STATES:
        st84, st85 = capture_status(a.out, T, ARM84), capture_status(a.out, T, ARM85)
        caps[ARM84][T] = {k: st84.get(k) for k in ('ok', 'why', 'error_last_line', 'template_sha256')}
        caps[ARM85][T] = {k: st85.get(k) for k in ('ok', 'why', 'error_last_line', 'template_sha256')}
        if not (st84['ok'] and st85['ok']):
            continue
        try:
            t84, t85 = load_template(a.out, T, ARM84), load_template(a.out, T, ARM85)
            tgt84[T], tgt85[T] = targets(t84), targets(t85)
            cmp_rows[T] = compare_state(t84, t85)
            sp84 = t84['owned'][1].local_observation_summary.get('urban_link_speed_kph', {})
            sp85 = t85['owned'][1].local_observation_summary.get('urban_link_speed_kph', {})
            spd[T] = speed_change(sp84, sp85)
            proto[T] = prototype_speed_check(st84.get('record'), sp85)
            d84, d85 = delays(uqm, t84), delays(uqm, t85)
            ch = sorted(((abs(d85[k] - d84[k]), k, d84[k], d85[k]) for k in d84 if d85[k] != d84[k]), reverse=True)
            dly[T] = {'sum_k84': sum(d84.values()), 'sum_k85': sum(d85.values()),
                      'pct': 100.0 * (sum(d85.values()) - sum(d84.values())) / sum(d84.values()),
                      'changed': len(ch), 'top': [[k, a_, b_] for _, k, a_, b_ in ch[:15]]}
        except Exception:
            cmp_rows[T] = {'pass_a': False, 'pass_d': False, 'exception': traceback.format_exc()[-2000:]}
        finally:
            t84 = t85 = None
    v['report']['delay_function'] = f'{uqm._link_delay_steps.__module__}.{uqm._link_delay_steps.__qualname__}'

    def item_a():
        bad = {T: {k: r.get(k) for k in ('state_attr_diff', 'summary_new_keys', 'summary_missing_keys', 'summary_diff',
                                         'diag_new_keys', 'diag_missing_keys', 'diag_diff', 'speed_summary_extra_keys',
                                         'speed_state_extra_keys', 'exception')}
               for T, r in cmp_rows.items() if not r.get('pass_a')}
        return {'pass': all(T in cmp_rows for T in CAPTURABLE) and not bad, 'states_compared': len(cmp_rows),
                'failing_states': bad}

    def item_b():
        r = dict(spd[2700])
        r['declared'] = PROTO_2700
        r['pass'] = (r['changed_gt_1pct'] == PROTO_2700['changed_gt_1pct']
                     and r['to_nominal'] == PROTO_2700['to_nominal'] and not r['extra_keys'])
        return r

    def item_c():
        out, ok = {}, True
        for T in DELAY_STATES:
            d = dly[T]
            pct1 = round(d['pct'], 1)
            good = DELAY_RANGE_PCT[0] <= pct1 <= DELAY_RANGE_PCT[1]
            out[T] = {'pass': good, 'sum_k84': d['sum_k84'], 'sum_k85': d['sum_k85'], 'pct': d['pct'], 'pct_0_1': pct1,
                      'report_defects_8_2': DELAY_PROTO[T],
                      'report_equal_to_defects': (d['sum_k84'], d['sum_k85']) == DELAY_PROTO[T]}
            ok &= good
        out['pass'] = ok
        out['declared_range_pct'] = DELAY_RANGE_PCT
        return out

    def item_d():
        bad = {T: {k: r.get(k) for k in ('unchanged_max_abs', 'unchanged_present', 'exception')}
               for T, r in cmp_rows.items() if not r.get('pass_d')}
        worst = {}
        for r in cmp_rows.values():
            for k, x in (r.get('unchanged_max_abs') or {}).items():
                worst[k] = max(worst.get(k, 0.0), x)
        tworst = max((max_abs_diff(tgt84[T][1], tgt85[T][1]) for T in tgt84 if T in tgt85), default=None)
        oworst = max((max_abs_diff(tgt84[T][2], tgt85[T][2]) for T in tgt84 if T in tgt85), default=None)
        return {'pass': all(T in cmp_rows for T in CAPTURABLE) and not bad, 'states_compared': len(cmp_rows),
                'failing_states': bad, 'worst_by_quantity': worst,
                'target_queue_worst_abs': tworst, 'target_occupancy_worst_abs': oworst}

    def item_e():
        ok85 = [T for T in CAPTURABLE if caps[ARM85][T]['ok']]
        ok84 = [T for T in CAPTURABLE if caps[ARM84][T]['ok']]
        uncapturable = {T: {'k84': caps[ARM84][T], 'k85': caps[ARM85][T],
                            'same_failure': (not caps[ARM84][T]['ok'] and not caps[ARM85][T]['ok']
                                             and caps[ARM84][T].get('error_last_line')
                                             == caps[ARM85][T].get('error_last_line'))}
                        for T in STATES if T not in CAPTURABLE}
        return {'pass': len(ok85) == len(CAPTURABLE) and len(ok84) == len(CAPTURABLE), 'k85_success': len(ok85),
                'k84_success': len(ok84), 'declared': len(CAPTURABLE),
                'k85_failures_capturable': {T: caps[ARM85][T] for T in CAPTURABLE if not caps[ARM85][T]['ok']},
                'report_t1_t150': uncapturable}

    gate_owner = {}

    def item_f():
        g, owners = strict_gate(a.out, tgt84, tgt85)
        gate_owner.update(owners)
        # STOP: a target (T + 150k of a judged or reported start) differing between the trees by more than 1e-9
        used = sorted({T + BLOCK_SEC * k for T in set(JUDGE_STARTS) | set(REPORT_STARTS) for k in BLOCKS
                       if T + BLOCK_SEC * k <= END_SEC})
        g['targets_checked'] = len(used)
        for T2 in used:
            if T2 not in tgt84 or T2 not in tgt85:
                g['stop'].append(f'target {T2}: capture missing in an arm')
                g['pass'] = False
                continue
            if max_abs_diff(tgt84[T2][1], tgt85[T2][1]) > TOL or max_abs_diff(tgt84[T2][2], tgt85[T2][2]) > TOL:
                g['stop'].append(f'target {T2}: K8-5 capture differs from K8-4 by more than 1e-9')
                g['pass'] = False
        return g

    for name, fn in (('a_only_s9_field', item_a), ('b_proto_2700_56_8', item_b), ('c_delay_sum_pct', item_c),
                     ('d_unchanged_declared', item_d), ('e_captures_59', item_e), ('f_strict_merge_gate', item_f),
                     ('g_unit_tests', lambda: item_unit(a.unit_log))):
        try:
            items[name] = fn()
        except Exception:
            items[name] = {'pass': False, 'exception': traceback.format_exc()[-3000:]}

    # reports
    try:
        three = {}
        for T in DELAY_STATES:
            o = gate_owner.get(T)
            if not o:
                three[T] = None
                continue
            top = sorted(o['owner_delta'].items(), key=lambda kv: -abs(kv[1]))[:4]
            three[T] = {'objective': o['objective'], 'omega_delta': o['omega_delta'], 'top_owners': top,
                        'h3_s9_prototype_k7_vs_k7_s9': H3_S9[T]}
        allj = [gate_owner[T] for T in JUDGE_STARTS if gate_owner.get(T)]
        per_owner = {}
        for o in allj:
            for name, d in o['owner_delta'].items():
                per_owner.setdefault(name, []).append(d)
        rep['reference_owner_cost_delta_b6_5'] = {
            'declared_states': three,
            'judge_starts_n': len(allj),
            'judge_starts_omega_delta_mean': fsum(o['omega_delta'] for o in allj) / len(allj) if allj else None,
            'judge_starts_omega_delta_min_max': [min(o['omega_delta'] for o in allj),
                                                 max(o['omega_delta'] for o in allj)] if allj else None,
            'judge_starts_owner_mean_delta': {k: fsum(x) / len(x) for k, x in
                                              sorted(per_owner.items(), key=lambda kv: -abs(fsum(kv[1])))},
            'per_start': {T: (o and {'omega_delta': o['omega_delta'], 'objective': o['objective']})
                          for T, o in gate_owner.items()}}
    except Exception:
        rep['reference_owner_cost_delta_b6_5'] = {'exception': traceback.format_exc()[-2000:]}
    try:
        det = {}
        for T, want in K84_REF_OBJECTIVE.items():
            r = job(a.out, T, JOB84)
            old = job(a.out, T, 'k84_REF_scalar')
            det[T] = {'g85_k84': repr(r.get('objective_veh_h')), 'k84_gate': repr(old.get('objective_veh_h')),
                      'k84_gate_report': want,
                      'equal': repr(r.get('objective_veh_h')) == repr(old.get('objective_veh_h')) == want}
        rep['k84_rollout_determinism'] = det
    except Exception:
        rep['k84_rollout_determinism'] = {'exception': traceback.format_exc()[-2000:]}
    rep['speed_change_per_state'] = spd
    rep['prototype_speed_check'] = {'states': len(proto),
                                    'all_keys_equal': all(p.get('keys_equal') for p in proto.values()) if proto else None,
                                    'worst_abs_kph': max((p.get('worst_abs_kph', 0.0) for p in proto.values()),
                                                         default=None),
                                    'worst_rel': max((p.get('worst_rel', 0.0) for p in proto.values()), default=None),
                                    'per_state': proto}
    rep['delay_steps_per_state'] = dly
    rep['template_level_diffs'] = {T: {'template_key_diff': r.get('template_key_diff'), 'owned_diff': r.get('owned_diff'),
                                       'state_attr_bytes_diff': r.get('report_state_attr_bytes_diff')}
                                   for T, r in cmp_rows.items()}
    rep['captures'] = caps
    v['pass'] = all(x['pass'] for x in items.values())
    v['merge'] = bool(items.get('f_strict_merge_gate', {}).get('pass'))
    text = json.dumps(v, indent=1, default=str)
    if a.json:
        Path(a.json).write_text(text, encoding='utf-8')
    print(json.dumps({k: x['pass'] for k, x in items.items()}), 'PASS' if v['pass'] else 'FAIL')
    g = items.get('f_strict_merge_gate', {})
    for k in BLOCKS:
        b = (g.get('blocks') or {}).get(k) or {}
        print(f'block {k}: n={b.get("n")} sumC84={b.get("sum_C_k84")} sumC85={b.get("sum_C_k85")} W={b.get("W")} '
              f'ties={b.get("ties")} R1={b.get("R1")} R2={b.get("R2")}')
    if g.get('stop'):
        print('STOP:', g['stop'][:10])
    return 0 if v['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
