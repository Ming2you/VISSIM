# Speed-candidate verdict helper (no verdict words in output): compare a candidate replay with its same-env baseline.
# Reads compare_vs_<baseline>.json written by s13_compare.py and re-derives the full R4 leaf lists to classify
# every non-clock difference. Prints counts of: (a) regex clock leaves, (a') leaves whose last key ends with "_sec"
# (duration leaves the fixed regex misses), (h) hash leaves explained only by files that carry clock leaves, other.
# usage: s27_candidate_check.py T candidate baseline
import json, re, sys, importlib.util
T, CAND, BASE = int(sys.argv[1]), sys.argv[2], sys.argv[3]
W = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/a0/'
sys.argv = ['s13_compare.py', str(T), CAND, BASE]
spec = importlib.util.spec_from_file_location('cmp', W + 's13_compare.py')
src = open(W + 's13_compare.py', encoding='utf-8').read()
# reuse helpers only (do not execute the module's top-level report)
helpers = src.split('R = files_dir(LABEL)')[0]
ns = {}
exec(compile(helpers, 's13_compare_helpers', 'exec'), ns)
t6 = '%06d' % T
R, F = ns['files_dir'](CAND), ns['files_dir'](BASE)
SEC = re.compile(r'(?i)_sec$')
out = {'T': T, 'candidate': CAND, 'baseline': BASE, 'files': {}}
for name in ('action_' + t6 + '.json', 'action_' + t6 + '.joint.json', 'action_' + t6 + '.joint_written.json',
             'obs150/derived_' + t6 + '.json', 'obs150/vsl_cohorts_' + t6 + '.json', 'action_' + t6 + '.decision_budget.json'):
    a, b = ns['load'](R + '/' + name), ns['load'](F + '/' + name)
    r = ns['leafcmp'](name, a, b)
    other = r['diff_other']
    sec = [k for k, _, _ in other if SEC.search([s for s in k.split('/') if not s.isdigit()][-1])]
    rest = [(k, va, vb) for k, va, vb in other if k not in set(sec)]
    out['files'][name] = {'leaves': r['leaves_replay'], 'equal': r['equal'], 'clock_regex': len(r['diff_time']),
                          'duration_sec_leaves': len(sec), 'hash': r['diff_hash'], 'path': len(r['diff_path']),
                          'other_unexplained': rest[:50], 'only_candidate': r['only_replay'][:20], 'only_baseline': r['only_ref'][:20]}
csv_a = open(R + '/action_' + t6 + '.csv', 'rb').read(); csv_b = open(F + '/action_' + t6 + '.csv', 'rb').read()
out['R1_csv_bytes_equal'] = csv_a == csv_b
jw_a, jw_b = ns['load'](R + '/action_' + t6 + '.joint_written.json'), ns['load'](F + '/action_' + t6 + '.joint_written.json')
out['R2_equal'] = all(jw_a.get(k) == jw_b.get(k) for k in ('seven_action_fields_sha256', 'ordered_physical_rows_sha256', 'expected_live_metadata_sha256', 'expected_csv_sha256', 'ordered_row_count'))
out['R3_equal'] = jw_a.get('scored_action_token') == jw_b.get('scored_action_token')
dst = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/out/' + CAND + '/T' + t6 + '/candidate_vs_' + BASE + '.json'
json.dump(out, open(dst, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({'T': T, 'cand': CAND, 'base': BASE, 'R1': out['R1_csv_bytes_equal'], 'R2': out['R2_equal'], 'R3': out['R3_equal'],
                  'per_file': {n: {k: (len(v) if isinstance(v, list) else v) for k, v in d.items()} for n, d in out['files'].items()}}, ensure_ascii=False))
