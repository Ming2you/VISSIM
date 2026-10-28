# V1c (VSL_OFFLINE, data-after declaration): per decision, read only: original_held_candidate,
# meter audit baseline/selected objective, and VSL of the 3-block selected plan (block 0 = written,
# blocks 1-2 = diagnostics.sdmpc_prediction_sequence.future). No model run.
import json, sys
RUNS = {'a1': 'D:/VISSIM_runs/20261025_codex_a1_s29/sdmpc/decisions_sdmpc31_sdmpc8100_s29',
        'joint': 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29'}
PLAN = [('a1', t) for t in (1650, 1800, 1950, 3000, 3450, 3600, 3750, 3900, 4050, 4200, 4350, 4500, 4650)] + \
       [('joint', t) for t in (1650, 1800, 1950, 3450, 3900, 4350, 4500, 4650)]
KEYS = ('FW_E__seg2', 'FW_E__seg5', 'FW_E__seg10', 'FW_E__seg13', 'FW_W__seg2', 'FW_W__seg5', 'FW_W__seg10', 'FW_W__seg13')
out = []
for arm, T in PLAN:
    o = json.load(open(f'{RUNS[arm]}/action_{T:06d}.json', encoding='utf-8'))
    j = o['metadata']['joint_leader_selection']
    seq = (o.get('diagnostics') or {}).get('sdmpc_prediction_sequence') or {}
    blocks = [{k: o['vsl'].get(k) for k in KEYS}] + [{k: b['vsl'].get(k) for k in KEYS} for b in seq.get('future', [])]
    h = j.get('original_held_candidate') or {}
    na = j.get('meter_neighbor_audit') or {}
    rec = dict(arm=arm, T=T, plan_vsl_non110=[{k: v for k, v in b.items() if v is not None and abs(v - 110) > 1e-9} for b in blocks],
               held_candidate={k: h.get(k) for k in ('evaluated', 'selected', 'reason', 'objective', 'objective_veh_h', 'reference_source') if k in h},
               held_candidate_keys=sorted(h.keys()), audit_selected=na.get('selected'), audit_baseline=na.get('baseline_objective'),
               selected_objective=j.get('selected_objective'), warm_start_objective=j.get('warm_start_objective'),
               pfo_initial=(j.get('pfo_warm_start') or {}).get('initial_omega_objective'),
               candidates=[(c.get('nuf_target'), c.get('status'), c.get('objective')) for c in j.get('candidates', [])])
    out.append(rec)
    print(json.dumps(rec)[:900], flush=True)
json.dump(out, open(sys.argv[1], 'w', encoding='utf-8'), indent=1)
