# -*- coding: utf-8 -*-
"""fo_report_extract.py - collect the numbers of FO_REPORT.md (Analyze step, 2026-10-28 KST). Read-only, light (no FZP).

Reads only the outputs of the declared final plan (fo_tables_out.json, fo_fwe_out.json), the fixed B outputs the table tool
already pinned (CW/rawcheck_b metrics), the FO stage outputs (metrics_out, dec_s*, walltimes, ramp_fc, runcheck), the fixed
FW_E reference line FWE_REF_C1.json (ce39344b...), and the FO .err lines 'could not be finished'. It does no new physics:
only copies, sums and differences, each marked in the output with how it was made.
  [copy]  value copied from a tool output (path + JSON key)
  [calc]  arithmetic on copied values (formula in 'how')
usage: python -B fo_report_extract.py <out.json>
"""
import hashlib, json, os, re, sys

SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
CW = SP + '/codex_handoff/work'
FA = SP + '/codex_handoff/fo/work/ana'
FD = SP + '/fwe_decomp'
FO_RUNS = 'D:/VISSIM_runs/20261028_codex_fo_v3c3'
SEEDS = (31, 41, 43)
FWE = ('RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484')
FWW = ('RM_C10480', 'RM_C10482', 'RM_C10646', 'RM_C10644')
PIN = {FD + '/out/FWE_REF_C1.json': 'ce39344bfbbe1b7c0b7d88ba129791b1772d551dad0ab74a0d8d2c36a90febc4',
       CW + '/rawcheck_b/s31/metrics_out.json': '74a067718717cd421ec5bde6587143d1da5557f6b564ac6b3c88976ca0973aaf',
       CW + '/rawcheck_b/s41/metrics_out.json': 'b9e41f9271b262bf755560ad9007fdf699a9da627cda5e84bcea4a4ea7240cb0',
       CW + '/rawcheck_b/s43/metrics_out.json': '9d3e4364d7027f1b6aa606f532b14cf0d06913626e869b8cd7e092f9004984d6',
       CW + '/rawcheck_b/dec_s31.json': 'c2dee5ed65374f747c69e2188875194571fe8d2ff2ebe38cd5da2c7c277dcb6a',
       CW + '/rawcheck_b/dec_s41.json': 'be75bcfc1aec1d096719ced443c66c45b3eb64351bd1e70875d58ed9d33c8209',
       CW + '/rawcheck_b/dec_s43.json': '067c863a3a9d5495c67eb60832c7c74028097a143d2a10f489b47becb8f41ce1'}
INPUTS = {}


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def jl(p):
    got = sha(p)
    if p in PIN and PIN[p] != got:
        raise SystemExit('PIN MISMATCH %s' % p)
    INPUTS[p] = got
    with open(p, encoding='utf-8-sig') as f:
        return json.load(f)


def r1(x, nd=1):
    return None if x is None else round(x + 0.0, nd)


def main(outp):
    T = jl(FA + '/fo_tables_out.json')
    F = jl(FA + '/fo_fwe_out.json')
    REF = jl(FD + '/out/FWE_REF_C1.json')['ref']
    out = {'tool': os.path.abspath(__file__).replace('\\', '/'), 'tool_sha256': sha(os.path.abspath(__file__)),
           'note': 'copy/calc only; seeds never averaged; veh.h unless noted', 'inputs': INPUTS}
    # ---------------------------------------------------------------- T1/T2 + B - NC3 [calc]
    tabs = {}
    for form in ('ours_9000', 'codex_8100'):
        t = T['tables'][form]
        labels = sorted({k.split('|')[0] for k in t})
        rows = {}
        for lab in labels:
            row = {}
            for s in SEEDS:
                fo, bf, fv = t['%s|FO-NC3|s%d' % (lab, s)], t['%s|B-FO|s%d' % (lab, s)], t['%s|FO-VA|s%d' % (lab, s)]
                bn = (bf + fo) if isinstance(bf, (int, float)) and isinstance(fo, (int, float)) else None
                share = (fo / bn) if (bn not in (None, 0) and isinstance(fo, (int, float))) else None
                row['s%d' % s] = {'FO-NC3': fo, 'B-FO': bf, 'FO-VA': fv, 'B-NC3_calc': bn, 'share_FO-NC3_of_B-NC3_calc': share}
            rows[lab] = row
        tabs[form] = rows
    out['tables'] = {'src': '[copy] fo_tables_out.json /tables; B-NC3_calc = (B-FO)+(FO-NC3) [calc]; share = (FO-NC3)/(B-NC3) [calc]',
                     'rows': tabs, 'daggers': T['daggers'], 'checks': T['checks'], 'stop': T['stop']}
    # ---------------------------------------------------------------- entry E / W (COMPARE_RULE_FO s5-9), codex form only
    ent = {}
    for s in SEEDS:
        fm = jl(CW + '/rawcheck_fo/s%d/metrics_out.json' % s)['codex_rule']
        bm = jl(CW + '/rawcheck_b/s%d/metrics_out.json' % s)['codex_rule']
        e = {}
        for k in ('onramps_E', 'onramps_W'):
            e[k] = {'FO_joint': fm['joint'][k], 'FO_nc': fm['nc'][k], 'B_joint': bm['joint'][k], 'B_nc': bm['nc'][k],
                    'FO-NC3': fm['joint'][k] - fm['nc'][k], 'B-FO': bm['joint'][k] - fm['joint'][k], 'B-NC3': bm['joint'][k] - bm['nc'][k],
                    'nc_check_absdiff': abs(fm['nc'][k] - bm['nc'][k]), 'nc_check_ok': abs(fm['nc'][k] - bm['nc'][k]) <= 1e-6}
        ent['s%d' % s] = e
    out['entry_EW'] = {'src': '[copy] metrics_out.json /codex_rule/{joint,nc}/onramps_E|W; differences [calc]', 'seeds': ent}
    # ---------------------------------------------------------------- FW_E rows
    fwe = {}
    for s in SEEDS:
        k = 'v3c3-s%d' % s
        rows = F['rows'][k]
        sec = {}
        for p in ('X-NC3', 'B-X', 'X-VA'):
            r = rows[p]
            z = {zn: {'bins900': v, 'sum_900_end_of_rounded_bins': r1(sum(v[1:]))} for zn, v in r['RF3'].items()}
            rf6 = {m: r['RF6'][m]['stock_d'] for m in r['RF6']}
            sec[p] = {'RF1': r['RF1'], 'RF2': r['RF2'], 'RF3': z, 'WITH': r['WITH'], 'RF5': r['RF5'],
                      'RF6_stock_d': rf6, 'RF6_stock_d_sum4_of_rounded': r1(sum(rf6.values())), 'RF6_full': r['RF6'],
                      'RF7': r['RF7'], 'RF8': r['RF8'], 'RF9': r['RF9'], 'RF10': r['RF10'], 'RF11': r['RF11']}
        pa = F['arms'][k]['per_arm']
        arms = {}
        for a in ('X', 'B', 'VA'):
            arms[a] = {'RF4': {m: ({x: v.get(x) for x in ('n_tight10', 'n_cycles', 'T_tight10', 'T_tight6', 'mean_green', 'green_hist')}
                                   if isinstance(v, dict) else v) for m, v in pa[a]['RF4'].items()},
                       'RF9': pa[a]['RF9'], 'RF10': pa[a]['RF10']}
        arms['NC3'] = {'RF4': pa['NC3']['RF4'], 'RF9': pa['NC3']['RF9']}
        rs = REF['seeds'][k]
        ref = {}
        for p in ('P-B', 'P-VA', 'P-BVA'):
            rr = rs[p]
            ref[p] = {'RF1': rr['RF1'], 'RF2': rr['RF2'], 'WITH': rr['WITH'], 'RF7': rr['RF7'],
                      'RF3_sum_900_end_of_rounded_bins': {zn: r1(sum(v[1:])) for zn, v in rr['RF3'].items()},
                      'RF5_10639': rr['RF5']['10639'] if p != 'P-BVA' else rr['RF5'].get('10639'),
                      'RF11': {x: rr['RF11'].get(x) for x in ('T_gain_a_s', 'T_gain_b_s', 'T_half_s', 'cum_d1_900_end')}}
        ref['levels'] = rs['levels']
        da = F['DA'][k]
        fwe[k] = {'pairs': sec, 'arms': arms, 'DA': da, 'ref_FWE_REF_C1': ref,
                  'pct_FO-NC3_d1_of_NC3_level_calc': r1(100.0 * rows['X-NC3']['RF1']['ours_9000'] / rs['levels']['NC3_d1_level']['ours_9000'], 2),
                  'pct_B-NC3_d1_of_NC3_level_read': REF['derived']['pct_d1_of_NC_level'].get('P-B|%s' % k)}
    out['fwe'] = {'src': '[copy] fo_fwe_out.json /rows,/arms,/DA (X = FO); [copy] FWE_REF_C1.json /ref/seeds; sums of rounded bins [calc]',
                  'stops': F['stops'], 'S6_ok': F.get('S6_ok'), 'tool_sha256': F['tool_sha256'], 'seeds': fwe,
                  'side_64cf_joint_minus_NC': {x: REF['side_64cf_joint_minus_NC'].get(x) for x in ('RF1', 'RF2', 'RF7', 'RF11')},
                  'ref_derived': REF['derived']}
    # ---------------------------------------------------------------- meters: commands (decision JSON) FO and B
    met = {}
    for s in SEEDS:
        for arm, p in (('FO', CW + '/rawcheck_fo/dec_s%d.json' % s), ('B', CW + '/rawcheck_b/dec_s%d.json' % s)):
            d = jl(p)
            per = {}
            for m in FWE + FWW:
                g = [x['rm_green'].get(m) for x in d if 900 <= x.get('t', 0) <= 8850 and isinstance(x.get('rm_green'), dict)]   # COMPARE_RULE_FO s5-3: T = 900-8,850
                g = [x for x in g if x is not None]
                hist = {}
                for x in g:
                    hist[str(x)] = hist.get(str(x), 0) + 1
                per[m] = {'n': len(g), 'n_green10': sum(1 for x in g if x == 10), 'n_green2': sum(1 for x in g if x == 2),
                          'min': min(g) if g else None, 'max': max(g) if g else None, 'hist': hist}
            vs = sorted({v for x in d if 900 <= x.get('t', 0) <= 8850 for v in (x.get('vsl_out') or [])})
            met['%s_s%d' % (arm, s)] = {'n_decisions_ge900': len(d), 'meters': per, 'vsl_out_values': vs,
                                        'T_range': [min(x['t'] for x in d), max(x['t'] for x in d)]}
    out['meter_commands'] = {'src': '[copy] dec_s<s>.json rm_green per decision (900 <= t <= 8850, 54 decisions); counts [calc]', 'runs': met}
    # ---------------------------------------------------------------- run checks (V1-V9) + readback FW_W
    rc = {}
    for s in SEEDS:
        r = jl(FA + '/runcheck_s%d.json' % s)
        v3 = r['report']['V3']
        rc['s%d' % s] = {'checks': r['checks'], 'usable': r['usable'], 'pass': r['pass'],
                         'V3_meter_rows': v3['meter_rows'], 'V3_bad': v3['requested_ne_readback_or_not_ok'],
                         'V3_per_meter': {m: {'cycles': v['cycles'], 'mismatch': v['mismatch'], 'cycles_green_lt10': v['cycles_green_lt10'],
                                              'readback_green_hist': v['readback_green_hist']} for m, v in v3['per_meter'].items()},
                         'V4': {x: r['report']['V4'].get(x) for x in ('signal_rows_T_ge_900', 'signal_rows_off_baseline', 'signal_sg_distinct_schedules',
                                                                      'd_not_written_sg_in_lsa', 'd_not_written_sg_with_difference', 'e_urban_readback_rows', 'e_urban_readback_bad')},
                         'V4_written_sg': r['report']['V4']['sg_native_run'],
                         'V5': r['report']['V5'], 'V1_holds': r['report']['V1']['holds_T_cause'], 'V9': r['report']['V9']}
    out['runcheck'] = {'src': '[copy] runcheck_s<s>.json', 'seeds': rc}
    # ---------------------------------------------------------------- walltimes, ramp forecast
    wt, rf = {}, {}
    for s in SEEDS:
        w = jl(CW + '/rawcheck_fo/s%d/walltimes_out.json' % s)['joint']
        wt['s%d' % s] = {x: w.get(x) for x in ('n_decisions_ge900', 'wall', 'budget_wall', 'held')}
        f = jl(CW + '/rawcheck_fo/s%d/ramp_fc_out.json' % s)
        lg = [x[1] for x in f]
        rf['s%d' % s] = {'n': len(lg), 'logged_min': r1(min(lg)), 'logged_max': r1(max(lg)), 'logged_mean_calc': r1(sum(lg) / len(lg)),
                         'T_first_last': [f[0][0], f[-1][0]]}
    out['walltimes'] = {'src': '[copy] walltimes_out.json /joint', 'seeds': wt}
    out['ramp_forecast'] = {'src': '[copy] ramp_fc_out.json col 1 (= forecast_ramp_arrival_total_vph); min/max/mean [calc]', 'seeds': rf}
    # ---------------------------------------------------------------- X5 helper: FO .err remaining vehicles
    er = {}
    for s in SEEDS:
        p = FO_RUNS + '/s%d/sdmpc/network/sdmpc31_sdmpc9000_s%d_001.err' % (s, s)
        INPUTS[p] = sha(p)
        rem = {}
        with open(p, 'rb') as f:
            for line in f:
                m = re.search(rb'Vehicle input (\d+):.*could not be finished completely \(remain: (\d+) vehicles\)', line)
                if m:
                    rem[m.group(1).decode()] = int(m.group(2))
        er['s%d' % s] = rem
    arr = T['checks']['X5_arrivals']
    x5 = {}
    nc_rem = {31: {'1099': 122}, 41: {'1087': 4}, 43: {}}   # [read] B_REPORT.md:56-58 (NC3 .err remain, same files B used)
    b_rem = {31: {'1099': 434}, 41: {'1087': 4, '1099': 296}, 43: {}}
    b_arr = {31: 66905, 41: 67304, 43: 67969}                # [read] B_REPORT.md:53
    for s in SEEDS:
        fo_t = arr['j1_s%d' % s] + sum(er['s%d' % s].values())
        nc_t = arr['nc3_s%d' % s] + sum(nc_rem[s].values())
        b_t = b_arr[s] + sum(b_rem[s].values())
        x5['s%d' % s] = {'first_seen_FO': arr['j1_s%d' % s], 'first_seen_NC3': arr['nc3_s%d' % s], 'first_seen_B_read': b_arr[s],
                         'err_remain_FO': er['s%d' % s], 'err_remain_NC3_read': nc_rem[s], 'err_remain_B_read': b_rem[s],
                         'first_plus_remain_FO_minus_NC3_calc': fo_t - nc_t, 'first_plus_remain_B_minus_NC3_calc': b_t - nc_t}
    out['X5'] = {'src': '[copy] fo_tables_out /checks/X5_arrivals; FO .err remain [run, regex]; NC3/B remain and B arrivals [read B_REPORT.md:53-58]',
                 'seeds': x5}
    with open(outp + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    os.replace(outp + '.tmp', outp)
    print('FO_REPORT_EXTRACT ok inputs=%d' % len(INPUTS))


if __name__ == '__main__':
    main(sys.argv[1])
