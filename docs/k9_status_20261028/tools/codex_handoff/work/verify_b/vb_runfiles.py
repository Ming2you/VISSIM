# vb_runfiles.py — B 런 파일(런 로그·명령 CSV·signal_readback·.err)을 새로 읽어 요약 (읽기만, 가벼움)
import csv, json, os, re, collections
V = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(V, 'out')
R = 'D:/VISSIM_runs/20261026_codex_b_v3c3'
MET = ['RM_C10480', 'RM_C10482', 'RM_C10646', 'RM_C10644', 'RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484']
res = {}
for s in ('31', '41', '43'):
    base = f'{R}/s{s}/sdmpc'
    o = {}
    # run log
    txt = open(f'{base}/runlog_sdmpc31_sdmpc9000_s{s}.txt', 'r', encoding='utf-8', errors='replace').read().splitlines()
    dec = []
    for ln in txt:
        m = re.match(r'CONTROLLER_DECISION sim_sec=(\d+) wall_sec=([\d.]+) result=exit=(-?\d+)', ln)
        if m:
            dec.append((int(m.group(1)), float(m.group(2)), int(m.group(3))))
    o['n_decision_lines'] = len(dec)
    o['exit_nonzero'] = sum(1 for d in dec if d[2] != 0)
    ctl = [d for d in dec if d[0] >= 900]
    w = [d[1] for d in ctl]
    o['n_ctl'] = len(ctl)
    o['wall_ctl_mean'] = round(sum(w) / len(w), 2)
    o['wall_ctl_max'] = max(w)
    o['wall_ctl_max_T'] = [d[0] for d in ctl if d[1] == max(w)]
    o['wall_T900'] = [d[1] for d in dec if d[0] == 900]
    o['wall_gt1500'] = sum(1 for x in w if x > 1500)
    o['warmup_T'] = [d[0] for d in dec if d[0] < 900]
    keys = ('DECISIONS_OK=', 'DECISIONS_FAILED=', 'DECISIONS_HELD_PREVIOUS=', 'DECISIONS_HELD_ON_EXCEPTION=', 'STAGE=', 'SIM_SEC=')
    o['summary_lines'] = [ln.strip() for ln in txt if ln.startswith(keys)]
    o['hold_attempt_lines'] = sum(1 for ln in txt if 'DECISION_HOLD_ATTEMPT' in ln)
    o['held_previous_lines'] = sum(1 for ln in txt if ln.startswith('DECISION_HELD_PREVIOUS'))
    # error txt files in decisions dir
    ddir = f'{base}/decisions_sdmpc31_sdmpc9000_s{s}'
    o['error_txt'] = len([f for f in os.listdir(ddir) if f.endswith('.error.txt')])
    # action CSV
    green = collections.defaultdict(dict)
    rate_ok = 0; rate_bad = 0
    vsl_vals = collections.Counter()
    with open(f'{base}/action_sdmpc31_sdmpc9000_s{s}.csv', newline='', encoding='utf-8', errors='replace') as fh:
        for row in csv.DictReader(fh):
            t = int(float(row['sim_sec']))
            if row['kind'] == 'ramp_meter':
                g = float(row['green_sec']); r = float(row['rate_vph'])
                if t >= 900:
                    green[row['id']][t] = g
                    if abs(r - 90.0 * g) < 1e-6: rate_ok += 1
                    else: rate_bad += 1
            elif row['kind'] == 'vsl':
                vsl_vals[row['speed_kph']] += 1
    o['csv_meter_rate_eq_green_x90'] = [rate_ok, rate_bad]
    o['csv_vsl_values'] = dict(vsl_vals)
    o['csv_meter_T'] = sorted({t for m in green for t in green[m]})[:2] + ['...', max(t for m in green for t in green[m]), len({t for m in green for t in green[m]})]
    dist = {}
    for m in MET:
        c54 = collections.Counter(int(g) if g == int(g) else g for t, g in green[m].items() if t <= 8850)
        c55 = collections.Counter(int(g) if g == int(g) else g for t, g in green[m].items())
        dist[m] = {'T900_8850': dict(sorted(c54.items())), 'T900_9000': dict(sorted(c55.items()))}
    o['csv_green_dist'] = dist
    # signal_readback: realized green per 10 s cycle from SG state timeline, vs commanded
    sc_of = {m: 9101 + i for i, m in enumerate(MET)}
    ev = collections.defaultdict(list)
    with open(f'{ddir}/signal_readback.csv', newline='', encoding='utf-8', errors='replace') as fh:
        rb_bad = 0; rb_n = 0
        for row in csv.DictReader(fh):
            sc = int(row['sc_no'])
            if 9101 <= sc <= 9108:
                rb_n += 1
                if row['requested_state'] != row['readback_state'] or row['ok'] != '1':
                    rb_bad += 1
                ev[sc].append((float(row['sim_sec']), row['readback_state']))
    o['readback_meter_rows'] = rb_n
    o['readback_meter_mismatch_or_notok'] = rb_bad
    cmp = {}
    for m in MET:
        sc = sc_of[m]
        e = sorted(ev[sc], key=lambda x: x[0])
        def state_at(t):
            st = None
            for tt, ss in e:
                if tt <= t: st = ss
                else: break
            return st
        Ts = sorted(green[m])
        n = 0; diff = 0; ex = []
        # step at 1 s resolution
        times = [x[0] for x in e]
        import bisect
        for T in Ts:
            if T >= 9000: continue
            cmd = green[m][T]
            for c in range(T, T + 150, 10):
                gs = 0
                for k in range(10):
                    t = c + k
                    i = bisect.bisect_right(times, t) - 1
                    st = e[i][1] if i >= 0 else None
                    if st == 'GREEN': gs += 1
                n += 1
                if abs(gs - cmd) > 0.5:
                    diff += 1
                    if len(ex) < 5: ex.append((c, cmd, gs))
        cmp[m] = {'cycles': n, 'cycles_realized_ne_cmd': diff, 'examples': ex}
    o['readback_vs_cmd'] = cmp
    # .err remaining
    errf = f'{base}/network/sdmpc31_sdmpc9000_s{s}_001.err'
    rem = re.findall(r'Vehicle input (\d+):[^\n]*?remain: (\d+) vehicles', open(errf, 'r', encoding='latin-1').read())
    o['err_remaining'] = rem
    ncf = f'D:/VISSIM_runs/20261001_v3c3/s{s}_v3c3nc/run/baseline_s{s}_v3c3nc_001.err'
    o['nc3_err_remaining'] = re.findall(r'Vehicle input (\d+):[^\n]*?remain: (\d+) vehicles', open(ncf, 'r', encoding='latin-1').read())
    res['s' + s] = o
json.dump(res, open(os.path.join(OUT, 'runfiles.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for k, o in res.items():
    print('==', k)
    for kk, vv in o.items():
        if kk in ('csv_green_dist', 'readback_vs_cmd'):
            continue
        print(' ', kk, vv)
    for m, dd in o['csv_green_dist'].items():
        print('  green', m, '54:', dd['T900_8850'], '| 55:', dd['T900_9000'])
    for m, dd in o['readback_vs_cmd'].items():
        print('  readback', m, dd)
