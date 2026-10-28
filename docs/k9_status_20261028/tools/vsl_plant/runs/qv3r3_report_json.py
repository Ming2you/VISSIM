"""Write QV3_REPORT.json r2 (Q-V3 r3 run; mechanical; reads finished outputs only).

    python -B qv3r3_report_json.py <status PASS|STOP|PARTIAL>

Reads: runs/qv3r3_collect.json, GT/out/tables/vp_tables_qv3r3.json, queue logs and .done records, L0/H0 records,
decl/R3_MARKS.json.  Writes VP/QV3_REPORT.json (the r1 JSON is kept as QV3_REPORT_r1.json)."""
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
    status = sys.argv[1]
    col = C.read_json(VP / 'runs' / 'qv3r3_collect.json') or {}
    tabs = C.read_json(OUT / 'tables' / 'vp_tables_qv3r3.json') or {}
    st_path = VP / 'selftest' / 'selftest_qv3r3_L0_745408.json'
    st = C.read_json(st_path) or {}
    res = {
        'schema': 'qv3-report/2', 'revision': 'r2', 'made_kst': C.kst(), 'status': status,
        'basis': {'PRE_VP_FIXED.md': sha(VP / 'PRE_VP_FIXED.md'), 'PRE_VP_R3.md': sha(VP / 'PRE_VP_R3.md'),
                  'decisions': 'D-K9-103 Q-V3; D-K9-108, D-K9-109 (r3)',
                  'K9_1_J1_NOTES_20261013.md': sha(VP.parent / 'K9_1_J1_NOTES_20261013.md')},
        'report_md_sha256': sha(VP / 'QV3_REPORT.md'),
        'r1_report': {'QV3_REPORT_r1.md': sha(VP / 'QV3_REPORT_r1.md'), 'QV3_REPORT_r1.json': sha(VP / 'QV3_REPORT_r1.json')},
        'steps': {
            'L0': {'kst': '2026-10-27 18:23', 'PRE_VP_R3_sha_matches': True, 'pins_VP_r3': '54/54', 'pins_EXT_r3': '14/14',
                   'SHA256SUMS_VP_r3.txt': sha(VP / 'SHA256SUMS_VP_r3.txt'),
                   'SHA256SUMS_VP_EXT_r3.txt': sha(VP / 'SHA256SUMS_VP_EXT_r3.txt'),
                   'treefields': {'file': 'selftest/treefields_qv3r3_L0_745408.json',
                                  'sha256': sha(VP / 'selftest' / 'treefields_qv3r3_L0_745408.json'),
                                  'ok': (C.read_json(VP / 'selftest' / 'treefields_qv3r3_L0_745408.json') or {}).get('ok')},
                   'selftest': {'file': 'selftest/selftest_qv3r3_L0_745408.json', 'sha256': sha(st_path),
                                'n_ok': st.get('n_ok'), 'n': st.get('n')}},
            'H0': {'jobs': 'runs/jobs_qv3r3_h0.json', 'jobs_sha256': sha(VP / 'runs' / 'jobs_qv3r3_h0.json'),
                   'kst': '18:24:42-18:25:02', 'wmi_pid': 20000, 'queue_pid': 28012,
                   'done': C.read_json(VP / 'logs' / 'qv3r3_h0' / 'tree_verify.done'),
                   'tree_after_H0': {k: (C.read_json(str(C.CODE) + '.tree.json') or {}).get(k)
                                     for k in ('ok', 'files_expected', 'missing_n', 'differs_n', 'freeze_sha256')},
                   'treefields_after_H0': {'file': 'selftest/treefields_qv3r3_H0_745612.json',
                                           'sha256': sha(VP / 'selftest' / 'treefields_qv3r3_H0_745612.json'),
                                           'ok': (C.read_json(VP / 'selftest' / 'treefields_qv3r3_H0_745612.json') or {}).get('ok')},
                   'queue_log_sha256': sha(VP / 'logs' / 'qv3r3_h0' / 'queue.log')},
            'H1': {'note': 'not rerun: 9 .done (exit 0) and output sha equal to LOG 17:40',
                   'jobs_sha256': sha(VP / 'decl' / 'jobs_fzp.json'), 'exits': {},
                   'outputs': {d + '/' + p.name: sha(p) for d in ('fzp_cell', 'fzp_frames')
                               for p in sorted((OUT / d).glob('*.json'))}},
            'H2': {'jobs': 'decl/specs/jobs_A.json', 'jobs_sha256': sha(VP / 'decl' / 'specs' / 'jobs_A.json'),
                   'launch_kst': '2026-10-27 18:25:20', 'wmi_pid': 38488, 'queue_pid': 43084,
                   'queue_sha256': sha(VP / 'tools' / 'vp_queue.py'), 'queue_log_sha256': sha(VP / 'logs' / 'plantA' / 'queue.log'),
                   'done': [], 'not_run': []},
            'L3': {'tool': 'tools/vp_analyze.py tables', 'tool_sha256': sha(VP / 'tools' / 'vp_analyze.py'),
                   'out_json': 'vp_tables_qv3r3.json', 'out_json_sha256': sha(OUT / 'tables' / 'vp_tables_qv3r3.json'),
                   'out_md': 'vp_tables_qv3r3.md', 'out_md_sha256': sha(OUT / 'tables' / 'vp_tables_qv3r3.md'),
                   'note': 'Q-V3 run name; the AB part reads plant_A and fzp_frames only; the P1 part of this file is '
                           'whatever the P1 run had finished at that moment (not a Q-V3 result)'}},
        'collector': {'script': 'runs/qv3r3_collect.py', 'script_sha256': sha(VP / 'runs' / 'qv3r3_collect.py'),
                      'json_sha256': sha(VP / 'runs' / 'qv3r3_collect.json'), 'md_sha256': sha(VP / 'runs' / 'qv3r3_collect.md')},
        'states': col.get('states'),
        'AB_stops_raw': col.get('AB_stops_raw'),
        'AB_stops_r3_bit_reports': col.get('AB_stops_r3_bit_reports'),
        'AB_stops_r3_hits': col.get('AB_stops_r3_hits'),
        'AB_summary': col.get('AB_summary'),
        'group_spans': col.get('group_spans'),
        'X1_max_over_states': col.get('X1_max_over_states'),
        'AB_table_rows': (tabs.get('AB') or {}).get('states'),
        'R3_MARKS': C.read_json(C.DECL / 'R3_MARKS.json'), 'R3_MARKS_sha256': sha(C.DECL / 'R3_MARKS.json'),
        'tools_pinned_r3': {n: sha(VP / 'tools' / n) for n in ('vp_probe.py', 'vp_analyze.py', 'vp_queue.py', 'vp_jobcheck.py',
                                                               'vp_job.py', 'vp_common.py', 'vp_launch.ps1', 'vp_treefields.py')},
        'hook_sha256': sha(VP / 'tools' / 'vp_hooks' / 'sitecustomize.py'),
        'report_scripts': {'qv3r3_report_json.py': sha(__file__)},
        'concurrent_P1_queue_log_sha256_at_report': sha(VP / 'logs' / 'plantP' / 'queue.log'),
        'not_done': ['VISSIM/COM/runner/freeze 0', 'GWT8 untouched (c20aff1d)', 'tool/rule change 0',
                     'sealed seeds 37/59/61/67 0, v3c3-s47 0, codex 64cf-s59/s61/s67 0', 'P1 (Q-V4) not run here',
                     'kills 0', 'STOP_VP written/removed by this run 0']}
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
    print('QV3_REPORT.json status=%s done=%d not_run=%d' % (status, len(res['steps']['H2']['done']),
                                                            len(res['steps']['H2']['not_run'])))


if __name__ == '__main__':
    main()
