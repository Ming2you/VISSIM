"""Compare two completed fixed RM responses; no new forecasts or native reads."""
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
R=HERE.parent
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
C=R/'sc1001_connection'
pins={}


def read(path):
    raw=path.read_bytes();pins[str(path)]=hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if path.suffix=='.gz' else raw)


def summarize(result):
    cost=result['cost_by_stock'];flows=result['control_area']['flow_counts']
    return dict(omega=result['ttt_omega_veh_h'],east=cost['freeway:FW_E'],west=cost['freeway:FW_W'],
        ramps=sum(v for k,v in cost.items() if k.startswith('ramp:')),
        outside=result['tracked_outside_residence_veh_h'],
        source=flows['origin:FW_E->freeway:FW_E'],
        merge=sum(v for k,v in flows.items() if k.startswith('merge_pending:') and k.endswith('->freeway:FW_E')),
        off=sum(v for k,v in flows.items() if k.startswith('freeway:FW_E->storage:')),
        terminal=flows['freeway:FW_E->external:terminal:FW_E'])


def main():
    target=HERE/'assessment.json'
    if target.exists():raise FileExistsError(target)
    old=read(I/'closedloop_recorded2700_lever450_sc1001_causal_history_routes/summary.json')
    new=read(I/'closedloop_recorded2700_lever450_sc1001_routed_history_s47/summary.json')
    actual=read(C/'assessment.json')['rm_delta_veh_h']
    prior=read(R/'sc1001_route_inventory_s43/rm47_model_flow_comparison.json')
    proof=read(I/'native_rm_observation2700_writerfix_v3/analysis/summary.json')
    assert proof['paired_prefix_exact'] and all(a['native_execution_passed'] for a in proof['arms'].values())
    base=read(C/'candidate_config.json');route=read(C/'candidate_route_inventory.json')
    route['freeway'].pop('offramp_route_inventory');assert route==base
    cases={};max_route=max_resource=0.;sec=0.
    for number,(arm,key) in enumerate((('hold','held_actual'),('release','release_actual'))):
        a,b=old['results'][key],new['results'][key]
        assert a['commands']==b['commands'] and a['physical_cell_states'][0]==b['physical_cell_states'][0]
        sec+=b['wall_sec']
        trace=read(C/f'sc1001_routed_history_s47_response_{number}.json.gz')
        assert len(trace['quantities']['owners'])==17
        max_resource=max(max_resource,trace['resource_max_exceedance'])
        for state in trace['route_inventory_checks']:
            max_route=max(max_route,max(v['max_cell_residual'] for v in state['roads'].values()))
        cases[arm]=dict(before=summarize(a),after=summarize(b),native_flow=prior['cases'][arm]['native'],
                       native_omega=proof['arms'][arm]['TTT_2700p1_3150_veh_h'])
    assert max_route<1e-7 and max_resource<1e-7
    delta={mode:{k:cases['release'][mode][k]-cases['hold'][mode][k] for k in cases['hold'][mode]}
           for mode in ('before','after')}
    delta['native']={**prior['release_minus_hold']['native'],
        'omega':actual['actual_Omega'],'east':actual['actual_FW_E'],'ramps':actual['actual_ramps'],
        'outside':proof['delta_outside_Omega_residence_veh_h']}
    assert delta['before']['omega']>0 and delta['after']['omega']>0 and delta['native']['omega']>0
    out=dict(status='RM_SIGN_RETAINED_NET_GAIN_ERROR_WORSE_NO_ADOPTION',cases=cases,release_minus_hold=delta,
        same_commands_and_initial_physical_stocks=True,config_diff_only_route_inventory=True,
        max_route_residual=max_route,max_resource_exceedance=max_resource,forecasts=2,forecast_compute_sec=sec,
        new_native=0,fzp_reads=0,coefficient_fit=0,source_pins=pins,
        limitations=['Existing seed47, not a new holdout.','Native phase0.1s and5s integration differ from scalar model.',
          'This routed candidate already fails seed43 VSL sign; preserving this RM sign does not qualify it.',
          'Prior native execution and exact prefix receipts reused, not re-scanned.'])
    target.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:out[k] for k in ('status','release_minus_hold','forecast_compute_sec','max_route_residual','max_resource_exceedance')},ensure_ascii=False))


if __name__=='__main__':main()
