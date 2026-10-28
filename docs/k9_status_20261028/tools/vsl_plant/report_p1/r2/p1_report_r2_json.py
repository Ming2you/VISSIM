"""One-off read-only collector for P1_REPORT r2 (not a tool of the run; reads outputs only, writes one JSON).

    python -B p1_report_r2_json.py <out.json>

Reads: GT/out/tables/vp_tables_p1r3.json (fixed tool vp_analyze.py a3638816..., L3), each GT/out/plant_P/<state>/
probe.json / jobcheck.json / job_summary.json, logs/plantP/queue.log, the interrupted r2 job record.  Applies only the
fixed rules of PRE_VP_FIXED 5.4 (pointing rule, R <= -0.2 wording, bands) and PRE_VP_R3 1.1 (reading of the R1
bit-report entries) to numbers the fixed tool already computed.  Everything after the run is labelled data_after."""
import hashlib
import json
import math
import re
import statistics
import sys
from pathlib import Path

sys.dont_write_bytecode = True
VP = Path(r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/'
          r'491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/vsl_plant')
GT = Path(r'D:/VISSIM-merge/k8_gate_trees/vsl_plant')
TABLES = GT / 'out' / 'tables' / 'vp_tables_p1r3.json'
TABLES_MD = GT / 'out' / 'tables' / 'vp_tables_p1r3.md'
METRICS = ['m1_VSa_speed', 'm2_M1_speed', 'm3_VSb_stock', 'm4_VSb_speed', "m5_VS0'_speed"]
METRIC_ZONE = {'m1_VSa_speed': ('VSa', 'speed'), 'm2_M1_speed': ('M1', 'speed'), 'm3_VSb_stock': ('VSb', 'stock'),
               'm4_VSb_speed': ('VSb', 'speed'), "m5_VS0'_speed": ("VS0'", 'speed')}
ABL = ['C1_vfree', 'C2_rhocrit', 'C3_merge', 'C4_lanedrop', 'C5_capdrop', 'C6_compliance', 'C7_initial',
       'C8_antic18', 'C9_lanedrop_both']


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def rj(p):
    with open(p, 'r', encoding='utf-8-sig') as f:
        return json.load(f)


def queue_times():
    """JOB_BEGIN / JOB_END / LOCK lines of the r3 queue run (pid of the QUEUE_START after 18:24)."""
    lines = (VP / 'logs' / 'plantP' / 'queue.log').read_text(encoding='utf-8').splitlines()
    start = max(i for i, l in enumerate(lines) if 'QUEUE_START' in l)
    out, waits = {}, {}
    for l in lines[start:]:
        m = re.match(r'^(\S+ \S+) KST \[pid=(\d+)\] (\S+) (.*)$', l)
        if not m:
            continue
        t, ev, rest = m.group(1), m.group(3), m.group(4)
        if ev == 'LOCK_ACQUIRED':
            tag = rest.split('plantP/')[1].split()[0]
            waits[tag] = int(re.search(r'waited_sec=(\d+)', rest).group(1))
        if ev in ('JOB_BEGIN', 'JOB_END', 'JOBCHECK'):
            tag = rest.split()[0]
            d = out.setdefault(tag, {})
            if ev == 'JOB_BEGIN':
                d['lock_begin_kst'] = t
            elif ev == 'JOB_END':
                d['lock_end_kst'] = t
                d['exit'] = int(re.search(r'exit=(-?\d+)', rest).group(1))
                d['sec'] = int(re.search(r'sec=(\d+)', rest).group(1))
            else:
                d['jobcheck_exit'] = int(re.search(r'exit=(-?\d+)', rest).group(1))
    for k, v in waits.items():
        out.setdefault(k, {})['lock_wait_sec'] = v
    return {'queue_log_sha256': sha(VP / 'logs' / 'plantP' / 'queue.log'), 'queue_start_line': lines[start][:200],
            'queue_end_present': any('QUEUE_END' in l for l in lines[start:]), 'jobs': out}


def main():
    out_path = Path(sys.argv[1])
    tab = rj(TABLES)
    p1 = tab['P1']
    qt = queue_times()
    jobs = []
    for st in p1['states']:
        jd = GT / 'out' / 'plant_P' / st['job']
        probe = rj(jd / 'probe.json')
        jc = rj(jd / 'jobcheck.json')
        js = rj(jd / 'job_summary.json')
        ck = probe.get('checks') or {}
        tag = 'P_' + st['job']
        jobs.append({
            'job': st['job'], 'label': st['label'], 'T': st['T'], 'queue': qt['jobs'].get(tag),
            'probe_exit': js.get('exit_code'), 'wall_sec': js.get('wall_sec'), 'killed': js.get('killed'),
            'stop': probe.get('stop'), 'errors': probe.get('errors'),
            'jobcheck_hits': jc.get('hits'), 'jobcheck_r1_rule': jc.get('r1_rule'), 'r1_objective_ok': jc.get('r1_objective_ok'),
            'checks': {k: ck.get(k) for k in ('R0_rec_token_equals_recorded', 'R1_objective_bit_equal', 'R1_objective_diff',
                                              'R1_objective_within_1e-9', 'R1_costs_same_keys', 'R1_costs_max_abs_diff',
                                              'R1_costs_within_1e-9', 'R2_minus_R1', 'R3_repack_bit_equal', 'null_bit_equal')},
            'r1_objective_ulp': (ck.get('R1_objective_diff') / math.ulp(probe['evaluations']['R1_REC_ad']['objective_veh_h'])
                                 if isinstance(ck.get('R1_objective_diff'), float) else None),
            'repack_token_equals_rec': (probe.get('plans') or {}).get('REPACK', {}).get('token') == (probe.get('plans') or {}).get('REC', {}).get('token'),
            'policy_sha256': probe.get('policy_sha256'), 'price_receipt_committed': probe.get('price_receipt_committed'),
            'hook_files': js.get('hook_files'), 'action_written': js.get('action_written'),
            'spec_sha256': js.get('spec_sha256'), 'probe_tool_sha256': js.get('probe_sha256'), 'hook_tool_sha256': js.get('hook_sha256'),
            'tree_freeze_sha': js.get('tree_freeze_sha'),
            'probe_json_sha256': sha(jd / 'probe.json'), 'jobcheck_json_sha256': sha(jd / 'jobcheck.json'),
            'job_summary_sha256': sha(jd / 'job_summary.json'),
            'J_EXEC_scalar_veh_h': probe['evaluations']['EXEC_scalar']['objective_veh_h'],
        })
    # r3 reading of the tables' stop list (PRE_VP_R3 1.1)
    by_job = {j['job']: j for j in jobs}
    stops_read = []
    for s in p1['stops']:
        j = by_job.get(s.get('job'))
        if s.get('check') == 'R1_objective_bit_equal' and j and not j['jobcheck_hits'] and j['r1_objective_ok'] is True:
            stops_read.append(dict(s, r3_reading='R1 bit report (no S-R1 in jobcheck, r1_objective_ok true; PRE_VP_R3 1.1)',
                                   R1_objective_diff=j['checks']['R1_objective_diff']))
        else:
            stops_read.append(dict(s, r3_reading='stop-rule hit'))
    # per state tables (numbers the fixed tool computed)
    states = []
    for st in p1['states']:
        z450, z0 = st['base']['w450']['zones'], st['base']['b0']['zones']
        row = {'job': st['job'], 'label': st['label'], 'T': st['T'],
               'base_bias_w450': {m: z450[METRIC_ZONE[m][0]]['e'][METRIC_ZONE[m][1]] for m in METRICS},
               'base_bias_b0': {m: z0[METRIC_ZONE[m][0]]['e'][METRIC_ZONE[m][1]] for m in METRICS},
               'plant_w450': {m: z450[METRIC_ZONE[m][0]]['plant'][METRIC_ZONE[m][1]] for m in METRICS},
               'vissim_w450': {m: z450[METRIC_ZONE[m][0]]['vissim'][METRIC_ZONE[m][1]] for m in METRICS},
               'initial_bias': (st.get('initial_bias') or {}).get('zones'),
               'exits_base': st.get('exits_base'), 'ablations': {}}
        for a in ['null'] + ABL:
            ab = (st.get('ablations') or {}).get(a)
            if not ab:
                row['ablations'][a] = None
                continue
            row['ablations'][a] = {'reach_ok': ab['reach_ok'], 'bit_identical_to_base': ab['bit_identical_to_base'],
                                   'dJ_vs_base': ab['dJ_vs_base'],
                                   'R': {m: ab['metrics'][m]['R'] for m in METRICS},
                                   'e_ablated': {m: ab['metrics'][m]['e_ablated'] for m in METRICS},
                                   'exits_blocked': ((ab.get('exits') or {}).get('blocked_veh')),
                                   'exits_veh': ((ab.get('exits') or {}).get('exit_veh'))}
        states.append(row)
    # fixed-rule readings (PRE_VP_FIXED 5.4) of the tool summary
    summ = p1['summary']
    db = tab.get('P1_direction') or {}
    readings = []
    for a in ABL:
        for m in METRICS:
            v = summ[a][m]
            label = None
            if v['points_to_term']:
                label = ('×1.2 민감도 규칙 충족' if a == 'C2_rhocrit' else '%s 가 %s 편향을 가리킴' % (a, m))
            elif v['median_R'] is not None and v['median_R'] <= -0.2:
                label = '%s 를 빼면 %s 편향이 커짐' % (a, m)
            if label is None:
                continue
            dirnote = None
            d = db.get(m) or {}
            if v['points_to_term'] and a == 'C1_vfree':
                g = d.get('C1_fd_minus_vissim_low_speed_mean')
                dirnote = {'C1_fd_minus_vissim_low_speed_mean': g, 'C1_cells': d.get('C1_cells'),
                           'literal_rule_label': '방향 근거 없음' if (g is not None and g > 0) else None}
            if v['points_to_term'] and a == 'C2_rhocrit':
                dirnote = {'C2_basis': d.get('C2_basis'), 'literal_rule_label': None if d.get('C2_basis') else '방향 근거 없음'}
            readings.append({'candidate': a, 'metric': m, 'label': label, 'median_R': v['median_R'], 'band': v['band'],
                             'n_defined': v['n_defined'], 'n_R_ge_0.5': v['n_R_ge_0.5'], 'n_R_le_-0.2': v['n_R_le_-0.2'],
                             'direction': dirnote})
    pointed = {m: [a for a in ABL if summ[a][m]['points_to_term']] for m in METRICS}
    not_pointed = [m for m in METRICS if not pointed[m]]
    x1 = tab.get('P1_X1')
    # data after: J differences of the ablations vs base (deployed objective, veh*h / 450 s)
    dj = {}
    for a in ['null'] + ABL:
        vals = [s['ablations'][a]['dJ_vs_base'] for s in states if s['ablations'].get(a)]
        dj[a] = {'n': len(vals), 'median': statistics.median(vals) if vals else None,
                 'min': min(vals) if vals else None, 'max': max(vals) if vals else None}
    # C1 changed cells and their direction (data-after reading aid)
    pp = tab.get('P1_params') or {}
    c1_cells = {i: {'v_free': c.get('v_free'), 'C1_replacement_v_free': c.get('C1_replacement_v_free'),
                    'plant_fd_speed_at_k_med': c.get('plant_fd_speed_at_k_med'), 'vissim_s_med': c.get('vissim_s_med'),
                    'vissim_k_med': c.get('vissim_k_med')}
                for i, c in (pp.get('cells') or {}).items() if c.get('C1_replacement_v_free') is not None}
    interrupted = GT / 'out' / 'interrupted' / 'plant_P' / 'v3c3-s31_T001800_interrupted_r2stop_20261027_182035'
    rec = {
        'schema': 'vp-p1-report/2', 'revision': 'r2 (after D-K9-108/109 and PRE_VP_R3)',
        'pre': {'PRE_VP_FIXED_sha256': sha(VP / 'PRE_VP_FIXED.md'), 'PRE_VP_R3_sha256': sha(VP / 'PRE_VP_R3.md'),
                'notes_sha256': sha(VP.parent / 'K9_1_J1_NOTES_20261013.md')},
        'tables': {'json_sha256': sha(TABLES), 'md_sha256': sha(TABLES_MD), 'tool': 'vp_analyze.py tables',
                   'tool_sha256': sha(VP / 'tools' / 'vp_analyze.py')},
        'queue': qt, 'jobs': jobs, 'stops_from_tables': stops_read,
        'summary_from_tool': summ, 'direction_basis_from_tool': db, 'x1_summary_from_tool': x1,
        'p1_params_scalars_from_tool': pp.get('scalars'), 'p1_params_from_state': pp.get('from_state'),
        'c1_changed_cells_from_tool': c1_cells,
        'fixed_rule_readings': readings, 'pointed_by_metric': pointed, 'metrics_not_pointed': not_pointed,
        'states': states,
        'data_after': {'dJ_ablation_minus_base_veh_h': dj},
        'interrupted_r2': {'folder_present': interrupted.is_dir(),
                           'probe_json_sha256': sha(interrupted / 'probe.json') if (interrupted / 'probe.json').is_file() else None,
                           'r1_objective_diff_r2': (rj(interrupted / 'probe.json').get('checks') or {}).get('R1_objective_diff')
                           if (interrupted / 'probe.json').is_file() else None},
    }
    tmp = out_path.with_name(out_path.name + '.tmp%d' % __import__('os').getpid())
    tmp.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding='utf-8')
    tmp.replace(out_path)
    print('P1_REPORT json: states %d jobs %d readings %d not_pointed %s' % (len(states), len(jobs), len(readings), not_pointed))


if __name__ == '__main__':
    main()
