# A0b summary over all replayed T (read-only). Inputs per T: replay_state.json, compare_vs_recorded.json (s13_compare.py),
# rows_vs_recorded.json (a0b_rows.py), decision_budget/joint/progress files of replay and record, codex runlog, cpu_load.csv.
# usage: a0b_summary.py out.json [label] [T,T,...] [rows_json_dir]   (default label a0b_hsw, T list below, rows in out/<label>/T<T>/)
import csv, json, os, re, statistics, sys
LABEL = sys.argv[2] if len(sys.argv) > 2 else 'a0b_hsw'
TS = [int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else [1050, 1200, 1350, 1500, 1650, 1800, 1950, 2100, 2250, 2400, 2550]
ROWSDIR = sys.argv[4] if len(sys.argv) > 4 else None
A0 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0'
DEC = 'decisions_sdmpc31_sdmpc8100_s29'
REC = 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/' + DEC
RUNLOG = 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/runlog_sdmpc31_sdmpc8100_s29.txt'
CLOCK = re.compile(r'(?i)(^elapsed_sec$|^seconds$|_sec$)')   # same as work/a0/s29_progress_diff.py
PAT = re.compile(r'^CONTROLLER_DECISION sim_sec=(\d+) wall_sec=([0-9.]+) result=exit=(-?\d+)')


def load(p):
    return json.loads(open(p, 'rb').read().decode('utf-8-sig'))


def plines(d, T):
    p = d + '/action_%06d.joint.progress.jsonl' % T
    return [json.loads(l) for l in open(p, encoding='utf-8')] if os.path.exists(p) else None


def strip(x):
    if isinstance(x, dict):
        return {k: strip(v) for k, v in x.items() if not CLOCK.search(k)}
    if isinstance(x, list):
        return [strip(v) for v in x]
    return x


def first_diff(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        sx, sy = strip(x), strip(y)
        if sx != sy:
            keys = sorted(k for k in set(sx) | set(sy) if sx.get(k) != sy.get(k))
            return {'index0': i, 'line1': i + 1, 'stage': x.get('stage'), 'ref_stage': y.get('stage'),
                    'fields': {k: [repr(sx.get(k))[:100], repr(sy.get(k))[:100]] for k in keys[:6]}}
    if len(a) != len(b):
        return {'index0': min(len(a), len(b)), 'line1': min(len(a), len(b)) + 1, 'stage': 'length', 'lengths': [len(a), len(b)]}
    return None


def work(d, T):
    try:
        j = load(d + '/action_%06d.joint.json' % T)
    except FileNotFoundError:
        return None
    prc = j.get('physical_response_cache', {}) or {}
    sel = j.get('selection', {}) or {}
    return {k: prc.get(k) for k in ('requests', 'cache_hits', 'scalar_rollouts', 'tangent_rollouts', 'total_rollouts')} | {
        'cache_rows': len(prc.get('rows', []) or []), 'tangent_derivatives': len(sel.get('tangent_derivatives', []) or [])}


def cpu_mean(p):
    vals = []
    if not os.path.exists(p):
        return None
    for i, row in enumerate(csv.reader(open(p, encoding='utf-8', errors='replace'))):
        if i == 0 or len(row) < 2:
            continue
        try:
            vals.append(float(row[1]))
        except ValueError:
            pass
    return {'samples': len(vals), 'mean_pct': round(statistics.mean(vals), 1) if vals else None}


runlog = {}
for line in open(RUNLOG, encoding='utf-8', errors='replace'):
    m = PAT.match(line)
    if m:
        runlog[int(m.group(1))] = {'wall_sec': float(m.group(2)), 'exit': int(m.group(3))}
held = [l.strip()[:160] for l in open(RUNLOG, encoding='utf-8', errors='replace') if l.startswith('DECISION_HELD_PREVIOUS')]
out = {'label': LABEL, 'Ts': TS, 'per_T': [], 'codex_held_lines': held}
for T in TS:
    t6 = '%06d' % T
    od = A0 + '/out/' + LABEL + '/T' + t6
    fd = od + '/files/sdmpc/' + DEC
    r = {'T': T}
    try:
        st = load(od + '/replay_state.json')
        r['replay'] = {k: st.get(k) for k in ('exit_code', 'wall_sec', 'start', 'end', 'priority', 'status', 'collect_exit')}
        r['replay_env_hsw_vars'] = {k: st.get('env', {}).get(k) for k in ('OPENBLAS_CORETYPE', 'NPY_DISABLE_CPU_FEATURES', 'NUMBA_CPU_NAME', 'PYTHONHASHSEED')}
    except FileNotFoundError:
        r['replay'] = None
        out['per_T'].append(r); continue
    try:
        c = load(od + '/compare_vs_recorded.json')
        r['R1_equal'], r['R2_equal'], r['R3_equal'] = c['R1_equal'], c['R2_equal'], c['R3_equal']
        r['R1_csv_sha'] = c['R1_csv_sha']
        r['R2_fields_equal'] = {k: v[2] for k, v in c['R2'].items()}
        r['R3_token'] = c['R3_token']
        r['R4'] = {n: {k: v for k, v in s.items() if k != 'examples'} for n, s in c['R4'].items()}
        r['R4_diff_other_examples'] = {n: s.get('examples', {}).get('diff_other', [])[:5] for n, s in c['R4'].items()}
    except FileNotFoundError:
        r['compare'] = 'missing'
    try:
        rows = load((ROWSDIR + '/rows_%s_%s.json' % (LABEL, t6)) if ROWSDIR else (od + '/rows_vs_recorded.json'))
        r['rows'] = {k: rows[k] for k in ('rows_replay', 'rows_record', 'header_equal', 'n_differing_rows', 'differing_rows_by_kind',
                                          'max_abs_delta_by_kind_col', 'signal_green_diff_ge_1s', 'ramp_meter_rate_or_green_diff',
                                          'vsl_speed_diff', 'nonnumeric_diffs', 'sc_with_diff', 'ids_with_diff_nonsignal')}
        r['rows']['identity_mismatch'] = len(rows['identity_mismatch'])
    except FileNotFoundError:
        r['rows'] = 'missing'
    try:
        rb, cb = load(fd + '/action_%s.decision_budget.json' % t6), load(REC + '/action_%s.decision_budget.json' % t6)
        r['budget_wall_sec'] = {'replay': rb.get('wall_sec'), 'codex': cb.get('wall_sec')}
        r['budget_cpu_sec'] = {'replay': rb.get('cpu_sec'), 'codex': cb.get('cpu_sec')}
        if rb.get('wall_sec') and cb.get('wall_sec'):
            r['ratio_budget_wall'] = round(rb['wall_sec'] / cb['wall_sec'], 3)
    except FileNotFoundError:
        r['budget_wall_sec'] = None
    r['codex_runlog'] = runlog.get(T)
    if r['replay'] and r['replay'].get('wall_sec') and runlog.get(T):
        r['ratio_process_wall_vs_runlog'] = round(r['replay']['wall_sec'] / runlog[T]['wall_sec'], 3)
    r['work'] = {'replay': work(fd, T), 'codex': work(REC, T)}
    r['work_equal'] = r['work']['replay'] == r['work']['codex'] if r['work']['replay'] else None
    pa, pb = plines(fd, T), plines(REC, T)
    r['progress_lines'] = [len(pa) if pa else None, len(pb) if pb else None]
    r['progress_first_diff'] = first_diff(pa, pb) if pa and pb else 'missing'
    r['cpu_load'] = cpu_mean(od + '/cpu_load.csv')
    out['per_T'].append(r)
done = [r for r in out['per_T'] if r.get('replay') and r['replay'].get('exit_code') == 0]
out['n_replayed_exit0'] = len(done)
out['first_T_R1_differs'] = next((r['T'] for r in out['per_T'] if r.get('R1_equal') is False), None)
out['first_T_rows_differ'] = next((r['T'] for r in out['per_T'] if isinstance(r.get('rows'), dict) and r['rows']['n_differing_rows'] > 0), None)
out['T_R1_equal'] = [r['T'] for r in out['per_T'] if r.get('R1_equal') is True]
w = [(r['budget_wall_sec']['replay'], r['budget_wall_sec']['codex']) for r in done if r.get('budget_wall_sec')]
if w:
    out['wall_totals'] = {'replay_budget_sum': round(sum(a for a, _ in w), 1), 'codex_budget_sum': round(sum(b for _, b in w), 1),
                          'ratio_of_sums': round(sum(a for a, _ in w) / sum(b for _, b in w), 3),
                          'ratio_min': round(min(a / b for a, b in w), 3), 'ratio_max': round(max(a / b for a, b in w), 3),
                          'replay_max': round(max(a for a, _ in w), 1)}
json.dump(out, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for r in out['per_T']:
    rows = r.get('rows') if isinstance(r.get('rows'), dict) else {}
    print(r['T'], 'exit', (r.get('replay') or {}).get('exit_code'), 'R1', r.get('R1_equal'), 'R2', r.get('R2_equal'), 'R3', r.get('R3_equal'),
          'rows', rows.get('n_differing_rows'), rows.get('differing_rows_by_kind'), 'wall', r.get('budget_wall_sec'), 'ratio', r.get('ratio_budget_wall'),
          'work_eq', r.get('work_equal'), 'pfd', (r.get('progress_first_diff') or {}).get('line1') if isinstance(r.get('progress_first_diff'), dict) else r.get('progress_first_diff'))
print('first_T_R1_differs', out['first_T_R1_differs'], 'first_T_rows_differ', out['first_T_rows_differ'], 'totals', out.get('wall_totals'))
