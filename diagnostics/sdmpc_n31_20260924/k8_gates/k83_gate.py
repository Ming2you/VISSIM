"""K8-3 (S1 + S1-OWN) gate judge (K8-0c; diagnostics only, reads outputs, runs nothing).

    python -B k83_gate.py --out <gates_out/k83> --k82 <gates_out/k82> --unit-log <pytest -v log> [--unit-log ...]
                          [--json <verdict.json>]

Declared values: K8_PREDECLARATION_AMENDMENT_1.md r2 §2 K8-3 row, as amended by amendment 2 (§2 N_P-4, §5 N-A2/N-A2'
(e)), under user decisions D-K8-2 (meter-owner cost attribution) and D-K8-5 (physical N_P accounting, amendment 3).
Fixed here, in a tool commit, before any K8-3 gate run. Comparison K8-3 - K8-2 (K8-2 = K7 numbers).

Layout under --out (one output root; captures per code root):
  out/<T>/jobs/k82_{REF,M2ALL}_scalar   K8-2 runtime (HEAD 5eef6be) baseline, cap_k82   (REF T in 900 1800 2700 4950
  out/<T>/jobs/k83_{REF,M2ALL}_scalar   K8-3 candidate, cap_k83                          6300; M2ALL 1800 2700 4950)
  out/002700/jobs/k83_REF_ad            surrogate reverse AD, REFERENCE
  out/002700/jobs/k83_M2ALL_adfull      non-surrogate reverse AD, M2ALL
  out/002700/jobs/k83_M2ALL_adfull_ownoff   same code, worker patch own_off (S1-OWN updates no-ops; gate (h))
  out/002700/full_k83                   full deployed decision
--k82 (the K8-2 gate output root, read only): out/002700/jobs/k82_M2ALL_adfull/result.pickle (K8-2 (f), sha256
  f4a5abac..., amendment 2 §2 binding input) and out/002700/jobs/k82_REF_ad/result.pickle (K8-2 surrogate REF AD).

Judged (all must pass; an exception inside an item fails that item):
  (a) M2ALL owner cost delta: FW_W, FW_E, PASSIVE_OMEGA each |d| <= 1e-3 veh*h; the other 17 owners repr-equal
  (b) M2ALL Omega |d| <= 1e-3
  (c) meter_spill_veh_h summed by meter owner, +-1e-6 of the declared values
  (d) T+450 spill E (+-1e-6): 10482|onW, 10490|onE, 10484|SC1001_W_out (4950: no 10484|SC1001_W_out entry);
      E = -(ramp stock delta) +-1e-6 (10482, 10490); E_10484 = -(SC1001_W_out available delta) +-1e-6
  (e) T+450 ramp stock delta +-0.01; for 10482 / 10490 the same amount reaches the feeder movement queue
      (SC1001_W_to_onW / _onE) +-1e-6. 10484 is judged only by its ramp delta here and by (d) (amendment 2 N-A2')
  (f) every K8-3 omega_costs call: partition total = ledger TTT, rel <= 1e-10
  (g) non-surrogate AD 2700 M2ALL: state_error <= 1e-8, complete match; 10482 own-owner derivative per green second
      blocks 0/1/2 = -0.4612 / -0.1660 / -0.0152 (+-1e-3, blocks 1 and 2 negative); own-meter 12-axis sums FW_W -1.394,
      FW_E -0.106 (+-0.01)
  (g') the 17 signal-owner rows of the cost Jacobian vs K8-2 (f): |d| <= 1e-9
  (h) S1-OWN off (same code, worker own_off) vs on: changed rows (|D| > 1e-12, an_ad.py) within {FW_W, FW_E,
      PASSIVE_OMEGA}; max |column-sum delta| <= 1e-12; objective repr equal; the off run applied own_off, no entry
  (h') same pair: resource Jacobian (2x231) and resources bit-identical
  (N_P-1) M2ALL scalar N_P delta (resources[0]) +-1e-6: 1800 -64.899994, 2700 -64.056146, 4950 -50.550202;
      non-surrogate AD 2700 M2ALL N_P delta vs K8-2 (f) -64.056146 +-1e-6
  (N_P-2) dN_P = -(E_10482|onW + E_10490|onE @T+450) +-1e-6 (three states)
  (N_P-3) M2ALL scalar N_UF (resources[1]) repr-equal
  (N_P-4) AD 2700 M2ALL vs K8-2 (f): N_UF row bit-identical; N_P row columns with |d| > 1e-9 exactly {64, 141, 218, 223}
      with d = +84.0, +84.0, +84.0, +1.76 (+-1e-6)
  (i) REFERENCE 900/1800/2700/4950/6300: objective, costs, resources repr = K8-2; no spill entry, no meter_spill_veh_h
  (ii) 2700 REFERENCE surrogate AD: cost and resource Jacobians bit-identical to K8-2
  (iii) 2700 full deployed decision: progress objective / held repr 498.5113776214157 / 501.1445316791073, exit 0
  (iv) unit tests diagnostics/test_k8_s1_admission_owner.py: the 7 S1 tests (AdmissionSpaceTests, DEFECTS §2.4, test 6
      with E <= rejected) and T-OWN-1..14 (MeterOwnerTests) each PASSED and none FAILED/ERROR/SKIPPED/SUBFAILED in the
      pytest 9 -v lines or the short summary; T-OWN-6 reads the K8-3 capture (K8_CAPTURED_TEMPLATE)
Reported: declared prototype values beside the measured ones, the K8-2 gate root's scalar results (cross-root repr
check), counts of 0 < |d| <= 1e-9 cells, owner self-derivative table, full owner deltas.
Ported calculation lines: amend1/s1/an_own.py (owner/block deltas), an_ad.py (meter derivative table, ii - i),
amend1r2/np_check.py (N_P identity), review_a1/rv_adrows.py (row max |d|), review_a1r2/rc_cols.py (changed N_P
columns), rc_ab1.py (17-row and resource comparisons); the reference is the K8-2 output instead of the K7 scratch.
"""
import argparse
import hashlib
import json
import pickle
import re
import traceback
from pathlib import Path

import numpy as np

STATES_REF = (900, 1800, 2700, 4950, 6300)
STATES_M2 = (1800, 2700, 4950)
FW = ('FW_W', 'FW_E', 'PASSIVE_OMEGA')
METER_OWNER = {'RM_C10480': 'FW_W', 'RM_C10482': 'FW_W', 'RM_C10646': 'FW_W', 'RM_C10644': 'FW_W',
               'RM_C10639': 'FW_E', 'RM_C10681': 'FW_E', 'RM_C10490': 'FW_E', 'RM_C10484': 'FW_E'}
TOL_OWNER = 1e-3
TOL_OMEGA = 1e-3
DECL_OWNER = {1800: (3.18e-5, -6.36e-5, 0.0), 2700: (8.55e-5, -1.710e-4, 0.0), 4950: (0.0, 1.4e-14, 0.0)}   # report
DECL_SPILL_VEH_H = {1800: {'FW_W': 1.011253, 'FW_E': 1.282791}, 2700: {'FW_W': 0.934243, 'FW_E': 1.311847},
                    4950: {'FW_W': 0.574982, 'FW_E': 0.603600}}
TOL_SPILL = 1e-6
E_KEYS = (('RM_C10482', 'movement:SC1001_W_to_onW'), ('RM_C10490', 'movement:SC1001_W_to_onE'),
          ('RM_C10484', 'storage:SC1001_W_out'))
DECL_E = {1800: (49.737288, 15.162705, 2.005495), 2700: (48.893441, 15.162705, 2.891375),
          4950: (38.280325, 12.269877, None)}
TOL_E = 1e-6
FEEDER_QUEUE = {'RM_C10482': 'SC1001_W_to_onW', 'RM_C10490': 'SC1001_W_to_onE'}
DECL_RAMP = {2700: {'RM_C10482': -48.89, 'RM_C10490': -15.16, 'RM_C10484': -2.99},
             4950: {'RM_C10482': -38.28, 'RM_C10490': -12.27},
             1800: {'RM_C10482': -49.74, 'RM_C10490': -15.16, 'RM_C10484': -2.06}}
TOL_RAMP = 0.01
TOL_SAME_AMOUNT = 1e-6
TOL_PARTITION_REL = 1e-10
STATE_ERROR_MAX = 1e-8
DECL_SELF_10482 = (-0.4612, -0.1660, -0.0152)
TOL_SELF = 1e-3
DECL_OWN_SUM = {'FW_W': -1.394, 'FW_E': -0.106}
TOL_OWN_SUM = 0.01
TOL_SIGNAL_ROWS = 1e-9
TOL_CHANGED_ROW = 1e-12       # an_ad.py changed-row definition
TOL_COLSUM = 1e-12
DECL_NP = {1800: -64.899994, 2700: -64.056146, 4950: -50.550202}
DECL_NP_AD = -64.056146
TOL_NP = 1e-6
NP4_COLS = (64, 141, 218, 223)
NP4_DELTA = (84.0, 84.0, 84.0, 1.76)
TOL_NP4_COL = 1e-9
TOL_NP4 = 1e-6
FULL_OBJ, FULL_HELD = '498.5113776214157', '501.1445316791073'
K82_F_SHA256 = 'f4a5abac8d94ca3150e041808a2d8a9d71f6c974afd5ea82b5cad2c22667200c'
S1_TESTS = ('test_s1_1_prehead_full_posthead_empty_admits_zero', 'test_s1_2_admits_only_what_head_service_frees',
            'test_s1_3_head_zero_unchanged', 'test_s1_4_initial_excess_preserved', 'test_s1_5_lane_min',
            'test_s1_6_rejected_urban_traffic_conserved', 'test_s1_7_forward_reverse_dual_agree')
OWN_TESTS = ('test_spill_absent_without_prehead_binding', 'test_spill_equals_k7_counterfactual',
             'test_spill_release_and_keep_entry', 'test_spill_capped_by_ready', 'test_partition_moves_cost_not_omega',
             'test_ramp_owner_mapping', 'test_multi_ramp_feeder_cap', 'test_creation_gate_primal',
             'test_physical_state_unchanged', 'test_sc2001_shared_factor_not_spill', 'test_lane_resolved_k7_space',
             'test_spill_reduces_k7_room', 'test_dual_forward_reverse_and_fd', 'test_zero_spill_keeps_derivative')
UNIT_FILES = {'diagnostics/test_k8_s1_admission_owner.py::AdmissionSpaceTests': S1_TESTS,
              'diagnostics/test_k8_s1_admission_owner.py::MeterOwnerTests': OWN_TESTS}
BAD_STATES = {'FAILED', 'ERROR', 'SKIPPED', 'XFAIL', 'XPASS', 'SUBFAILED', 'SUBSKIPPED'}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(p):
    return pickle.loads(Path(p).read_bytes())


def f(x):
    return float(getattr(x, 'value', x))


def job(root, T, label):
    p = Path(root) / 'out' / f'{T:06d}' / 'jobs' / label / 'result.pickle'
    return load(p) if p.is_file() else {'error': f'missing {p}'}


def blocks(r):
    return (r.get('summary') or {}).get('blocks') or []


def last_omega(r):
    calls = (r.get('summary') or {}).get('omega_calls') or []
    return calls[-1] if calls else {}


def owner_delta(a, b, order):          # an_own.py
    return {order[i]: y - x for i, (x, y) in enumerate(zip(a['costs'], b['costs'])) if y != x}


def last_progress(d, T):
    rows = [json.loads(x) for x in (d / f'action_{T:06d}.joint.progress.jsonl').read_text(encoding='utf-8').splitlines()
            if x.strip()]
    for r in reversed(rows):
        if 'objective' in r or 'held_objective' in r:
            return repr(r.get('objective')), repr(r.get('held_objective'))
    return None, None


def unit_results(logs):
    """pytest 9 -v lines '<nodeid> STATE' and short-summary '(SUB)FAILED|ERROR <nodeid>' lines -> {nodeid: states}."""
    seen = {}
    for log in logs:
        raw = Path(log).read_bytes()
        text = raw.decode('utf-16') if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else raw.decode('utf-8', errors='replace')
        for m in re.finditer(r'^(\S+?::\S+?)\s+(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS|SUBPASSED|SUBFAILED|SUBSKIPPED)\b',
                             text, re.M):
            seen.setdefault(m.group(1), set()).add(m.group(2))
        for m in re.finditer(r'^(FAILED|ERROR|SUBFAILED)(?:\[[^\]]*\]|\(.*?\))? (\S+?::\S+)\s*$', text, re.M):
            seen.setdefault(m.group(2), set()).add('FAILED')
    return seen


class Ctx:
    def __init__(self, a):
        self.O, self.K82, self.logs = Path(a.out), Path(a.k82), a.unit_log
        self.m2 = {T: (job(self.O, T, 'k82_M2ALL_scalar'), job(self.O, T, 'k83_M2ALL_scalar')) for T in STATES_M2}
        self.order = None
        for T in STATES_M2:
            self.order = self.order or self.m2[T][1].get('costs_order') or self.m2[T][0].get('costs_order')
        self.errors = {f'{T} M2ALL {n}': r.get('error') for T, pair in self.m2.items()
                       for n, r in zip(('k82', 'k83'), pair) if r.get('error')}
        self.e450 = {}
        kf_path = self.K82 / 'out/002700/jobs/k82_M2ALL_adfull/result.pickle'
        self.kf_sha = sha(kf_path) if kf_path.is_file() else None
        self.kf = load(kf_path) if self.kf_sha == K82_F_SHA256 else None
        self.ad = job(self.O, 2700, 'k83_M2ALL_adfull')
        self.off = job(self.O, 2700, 'k83_M2ALL_adfull_ownoff')
        self.axes = self.ad.get('axes') or []
        self.aorder = self.ad.get('costs_order') or self.order


def item_a(c):
    rows, ok = [], not c.errors
    for T, (base, cand) in c.m2.items():
        if base.get('error') or cand.get('error'):
            continue
        d = {c.order[i]: y - x for i, (x, y) in enumerate(zip(base['costs'], cand['costs']))}
        others = {o: (repr(base['costs'][i]), repr(cand['costs'][i])) for i, o in enumerate(c.order) if o not in FW}
        bad = {o: pr for o, pr in others.items() if pr[0] != pr[1]}
        r = {'T': T, 'delta': {o: d[o] for o in FW}, 'declared_report': dict(zip(FW, DECL_OWNER[T])),
             'other17_not_repr_equal': bad, 'n_other': len(others)}
        r['pass'] = all(abs(d[o]) <= TOL_OWNER for o in FW) and not bad and len(others) == 17
        ok &= r['pass']
        rows.append(r)
    return {'pass': ok and len(rows) == 3, 'rows': rows, 'errors': c.errors}


def item_b(c):
    rows, ok = [], not c.errors
    for T, (base, cand) in c.m2.items():
        if base.get('error') or cand.get('error'):
            continue
        dom = cand['objective_veh_h'] - base['objective_veh_h']
        rows.append({'T': T, 'omega_delta': dom, 'pass': abs(dom) <= TOL_OMEGA})
        ok &= abs(dom) <= TOL_OMEGA
    return {'pass': ok and len(rows) == 3, 'rows': rows}


def item_c(c):
    rows, ok = [], not c.errors
    for T, (base, cand) in c.m2.items():
        part = last_omega(cand).get('meter_spill_veh_h') or {}
        by_owner, unknown = {'FW_W': 0.0, 'FW_E': 0.0}, {}
        for ramp, by in part.items():
            o = METER_OWNER.get(ramp)
            if o is None:
                unknown[ramp] = by
                continue
            by_owner[o] += sum(by.values())
        r = {'T': T, 'by_owner': by_owner, 'declared': DECL_SPILL_VEH_H[T], 'by_ramp_feeder': part, 'unknown': unknown,
             'base_has_key': last_omega(base).get('meter_spill_veh_h') is not None}
        r['pass'] = bool(part) and not unknown and all(abs(by_owner[o] - DECL_SPILL_VEH_H[T][o]) <= TOL_SPILL
                                                       for o in by_owner)
        ok &= r['pass']
        rows.append(r)
    return {'pass': ok, 'rows': rows}


def item_d_e(c):
    rows_d, ok_d, rows_e, ok_e = [], not c.errors, [], not c.errors
    for T, (base, cand) in c.m2.items():
        bb, cb = blocks(base), blocks(cand)
        if len(bb) != 3 or len(cb) != 3:
            ok_d = ok_e = False
            rows_d.append({'T': T, 'error': 'block summary missing'})
            continue
        b2, c2 = bb[2], cb[2]
        spill = c2.get('meter_spill') or {}
        e = [spill.get(r, {}).get(fd) for r, fd in E_KEYS]
        c.e450[T] = e
        ramp_d = {r: c2['ramp_queue'][r] - b2['ramp_queue'][r] for r in b2['ramp_queue']}
        queue_d = {r: c2['movement_queue'][q] - b2['movement_queue'][q] for r, q in FEEDER_QUEUE.items()}
        avail_d = c2['storage_available']['SC1001_W_out'] - b2['storage_available']['SC1001_W_out']
        checks = []
        for (ramp, fd), got, want in zip(E_KEYS, e, DECL_E[T]):
            if want is None:
                checks.append(('absent ' + ramp, got is None))
            else:
                checks.append((f'E {ramp}', got is not None and abs(got - want) <= TOL_E))
        for ramp in ('RM_C10482', 'RM_C10490'):
            got = spill.get(ramp, {}).get(dict(E_KEYS)[ramp])
            checks.append((f'E=-ramp {ramp}', got is not None and abs(got + ramp_d[ramp]) <= TOL_E))
        if DECL_E[T][2] is not None:
            checks.append(('E=-avail 10484', e[2] is not None and abs(e[2] + avail_d) <= TOL_E))
        r = {'T': T, 'E': dict(zip([f'{x}|{y}' for x, y in E_KEYS], e)), 'declared': DECL_E[T],
             'ramp_delta': ramp_d, 'feeder_queue_delta': queue_d, 'SC1001_W_out_available_delta': avail_d,
             'all_entries_T450': spill, 'time_sec': [b2.get('time_sec'), c2.get('time_sec')], 'checks': checks,
             'pass': all(x for _, x in checks)}
        ok_d &= r['pass']
        rows_d.append(r)
        ce = [(f'ramp {ramp}', abs(ramp_d[ramp] - want) <= TOL_RAMP) for ramp, want in DECL_RAMP[T].items()]
        ce += [(f'feeder {ramp}', abs(queue_d[ramp] + ramp_d[ramp]) <= TOL_SAME_AMOUNT) for ramp in FEEDER_QUEUE]
        rows_e.append({'T': T, 'declared': DECL_RAMP[T], 'ramp_delta': {k: ramp_d[k] for k in DECL_RAMP[T]},
                       'feeder_plus_ramp': {k: queue_d[k] + ramp_d[k] for k in FEEDER_QUEUE},
                       'report_10484_ramp_minus_E': (ramp_d.get('RM_C10484', 0.0) + (e[2] or 0.0)),
                       'checks': ce, 'pass': all(x for _, x in ce)})
        ok_e &= rows_e[-1]['pass']
    return ({'pass': ok_d and len(rows_d) == 3, 'rows': rows_d},
            {'pass': ok_e and len(rows_e) == 3, 'rows': rows_e})


def item_f(c):
    rows, ok = [], True
    labels = ([(T, 'k83_REF_scalar') for T in STATES_REF] + [(T, 'k83_M2ALL_scalar') for T in STATES_M2]
              + [(2700, 'k83_REF_ad'), (2700, 'k83_M2ALL_adfull'), (2700, 'k83_M2ALL_adfull_ownoff')])
    for T, label in labels:
        r = job(c.O, T, label)
        calls = (r.get('summary') or {}).get('omega_calls') or []
        worst = max((abs(x['total'] - x['ledger_ttt']) / max(1e-300, abs(x['ledger_ttt'])) for x in calls
                     if 'total' in x), default=None)
        bad = bool(r.get('error')) or not calls or any('record_error' in x for x in calls) or worst is None \
            or worst > TOL_PARTITION_REL
        rows.append({'T': T, 'label': label, 'calls': len(calls), 'max_rel': worst, 'pass': not bad})
        ok &= not bad
    return {'pass': ok, 'rows': rows}


def item_g(c):
    ad, axes, aorder = c.ad, c.axes, c.aorder
    g = {'error': (ad.get('error') or '')[-1500:], 'n_axes': len(axes)}
    if ad.get('error') or not axes:
        g['pass'] = False
        return g
    J = np.asarray(ad['cost_jacobian'], dtype=np.float64)
    err = ad.get('max_primal_state_error')
    meters = [j for j, x in enumerate(axes) if x['kind'] == 'meter']
    table = []
    for j in meters:                                        # an_ad.py meter derivative table
        x = axes[j]
        table.append(dict(axis=j, key=x['key'], owner=x['owner'], block=x.get('block', 0), scale=x['scale'],
                          own=float(J[aorder.index(x['owner']), j]) / x['scale'],
                          passive=float(J[aorder.index('PASSIVE_OMEGA'), j]) / x['scale'],
                          colsum=float(J[:, j].sum()) / x['scale']))
    self_10482 = [r['own'] for r in sorted((r for r in table if r['key'] == 'RM_C10482'), key=lambda r: r['block'])]
    own_sum = {o: float(sum(J[aorder.index(o), j] / axes[j]['scale'] for j in meters if axes[j]['owner'] == o))
               for o in ('FW_W', 'FW_E')}
    n_meter = {o: sum(axes[j]['owner'] == o for j in meters) for o in ('FW_W', 'FW_E')}
    g.update(max_primal_state_error=err, complete_primal_state_match=ad.get('complete_primal_state_match'),
             shape=list(J.shape), self_10482=self_10482, declared_self_10482=DECL_SELF_10482, own_meter_sum=own_sum,
             declared_own_sum=DECL_OWN_SUM, n_meter_axes=n_meter, meter_table=table)
    g['pass'] = bool(err is not None and err <= STATE_ERROR_MAX and ad.get('complete_primal_state_match') is True
                     and len(self_10482) == 3
                     and all(abs(x - y) <= TOL_SELF for x, y in zip(self_10482, DECL_SELF_10482))
                     and self_10482[1] < 0 and self_10482[2] < 0
                     and all(abs(own_sum[o] - DECL_OWN_SUM[o]) <= TOL_OWN_SUM for o in own_sum)
                     and n_meter == {'FW_W': 12, 'FW_E': 12})
    return g


def item_gprime_np4(c):
    ad, kf, axes, aorder = c.ad, c.kf, c.axes, c.aorder
    base = {'k82_f_sha256': c.kf_sha, 'k82_f_sha_ok': c.kf_sha == K82_F_SHA256}
    if kf is None or ad.get('error') or not axes:
        return dict(base, pass_=False), dict(base, pass_=False), None
    J, K = np.asarray(ad['cost_jacobian'], dtype=np.float64), np.asarray(kf['cost_jacobian'], dtype=np.float64)
    D = J - K
    sig = [i for i, o in enumerate(aorder) if o not in FW]
    row_max = {aorder[i]: float(np.abs(D[i]).max()) for i in range(D.shape[0]) if np.abs(D[i]).max() > 0}  # rv_adrows
    gp = dict(base, n_signal_rows=len(sig), signal_rows_maxabs=float(np.abs(D[sig]).max()), row_maxabs=row_max,
              shape_equal=J.shape == K.shape)
    gp['pass_'] = J.shape == K.shape and len(sig) == 17 and gp['signal_rows_maxabs'] <= TOL_SIGNAL_ROWS
    RJ, RK = np.asarray(ad['resource_jacobian'], dtype=np.float64), np.asarray(kf['resource_jacobian'], dtype=np.float64)
    RD = RJ - RK
    cols = [int(x) for x in np.nonzero(np.abs(RD[0]) > TOL_NP4_COL)[0]]                         # rc_cols.py
    np4 = dict(base, changed_cols=cols, names=[dict(axes[x]) for x in cols if x < len(axes)],
               delta=[float(RD[0, x]) for x in cols], k82=[float(RK[0, x]) for x in cols],
               k83=[float(RJ[0, x]) for x in cols], nuf_row_changed_cells=int((RD[1] != 0).sum()),
               np_row_small_cells=int(((np.abs(RD[0]) > 0) & (np.abs(RD[0]) <= TOL_NP4_COL)).sum()),
               row_maxabs=[float(np.abs(RD[k]).max()) for k in range(RD.shape[0])], shape=list(RD.shape))
    np4['pass_'] = (RD.shape == (2, len(axes)) and np4['nuf_row_changed_cells'] == 0 and tuple(cols) == NP4_COLS
                    and all(abs(x - y) <= TOL_NP4 for x, y in zip(np4['delta'], NP4_DELTA)))
    return gp, np4, f(ad['resources'][0]) - f(kf['resources'][0])


def item_h(c):
    ad, off, aorder = c.ad, c.off, c.aorder
    h = {'error': [(ad.get('error') or '')[-800:], (off.get('error') or '')[-800:]]}
    if ad.get('error') or off.get('error') or not c.axes:
        return dict(h, pass_=False), {'pass': False}
    J, I = np.asarray(ad['cost_jacobian'], dtype=np.float64), np.asarray(off['cost_jacobian'], dtype=np.float64)
    D = J - I                                                                                  # an_ad.py ii - i
    changed = sorted({aorder[i] for i in np.nonzero(np.abs(D) > TOL_CHANGED_ROW)[0]})
    exact_changed = sorted({aorder[i] for i in np.nonzero(D != 0)[0]})
    colsum = float(np.abs(D.sum(axis=0)).max())
    oa, oo = (ad.get('summary') or {}).get('objective'), (off.get('summary') or {}).get('objective')
    off_blocks = blocks(off)
    h.update(changed_rows=changed, exact_changed_rows=exact_changed, max_abs=float(np.abs(D).max()),
             max_abs_colsum_delta=colsum, cols_changed=int(np.sum(np.any(np.abs(D) > TOL_CHANGED_ROW, axis=0))),
             objective=[repr(oa), repr(oo)], ownoff_patched=off.get('patched'),
             ownoff_spill_entries=[b.get('meter_spill') for b in off_blocks],
             on_spill_entries_T450=(blocks(ad)[2].get('meter_spill') if len(blocks(ad)) == 3 else None),
             ownoff_state_error=off.get('max_primal_state_error'))
    h['pass_'] = bool(set(changed) <= set(FW) and colsum <= TOL_COLSUM and oa is not None and repr(oa) == repr(oo)
                      and any('meter_spill' in str(x) for x in (off.get('patched') or []))
                      and len(off_blocks) == 3 and all(not b.get('meter_spill') for b in off_blocks))
    RJ, RI = np.asarray(ad['resource_jacobian'], dtype=np.float64), np.asarray(off['resource_jacobian'], dtype=np.float64)
    hp = {'resource_jacobian_bit_identical': RJ.shape == RI.shape and RJ.tobytes() == RI.tobytes(),
          'resources': [[repr(f(x)) for x in ad['resources']], [repr(f(x)) for x in off['resources']]]}
    hp['resources_equal'] = hp['resources'][0] == hp['resources'][1]
    hp['pass'] = hp['resource_jacobian_bit_identical'] and hp['resources_equal']
    return h, hp


def item_np(c, np1_ad):
    rows, ok1, ok2, ok3 = [], not c.errors, not c.errors, not c.errors
    for T, (base, cand) in c.m2.items():
        if base.get('error') or cand.get('error'):
            continue
        a0, b0 = [f(x) for x in base['resources']], [f(x) for x in cand['resources']]
        dnp = b0[0] - a0[0]
        e = c.e450.get(T) or [None, None, None]
        eon = (e[0] or 0.0) + (e[1] or 0.0)
        r = {'T': T, 'NP_k82': a0[0], 'NP_k83': b0[0], 'dNP': dnp, 'declared': DECL_NP[T],
             'E_onW_plus_onE': eon, 'identity_residual': dnp + eon,
             'NUF_repr': [repr(f(base['resources'][1])), repr(f(cand['resources'][1]))]}
        r['np1'] = abs(dnp - DECL_NP[T]) <= TOL_NP
        r['np2'] = e[0] is not None and e[1] is not None and abs(dnp + eon) <= TOL_NP
        r['np3'] = r['NUF_repr'][0] == r['NUF_repr'][1]
        ok1 &= r['np1']
        ok2 &= r['np2']
        ok3 &= r['np3']
        rows.append(r)
    full = len(rows) == 3
    ad_ok = np1_ad is not None and abs(np1_ad - DECL_NP_AD) <= TOL_NP
    return ({'pass': bool(ok1 and ad_ok and full), 'rows': rows, 'ad_dNP': np1_ad, 'ad_declared': DECL_NP_AD},
            {'pass': bool(ok2 and full), 'residuals': {r['T']: r['identity_residual'] for r in rows}},
            {'pass': bool(ok3 and full), 'rows': {r['T']: r['NUF_repr'] for r in rows}})


def item_i(c):
    rows, ok = [], True
    for T in STATES_REF:
        base, cand = job(c.O, T, 'k82_REF_scalar'), job(c.O, T, 'k83_REF_scalar')
        if base.get('error') or cand.get('error'):
            rows.append({'T': T, 'error': [base.get('error'), cand.get('error')], 'pass': False})
            ok = False
            continue
        spill_blocks = [b.get('meter_spill') for b in blocks(cand)]
        spill_calls = [x.get('meter_spill_veh_h') for x in (cand.get('summary') or {}).get('omega_calls') or []]
        r = {'T': T, 'objective': [repr(base['objective_veh_h']), repr(cand['objective_veh_h'])],
             'costs_equal': [repr(x) for x in base['costs']] == [repr(x) for x in cand['costs']],
             'resources_equal': [repr(f(x)) for x in base['resources']] == [repr(f(x)) for x in cand['resources']],
             'spill_blocks': spill_blocks, 'spill_veh_h_calls': spill_calls}
        r['pass'] = bool(r['objective'][0] == r['objective'][1] and r['costs_equal'] and r['resources_equal']
                         and len(spill_blocks) == 3 and not any(spill_blocks) and spill_calls
                         and all(x is None for x in spill_calls))
        ok &= r['pass']
        rows.append(r)
    return {'pass': ok, 'rows': rows}


def item_ii(c):
    base, cand = job(c.K82, 2700, 'k82_REF_ad'), job(c.O, 2700, 'k83_REF_ad')
    r = {'errors': [base.get('error'), cand.get('error')]}
    if base.get('error') or cand.get('error'):
        r['pass'] = False
        return r
    for k in ('cost_jacobian', 'resource_jacobian'):
        C, B = np.array(cand[k], dtype=np.float64), np.array(base[k], dtype=np.float64)
        r[k + '_bit_identical'] = C.shape == B.shape and C.tobytes() == B.tobytes()
        r[k + '_changed_cells'] = int((C != B).sum()) if C.shape == B.shape else None
    r['objective'] = [repr(base.get('objective_veh_h')), repr(cand.get('objective_veh_h'))]
    r['spill_blocks'] = [b.get('meter_spill') for b in blocks(cand)]
    r['pass'] = r['cost_jacobian_bit_identical'] and r['resource_jacobian_bit_identical']
    return r


def item_iii(c):
    fd = c.O / 'out/002700/full_k83'
    prog = last_progress(fd, 2700)
    run = json.loads((fd / 'run.json').read_text(encoding='utf-8'))
    return {'pass': prog == (FULL_OBJ, FULL_HELD) and run.get('exit') == 0, 'progress': prog,
            'declared': (FULL_OBJ, FULL_HELD), 'run': run}


def item_iv(c):
    seen = unit_results(c.logs)
    rows, ok = [], True
    for prefix, names in UNIT_FILES.items():
        for name in names:
            hits = {k: s for k, s in seen.items() if k == prefix + '::' + name}
            states = set().union(*hits.values()) if hits else set()
            good = 'PASSED' in states and not (states & BAD_STATES)
            rows.append({'test': f'{prefix}::{name}', 'states': sorted(states), 'pass': good})
            ok &= good
    return {'pass': ok, 'rows': rows, 'logs': [str(x) for x in c.logs],
            'n_declared': sum(len(x) for x in UNIT_FILES.values())}


def guarded(v, name, fn, *args):
    try:
        out = fn(*args)
    except Exception:
        v['items'][name] = {'pass': False, 'exception': traceback.format_exc()[-3000:]}
        return None
    v['items'][name] = out
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True, help='K8-3 gate output root (gates_out/k83)')
    ap.add_argument('--k82', required=True, help='K8-2 gate output root (gates_out/k82), read only')
    ap.add_argument('--unit-log', action='append', required=True)
    ap.add_argument('--json')
    a = ap.parse_args()
    c = Ctx(a)
    v = {'items': {}, 'report': {}}
    guarded(v, 'a_owner_costs', item_a, c)
    guarded(v, 'b_omega', item_b, c)
    guarded(v, 'c_meter_spill_veh_h', item_c, c)
    try:
        v['items']['d_spill_E_T450'], v['items']['e_ramp_and_feeder'] = item_d_e(c)
    except Exception:
        tb = traceback.format_exc()[-3000:]
        v['items']['d_spill_E_T450'] = v['items']['e_ramp_and_feeder'] = {'pass': False, 'exception': tb}
    guarded(v, 'f_partition_total', item_f, c)
    guarded(v, 'g_nonsurrogate_ad', item_g, c)
    np1_ad = None
    try:
        gp, np4, np1_ad = item_gprime_np4(c)
        gp['pass'], np4['pass'] = gp.pop('pass_'), np4.pop('pass_')
        v['items']['g_prime_signal_rows'], v['items']['np4_resource_jacobian'] = gp, np4
    except Exception:
        tb = traceback.format_exc()[-3000:]
        v['items']['g_prime_signal_rows'] = v['items']['np4_resource_jacobian'] = {'pass': False, 'exception': tb}
    try:
        h, hp = item_h(c)
        h['pass'] = h.pop('pass_')
        v['items']['h_ownoff_rows'], v['items']['h_prime_ownoff_resources'] = h, hp
    except Exception:
        tb = traceback.format_exc()[-3000:]
        v['items']['h_ownoff_rows'] = v['items']['h_prime_ownoff_resources'] = {'pass': False, 'exception': tb}
    try:
        v['items']['np1_np_delta'], v['items']['np2_identity'], v['items']['np3_nuf'] = item_np(c, np1_ad)
    except Exception:
        tb = traceback.format_exc()[-3000:]
        for k in ('np1_np_delta', 'np2_identity', 'np3_nuf'):
            v['items'][k] = {'pass': False, 'exception': tb}
    guarded(v, 'i_reference_repr', item_i, c)
    guarded(v, 'ii_reference_ad', item_ii, c)
    guarded(v, 'iii_full_decision', item_iii, c)
    guarded(v, 'iv_unit_tests', item_iv, c)

    try:
        cross = {}
        for T in STATES_M2:
            for A in ('REF', 'M2ALL'):
                x, y = job(c.K82, T, f'k82_{A}_scalar'), job(c.O, T, f'k82_{A}_scalar')
                if not x.get('error') and not y.get('error'):
                    cross[f'{T} {A}'] = (repr(x['objective_veh_h']) == repr(y['objective_veh_h'])
                                         and [repr(z) for z in x['costs']] == [repr(z) for z in y['costs']]
                                         and [repr(f(z)) for z in x['resources']] == [repr(f(z)) for z in y['resources']])
        v['report']['k82_cross_root_scalar_repr_equal'] = cross
        v['report']['owner_delta_full'] = {T: owner_delta(b, x, c.order) for T, (b, x) in c.m2.items()
                                           if not b.get('error') and not x.get('error')}
    except Exception:
        v['report']['exception'] = traceback.format_exc()[-2000:]
    v['pass'] = all(x['pass'] for x in v['items'].values())
    text = json.dumps(v, indent=1, default=str)
    if a.json:
        Path(a.json).write_text(text, encoding='utf-8')
    print(json.dumps({k: x['pass'] for k, x in v['items'].items()}), 'PASS' if v['pass'] else 'FAIL')
    return 0 if v['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
