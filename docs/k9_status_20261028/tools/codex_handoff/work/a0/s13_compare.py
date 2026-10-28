# A0-CMP-1 comparison (rule file COMPARE_RULE_A0.md, sha a05f2071...).
# usage: s13_compare.py T replay_label [reference]   reference = 'recorded' (default) or another replay label
import hashlib, json, math, re, sys
BS = chr(92)
T = int(sys.argv[1]); LABEL = sys.argv[2]; REF = sys.argv[3] if len(sys.argv) > 3 else 'recorded'
t6 = '%06d' % T
A0 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0'
DEC = 'decisions_sdmpc31_sdmpc8100_s29'


def files_dir(label):
    if label == 'recorded':
        return 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/' + DEC
    return A0 + '/out/' + label + '/T' + t6 + '/files/sdmpc/' + DEC


ORIG_RUN = 'E:' + BS + 'VISSIM_runs' + BS + '20261012_adopted355_optimized_s29_8100' + BS + 'sdmpc'
ORIG_FROZEN = 'D:' + BS + 'VISSIM_runtime' + BS + '20261012_adopted355_vsl_three' + BS + 'frozen' + BS + 'sdmpc31_ca181e84_202610121132'
NEW_RUN = A0.replace('/', BS) + BS + 'runs' + BS + 'T' + t6 + BS + 'sdmpc'
NEW_CODE = A0.replace('/', BS) + BS + 'code'
TIME_KEY = re.compile(r'(?i)(wall|cpu|elapsed|perf_counter|timestamp|_utc$|^started|^ended|seconds$|_sec_including_spawn$|^scalar_sec$|^scalar_export_sec$)')
TMP = re.compile(r'(?i)sdmpc-[a-z]+-[a-z0-9_]{6,}')
HEX64 = re.compile(r'^[0-9a-f]{64}$')


def norm(s):
    if not isinstance(s, str):
        return s
    if REF == 'recorded':
        s = s.replace(ORIG_RUN, NEW_RUN).replace(ORIG_FROZEN, NEW_CODE)
        s = s.replace(ORIG_RUN.replace(BS, '/'), NEW_RUN.replace(BS, '/')).replace(ORIG_FROZEN.replace(BS, '/'), NEW_CODE.replace(BS, '/'))
    return TMP.sub('sdmpc-TMP', s)


def normrep(s):
    return TMP.sub('sdmpc-TMP', s) if isinstance(s, str) else s


def flatten(x, p, out, nf):
    if isinstance(x, dict):
        for k, v in x.items():
            flatten(v, p + '/' + nf(str(k)), out, nf)
        if not x:
            out[p] = '{}'
    elif isinstance(x, list):
        for i, v in enumerate(x):
            flatten(v, p + '/' + str(i), out, nf)
        if not x:
            out[p] = '[]'
    else:
        out[p] = nf(x)


def same(a, b):
    if type(a) is float and type(b) is float:
        return repr(a) == repr(b) or (math.isnan(a) and math.isnan(b))
    return type(a) is type(b) and a == b


def leafcmp(name, a, b):
    fa, fb = {}, {}
    flatten(a, '', fa, normrep)
    flatten(b, '', fb, norm)
    keys = set(fa) | set(fb)
    res = {'leaves_replay': len(fa), 'leaves_ref': len(fb), 'equal': 0, 'diff_time': [], 'diff_hash': [], 'diff_path': [], 'diff_other': [],
           'only_replay': [], 'only_ref': []}
    for k in sorted(keys):
        if k not in fb:
            res['only_replay'].append(k); continue
        if k not in fa:
            res['only_ref'].append(k); continue
        va, vb = fa[k], fb[k]
        if same(va, vb):
            res['equal'] += 1; continue
        last = [s for s in k.split('/') if not s.isdigit()][-1] if k else ''
        if TIME_KEY.search(last):
            res['diff_time'].append(k)
        elif isinstance(va, str) and isinstance(vb, str) and HEX64.match(va) and HEX64.match(vb):
            res['diff_hash'].append(k)
        elif isinstance(va, str) and (':' + BS in va or ':/' in va):
            res['diff_path'].append(k)
        else:
            res['diff_other'].append((k, repr(va)[:120], repr(vb)[:120]))
    return res


def load(path):
    return json.loads(open(path, 'rb').read().decode('utf-8-sig'))


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


R = files_dir(LABEL); F = files_dir(REF)
report = {'T': T, 'replay': LABEL, 'reference': REF, 'rule_sha256': sha('C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/a0/COMPARE_RULE_A0.md')}
csv_r, csv_f = R + '/action_' + t6 + '.csv', F + '/action_' + t6 + '.csv'
report['R1_csv_sha'] = {'replay': sha(csv_r), 'reference': sha(csv_f)}
report['R1_equal'] = report['R1_csv_sha']['replay'] == report['R1_csv_sha']['reference']
jw_r, jw_f = load(R + '/action_' + t6 + '.joint_written.json'), load(F + '/action_' + t6 + '.joint_written.json')
keys2 = ['seven_action_fields_sha256', 'ordered_physical_rows_sha256', 'expected_live_metadata_sha256', 'expected_csv_sha256', 'ordered_row_count']
report['R2'] = {k: [jw_r.get(k), jw_f.get(k), jw_r.get(k) == jw_f.get(k)] for k in keys2}
report['R2_equal'] = all(v[2] for v in report['R2'].values())
report['R3_token'] = [jw_r.get('scored_action_token'), jw_f.get('scored_action_token')]
report['R3_equal'] = report['R3_token'][0] == report['R3_token'][1]
R4 = {}
for name in ('action_' + t6 + '.json', 'action_' + t6 + '.joint.json', 'action_' + t6 + '.joint_written.json',
             'obs150/derived_' + t6 + '.json', 'obs150/vsl_cohorts_' + t6 + '.json', 'action_' + t6 + '.decision_budget.json'):
    try:
        a, b = load(R + '/' + name), load(F + '/' + name)
    except FileNotFoundError as e:
        R4[name] = {'missing': str(e)}; continue
    r = leafcmp(name, a, b)
    summary = {k: (len(v) if isinstance(v, list) else v) for k, v in r.items()}
    summary['examples'] = {k: v[:25] for k, v in r.items() if isinstance(v, list) and v}
    R4[name] = summary
report['R4'] = R4
out = A0 + '/out/' + LABEL + '/T' + t6 + '/compare_vs_' + REF + '.json'
json.dump(report, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({k: report[k] for k in ('T', 'replay', 'reference', 'R1_equal', 'R2_equal', 'R3_equal')}))
for n, s in R4.items():
    print(n, {k: v for k, v in s.items() if k != 'examples'})
    for k, v in s.get('examples', {}).items():
        if k in ('diff_other', 'only_replay', 'only_ref', 'diff_hash', 'diff_path'):
            print('   ', k, v[:6])
