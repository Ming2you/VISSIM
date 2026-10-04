"""Read a saved state through the canonical initializer, without a rollout."""
import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT))
from evaluation.controllers import observation_projection as projection, obs150_contract as oc

label,sec=sys.argv[1],int(sys.argv[2])
held450=sys.argv[3:]==['--held450']
assert len(sys.argv)==3 or held450
if held450:
    assert sec==4050
    import ctypes
    kernel32=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel32.GetCurrentProcess.restype=ctypes.c_void_p
    kernel32.SetPriorityClass.argtypes=(ctypes.c_void_p,ctypes.c_uint32)
    kernel32.SetPriorityClass.restype=ctypes.c_int
    if not kernel32.SetPriorityClass(kernel32.GetCurrentProcess(),0x4000):
        raise ctypes.WinError(ctypes.get_last_error())
target=HERE/(label+'.json')
assert not target.exists()
evidence={'label':label,'sec':sec,'new_rollouts':0,'native_started':False}
if held450:
    from src.controllers import rollout_endpoint as endpoint
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    evaluate=endpoint.evaluate_price_point
    def checked_evaluate(state,action,forecast,prices,spec,**kwargs):
        point=evaluate(state,action,forecast,prices,spec,**kwargs)
        evidence['new_rollouts']+=1
        assert evidence['new_rollouts']==1 and len(point.states)==3 and not point.aborted
        checked=[]
        for saved in (state,*point.states):
            get_ledger(saved).assert_stocks(model_inventory(saved,spec.cfg))
            if hasattr(saved,'sc1001_approach'):saved.sc1001_approach.assert_network_mirror(saved,spec.cfg)
            tags=getattr(saved,'gate_initial_route_tags',{}).get('in_SC1004_S',{})
            checked.append(dict(time_sec=saved.time_sec,initial_tag_veh=sum(sum(row.values()) for row in tags.values())))
        exceedance=max((r['exceedance_veh'] for r in point.control_area_response['resource_allocations']),default=0.)
        assert exceedance<1e-7 and checked[-1]['initial_tag_veh']==0.
        evidence['rollout_checks']=dict(saved_states=checked,max_resource_exceedance_veh=exceedance)
        return point
original=projection.initialize_kinematic_arrivals
def inspect(adapter,state,cfg,tuning,raw,detectors):
    def snapshot():
        origin='in_SC1004_S'
        return copy.deepcopy(dict(support=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link'].get('66'),
            storage=state.urban_link_storage[origin],arrival=state.urban_arrival_buffer.get(origin,{}),
            release=state.urban_storage_release_buffer.get(origin,{}),
            queues={k:v for k,v in state.urban_movement_queue.items() if cfg.network.urban_movements[k].get('origin')==origin},
            all_storage=state.urban_link_storage,all_queue=state.urban_movement_queue,
            all_arrival=state.urban_arrival_buffer,all_release=state.urban_storage_release_buffer,
            tags=getattr(state,'gate_initial_route_tags',{}),
            stock_assignment=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']))
    evidence['before']=snapshot()
    try:
        metadata=original(adapter,state,cfg,tuning,raw,detectors)
    except Exception as error:
        evidence['error']=dict(type=type(error).__name__,message=str(error))
        raise
    evidence['after']=snapshot(); evidence['metadata']=metadata
    return metadata
projection.initialize_kinematic_arrivals=inspect
def readonly_derived(raw,derived):
    # Raw native evidence is immutable. Verify its previously written cache.
    path=oc.resolve(raw[oc.RAW_STATE_KEY],oc.derived_path(derived['sim_sec']))
    assert path.read_bytes()==oc.derived_bytes(derived)
    return path
oc.write_derived=readonly_derived
driver=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/probe_selected_arrival_path.py'
spec=importlib.util.spec_from_file_location('queue_zero_driver',driver)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
if held450:
    original_probe=module.probe_levers
    def checked_probe(*args,**kwargs):
        # Install after area_runtime wraps the endpoint and attaches its ledger.
        global evaluate
        evaluate=endpoint.evaluate_price_point
        endpoint.evaluate_price_point=checked_evaluate
        try:return original_probe(*args,**kwargs)
        finally:endpoint.evaluate_price_point=evaluate
    module.probe_levers=checked_probe
sys.argv=[str(driver),'--closedloop-recorded',f'--at={sec}','--held450' if held450 else '--initialize-only','--warm-head-history','--replay-vsl-history',
    '--recording-dir=D:/VISSIM_runs/20261003_service66_posthead_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29',
    '--tuning-json='+str(ROOT/'diagnostics/repin_v3c3_review_20261001/rm47_service66_response/candidate_config.json'),
    '--probe-label=queuezero79_'+label]
try:
    module.main();evidence['completed']=True
except Exception as error:
    evidence['completed']=False;evidence['outer_error']=dict(type=type(error).__name__,message=str(error))
finally:
    evidence['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        (Path(projection.__file__),ROOT/'evaluation/controllers/runtime_setup.py',ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py',driver)}
    target.write_text(json.dumps(evidence,indent=2,allow_nan=False),encoding='utf-8')
print(json.dumps({k:v for k,v in evidence.items() if k not in ('before','after','source_sha256')}))
sys.exit(0 if evidence['completed'] else 1)
