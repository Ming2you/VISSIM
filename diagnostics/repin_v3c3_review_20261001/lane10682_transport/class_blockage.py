"""Explain the rejected candidate's false exit-lane retention; no new forecast."""
import gzip
import importlib.util
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
path=HERE.parent/'lane10682_feasibility/check_partition.py'
spec=importlib.util.spec_from_file_location('previous_partition',path)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
mod.Partition.setUpClass()
worker=mod.Partition('test_lane_initialization_preserves_each_class_and_native_lane_mass')
def mass(row,target):return sum(n for k,n in row.items() if k.endswith('|'+target))
result={}
for seed,start,end,prefix in [(43,2250,2700,'closedloop_recorded2250_lever450_trace10681_'),
                            (47,2700,3150,'closedloop_recorded2700_select_check_trace10681_')]:
    path=I/(prefix+'lane10682_transport_multi'+str(seed))/'held_actual_RM_C10681_trace.json.gz'
    trace=json.loads(gzip.decompress(path.read_bytes()))
    states=trace['offramp_network_diagnostics']['route_states']
    final=states[-1]['inventory']['lane_cells']['FW_E']
    observed=next(f for f in mod.Partition.fixtures if f['seed']==seed and f['time']==end)
    obs,_=worker.initialize(observed,observed['partition'])
    native=obs.offramp_route_inventory_state['lane_cells']['FW_E']
    initial=states[0]['inventory']['cells']['FW_E']
    result[str(seed)]=dict(
        time_window=[start,end],
        first_exit_initial_inlet_target_stock=mass(initial[8],'10643'),
        first_exit_missing_target_share_fallback=[.25]*4,
        ending10643_target_by_lane=[mass(row,'10643') for row in final[9]],
        observed10643_target_by_group=[mass(row,'10643') for row in native[9]],
        observed_group_meaning=['lane1','lane2','lanes3_and4'],
        predicted10643_inaccessible_stock=mass(final[9][2],'10643')+mass(final[9][3],'10643'),
        observed10643_inaccessible_stock=mass(native[9][2],'10643'),
        ending10682_target_by_lane=[mass(row,'10682') for row in final[11]],
        interpretation='The prototype freezes a target-specific inlet share from one short cell; an absent target falls back to uniform lanes. Unconditional exchange then retains target vehicles in inaccessible lanes. This diagnoses the new candidate, not the retained baseline.')
target=HERE/'class_blockage.json';assert not target.exists()
target.write_text(json.dumps(dict(status='rejected_candidate_diagnosis',cases=result,
    new_forecasts=0,new_fzp=0,new_native=0,future_truth_used_only_for_evaluation=True),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(result,ensure_ascii=False))
