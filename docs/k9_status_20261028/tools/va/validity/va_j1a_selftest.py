"""Self-test comparison for va_j1a.py on J1 runs (published numbers; no V-A data).
python -B va_j1a_selftest.py <outdir>
Reads <outdir>/st_check_j1r_s31.json, st_check_j1_s41.json, st_check_j1_s43.json, st_pair_j1r_s31.json,
st_pair_j1_s41.json, st_pair_j1_s43.json, st_freeze_j1r.json, st_ha_*.json (made by va_j1a.py) and the J1 published
outputs (sha256 checked against the values in SP/j1/analysis/VALIDITY.md sec.7 / sec.11 and the J1-A reports):
  SP/j1/analysis/out/j1a_s31r.json 53cf93b8..., pair_s31r.json cc81bc3d..., freeze_check.json 0a64a025...,
  SP/j1/s31fail/out/j1a_s41.json 212b1c8d..., j1a_s43.json 200131d5..., pair_s41.json 4c2249b3..., pair_s43.json 1f120901...
Prints one line per comparison and SELFTEST_ALL_OK / SELFTEST_DIFF. Writes <outdir>/selftest_compare.json."""
import hashlib
import json
import os
import sys

sys.dont_write_bytecode = True
SP = r'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\j1'
REF = {
    'j1a_s31r': (os.path.join(SP, 'analysis', 'out', 'j1a_s31r.json'), '53cf93b8'),
    'pair_s31r': (os.path.join(SP, 'analysis', 'out', 'pair_s31r.json'), 'cc81bc3d'),
    'freeze_k8b': (os.path.join(SP, 'analysis', 'out', 'freeze_check.json'), '0a64a025'),
    'j1a_s41': (os.path.join(SP, 's31fail', 'out', 'j1a_s41.json'), '212b1c8d'),
    'j1a_s43': (os.path.join(SP, 's31fail', 'out', 'j1a_s43.json'), '200131d5'),
    'pair_s41': (os.path.join(SP, 's31fail', 'out', 'pair_s41.json'), '4c2249b3'),
    'pair_s43': (os.path.join(SP, 's31fail', 'out', 'pair_s43.json'), '1f120901'),
}
MAP_ON = {'S1': 'S1_DECISIONS_FAILED_0_and_HELD_line_1', 'S2': 'S2_no_ERROR_lines', 'S3': 'S3_launcher_EXIT_code0',
          'S4': 'S4_STAGE_SIM_DONE', 'S5': 'S5_failure_counters_0', 'S6': 'S6_error_txt_only_at_hold_T_and_hold_error_0',
          'K8': 'K8_DECISION_FAILED_only_allowed_places', 'SIG1': 'SIG1_MIDBLOCK_COM_SKIPS_gt0', 'SIG2': 'SIG2_readback_sg_ge_9_zero',
          'DEC1': 'DEC1_61_eq_OK_plus_HELD_and_hold_sets_equal', 'DEC2': 'DEC2_warmup_no_control',
          'DEC3': 'DEC3_sdmpc_active_nonhold_T_ge_900_applied_pending', 'DEC4': 'DEC4_budget_fields_nonhold',
          'DEC5': 'DEC5_exit0_nonhold', 'PROV1': 'PROV1_head_b9734abe_reading_A', 'PROV2': 'PROV2_tuning_d0f9ef39',
          'PROV3': 'PROV3_network_3de889f0', 'PROV_freeze': 'PROV_freeze_6143d3eb', 'PROV_env': 'PROV_env_policy_failfast',
          'PROV_runlog_policy_line': 'PROV_runlog_policy_line_1', 'PROV_seed': 'PROV_seed_31',
          'VSL1': 'VSL1_box_step_le_40_and_hold_delta_0', 'VSL2': 'VSL2_block0_allowed_80_90_100_110',
          'MTR': 'MTR_K3_RM_C10490_no_green_3', 'K8a': 'K8a_install_check_present_passed_nonhold_T_ge_900',
          'K8b': 'K8b_S6_capture_every_decision_plus_hold_caps', 'U9a': 'U9a_chain_no_mismatch'}
MAP_OFF = {'S1': 'S_DECISIONS_FAILED_0', 'S2': 'S_no_ERROR_lines', 'S3': 'S_launcher_EXIT_code0', 'S4': 'S_STAGE_SIM_DONE',
           'S5': 'S_failure_counters_0', 'S6': 'S_no_error_txt', 'K8': 'S_K8_DECISION_FAILED_0',
           'SIG1': 'SIG_MIDBLOCK_COM_SKIPS_gt0', 'SIG2': 'SIG_readback_sg_ge_9_zero', 'DEC1': 'DEC_61_6_55',
           'DEC2': 'DEC_warmup_no_control', 'DEC3': 'DEC_sdmpc_active_T_ge_900', 'DEC4': 'DEC_budget_fields',
           'DEC5': 'DEC_all_exit0', 'PROV1': 'PROV_head_K8', 'PROV2': 'PROV_tuning_5f0d0e40', 'PROV3': 'PROV_network_3de889f0',
           'VSL1': 'VSL_box_step_le_40', 'VSL2': 'VSL_block0_allowed_80_90_100_110', 'MTR': 'METER_K3_RM_C10490_no_green_3',
           'K8a': 'K8_install_check_present_passed_T_ge_900', 'K8b': 'K8_S6_capture_every_decision', 'U9a': 'U9a_chain_no_mismatch'}
DF_FILES = ('runlog', 'runlog.err', 'launch', 'wmi', 'WATCHDOG_PROGRESS.txt', 'vissim_simulation_001.err', 'vissim_network.err')
WD_WALL = {'j1r_s31': 30699, 'j1_s41': 30045, 'j1_s43': 33055}   # J1_REPORT.md:408-410 / VALIDITY.md sec.2 S3


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


rows = []


def cmp(tag, what, mine, ref):
    ok = mine == ref
    rows.append({'tag': tag, 'what': what, 'ok': ok, 'mine': mine if not ok else None, 'ref': ref if not ok else None})
    print('%-4s %-10s %-48s %s' % ('OK' if ok else 'DIFF', tag, what, '' if ok else 'mine=%r ref=%r' % (mine, ref)))


def main():
    od = sys.argv[1]
    ref = {}
    for k, (p, s16) in REF.items():
        got = sha(p)
        cmp('ref', k + ' sha16', got[:8], s16)
        ref[k] = load(p)
    for tag, rk, mp, pk in (('j1r_s31', 'j1a_s31r', MAP_ON, 'pair_s31r'), ('j1_s41', 'j1a_s41', MAP_OFF, 'pair_s41'),
                            ('j1_s43', 'j1a_s43', MAP_OFF, 'pair_s43')):
        m = load(os.path.join(od, 'st_check_%s.json' % tag))
        r = ref[rk]
        for mine_k, ref_k in mp.items():
            cmp(tag, 'item ' + mine_k, m['items'][mine_k], r['items'][ref_k])
        cmp(tag, 'n items counted', m['n_items_counted'], len(r['items']))
        cmp(tag, 'failed_items', m['failed_items'], r['failed_items'])
        cmp(tag, 'runlog_counters', m['runlog_counters'], {k: r['runlog_counters'].get(k) for k in m['runlog_counters']})
        cmp(tag, 'signal_readback', m['signal_readback'], r['signal_readback'])
        for k in ('rows_vsl_readback', 'expected_rows', 'n_rows_checked', 'n_mismatch', 'vr_not_ok', 'seg_fallback_rows',
                  'csv_speed_forbidden_rows', 'vr_stages', 'vr_classes'):
            cmp(tag, 'u9a ' + k, m['u9a'][k], r['u9a'][k])
        cmp(tag, 'u9a below110', m['u9a']['below110_by_road_cmd'], r['u9a']['below110'])
        if 'below110_T' in r['u9a']:
            cmp(tag, 'u9a below110_T', m['u9a']['below110_T'], r['u9a']['below110_T'])
        for k in ('pairs', 'max_abs_step', 'keys_n', 'block0_allowed_sets', 'block0_bad', 'block0_coords_per_decision'):
            cmp(tag, 'vsl_box ' + k, m['vsl_box'][k], r['vsl_box'][k])
        cmp(tag, 'vsl_box violations', m['vsl_box']['n_violations'], len(r['vsl_box']['violations']))
        cmp(tag, 'meter RM_C10490 green 3 rows', m['meter_K3']['RM_C10490_green_3_rows'], r['meter_K3']['RM_C10490_green_3_rows'])
        cmp(tag, 'n_json / warmup / sdmpc', [m['n_json'], m['n_warmup_json'], m['n_sdmpc_json']],
            [r['n_json'], r['n_warmup_json'], r['n_sdmpc_json']])
        cmp(tag, 'error_files', m['error_files'], r['error_files'])
        cmp(tag, 'DECISION_FAILED captures', m['decision_failed_counts_captures'], r['decision_failed_counts_captures'])
        rdf = r['decision_failed_counts_logs']
        rdf_n = {}
        for k, v in rdf.items():
            kk = k.replace(r['name'], '<run>')
            kk = {'runlog_<run>.txt': 'runlog', 'runlog_<run>.txt.err': 'runlog.err', 'launch_<run>.log': 'launch',
                  'wmi_<run>.log': 'wmi'}.get(kk, kk)
            rdf_n[kk] = v
        cmp(tag, 'DECISION_FAILED logs', {k: m['decision_failed_counts_logs'][k] for k in DF_FILES}, {k: rdf_n.get(k) for k in DF_FILES})
        if 'hold_T_sets' in r:
            cmp(tag, 'hold_T_sets', m['hold_T_sets'], r['hold_T_sets'])
            cmp(tag, 'n_hold', m['n_hold'], r['n_hold'])
        mw, rw = m['report']['sdmpc_wall_sec'], r['report']['sdmpc_wall_sec']
        cmp(tag, 'sdmpc wall n/min/max/sum/mean/median', [mw['n'], mw['min'], mw['max'], mw['sum'], mw['mean'], mw['median']],
            [rw['n'], rw['min'], rw['max'], rw['sum'], rw['mean'], rw['median']])
        cmp(tag, 'sdmpc wall gt_900_T', mw['gt_900_T'], rw['gt_900_T'])
        if 'warmup_wall_sec' in r['report']:
            cmp(tag, 'warmup wall min/max', [m['report']['warmup_wall_sec']['min'], m['report']['warmup_wall_sec']['max']],
                r['report']['warmup_wall_sec'])
        cmp(tag, 'WATCHDOG wall_sec', m['report']['watchdog_wall_sec'], WD_WALL[tag])
        pv, rp = m['provenance'], r['provenance']
        for k in ('plan_freeze_head', 'frz_FREEZE_json_git_head', 'plan_tuning_sha256', 'prov_files_tuning_sha256',
                  'prov_env_tuning_sha256', 'frz_tuning_file_sha256', 'prov_files_network_sha256', 'network_copy_file_sha256',
                  'prov_seed', 'plan_seed', 'prov_workspace_git_commit', 'frz_FREEZE_json_file_sha256', 'plan_freeze_sha256',
                  'prov_vbs_sha256', 'prov_wd_sha256', 'prov_cao_sha256'):
            if k in rp:
                cmp(tag, 'prov ' + k, pv.get(k), rp.get(k))
        if 'literal_9_2_PROV1_run_provenance_workspace_git_commit_eq_head' in r:
            cmp(tag, 'PROV1 reading B (literal)', m['prov_checks']['PROV1_reading_B_run_provenance_workspace_git_commit_eq_head (report only, amendment 34 sec.7.1)'],
                r['literal_9_2_PROV1_run_provenance_workspace_git_commit_eq_head'])
        cmp(tag, 'hold audit vacuous', [m['hold_audit']['n_hold_T'], m['hold_audit']['violations'], m['hold_audit']['incomplete']], [0, [], []])
        cmp(tag, 'run folder after EXIT+60s', m['report']['after_exit']['n_modified_after_exit_plus_60s'], 0)
        cmp(tag, 'FZP last frame', m['report']['fzp']['last_frame_sec'], 8995.1)
        cs = m['comparator_selftest']
        cmp(tag, 'HA6 comparator all non-hold equal', cs['HA6_runner_log_eq_adapter_csv_nonhold']['not_equal_T'], [])
        cmp(tag, 'HA4 comparator all pinned equal', cs['HA4_next_pin_eq_prev_json_nonhold']['not_equal_T'], [])
        print('     %-10s HA4 comparator: with pin %d, equal %d, next without pin %s' % (
            tag, cs['HA4_next_pin_eq_prev_json_nonhold']['n_with_pin'], cs['HA4_next_pin_eq_prev_json_nonhold']['equal'],
            cs['HA4_next_pin_eq_prev_json_nonhold']['next_without_pin_T']))
        cmp(tag, 'run_valid_by_tool', m['run_valid_by_tool'], True)
        # pair
        pm, pr = load(os.path.join(od, 'st_pair_%s.json' % tag)), ref[pk]
        cmp(tag, 'pairing_check', pm['pairing_check'], pr['pairing_check'])
        for k in ('pre900_frames', 'pre900_all_equal', 'pre900_omega_equal', 'pre900_entries_equal_inputs', 'inputs', 'pre900_entries_total'):
            cmp(tag, 'pair ' + k, pm[k], pr[k])
        arm_ref = pr.get('j1r') or pr.get('j1')
        cmp(tag, 'pair arm shim', pm['arm']['shim'], arm_ref['shim'])
        cmp(tag, 'pair nc3 shim', pm['nc3']['shim'], pr['nc3']['shim'])
        cmp(tag, 'pair frames', [pm['arm']['frames'], pm['nc3']['frames']], [arm_ref['frames'], pr['nc3']['frames']])
    fm, fr = load(os.path.join(od, 'st_freeze_j1r.json')), ref['freeze_k8b']
    for k in ('freeze_json_sha256', 'n_listed', 'n_listed_bad', 'git_head', 'n_unlisted_noncache'):
        cmp('frz_k8b', k, fm[k], fr[k])
    cmp('frz_k8b', 'unlisted cache (report only; later runs may add)', fm['unlisted_cache_files'], fr['unlisted_cache_files'])
    for f in sorted(os.listdir(od)):
        if f.startswith('st_ha_') and f.endswith('.json'):
            h = load(os.path.join(od, f))
            cmp('ha_unit', f + ' HA1 HA2 HA3 HA5 HA7', [h.get(k) for k in ('HA1', 'HA2', 'HA3', 'HA5', 'HA7')], [True] * 5)
    diffs = [x for x in rows if not x['ok'] and not x['what'].startswith('unlisted cache')]
    with open(os.path.join(od, 'selftest_compare.json'), 'w', encoding='utf-8') as f:
        json.dump({'rows': rows, 'n': len(rows), 'n_diff_counted': len(diffs)}, f, indent=1, default=str)
    print('SELFTEST_ALL_OK' if not diffs else 'SELFTEST_DIFF %d' % len(diffs), 'rows', len(rows))


if __name__ == '__main__':
    main()
