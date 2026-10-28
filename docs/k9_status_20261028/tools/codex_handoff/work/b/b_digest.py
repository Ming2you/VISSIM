# Print a compact digest of work/b/b_run_summary_s<seed>.json (read-only). usage: python -B b_digest.py <seed>
import json, sys
W = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/b'
s = sys.argv[1]
d = json.load(open(W + '/b_run_summary_s%s.json' % s, encoding='utf-8'))
r = d['runlog']
print('== s%s' % s)
for k in ('lines', 'stage_lines', 'startup_stage_last', 'SIM_SEC', 'SIM_STEPS', 'DECISIONS_OK', 'DECISIONS_FAILED', 'DECISIONS_HELD_PREVIOUS', 'DECISIONS_HELD_ON_EXCEPTION', 'RUN_MODE', 'runlog_err_bytes'):
    print(k, r.get(k))
print('n_decisions', len(r['decisions']), 'first', r['decisions'][:2], 'last', r['decisions'][-2:])
print('warmup', r['warmup_decisions'])
print('wall_ge900', r.get('wall_ge900'))
print('hold_attempts', r['hold_attempts'], 'held_previous', r['held_previous'])
print('other_decision_lines', r['other_decision_lines'][:10])
print('error_like_lines', r['error_like_lines'][:10])
print('wrapper', json.dumps(d['wrapper'])[:1500])
ns = d['native_status']
print('native_status', {k: ns.get(k) for k in list(ns)[:12]} if isinstance(ns, dict) else ns)
print('launch.log', d['launch.log'])
print('WATCHDOG_PROGRESS', d['WATCHDOG_PROGRESS.txt'])
print('stop_files', d['stop_files'])
dd = d['decisions_dir']
print('error_txt', dd.get('error_txt'))
print('action_json_T n', len(dd.get('action_json_T', [])), dd.get('action_json_T', [])[:3], dd.get('action_json_T', [])[-3:])
bw = [v for k, v in dd.get('budget_wall', {}).items() if int(k) >= 900]
print('budget_wall_ge900 n', len(bw), 'max', max(bw) if bw else None)
a = d['action_csv']
print('action_csv', {k: a.get(k) for k in ('kinds', 'n_decision_times', 'rows_per_kind_per_T', 'vsl_speed_counts', 'vsl_non110')})
print('meter_rate_green_counts', json.dumps(a.get('meter_rate_green_counts')))
print('err_b', json.dumps(d['err_b'])[:2500])
print('err_nc3', json.dumps(d['err_nc3'])[:2500])
print('walltimes_tool', d.get('walltimes_tool'))
dt = d.get('dec_tool', {})
print('dec_tool n', dt.get('n'), 'controller_status', dt.get('controller_status'), 'selection_status', dt.get('selection_status'))
print('rm_out_counts', json.dumps(dt.get('rm_out_counts')))
print('rm_green_counts', json.dumps(dt.get('rm_green_counts')))
print('vsl_out_sets', json.dumps(dt.get('vsl_out_sets'))[:600])
fc = dt.get('forecast_ramp_arrival_total_vph') or []
vals = [v for t, v in fc if v is not None]
print('forecast n', len(fc), 'non-null', len(vals), 'min', min(vals) if vals else None, 'max', max(vals) if vals else None)
rf = d.get('ramp_fc_tool')
print('ramp_fc_tool keys', list(rf.keys()) if isinstance(rf, dict) else type(rf))
print('rm_exec_tool', d.get('rm_exec_tool'))
print('prefix_vhr', d.get('prefix_vhr'))
print('fzp_firstdiff_tool', json.dumps(d.get('fzp_firstdiff_tool'))[:1500])
