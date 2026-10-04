"""K8-4 (S5 residual stopped split) gate judge (K8-0d; diagnostics only, reads outputs, runs nothing).

    python -B k84_gate.py --out <gates_out/k84> --unit-log <pytest -v log> [--unit-log ...] [--json <verdict.json>]
                          [--root <code root for unpickling>]

Declared values: K8_PREDECLARATION_AMENDMENT_1.md r2 §B.7 and §2 K8-4 row (amendment 2 leaves the row unchanged),
DEFECTS.md §5.3 as corrected by B7. Fixed here, in a tool commit, before any K8-4 gate run. Comparison K8-4 - K8-3
(the runtime commit just before; K8-3 = 91bfa56). Both arms are captured into one output root by the unpatched
cap_child ('base' variant), so replay paths are the same in both arms.

Layout under --out:
  replays/<T>/                 prep.py copies of the 61 R-obs3 decision states (T = 1, 150, ..., 9000)
  out/<T>/cap_k83/             K8-3 runtime (HEAD 91bfa56, clean worktree) capture
  out/<T>/cap_k84/             K8-4 candidate capture (kept: the K8-5 strict gate reuses these 61, amendment 1 §2.1)
  out/<T>/jobs/k8{3,4}_REF_scalar   REFERENCE scalar rollouts at 1800 / 2700 / 4950 (report only, B6-5)

Judged (all must pass; an exception inside an item fails that item):
  (a) +105 -> +15 shift at T = 1800 / 2700 / 4950: in the captured initial state, the K8-4 - K8-3 arrival-buffer
      delta summed over links at offset +15 s equals +159.132 / +197.121 / +113.203 (+-0.001) and at offset +105 s
      the negative of it (+-0.001); every other offset |delta| <= 1e-9
  (b) link 127's share of that shift (+-0.001): 11.304 / 11.782 / 8.438 = K8-4 diagnostic row 127|in_SC1001_W
      moving - the K8-3 rule's moving for the same storage share (assigned * (1 - min(1, max(0, stopped / count))),
      with count / stopped / queue from the K8-3 capture and assigned = the K8-4 row's moving + stopped)
  (c) only the S5 fields change, on every state captured by both arms: every TrafficState attribute other than
      urban_arrival_buffer, urban_storage_release_buffer, local_observation_summary and
      _conservative_initial_transit_applied (numbers +-1e-9) pickles to the same bytes; in local_observation_summary
      only urban_link_storage_stopped, urban_arrival_seed, projection_diagnostics and the new urban_link_storage_by_link
      differ; in projection_diagnostics every K8-3 key is byte-equal and the new keys are exactly
      residual_stopped_split_links, residual_stopped_ready_exceeds_stopped_links / _veh, storage_seed_split_by_link,
      storage_seed_split_rows, storage_seed_split_unattributed_veh; the two buffers differ only at offsets +15 / +105
      and keep every link's total (+-1e-9)
  (d) must not change, every state captured by both arms (subset of (c), named as declared): seed totals (per-link
      arrival totals +-1e-9, urban_arrival_seed links equal and moving + stopped +-1e-9), movement queues
      (urban_movement_queue state and summary byte-equal), storage occupancy (urban_link_storage and summary
      occupancy byte-equal), speeds (urban_link_speed_kph byte-equal), ramp stocks (ramp_queue and lane_ramp_runtime
      byte-equal)
  (e) R-obs3 61-state capture: 61/61 K8-4 captures succeed (capture.json with meta; template present)
  (f) violation counts recorded: every successful K8-4 capture carries residual_stopped_ready_exceeds_stopped_links
      and _veh (finite numbers); at 1800 / 2700 / 4950 both are 0
  (g) split assertion, every successful K8-4 capture: storage_seed_split_by_link present; every row has finite
      moving >= 0, stopped >= 0 and int due steps equal to step0 + 15 / step0 + 105 (step0 = round(time / T_u));
      for every storage in the split, rows + unattributed = the seed's own (moving, stopped) recomputed from the
      summary occupancy / stopped (+-1e-9 each); the number of split storages = urban_arrival_seed links;
      unattributed in_SC1001_W absent or |moving|, |stopped| <= 1e-9
  (h) unit tests diagnostics/test_k8_s5_residual_stopped.py: every declared test PASSED and none FAILED / ERROR /
      SKIPPED / SUBFAILED in the pytest 9 -v lines or the short summary (amendment 6 §1 rule)
Reported: the K8-3 arm's capture failures beside the K8-4 ones (same exception text?), projection-level shift and
per-source split from the K8-4 locals, the 127 rows (spec amendment §5.8-7 example (30, 13) / (48, 35) / (44, 74)),
violation counts of all states, rows vs physical_stock_assignment_by_link, REFERENCE owner cost deltas (B6-5;
amendment 1 §H.3 values: S5 1800 PASSIVE -1.895, SC1003 +0.399, SC11 +0.265, Omega -0.695; 2700 PASSIVE -2.431,
SC1004 +0.313, Omega -0.432; 4950 PASSIVE -1.633, SC1004 +0.231, Omega -0.898), template-level diffs.
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
SHIFT = {1800: 159.132, 2700: 197.121, 4950: 113.203}           # amendment 1 r2 §2 K8-4 row
SHARE_127 = {1800: 11.304, 2700: 11.782, 4950: 8.438}
TOL_SHIFT = 1e-3
TOL = 1e-9
GATE_STORAGE = 'in_SC1001_W'
L127 = '127'
TAU_MOVING, TAU_STOPPED = 15.0, 105.0                          # ADP _ARRIVAL_TAU_*_SEC
ALLOWED_STATE = {'urban_arrival_buffer', 'urban_storage_release_buffer', 'local_observation_summary'}
NUMERIC_STATE = {'_conservative_initial_transit_applied'}
ALLOWED_SUMMARY = {'urban_link_storage_stopped', 'urban_arrival_seed', 'projection_diagnostics'}
NEW_SUMMARY = {'urban_link_storage_by_link'}
NEW_DIAG = {'residual_stopped_split_links', 'residual_stopped_ready_exceeds_stopped_links',
            'residual_stopped_ready_exceeds_stopped_veh', 'storage_seed_split_by_link', 'storage_seed_split_rows',
            'storage_seed_split_unattributed_veh'}
UNIT_FILE = 'diagnostics/test_k8_s5_residual_stopped.py'
UNIT_TESTS = {
    'ResidualStoppedRuleTests': ('test_contiguous_link_127_uses_the_residual',
                                 'test_stopped_instant_link_has_no_stopped_residual',
                                 'test_ready_queue_above_observed_stopped_is_clipped_and_counted',
                                 'test_constant_and_physical_branch_links_keep_the_k83_rule',
                                 'test_link_without_movements_is_bit_identical_to_the_old_rule',
                                 'test_only_the_stopped_split_changes'),
    'SeedSplitTests': ('test_rows_sum_to_the_scheduled_seed_with_due_cells', 'test_two_storages_and_a_step_length',
                       'test_mass_without_a_link_part_is_unattributed',
                       'test_split_assertion_refuses_a_part_with_stopped_above_occupancy',
                       'test_storage_outside_routing_and_seed_off_write_nothing',
                       'test_kind_the_seed_does_not_schedule_is_zero_in_every_row',
                       'test_projection_error_is_not_raised_by_the_rule')}
BAD_STATES = {'FAILED', 'ERROR', 'SKIPPED', 'XFAIL', 'XPASS', 'SUBFAILED', 'SUBSKIPPED'}
H3 = {1800: {'PASSIVE_OMEGA': -1.895, 'SC1003': 0.399, 'SC11': 0.265, 'Omega': -0.695},
      2700: {'PASSIVE_OMEGA': -2.431, 'SC1004': 0.313, 'Omega': -0.432},
      4950: {'PASSIVE_OMEGA': -1.633, 'SC1004': 0.231, 'Omega': -0.898}}


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


class Arm:
    def __init__(self, out, T, arm):
        self.T, self.arm = T, arm
        self.status = capture_status(out, T, arm)
        self.t = pickle.loads((cap_dir(out, T, arm) / 'template.pickle').read_bytes()) if self.status['ok'] else None

    @property
    def state(self):
        return self.t['owned'][1]

    @property
    def cfg(self):
        return self.t['owned'][0].cfg

    @property
    def summary(self):
        return self.state.local_observation_summary

    def step0(self):
        return int(round(float(self.state.time_sec) / float(self.cfg.simulation.T_u_sec)))


def offset_profile(buffer, step0):
    prof = {}
    for _link, d in buffer.items():
        for step, n in d.items():
            prof[int(step) - step0] = prof.get(int(step) - step0, 0.0) + float(n)
    return prof


def buffer_diff(a, b, step0):
    """(bad cells off +15/+105, worst per-link total delta, delta profile)."""
    bad, worst = [], 0.0
    for link in set(a) | set(b):
        x, y = a.get(link, {}), b.get(link, {})
        for step in set(x) | set(y):
            d = float(y.get(step, 0.0)) - float(x.get(step, 0.0))
            if d != 0.0 and int(step) - step0 not in (15, 105):
                bad.append([link, int(step) - step0, d])
        worst = max(worst, abs(math.fsum(map(float, y.values())) - math.fsum(map(float, x.values()))))
    pa, pb = offset_profile(a, step0), offset_profile(b, step0)
    prof = {k: pb.get(k, 0.0) - pa.get(k, 0.0) for k in sorted(set(pa) | set(pb))}
    return bad, worst, prof


def numeric_close(x, y):
    if isinstance(x, dict) and isinstance(y, dict):
        return set(x) == set(y) and all(numeric_close(x[k], y[k]) for k in x)
    if isinstance(x, (int, float)) and isinstance(y, (int, float)):
        return abs(float(x) - float(y)) <= TOL
    return pk(x) == pk(y)


def compare(a, b):
    """Item (c)/(d) facts for one state captured by both arms (a = K8-3, b = K8-4)."""
    sa, sb = a.state, b.state
    r = {}
    keys = set(vars(sa)) | set(vars(sb))
    r['state_attr_diff'] = sorted(k for k in keys if k not in ALLOWED_STATE and k not in NUMERIC_STATE
                                  and pk(getattr(sa, k, None)) != pk(getattr(sb, k, None)))
    r['numeric_attr_diff'] = sorted(k for k in NUMERIC_STATE if not numeric_close(getattr(sa, k, None),
                                                                                    getattr(sb, k, None)))
    la, lb = sa.local_observation_summary, sb.local_observation_summary
    r['summary_new_keys'] = sorted(set(lb) - set(la))
    r['summary_missing_keys'] = sorted(set(la) - set(lb))
    r['summary_diff'] = sorted(k for k in set(la) & set(lb) if k not in ALLOWED_SUMMARY and pk(la[k]) != pk(lb[k]))
    da, db = la.get('projection_diagnostics', {}), lb.get('projection_diagnostics', {})
    r['diag_diff'] = sorted(k for k in set(da) & set(db) if pk(da[k]) != pk(db[k]))
    r['diag_new_keys'] = sorted(set(db) - set(da))
    r['diag_missing_keys'] = sorted(set(da) - set(db))
    step0 = b.step0()
    r['arrival_bad'], r['arrival_link_total_worst'], r['arrival_profile_delta'] = buffer_diff(
        sa.urban_arrival_buffer, sb.urban_arrival_buffer, step0)
    r['release_bad'], r['release_link_total_worst'], r['release_profile_delta'] = buffer_diff(
        sa.urban_storage_release_buffer, sb.urban_storage_release_buffer, step0)
    sda, sdb = la.get('urban_arrival_seed', {}), lb.get('urban_arrival_seed', {})
    r['seed_stats'] = [sda, sdb]
    r['seed_links_equal'] = sda.get('links') == sdb.get('links')
    r['seed_total_delta'] = ((sdb.get('moving_veh', 0.0) + sdb.get('stopped_veh', 0.0))
                             - (sda.get('moving_veh', 0.0) + sda.get('stopped_veh', 0.0)))
    r['seed_dropped_equal'] = sda.get('dropped_veh') == sdb.get('dropped_veh')
    r['movement_queue_equal'] = (pk(sa.urban_movement_queue) == pk(sb.urban_movement_queue)
                                 and pk(la.get('urban_movement_queue')) == pk(lb.get('urban_movement_queue')))
    r['storage_equal'] = (pk(sa.urban_link_storage) == pk(sb.urban_link_storage)
                          and pk(la.get('urban_link_storage_occupancy')) == pk(lb.get('urban_link_storage_occupancy')))
    r['speed_equal'] = (pk(sa.urban_link_speed_kph) == pk(sb.urban_link_speed_kph)
                        and pk(la.get('urban_link_speed_kph')) == pk(lb.get('urban_link_speed_kph')))
    r['ramp_equal'] = (pk(sa.ramp_queue) == pk(sb.ramp_queue)
                       and pk(getattr(sa, 'lane_ramp_runtime', None)) == pk(getattr(sb, 'lane_ramp_runtime', None)))
    r['template_key_diff'] = sorted(k for k in set(a.t) | set(b.t) if k != 'owned' and pk(a.t.get(k)) != pk(b.t.get(k)))
    r['owned_diff'] = [i for i in (0, 2, 3) if pk(a.t['owned'][i]) != pk(b.t['owned'][i])]
    r['stopped_total'] = [math.fsum(la['urban_link_storage_stopped'].values()),
                          math.fsum(lb['urban_link_storage_stopped'].values())]
    r['pass_c'] = (not r['state_attr_diff'] and not r['numeric_attr_diff'] and r['summary_new_keys'] == sorted(NEW_SUMMARY)
                   and not r['summary_missing_keys'] and not r['summary_diff'] and not r['diag_diff']
                   and r['diag_new_keys'] == sorted(NEW_DIAG) and not r['diag_missing_keys']
                   and not r['arrival_bad'] and not r['release_bad']
                   and r['arrival_link_total_worst'] <= TOL and r['release_link_total_worst'] <= TOL)
    r['pass_d'] = (r['seed_links_equal'] and abs(r['seed_total_delta']) <= TOL and r['seed_dropped_equal']
                   and r['arrival_link_total_worst'] <= TOL and r['movement_queue_equal'] and r['storage_equal']
                   and r['speed_equal'] and r['ramp_equal'])
    return r


def split_check(b):
    """Item (g) for one K8-4 capture: the split reproduces the seed recomputed from the summary."""
    s = b.summary
    d = s.get('projection_diagnostics', {})
    split = d.get('storage_seed_split_by_link')
    r = {'present': isinstance(split, dict)}
    if not r['present']:
        r['pass'] = False
        return r
    step0 = b.step0()
    t_u = float(b.cfg.simulation.T_u_sec)
    due_m = step0 + max(1, int(round(TAU_MOVING / t_u)))
    due_s = step0 + max(1, int(round(TAU_STOPPED / t_u)))
    unatt = split.get('unattributed', {})
    rows = {k: v for k, v in split.items() if k != 'unattributed'}
    occ = s.get('urban_link_storage_occupancy', {})
    stp = s.get('urban_link_storage_stopped', {})
    bad_rows, sums = [], {}
    for link, by_storage in rows.items():
        for storage, row in by_storage.items():
            m, st = row.get('moving'), row.get('stopped')
            ok = (isinstance(m, float) and isinstance(st, float) and math.isfinite(m) and math.isfinite(st)
                  and m >= 0.0 and st >= 0.0 and type(row.get('due_moving_step')) is int
                  and type(row.get('due_stopped_step')) is int
                  and row['due_moving_step'] == due_m and row['due_stopped_step'] == due_s)
            if not ok:
                bad_rows.append([link, storage, row])
            acc = sums.setdefault(storage, [[], []])
            acc[0].append(float(m or 0.0))
            acc[1].append(float(st or 0.0))
    worst, bad_storages = 0.0, []
    for storage in set(sums) | set(unatt):
        occupied = max(0.0, float(occ.get(storage, 0.0)))
        stopped = min(occupied, max(0.0, float(stp.get(storage, 0.0))))
        moving = max(0.0, occupied - stopped)
        u = unatt.get(storage, {})
        got_m = math.fsum(sums.get(storage, [[], []])[0] + [float(u.get('moving', 0.0))])
        got_s = math.fsum(sums.get(storage, [[], []])[1] + [float(u.get('stopped', 0.0))])
        e = max(abs(got_m - moving), abs(got_s - stopped))
        worst = max(worst, e)
        if e > TOL:
            bad_storages.append([storage, got_m, moving, got_s, stopped])
    gate_u = unatt.get(GATE_STORAGE, {})
    r.update(rows=sum(len(v) for v in rows.values()), storages=len(set(sums) | set(unatt)),
             seed_links=s.get('urban_arrival_seed', {}).get('links'), due=[due_m, due_s], bad_rows=bad_rows[:20],
             n_bad_rows=len(bad_rows), worst_residual=worst, bad_storages=bad_storages[:20],
             unattributed=unatt, unattributed_gate=gate_u,
             row_127=(rows.get(L127) or {}).get(GATE_STORAGE))
    r['pass'] = (not bad_rows and not bad_storages and r['storages'] == r['seed_links']
                 and abs(float(gate_u.get('moving', 0.0))) <= TOL and abs(float(gate_u.get('stopped', 0.0))) <= TOL)
    # report: rows vs projection provenance (may be rewritten later in setup, so not judged)
    prov = d.get('physical_stock_assignment_by_link') or {}
    mism = []
    for link, by_storage in rows.items():
        for storage, row in by_storage.items():
            p = (prov.get(link) or {}).get('storage:' + storage)
            if p is not None and abs(float(p) - row['moving'] - row['stopped']) > TOL:
                mism.append([link, storage, float(p), row['moving'] + row['stopped']])
    r['report_rows_vs_provenance_mismatch'] = mism[:20]
    r['report_rows_vs_provenance_n'] = len(mism)
    return r


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


def item_unit(logs):
    seen = unit_results(logs)
    rows, ok = [], True
    for cls, names in UNIT_TESTS.items():
        for name in names:
            node = f'{UNIT_FILE}::{cls}::{name}'
            states = set().union(*[s for k, s in seen.items() if k == node]) if node in seen else set()
            good = 'PASSED' in states and not (states & BAD_STATES)
            rows.append({'test': node, 'states': sorted(states), 'pass': good})
            ok &= good
    return {'pass': ok, 'rows': rows, 'logs': [str(x) for x in logs],
            'n_declared': sum(len(v) for v in UNIT_TESTS.values())}


def old_rule_127(a, b):
    """Item (b): K8-4 row 127 moving minus the K8-3 rule's moving for the same storage share."""
    la = a.summary
    row = b.summary['projection_diagnostics']['storage_seed_split_by_link'][L127][GATE_STORAGE]
    assigned = row['moving'] + row['stopped']
    count = float(la['link_counts'][L127])
    stopped_obs = float(la['link_stopped_counts'].get(L127, 0.0))
    old_stopped = assigned * min(1.0, max(0.0, stopped_obs / count))
    return {'row_127': row, 'assigned': assigned, 'count': count, 'observed_stopped': stopped_obs,
            'queue_k83': la['queue_count_by_link'][L127], 'queue_k84': b.summary['queue_count_by_link'][L127],
            'source_k84': b.summary['urban_queue_source_by_link'].get(L127),
            'old_moving': assigned - old_stopped, 'old_stopped': old_stopped,
            'share': row['moving'] - (assigned - old_stopped)}


def job(out, T, label):
    p = Path(out) / 'out' / f'{T:06d}' / 'jobs' / label / 'result.pickle'
    return pickle.loads(p.read_bytes()) if p.is_file() else {'error': f'missing {p}'}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True, help='K8-4 gate output root (gates_out/k84)')
    ap.add_argument('--unit-log', action='append', required=True)
    ap.add_argument('--json')
    ap.add_argument('--root', default=str(GATES.parents[2]), help='code root for unpickling (default: this worktree)')
    a = ap.parse_args()
    root = Path(a.root)
    sys.path[:0] = [str(root), str(root / 'vendor/NumSim-mine'), str(root / 'evaluation/controllers')]
    v = {'items': {}, 'report': {'per_state': {}}}
    items = v['items']
    per = v['report']['per_state']
    caps = {'k83': {}, 'k84': {}}
    cmp_rows, split_rows, viol = {}, {}, {}
    gate = {}
    for T in STATES:
        try:
            x, y = Arm(a.out, T, 'k83'), Arm(a.out, T, 'k84')
        except Exception:
            per[T] = {'load_exception': traceback.format_exc()[-2000:]}
            caps['k83'][T] = caps['k84'][T] = {'ok': False, 'why': 'load exception'}
            continue
        caps['k83'][T] = {k: x.status.get(k) for k in ('ok', 'why', 'error_last_line', 'template_sha256')}
        caps['k84'][T] = {k: y.status.get(k) for k in ('ok', 'why', 'error_last_line', 'template_sha256')}
        rec = {}
        if y.t is not None:
            d = y.summary.get('projection_diagnostics', {})
            viol[T] = [d.get('residual_stopped_ready_exceeds_stopped_links'),
                       d.get('residual_stopped_ready_exceeds_stopped_veh'), d.get('residual_stopped_split_links')]
            try:
                split_rows[T] = split_check(y)
            except Exception:
                split_rows[T] = {'pass': False, 'exception': traceback.format_exc()[-2000:]}
        else:
            proj = (y.status.get('record') or {}).get('projection') or {}
            rec['k84_failed_capture_projection_record'] = {k: proj.get(k) for k in (
                'S5_ready_exceeds_stopped_links', 'S5_ready_exceeds_stopped_veh', 'S5_shift_105_to_15_veh')}
        if x.t is not None and y.t is not None:
            try:
                cmp_rows[T] = compare(x, y)
            except Exception:
                cmp_rows[T] = {'pass_c': False, 'pass_d': False, 'exception': traceback.format_exc()[-2000:]}
            if T in SHIFT:
                gate[T] = (x, y)
            else:
                x.t = y.t = None
        rec['k84_projection_record'] = {k: ((y.status.get('record') or {}).get('projection') or {}).get(k) for k in (
            'S5_shift_105_to_15_veh', 'S5_links_changed', 'S5_shift_by_source', 'S5_ready_exceeds_stopped_links')}
        per[T] = rec

    # (a) and (b): the three declared states
    def item_a():
        out = {}
        ok = True
        for T, exp in SHIFT.items():
            if T not in gate:
                out[T] = {'pass': False, 'why': 'capture missing in an arm'}
                ok = False
                continue
            prof = cmp_rows[T]['arrival_profile_delta']
            p15, p105 = prof.get(15, 0.0), prof.get(105, 0.0)
            others = {k: d for k, d in prof.items() if k not in (15, 105) and abs(d) > TOL}
            good = abs(p15 - exp) <= TOL_SHIFT and abs(p105 + exp) <= TOL_SHIFT and not others
            out[T] = {'pass': good, 'declared': exp, 'plus15': p15, 'plus105': p105, 'other_offsets': others,
                      'release_plus15': cmp_rows[T]['release_profile_delta'].get(15, 0.0),
                      'release_plus105': cmp_rows[T]['release_profile_delta'].get(105, 0.0)}
            ok &= good
        out['pass'] = ok
        return out

    def item_b():
        out = {}
        ok = True
        for T, exp in SHARE_127.items():
            if T not in gate:
                out[T] = {'pass': False, 'why': 'capture missing in an arm'}
                ok = False
                continue
            r = old_rule_127(*gate[T])
            r['declared'] = exp
            r['pass'] = abs(r['share'] - exp) <= TOL_SHIFT and r['queue_k83'] == r['queue_k84']
            out[T] = r
            ok &= r['pass']
        out['pass'] = ok
        return out

    def item_c():
        bad = {T: {k: r.get(k) for k in ('state_attr_diff', 'numeric_attr_diff', 'summary_new_keys', 'summary_diff',
                                         'diag_diff', 'diag_new_keys', 'diag_missing_keys', 'arrival_bad',
                                         'release_bad', 'arrival_link_total_worst', 'release_link_total_worst',
                                         'exception')}
               for T, r in cmp_rows.items() if not r.get('pass_c')}
        return {'pass': bool(cmp_rows) and all(T in cmp_rows for T in SHIFT) and not bad,
                'states_compared': len(cmp_rows), 'failing_states': bad}

    def item_d():
        bad = {T: {k: r.get(k) for k in ('seed_links_equal', 'seed_total_delta', 'seed_dropped_equal',
                                         'arrival_link_total_worst', 'movement_queue_equal', 'storage_equal',
                                         'speed_equal', 'ramp_equal', 'exception')}
               for T, r in cmp_rows.items() if not r.get('pass_d')}
        worst = max((abs(r.get('seed_total_delta', 0.0)) for r in cmp_rows.values()), default=None)
        return {'pass': bool(cmp_rows) and all(T in cmp_rows for T in SHIFT) and not bad,
                'states_compared': len(cmp_rows), 'failing_states': bad, 'worst_seed_total_delta': worst}

    def item_e():
        ok84 = [T for T in STATES if caps['k84'][T]['ok']]
        ok83 = [T for T in STATES if caps['k83'][T]['ok']]
        fail84 = {T: caps['k84'][T] for T in STATES if not caps['k84'][T]['ok']}
        same = {T: (not caps['k83'][T]['ok'] and caps['k83'][T].get('error_last_line') == f.get('error_last_line'))
                for T, f in fail84.items()}
        return {'pass': len(ok84) == len(STATES), 'k84_success': len(ok84), 'declared': len(STATES),
                'k84_failures': fail84, 'report_k83_success': len(ok83),
                'report_k83_failures': {T: caps['k83'][T] for T in STATES if not caps['k83'][T]['ok']},
                'report_failure_identical_in_k83': same}

    def item_f():
        missing = [T for T in viol if not all(isinstance(z, float) and math.isfinite(z) for z in viol[T][:2])]
        three = {T: viol.get(T) for T in SHIFT}
        zero3 = all(T in viol and viol[T][0] == 0.0 and viol[T][1] == 0.0 for T in SHIFT)
        return {'pass': bool(viol) and not missing and zero3, 'recorded_states': len(viol), 'missing': missing,
                'declared_states': three, 'all_states': viol,
                'states_with_violations': {T: z for T, z in viol.items() if z[0]}}

    def item_g():
        bad = {T: r for T, r in split_rows.items() if not r.get('pass')}
        worst = max((r.get('worst_residual', 0.0) for r in split_rows.values()), default=None)
        return {'pass': bool(split_rows) and not bad, 'states_checked': len(split_rows), 'failing_states': bad,
                'worst_residual': worst,
                'rows_per_state': {T: r.get('rows') for T, r in split_rows.items()},
                'row_127_gate_states': {T: (split_rows.get(T) or {}).get('row_127') for T in SHIFT},
                'report_rows_vs_provenance_n': {T: r.get('report_rows_vs_provenance_n') for T, r in split_rows.items()},
                'unattributed_nonempty': {T: r['unattributed'] for T, r in split_rows.items() if r.get('unattributed')}}

    for name, fn in (('a_shift_105_to_15', item_a), ('b_link127_share', item_b), ('c_only_s5_fields', item_c),
                     ('d_unchanged_declared', item_d), ('e_capture_61', item_e), ('f_violation_counts', item_f),
                     ('g_split_assertion', item_g), ('h_unit_tests', lambda: item_unit(a.unit_log))):
        try:
            items[name] = fn()
        except Exception:
            items[name] = {'pass': False, 'exception': traceback.format_exc()[-3000:]}

    # reports
    try:
        rep = {}
        for T in SHIFT:
            x, y = job(a.out, T, 'k83_REF_scalar'), job(a.out, T, 'k84_REF_scalar')
            if x.get('error') or y.get('error'):
                rep[T] = {'error': [x.get('error'), y.get('error')]}
                continue
            order = y.get('costs_order') or x.get('costs_order')
            delta = {order[i]: q - p for i, (p, q) in enumerate(zip(x['costs'], y['costs'])) if q != p} if order else None
            rep[T] = {'objective': [repr(x['objective_veh_h']), repr(y['objective_veh_h'])],
                      'omega_delta': y['objective_veh_h'] - x['objective_veh_h'], 'owner_delta': delta,
                      'h3_declared_prototype': H3[T]}
        v['report']['reference_owner_cost_delta_b6_5'] = rep
    except Exception:
        v['report']['reference_owner_cost_delta_b6_5'] = {'exception': traceback.format_exc()[-2000:]}
    v['report']['template_level_diffs'] = {T: {'template_key_diff': r.get('template_key_diff'),
                                               'owned_diff': r.get('owned_diff')} for T, r in cmp_rows.items()}
    v['report']['stopped_total_k83_k84'] = {T: r.get('stopped_total') for T, r in cmp_rows.items()}
    v['report']['captures'] = caps
    v['pass'] = all(x['pass'] for x in items.values())
    text = json.dumps(v, indent=1, default=str)
    if a.json:
        Path(a.json).write_text(text, encoding='utf-8')
    print(json.dumps({k: x['pass'] for k, x in items.items()}), 'PASS' if v['pass'] else 'FAIL')
    return 0 if v['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
