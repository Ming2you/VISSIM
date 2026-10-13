
"""Focused context/bounds/writer/AD qualification; no native traffic execution."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
os.environ['RW_OFFSET_WRITER']='experiment'
import argparse,copy,hashlib,json,pickle,time
from collections import deque
from pathlib import Path
from types import SimpleNamespace
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers import sdmpc,sdmpc_regional_context as context_factory
from evaluation.controllers import area_follower_objective as joint,area_meter_finalization as meters
from evaluation.controllers import physical_ramp_branches,sdmpc_sequence,sdmpc_budget
from evaluation.controllers.sdmpc_tangent import prepare_request
from evaluation.controllers.sdmpc_tangent_surrogate import Query


def load(mode,path):
    x=pickle.loads(Path(path).read_bytes())
    c,s,f,h,m=x['args']
    config=json.loads(Path('diagnostics/solo355_local_20261013/'+mode+'_config.json').read_text(encoding='utf-8'))
    sdmpc.configure(config,c.cfg)
    return x


def prepare(x):
    c,s,f,h,m=x['args']
    return context_factory.prepare(c,s,f,h,m,derived=x['obs']['merged']['obs150_derived'],
        bootstrap=dict(x['kwargs']['worker_bootstrap'],runtime_sources={}))


def inputs(local,x):
    c,s,f,h,m=(local[k] for k in ('controller','state','forecast','historical','mapping'))
    cfg=c.cfg;mode=cfg.network.sdmpc_options['regional_prediction_prototype']
    policy=cfg.network.sdmpc_options
    reference=meters.prepare_held_actual_reference(h,cfg)
    bounds=physical_ramp_branches.configure_operating_bounds(s,cfg,reference) if mode=='freeway_only' else None
    callbacks,context,fingerprint=joint._joint_runtime_callbacks(c.nash_solver,s,f,h,reference,m,{},
        reference=reference,total_budget=None,directional={},tolerance=1e-7,regional_mode=mode)
    coord=sdmpc_sequence.SequenceCoordinates(cfg,reference,callbacks['move_box'],policy)
    from evaluation.controllers.urban_storage_guard import operating_seed
    seed=operating_seed(coord,reference,policy)
    template=prepare_request(c.nash_solver,s,f,reference,seed,coord,local['worker_bootstrap'])
    domain=({'np_values':(0.,)} if mode=='freeway_only' else joint.prepare_joint_leader_candidates(
        c,s,f,h,budget_tolerance_veh_h=1e-7,np_only=True))
    s._sdmpc_interval_sec=cfg.simulation.T_c_sec
    prices,price_receipt=sdmpc.load_prices(x['kwargs']['previous_path'],s,policy)
    del s._sdmpc_interval_sec
    view=dict(context=context,bootstrap=local['worker_bootstrap'],bounds=bounds,axes=coord.axes,
        lower=coord.lower,upper=coord.upper,owners=coord.owners,leader_domain=domain,
        active_prices=prices,move_box=callbacks['move_box'].entries,seed=seed)
    return SimpleNamespace(view=view,template=template,coord=coord,seed=seed,reference=reference,
        callbacks=callbacks,context=context,local=local,fingerprint=fingerprint)


def canonical(value):
    if value is None or isinstance(value,(str,int,float,bool)):return value
    if isinstance(value,dict):return {str(k):canonical(v) for k,v in sorted(value.items(),key=lambda row:str(row[0]))}
    if isinstance(value,(list,tuple,deque)):return [canonical(v) for v in value]
    if isinstance(value,(set,frozenset)):return sorted((canonical(v) for v in value),key=repr)
    if hasattr(value,'tolist'):return canonical(value.tolist())
    if hasattr(value,'__dict__'):
        return {'type':type(value).__module__+'.'+type(value).__qualname__,'fields':canonical(vars(value))}
    raise TypeError(type(value))


def token(value):
    return hashlib.sha256(json.dumps(canonical(value),sort_keys=True,allow_nan=False).encode()).hexdigest()


def evaluate(prepared,x):
    query=Query(prepared.template,lambda *_:None,lambda *a,**kw:None)
    start=time.perf_counter()
    try:
        item=query.evaluate([prepared.seed],derivatives=True)[0]
        derivative=query.derivative(prepared.seed)
        action,initial=sdmpc_budget.initialize(prepared.local['controller'].nash_solver,
            prepared.local['state'],prepared.seed,item,x['kwargs']['options'])
        query.bind_warm_budget(prepared.seed,action,x['kwargs']['options'])
        bound=query.evaluate([action],derivatives=True)[0]
        held=joint.validate_actual_decision_hold(prepared.local['controller'].nash_solver,
            prepared.local['state'],action,bound,callbacks=prepared.callbacks,context=prepared.context,
            source_fingerprint='regional-context-qualification',options=x['kwargs']['options'])
        assert held['feasible']
        return dict(response=bound,derivative=derivative,writer=held['command_evidence'],
            feasible=held['feasible'],initialization=initial,seconds=time.perf_counter()-start,
            query_stats=query.stats())
    finally:query.close()


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--mode',required=True,choices=context_factory.regional_modes())
    p.add_argument('--capture',default='D:/VISSIM_analysis/20261013_solo355_local/projected.pkl')
    p.add_argument('--output',required=True)
    p.add_argument('--evaluate',action='store_true')
    a=p.parse_args()
    x=load(a.mode,a.capture);local=prepare(x);prepared=inputs(local,x)
    result=dict(mode=a.mode,stage='context_preparation',native_runs=0,full_selections=0,
        complete_context_sha256=token(prepared.view),axes=len(prepared.coord.axes),
        leader_domain=prepared.view['leader_domain'])
    if a.evaluate:result['evaluation']=evaluate(prepared,x)
    Path(a.output).write_text(json.dumps(canonical(result),indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='evaluation'}),flush=True)


if __name__=='__main__':main()
