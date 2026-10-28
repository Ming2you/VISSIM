# -*- coding: utf-8 -*-
"""Run checks V1 (completion), V2 (commands applied) and V3 (prefix equal to NC3 before 900 s) for the three v3c3
fixed VSL-only runs, exactly as defined in PRE_VSL.md section 6.2 (sha 27452ae6...). 2026-10-27 KST, vsl_v3c3.

Usage: python -B vsl_runcheck.py [<firstdiff_dir>]   -> VS/out/runcheck/runcheck.json (+ prints one line per seed)
Light: reads run.json, stdout.txt, fixed_readback.csv, fixed_validation.json, launcher end markers, and (if present)
firstdiff_s<S>.json written by vsl_firstdiff.py. Never opens an FZP. Writes only its output file.
Run pick = same rule as vsl_metrics.py / vsl_analysis_jobs.py: run_retry1 only if the launcher recorded run2 as done.
"""
import csv, json, os, re, sys

VS = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/vsl_v3c3'
RR = 'D:/VISSIM_runs/20261027_vsl_v3c3'
SEEDS = (31, 41, 43)
DSD = ('63', '64', '65', '66')
CLASSES = ('10', '20', '30', '70')
CMD_T, CMD_V, BEFORE_V, END_T = '900', '91', '110', '9000'


def jload(p):
    if not os.path.exists(p):
        return None
    with open(p, encoding='utf-8-sig') as f:
        return json.load(f)


def pick_run(s):
    e2 = jload(RR + '/_launcher/end_s%d_run2.json' % s)
    if e2 and e2.get('status') == 'done':
        return RR + '/s%d/run_retry1' % s, 'run_retry1'
    return RR + '/s%d/run' % s, 'run'


def v1(run):
    rj = jload(run + '/run.json')
    fv = jload(run + '/fixed_validation.json')
    out = os.path.join(run, 'stdout.txt')
    log = open(out, encoding='utf-8', errors='replace').read() if os.path.exists(out) else ''
    c = {
        'run_json': rj is not None,
        'completed_true': bool(rj) and rj.get('completed') is True,
        'exit_code_0': bool(rj) and rj.get('exit_code') == 0,
        'validation_exit_0': bool(rj) and rj.get('fixed_profile_validation_exit_code') == 0,
        'fixed_validation_passed': bool(fv) and fv.get('passed') is True,
        'stdout_SIM_DONE': re.search(r'(?m)^STAGE=SIM_DONE\r?$', log) is not None,
        'stdout_SIM_SEC_9000': re.search(r'(?m)^SIM_SEC=9000\r?$', log) is not None,
    }
    info = {}
    if rj:
        for k in ('started', 'finished', 'error', 'exit_code', 'fixed_profile_validation_exit_code', 'terminal_sec',
                  'owned_native_alive', 'vissim', 'cscript_pid', 'first_native_progress', 'last_native_progress', 'error_files',
                  'prepared_sha256', 'runner_sha256'):
            info[k] = rj.get(k)
        info['native_files'] = rj.get('native_files')
    if fv:
        info['fixed_validation'] = {k: fv.get(k) for k in ('passed', 'event_readbacks', 'snapshot_addresses',
                                                          'untargeted_snapshot_sha256_before', 'untargeted_snapshot_sha256_after',
                                                          'native_ldp_row_count', 'native_meter_samples_checked', 'error')}
    return all(c.values()), c, info


def v2(run):
    p = run + '/fixed_readback.csv'
    if not os.path.exists(p):
        return False, {'fixed_readback_csv': False}, {}
    with open(p, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    writes = [r for r in rows if r['phase'] == 'write']
    want = {(d, v) for d in DSD for v in CLASSES}
    got = [(r['time_s'], r['kind'], r['no'], r['veh_class'], r['expected'], r['actual'], r['ok']) for r in writes]
    exact = sorted(got) == sorted((CMD_T, 'vsl', d, v, CMD_V, CMD_V, '1') for d, v in want)
    meter_writes = sum(1 for r in writes if r['kind'] == 'meter')
    def snap(phase, t):
        return {(r['no'], r['veh_class']): r for r in rows if r['phase'] == phase and r['kind'] == 'vsl' and r['no'] in DSD}
    ini, fin = snap('initial', '0'), snap('final', END_T)
    c = {
        'fixed_readback_csv': True,
        'writes_exactly_16': len(writes) == 16,
        'writes_are_900_vsl_63to66_x4_91_ok': exact,
        'meter_writes_0': meter_writes == 0,
        'initial_63to66_eq_110': set(ini) == want and all(r['time_s'] == '0' and r['expected'] == r['actual'] == BEFORE_V and r['ok'] == '1' for r in ini.values()),
        'final_63to66_eq_91': set(fin) == want and all(r['time_s'] == END_T and r['expected'] == r['actual'] == CMD_V and r['ok'] == '1' for r in fin.values()),
    }
    info = {'readback_rows': len(rows), 'write_rows': len(writes), 'meter_write_rows': meter_writes,
            'phases': {ph: sum(1 for r in rows if r['phase'] == ph) for ph in ('initial', 'write', 'final')},
            'write_rows_list': [list(g) for g in sorted(got)]}
    return all(c.values()), c, info


def v3(fd_dir, s):
    fd = jload(os.path.join(fd_dir, 'firstdiff_s%d.json' % s)) if fd_dir else None
    if not fd:
        return None, {'firstdiff_json': False}, {}
    pre = fd['prefix_le_895_1']
    first = fd.get('first_diff')
    c = {'firstdiff_json': True, 'prefix_le_895_1_equal': pre['equal'] is True}
    info = {'prefix_rows_vsl': pre['rows_a'], 'prefix_rows_nc3': pre['rows_b'], 'prefix_sha_vsl': pre['sha_a'], 'prefix_sha_nc3': pre['sha_b'],
            'first_diff_time_vsl_s': first and first['time_a_s'], 'first_diff_time_nc3_s': first and first['time_b_s'],
            'first_diff_row_index': first and first['row_index'], 'frames_equal_before_s': fd.get('frames_equal_before_s'),
            'identical_files_data_rows': fd.get('identical_files_data_rows'), 'a': fd.get('a'), 'b': fd.get('b')}
    return all(c.values()), c, info


def main():
    fd_dir = sys.argv[1] if len(sys.argv) > 1 else None
    res = {'pre_vsl_sha256': '27452ae62ae84e7c1cbe4717f1c8777b3c18b5a3f5d18b7cd5da033d83a3faf1', 'firstdiff_dir': fd_dir, 'seeds': {}}
    for s in SEEDS:
        run, which = pick_run(s)
        ends = {a: jload(RR + '/_launcher/end_s%d_run%d.json' % (s, a)) for a in (1, 2)}
        ok1, c1, i1 = v1(run)
        ok2, c2, i2 = v2(run)
        ok3, c3, i3 = v3(fd_dir, s)
        fz = run + '/vissim_eval/baseline_s%d_v3c3vsl_001.fzp' % s
        res['seeds']['s%d' % s] = {'run': run, 'picked': which, 'launcher_end': {k: (v and v.get('status')) for k, v in ends.items()},
                                   'fzp': fz, 'fzp_bytes': os.path.getsize(fz) if os.path.exists(fz) else None,
                                   'V1_ok': ok1, 'V1': c1, 'V1_info': i1, 'V2_ok': ok2, 'V2': c2, 'V2_info': i2,
                                   'V3_ok': ok3, 'V3': c3, 'V3_info': i3}
        print('s%d' % s, which, 'V1', ok1, 'V2', ok2, 'V3', ok3, 'first_diff', i3.get('first_diff_time_vsl_s'))
    od = VS + '/out/runcheck'
    os.makedirs(od, exist_ok=True)
    with open(od + '/runcheck.json', 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    print(od + '/runcheck.json')


if __name__ == '__main__':
    main()
