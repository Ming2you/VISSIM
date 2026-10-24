"""Actual transformed saved local10s response; signal AD vs central differences."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import copy,json,pickle,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]

def main():
    output=HERE/'reverse_local.json';assert not output.exists()
    from evaluation.controllers.sdmpc_tangent_runtime import install
    finder=install(ROOT,backend='reverse-v1')
    req=pickle.loads((HERE.parent/'multirate271/macro_hold_ad_v3_request.pickle').read_bytes())
    cfg=req['owned'][0].cfg;initial=req['owned'][1]
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc_sequence,sdmpc_continuous
    from evaluation.controllers.runtime_setup import install_worker_runtime
    from evaluation.controllers.multirate_urban_clock import rebase_projection
    install_worker_runtime(adapter,cfg,req['bootstrap']['state_json'],req['bootstrap']['detector_mapping'])
    sdmpc_continuous.install(cfg)
    action=sdmpc_sequence.actions(req['action'],3)[0]
    axes=[('green',k) for k in sorted(action.green_times) if k.startswith('SC1004_')]+[('offset','SC1004')]
    def evaluate(control):
        conf,state=copy.deepcopy((cfg,initial));rebase_projection(conf,state)
        k=int(state.time_sec//10)
        state.route_choice_corridor_state.update(last_step=k,service_limit_veh={},service_used_veh={})
        state.native_input_route_state['last_step']=k;state.native_input_prehead_state['last_step']=k
        state._control_area_ledger.begin_response_step('urban',state.time_sec,state.time_sec+10)
        local=state.lane_urban_runtime;row=local.advance(state,control,conf,k)
        return [row['lane_urban_exit_veh'],row['lane_urban_stock_veh'],sum(p.stock for p in local.port.lanes)]
    trace=finder.ad.Trace([1.]*len(axes));taped=action.copy()
    def field(control,kind):return control.green_times if kind=='green' else control.offsets
    for j,(kind,key) in enumerate(axes):
        values=field(taped,kind);values[key]=finder.ad.Dual(values[key],{j:1.},trace)
    values=evaluate(taped);jac=trace.jacobian(values,workers=1).tolist()
    scalar=evaluate(action);eps=1e-4;fd=[]
    for kind,key in axes:
        plus=action.copy();minus=action.copy()
        field(plus,kind)[key]+=eps;field(minus,kind)[key]-=eps
        a,b=evaluate(plus),evaluate(minus)
        fd.append([(x-y)/(2*eps) for x,y in zip(a,b)])
    fd=list(map(list,zip(*fd)))
    primal_error=max(abs(finder.ad.primal(a)-b) for a,b in zip(values,scalar))
    derivative_error=max(abs(a-b) for row,reference in zip(jac,fd) for a,b in zip(row,reference))
    assert primal_error<1e-8 and derivative_error<1e-5,(primal_error,derivative_error)
    assert any(p.endswith('lane_urban_runtime.py') for p in finder.source_hashes)
    assert any(p.endswith('route_choice_corridor.py') for p in finder.source_hashes)
    result=dict(status='actual_coarse_local_reverse_pass',axes=axes,outputs=['exits','local_stock','offramp_stock'],
        values=[finder.ad.primal(v) for v in values],jacobian=jac,central_difference=fd,
        primal_error=primal_error,derivative_error=derivative_error,epsilon=eps,
        nonzero_derivatives=sum(abs(x)>1e-7 for row in jac for x in row),operations=trace.result()['operations'],
        scope='Saved2400 local CTM only; downstream/incoming allocators frozen. Continuous signal controls, not full213axis plant/choice.',
        transformed_sources=finder.source_hashes)
    output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='transformed_sources'},ensure_ascii=False))
if __name__=='__main__':main()
