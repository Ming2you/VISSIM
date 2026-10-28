"""One-off writer of P1_REPORT.json (P1 stop report, 2026-10-27 KST).  Not a probe tool: reads finished outputs only."""
import glob
import hashlib
import json
import math
import os

VP = r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/vsl_plant'
GT = r'D:/VISSIM-merge/k8_gate_trees/vsl_plant'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()


J = GT + '/out/plant_P/v3c3-s31_T001800'
p = json.load(open(J + '/probe.json', encoding='utf-8'))
rec = p['recorded']
r1 = p['evaluations']['R1_REC_ad']
d_obj = r1['objective_veh_h'] - rec['selected_objective']
cost_diffs = {k: {'recorded': rec['omega_costs'][k], 'replay_R1': r1['costs'][k],
                  'diff': r1['costs'][k] - rec['omega_costs'][k], 'ulp': math.ulp(rec['omega_costs'][k])}
              for k in rec['omega_costs'] if r1['costs'][k] != rec['omega_costs'][k]}
qa = json.load(open(GT + '/out/plant_A/v3c3-s31_T003300/probe.json', encoding='utf-8'))['checks']
fz = json.load(open(GT + '/out/tables/p1_fzp_afterH1.json', encoding='utf-8'))['profiles']
cells = [str(i) for i in range(8, 26)]
p1f = {}
for lab, prof in sorted(fz.items()):
    a = prof['all']
    row = {'low_speed_med': {c: a[c]['low_speed_med'] for c in cells}, 'low_n': {c: a[c]['low_n'] for c in cells},
           'congested_share': {c: a[c]['congested_share'] for c in cells},
           'cell18_minus_cells16_17_low_speed_med': a['18'].get("low_VS0'_minus_Mu'_speed_med"),
           'scan_sha256': prof['scan_sha256']}
    if 'vsl_free' in prof:
        row['vsl_free_low_speed_med'] = {c: prof['vsl_free'][c]['low_speed_med'] for c in cells}
    p1f[lab] = row
specs = {os.path.basename(f): sha(f) for f in sorted(glob.glob(GT + '/out/p1_specs/spec_P_*.json'))}
inputs = json.load(open(GT + '/out/p1_specs/p1_inputs.json', encoding='utf-8'))
out = {
    'schema': 'vp-p1-report/1', 'written_kst': __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S KST'),
    'pre': {'name': 'PRE_VP_FIXED.md', 'sha256': sha(VP + '/PRE_VP_FIXED.md'),
            'sections': 'section 5 (P1), 3.4 (R1), 7 (stop rules), 8 (order)'},
    'status': 'STOP', 'stop_rule': 'S-R1',
    'stop': {
        'state': 'v3c3-s31 T=1800 (P1, first of 9)', 'job_tag': 'P_v3c3-s31_T001800',
        'probe_exit': 5, 'jobcheck_exit': 2, 'stop_vp_written_kst': '2026-10-27 17:49:46 KST',
        'checks': p['checks'],
        'recorded_selected_objective': rec['selected_objective'], 'replay_R1_objective': r1['objective_veh_h'],
        'objective_diff_veh_h': d_obj, 'objective_ulp': math.ulp(rec['selected_objective']),
        'objective_diff_in_ulp': d_obj / math.ulp(rec['selected_objective']),
        'costs_n': len(rec['omega_costs']), 'costs_differing': cost_diffs,
        'FW_E_cost_bit_equal': r1['costs']['FW_E'] == rec['omega_costs']['FW_E'],
        'sum_recorded_costs': sum(rec['omega_costs'].values()), 'sum_replay_costs': sum(r1['costs'].values()),
        'rec_token': p['plans']['REC']['token'], 'recorded_plan_action_token': rec['plan_action_token'],
        'policy_token': p.get('policy_sha256'), 'price_receipt_committed': p.get('price_receipt_committed'),
        'R1_wall_sec': r1['wall_sec'], 'runs': p['runs'],
        'not_run': ['R2_REC_scalar', 'R3_REPACK_scalar', 'EXEC_scalar', 'ABL_null', 'ABL_C1..C9', 'P1 states 2..9']},
    'comparison_after_data': {
        'smoke_v3c3-s31_T2400_offlist': 'objective bit-equal in v1-v5; cost max diff 1.42e-14 (v1/v2/v4), <= 1e-13 (v5) [LOG]',
        'QV3_A_v3c3-s31_T3300': {k: qa[k] for k in ('R1_objective_bit_equal', 'R1_objective_diff', 'R1_costs_max_abs_diff')},
        'arith': {'diff_over_cost_tolerance_1e-9': d_obj / 1e-9, 'diff_over_sign_threshold_0.01': d_obj / 0.01}},
    'steps': {
        'L0': {'pins_VP': '39/39 OK', 'pins_VP_sha256': sha(VP + '/SHA256SUMS_VP.txt'), 'pins_EXT': '15/15 OK',
               'pins_EXT_sha256': sha(VP + '/SHA256SUMS_VP_EXT.txt'), 'selftest': '65/65',
               'selftest_record_sha256': sha(VP + '/selftest/selftest_L0_p1.json')},
        'L1': {'out': 'GT/out/tables/p1_fzp_L1.json', 'sha256': sha(GT + '/out/tables/p1_fzp_L1.json'),
               'sources_with_scan': 6},
        'H0': {'by': 'Q-V3 queue qv3_h0 (same VP/GT)', 'kst': '17:32:18-17:32:39', 'ok': True, 'files': 10569,
               'missing': 0, 'differs': 0, 'tree_record_sha256_now': sha(GT + '/code_va.tree.json'),
               'queue_log_sha256': sha(VP + '/logs/qv3_h0/queue.log'),
               'note': 'tree record rewritten by H0 (checked_kst); EXT pin line 53e4403f... no longer matches, by design'},
        'H1': {'by': 'Q-V3 queue fzp, decl/jobs_fzp.json', 'jobs_sha256': sha(VP + '/decl/jobs_fzp.json'),
               'kst': '17:33:13-17:40:33', 'exits': 'all 0 (9/9)', 'queue_log_sha256': sha(VP + '/logs/fzp/queue.log'),
               'outputs': {os.path.basename(os.path.dirname(f)) + '/' + os.path.basename(f): sha(f) for f in
                           sorted(glob.glob(GT + '/out/fzp_cell/*.json') + glob.glob(GT + '/out/fzp_frames/*.json'))}},
        'L2': {'p1_inputs_sha256': sha(GT + '/out/p1_specs/p1_inputs.json'),
               'jobs_P_sha256': sha(GT + '/out/p1_specs/jobs_P.json'), 'specs': specs,
               'C1_cells_changed': sorted(inputs['C1']['cells'], key=int), 'C7_frames_per_state': 2},
        'H3': {'launch': 'vp_launch.ps1 tag p1h3, WMI PID 32620, queue pid 35444, BELOW_NORMAL',
               'queue_log_sha256': sha(VP + '/logs/plantP/queue.log'), 'jobs_run': 1, 'jobs_not_run': 8,
               'job_lock_kst': '17:46:02-17:49:45',
               'evidence': {n: sha(J + '/' + n) for n in ('probe.json', 'job_summary.json', 'jobcheck.json',
                                                         'bundle_record.json')},
               'hook_files': {os.path.basename(f): sha(f) for f in glob.glob(J + '/hooks/*.json')},
               'stop_vp_sha256': sha(VP + '/STOP_VP')},
        'L3': 'not run (stopped before any table input)'},
    'p1f_vissim_after_data': {
        'tool': 'vp_analyze.py p1-fzp (pinned a3638816...)', 'out_sha256': sha(GT + '/out/tables/p1_fzp_afterH1.json'),
        'cells': '8-25', 'low_density': 'k <= 12 veh/km/lane, 60 s windows, 900 <= t0, t0+60 <= 9000', 'sources': p1f},
    'observed_other_workflow': ('Q-V3 queue plantA (pid 27604) took the lock at 17:50:05, after STOP_VP (17:49:46), and '
                                'started A_v3c3-s31_T003450. vp_queue.py checks STOP_VP before waiting for the lock '
                                '(line 38), not after taking it (line 47). That job released the lock at 17:54:28 and the queue stopped at 17:54:29 before A_v3c3-s31_T004050. Not our process; untouched.'),
    'not_done': ['VISSIM/COM/runner/freeze 0', 'GWT8 untouched (c20aff1d)', 'repo/frozen tree writes 0',
                 'rule change 0', 'rerun 0', 'other processes killed 0', 'sealed seeds 0'],
}
with open(VP + '/P1_REPORT.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print('ok', sha(VP + '/P1_REPORT.json'))
print(json.dumps(cost_diffs))
print(out['comparison_after_data']['arith'])
