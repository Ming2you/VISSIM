# -*- coding: utf-8 -*-
"""fo_run_check.py r2 - FO run validity checks V1-V9 for one seed (PRE_FO r2 s7; 2026-10-27 KST, D-K9-113). Read-only.
r2 (review, before any FO data; r1 = fo_run_check_r1.py acfd805b...): V1 follows the B usability rule (holds on exception are
designed behaviour, PRE_B_CONCURRENT s7), V4 gains (d) never-written urban SGs stay native in the FO .lsa and (e) urban readback
requested == readback and ok == 1, new V9 (STOP) = a hold whose cause is the actuator-scope check. Nothing else changed.

V1 completion   wrapper end runner_exit 0; run log STAGE=SIM_DONE and SIM_SEC=9000; every failed decision was held on exception
                (DECISIONS_FAILED == DECISIONS_HELD_ON_EXCEPTION, both present) and action_*.error.txt count == that number
                (= B rule: holds are designed behaviour; reported with T and cause).
                (report: DECISIONS_OK / HELD_PREVIOUS / HELD_ON_EXCEPTION, decision count, hold lines with T and cause).
V2 provenance   seed (provenance) == seed; network sha 3de889f0...; tuning sha == FO config; RW_SIGNAL_OBSERVATION_CONFIG_SHA256 ==
                FO config; freeze pin == FRZ_FO FREEZE.json sha; hold env (hold_previous_on_exception, 1, 0).
V3 meters       signal_readback.csv meter rows: requested == readback and ok == 1 for all; per 10 s cycle (900..8990) and meter:
                readback GREEN seconds == commanded green_sec of the decision in force (0 mismatches over 8 x 810 cycles);
                report: green distribution per meter, cycles with green < 10.
V4 urban        (a) every decision T >= 900: 17 'signal' rows with p1-p4 and offset == the FO config baseline (|d| <= 1e-9);
                (b) the 'signal_sg' rows are the same at every decision T >= 900 (one schedule);
                (c) fog_sg_native.py 'run' rule: realized GREEN frames of every written urban SG over [901, 9000] == the native
                    program (B .lsa of the same seed, extended by its cycle) -> 0 differing frames (GREEN only);
                (d) r2: every urban SG in the FO .lsa that the FO run never wrote (not in its signal_readback.csv): GREEN frames
                    [901, 9000] of the FO .lsa == the native program (B .lsa [2, 899] extended by its cycle), 0 differing
                    frames (the .lsa is NOT used for written SGs: in the codex 64cf run it does not show COM-set states);
                (e) r2: every urban signal_readback.csv row (both stages): requested_state == readback_state and ok == 1.
V5 VSL          run action CSV 'vsl' rows all 110.0; vsl_readback.csv requested and readback all 110 and ok == 1.
V6 prefix       FO FZP rows <= 895.1 s: lf_sha_le_895_1 (vhr_scan_fo output) == B (same seed) and == NC3 reported per
                COMPARE_RULE_B s1 (a 0.1 s frame difference is marked, not removed); needs the scans (else 'not yet').
V7 warm-up      (report) action_000001..000750 CSV bytes == B (same seed); action_000001.json
                metadata.prediction_runtime_unavailable_reason == the solo runtime_setup.py text (declared marker).
V8 wall         (report) controller decision wall seconds (run log CONTROLLER_DECISION lines, T >= 900): n, mean, median,
                max, > 1,500 s, > 3,600 s.
V9 scope hold   r2 (STOP when false): no DECISION_HOLD_ATTEMPT cause carries an actuator-scope message of
                sdmpc_actuator_scope.py ('Inactive urban actuator changed', 'Actuator scope requires', 'Unknown or incomplete
                actuator scope', 'Fixed urban baseline must cover', 'Invalid fixed urban command').
usage: python -B fo_run_check.py <seed> <out.json> [--root <results root s<seed>>] [--launch-dir fo_launch] [--selftest-b]
  --selftest-b: point at the B run of the seed (b_launch) to exercise the parsers (V2/V4 are expected false there).
"""
import csv, glob, hashlib, importlib.util, json, os, re, statistics, sys

FW = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/fo/work'
CW = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work'
FRZ = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/fo/frozen/sdmpc31_a49981ff_202610271954'
FRZ_SHA = 'd7fa4db6c3ca854a3c6c7dfd352f97626d6f9ca9d0e5ea6f18e36fc779d37373'
FO_CFG = FRZ + '/diagnostics/b0_v3c3/config_fo_v3c3.json'
FO_CFG_SHA = '80e0abefdb25526374c97d8f7a6b45b9ad434db1f3499cec208985038ac249f3'
NET_SHA = '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e'
BR = 'D:/VISSIM_runs/20261026_codex_b_v3c3/s%d'
FOR = 'D:/VISSIM_runs/20261028_codex_fo_v3c3/s%d'
SG_TOOL = FW + '/gate/fog_sg_native.py'
METERS = ['RM_C10480', 'RM_C10482', 'RM_C10646', 'RM_C10644', 'RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484']
SOLO_MSG = 'Startup has no closed observation window; legal native baseline held without prediction'
SCOPE_MSGS = ('Inactive urban actuator changed', 'Actuator scope requires', 'Unknown or incomplete actuator scope',
              'Fixed urban baseline must cover', 'Invalid fixed urban command')


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def jl(p):
    return json.load(open(p, encoding='utf-8-sig'))


def txt(p):
    if not os.path.exists(p):
        return ''
    raw = open(p, 'rb').read()
    if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return raw.decode('utf-16')
    return raw.decode('utf-8-sig', errors='replace')


def main(argv):
    seed, out = int(argv[0]), argv[1]
    selftest = '--selftest-b' in argv
    root = (BR % seed) if selftest else (FOR % seed)
    launch = 'b_launch' if selftest else 'fo_launch'
    if '--root' in argv:
        root = argv[argv.index('--root') + 1]
    if '--launch-dir' in argv:
        launch = argv[argv.index('--launch-dir') + 1]
    name = 'sdmpc31_sdmpc9000_s%d' % seed
    sd = root + '/sdmpc'
    dec = sd + '/decisions_' + name
    res = {'seed': seed, 'root': root, 'selftest_b': selftest, 'checks': {}, 'report': {}}
    if sha(FO_CFG) != FO_CFG_SHA:
        raise SystemExit('FO config sha changed')
    base = jl(FO_CFG)['adapter']['sdmpc_actuator_scope']['baseline']
    # ---------------- V1
    ends = sorted(glob.glob(root + '/' + launch + '/wrapper_run*_try*_end.json'))
    end = jl(ends[-1]) if ends else {}
    rl = txt(sd + '/runlog_' + name + '.txt')
    summ = {k: (re.search(r'(?m)^%s=(\d+)' % k, rl).group(1) if re.search(r'(?m)^%s=(\d+)' % k, rl) else None)
            for k in ('DECISIONS_OK', 'DECISIONS_FAILED', 'DECISIONS_HELD_PREVIOUS', 'DECISIONS_HELD_ON_EXCEPTION')}
    errs = glob.glob(dec + '/action_*.error.txt')
    dlines = [(int(m.group(1)), float(m.group(2)), int(m.group(3))) for m in
              re.finditer(r'(?m)^CONTROLLER_DECISION sim_sec=(\d+) wall_sec=([\d.]+) result=exit=(-?\d+)', rl)]
    holds = [(int(m.group(1)), m.group(2).rstrip()[:200]) for m in re.finditer(r'(?m)^DECISION_HOLD_ATTEMPT sim_sec=(\d+) cause=(.*)$', rl)]
    res['report']['V1'] = {'wrapper_end': ends[-1] if ends else None, 'runner_exit': end.get('runner_exit'), 'summary': summ,
                           'error_txt': len(errs), 'decision_lines': len(dlines), 'exit_nonzero': sum(1 for d in dlines if d[2] != 0),
                           'hold_attempt_lines': rl.count('DECISION_HOLD_ATTEMPT'), 'held_previous_lines': len(re.findall(r'(?m)^DECISION_HELD_PREVIOUS', rl)),
                           'holds_T_cause': holds}
    # r2: the B usability rule (COMPARE_RULE_B s1, PRE_B_CONCURRENT s7): a completed run; failures only as holds on exception
    failed, held = summ['DECISIONS_FAILED'], summ['DECISIONS_HELD_ON_EXCEPTION']
    res['checks']['V1_completion'] = (end.get('runner_exit') == 0 and bool(re.search(r'(?m)^STAGE=SIM_DONE\r?$', rl))
                                      and bool(re.search(r'(?m)^SIM_SEC=9000\r?$', rl)) and failed is not None and held is not None
                                      and failed == held and len(errs) == int(held))
    # r2 V9: a hold caused by the actuator-scope check means the O2 combination itself broke at that state -> STOP
    scope_holds = [(t, c) for t, c in holds if any(s in c for s in SCOPE_MSGS)]
    scope_err = [os.path.basename(p) for p in errs if any(s in txt(p) for s in SCOPE_MSGS)]
    res['report']['V9'] = {'scope_holds': scope_holds, 'scope_error_txt': scope_err}
    res['checks']['V9_no_scope_hold'] = not scope_holds and not scope_err
    # ---------------- V2
    prov = jl(sd + '/run_provenance_' + name + '.json')
    env = prov.get('env', {})
    v2 = {'seed': prov.get('seed'), 'network_sha256': prov['files']['network']['sha256'], 'tuning_sha256': prov['files']['tuning']['sha256'],
          'rw_config_sha': env.get('RW_SIGNAL_OBSERVATION_CONFIG_SHA256'), 'freeze_sha256': (prov.get('observation') or {}).get('freeze', {}).get('sha256'),
          'hold_env': [env.get('RW_DECISION_ERROR_POLICY'), env.get('RW_DECISION_HOLD_PREVIOUS'), env.get('RW_DECISION_TIMEOUT_SEC')]}
    res['report']['V2'] = v2
    res['checks']['V2_provenance'] = (v2['seed'] == seed and v2['network_sha256'] == NET_SHA and v2['tuning_sha256'] == FO_CFG_SHA
                                      and v2['rw_config_sha'] == FO_CFG_SHA and v2['freeze_sha256'] == FRZ_SHA
                                      and v2['hold_env'] == ['hold_previous_on_exception', '1', '0'])
    # ---------------- run action CSV
    act = sd + '/action_' + name + '.csv'
    green = {m: {} for m in METERS}
    vsl_vals = {}
    sig_bad, sig_n, sg_sets = [], 0, {}
    with open(act, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            t = int(float(row['sim_sec']))
            k = row['kind']
            if k == 'ramp_meter' and t >= 900:
                green[row['id']][t] = float(row['green_sec'])
            elif k == 'vsl':
                vsl_vals[row['speed_kph']] = vsl_vals.get(row['speed_kph'], 0) + 1
            elif k == 'signal' and t >= 900:
                sig_n += 1
                sc = row['id']
                for i, p in enumerate(('p1_green', 'p2_green', 'p3_green', 'p4_green')):
                    want = base['green_times'].get('%s_p%d' % (sc, i + 1))
                    if want is None or abs(float(row[p]) - want) > 1e-9:
                        sig_bad.append((t, sc, p, row[p], want))
                if base['offsets'].get(sc) is None or abs(float(row['offset']) - base['offsets'][sc]) > 1e-9:
                    sig_bad.append((t, sc, 'offset', row['offset'], base['offsets'].get(sc)))
            elif k == 'signal_sg' and t >= 900:
                sg_sets.setdefault(t, []).append((row['id'], row['p1_green'], row['p2_green'], row['offset'], row['green_sec']))
    Ts = sorted(sg_sets)
    distinct = {tuple(sorted(v)) for v in sg_sets.values()}
    # ---------------- V3 meters (readback GREEN seconds per 10 s cycle vs command)
    import bisect
    sc_of = {m: 9101 + i for i, m in enumerate(METERS)}
    ev = {sc: [] for sc in sc_of.values()}
    rb_bad = rb_n = 0
    with open(dec + '/signal_readback.csv', newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            sc = int(row['sc_no'])
            if 9101 <= sc <= 9108:
                rb_n += 1
                if row['requested_state'] != row['readback_state'] or row['ok'] != '1':
                    rb_bad += 1
                ev[sc].append((float(row['sim_sec']), row['readback_state']))
    v3 = {}
    tot_mis = 0
    for m in METERS:
        e = sorted(ev[sc_of[m]], key=lambda x: x[0])
        times = [x[0] for x in e]
        Tm = sorted(green[m])
        n = mis = 0
        ex = []
        hist = {}
        for c in range(900, 9000, 10):
            i = bisect.bisect_right(Tm, c) - 1
            if i < 0:
                continue
            cmd = green[m][Tm[i]]
            gs = 0
            for k in range(10):
                j = bisect.bisect_right(times, c + k) - 1
                if j >= 0 and e[j][1] == 'GREEN':
                    gs += 1
            n += 1
            hist[gs] = hist.get(gs, 0) + 1
            if abs(gs - cmd) > 0.5:
                mis += 1
                if len(ex) < 5:
                    ex.append((c, cmd, gs))
        v3[m] = {'cycles': n, 'mismatch': mis, 'examples': ex, 'readback_green_hist': dict(sorted(hist.items())),
                 'cycles_green_lt10': sum(v for g, v in hist.items() if g < 10)}
        tot_mis += mis
    res['report']['V3'] = {'meter_rows': rb_n, 'requested_ne_readback_or_not_ok': rb_bad, 'per_meter': v3}
    res['checks']['V3_meters_commanded'] = rb_bad == 0 and tot_mis == 0 and all(v['cycles'] == 810 for v in v3.values())
    # ---------------- V4 urban
    spec = importlib.util.spec_from_file_location('fog_sg_native', SG_TOOL)
    sgm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sgm)
    tmp = out + '.v4c.json'
    sgm.mode_run(seed, dec, tmp)
    v4c = jl(tmp)
    # r2 V4(d): urban SGs never written by this run stay native in its own .lsa over [901, 9000] (native = B .lsa [2, 899])
    fo_lsa = sd + '/vissim_eval/' + name + '_001.lsa'
    b_lsa = sgm.b_inputs(seed)[1]
    written_fo = sgm.written_set(dec + '/signal_readback.csv')
    ev_fo, cyc_fo = sgm.read_lsa(fo_lsa) if os.path.exists(fo_lsa) else ({}, {})
    ev_b, cyc_b = sgm.read_lsa(b_lsa)
    early, late = list(range(2, 900)), list(range(901, 9001))
    nw_n = nw_bad_sg = nw_bad = 0
    nw_ex = {}
    for key in sorted(k for k in ev_fo if k[0] < 9000 and k not in written_fo):
        C, delta, ok = sgm.native_cycle(cyc_b.get(key[0], []))
        base = sgm.lsa_green_frames(ev_b.get(key, []), early)
        prog = {(t + delta) % C for t in base if t >= 2 + C} if ok else set()
        got = sgm.lsa_green_frames(ev_fo[key], late)
        d = [t for t in late if (t in got) != (((t + delta) % C) in prog)] if ok else late
        nw_n += 1
        if d:
            nw_bad_sg += 1
            nw_bad += len(d)
            if len(nw_ex) < 10:
                nw_ex['%d:%d' % key] = d[:3]
    # report: FO .lsa prefix [2, 899] == B .lsa prefix for every urban SG of either file (native part of the run)
    pre_diff = sorted('%d:%d' % k for k in set(ev_fo) | set(ev_b) if k[0] < 9000 and
                      sgm.lsa_green_frames(ev_fo.get(k, []), early) != sgm.lsa_green_frames(ev_b.get(k, []), early))
    # r2 V4(e): urban readback rows requested == readback and ok == 1 (both stages)
    ub_n = ub_bad = 0
    with open(dec + '/signal_readback.csv', newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            if int(row['sc_no']) < 9000:
                ub_n += 1
                if row['requested_state'] != row['readback_state'] or row['ok'] != '1':
                    ub_bad += 1
    v4d = os.path.exists(fo_lsa) and nw_n > 0 and nw_bad == 0
    v4e = ub_n > 0 and ub_bad == 0
    res['report']['V4'] = {'signal_rows_T_ge_900': sig_n, 'signal_rows_off_baseline': len(sig_bad), 'examples': sig_bad[:10],
                           'signal_sg_decisions': len(Ts), 'signal_sg_distinct_schedules': len(distinct),
                           'sg_native_run': {k: v4c.get(k) for k in ('written_sg', 'sg_with_difference', 'differing_frames_total', 'pass')},
                           'sg_tool_sha256': sha(SG_TOOL),
                           'd_not_written_sg_in_lsa': nw_n, 'd_not_written_sg_with_difference': nw_bad_sg, 'd_differing_frames': nw_bad,
                           'd_examples': nw_ex, 'd_fo_lsa': fo_lsa, 'd_fo_lsa_sha256': sha(fo_lsa) if os.path.exists(fo_lsa) else None,
                           'd_b_lsa_sha256': sha(b_lsa), 'report_lsa_prefix_2_899_sg_differing_fo_vs_b': pre_diff[:20],
                           'report_lsa_prefix_2_899_sg_differing_n': len(pre_diff),
                           'e_urban_readback_rows': ub_n, 'e_urban_readback_bad': ub_bad, 'd_pass': v4d, 'e_pass': v4e}
    res['checks']['V4_urban_baseline_only'] = (sig_n == 17 * len(Ts) and not sig_bad and len(distinct) == 1 and v4c.get('pass') is True
                                               and v4d and v4e)
    # ---------------- V5 VSL
    vb = vbad = 0
    vr = dec + '/vsl_readback.csv'
    if os.path.exists(vr):
        with open(vr, newline='', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                vb += 1
                if abs(float(row['requested_kph']) - 110.0) > 1e-9 or abs(float(row['readback_distribution_no']) - 110.0) > 1e-9 or row['ok'] != '1':
                    vbad += 1
    res['report']['V5'] = {'action_vsl_values': vsl_vals, 'vsl_readback_rows': vb, 'vsl_readback_not_110_or_not_ok': vbad}
    res['checks']['V5_vsl_110'] = set(vsl_vals) == {'110.0'} and vb > 0 and vbad == 0
    # ---------------- V6 prefix (needs the scans)
    fo_scan = CW + '/vhr_fo/scan_out/j1_s%d.json' % seed
    nc_scan = CW + '/vhr_fo/scan_out/nc3_s%d.json' % seed
    b_scan = CW + '/vhr_b/scan_out/j1_s%d.json' % seed
    if os.path.exists(fo_scan) and os.path.exists(nc_scan) and not selftest:
        f, n, b = jl(fo_scan), jl(nc_scan), jl(b_scan)
        res['report']['V6'] = {'fo_lf_sha_le_895_1': f['lf_sha_le_895_1'], 'nc3': n['lf_sha_le_895_1'], 'b': b['lf_sha_le_895_1'],
                               'fo_eq_nc3': f['lf_sha_le_895_1'] == n['lf_sha_le_895_1'], 'fo_eq_b': f['lf_sha_le_895_1'] == b['lf_sha_le_895_1'],
                               'fo_has_0p1_frame': f.get('has_0p1_frame'), 'fo_rows_0p1': f.get('rows_0p1')}
        res['checks']['V6_prefix_equals_B'] = res['report']['V6']['fo_eq_b']
    else:
        res['report']['V6'] = 'not yet (vhr_scan_fo outputs missing)' if not selftest else 'skipped in selftest'
    # ---------------- V7 warm-up (report)
    w = {}
    for T in (1, 150, 300, 450, 600, 750):
        a = dec + '/action_%06d.csv' % T
        bb = (BR % seed) + '/sdmpc/decisions_' + name + '/action_%06d.csv' % T
        w[str(T)] = (os.path.exists(a) and os.path.exists(bb) and sha(a) == sha(bb))
    j1 = dec + '/action_000001.json'
    msg = (jl(j1).get('metadata') or {}).get('prediction_runtime_unavailable_reason') if os.path.exists(j1) else None
    res['report']['V7'] = {'warmup_csv_equal_b': w, 't1_prediction_runtime_unavailable_reason': msg, 'solo_text': msg == SOLO_MSG}
    # ---------------- V8 wall (report)
    wall = [d[1] for d in dlines if d[0] >= 900]
    res['report']['V8'] = ({'n': len(wall), 'mean': round(statistics.mean(wall), 1), 'median': round(statistics.median(wall), 1),
                            'max': max(wall), 'gt1500': sum(1 for x in wall if x > 1500), 'gt3600': sum(1 for x in wall if x > 3600)} if wall else None)
    res['usable'] = res['checks']['V1_completion']
    res['pass'] = all(v for k, v in res['checks'].items())
    json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('RUNCHECK s%d usable=%s pass=%s %s' % (seed, res['usable'], res['pass'], json.dumps(res['checks'])))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
