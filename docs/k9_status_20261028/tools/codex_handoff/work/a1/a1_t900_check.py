# A1 first SDMPC decision (T=900) check, declared before the A1 data exists (rule COMPARE_RULE_A1_T900.md).
# usage: python -B a1_t900_check.py <out.json> [A1 run dir override, smoke test only]     read-only.
# 1) runlog CONTROLLER_DECISION lines T=1..900: exit, wall_sec (A1 and codex), decision_budget wall_sec at T=900.
# 2) R1 command CSV sha256 for T = 1, 150, 300, 450, 600, 750, 900: A1 vs codex record; T=900 also vs the A0 env_hsw replay.
# 3) R2 five joint_written fields and R3 scored_action_token at T=900: A1 vs codex, A1 vs A0 env_hsw.
# 4) T=900 differing command rows (file order, identity columns checked): A1 vs codex, A1 vs A0 env_hsw.
# 5) T=900 inputs: leaf comparison of state_000900.json and obs150/derived_000900.json, A1 vs codex record,
#    after mapping the two run folders and the two frozen roots; differing leaves split into
#    clock (A0-CMP-1 clock regex on the last key), path-like strings, sha-like 64-hex strings, other.
import csv, hashlib, json, re, sys
BS = chr(92)
DEC = 'decisions_sdmpc31_sdmpc8100_s29'
A1RUN = sys.argv[2] if len(sys.argv) > 2 else 'D:/VISSIM_runs/20261025_codex_a1_s29/sdmpc'   # argv[2] only for the smoke test
A1DEC = A1RUN + '/' + DEC
CXRUN = 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc'
CXDEC = CXRUN + '/' + DEC
A0DEC = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/out/env_hsw/T000900/files/sdmpc/' + DEC
NAME = 'sdmpc31_sdmpc8100_s29'
MAPS_CX = [('E:' + BS + 'VISSIM_runs' + BS + '20261012_adopted355_optimized_s29_8100', 'RUNROOT'),
           ('D:' + BS + 'VISSIM_runtime' + BS + '20261012_adopted355_vsl_three' + BS + 'frozen' + BS + 'sdmpc31_ca181e84_202610121132', 'FRZ')]
MAPS_A1 = [('D:' + BS + 'VISSIM_runs' + BS + '20261025_codex_a1_s29', 'RUNROOT'),
           ('D:' + BS + 'VISSIM_runtime' + BS + '20261025_codex_a1' + BS + 'frozen' + BS + 'sdmpc31_a49981ff_202610251820', 'FRZ')]
TIME_KEY = re.compile(r'(?i)(wall|cpu|elapsed|perf_counter|timestamp|_utc$|^started|^ended|seconds$|_sec_including_spawn$|^scalar_sec$|^scalar_export_sec$)')
HEX64 = re.compile(r'^[0-9a-f]{64}$')
PATHLIKE = re.compile(r'(?i)([a-z]:[' + re.escape(BS) + '/])|(' + re.escape(BS + BS) + ')')
IDCOLS = ('kind', 'id', 'dsd_no', 'sc_no', 'link', 'lane')


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


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
    res = {'leaves_a1': len(fa), 'leaves_codex': len(fb), 'only_a1': sorted(set(fa) - set(fb))[:30], 'only_codex': sorted(set(fb) - set(fa))[:30],
           'n_only_a1': len(set(fa) - set(fb)), 'n_only_codex': len(set(fb) - set(fa)),
           'same': 0, 'diff_clock': [], 'diff_path': [], 'diff_hex64': [], 'diff_other': []}
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
        item = [k, fa[k] if not isinstance(fa[k], str) else fa[k][:160], fb[k] if not isinstance(fb[k], str) else fb[k][:160]]
        if TIME_KEY.search(last):
            res['diff_clock'].append(item)
        elif isinstance(va, str) and isinstance(vb, str) and (PATHLIKE.search(va) or PATHLIKE.search(vb)):
            res['diff_path'].append(item)
        elif isinstance(va, str) and isinstance(vb, str) and HEX64.match(va) and HEX64.match(vb):
            res['diff_hex64'].append(item)
        else:
            res['diff_other'].append(item)
    for c in ('diff_clock', 'diff_path', 'diff_hex64', 'diff_other'):
        res['n_' + c] = len(res[c])
        res[c] = res[c][:40]
    return res


def rows(pa, pb):
    a = list(csv.DictReader(open(pa, encoding='utf-8')))
    b = list(csv.DictReader(open(pb, encoding='utf-8')))
    res = {'rows_a': len(a), 'rows_b': len(b), 'header_equal': (list(a[0].keys()) if a else []) == (list(b[0].keys()) if b else []),
           'identity_mismatch': 0, 'n_differing_rows': 0, 'by_kind': {}, 'max_abs_delta_by_kind_col': {}, 'signal_green_diff_ge_1s': 0,
           'ramp_meter_rate_or_green_diff': 0, 'vsl_speed_diff': 0, 'nonnumeric_diffs': 0, 'examples': []}
    for i, (x, y) in enumerate(zip(a, b)):
        if any(x.get(k) != y.get(k) for k in IDCOLS):
            res['identity_mismatch'] += 1
            continue
        cols = []
        for k in x:
            if x[k] == y[k]:
                continue
            try:
                d = float(x[k]) - float(y[k])
                key = x['kind'] + ':' + k
                res['max_abs_delta_by_kind_col'][key] = round(max(res['max_abs_delta_by_kind_col'].get(key, 0.0), abs(d)), 6)
                if x['kind'] in ('signal', 'signal_sg') and k.endswith('_green') and abs(d) >= 1.0:
                    res['signal_green_diff_ge_1s'] += 1
                if x['kind'] == 'ramp_meter' and k in ('rate_vph', 'green_sec'):
                    res['ramp_meter_rate_or_green_diff'] += 1
                if x['kind'] == 'vsl' and k == 'speed_kph':
                    res['vsl_speed_diff'] += 1
                cols.append([k, x[k], y[k]])
            except ValueError:
                res['nonnumeric_diffs'] += 1
                cols.append([k, x[k], y[k]])
        if cols:
            res['n_differing_rows'] += 1
            res['by_kind'][x['kind']] = res['by_kind'].get(x['kind'], 0) + 1
            if len(res['examples']) < 40:
                res['examples'].append({'row': i + 1, **{k: x.get(k) for k in IDCOLS}, 'cols': cols})
    return res


def runlog_decisions(path):
    out = {}
    pat = re.compile(r'^CONTROLLER_DECISION sim_sec=(\d+) wall_sec=([0-9.]+) result=exit=(-?\d+)')
    for line in open(path, encoding='utf-8', errors='replace'):
        m = pat.match(line)
        if m:
            out[int(m.group(1))] = {'wall_sec': float(m.group(2)), 'exit': int(m.group(3))}
    return out


out = {'rule': 'COMPARE_RULE_A1_T900.md', 'a1_dec': A1DEC, 'codex_dec': CXDEC, 'a0_env_hsw_dec': A0DEC}
rl_a1 = runlog_decisions(A1RUN + '/runlog_' + NAME + '.txt')
rl_cx = runlog_decisions(CXRUN + '/runlog_' + NAME + '.txt')
out['runlog'] = {str(t): {'a1': rl_a1.get(t), 'codex': rl_cx.get(t)} for t in (1, 150, 300, 450, 600, 750, 900)}
try:
    out['decision_budget_wall_sec_900'] = {'a1': load(A1DEC + '/action_000900.decision_budget.json').get('wall_sec'),
                                           'codex': load(CXDEC + '/action_000900.decision_budget.json').get('wall_sec')}
except Exception as e:
    out['decision_budget_wall_sec_900'] = {'error': repr(e)}
r1 = {}
for t in (1, 150, 300, 450, 600, 750, 900):
    t6 = '%06d' % t
    try:
        a = sha(A1DEC + '/action_' + t6 + '.csv')
    except FileNotFoundError:
        a = None
    c = sha(CXDEC + '/action_' + t6 + '.csv')
    r1[str(t)] = {'a1': a, 'codex': c, 'equal_codex': a == c}
r1['900']['a0_env_hsw'] = sha(A0DEC + '/action_000900.csv')
r1['900']['equal_a0_env_hsw'] = r1['900']['a1'] == r1['900']['a0_env_hsw']
out['R1'] = r1
K2 = ['seven_action_fields_sha256', 'ordered_physical_rows_sha256', 'expected_live_metadata_sha256', 'expected_csv_sha256', 'ordered_row_count']
jw = {'a1': load(A1DEC + '/action_000900.joint_written.json'), 'codex': load(CXDEC + '/action_000900.joint_written.json'),
      'a0_env_hsw': load(A0DEC + '/action_000900.joint_written.json')}
out['R2'] = {k: {s: jw[s].get(k) for s in jw} for k in K2}
out['R2_equal_codex'] = all(jw['a1'].get(k) == jw['codex'].get(k) for k in K2)
out['R2_equal_a0_env_hsw'] = all(jw['a1'].get(k) == jw['a0_env_hsw'].get(k) for k in K2)
out['R3'] = {s: jw[s].get('scored_action_token') for s in jw}
out['R3_equal_codex'] = out['R3']['a1'] == out['R3']['codex']
out['R3_equal_a0_env_hsw'] = out['R3']['a1'] == out['R3']['a0_env_hsw']
out['rows_vs_codex'] = rows(A1DEC + '/action_000900.csv', CXDEC + '/action_000900.csv')
out['rows_vs_a0_env_hsw'] = rows(A1DEC + '/action_000900.csv', A0DEC + '/action_000900.csv')
out['inputs_vs_codex'] = {}
for nm in ('state_000900.json', 'obs150/derived_000900.json'):
    try:
        out['inputs_vs_codex'][nm] = leafdiff(load(A1DEC + '/' + nm), load(CXDEC + '/' + nm))
    except Exception as e:
        out['inputs_vs_codex'][nm] = {'error': repr(e)}
json.dump(out, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
brief = {'runlog_900': out['runlog']['900'], 'budget_900': out['decision_budget_wall_sec_900'],
         'R1': {t: (v['equal_codex'], v.get('equal_a0_env_hsw')) for t, v in r1.items()},
         'R2_codex': out['R2_equal_codex'], 'R2_a0': out['R2_equal_a0_env_hsw'], 'R3_codex': out['R3_equal_codex'], 'R3_a0': out['R3_equal_a0_env_hsw'],
         'rows_codex': out['rows_vs_codex']['n_differing_rows'], 'rows_a0': out['rows_vs_a0_env_hsw']['n_differing_rows'],
         'inputs': {k: {kk: v.get(kk) for kk in ('same', 'n_only_a1', 'n_only_codex', 'n_diff_clock', 'n_diff_path', 'n_diff_hex64', 'n_diff_other', 'error')}
                    for k, v in out['inputs_vs_codex'].items()}}
print(json.dumps(brief, ensure_ascii=False))
