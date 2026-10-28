# B run completion summary (2026-10-26, written before any B data). Read-only on run folders.
# usage: python -B b_run_summary.py <seed> <out.json>
# Collects: run log stages/summary counters/decision rows/holds, wrapper end/error, native_status, launch.log, WATCHDOG_PROGRESS,
# decision folder (error.txt last lines, decision_budget wall), action CSV meter/VSL command counts (sim_sec >= 900),
# .err files (B and NC3 same seed: line counts per type, top messages), and, if present, the pinned-tool outputs
# walltimes_out.json, dec_s<seed>.json, ramp_fc_out.json, rm_exec_out.json, fzp_firstdiff_s<seed>.json, vhr scan prefix sha.
import json, re, os, sys, glob, csv, statistics, collections
seed = int(sys.argv[1]); OUTF = sys.argv[2]
RES = 'D:/VISSIM_runs/20261026_codex_b_v3c3/s%d' % seed
SD = RES + '/sdmpc'
NAME = 'sdmpc31_sdmpc9000_s%d' % seed
DEC = SD + '/decisions_' + NAME
CW = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work'
NC3 = 'D:/VISSIM_runs/20261001_v3c3/s%d_v3c3nc/run' % seed
out = {'seed': seed, 'res': RES}


def rd(p, enc='utf-8'):
    with open(p, encoding=enc, errors='replace') as f:
        return f.read()


def jload(p):
    try:
        with open(p, encoding='utf-8-sig') as f:
            return json.load(f)
    except Exception as e:
        return {'_error': repr(e)}


# ---- run log ----
rl = SD + '/runlog_' + NAME + '.txt'
r = {'exists': os.path.exists(rl)}
if r['exists']:
    txt = rd(rl)
    lines = txt.splitlines()
    r['lines'] = len(lines)
    r['stage_lines'] = [l for l in lines if l.startswith('STAGE=')]
    r['startup_stage_last'] = ([l for l in lines if l.startswith('STARTUP_STAGE=')] or [None])[-1]
    for k in ('SIM_SEC', 'SIM_STEPS', 'DECISIONS_OK', 'DECISIONS_FAILED', 'DECISIONS_HELD_PREVIOUS', 'DECISIONS_HELD_ON_EXCEPTION', 'RUN_MODE'):
        m = [l for l in lines if l.startswith(k + '=')]
        r[k] = [x.split('=', 1)[1] for x in m]
    pat = re.compile(r'^CONTROLLER_DECISION sim_sec=(\d+) wall_sec=([0-9.]+) result=exit=(-?\d+)')
    rows = []
    for l in lines:
        m = pat.match(l)
        if m:
            rows.append((int(m.group(1)), float(m.group(2)), int(m.group(3))))
    r['decisions'] = rows
    holds = []
    for l in lines:
        if l.startswith('DECISION_HOLD_ATTEMPT'):
            t = re.search(r'sim_sec=(\d+)', l)
            ty = re.search(r'type=(\S+)', l)
            msg = re.search(r'message=(.*?) root_error=', l)
            holds.append({'t': int(t.group(1)) if t else None, 'type': ty.group(1) if ty else None,
                          'message': (msg.group(1) if msg else l)[:120]})
    r['hold_attempts'] = holds
    r['held_previous'] = [{'t': int(re.search(r'sim_sec=(\d+)', l).group(1)), 'source': os.path.basename(l.split('source=', 1)[1]) if 'source=' in l else None}
                          for l in lines if l.startswith('DECISION_HELD_PREVIOUS')]
    r['other_decision_lines'] = [l[:200] for l in lines if l.startswith('DECISION') and not l.startswith(('DECISION_HOLD_ATTEMPT', 'DECISION_HELD_PREVIOUS', 'DECISIONS_', 'DECISION_DIR'))][:50]
    r['error_like_lines'] = [l[:200] for l in lines if re.match(r'^(ERROR|FATAL|ABORT|STOP)', l)][:50]
    ctl = [x for x in rows if x[0] >= 900]
    w = [x[1] for x in ctl]
    if w:
        ws = sorted(w)
        r['wall_ge900'] = {'n': len(w), 'mean': round(statistics.mean(w), 1), 'median': round(statistics.median(w), 1),
                           'p90': ws[min(len(ws) - 1, int(0.9 * (len(ws) - 1) + 0.5))], 'min': min(w), 'max': max(w),
                           'max_at': [x[0] for x in ctl if x[1] == max(w)], 'gt360': sum(x > 360 for x in w),
                           'gt1500': sum(x > 1500 for x in w), 'gt1800': sum(x > 1800 for x in w), 'gt2400': sum(x > 2400 for x in w),
                           'sum': round(sum(w), 1), 'exit_nonzero': [(x[0], x[1], x[2]) for x in ctl if x[2] != 0]}
    pre = [x for x in rows if x[0] < 900]
    r['warmup_decisions'] = pre
    e = rl + '.err'
    r['runlog_err_bytes'] = os.path.getsize(e) if os.path.exists(e) else None
    r['runlog_err_text'] = rd(e)[:2000] if os.path.exists(e) and os.path.getsize(e) else ''
out['runlog'] = r

# ---- wrapper / status / watchdog ----
out['wrapper'] = {os.path.basename(p): jload(p) for p in sorted(glob.glob(RES + '/b_launch/wrapper_run*_end.json') + glob.glob(RES + '/b_launch/wrapper_run*_error.json') + glob.glob(RES + '/b_launch/wmi_launch_run*.json'))}
out['native_status'] = jload(RES + '/native_status.json') if os.path.exists(RES + '/native_status.json') else None
for nm in ('launch.log', 'WATCHDOG_PROGRESS.txt'):
    p = SD + '/' + nm
    out[nm] = rd(p).splitlines()[-40:] if os.path.exists(p) else None
out['stop_files'] = [p for p in (RES + '/STOP', os.path.dirname(RES) + '/STOP') if os.path.exists(p)]

# ---- decision folder ----
d = {}
if os.path.isdir(DEC):
    d['error_txt'] = {}
    for p in sorted(glob.glob(DEC + '/action_*.error.txt')):
        t = int(re.search(r'action_(\d+)\.error', p).group(1))
        ls = [x for x in rd(p).splitlines() if x.strip()]
        d['error_txt'][t] = ls[-1][:200] if ls else ''
    d['action_json_T'] = sorted(int(re.search(r'action_(\d+)\.json$', p).group(1)) for p in glob.glob(DEC + '/action_*.json') if re.search(r'action_(\d+)\.json$', p))
    bw = {}
    for p in glob.glob(DEC + '/action_*.decision_budget.json'):
        t = int(re.search(r'action_(\d+)\.decision_budget', p).group(1))
        bw[t] = jload(p).get('wall_sec')
    d['budget_wall'] = dict(sorted(bw.items()))
out['decisions_dir'] = d

# ---- action CSV commands (sim_sec >= 900) ----
ac = SD + '/action_' + NAME + '.csv'
a = {'exists': os.path.exists(ac)}
if a['exists']:
    meters = collections.defaultdict(collections.Counter)
    vsl = collections.Counter(); vsl_non110 = []
    kinds = collections.Counter(); per_t = collections.defaultdict(collections.Counter)
    with open(ac, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            t = float(row['sim_sec'])
            if t < 900:
                continue
            kinds[row['kind']] += 1
            per_t[int(t)][row['kind']] += 1
            if row['kind'] == 'ramp_meter':
                meters[row['id']][(row['rate_vph'], row['green_sec'])] += 1
            elif row['kind'] == 'vsl':
                vsl[row['speed_kph']] += 1
                if row['speed_kph'] not in ('110', '110.0'):
                    vsl_non110.append((int(t), row['id'], row['speed_kph']))
    a['kinds'] = dict(kinds)
    a['n_decision_times'] = len(per_t)
    a['decision_times'] = sorted(per_t)
    a['rows_per_kind_per_T'] = sorted({tuple(sorted(c.items())) for c in per_t.values()})
    a['meter_rate_green_counts'] = {k: {'%s/%s' % rg: n for rg, n in sorted(v.items())} for k, v in sorted(meters.items())}
    a['vsl_speed_counts'] = dict(vsl)
    a['vsl_non110'] = vsl_non110[:50]
out['action_csv'] = a


# ---- .err files ----
def err_summary(p):
    s = {'bytes': os.path.getsize(p)}
    try:
        txt = rd(p, 'utf-8')
    except Exception:
        txt = rd(p, 'latin-1')
    ls = [x for x in txt.splitlines() if x.strip()]
    s['lines'] = len(ls)
    types = collections.Counter(); msgs = collections.Counter()
    for x in ls:
        parts = [q.strip() for q in x.split('\t') if q.strip()]
        ty = parts[0] if parts and parts[0] in ('Warning', 'Error', 'Note', 'Fatal error') else 'other'
        types[ty] += 1
        body = parts[1] if len(parts) > 1 else (parts[0] if parts else '')
        if body.startswith('OBS150_ERR_FLUSH_PADDING'):
            body = 'OBS150_ERR_FLUSH_PADDING'
        msgs[(ty, re.sub(r'\d+(\.\d+)?', '#', body)[:90])] += 1
    s['types'] = dict(types)
    s['top'] = [[k[0], k[1], n] for k, n in msgs.most_common(12)]
    return s


out['err_b'] = {os.path.relpath(p, SD).replace('\\', '/'): err_summary(p) for p in sorted(glob.glob(SD + '/**/*.err', recursive=True))}
out['err_nc3'] = {os.path.relpath(p, NC3).replace('\\', '/'): err_summary(p) for p in sorted(glob.glob(NC3 + '/*.err'))}

# ---- pinned-tool outputs (if present) ----
p = CW + '/rawcheck_b/s%d/walltimes_out.json' % seed
if os.path.exists(p):
    wt = jload(p).get('joint', {})
    out['walltimes_tool'] = {k: v for k, v in wt.items() if k != 'per_decision'}
p = CW + '/rawcheck_b/dec_s%d.json' % seed
if os.path.exists(p):
    rows = jload(p)
    rows = [x for x in rows if 900 <= x['t'] <= 8850]
    rmo = collections.defaultdict(collections.Counter); rmg = collections.defaultdict(collections.Counter)
    vs = collections.Counter(); cs = collections.Counter(); ss = collections.Counter(); fc = []
    for x in rows:
        for k, v in (x.get('rm_out') or {}).items():
            rmo[k][str(v)] += 1
        for k, v in (x.get('rm_green') or {}).items():
            rmg[k][str(v)] += 1
        vs[json.dumps(x.get('vsl_out'))] += 1
        cs[str(x.get('controller_status'))] += 1
        ss[str(x.get('selection_status'))] += 1
        fc.append((x['t'], x.get('forecast_ramp_arrival_total_vph')))
    out['dec_tool'] = {'n': len(rows), 'rm_out_counts': {k: dict(v) for k, v in sorted(rmo.items())},
                       'rm_green_counts': {k: dict(v) for k, v in sorted(rmg.items())}, 'vsl_out_sets': dict(vs),
                       'controller_status': dict(cs), 'selection_status': dict(ss), 'forecast_ramp_arrival_total_vph': fc}
for nm, key in (('ramp_fc_out.json', 'ramp_fc_tool'), ('rm_exec_out.json', 'rm_exec_tool')):
    p = CW + '/rawcheck_b/s%d/%s' % (seed, nm)
    if os.path.exists(p):
        out[key] = jload(p)
p = CW + '/rawcheck_b/s%d/fzp_firstdiff_s%d.json' % (seed, seed)
if os.path.exists(p):
    fz = jload(p)
    out['fzp_firstdiff_tool'] = [{k: v for k, v in q.items() if k != 'blocks'} for q in fz.get('pairs', [])]
pj = CW + '/vhr_b/scan_out/j1_s%d.json' % seed; pn = CW + '/vhr_b/scan_out/nc3_s%d.json' % seed; pv = CW + '/vhr_b/scan_out/va_s%d.json' % seed
if os.path.exists(pj) and os.path.exists(pn):
    J, N = jload(pj), jload(pn)
    V = jload(pv) if os.path.exists(pv) else {}
    out['prefix_vhr'] = {'b_lf_sha_le_895_1': J.get('lf_sha_le_895_1'), 'nc3_lf_sha_le_895_1': N.get('lf_sha_le_895_1'),
                         'equal_b_nc3': J.get('lf_sha_le_895_1') == N.get('lf_sha_le_895_1'),
                         'b_rows_le_895_1': J.get('rows_le_895_1'), 'nc3_rows_le_895_1': N.get('rows_le_895_1'),
                         'va_lf_sha_le_895_1': V.get('lf_sha_le_895_1'), 'equal_b_va': J.get('lf_sha_le_895_1') == V.get('lf_sha_le_895_1'),
                         'b_first_frame_s': J.get('first_frame_s'), 'b_last_frame_s': J.get('last_frame_s'), 'b_has_0p1_frame': J.get('has_0p1_frame'),
                         'b_rows_all': J.get('rows_all'), 'b_file_sha256': J.get('file_sha256')}
with open(OUTF, 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=1, ensure_ascii=False, default=str)
print('written', OUTF)
