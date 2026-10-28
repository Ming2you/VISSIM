r"""VERIFY_N2: W264 (64cf-s29, codex ca181e84 window264) decision JSON neighbor-audit check, fresh code, read only."""
import io, json, os, sys, hashlib
D = r'D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc/decisions_sdmpc31_sdmpc9000_s29'
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'out')
res = {}
for T in (1200, 1500, 1650, 1800, 1950):
    p = os.path.join(D, 'action_%06d.json' % T)
    raw = open(p, 'rb').read()
    d = json.loads(raw.decode('utf-8'))
    jl = d['metadata']['joint_leader_selection']
    a = jl['meter_neighbor_audit']
    per = {}
    for b in a['budget_audits']:
        for c in b['candidates']:
            per.setdefault(c['candidate'], []).append(round(c['delta_veh_h'], 6))
    fc = jl.get('final_constraints', {})
    prm = fc.get('physical_ramp_merge')
    trial = jl.get('trial_rows')
    tr0 = None
    if isinstance(trial, list):
        for r in trial:
            if isinstance(r, dict) and abs(float(r.get('objective', r.get('ttt_veh_h', -1)) or -1) - a['baseline_objective']) < 1e-9:
                tr0 = r
                break
    res[T] = {'sha256': hashlib.sha256(raw).hexdigest(), 'baseline_objective': a['baseline_objective'], 'selected': a['selected'],
              'selected_objective': jl.get('selected_objective'), 'n_candidates': len(a['candidates']),
              'n_budget': len(a['budget_audits']), 'delta_by_candidate': per,
              'final_merge_keys': (list(prm.keys())[:10] if isinstance(prm, dict) else type(prm).__name__),
              'trial_row_keys': (list(tr0.keys())[:30] if tr0 else None),
              'trial_rows_type': type(trial).__name__, 'trial_rows_len': (len(trial) if hasattr(trial, '__len__') else None)}
    if T == 1800:
        res[T]['final_merge'] = prm
        res[T]['trial0_merge'] = (tr0 or {}).get('physical_ramp_merge') if tr0 else None
        if isinstance(trial, list) and trial and isinstance(trial[0], dict):
            res[T]['trial_first_keys'] = list(trial[0].keys())
            res[T]['trial_objs'] = [r.get('objective') for r in trial[:12]]
    del d, raw
    print(T, res[T]['sha256'][:8], res[T]['baseline_objective'], res[T]['selected'], res[T]['selected_objective'], res[T]['n_candidates'], flush=True)
    for k, v in sorted(per.items()):
        print('   %-22s %s' % (k, v))
with io.open(os.path.join(OUT, 'v2_w264.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, indent=1, default=str)
