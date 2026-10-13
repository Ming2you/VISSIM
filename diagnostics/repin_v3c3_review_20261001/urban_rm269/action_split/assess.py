"""Factorial model cost decomposition; no invented isolated native effects."""
import hashlib, json
from pathlib import Path

HERE=Path(__file__).resolve().parent
H=HERE.parent
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    out=HERE/'assessment.json'
    assert not out.exists()
    folder=HERE/'forecast2400_checked'
    forecast=read(folder/'summary.json')
    assert forecast['status']=='complete' and forecast['forecasts']==2
    assert forecast['depth']==3 and forecast['native_runs']==forecast['optimizer_calls']==0
    assert read(folder/'initialization_equivalence.json')['status']=='passed'
    for p,d in forecast['source_pins'].items():assert sha(Path(p))==d,p
    rows={name:read(H/'native_beta/forecast2400_checked'/(name+'.json')) for name in ('hold','selected')}
    rows.update({name:read(folder/(name+'.json')) for name in ('city_only','rm_only')})
    for r in rows.values():
        assert r['writer_validated'] and r['resource_max_exceedance']<1e-7 and r['conservation_states']==4
        assert abs(sum(r['costs_by_stock'].values())-r['omega_ttt_veh_h'])<1e-7
    caps={tuple(r['shared_constraints'][k]['target'] for k in ('np','nuf')) for r in rows.values()}
    assert len(caps)==1
    keys=set().union(*(r['costs_by_stock'] for r in rows.values()))
    deltas={name:{k:rows[name]['costs_by_stock'].get(k,0)-rows['hold']['costs_by_stock'].get(k,0) for k in keys}
            for name in ('city_only','rm_only','selected')}
    deltas['interaction']={k:deltas['selected'][k]-deltas['city_only'][k]-deltas['rm_only'][k] for k in keys}
    summary={name:dict(omega=sum(d.values()),mainline=sum(v for k,v in d.items() if k.startswith('freeway:')),
        nonmainline=sum(v for k,v in d.items() if not k.startswith('freeway:')),
        wout_storage=d.get('storage:SC1004_W_out',0)) for name,d in deltas.items()}
    assert abs(summary['selected']['omega']-sum(summary[n]['omega'] for n in ('city_only','rm_only','interaction')))<1e-7
    merge={name:{k:v-rows['hold']['predicted_merge']['accepted_vehicles_by_ramp'][k]
                 for k,v in r['predicted_merge']['accepted_vehicles_by_ramp'].items()} for name,r in rows.items() if name!='hold'}
    support=read(H/'native2400_analysis/initial_support_cost_diagnostic.json')
    groups=[]
    for g in support['groups']:
        groups.append(dict(stocks=g['stocks'],links=g['links'],native_joint_delta=g['native_delta'],
            model={name:sum(d.get(k,0) for k in g['stocks']) for name,d in deltas.items()}))
    groups.sort(key=lambda r:abs(r['model']['selected']-r['native_joint_delta']),reverse=True)
    result=dict(status='model_decomposition_complete',new_fixed450_forecasts=2,reused450_forecasts=2,new_native=0,new_optimizations=0,
        initial_sec=2400,end_sec=2850,delta_definition='Each action minus held; interaction=joint-city_only-rm_only+held.',
        baseline='native_beta/config.json; SC109 v12 candidate not enabled',
        delta_ttt_veh_h=summary,absolute_omega_veh_h={name:r['omega_ttt_veh_h'] for name,r in rows.items()},
        actual_joint_delta_omega_veh_h=read(H/'native2400_assessment.json')['delta_omega_veh_h']['actual'],
        extra_merge_by_ramp=merge,feasible={name:r['shared_constraints']['feasible'] for name,r in rows.items()},
        same_np_nuf_targets=list(next(iter(caps))),conservation_and_resource_checks_passed=True,
        model_cost_deltas_by_stock=deltas,initial_support_diagnostic=groups,initial_support_scope=support['scope'],
        limitations=['City-only/RM-only are model predictions, not measured native isolated effects.',
                    'Initial support geographic cost groups do not assign all future transit; full Omega cost is exact for the defined model ledger.',
                    'One saved state and seed; no proof of general control-gain calibration.'],
        calibration_control_gate_passed=False,runtime_pair_launched=False,
        source_pins={str(p):sha(p) for p in (Path(__file__),HERE/'plan.json',folder/'summary.json',
            H/'native_beta/forecast2400_checked/summary.json',H/'native2400_assessment.json',
            H/'native2400_analysis/initial_support_cost_diagnostic.json')})
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('delta_ttt_veh_h','actual_joint_delta_omega_veh_h','extra_merge_by_ramp','feasible')},indent=2))

if __name__=='__main__':main()
