# Compare an A1 run_provenance JSON with the codex joint provenance (read-only). Usage: python -B a1_prov_cmp.py <a1_prov> <codex_prov> <out.json>
import json, sys
BS = chr(92)
a = json.load(open(sys.argv[1], encoding='utf-8-sig'))
c = json.load(open(sys.argv[2], encoding='utf-8-sig'))
out = {'a1': sys.argv[1], 'codex': sys.argv[2]}
out['scalars'] = {k: {'a1': a.get(k), 'codex': c.get(k)} for k in
                  ('seed', 'sim_period_sec', 'controller', 'control_interval_sec', 'state_log_interval_sec', 'startup_stall_sec',
                   'demand_scale', 'audit_anchors_sec', 'workspace_git_commit', 'numsim_git_commit', 'numsim_snapshot_commit', 'workspace_root')}
env = {}
for k in sorted(set(a['env']) | set(c['env'])):
    env[k] = {'a1': a['env'].get(k), 'codex': c['env'].get(k), 'same': a['env'].get(k) == c['env'].get(k)}
out['env_n'] = {'a1': len(a['env']), 'codex': len(c['env'])}
out['env'] = env
files = {}
for k in sorted(set(a['files']) | set(c['files'])):
    va, vc = a['files'].get(k, {}), c['files'].get(k, {})
    files[k] = {'a1_sha256': va.get('sha256'), 'codex_sha256': vc.get('sha256'), 'same_sha': va.get('sha256') == vc.get('sha256'),
                'a1_exists': va.get('exists'), 'codex_exists': vc.get('exists')}
out['files'] = files


def leafmap(lst):
    return {x['path'].replace(BS, '/').split('/')[-1]: x['sha256'] for x in lst}


for key in ('controller_sources', 'signal_programs'):
    sa, sc = leafmap(a.get(key, [])), leafmap(c.get(key, []))
    out[key] = {'n_a1': len(sa), 'n_codex': len(sc), 'diff': sorted(k for k in set(sa) | set(sc) if sa.get(k) != sc.get(k))}
for key in ('ramp_meter_timing', 'signal_observation', 'observation'):
    out[key + '_same_json'] = json.dumps(a.get(key), sort_keys=True) == json.dumps(c.get(key), sort_keys=True)
    out[key + '_a1'] = a.get(key)
    out[key + '_codex'] = c.get(key)
json.dump(out, open(sys.argv[3], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('env_n', out['env_n'])
for k, v in env.items():
    print(('same ' if v['same'] else 'DIFF ') + k + ' | a1=' + str(v['a1'])[:110] + ('' if v['same'] else ' | codex=' + str(v['codex'])[:110]))
for k, v in files.items():
    print(('same ' if v['same_sha'] else 'DIFF ') + 'file ' + k + ' ' + str(v['a1_sha256'])[:12] + ' codex ' + str(v['codex_sha256'])[:12])
for key in ('controller_sources', 'signal_programs'):
    print(key, out[key])
for key in ('ramp_meter_timing', 'signal_observation', 'observation'):
    print(key, 'same_json' if out[key + '_same_json'] else 'DIFF')
for k, v in out['scalars'].items():
    print('scalar', k, v)
