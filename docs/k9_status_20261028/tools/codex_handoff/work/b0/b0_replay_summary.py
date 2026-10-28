# B0 replay summary (descriptive, no verdict).  Fixed before the replay data exist (COMPARE_RULE_B0.md).
# For each replay label found under b0/out/: exit, wall, decision budget wall/cpu, progress lines, CPU load mean,
# action CSV rows by kind, ramp-arrival forecast metadata, phantom-alias counts, held/exception, stand-in / calibration
# file reads (open log).  For R1 vs R2 (same state, ramp-forecast object differs): CSV bytes equal, differing rows by
# kind, max |diff| per numeric column, selection scalars.   usage: python -B b0_replay_summary.py <out.json>
import csv, glob, hashlib, io, json, os, re, sys
B0 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/b0'
DEC = 'decisions_sdmpc31_v3c3_k92va_s31'
STANDINS = ('flow279/config_10686_free.json', 'sc107_shared316/config.json', 'sc109_transport317/config.json',
            'native348/calibration.json')
SEL = ('held_objective', 'warm_start_objective', 'selected_objective', 'prediction_ttt_reduction', 'selection_status')


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def rows(path):
    return list(csv.DictReader(io.StringIO(open(path, encoding='utf-8-sig').read())))


def one(label_dir):
    st = json.load(open(label_dir + '/replay_state.json', encoding='utf-8-sig'))
    T = int(st['T'])
    t6 = '%06d' % T
    d = label_dir + '/files/run/' + DEC
    r = {'label_dir': label_dir, 'T': T, 'src': st['src'], 'tuning_sha256': st.get('tuning_sha256'), 'exit': st.get('exit_code'),
         'wall_sec': st.get('wall_sec'), 'python_priority': st.get('python_priority')}
    err = (open(label_dir + '/stderr.txt', encoding='utf-8', errors='replace').read() if os.path.exists(label_dir + '/stderr.txt') else '')
    r['stderr_tail'] = err.strip().splitlines()[-1][:400] if err.strip() else ''
    m = re.search(r'DECISION_FAILED type=(\S+)', err)
    r['exception_type'] = m.group(1) if m else None
    bud = d + '/action_' + t6 + '.decision_budget.json'
    if os.path.exists(bud):
        b = json.load(open(bud, encoding='utf-8-sig'))
        r['budget_wall_sec'], r['budget_cpu_sec'] = b.get('wall_sec'), b.get('cpu_sec')
    prog = d + '/action_' + t6 + '.joint.progress.jsonl'
    r['progress_lines'] = sum(1 for _ in open(prog, encoding='utf-8')) if os.path.exists(prog) else None
    cpu = label_dir + '/cpu_load.csv'
    if os.path.exists(cpu):
        vals = []
        for row in list(csv.reader(open(cpu, encoding='utf-8', errors='replace')))[1:]:
            try:
                vals.append(float(row[1]))
            except Exception:
                pass
        r['cpu_total_pct_mean'] = round(sum(vals) / len(vals), 1) if vals else None
    csvp = d + '/action_' + t6 + '.csv'
    if os.path.exists(csvp):
        rr = rows(csvp)
        r['csv_sha256'] = sha(csvp)
        r['csv_rows'] = len(rr)
        kinds = {}
        for x in rr:
            kinds[x['kind']] = kinds.get(x['kind'], 0) + 1
        r['csv_rows_by_kind'] = kinds
        r['vsl_speeds'] = sorted({x['speed_kph'] for x in rr if x['kind'] == 'vsl'})
        r['meter_rows'] = {x['id']: {'rate_vph': x['rate_vph'], 'green_sec': x['green_sec']} for x in rr if x['kind'] == 'ramp_meter'}
    aj = d + '/action_' + t6 + '.json'
    if os.path.exists(aj):
        a = json.load(open(aj, encoding='utf-8-sig'))
        md = a.get('metadata', {})
        r['forecast'] = {k: v for k, v in md.items() if 'ramp_arrival' in k}
        r['phantom_alias'] = {k: v for k, v in md.items() if 'phantom' in k}
        txt = json.dumps(a)
        r['phantom_alias_mentions'] = len(re.findall('phantom_route_alias', txt))
        r['decision_wall_sec_meta'] = md.get('decision_wall_sec')
    jj = d + '/action_' + t6 + '.joint.json'
    if os.path.exists(jj):
        s = json.load(open(jj, encoding='utf-8-sig')).get('selection', {})
        r['selection'] = {k: s.get(k) for k in SEL}
    op = label_dir + '/opens.tsv'
    if os.path.exists(op):
        lines = open(op, encoding='utf-8', errors='replace').read().splitlines()
        r['opens_lines'] = len(lines)
        r['standin_or_calibration_reads'] = sorted({l.split(chr(9), 1)[-1] for l in lines
                                                    if any(s in l.replace(chr(92), '/') for s in STANDINS)})
    r['hold_files'] = sorted(os.path.basename(p) for p in glob.glob(d + '/action_' + t6 + '.hold*'))
    return r


def diff_csv(a, b):
    ra, rb = rows(a), rows(b)
    key = lambda x: (x['kind'], x['id'], x['dsd_no'], x['sc_no'], x['link'], x['lane'])
    da, db = {key(x): x for x in ra}, {key(x): x for x in rb}
    out = {'rows_a': len(ra), 'rows_b': len(rb), 'keys_only_a': len(set(da) - set(db)), 'keys_only_b': len(set(db) - set(da)),
           'differing_rows_by_kind': {}, 'max_abs_diff': {}}
    for k in set(da) & set(db):
        x, y = da[k], db[k]
        cols = [c for c in x if c != 'metadata' and x[c] != y[c]]
        if cols:
            out['differing_rows_by_kind'][k[0]] = out['differing_rows_by_kind'].get(k[0], 0) + 1
            for c in cols:
                try:
                    v = abs(float(x[c]) - float(y[c]))
                except Exception:
                    v = None
                if v is not None:
                    out['max_abs_diff'][c] = max(out['max_abs_diff'].get(c, 0.0), v)
    return out


res = {'replays': [], 'pairs': []}
for ld in sorted(glob.glob(B0 + '/out/b0R*/*/T*')):
    res['replays'].append(one(ld.replace(chr(92), '/')))
by = {os.path.basename(os.path.dirname(os.path.dirname(x['label_dir']))): x for x in res['replays']}
for a, b in (('b0R1', 'b0R2'), ('b0R1_r2', 'b0R2'), ('b0R1', 'b0R2_r2')):
    if a in by and b in by and by[a].get('csv_sha256') and by[b].get('csv_sha256'):
        pa = by[a]['label_dir'] + '/files/run/' + DEC + '/action_%06d.csv' % by[a]['T']
        pb = by[b]['label_dir'] + '/files/run/' + DEC + '/action_%06d.csv' % by[b]['T']
        p = {'a': a, 'b': b, 'csv_bytes_equal': by[a]['csv_sha256'] == by[b]['csv_sha256'], 'csv': diff_csv(pa, pb),
             'forecast_a': by[a].get('forecast'), 'forecast_b': by[b].get('forecast'),
             'selection_a': by[a].get('selection'), 'selection_b': by[b].get('selection')}
        res['pairs'].append(p)
json.dump(res, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for x in res['replays']:
    print(x['label_dir'].split('/out/')[1], 'exit', x['exit'], 'wall', x['wall_sec'], 'budget', x.get('budget_wall_sec'), 'rows', x.get('csv_rows'), 'exc', x['exception_type'])
for p in res['pairs']:
    print(p['a'], p['b'], 'csv_equal', p['csv_bytes_equal'], json.dumps(p['csv']['differing_rows_by_kind']))
