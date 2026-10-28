# Gate 1 summary (descriptive). Fixed before the replay data exist (GATE1_RULE.md). Derived from work/b0/b0_replay_summary.py
# (b20edbf4...) with the collect path fixed (files/<decision folder>, not files/run/...) and more fields.
# Per replay: exit, exception (stderr Traceback / DECISION_FAILED / .error.txt), process wall (wrapper stopwatch),
# decision_budget wall/cpu/output_completed, progress lines, CPU load mean, action CSV rows by kind + sha, VSL speeds,
# meter rows (rate_vph, green_sec), signal rows (p1..p4 greens, offset), ramp-arrival forecast metadata (total, old group
# keys, any RM_C arrival key), selection scalars (joint.json), hold/error files, decision_wall_sec metadata.
# Gate: every replay exit 0, no exception, outputs complete, process wall <= 1500 s.  R1 vs R4 (same state, ramp-arrival
# forecast object differs): CSV bytes equal, differing rows by kind, max |diff| per numeric column, forecast and selection.
# Preflights: exit, FREEZE_VERIFIED, network sha, hold-policy env, tuning sha, plant manifest pin, detector rows, freeze pin.
# usage: python -B g1_summary.py <out.json>
import csv, glob, hashlib, io, json, os, re, sys
G1 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/gate1'
DEC = {'va_s31': 'decisions_sdmpc31_v3c3_k92va_s31', 'va_s31gk': 'decisions_sdmpc31_v3c3_k92va_s31',
       'va_s41': 'decisions_sdmpc31_v3c3_k92va_s41', 'va_s43': 'decisions_sdmpc31_v3c3_k92va_s43'}
SEL = ('held_objective', 'warm_start_objective', 'selected_objective', 'prediction_ttt_reduction', 'selection_status')
WALL_MAX = 1500.0
NET_SHA = '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e'
FREEZE_SHA = '853d1c4fb97ed3de4cf62a409b06b9001648ce56171e2ed826236bdddb1506c6'
PLANT_SHA = '1184249889cc8ceeb0e730176ea058cf5a7e53aa98732bbb14e0dd113411f25c'
DET_SHA = '108debbb4b021796b195927ba2140dafab571e1d976734190f5d8f5bd255cfbc'
TUNING = {'': '729640af754a90c8d7fbe8f81577b27bae02b86f1d504e18333c0fc99717f983',
          'gk': 'e8a5730aed250e3dbd721c4ce931d2603fed49fe7a77d3022985d046b7e3d855'}


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def rows(path):
    return list(csv.DictReader(io.StringIO(open(path, encoding='utf-8-sig').read())))


def jl(p):
    return json.load(open(p, encoding='utf-8-sig'))


def one(label_dir):
    st = jl(label_dir + '/replay_state.json')
    T = int(st['T'])
    t6 = '%06d' % T
    d = label_dir + '/files/' + DEC[st['src']]
    r = {'label_dir': label_dir, 'label': st.get('label'), 'T': T, 'src': st['src'], 'tuning_sha256': st.get('tuning_sha256'),
         'exit': st.get('exit_code'), 'wall_sec': st.get('wall_sec'), 'start': st.get('start'), 'end': st.get('end'),
         'python_priority': st.get('python_priority'), 'status': st.get('status'), 'collect_exit': st.get('collect_exit'),
         'other_python_vissim_at_start': st.get('other_python_vissim_at_start'), 'rw_from_provenance': st.get('rw_from_provenance')}
    err = (open(label_dir + '/stderr.txt', encoding='utf-8', errors='replace').read() if os.path.exists(label_dir + '/stderr.txt') else '')
    lines = [l for l in err.strip().splitlines() if l.strip()]
    r['stderr_lines'] = len(lines)
    r['stderr_tail'] = lines[-1][:400] if lines else ''
    r['traceback'] = 'Traceback (most recent call last)' in err
    m = re.search(r'DECISION_FAILED type=(\S+)', err)
    exc = m.group(1) if m else None
    if exc is None and r['traceback']:
        m2 = re.findall(r'^(\w[\w.]*(?:Error|Exception|Exit)\b[^\n]*)$', err, re.M)
        exc = m2[-1][:200] if m2 else 'Traceback'
    r['exception'] = exc
    r['stderr_warning_lines'] = sum(1 for l in lines if '[경고]' in l or 'Warning' in l)
    bud = d + '/action_' + t6 + '.decision_budget.json'
    if os.path.exists(bud):
        b = jl(bud)
        r['budget_wall_sec'], r['budget_cpu_sec'] = b.get('wall_sec'), b.get('cpu_sec')
        r['budget_output_completed'], r['budget_output_error'] = b.get('output_completed'), b.get('output_error')
        r['budget_unlimited_time'] = b.get('unlimited_time')
    prog = d + '/action_' + t6 + '.joint.progress.jsonl'
    r['progress_lines'] = sum(1 for _ in open(prog, encoding='utf-8')) if os.path.exists(prog) else None
    cpu = label_dir + '/cpu_load.csv'
    if os.path.exists(cpu):
        vals, ql = [], []
        for row in list(csv.reader(open(cpu, encoding='utf-8', errors='replace')))[1:]:
            try:
                vals.append(float(row[1])); ql.append(float(row[2]))
            except Exception:
                pass
        r['cpu_total_pct_mean'] = round(sum(vals) / len(vals), 1) if vals else None
        r['cpu_queue_len_mean'] = round(sum(ql) / len(ql), 1) if ql else None
        r['cpu_samples'] = len(vals)
    csvp = d + '/action_' + t6 + '.csv'
    r['action_csv_exists'] = os.path.exists(csvp)
    if os.path.exists(csvp):
        rr = rows(csvp)
        r['csv_sha256'] = sha(csvp)
        r['csv_rows'] = len(rr)
        kinds = {}
        for x in rr:
            kinds[x['kind']] = kinds.get(x['kind'], 0) + 1
        r['csv_rows_by_kind'] = kinds
        r['vsl_speeds'] = sorted({x['speed_kph'] for x in rr if x['kind'] == 'vsl'})
        r['vsl_rows'] = sum(1 for x in rr if x['kind'] == 'vsl')
        r['meter_rows'] = {x['id']: {'rate_vph': x['rate_vph'], 'green_sec': x['green_sec']} for x in rr if x['kind'] == 'ramp_meter'}
        r['signal_rows'] = {x['id']: {k: x[k] for k in ('sc_no', 'p1_green', 'p2_green', 'p3_green', 'p4_green', 'offset')}
                            for x in rr if x['kind'] == 'signal'}
        r['signal_sg_rows'] = sum(1 for x in rr if x['kind'] == 'signal_sg')
    aj = d + '/action_' + t6 + '.json'
    r['action_json_exists'] = os.path.exists(aj)
    if os.path.exists(aj):
        a = jl(aj)
        md = a.get('metadata', {})
        r['controller_status'] = md.get('controller_status')
        r['forecast'] = {k: v for k, v in md.items() if 'ramp_arrival' in k or ('arrival' in k and 'RM_C' in k)}
        r['ramp_metering_json'] = a.get('ramp_metering')
        r['vsl_json_values'] = sorted({v for v in (a.get('vsl') or {}).values()}) if isinstance(a.get('vsl'), dict) else None
        r['decision_wall_sec_meta'] = md.get('decision_wall_sec')
        r['prediction_wall_sec_meta'] = md.get('prediction_wall_sec')
        r['sdmpc_state_present'] = 'sdmpc_state' in md
        txt = json.dumps(a)
        r['phantom_alias_mentions'] = len(re.findall('phantom_route_alias', txt))
        del a, txt
    jj = d + '/action_' + t6 + '.joint.json'
    if os.path.exists(jj):
        s = jl(jj).get('selection', {})
        r['selection'] = {k: s.get(k) for k in SEL}
    r['hold_or_error_files'] = sorted(os.path.basename(p) for p in glob.glob(d + '/action_' + t6 + '*')
                                      if re.search(r'\.(hold|error)', os.path.basename(p)))
    complete = (r['exit'] == 0 and r['action_csv_exists'] and r['action_json_exists'] and r.get('budget_output_completed') is True)
    no_exc = (r['exit'] == 0 and not r['traceback'] and r['exception'] is None and not any('error' in f for f in r['hold_or_error_files']))
    wall_gate = max([x for x in (r['wall_sec'], r.get('budget_wall_sec')) if isinstance(x, (int, float))] or [float('inf')])
    r['gate'] = {'finished': bool(complete), 'no_exception': bool(no_exc), 'gate_wall_sec': wall_gate,
                 'wall_le_1500': wall_gate <= WALL_MAX, 'pass': bool(complete and no_exc and wall_gate <= WALL_MAX)}
    return r


def diff_csv(a, b):
    ra, rb = rows(a), rows(b)
    key = lambda x: (x['kind'], x['id'], x['dsd_no'], x['sc_no'], x['link'], x['lane'])
    da, db = {key(x): x for x in ra}, {key(x): x for x in rb}
    out = {'rows_a': len(ra), 'rows_b': len(rb), 'keys_only_a': len(set(da) - set(db)), 'keys_only_b': len(set(db) - set(da)),
           'differing_rows_by_kind': {}, 'max_abs_diff': {}, 'differing_ids': {}}
    for k in sorted(set(da) & set(db)):
        x, y = da[k], db[k]
        cols = [c for c in x if c != 'metadata' and x[c] != y[c]]
        if cols:
            out['differing_rows_by_kind'][k[0]] = out['differing_rows_by_kind'].get(k[0], 0) + 1
            out['differing_ids'].setdefault(k[0], []).append(k[1])
            for c in cols:
                try:
                    v = abs(float(x[c]) - float(y[c]))
                except Exception:
                    v = None
                if v is not None:
                    out['max_abs_diff'][c] = max(out['max_abs_diff'].get(c, 0.0), v)
    return out


def preflight(label):
    root = G1 + '/runner_preflight/' + label
    w = G1 + '/runner_preflight/_wrapper/' + label
    seed = int(re.match(r's(\d+)', label).group(1))
    tag = label[len('s%d' % seed):]
    r = {'label': label, 'seed': seed, 'tag': tag}
    end = w + '/end.json'
    r['runner_exit'] = jl(end).get('runner_exit') if os.path.exists(end) else None
    r['wall_sec'] = jl(end).get('wall_sec') if os.path.exists(end) else None
    r['wrapper_error'] = jl(w + '/error.json').get('error') if os.path.exists(w + '/error.json') else None
    log = open(w + '/runner.log', encoding='utf-8', errors='replace').read() if os.path.exists(w + '/runner.log') else ''
    r['freeze_verified'] = 'FREEZE_VERIFIED' in log
    st = w + '/preflight_status.json'
    r['status_stage'] = jl(st).get('stage') if os.path.exists(st) else None
    prov = root + '/sdmpc/preflight/run_provenance_sdmpc31_sdmpc9000_s%d.json' % seed
    r['provenance'] = prov if os.path.exists(prov) else None
    if os.path.exists(prov):
        p = jl(prov)
        r['provenance_sha256'] = sha(prov)
        env = p.get('env', {})
        r['env_keys'] = len(env)
        r['env_empty_values'] = sorted(k for k, v in env.items() if v == '')
        r['hold_env'] = {k: env.get(k) for k in ('RW_DECISION_ERROR_POLICY', 'RW_DECISION_HOLD_PREVIOUS', 'RW_DECISION_TIMEOUT_SEC')}
        r['network_sha256'] = p['files']['network']['sha256']
        r['tuning_sha256'] = (p['files'].get('tuning') or {}).get('sha256')
        r['freeze_pin'] = (p.get('observation') or {}).get('freeze')
        r['plant_manifest'] = (p.get('observation') or {}).get('plant_manifest')
        det = (p.get('observation') or {}).get('detectors')
        r['detectors'] = det
        r['seed_in_provenance'] = p.get('seed')
        r['sim_period_sec'] = p.get('sim_period_sec')
        r['controller'] = p.get('controller')
        r['workspace_root'] = p.get('workspace_root')
        r['startup_stall_sec'] = p.get('startup_stall_sec')
        r['checks'] = {
            'exit0': r['runner_exit'] == 0, 'freeze_verified': r['freeze_verified'],
            'network_sha': r['network_sha256'] == NET_SHA,
            'hold_policy_env': r['hold_env'] == {'RW_DECISION_ERROR_POLICY': 'hold_previous_on_exception',
                                                 'RW_DECISION_HOLD_PREVIOUS': '1', 'RW_DECISION_TIMEOUT_SEC': '0'},
            'tuning_sha': r['tuning_sha256'] == TUNING.get(tag),
            'freeze_pin': isinstance(r['freeze_pin'], dict) and r['freeze_pin'].get('sha256') == FREEZE_SHA,
            'plant_manifest_pin': isinstance(r['plant_manifest'], dict) and r['plant_manifest'].get('sha256') == PLANT_SHA,
            'detector_pin': isinstance(det, dict) and det.get('sha256') == DET_SHA and det.get('rows') == 294,
            'controller_wu_link': r['controller'] == 'wu-link',
            'seed': r['seed_in_provenance'] == seed, 'sim_period_9000': r['sim_period_sec'] == 9000,
            'no_empty_rw_value': not r['env_empty_values'] or r['env_empty_values'] == ['RW_OBS150_GT'],
        }
        r['pass'] = all(r['checks'].values())
    else:
        r['pass'] = False
    return r


res = {'replays': [], 'pairs': [], 'preflights': [], 'freeze_verify_after': None}
for ld in sorted(glob.glob(G1 + '/out/g1R*/*/T*')):
    try:
        res['replays'].append(one(ld.replace(chr(92), '/')))
    except Exception as e:  # noqa: BLE001
        res['replays'].append({'label_dir': ld, 'summary_error': repr(e), 'gate': {'pass': False}})
by = {x.get('label'): x for x in res['replays']}
if by.get('g1R1', {}).get('csv_sha256') and by.get('g1R4', {}).get('csv_sha256'):
    a, b = by['g1R1'], by['g1R4']
    pa = a['label_dir'] + '/files/' + DEC[a['src']] + '/action_%06d.csv' % a['T']
    pb = b['label_dir'] + '/files/' + DEC[b['src']] + '/action_%06d.csv' % b['T']
    res['pairs'].append({'a': 'g1R1', 'b': 'g1R4', 'csv_bytes_equal': a['csv_sha256'] == b['csv_sha256'], 'csv': diff_csv(pa, pb),
                         'forecast_a': a.get('forecast'), 'forecast_b': b.get('forecast'),
                         'selection_a': a.get('selection'), 'selection_b': b.get('selection')})
for lab in ('s31', 's41', 's43', 's31gk'):
    if os.path.isdir(G1 + '/runner_preflight/_wrapper/' + lab):
        res['preflights'].append(preflight(lab))
fv = G1 + '/freeze_verify_after.txt'
if os.path.exists(fv):
    t = open(fv, encoding='utf-8', errors='replace').read()
    res['freeze_verify_after'] = {'text_tail': t.strip()[-400:], 'verified': 'FREEZE_VERIFIED' in t}
rep_main = [x for x in res['replays'] if x.get('label') in ('g1R1', 'g1R2', 'g1R3', 'g1R4')]
res['gate1'] = {'replays_found': len(rep_main), 'replays_pass': sum(1 for x in rep_main if x['gate']['pass']),
                'max_gate_wall_sec': max([x['gate']['gate_wall_sec'] for x in rep_main] or [None]),
                'preflights_B_pass': [p['label'] for p in res['preflights'] if p['tag'] == '' and p['pass']],
                'pass': (len(rep_main) == 4 and all(x['gate']['pass'] for x in rep_main)
                         and sorted(p['label'] for p in res['preflights'] if p['tag'] == '' and p['pass']) == ['s31', 's41', 's43']
                         and bool(res['freeze_verify_after'] and res['freeze_verify_after']['verified']))}
json.dump(res, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for x in res['replays']:
    print(x.get('label'), x.get('src'), 'exit', x.get('exit'), 'wall', x.get('wall_sec'), 'budget', x.get('budget_wall_sec'),
          'rows', x.get('csv_rows'), 'exc', x.get('exception'), 'gate', x['gate'])
for p in res['pairs']:
    print(p['a'], p['b'], 'csv_equal', p['csv_bytes_equal'], json.dumps(p['csv']['differing_rows_by_kind']))
for p in res['preflights']:
    print('preflight', p['label'], 'pass', p['pass'], json.dumps(p.get('checks')))
print('freeze_verify_after', res['freeze_verify_after'])
print('GATE1', json.dumps(res['gate1']))
