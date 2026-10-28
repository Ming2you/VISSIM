# vhr_leaves2.py - targeted numeric-internals comparison (mine vs A0 env_hsw vs record), T=900.
import hashlib, json, re

t6 = '000900'
D = {'mine': f'D:/VISSIM-merge/k8_gate_trees/codexhandoff/vhr/runs/T{t6}/sdmpc/decisions_sdmpc31_sdmpc8100_s29',
     'a0': f'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/out/env_hsw/T{t6}/files/sdmpc/decisions_sdmpc31_sdmpc8100_s29',
     'a0_base': f'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/out/base_rep2/T{t6}/files/sdmpc/decisions_sdmpc31_sdmpc8100_s29',
     'rec': 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29'}
TIM = re.compile(r'(sec|seconds|elapsed|wall|_at|timestamp|created|path|sha256|token|key|digest|directory|source)$', re.I)


def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if not TIM.search(k)}
    if isinstance(o, list):
        return [strip(v) for v in o]
    return o


def h(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, separators=(',', ':')).encode()).hexdigest()[:16]


SUB = ['selected_objective', 'held_objective', 'prediction_ttt_reduction', 'gradient_rows', 'local_rows', 'trial_rows', 'candidates',
       'central_multiplier', 'central_derivative_work', 'pfo_warm_start', 'meter_neighbor_audit', 'iteration_dual_updates', 'price_update']
out = {}
for k, d in D.items():
    a = json.load(open(f'{d}/action_{t6}.json', encoding='utf-8'))
    j = a['metadata']['joint_leader_selection']
    row = {s: h(strip(j.get(s))) for s in SUB}
    row['seven_fields'] = h({f: a.get(f) for f in ['N_P_star', 'N_UF_star', 'ramp_metering', 'vsl', 'green_times', 'offsets', 'inflow_outflow_allocation']})
    row['selected_objective_value'] = j.get('selected_objective')
    row['prediction_ttt_reduction_value'] = j.get('prediction_ttt_reduction')
    cdw = j.get('central_derivative_work')
    row['central_derivative_work_sample'] = json.dumps(cdw)[:300] if cdw is not None else None
    out[k] = row
    del a, j
names = list(D)
cmp = {}
for s in SUB + ['seven_fields']:
    cmp[s] = {f'{x}~{y}': out[x][s] == out[y][s] for i, x in enumerate(names) for y in names[i + 1:]}
out['equal'] = cmp
json.dump(out, open('C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/vhr/leaves2_T000900.json', 'w'), indent=1)
for s, v in cmp.items():
    print(s, v)
for k in names:
    print(k, out[k]['selected_objective_value'], out[k]['prediction_ttt_reduction_value'])
