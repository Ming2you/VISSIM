"""Saved local CTM with current command and a frozen downstream receiver.

Only the local roads,10643/10700,existing entry queues and actual exit receipts
advance. Other urban allocators/inflows are absent. This is not a full forecast.
"""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import copy,hashlib,importlib.util,json,pickle,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save=lambda p,x:p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')

def main():
    out=HERE/'saved_local.json';assert not out.exists()
    t0=time.perf_counter()
    source=HERE.parent/'multirate271/macro_hold_ad_v3_request.pickle'
    req=pickle.loads(source.read_bytes());cfg=req['owned'][0].cfg;initial=req['owned'][1]
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc_sequence
    from evaluation.controllers import lane_urban_runtime as lu
    from evaluation.controllers.runtime_setup import install_worker_runtime
    from evaluation.controllers.multirate_urban_clock import rebase_projection
    from evaluation.controllers.sdmpc_tangent_worker import state_error
    from evaluation.controllers.area_runtime import model_inventory
    install_worker_runtime(adapter,cfg,req['bootstrap']['state_json'],req['bootstrap']['detector_mapping'])
    control=sdmpc_sequence.actions(req['action'],3)[0]
    spec=importlib.util.spec_from_file_location('local_before276',HERE/'lane_urban_runtime.py.before')
    # .before deliberately has no executable suffix; load as source explicitly.
    from importlib.machinery import SourceFileLoader
    spec=importlib.util.spec_from_loader('local_before276',SourceFileLoader('local_before276',str(HERE/'lane_urban_runtime.py.before')))
    legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
    legacy.CandidateSignalProgram=lu.CandidateSignalProgram
    start=int(initial.time_sec)
    def stats(state):
        local=state.lane_urban_runtime
        return dict(urban_by_road={str(road):sum(q.stock for (r,l,c),q in local.port.urban.cells.items() if r==road)
                                  for road in local.local_storage},
            offramp=sum(p.stock for p in local.port.lanes),side=local.side_port.stock,
            movement={m:state.urban_movement_queue[m] for m in local.exits_by_movement},
            receiver={m:state.urban_link_storage[cfg.network.urban_movements[m]['receiving_link']] for m in local.exits_by_movement})
    def run(coarse,old=False):
        conf,state=copy.deepcopy((cfg,initial))
        if coarse:rebase_projection(conf,state)
        dt=int(conf.simulation.T_u_sec);local=state.lane_urban_runtime
        before=stats(state);total=0.;rows=[]
        for sec in range(start,start+10,dt):
            k=sec//dt;state.time_sec=sec
            # Freeze every other allocator, but open one current service visit.
            # This is explicitly a local response boundary, not a fabricated
            # completed urban advance or a coupled-model coverage certificate.
            state.route_choice_corridor_state.update(last_step=k,service_limit_veh={},service_used_veh={})
            state.native_input_route_state['last_step']=k
            state.native_input_prehead_state['last_step']=k
            state._control_area_ledger.begin_response_step('urban',sec,sec+dt)
            method=legacy.LaneUrbanRuntime.advance if old else lu.LaneUrbanRuntime.advance
            row=method(local,state,control,conf,k);total+=row['lane_urban_exit_veh'];rows.append(row)
            state._control_area_ledger.assert_stocks(model_inventory(state,conf))
        local.port.check();local.assert_pending(state)
        assert local.port.urban.time==start+10
        return state,dict(before=before,after=stats(state),exits=total,physical_time=local.port.urban.time,
                          service_used=state.route_choice_corridor_state['service_used_veh'])
    old,_=run(False,True);fine,f=run(False);coarse,c=run(True)
    error=state_error(old,fine);assert error<1e-9,error
    report=dict(status='complete_reviewed',scope=__doc__,source_sha256=sha(source),
        fine=f,coarse=c,old_default_state_error=error,canonical_stock_ledger_pass=True,
        local_substeps=10,global_urban_tick_sec=10,whole_scheduler_qualified=False,
        full_rollouts=0,full_sdmpc_selections=0,native_runs=0,wall_sec=time.perf_counter()-t0)
    save(out,report)
    print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
