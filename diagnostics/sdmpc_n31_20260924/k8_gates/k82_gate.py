"""K8-2 (S3) gate judge (K8-0b; diagnostics only, reads outputs, runs nothing).

    python -B k82_gate.py --out <gates_out/k82> --k7 <scratch k8 root> --unit-log <pytest log> [--json <verdict.json>]

Declared values: K8_PREDECLARATION_AMENDMENT_1.md (r2) §2 K8-2 row (a)-(f) and amendment 2; fixed here before any K8-2
gate run. Layout under --out (one output root for every code root, so replay paths are identical):
  out/<T>/jobs/k81_<A>_<mode>, k82_<A>_<mode>      s3run.py jobs, baseline (K8-1 runtime, anchors k81) / candidate (k82)
  out/2700/full_k81, full_ctrl, full_k82            s3run.py full decisions (ctrl = baseline + comment-only EOF lines in
                                                    the four edited files, anchors k81: isolates source-hash provenance)
  k81_table_s3.json, k82_table_s3.json              table_s3.py over (2700 REF ad, 2700 M2ALL ad, 4950 REF ad, 2700 full)
Judged items (all must pass):
  (a) scalar repr: objective repr = declared, costs/resources repr = K8-1 baseline, 1800/2700/4950 x REF/M2ALL
  (b) surrogate AD: cost 20x231 and resource 2x231 Jacobians bit-identical to the K8-1 baseline, objective repr =
      declared: 2700 REF, 2700 M2ALL, 4950 REF
  (c) S3 31-site table (reached / tape Dual / structural / exact != 0) = scratch table_s3.json (sha16 e5fd5195a084e698)
      in all four runs; structural = UFA:892 @ 4950 REF 28, else 0; exact != 0 all 0; no anchor mismatch / hook error
  (d) 2700 full deployed decision: progress objective / held repr = 498.5113776214157 / 501.1445316791073, action CSV
      sha16 f5ab5fa7fa0ef53c and bytes = baseline, action JSON = baseline outside V (S3_WIDE cmp_full timing-token keys)
      and rule 3 (run_provenance keys of amendment 1 §E rule 3, plus the source-hash provenance paths that differ in the
      control run)
  (e) unit tests: diagnostics/test_k8_s3_has_transfer.py passed (pytest log)
  (f) non-surrogate AD 2700 M2ALL: max_primal_state_error <= 1e-8 and complete_primal_state_match True
Reported (not judged): K7-scratch comparisons, owner accepted_event_count differences, trace event counts, baseline
table vs the scratch table (hook-port check), control-run hook table.
"""
import argparse
import hashlib
import json
import pickle
import re
from pathlib import Path

import numpy as np

SCALAR = {(1800, 'REF'): '470.0760810788538', (1800, 'M2ALL'): '476.34027641825486',
          (2700, 'REF'): '506.4944030335033', (2700, 'M2ALL'): '513.4991367407767',
          (4950, 'REF'): '381.6981739734223', (4950, 'M2ALL'): '386.2939267117166'}
AD = {(2700, 'REF'): '506.4944030335033', (2700, 'M2ALL'): '513.4991367407769', (4950, 'REF'): '381.6981739734223'}
FULL_OBJ, FULL_HELD = '498.5113776214157', '501.1445316791073'
CSV_SHA16 = 'f5ab5fa7fa0ef53c'
TABLE_SHA16 = 'e5fd5195a084e698'
STATE_ERROR_MAX = 1e-8
JUDGED_CELLS = ('reached', 'values_rdual', 'ev_struct', 'ev_exact_nonzero')
RUNS = ('2700 REF', '2700 M2ALL', '4950 REF', '2700 full')
TIMING = ('sec', 'wall', 'time', 'elapsed', 'started', 'finished', 'duration', 'pid', 'path', 'dir', 'tmp', 'created',
          'utc', 'stamp')   # S3_WIDE §3 cmp_full.py (amend1/s3/tools/cmp_full.py) volatile key tokens
RULE3 = (r'^/(metadata/)?run_provenance/(workspace_git_commit|execution_fingerprint_sha256)$',
         r'^/(metadata/)?run_provenance/imported_modules(/.*)?$',
         r'^/(metadata/)?run_provenance/inputs/[^/]+/sha256$')


def sha(p, n=64):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:n]


def load(p):
    return pickle.loads(Path(p).read_bytes())


def f(x):
    return float(getattr(x, 'value', x))


def jdiff(x, y, path, acc):
    if isinstance(x, dict) and isinstance(y, dict):
        for k in sorted(set(x) | set(y), key=str):
            p = path + '/' + str(k)
            if k not in x or k not in y:
                acc.append((p, 'presence', str(x.get(k))[:80], str(y.get(k))[:80]))
            else:
                jdiff(x[k], y[k], p, acc)
    elif isinstance(x, list) and isinstance(y, list):
        if len(x) != len(y):
            acc.append((path, 'length', len(x), len(y)))
        else:
            for i, (u, v) in enumerate(zip(x, y)):
                jdiff(u, v, path + f'[{i}]', acc)
    elif x != y or type(x) is not type(y):
        acc.append((path, 'value', str(x)[:80], str(y)[:80]))


def norm(p):
    return re.sub(r'\[\d+\]', '[]', p)


def in_v(p):
    return any(any(t in seg.lower() for t in TIMING) for seg in re.sub(r'\[\d+\]', '', p).split('/') if seg)


def in_rule3(p):
    return any(re.match(r, p) for r in RULE3)


def last_progress(d, T):
    rows = [json.loads(x) for x in (d / f'action_{T:06d}.joint.progress.jsonl').read_text(encoding='utf-8').splitlines()
            if x.strip()]
    for r in reversed(rows):
        if 'objective' in r or 'held_objective' in r:
            return repr(r.get('objective')), repr(r.get('held_objective'))
    return None, None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True)
    ap.add_argument('--k7', required=True, help='scratch k8 folder (out/<T>/jobs K7 results, amend1/s3/out/table_s3.json)')
    ap.add_argument('--unit-log', required=True)
    ap.add_argument('--json')
    a = ap.parse_args()
    O, K7 = Path(a.out) / 'out', Path(a.k7)
    v = {'items': {}, 'report': {}}

    # (a) scalar repr
    rows, ok = [], True
    for (T, A), want in SCALAR.items():
        base, cand = load(O / f'{T:06d}/jobs/k81_{A}_scalar/result.pickle'), load(O / f'{T:06d}/jobs/k82_{A}_scalar/result.pickle')
        k7 = K7 / f'out/{T:06d}/jobs/{A}_scalar/result.pickle'
        k7r = load(k7) if k7.is_file() else {}
        r = {'T': T, 'A': A, 'declared': want, 'cand': repr(cand.get('objective_veh_h')),
             'base': repr(base.get('objective_veh_h')),
             'costs_eq_base': [repr(x) for x in cand['costs']] == [repr(x) for x in base['costs']],
             'resources_eq_base': [repr(f(x)) for x in cand['resources']] == [repr(f(x)) for x in base['resources']],
             'errors': [cand.get('error'), base.get('error')],
             'k7_objective': repr(k7r.get('objective_veh_h')),
             'costs_eq_k7': [repr(x) for x in cand['costs']] == [repr(x) for x in k7r.get('costs', [])],
             'resources_eq_k7': ([repr(f(x)) for x in cand['resources']] == [repr(f(x)) for x in k7r.get('resources', [])]
                                 if 'resources' in k7r else None)}
        r['pass'] = (r['cand'] == want and r['costs_eq_base'] and r['resources_eq_base']
                     and not cand.get('error') and not base.get('error'))
        ok &= r['pass']
        rows.append(r)
    v['items']['a_scalar_repr'] = {'pass': ok, 'rows': rows}

    # (b) surrogate AD Jacobians
    rows, ok = [], True
    for (T, A), want in AD.items():
        base, cand = load(O / f'{T:06d}/jobs/k81_{A}_ad/result.pickle'), load(O / f'{T:06d}/jobs/k82_{A}_ad/result.pickle')
        k7p = K7 / f'out/{T:06d}/jobs/{A}_ad/result.pickle'
        k7r = load(k7p) if k7p.is_file() else None
        r = {'T': T, 'A': A, 'declared_objective': want, 'cand_objective': repr(cand.get('objective_veh_h')),
             'errors': [cand.get('error'), base.get('error')]}
        for k in ('cost_jacobian', 'resource_jacobian'):
            C, B = np.array(cand[k], dtype=np.float64), np.array(base[k], dtype=np.float64)
            r[k + '_shape'] = list(C.shape)
            r[k + '_bit_identical_base'] = C.shape == B.shape and C.tobytes() == B.tobytes()
            r[k + '_changed_cells_base'] = int((C != B).sum()) if C.shape == B.shape else None
            if k7r is not None:
                K = np.array(k7r[k], dtype=np.float64)
                r[k + '_bit_identical_k7'] = K.shape == C.shape and K.tobytes() == C.tobytes()
        r['costs_repr_eq_base'] = [repr(x) for x in cand['costs']] == [repr(x) for x in base['costs']]
        r['trace_event_counts_eq_base'] = (cand.get('trace') or {}).get('event_counts') == (base.get('trace') or {}).get('event_counts')
        r['trace_discrete_axes_eq_base'] = ((cand.get('trace') or {}).get('discrete_dependent_axes')
                                            == (base.get('trace') or {}).get('discrete_dependent_axes'))
        r['trace_tie_axes_eq_base'] = ((cand.get('trace') or {}).get('exact_tie_axes')
                                       == (base.get('trace') or {}).get('exact_tie_axes'))
        r['trace_nodes'] = [((x.get('trace') or {}).get('reverse_sweeps') or {}).get('nodes') for x in (cand, base)]
        r['kind_service_eq_base'] = cand.get('kind_service') == base.get('kind_service')
        r['kind_service_calls'] = [len(cand.get('kind_service') or []), len(base.get('kind_service') or [])]
        r['pass'] = (r['cand_objective'] == want and r['cost_jacobian_bit_identical_base']
                     and r['resource_jacobian_bit_identical_base'] and not cand.get('error') and not base.get('error'))
        ok &= r['pass']
        rows.append(r)
    v['items']['b_ad_jacobian'] = {'pass': ok, 'rows': rows}
    v['report']['accepted_event_count_diff_ad'] = {f"{r['T']} {r['A']}": (r['kind_service_eq_base'], r['kind_service_calls'])
                                                   for r in rows}

    # (c) S3 31-site table
    ref_path = K7 / 'amend1/s3/out/table_s3.json'
    ref = json.loads(ref_path.read_text(encoding='utf-8'))
    cand_t = json.loads((Path(a.out) / 'k82_table_s3.json').read_text(encoding='utf-8'))
    base_t = json.loads((Path(a.out) / 'k81_table_s3.json').read_text(encoding='utf-8'))
    cells, other, base_cells = [], [], []
    for site in sorted(set(ref['table']) | set(cand_t['table'])):
        for run in RUNS:
            R = ref['table'].get(site, {}).get(run, {})
            Cc = cand_t['table'].get(site, {}).get(run, {})
            Bb = base_t['table'].get(site, {}).get(run, {})
            for k in R.keys() | Cc.keys():
                (cells if k in JUDGED_CELLS else other).append((site, run, k, R.get(k, 0), Cc.get(k, 0))) \
                    if R.get(k, 0) != Cc.get(k, 0) else None
                if R.get(k, 0) != Bb.get(k, 0):
                    base_cells.append((site, run, k, R.get(k, 0), Bb.get(k, 0)))
    struct = {(s, r): cand_t['table'][s][r]['ev_struct'] for s in cand_t['table'] for r in RUNS
              if cand_t['table'][s].get(r, {}).get('ev_struct')}
    exact = {(s, r): cand_t['table'][s][r]['ev_exact_nonzero'] for s in cand_t['table'] for r in RUNS
             if cand_t['table'][s].get(r, {}).get('ev_exact_nonzero')}
    proc_issues = [(run, p.get('pid'), p.get('anchor_mismatch'), p.get('hook_errors'), p.get('errors'))
                   for run, procs in (cand_t.get('processes') or {}).items() for p in procs or []
                   if p.get('anchor_mismatch') or p.get('hook_errors') or p.get('errors')]
    c_pass = (sha(ref_path, 16) == TABLE_SHA16 and not cells and struct == {('UFA:892', '4950 REF'): 28}
              and not exact and not proc_issues and len(cand_t['table']) == 31)
    v['items']['c_hook_table'] = {'pass': c_pass, 'reference_sha16': sha(ref_path, 16), 'sites': len(cand_t['table']),
                                  'judged_cell_differences': cells, 'structural_nonzero': {f'{s} @ {r}': n for (s, r), n in struct.items()},
                                  'exact_nonzero': {f'{s} @ {r}': n for (s, r), n in exact.items()},
                                  'process_issues': proc_issues,
                                  'other_cell_differences': other[:60], 'n_other_cell_differences': len(other)}
    v['report']['baseline_table_vs_reference'] = {'n_differences': len(base_cells), 'first': base_cells[:40]}

    # (d) full deployed decision
    T = 2700
    fb, fc, fx = O / f'{T:06d}/full_k81', O / f'{T:06d}/full_k82', O / f'{T:06d}/full_ctrl'
    obj_c, obj_b, obj_x = last_progress(fc, T), last_progress(fb, T), last_progress(fx, T)
    csv_c, csv_b = (fc / f'action_{T:06d}.csv').read_bytes(), (fb / f'action_{T:06d}.csv').read_bytes()
    jb = json.loads((fb / f'action_{T:06d}.json').read_text(encoding='utf-8'))
    jc = json.loads((fc / f'action_{T:06d}.json').read_text(encoding='utf-8'))
    jx = json.loads((fx / f'action_{T:06d}.json').read_text(encoding='utf-8'))
    ctrl, cand = [], []
    jdiff(jb, jx, '', ctrl)
    jdiff(jb, jc, '', cand)
    ctrl_paths = {norm(p) for p, *_ in ctrl if not in_v(p)}
    outside, by_class = [], {'V': 0, 'rule3': 0, 'ctrl_provenance': 0}
    for p, kind, x, y in cand:
        if in_v(p):
            by_class['V'] += 1
        elif in_rule3(p):
            by_class['rule3'] += 1
        elif norm(p) in ctrl_paths:
            by_class['ctrl_provenance'] += 1
        else:
            outside.append((p, kind, x, y))
    d_pass = (obj_c == (FULL_OBJ, FULL_HELD) and hashlib.sha256(csv_c).hexdigest()[:16] == CSV_SHA16 and csv_c == csv_b
              and not outside)
    v['items']['d_full_decision'] = {
        'pass': d_pass, 'progress_cand': obj_c, 'progress_base': obj_b, 'progress_ctrl': obj_x,
        'csv_sha16': [hashlib.sha256(csv_c).hexdigest()[:16], hashlib.sha256(csv_b).hexdigest()[:16]],
        'csv_bytes_equal_base': csv_c == csv_b,
        'metadata_held_objective': [repr((x.get('metadata', {}).get('joint_leader_selection') or {}).get('held_objective'))
                                    for x in (jc, jb)],
        'json_diff_paths_total': len(cand), 'json_diff_by_class': by_class, 'json_diff_outside_allowed': outside[:60],
        'n_outside_allowed': len(outside),
        'ctrl_provenance_paths': sorted(ctrl_paths), 'ctrl_vs_base_paths_total': len(ctrl),
        'ctrl_csv_equal_base': (fx / f'action_{T:06d}.csv').read_bytes() == csv_b}

    # (e) unit tests
    log = Path(a.unit_log).read_text(encoding='utf-8', errors='replace')
    m = re.findall(r'=+ (.*?) in [\d.]+s', log)
    tail = m[-1] if m else ''
    e_pass = bool(re.search(r'\b\d+ passed\b', tail)) and not re.search(r'failed|error', tail)
    v['items']['e_unit_tests'] = {'pass': e_pass, 'summary': tail, 'log': str(a.unit_log)}

    # (f) non-surrogate AD
    rp = O / f'{T:06d}/jobs/k82_M2ALL_adfull/result.pickle'
    r = load(rp)
    err = r.get('max_primal_state_error')
    f_pass = (not r.get('error') and err is not None and err <= STATE_ERROR_MAX
              and r.get('complete_primal_state_match') is True)
    v['items']['f_nonsurrogate_ad'] = {'pass': f_pass, 'max_primal_state_error': err,
                                       'complete_primal_state_match': r.get('complete_primal_state_match'),
                                       'result_pickle': str(rp), 'result_pickle_sha256': sha(rp),
                                       'resources': [f(x) for x in r.get('resources') or []],
                                       'error': (r.get('error') or '')[-800:]}
    bp = O / f'{T:06d}/jobs/k81_M2ALL_adfull/result.pickle'
    if bp.is_file():
        b = load(bp)
        v['report']['adfull_vs_baseline'] = {
            k + '_bit_identical': (np.array(r[k]).tobytes() == np.array(b[k]).tobytes()) for k in ('cost_jacobian', 'resource_jacobian')}
        v['report']['adfull_vs_baseline']['baseline_state_error'] = b.get('max_primal_state_error')
        v['report']['adfull_vs_baseline']['resources_repr_equal'] = ([repr(f(x)) for x in r['resources']]
                                                                    == [repr(f(x)) for x in b['resources']])
    v['pass'] = all(x['pass'] for x in v['items'].values())
    text = json.dumps(v, indent=1, default=str)
    if a.json:
        Path(a.json).write_text(text, encoding='utf-8')
    print(json.dumps({k: x['pass'] for k, x in v['items'].items()}), 'PASS' if v['pass'] else 'FAIL')
    return 0 if v['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
