"""Read-only numerical review of the completed tail and physical-clock pair."""
from pathlib import Path
import json,math,pickle
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.tail337.prepare import HERE,S,read,save

def main():
    tail=read(HERE/'tail_summary.json'); physical=read(HERE/'physical_v2/summary.json')
    assert read(HERE/'tail_execution.json')['status']=='complete'
    assert physical['status']=='complete' and physical['both_shared_feasible']
    old=read(S/'full3300/unused.joint.json')['selection']['meter_neighbor_audit']['budget_audits']
    replay=tail['finite_rm']['budget_audits'][1:]
    assert len(old)==len(replay)==2
    for a,b in zip(old,replay):
        assert a['incumbent_action_token']==b['incumbent_action_token']
        assert a['selected']==b['selected'] and len(a['candidates'])==len(b['candidates'])
        for x,y in zip(a['candidates'],b['candidates']):
            assert x['candidate']==y['candidate'] and x['feasible']==y['feasible']
            assert abs(x['objective']-y['objective'])<=1e-8
    assert tail['new_predictions']==17 and tail['cache']['tangent_rollouts']==0
    from evaluation.controllers import sdmpc_sequence as seq
    record=pickle.loads((HERE/'selected.pickle').read_bytes())
    for a,b in zip(seq.actions(record['held'][0],3),seq.actions(record['selected'][0],3)):
        assert a.green_times==b.green_times and a.offsets==b.offsets and a.vsl==b.vsl
        assert a.N_P_star==b.N_P_star and a.N_UF_star==b.N_UF_star
    held,selected=(physical['results'][k] for k in ('held','selected'))
    costs={k:selected['inside_costs'].get(k,0)-held['inside_costs'].get(k,0)
           for k in selected['inside_costs'].keys()|held['inside_costs'].keys()}
    assert abs(sum(costs.values())-physical['delta_ttt'])<1e-7
    results=dict(status='passed',saved_budget_audits_equivalent=True,
        changed_only_rm_between_held_and_selected=True,new_scalar_forecasts=17,
        completed_physical_forecasts=2,failed_recording_attempt_computed_forecasts=1,
        discarded_attempt_reason='Set-valued report field was not JSON serializable; failed output retained, no model change',
        continuous_delta=tail['selected']-tail['initial'],physical_clock_delta=physical['delta_ttt'],
        same_direction=tail['selected']<tail['initial'] and physical['delta_ttt']<0,
        physical_percent=100*(held['omega_ttt']-selected['omega_ttt'])/held['omega_ttt'],
        ramp10681_merge_held=held['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681'],
        ramp10681_merge_selected=selected['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681'],
        ramp10681_cost_delta=costs['ramp:RM_C10681'],
        downstream_SC1004_W_out_cost_delta=costs['storage:SC1004_W_out'],
        approach52_cost_delta=selected['group_costs']['approach52']-held['group_costs']['approach52'],
        freeway_E_cost_delta=costs['freeway:FW_E'],
        outside_cost_delta=sum(selected['outside_costs'].values())-sum(held['outside_costs'].values()),
        important_limits=['One3300 state, no unseen state/seed verified here','Four ramps change together; not isolated10681 causality',
                          'Physical-clock model is not native VISSIM','SC1004_W_out is a model storage group, not a new exact68 lane metric',
                          'Net effect small; no calibration performed to fit its sign'],
        new_full_optimizer=0,new_native=0,goal_complete=False)
    save('review.json',results)
    print(json.dumps(results,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
