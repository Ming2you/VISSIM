# A1 full-run decision trace vs the codex joint record (rule COMPARE_RULE_A1_FULL.md, part A + part D).
# usage: python -B a1_trace.py <out.json> [--smoke]        read-only toward both run folders and the A0b outputs.
#   --smoke : the "A1" side is the codex record itself (tool self-test before A1 data; everything must come out equal).
# Per decision T (1, 150, ..., 750 and 900, 1050, ..., 8100):
#   runlog CONTROLLER_DECISION exit / wall_sec, hold lines (DECISION_HOLD_ATTEMPT cause, DECISION_HELD_PREVIOUS), ERROR= lines;
#   action_T.json metadata (controller_status, joint selection status/objectives); action_T.error.txt last line;
#   decision_budget wall_sec; R1 command CSV sha; R2 five joint_written fields; R3 scored_action_token;
#   command rows by lever (ramp_meter / vsl / signal / signal_sg) with per-meter values;
#   inputs: leaf diff of state_T.json and obs150/derived_T.json (classes clock / path / hex64 / meta / value);
#   A1 vs the A0b replay (T = 1050 ... 2550) R1 and differing rows.
import csv, hashlib, json, os, re, sys

BS = chr(92)
SMOKE = '--smoke' in sys.argv
NAME = 'sdmpc31_sdmpc8100_s29'
DEC = 'decisions_' + NAME
CXRUN = 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc'
A1RUN = CXRUN if SMOKE else 'D:/VISSIM_runs/20261025_codex_a1_s29/sdmpc'
CXDEC, A1DEC = CXRUN + '/' + DEC, A1RUN + '/' + DEC
A0B = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/out/a0b_hsw'
MAPS_CX = [('E:' + BS + 'VISSIM_runs' + BS + '20261012_adopted355_optimized_s29_8100', 'RUNROOT'),
           ('D:' + BS + 'VISSIM_runtime' + BS + '20261012_adopted355_vsl_three' + BS + 'frozen' + BS + 'sdmpc31_ca181e84_202610121132', 'FRZ')]
MAPS_A1 = MAPS_CX if SMOKE else [('D:' + BS + 'VISSIM_runs' + BS + '20261025_codex_a1_s29', 'RUNROOT'),
                                 ('D:' + BS + 'VISSIM_runtime' + BS + '20261025_codex_a1' + BS + 'frozen' + BS + 'sdmpc31_a49981ff_202610251820', 'FRZ')]
TIME_KEY = re.compile(r'(?i)(wall|cpu|elapsed|perf_counter|timestamp|_utc$|^started|^ended|seconds$|_sec_including_spawn$|^scalar_sec$|^scalar_export_sec$)')
HEX64 = re.compile(r'^[0-9a-f]{64}$')
PATHLIKE = re.compile(r'(?i)([a-z]:[' + re.escape(BS) + '/])|(' + re.escape(BS + BS) + ')')
META_KEYS = {'run_id', 'byte_start', 'byte_end', 'max_t_any'}      # fixed before A1 data (seen at T=900 as record-only leaves)
IDCOLS = ('kind', 'id', 'dsd_no', 'sc_no', 'link', 'lane')
K2 = ['seven_action_fields_sha256', 'ordered_physical_rows_sha256', 'expected_live_metadata_sha256', 'expected_csv_sha256', 'ordered_row_count']
TS = [1, 150, 300, 450, 600, 750] + list(range(900, 8101, 150))
A0B_TS = list(range(1050, 2551, 150))


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def load(p):
    return json.loads(open(p, 'rb').read().decode('utf-8-sig'))


def norm(s, maps):
    for a, b in maps:
        for v in (a, a.replace(BS, '/'), a.replace(BS, BS + BS)):
            s = s.replace(v, b).replace(v.lower(), b)
    return s


def flatten(x, p, out):
    if isinstance(x, dict):
        for k, v in x.items():
            flatten(v, p + '/' + str(k), out)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            flatten(v, p + '/' + str(i), out)
    else:
        out[p] = x
    return out


def leafdiff(a, b):
    fa = {norm(k, MAPS_A1): v for k, v in flatten(a, '', {}).items()}
    fb = {norm(k, MAPS_CX): v for k, v in flatten(b, '', {}).items()}
    res = {'leaves_a1': len(fa), 'leaves_codex': len(fb), 'n_only_a1': len(set(fa) - set(fb)), 'n_only_codex': len(set(fb) - set(fa)),
           'only_a1': sorted(set(fa) - set(fb))[:20], 'only_codex': sorted(set(fb) - set(fa))[:20],
           'same': 0, 'n_diff_clock': 0, 'n_diff_path': 0, 'n_diff_hex64': 0, 'n_diff_meta': 0, 'n_diff_value': 0,
           'value_numeric_max_abs': 0.0, 'value_numeric_n': 0, 'value_by_top': {}, 'value_examples': [], 'meta_examples': []}
    for k in sorted(set(fa) & set(fb)):
        va, vb = fa[k], fb[k]
        if isinstance(va, str):
            va = norm(va, MAPS_A1)
        if isinstance(vb, str):
            vb = norm(vb, MAPS_CX)
        if type(va) == type(vb) and repr(va) == repr(vb):
            res['same'] += 1
            continue
        last = k.rsplit('/', 1)[-1]
        if TIME_KEY.search(last):
            res['n_diff_clock'] += 1
        elif isinstance(va, str) and isinstance(vb, str) and (PATHLIKE.search(va) or PATHLIKE.search(vb)):
            res['n_diff_path'] += 1
        elif isinstance(va, str) and isinstance(vb, str) and HEX64.match(va) and HEX64.match(vb):
            res['n_diff_hex64'] += 1
        elif last in META_KEYS:
            res['n_diff_meta'] += 1
            if len(res['meta_examples']) < 10:
                res['meta_examples'].append([k, fa[k], fb[k]])
        else:
            res['n_diff_value'] += 1
            top = '/'.join(k.split('/')[:2])
            res['value_by_top'][top] = res['value_by_top'].get(top, 0) + 1
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)) and not isinstance(va, bool) and not isinstance(vb, bool):
                res['value_numeric_n'] += 1
                res['value_numeric_max_abs'] = max(res['value_numeric_max_abs'], abs(float(va) - float(vb)))
            if len(res['value_examples']) < 30:
                res['value_examples'].append([k, fa[k] if not isinstance(fa[k], str) else fa[k][:120], fb[k] if not isinstance(fb[k], str) else fb[k][:120]])
    return res


def fnum(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def rows(pa, pb):
    a = list(csv.DictReader(open(pa, encoding='utf-8-sig')))
    b = list(csv.DictReader(open(pb, encoding='utf-8-sig')))
    res = {'rows_a1': len(a), 'rows_codex': len(b), 'header_equal': (list(a[0].keys()) if a else []) == (list(b[0].keys()) if b else []),
           'identity_mismatch': 0, 'n_differing_rows': 0, 'by_kind': {}, 'max_abs_delta_by_kind_col': {},
           'signal_green_diff_ge_1s': 0, 'signal_green_diff_ge_0p01s': 0, 'signal_offset_diff_ge_1s': 0, 'sc_with_diff': [],
           'ramp_meter_rate_or_green_diff': 0, 'vsl_speed_diff': 0, 'nonnumeric_diffs': 0, 'metadata_only_rows': 0, 'examples': []}
    sc = set()
    for i, (x, y) in enumerate(zip(a, b)):
        if any(x.get(k) != y.get(k) for k in IDCOLS):
            res['identity_mismatch'] += 1
            continue
        cols = []
        for k in x:
            if x[k] == y[k]:
                continue
            dx, dy = fnum(x[k]), fnum(y[k])
            if dx is not None and dy is not None:
                d = dx - dy
                key = x['kind'] + ':' + k
                res['max_abs_delta_by_kind_col'][key] = round(max(res['max_abs_delta_by_kind_col'].get(key, 0.0), abs(d)), 6)
                if x['kind'] in ('signal', 'signal_sg') and k.endswith('_green'):
                    if abs(d) >= 1.0:
                        res['signal_green_diff_ge_1s'] += 1
                    if abs(d) >= 0.01:
                        res['signal_green_diff_ge_0p01s'] += 1
                if x['kind'] in ('signal', 'signal_sg') and k == 'offset' and abs(d) >= 1.0:
                    res['signal_offset_diff_ge_1s'] += 1
                if x['kind'] == 'ramp_meter' and k in ('rate_vph', 'green_sec'):
                    res['ramp_meter_rate_or_green_diff'] += 1
                if x['kind'] == 'vsl' and k == 'speed_kph':
                    res['vsl_speed_diff'] += 1
            else:
                res['nonnumeric_diffs'] += 1
            cols.append([k, x[k], y[k]])
        if cols:
            if all(c[0] == 'metadata' for c in cols):
                res['metadata_only_rows'] += 1
            res['n_differing_rows'] += 1
            res['by_kind'][x['kind']] = res['by_kind'].get(x['kind'], 0) + 1
            if x.get('sc_no'):
                sc.add(x['sc_no'])
            if len(res['examples']) < 25:
                res['examples'].append({'row': i + 1, **{k: x.get(k) for k in IDCOLS}, 'cols': cols})
    res['sc_with_diff'] = sorted(sc, key=lambda s: int(s) if s.isdigit() else 0)
    return res


def levers(p):
    """Per-lever view of one command CSV: meters (id -> rate, green), VSL distinct speeds, hold marker count."""
    out = {'meters': {}, 'vsl_speeds': [], 'hold_marker_rows': 0, 'rows': 0}
    vs = set()
    for r in csv.DictReader(open(p, encoding='utf-8-sig')):
        out['rows'] += 1
        if 'hold_previous_error=1' in (r.get('metadata') or ''):
            out['hold_marker_rows'] += 1
        if r['kind'] == 'ramp_meter':
            out['meters'][r['id']] = [fnum(r['rate_vph']), fnum(r['green_sec'])]
        elif r['kind'] == 'vsl':
            vs.add(fnum(r['speed_kph']))
    out['vsl_speeds'] = sorted(v for v in vs if v is not None)
    return out


PAT_DEC = re.compile(r'^CONTROLLER_DECISION sim_sec=(\d+) wall_sec=([0-9.]+) result=exit=(-?\d+)(.*)$')
PAT_SIM = re.compile(r'sim_sec=(\d+)')


def runlog(path):
    dec, hold_attempt, held, errors, summary = {}, {}, {}, {}, {}
    if not os.path.isfile(path):
        return {'missing': path}
    for line in open(path, encoding='utf-8', errors='replace'):
        line = line.rstrip('\r\n')
        m = PAT_DEC.match(line)
        if m:
            t = int(m.group(1))
            tail = m.group(4)
            dec[t] = {'wall_sec': float(m.group(2)), 'exit': int(m.group(3))}
            if int(m.group(3)) != 0:
                dec[t]['stderr_head'] = tail[:300]
            continue
        if line.startswith('DECISION_HOLD_ATTEMPT'):
            m = PAT_SIM.search(line)
            hold_attempt[int(m.group(1))] = line[:400]
        elif line.startswith('DECISION_HELD_PREVIOUS'):
            m = PAT_SIM.search(line)
            held[int(m.group(1))] = norm(line, MAPS_A1 if path.startswith(A1RUN) else MAPS_CX)[:300]
        elif line.startswith('ERROR='):
            m = PAT_SIM.search(line)
            errors.setdefault(int(m.group(1)) if m else -1, []).append(line[:300])
        else:
            for k in ('DECISIONS_OK', 'DECISIONS_FAILED', 'DECISIONS_HELD_PREVIOUS', 'STAGE', 'SIM_SEC', 'SIM_STEPS', 'OBSERVATION_FAILURES',
                      'SIGNAL_FAILURES', 'COM_FAILURES', 'ACTION_FORMAT_FAILURES', 'OBS150_BUNDLES'):
                if line.startswith(k + '='):
                    summary.setdefault(k, []).append(line.split('=', 1)[1])
    return {'decisions': dec, 'hold_attempt': hold_attempt, 'held_previous': held, 'errors': errors, 'summary': summary}


def action_meta(p):
    if not os.path.isfile(p):
        return None
    o = load(p)
    md = o.get('metadata') or {}
    j = md.get('joint_leader_selection') or {}
    hp = md.get('hold_previous') or {}
    return {'controller_status': md.get('controller_status'), 'selection_status': j.get('selection_status'),
            'selected_objective': j.get('selected_objective'), 'held_objective': j.get('held_objective'),
            'prediction_ttt_reduction': j.get('prediction_ttt_reduction'), 'hold_source_sim_sec': hp.get('source_sim_sec'),
            'controller_error': md.get('controller_error'), 'vsl_values': sorted(set((o.get('vsl') or {}).values())) if isinstance(o.get('vsl'), dict) else None}


def err_tail(p):
    if not os.path.isfile(p):
        return None
    lines = [x.rstrip() for x in open(p, encoding='utf-8', errors='replace') if x.strip()]
    return lines[-1][:300] if lines else ''


def safe(f, *a):
    try:
        return f(*a)
    except Exception as e:  # noqa: BLE001
        return {'error': repr(e)[:300]}


out = {'rule': 'COMPARE_RULE_A1_FULL.md', 'smoke': SMOKE, 'a1_dec': A1DEC, 'codex_dec': CXDEC, 'per_T': {}}
rl = {'a1': runlog(A1RUN + '/runlog_' + NAME + '.txt'), 'codex': runlog(CXRUN + '/runlog_' + NAME + '.txt')}
out['runlog_summary'] = {s: {k: v for k, v in rl[s].items() if k in ('summary', 'errors', 'missing')} for s in rl}
for t in TS:
    t6 = '%06d' % t
    r = {}
    for s, d in (('a1', A1DEC), ('codex', CXDEC)):
        x = {'runlog': rl[s].get('decisions', {}).get(t), 'hold_attempt': rl[s].get('hold_attempt', {}).get(t),
             'held_previous': rl[s].get('held_previous', {}).get(t), 'errors': rl[s].get('errors', {}).get(t)}
        csvp = d + '/action_' + t6 + '.csv'
        x['csv_exists'] = os.path.isfile(csvp)
        x['csv_sha'] = sha(csvp) if x['csv_exists'] else None
        x['levers'] = safe(levers, csvp) if x['csv_exists'] else None
        x['meta'] = safe(action_meta, d + '/action_' + t6 + '.json') if t >= 900 else None
        x['error_txt_last'] = err_tail(d + '/action_' + t6 + '.error.txt')
        bp = d + '/action_' + t6 + '.decision_budget.json'
        x['budget_wall_sec'] = safe(lambda p: load(p).get('wall_sec'), bp) if os.path.isfile(bp) else None
        jp = d + '/action_' + t6 + '.joint_written.json'
        x['joint_written'] = safe(lambda p: {k: load(p).get(k) for k in K2 + ['scored_action_token']}, jp) if os.path.isfile(jp) else None
        r[s] = x
    a, c = r['a1'], r['codex']
    r['R1_equal'] = (a['csv_sha'] is not None and a['csv_sha'] == c['csv_sha'])
    if isinstance(a['joint_written'], dict) and isinstance(c['joint_written'], dict):
        r['R2_equal'] = all(a['joint_written'].get(k) == c['joint_written'].get(k) for k in K2)
        r['R3_equal'] = a['joint_written'].get('scored_action_token') == c['joint_written'].get('scored_action_token')
    else:
        r['R2_equal'] = r['R3_equal'] = None
    if a['csv_exists'] and c['csv_exists']:
        r['rows'] = safe(rows, A1DEC + '/action_' + t6 + '.csv', CXDEC + '/action_' + t6 + '.csv')
    if t >= 900:
        r['inputs'] = {}
        for nm in ('state_' + t6 + '.json', 'obs150/derived_' + t6 + '.json'):
            pa, pc = A1DEC + '/' + nm, CXDEC + '/' + nm
            if os.path.isfile(pa) and os.path.isfile(pc):
                r['inputs'][nm] = safe(lambda u, v: leafdiff(load(u), load(v)), pa, pc)
            else:
                r['inputs'][nm] = {'missing': [p for p in (pa, pc) if not os.path.isfile(p)]}
        if isinstance(a['meta'], dict) and isinstance(c['meta'], dict):
            so, sc_ = a['meta'].get('selected_objective'), c['meta'].get('selected_objective')
            r['selected_objective_delta'] = (so - sc_) if isinstance(so, (int, float)) and isinstance(sc_, (int, float)) else None
    if t in A0B_TS:
        pz = A0B + '/T' + t6 + '/files/sdmpc/' + DEC + '/action_' + t6 + '.csv'
        if os.path.isfile(pz) and a['csv_exists']:
            r['a0b'] = {'a0b_csv_sha': sha(pz), 'R1_equal_a1_a0b': sha(pz) == a['csv_sha'], 'R1_equal_a0b_codex': sha(pz) == c['csv_sha'],
                        'rows_a1_vs_a0b': safe(rows, A1DEC + '/action_' + t6 + '.csv', pz)}
    out['per_T'][str(t)] = r
    print(t, 'R1', r['R1_equal'], 'rows', (r.get('rows') or {}).get('n_differing_rows'), 'bykind', (r.get('rows') or {}).get('by_kind'),
          'state_value', ((r.get('inputs') or {}).get('state_' + t6 + '.json') or {}).get('n_diff_value'), flush=True)
# summary
dec = [t for t in TS if t >= 900]
first_r1 = next((t for t in TS if out['per_T'][str(t)]['R1_equal'] is False), None)
first_state = next((t for t in dec if ((out['per_T'][str(t)].get('inputs') or {}).get('state_%06d.json' % t) or {}).get('n_diff_value', 0)), None)
first_derived = next((t for t in dec if ((out['per_T'][str(t)].get('inputs') or {}).get('obs150/derived_%06d.json' % t) or {}).get('n_diff_value', 0)), None)
growth = []
for t in dec:
    r = out['per_T'][str(t)]
    rw = r.get('rows') or {}
    mk = rw.get('max_abs_delta_by_kind_col') or {}
    st = (r.get('inputs') or {}).get('state_%06d.json' % t) or {}
    a, c = r['a1'], r['codex']
    growth.append({'T': t, 'R1_equal': r['R1_equal'], 'n_rows_diff': rw.get('n_differing_rows'), 'by_kind': rw.get('by_kind'),
                   'n_sc_diff': len(rw.get('sc_with_diff') or []), 'max_green_delta': max([v for k, v in mk.items() if k.endswith('_green')] or [0.0]),
                   'max_offset_delta': max([v for k, v in mk.items() if k.endswith(':offset')] or [0.0]),
                   'green_ge_1s': rw.get('signal_green_diff_ge_1s'), 'meter_diff': rw.get('ramp_meter_rate_or_green_diff'), 'vsl_diff': rw.get('vsl_speed_diff'),
                   'state_value_leaves': st.get('n_diff_value'), 'state_value_max_abs': st.get('value_numeric_max_abs'),
                   'a1_exit': (a['runlog'] or {}).get('exit'), 'codex_exit': (c['runlog'] or {}).get('exit'),
                   'a1_status': (a['meta'] or {}).get('controller_status') if isinstance(a['meta'], dict) else None,
                   'codex_status': (c['meta'] or {}).get('controller_status') if isinstance(c['meta'], dict) else None,
                   'a1_wall': (a['runlog'] or {}).get('wall_sec'), 'codex_wall': (c['runlog'] or {}).get('wall_sec'),
                   'a1_budget': a['budget_wall_sec'], 'codex_budget': c['budget_wall_sec'],
                   'sel_obj_delta': r.get('selected_objective_delta')})
wa = [g['a1_wall'] for g in growth if isinstance(g['a1_wall'], float)]
wc = [g['codex_wall'] for g in growth if isinstance(g['codex_wall'], float)]
out['summary'] = {'first_R1_diff_T': first_r1, 'first_state_value_diff_T': first_state, 'first_derived_value_diff_T': first_derived,
                  'n_decisions_ge900_a1_runlog': len(wa), 'n_decisions_ge900_codex_runlog': len(wc),
                  'n_R1_equal_ge900': sum(1 for g in growth if g['R1_equal']),
                  'a1_wall_sum': round(sum(wa), 2), 'codex_wall_sum': round(sum(wc), 2),
                  'a1_wall_max': max(wa) if wa else None, 'codex_wall_max': max(wc) if wc else None,
                  'a1_wall_gt1500': sum(1 for x in wa if x > 1500), 'a1_wall_gt1800': sum(1 for x in wa if x > 1800),
                  'a1_holds': sorted(rl['a1'].get('held_previous', {}).keys()), 'codex_holds': sorted(rl['codex'].get('held_previous', {}).keys()),
                  'a1_hold_attempts': {str(k): v for k, v in rl['a1'].get('hold_attempt', {}).items()},
                  'a1_nonzero_exit': sorted(t for t, v in rl['a1'].get('decisions', {}).items() if v['exit'] != 0),
                  'codex_nonzero_exit': sorted(t for t, v in rl['codex'].get('decisions', {}).items() if v['exit'] != 0)}
out['growth'] = growth
json.dump(out, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(out['summary'], ensure_ascii=False))
