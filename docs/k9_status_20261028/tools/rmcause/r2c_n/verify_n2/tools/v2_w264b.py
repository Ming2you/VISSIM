import json
d = json.load(open(r'D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc/decisions_sdmpc31_sdmpc9000_s29/action_001800.json', encoding='utf-8'))
jl = d['metadata']['joint_leader_selection']
base = jl['meter_neighbor_audit']['baseline_objective']
for i, r in enumerate(jl['trial_rows']):
    if abs(r['objective'] - base) < 1e-9:
        q = r['quantities']
        print(i, list(q.keys())[:20] if isinstance(q, dict) else type(q))
        prm = q.get('physical_ramp_merge') if isinstance(q, dict) else None
        if prm: print(json.dumps(prm.get('accepted_vehicles_by_ramp')))
