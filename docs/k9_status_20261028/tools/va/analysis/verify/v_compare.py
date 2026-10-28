# 검증 대조: 검증자 재계산(v_metrics·v_local·v_control) 대 분석 출력(va_metrics·va_local·va_control·va_followup).
# veh·h 칸은 |차| <= 0.05 (0.1 반올림 안), 대수·T·목록은 같음, 비율·평균은 1e-6. 분석 도구를 import 하지 않음(출력 JSON만 읽음).
# 사용: python -B v_compare.py --profile va|selftest  ->  <out>/v_compare.json, 끝 줄 ALL_OK 또는 NOT_OK
import io, json, os, sys
from v_common import profile, out_dir, jl, jd, SEEDS

prof = profile()
OUT = out_dir(prof)
SP = r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/va/analysis'
AOUT = SP + ('/out' if prof == 'va' else '/selftest/out')
VM, VL, VC = jl(OUT + '/v_metrics.json'), jl(OUT + '/v_local.json'), jl(OUT + '/v_control.json')
AM, AL, AC, AF = (jl(AOUT + '/va_metrics.json'), jl(AOUT + '/va_local.json'), jl(AOUT + '/va_control.json'),
                  jl(AOUT + '/va_followup.json'))
R = []
TOL_VH = 0.05


def ck(name, a, b, tol=None):
    if tol is None:
        ok = a == b
    else:
        ok = (a is None and b is None) or (a is not None and b is not None and abs(a - b) <= tol)
    R.append(dict(check=name, ok=bool(ok), verify=a if not ok else None, analysis=b if not ok else None))


S = [str(s) for s in SEEDS]
KM = {'M1': 'M1', 'M2': 'M2', 'M3': 'M3', 'M3u': 'M3u', 'M4': 'M4', 'M4a': 'M4a', 'M4b': 'M4b', 'OUTa': 'OUT_a', 'OUTb': 'OUT_b',
      'U1098': 'unins_1098', 'U1099': 'unins_1099', 'Uother': 'unins_other', 'REC': 'x_off_receivers_shared', 'REM': 'REM', 'REM_B': 'REM_B'}
for u in ('U6VA', 'U9', 'U6J1'):
    ck('union.%s' % u, [str(x) for x in VM['union'][u]], AM['unions'][u])
for pk in ('A', 'B', 'Bp', 'J1R'):
    vp, ap = VM['pairs'][pk], AM['pairs'][pk]
    for vk, ak in KM.items():
        tol = 1e-9 if vk.startswith('REM') else TOL_VH
        for i, s in enumerate(S):
            ck('pair.%s.%s.d.s%s' % (pk, ak, s), vp['stats'][vk]['d'][i], ap['summary'][ak]['per_seed'][s], tol)
        ck('pair.%s.%s.mean' % (pk, ak), vp['stats'][vk]['mean'], ap['summary'][ak]['mean'], tol)
        ck('pair.%s.%s.ci_lo' % (pk, ak), vp['stats'][vk]['ci'][0], ap['summary'][ak]['ci90'][0], TOL_VH)
        ck('pair.%s.%s.ci_excl0' % (pk, ak), vp['stats'][vk]['ci_excl0'], ap['summary'][ak]['ci_excludes_0'])
    for vk, ak in (('om_fw_e_main', 'fw_e_main'), ('om_fw_w_main', 'fw_w_main'), ('om_onramp', 'onramp'),
                   ('om_offramp', 'offramp_inside'), ('om_urban_omega', 'urban_omega')):
        for i, s in enumerate(S):
            ck('split.%s.%s.s%s' % (pk, ak, s), vp['stats'][vk]['d'][i], ap['omega_split_summary'][ak]['per_seed'][s], TOL_VH)
    for s in S + ['mean']:
        for k in ('N', 'W_A', 'W_B'):
            ck('label.%s.%s.%s' % (pk, s, k), True, ap['labels'][s][k].startswith(vp['labels'][s][k]))
    for s in S:
        ck('pairing.%s.s%s' % (pk, s), VM['pairing']['%s_s%s' % (pk, s)]['ok'], ap['pairing'][s]['ok'])
        ck('pre900.%s.s%s' % (pk, s), vp['pre900_maxabs'][s], ap['pairing'][s]['max_abs_pre900_delta'], TOL_VH)
for s in S:
    for arm in ('nc3', 'j1', 'va'):
        t = '%s_s%s' % (arm, s)
        e, a = VM['end'][t], AM['per_run']['U9|' + t]['end_state']
        ck('end.%s.in_net' % t, e['in_net'], a['in_network_last_frame'])
        ck('end.%s.omega' % t, e['omega'], a['omega_last_frame'])
        ck('end.%s.seen' % t, e['seen'], a['vehicles_seen'])
        ck('end.%s.removals' % t, e['removals'], a['removals'])
        ck('end.%s.rem_outside' % t, e['rem_outside'], a['removals_membership']['outside_omega'])
        ck('end.%s.remains' % t, {str(k): v for k, v in e['remains'].items()}, a['remains'])
    for arm in ('j1', 'va'):
        t = '%s_s%s' % (arm, s)
        ck('s7.%s.late' % t, VM['s7'][t]['n_late'], AM['s7_late'][t]['late'])
        ck('s7.%s.unique' % t, VM['s7'][t]['n_jsonl'], AM['s7_late'][t]['unique_removals'])
for u in ('U6VA', 'U9'):
    for no, v in VM['uninserted_by_input'][u].items():
        for t, x in v.items():
            ck('unins.%s.%s.%s' % (u, no, t), x['total'], AM['unins_by_input'][u][no][t]['veh_h_nc_anchor'], TOL_VH)
F1, A1 = VM['input_1083'], AF['input_1083']
for s in S:
    for arm in ('nc3', 'j1', 'va'):
        t = '%s_s%s' % (arm, s)
        ck('i1083.%s.remain' % t, F1[t]['remain'], A1['runs'][t]['remain_err'])
        ck('i1083.%s.inserted' % t, F1[t]['inserted'], A1['runs'][t]['inserted'])
        ck('i1083.%s.delay' % t, F1[t]['delay'], A1['runs'][t]['delay_veh_h_nc3_anchor'], TOL_VH)
        ck('i1083.%s.maxq' % t, F1[t]['maxq_frame'], A1['runs'][t]['max_queue_frame'], 0.5)
    for pk in ('A', 'B'):
        ck('i1083.%s.s%s.first_gt10' % (pk, s), F1['%s_s%s' % (pk, s)]['first_gt10'], A1['pairs'][pk]['s' + s]['first_gt10_clipped_t'])
        ck('i1083.%s.s%s.bindiff' % (pk, s), F1['%s_s%s' % (pk, s)]['bindiff_from28'], A1['pairs'][pk]['s' + s]['entries_diff_from_bin28'])
        ck('i1083.%s.s%s.share' % (pk, s), F1['%s_s%s' % (pk, s)]['share'], A1['pairs'][pk]['s' + s]['d4b_share_1083'], TOL_VH)
for l, v in VM['link174_chain'].items():
    for t, x in v['ttt'].items():
        ck('chain.%s.%s.full' % (l, t), x[0], AF['link174_chain']['link_vh'][l][t]['full'], TOL_VH)
        ck('chain.%s.%s.from4350' % (l, t), x[1], AF['link174_chain']['link_vh'][l][t]['from_4350'], TOL_VH)
for t, x in VM['link174_chain']['174']['frames'].items():
    a = AL['runs'][t]['occ_174']['F_all']
    ck('fzp174.%s.mean' % t, x['mean'], a['mean'], 1e-6)
    ck('fzp174.%s.max' % t, x['max'], a['max'])
    ck('fzp174.%s.max_t' % t, x['max_t'], a['max_t'])
for l, v in VM['sc109_east'].items():
    for t, x in v['ttt'].items():
        ck('east.%s.%s.full' % (l, t), x[0], AF['sc109_east']['link_vh'][l][t]['full'], TOL_VH)
        ck('east.%s.%s.P' % (l, t), x[1], AF['sc109_east']['link_vh'][l][t]['P_1800_7200'], TOL_VH)
        f, a = v['frames'][t], AL['runs'][t]['occ_%s' % l]
        ck('east.%s.%s.F_mean' % (l, t), f['F_mean'], a['F_all']['mean'], 1e-6)
        ck('east.%s.%s.F_max' % (l, t), f['F_max'], a['F_all']['max'])
        ck('east.%s.%s.P_mean' % (l, t), f['P_mean'], a['P_1800_7200']['mean'], 1e-6)
    for pk in ('A', 'B'):
        for w in ('full', 'P_1800_7200'):
            ck('east.%s.%s.%s.mean' % (l, pk, w), v['%s_%s' % (pk, w)]['mean'], AF['sc109_east']['paired'][pk]['%s.link_vh.%s' % (l, w)]['mean'], TOL_VH)
LMAP = {'n491_P_mean': 'occ_10491.P_1800_7200.mean', 'n491_P_max': 'occ_10491.P_1800_7200.max', 'n491_F_mean': 'occ_10491.F_all.mean',
        'n491_F_max': 'occ_10491.F_all.max', 'n127_P_mean': 'occ_127_lanes12.P_1800_7200.mean', 'n127_P_max': 'occ_127_lanes12.P_1800_7200.max',
        'n127_F_mean': 'occ_127_lanes12.F_all.mean', 'n127_F_max': 'occ_127_lanes12.F_all.max'}
for pk in ('A', 'B'):
    for vk, ak in LMAP.items():
        ck('local.%s.%s.mean' % (pk, vk), VL['local_stats']['%s_%s' % (pk, vk)]['mean'], AL['paired'][pk][ak]['mean'], 1e-6)
    for side in ('W', 'E'):
        for k in ('frac_peak', 'frac_all'):
            ck('local.%s.%s.%s' % (pk, side, k), VL['local_stats']['%s_%s_%s' % (pk, side, k)]['mean'],
               AL['paired'][pk]['spill_FW_%s.%s' % (side, k)]['mean'], 1e-9)
for s in S:
    for t in ('nc3_s' + s, 'j1_s' + s, 'va_s' + s):
        ck('events.%s.W' % t, [VL['local'][t]['W']['n_ev'], VL['local'][t]['W']['first']],
           [AL['runs'][t]['spill_FW_W']['n_event_windows'], AL['runs'][t]['spill_FW_W']['first']])
    ds = VL['desspeed']['va_s' + s]
    az = AL['desspeed']['s' + s]['by_level_zone']
    for key, x in ds.items():
        c, z, g = key.split('|')
        grp = 'sign_passed' if g == 'pass' else 'no_upstream_obs'
        for rd, field in (('C_command', 'in_C'), ('M_written', 'in_M')):
            a = (((az.get(rd) or {}).get('%g' % float(c)) or {}).get(z) or {}).get(grp) or {'n': 0, 'in_band': 0}
            ck('dess.s%s.%s.%s.n' % (s, rd, key), x['n'], a['n'])
            ck('dess.s%s.%s.%s.in' % (s, rd, key), x[field], a['in_band'])
for s in S:
    for arm in ('j1', 'va'):
        t = '%s_s%s' % (arm, s)
        v, a = VC['runs'][t], AC['runs'][t]
        ck('ctl.%s.n_json' % t, v['n_json'], a['n_action_json'])
        ck('ctl.%s.exit_codes' % t, {str(k): x for k, x in v['exit_codes'].items()}, a['exit_codes'])
        ck('ctl.%s.sdmpc_wall_median' % t, v['sdmpc_wall']['median'], a['wall_sdmpc']['median'], 1e-9)
        ck('ctl.%s.sdmpc_wall_sum' % t, v['sdmpc_wall']['sum'], a['wall_sdmpc']['sum'], 1e-6)
        ck('ctl.%s.over900' % t, v['sdmpc_wall']['over900'], len(a['wall_sdmpc_gt900_T']))
        ck('ctl.%s.holds' % t, v['holds'], a['holds']['T'])
        pp = a['previous_plan_kept']
        ck('ctl.%s.prev_plan' % t, [v['prev_plan'][k] for k in ('cand', 'ga', 'na', 'da')] + [v['prev_plan']['three']],
           [pp['candidates'], pp['ga_same_green_offsets'], pp['na_no_prediction_sequence'], pp['da_selected_repr_eq_held'], pp['all_three_T']])
        ck('ctl.%s.p3' % t, [v['p3']['count'], v['p3']['first'], v['p3']['longest']],
           [a['sc109_p3']['le_24_5_count'], a['sc109_p3']['first_T'], a['sc109_p3']['longest_run']])
        for ph in ('p2', 'p3', 'p4'):
            for w in ('all', 'T_ge_4350'):
                x = v['p3']['stats']['%s_%s' % (ph, w)]
                y = a['sc109_p3'][ph][w]
                ck('ctl.%s.%s.%s' % (t, ph, w), x, [y['mean'], y['max']] if y.get('n') else None)
        fl, af = v['floor'], a['floor_173_p4']
        ck('ctl.%s.floor_names' % t, fl['names'], af['names'])
        ck('ctl.%s.floor_first_max' % t, [fl['first'][0] if fl['first'] else None, fl['first'][1] if fl['first'] else None, fl['max']],
           [af['first_T'], af['first_value'], af['max']])
        ck('ctl.%s.floor_fell' % t, [fl['fell'], fl['fell_after_hold']], [af['fell_T'], af['fell_T_after_hold']])
        ck('ctl.%s.bind1' % t, fl['bind1'], af['seed_binding_eq_1_count'])
        ck('ctl.%s.carried_updated' % t, [fl['carried'], fl['updated']], [af['groups_carried_sum'], af['groups_updated_sum']])
        ck('ctl.%s.pdisc1' % t, fl['pdisc1'], af['prior_discarded_eq_1_T'])
        ck('ctl.%s.k92' % t, [fl['k92'].get('k92_w', 0), fl['k92'].get('k92_hb', 0)], [af['k92_present']['k92_w'], af['k92_present']['k92_hb']])
        ck('ctl.%s.meter_changed' % t, v['meters']['changed'], a['meter_command_changed_decisions'])
        for road in ('FW_E', 'FW_W'):
            ck('ctl.%s.vsl.%s' % (t, road), [v['vsl'][road]['frac'], v['vsl'][road]['first'], v['vsl'][road]['longest']],
               [a['vsl_stats'][road]['frac_any_lt110'], a['vsl_stats'][road]['first_T'], a['vsl_stats'][road]['longest_run_decisions']])
        ck('ctl.%s.vsl_rows' % t, v['vsl_rows'], a['vsl_written_speed_rows'])
        ck('ctl.%s.status' % t, v['status'], a['selection']['selection_status'])
    ck('ctl.ratio.s%s' % s, VC['runs']['ratio_s%s' % s], AC['wall_ratio']['s' + s]['ratio'], 1e-9)
bad = [r for r in R if not r['ok']]
jd(dict(profile=prof, n=len(R), bad=len(bad), checks=R), OUT + '/v_compare.json')
for r in bad[:60]:
    print('BAD', r['check'], r['verify'], r['analysis'])
print('CHECKS %d/%d' % (len(R) - len(bad), len(R)))
print('ALL_OK' if not bad else 'NOT_OK')
