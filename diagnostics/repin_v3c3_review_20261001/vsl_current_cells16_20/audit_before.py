"""One recorded current-state projection audit; no solve or native execution."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'

def main():
    global HERE
    from evaluation.controllers import runtime_setup,obs150_contract as oc
    mode=sys.argv[1]
    label='u7'
    for option in sys.argv[2:]:
        if option.startswith('--output-dir='): HERE=ROOT/option.split('=',1)[1]
        elif option.startswith('--label='): label=option.split('=',1)[1]
        else: raise ValueError('Unknown audit option: '+option)
    assert mode in ('before','after','before47','after47','after43','after_rm47')
    rm_pair=mode=='after_rm47'
    forecast=mode.endswith(('47','43'))
    target=HERE/(mode+'.json')
    assert not target.exists(),target
    config=HERE/'candidate_config.json' if mode.startswith('after') else HERE.parent/'retained10638/candidate_config.json'
    script=I/'probe_selected_arrival_path.py'
    spec=importlib.util.spec_from_file_location('u7_current_probe',script)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    if forecast:
        original_probe=module.probe_levers
        def with_trace(*args,**kwargs):
            from src.controllers import rollout_endpoint as endpoint
            captured=args[0];cfg=captured['cfg'];original=endpoint.evaluate_price_point
            points=[]
            def evaluate(*a,**kw):
                assert len(points)<(4 if mode.endswith('43') else 2)
                point=original(*a,**kw)
                source='in_SC1004_S'
                movements=[m for m,spec in cfg.network.urban_movements.items() if spec.get('origin')==source]
                relevant=lambda key:key=='storage:'+source or key=='transit:gate:'+source or key in {'movement:'+m for m in movements}
                response=point.control_area_response
                points.append(dict(states=[dict(time_sec=s.time_sec,
                    queue={m:s.urban_movement_queue[m] for m in movements},
                    storage=cfg.network.urban_link_storage_veh[source]-s.urban_link_storage[source],
                    gate_transit=sum(s.urban_inflow_transit_buffer.get('gate:'+source,{}).values())) for s in (a[0],*point.states)],
                    transfers=[r for r in response['transfers'] if relevant(r['source']) or relevant(r['target'])],
                    residence=[dict(time_sec=r['end_sec'],dt_h=r['dt_h'],
                        stock={k:v for k,v in r['model_stock_veh'].items() if relevant(k)})
                        for r in response['residence'] if r['stage']=='urban'],
                    resource_max=max((r['exceedance_veh'] for r in response['resource_allocations']),default=0.)))
                if rm_pair:
                    from evaluation.controllers.area_runtime import model_inventory
                    from evaluation.controllers.control_area_objective import get_ledger
                    inventories=[]
                    for state in (a[0],*point.states):
                        inventory=model_inventory(state,cfg)
                        get_ledger(state).assert_stocks(inventory)
                        inventories.append(dict(time_sec=state.time_sec,stock=inventory))
                    flows={}
                    for row in response['transfers']:
                        key=(row['source'],row['target'],row['route_key'])
                        flows[key]=flows.get(key,0.)+row['vehicles']
                    points[-1]['full_stock_witness']=inventories
                    points[-1]['all_transfers_aggregated']=[dict(source=k[0],target=k[1],route_key=k[2],vehicles=v)
                                                           for k,v in flows.items()]
                (HERE/(mode+'_local.json')).write_text(json.dumps(points,ensure_ascii=False)+'\n',encoding='utf-8')
                return point
            endpoint.evaluate_price_point=evaluate
            try:return original_probe(*args,**kwargs)
            finally:endpoint.evaluate_price_point=original
        module.probe_levers=with_trace
    def existing(raw,derived):
        obs=raw[oc.RAW_STATE_KEY];p=oc.resolve(obs,oc.derived_path(obs['sim_sec']))
        assert p.read_bytes()==oc.derived_bytes(derived)
        return p
    oc.write_derived=existing
    configure=runtime_setup.configure_runtime
    result_doc={}
    def capture(*args,**kwargs):
        result=configure(*args,**kwargs)
        state,detectors,metadata=result;adapter,cfg,tuning,mapping,raw=args[:5]
        source='in_SC1004_S'
        from src.models.urban_queue_model import approach_routing
        routing=dict(approach_routing(cfg)[source])
        summary=state.local_observation_summary
        result_doc.update(source=source,raw_time=raw['sim_sec'],routing=routing,
            queue={m:state.urban_movement_queue[m] for m in routing},
            storage_capacity=cfg.network.urban_link_storage_veh[source],
            storage_veh=cfg.network.urban_link_storage_veh[source]-state.urban_link_storage[source],
            arrival=state.urban_arrival_buffer.get(source),release=state.urban_storage_release_buffer.get(source),
            tags=getattr(state,'gate_initial_route_tags',{}).get(source),
            current_records=[r for r in raw['vehicle_records']['records'] if r['link_no']==66],
            lane_queues={str(k):v for k,v in adapter._contiguous_stopline_queue(raw,per_lane=True).items() if k[0]=='66'},
            projection=summary['projection_diagnostics']['physical_stock_assignment_by_link'].get('66'),
            movement_specs={m:cfg.network.urban_movements[m] for m in routing},
            movement_capacities={m:cfg.network.movement_capacity_by_movement_veh_h[m] for m in routing},
            physical_head_resources=getattr(cfg.network,'head_service_resources',None),
            detector_origins={k:v for k,v in detectors['link_to_origins'].items() if source in v},
            head_lane_support=getattr(cfg.network,'head_queue_movement_lanes',{}).get('66'),
            metadata={k:v for k,v in metadata.items() if 'arrival' in k or 'kinematic' in k},
            config_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),new_forecasts=0)
        return result
    runtime_setup.configure_runtime=capture
    recording=Path('D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47')
    sys.argv=[str(script),'--closedloop-recorded','--at=2700','--warm-head-history','--replay-vsl-history',
              '--initialize-only','--output-suffix='+label+'_'+mode,'--recording-dir='+str(recording),
              '--fixed-replay-summary='+str(I/'native_rm_observation2700_writerfix_v3/analysis/summary.json'),
              '--tuning-json='+str(config)]
    if forecast:
        sys.argv.remove('--initialize-only')
        if not rm_pair:
            sys.argv.append('--trace-ramp=RM_C10681')
        if mode.endswith('43'):
            proof=I/'seed43_fullplant_20260929/analysis_v2/observation_reuse.json'
            receipt=json.loads(proof.read_bytes())
            assert receipt['passed'] and receipt['seed']==43
            sys.argv=[x for x in sys.argv if not x.startswith(('--at=','--recording-dir=','--fixed-replay-summary='))]
            sys.argv.extend(['--at=2250','--recording-dir='+receipt['recording_dir'],'--four-arm-receipt='+str(proof)])
        elif rm_pair:
            sys.argv.append('--lever-probe450')
        else:
            executed=I/'closedloop_recorded2700_native_selected_res47v2'
            proof=json.loads((executed/'analysis/summary.json').read_bytes())
            assert proof['counterfactual_valid'] and proof['paired_prefix_exact'] and proof['common_start_vehicle_records_exact']
            assert all(a['native_execution_passed'] for a in proof['arms'].values())
            action=I/'closedloop_recorded2700_select_res47v2/unused_action.json'
            pins=json.loads((executed/'protocol.json').read_bytes())['command_pins']
            assert hashlib.sha256(action.read_bytes()).hexdigest()==pins[str(action)]
            sys.argv.extend(['--selection-check','--probe-label='+label+'_'+mode,'--selection-reference='+str(action.parent)])
    try:module.main()
    finally:runtime_setup.configure_runtime=configure
    target.write_text(json.dumps(result_doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    result_doc['new_forecasts']=4 if mode.endswith('43') else 2 if forecast else 0
    target.write_text(json.dumps(result_doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result_doc[k] for k in ('source','queue','storage_veh','new_forecasts')},ensure_ascii=False))

if __name__=='__main__':main()
