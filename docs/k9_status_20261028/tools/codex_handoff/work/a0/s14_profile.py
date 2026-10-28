# Stage profile of one joint decision from its progress JSONL + decision_budget.json.
# usage: s14_profile.py <files_dir> <T> [<files_dir2> ...]   prints JSON rows
import json, sys
from collections import OrderedDict


def profile(d, T):
    t6 = '%06d' % T
    rows = [json.loads(l) for l in open(d + '/action_' + t6 + '.joint.progress.jsonl', encoding='utf-8')]
    budget = json.load(open(d + '/action_' + t6 + '.decision_budget.json', encoding='utf-8-sig'))
    out = OrderedDict()
    def add(k, v):
        out[k] = round(out.get(k, 0.0) + v, 3)
    cap = 0
    region = 'pre'
    prev = 0.0
    batches = OrderedDict()
    in_secant = False
    for r in rows:
        e, s = r.get('elapsed_sec', 0.0), r['stage']
        dt = e - prev
        if s == 'sdmpc_pfo_start':
            add('pre_joint', dt); region = 'pfo'
        elif s == 'sdmpc_candidate_start':
            add(region if region != 'pfo' else 'pfo_tail', dt); cap += 1; region = 'cap%d' % cap
        elif s == 'sdmpc_meter_neighbors_start':
            add(region + ':other', dt); region = 'neighbor_audit'
        elif s == 'sdmpc_completed':
            add(region if region == 'neighbor_audit' else region + ':other', dt); region = 'post'
        elif region.startswith('cap'):
            if s == 'sdmpc_derivatives_start':
                in_secant = True
                add(region + ':other', dt)
            elif in_secant and s != 'sdmpc_derivatives_done':
                add(region + ':secant_batch', dt)
            elif s == 'sdmpc_derivatives_done':
                in_secant = False
                add(region + ':secant_batch', dt)
            elif s == 'sdmpc_tangent_done':
                add(region + ':tangent_wait', dt)
                add(region + ':tangent_compute(overlapped)', r.get('seconds', 0.0))
            elif s == 'sdmpc_surrogate_batch_done':
                add(region + ':step_predictions', dt)
            elif s == 'sdmpc_central_recovery_done':
                add(region + ':recovery_or_unlogged', dt)
            else:
                add(region + ':other', dt)
        else:
            add(region, dt)
        if s == 'sdmpc_surrogate_batch_done':
            batches.setdefault(region, []).append(round(r.get('seconds', 0.0), 2))
        prev = e
    total = budget.get('wall_sec')
    out['joint_elapsed_end'] = round(prev, 3)
    out['decision_wall_sec(budget)'] = round(total, 3) if total else None
    out['outside_joint(load+setup+final)'] = round(total - prev, 3) if total else None
    for k, v in (budget.get('inclusive_scopes') or {}).items():
        out['scope:' + k] = round(v.get('wall_sec', 0.0), 3)
    out['cpu_sec(main process)'] = budget.get('cpu_sec')
    out['n_caps'] = cap
    out['batch_seconds'] = batches
    return out


args = sys.argv[1:]
res = {}
i = 0
while i < len(args):
    d, T = args[i], int(args[i + 1]); i += 2
    res[d + '#' + str(T)] = profile(d, T)
print(json.dumps(res, ensure_ascii=False, indent=1))
