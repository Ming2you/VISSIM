# vf_runfiles.py - VERIFY_FO run-file checks (2026-10-28 KST). New code, read only.
# No code from fo_run_check.py, fog_*, dec_extract_fo, rb_readback or vb_* is reused.
# usage: python -B vf_runfiles.py <out_json>
# per FO seed (seed taken from run provenance, paths built from the seed and then checked against provenance):
#   run log (decisions, exits, holds, summary keys), wrapper end, error files, scope-check strings
#   decision CSVs: urban signal rows vs the FO config baseline, signal_sg rows equal over decisions,
#                  ramp meter rows (rate = green x 90), VSL rows
#   decision JSONs: controller status, SDMPC coordinates kinds, green_times/offsets vs baseline, VSL values,
#                   meter green (diagnostics) vs CSV, policy sha, regional markers
#   signal_readback.csv: requested = readback, ok; meter GREEN seconds per 10 s cycle vs commanded green;
#                   urban SG GREEN seconds vs the native program taken from the same run's .lsa before 900 s
#                   (periodic extension), shifts 0/1/2 s; unwritten SGs: .lsa after 900 s vs the same extension
#   vsl_readback.csv: requested and read 110, ok
#   .lsa rows <= 900 s: FO vs B same seed (text equality)
import sys, os, json, csv, re, glob, hashlib, statistics
from collections import Counter, defaultdict

FO_ROOT = 'D:/VISSIM_runs/20261028_codex_fo_v3c3'
B_ROOT = 'D:/VISSIM_runs/20261026_codex_b_v3c3'
FRZ = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/fo/frozen/sdmpc31_a49981ff_202610271954'
CFG_FO = FRZ + '/diagnostics/b0_v3c3/config_fo_v3c3.json'
CFG_B = FRZ + '/diagnostics/b0_v3c3/config_b0_v3c3.json'
FREEZE_FO = 'd7fa4db6c3ca854a3c6c7dfd352f97626d6f9ca9d0e5ea6f18e36fc779d37373'
CFG_FO_SHA = '80e0abefdb25526374c97d8f7a6b45b9ad434db1f3499cec208985038ac249f3'
SEEDS = [31, 41, 43]
URBAN = [1, 5, 6, 7, 11, 12, 16, 101, 105, 107, 108, 109, 1001, 1002, 1003, 1004, 1005]
METER_SC = list(range(9101, 9109))
SCOPE_ERR = ['Inactive urban actuator changed', 'Actuator scope requires', 'Unknown or incomplete actuator scope',
             'Fixed urban baseline must cover', 'Invalid fixed urban command']
REGIONAL = {'regional_context', 'regional_prediction_blocks', 'regional_boundary', 'regional_mode', 'active_cost_owners',
            'input_isolation_qualified', 'input_context_schema', 'regional_startup_baseline', 'active_resources',
            'active_resource', 'region', 'regional_prediction_prototype', 'regional_context_required'}
LSA_ROW = re.compile(r'^\s*([0-9.]+);\s*([0-9.]+);\s*(\d+);\s*(\d+);\s*([A-Za-z/ ]+?)\s*;')


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for blk in iter(lambda: fh.read(1 << 22), b''):
            h.update(blk)
    return h.hexdigest()


def jload(path):
    with open(path, encoding='utf-8-sig') as fh:
        return json.load(fh)


def find_strings(obj, needles, path=''):
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            hits += find_strings(v, needles, path + '/' + str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits += find_strings(v, needles, path + '/' + str(i))
    elif isinstance(obj, str):
        for n in needles:
            if n in obj:
                hits.append((n, path))
    return hits


def walk_keys(obj, keys, found):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in keys:
                found.add(k)
            walk_keys(v, keys, found)
    elif isinstance(obj, list):
        for v in obj:
            walk_keys(v, keys, found)


def states_per_second(rows, t_from, t_to):
    # rows: list of (t, state) in file order (immediate rows only); state at second t = last row with time <= t
    rows = sorted(enumerate(rows), key=lambda x: (x[1][0], x[0]))
    out = [None] * (t_to - t_from)
    cur = None
    j = 0
    for t in range(t_from, t_to):
        while j < len(rows) and rows[j][1][0] <= t:
            cur = rows[j][1][1]
            j += 1
        out[t - t_from] = cur
    return out


def lsa_rows(path):
    rows = []
    texts = []
    frac = 0
    with open(path, encoding='latin-1') as fh:
        for line in fh:
            m = LSA_ROW.match(line)
            if not m:
                continue
            t = float(m.group(1))
            if abs(t - round(t)) > 1e-9:
                frac += 1
            rows.append((t, int(m.group(3)), int(m.group(4)), m.group(5).strip().lower()))
            texts.append((t, line.rstrip('\r\n')))
    return rows, texts, frac


def native_model(lsa, sc_list):
    # per (sc, sg): green indicator per integer second 1..900 from rows with t <= 900, period per SC
    by = defaultdict(list)
    for t, sc, sg, st in lsa:
        if sc in sc_list:
            by[(sc, sg)].append((t, st))
    pre = {}
    for key, rs in by.items():
        rr = [(t, st) for t, st in rs if t <= 900.0 + 1e-9]
        arr = [None] * 901
        cur = None
        j = 0
        rr.sort(key=lambda x: x[0])
        for tau in range(0, 901):
            while j < len(rr) and rr[j][0] <= tau + 1e-9:
                cur = rr[j][1]
                j += 1
            arr[tau] = cur
        pre[key] = arr
    period = {}
    for sc in sc_list:
        keys = [k for k in pre if k[0] == sc]
        if not keys:
            continue
        chosen = None
        for C in range(20, 301):
            ok = True
            for k in keys:
                a = pre[k]
                for tau in range(max(300, C + 1), 901):
                    if (a[tau] == 'green') != (a[tau - C] == 'green'):
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                chosen = C
                break
        period[sc] = chosen
    return by, pre, period


def native_green(pre, period, key, tau):
    a = pre[key]
    if tau <= 900:
        return a[tau] == 'green'
    C = period[key[0]]
    k = -(-(tau - 900) // C)
    return a[tau - k * C] == 'green'


def check_seed(s, cfg_base):
    base = '%s/s%d/sdmpc' % (FO_ROOT, s)
    name = 'sdmpc31_sdmpc9000_s%d' % s
    P = {'prov': '%s/run_provenance_%s.json' % (base, name), 'runlog': '%s/runlog_%s.txt' % (base, name),
         'dec': '%s/decisions_%s' % (base, name), 'lsa': '%s/vissim_eval/%s_001.lsa' % (base, name),
         'wrapper_end': '%s/s%d/fo_launch/wrapper_run1_try1_end.json' % (FO_ROOT, s),
         'b_lsa': '%s/s%d/sdmpc/vissim_eval/%s_001.lsa' % (B_ROOT, s, name),
         'b_prov': '%s/s%d/sdmpc/run_provenance_%s.json' % (B_ROOT, s, name)}
    R = {'paths': P}
    prov = jload(P['prov'])
    R['prov_seed'] = prov.get('seed')
    R['b_prov_seed'] = jload(P['b_prov']).get('seed')
    hits = find_strings(prov, [CFG_FO_SHA, FREEZE_FO, '729640af', '558de2c1'])
    R['prov_hits'] = {n: sorted(set(p for nn, p in hits if nn == n)) for n in [CFG_FO_SHA, FREEZE_FO, '729640af', '558de2c1']}
    # run log
    lines = open(P['runlog'], encoding='utf-8', errors='replace').read().splitlines()
    dec = []
    for l in lines:
        if l.startswith('CONTROLLER_DECISION '):
            m = re.search(r'sim_sec=(\d+) wall_sec=([0-9.]+) result=exit=(-?\d+)', l)
            dec.append((int(m.group(1)), float(m.group(2)), int(m.group(3))))
    R['n_decisions'] = len(dec)
    R['n_exit_nonzero'] = sum(1 for d in dec if d[2] != 0)
    R['decision_times'] = [d[0] for d in dec]
    w9 = [d[1] for d in dec if d[0] >= 900]
    R['wall_ge900'] = {'n': len(w9), 'mean': statistics.mean(w9), 'median': statistics.median(w9), 'max': max(w9),
                       'max_at': [d[0] for d in dec if d[0] >= 900 and d[1] == max(w9)],
                       'n_gt1500': sum(1 for x in w9 if x > 1500), 'n_gt3600': sum(1 for x in w9 if x > 3600)}
    summ = {}
    for key in ['DECISIONS_OK', 'DECISIONS_FAILED', 'DECISIONS_HELD_PREVIOUS', 'DECISIONS_HELD_ON_EXCEPTION', 'SIM_SEC',
                'SIGNAL_FAILURES', 'SIGNAL_WRITE_ATTEMPTS', 'SIGNAL_READBACK_OK', 'SIGNAL_PERSISTENCE_CHECKS',
                'SIGNAL_PERSISTENCE_OK', 'SIGNAL_SG_PLAN_ROWS', 'SIGNAL_MIDBLOCK_PLAN_SKIPS']:
        vals = [l.split('=', 1)[1] for l in lines if l.startswith(key + '=')]
        summ[key] = vals
    R['summary'] = summ
    R['stage_sim_done'] = any(l.strip() == 'STAGE=SIM_DONE' for l in lines)
    R['n_hold_attempt_lines'] = sum(1 for l in lines if 'DECISION_HOLD_ATTEMPT' in l)
    R['n_held_previous_lines'] = sum(1 for l in lines if 'DECISION_HELD_PREVIOUS' in l and not l.startswith('DECISIONS_'))
    R['scope_err_in_runlog'] = {e: sum(1 for l in lines if e in l) for e in SCOPE_ERR}
    errs = sorted(glob.glob(P['dec'] + '/action_*.error*'))
    R['n_error_files'] = len(errs)
    R['wrapper_end'] = jload(P['wrapper_end'])
    # decision CSV + JSON
    csvs = sorted(glob.glob(P['dec'] + '/action_[0-9][0-9][0-9][0-9][0-9][0-9].csv'))
    R['n_csv'] = len(csvs)
    cmd_green = {}  # (T, sc_no) -> green
    sig_bad = {'ge900': 0, 'lt900': 0}
    sig_rows = {'ge900': 0, 'lt900': 0}
    sgsets = {}
    rm_rate_bad = 0
    rm_rows = 0
    vsl_rows = 0
    vsl_bad = []
    meter_ids = {}
    sg_scs = set()
    for f in csvs:
        T = int(os.path.basename(f)[7:13])
        tag = 'ge900' if T >= 900 else 'lt900'
        sgset = []
        with open(f, encoding='utf-8-sig', newline='') as fh:
            for row in csv.DictReader(fh):
                k = row['kind']
                if k == 'signal':
                    sig_rows[tag] += 1
                    sc = row['id']
                    for i in range(1, 5):
                        v = float(row['p%d_green' % i])
                        if abs(v - cfg_base['green_times']['%s_p%d' % (sc, i)]) > 1e-9:
                            sig_bad[tag] += 1
                    if abs(float(row['offset']) - cfg_base['offsets'][sc]) > 1e-9:
                        sig_bad[tag] += 1
                elif k == 'signal_sg':
                    sgset.append(tuple(row[c] for c in ['id', 'dsd_no', 'sc_no', 'link', 'lane', 'speed_kph', 'p1_green',
                                                         'p2_green', 'p3_green', 'p4_green', 'offset', 'rate_vph', 'green_sec']))
                    sg_scs.add(int(row['sc_no']))
                elif k == 'ramp_meter':
                    rm_rows += 1
                    g = float(row['green_sec'])
                    r = float(row['rate_vph'])
                    if abs(r - 90.0 * g) > 1e-6:
                        rm_rate_bad += 1
                    cmd_green[(T, int(row['sc_no']))] = g
                    meter_ids[int(row['sc_no'])] = row['id']
                elif k == 'vsl':
                    vsl_rows += 1
                    if abs(float(row['speed_kph']) - 110.0) > 1e-9:
                        vsl_bad.append((T, row['id'], row['speed_kph']))
        if T >= 900:
            sgsets[T] = tuple(sorted(sgset))
    R['csv_signal_rows'] = sig_rows
    R['csv_signal_mismatch_vs_baseline'] = sig_bad
    first_set = sgsets[min(sgsets)]
    R['csv_signal_sg'] = {'n_decisions': len(sgsets), 'rows_first': len(first_set),
                          'all_equal': all(v == first_set for v in sgsets.values()), 'scs': sorted(sg_scs),
                          'scs_outside_urban17': sorted(x for x in sg_scs if x not in URBAN),
                          'distinct_sg_keys': len(set((r[2], r[1]) for r in first_set))}
    R['csv_ramp_rows'] = rm_rows
    R['csv_ramp_rate_ne_green_x90'] = rm_rate_bad
    R['csv_vsl_rows'] = vsl_rows
    R['csv_vsl_not110'] = vsl_bad[:20]
    R['csv_vsl_not110_n'] = len(vsl_bad)
    R['meter_ids'] = {str(k): v for k, v in sorted(meter_ids.items())}
    jsons = sorted(glob.glob(P['dec'] + '/action_[0-9][0-9][0-9][0-9][0-9][0-9].json'))
    R['n_json'] = len(jsons)
    jr = {'status': Counter(), 'coord_kinds': Counter(), 'coord_n': Counter(), 'gt_bad': 0, 'off_bad': 0,
          'gt_n': Counter(), 'vsl_not110': 0, 'vsl_n': Counter(), 'rwg_vs_csv_bad': 0, 'policy': Counter(),
          'regional_keys': set(), 'warm_gt_bad': 0, 'warm_off_bad': 0, 'selection': Counter()}
    for f in jsons:
        T = int(os.path.basename(f)[7:13])
        d = jload(f)
        meta = d.get('metadata', {})
        jr['status'][str(meta.get('controller_status'))] += 1
        gt = d.get('green_times', {})
        of = d.get('offsets', {})
        bad_g = sum(1 for k, v in cfg_base['green_times'].items() if abs(float(gt.get(k, float('nan'))) - v) > 1e-9 or k not in gt)
        bad_o = sum(1 for k, v in cfg_base['offsets'].items() if abs(float(of.get(k, float('nan'))) - v) > 1e-9 or k not in of)
        if T >= 900:
            jls = meta.get('joint_leader_selection', {})
            co = jls.get('coordinates', [])
            jr['coord_n'][len(co)] += 1
            for c in co:
                jr['coord_kinds'][c.get('kind')] += 1
            jr['selection'][str(jls.get('selection_status'))] += 1
            jr['gt_bad'] += bad_g
            jr['off_bad'] += bad_o
            jr['gt_n'][(len(gt), len(of))] += 1
            vv = d.get('vsl', {})
            jr['vsl_n'][len(vv)] += 1
            jr['vsl_not110'] += sum(1 for v in vv.values() if abs(float(v) - 110.0) > 1e-9)
            diag = d.get('diagnostics', {})
            for scno, mid in meter_ids.items():
                g = diag.get('rw_meter_green_' + mid)
                if g is None or abs(float(g) - cmd_green[(T, scno)]) > 1e-9:
                    jr['rwg_vs_csv_bad'] += 1
            st = meta.get('sdmpc_state')
            jr['policy'][st.get('policy_sha256') if isinstance(st, dict) else None] += 1
            walk_keys(d, REGIONAL, jr['regional_keys'])
        else:
            jr['warm_gt_bad'] += bad_g
            jr['warm_off_bad'] += bad_o
    for k in list(jr):
        if isinstance(jr[k], Counter):
            jr[k] = {str(a): b for a, b in jr[k].items()}
        elif isinstance(jr[k], set):
            jr[k] = sorted(jr[k])
    R['json'] = jr
    # signal readback
    rb_total = Counter()
    rb_bad = Counter()
    imm = defaultdict(list)
    with open(P['dec'] + '/signal_readback.csv', encoding='utf-8-sig', newline='') as fh:
        for row in csv.DictReader(fh):
            sc = int(row['sc_no'])
            grp = 'meter' if sc in METER_SC else ('urban17' if sc in URBAN else 'other')
            rb_total[(grp, row['stage'])] += 1
            if row['requested_state'] != row['readback_state'] or row['ok'] != '1':
                rb_bad[(grp, row['stage'])] += 1
            if row['stage'] == 'immediate':
                imm[(sc, int(row['sg_no']))].append((int(row['sim_sec']), row['requested_state']))
    R['readback_rows'] = {'%s|%s' % k: v for k, v in rb_total.items()}
    R['readback_bad'] = {'%s|%s' % k: v for k, v in rb_bad.items()}
    # meters per 10 s cycle
    mres = {}
    for scno in METER_SC:
        key = (scno, 1)
        st = states_per_second(imm.get(key, []), 900, 9000)
        greens = []
        mism = []
        for k in range(810):
            t0 = 900 + 10 * k
            g = sum(1 for x in st[t0 - 900:t0 - 900 + 10] if x == 'GREEN')
            Td = 900 + 150 * ((10 * k) // 150)
            c = cmd_green[(Td, scno)]
            greens.append(g)
            if abs(g - c) > 1e-9:
                mism.append((t0, g, c))
        lt10 = [900 + 10 * k for k, g in enumerate(greens) if g < 10]
        le6 = [900 + 10 * k for k, g in enumerate(greens) if g <= 6]
        mres[meter_ids.get(scno, str(scno))] = {
            'sc': scno, 'n_cycles': len(greens), 'mismatch_n': len(mism), 'mismatch_first': mism[:5],
            'n_green_lt10': len(lt10), 'T_tight10': lt10[0] if lt10 else None, 'T_tight6': le6[0] if le6 else None,
            'green_hist': {str(a): b for a, b in sorted(Counter(greens).items())},
            'mean_green': sum(greens) / len(greens), 'none_seconds': sum(1 for x in st if x is None)}
    R['meters'] = mres
    # urban SG: readback GREEN vs native (.lsa <= 900 s periodic extension)
    lsa, lsa_text, frac = lsa_rows(P['lsa'])
    R['lsa_rows'] = len(lsa)
    R['lsa_fractional_times'] = frac
    by, pre, period = native_model(lsa, URBAN + [s_ for s_ in set(r[1] for r in lsa) if s_ not in URBAN and s_ not in METER_SC])
    R['periods_urban17'] = {str(sc): period.get(sc) for sc in URBAN}
    written = sorted(k for k in imm if k[0] in URBAN)
    R['urban_written_sg'] = len(written)
    R['urban_written_sg_with_green'] = sum(1 for k in written if any(st_ == 'GREEN' for _, st_ in imm[k]))
    R['urban_written_sg_not_in_lsa'] = [list(k) for k in written if k not in pre]
    shift_mis = {}
    per_sg_mis = {}
    rb_none = 0
    for shift in (0, 1, 2):
        tot = 0
        nsg = 0
        for k in written:
            if k not in pre:
                continue
            st = states_per_second(imm[k], 900, 9000)
            mis = 0
            for i, x in enumerate(st):
                t = 900 + i
                if x is None:
                    if shift == 1:
                        rb_none += 1
                    continue
                tau = t + shift
                if tau > 9000:
                    continue
                if (x == 'GREEN') != native_green(pre, period, k, tau):
                    mis += 1
            tot += mis
            if mis:
                nsg += 1
            if shift == 1 and mis:
                per_sg_mis['%d_%d' % k] = mis
        shift_mis[str(shift)] = {'frames': tot, 'sg_with_diff': nsg}
    R['urban_readback_vs_native'] = shift_mis
    R['urban_readback_vs_native_shift1_per_sg'] = per_sg_mis
    R['urban_readback_none_seconds'] = rb_none
    R['urban_written_lsa_rows_after900'] = sum(1 for t, sc, sg, st_ in lsa if (sc, sg) in set(written) and t > 900.0 + 1e-9)
    # unwritten SGs: .lsa after 900 vs extension
    wset = set(k for k in imm)
    unw = sorted(k for k in pre if k not in wset and k[0] not in METER_SC)
    tot = 0
    nsg = 0
    unw_urban = 0
    unw_with_rows_after = 0
    for k in unw:
        rs = sorted(by[k], key=lambda x: x[0])
        if any(t > 900 for t, _ in rs):
            unw_with_rows_after += 1
        if k[0] in URBAN:
            unw_urban += 1
        if period.get(k[0]) is None:
            continue
        cur = None
        j = 0
        mis = 0
        for tau in range(0, 9001):
            while j < len(rs) and rs[j][0] <= tau + 1e-9:
                cur = rs[j][1]
                j += 1
            if tau >= 901 and (cur == 'green') != native_green(pre, period, k, tau):
                mis += 1
        tot += mis
        if mis:
            nsg += 1
    R['unwritten_sg'] = {'n': len(unw), 'n_in_urban17': unw_urban, 'n_with_rows_after900': unw_with_rows_after,
                         'frames_diff': tot, 'sg_with_diff': nsg,
                         'sc_without_period': sorted(str(sc) for sc in set(k[0] for k in unw) if period.get(sc) is None)}
    # FO vs B .lsa rows <= 900 s
    blsa, blsa_text, _ = lsa_rows(P['b_lsa'])
    fo_pre = [x for t, x in lsa_text if t <= 900.0 + 1e-9]
    b_pre = [x for t, x in blsa_text if t <= 900.0 + 1e-9]
    R['lsa_pre900_fo_eq_b'] = {'equal': fo_pre == b_pre, 'n_fo': len(fo_pre), 'n_b': len(b_pre)}
    # VSL readback
    vb = Counter()
    vbad = 0
    with open(P['dec'] + '/vsl_readback.csv', encoding='utf-8-sig', newline='') as fh:
        for row in csv.DictReader(fh):
            vb[row['stage']] += 1
            if abs(float(row['requested_kph']) - 110.0) > 1e-9 or abs(float(row['readback_distribution_no']) - 110.0) > 1e-9 or row['ok'] != '1':
                vbad += 1
    R['vsl_readback'] = {'rows': dict(vb), 'bad': vbad}
    return R


def main():
    out = sys.argv[1]
    cfg = jload(CFG_FO)
    cfgb = jload(CFG_B)
    ad = cfg['adapter']
    scope = ad['sdmpc_actuator_scope']
    base = {'green_times': {k: float(v) for k, v in scope['baseline']['green_times'].items()},
            'offsets': {k: float(v) for k, v in scope['baseline']['offsets'].items()}}
    res = {'cfg_fo_sha256': sha(CFG_FO), 'cfg_b_sha256': sha(CFG_B), 'scope_mode': scope.get('mode'),
           'n_baseline_green': len(base['green_times']), 'n_baseline_offsets': len(base['offsets']),
           'information_scope_in_fo': 'sdmpc_information_scope' in ad,
           'fixed_vsl_fo': ad.get('sdmpc_fixed_vsl'), 'fixed_vsl_b': cfgb['adapter'].get('sdmpc_fixed_vsl'),
           'actuator_scope_in_b': 'sdmpc_actuator_scope' in cfgb['adapter'], 'seeds': {}}
    for s in SEEDS:
        res['seeds'][str(s)] = check_seed(s, base)
        print('VF_RUNFILES_SEED_DONE', s, flush=True)
    tmp = out + '.tmp' + str(os.getpid())
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(res, fh, indent=1, default=str)
    os.replace(tmp, out)
    print('VF_RUNFILES_DONE', flush=True)


if __name__ == '__main__':
    main()
