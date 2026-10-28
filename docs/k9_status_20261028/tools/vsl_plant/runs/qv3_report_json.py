"""Write QV3_REPORT.json (mechanical; reads finished outputs only).  python -B qv3_report_json.py"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import vp_common as C  # noqa: E402

VP = C.VP
OUT = C.OUT


def sha(p):
    p = Path(p)
    return C.sha256_file(p) if p.is_file() else None


def main():
    col = C.read_json(VP / 'runs' / 'qv3_collect.json')
    tabs = C.read_json(OUT / 'tables' / 'vp_tables_qv3_stop.json')
    p1dir = OUT / 'plant_P' / 'v3c3-s31_T001800'
    p1 = C.read_json(p1dir / 'probe.json') or {}
    st_path = VP / 'selftest' / 'selftest_qv3_run_741546.json'
    res = {
        'schema': 'qv3-report/1', 'made_kst': C.kst(), 'status': 'STOP',
        'basis': {'PRE_VP_FIXED.md': sha(VP / 'PRE_VP_FIXED.md'), 'decision': 'D-K9-103 Q-V3',
                  'K9_1_J1_NOTES_first_344_lines': 'b33fe5e79c60fa499cce17a41bc18d24b1de33773226d8e80600a7c9bc8f5f89'},
        'report_md_sha256': sha(VP / 'QV3_REPORT.md'),
        'stop': {'rule': 'S-R1 (PRE_VP_FIXED 3.4, 7)', 'by_job': 'P_v3c3-s31_T001800 (P1 run, queue pid 35444)',
                 'STOP_VP': C.read_json(VP / 'STOP_VP'), 'STOP_VP_sha256': sha(VP / 'STOP_VP'),
                 'p1_probe_sha256': sha(p1dir / 'probe.json'), 'p1_jobcheck_sha256': sha(p1dir / 'jobcheck.json'),
                 'p1_checks': p1.get('checks'),
                 'p1_recorded_selected_objective': (p1.get('recorded') or {}).get('selected_objective'),
                 'p1_R1_objective': ((p1.get('evaluations') or {}).get('R1_REC_ad') or {}).get('objective_veh_h'),
                 'our_queue': {'log_sha256': sha(VP / 'logs' / 'plantA' / 'queue.log'),
                               'stop_vp_written_kst': '2026-10-27 17:49:46',
                               'A2_job_lock_acquired_kst': '2026-10-27 17:50:05',
                               'A2_job_end_kst': '2026-10-27 17:54:28', 'queue_stop_kst': '2026-10-27 17:54:29',
                               'gap': 'vp_queue.py checks STOP_VP before lock_acquire (:38) only, not after (:47)'}},
        'steps': {
            'L0': {'kst': '2026-10-27 17:31', 'pins_VP': '39/39', 'pins_EXT': '15/15',
                   'SHA256SUMS_VP.txt': sha(VP / 'SHA256SUMS_VP.txt'),
                   'SHA256SUMS_VP_EXT.txt': sha(VP / 'SHA256SUMS_VP_EXT.txt'),
                   'selftest': {'file': 'selftest/selftest_qv3_run_741546.json', 'sha256': sha(st_path),
                                'n_ok': (C.read_json(st_path) or {}).get('n_ok'), 'n': (C.read_json(st_path) or {}).get('n')}},
            'H0': {'jobs': 'runs/jobs_qv3_h0.json', 'jobs_sha256': sha(VP / 'runs' / 'jobs_qv3_h0.json'),
                   'kst': '17:32:18-17:32:39', 'wmi_pid': 4140, 'tree': C.read_json(str(C.CODE) + '.tree.json'),
                   'tree_record_sha256': sha(str(C.CODE) + '.tree.json'),
                   'note': 'tree record rewritten (checked_kst); its EXT pin line differs after H0 (recheck 17:59: VP 39/39, EXT 14/15)'},
            'H1': {'jobs': 'decl/jobs_fzp.json', 'jobs_sha256': sha(VP / 'decl' / 'jobs_fzp.json'),
                   'kst': '17:33:13-17:40:33', 'wmi_pid': 40772, 'exits': {},
                   'outputs': {d + '/' + p.name: sha(p) for d in ('fzp_cell', 'fzp_frames')
                               for p in sorted((OUT / d).glob('*.json'))},
                   'queue_log_sha256': sha(VP / 'logs' / 'fzp' / 'queue.log')},
            'H2': {'jobs': 'decl/specs/jobs_A.json', 'jobs_sha256': sha(VP / 'decl' / 'specs' / 'jobs_A.json'),
                   'kst': '17:40:59-17:54:29', 'wmi_pid': 24604, 'done': [], 'not_run': []},
            'L3': {'tool': 'tools/vp_analyze.py tables', 'tool_sha256': sha(VP / 'tools' / 'vp_analyze.py'),
                   'out_json': 'vp_tables_qv3_stop.json', 'out_json_sha256': sha(OUT / 'tables' / 'vp_tables_qv3_stop.json'),
                   'out_md': 'vp_tables_qv3_stop.md', 'out_md_sha256': sha(OUT / 'tables' / 'vp_tables_qv3_stop.md'),
                   'note': 'partial (2 states); declared names vp_tables.json/md not written'}},
        'collector': {'script_sha256': sha(VP / 'runs' / 'qv3_collect.py'),
                      'json_sha256': sha(VP / 'runs' / 'qv3_collect.json'), 'md_sha256': sha(VP / 'runs' / 'qv3_collect.md')},
        'partial_states': (col or {}).get('states'),
        'AB_table_rows': ((tabs or {}).get('AB') or {}).get('states'),
        'AB_summary_partial_not_declared_design': ((tabs or {}).get('AB') or {}).get('summary'),
        'AB_stops': ((tabs or {}).get('AB') or {}).get('stops'),
        'tools_pinned': {n: sha(VP / 'tools' / n) for n in ('vp_probe.py', 'vp_analyze.py', 'vp_queue.py', 'vp_jobcheck.py',
                                                            'vp_job.py', 'vp_common.py', 'vp_launch.ps1')},
        'hook_sha256': sha(VP / 'tools' / 'vp_hooks' / 'sitecustomize.py'),
        'report_scripts': {'qv3_report_json.py': sha(__file__)},
        'user_decisions': ['Q1 R1 objective rule (= P1_REPORT D1)',
                           'Q2 keep or rerun the T=3450 job that started after STOP_VP',
                           'Q3 queue STOP_VP check gap (= P1_REPORT D4)', 'Q4 EXT pin line for code_va.tree.json',
                           'Q5 STOP_VP removal (= P1_REPORT D2)'],
        'not_done': ['VISSIM/COM/runner/freeze 0', 'GWT8 untouched', 'tool/rule change 0', 'STOP_VP removal 0',
                     'sealed seeds 37/59/61/67 0, v3c3-s47 0, codex 64cf-s59/s61/s67 0', 'P1 (Q-V4) not run here',
                     'kills 0']}
    for p in sorted((VP / 'logs' / 'fzp').glob('*.done')):
        d = C.read_json(p) or {}
        res['steps']['H1']['exits'][d.get('tag')] = d.get('exit')
    states = C.read_json(C.DECL / 'VP_STATES.json')
    for r in states['probe_A']:
        tag = 'A_%s_T%06d' % (r['label'], r['T'])
        d = C.read_json(VP / 'logs' / 'plantA' / (tag + '.done'))
        if d:
            res['steps']['H2']['done'].append({'tag': tag, 'exit': d.get('exit'), 'sec': d.get('sec'), 'kst': d.get('kst')})
        else:
            res['steps']['H2']['not_run'].append(tag)
    C.write_json(VP / 'QV3_REPORT.json', res)
    print('QV3_REPORT.json done=%d not_run=%d' % (len(res['steps']['H2']['done']), len(res['steps']['H2']['not_run'])))


if __name__ == '__main__':
    main()
