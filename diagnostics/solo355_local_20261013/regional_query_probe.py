"""Offline Query/AD integration milestone; not solver or input-isolation proof."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,json,math,pickle,time
from pathlib import Path
from types import SimpleNamespace
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers import sdmpc_regional_prototype as regional
from evaluation.controllers import sdmpc_sequence,sdmpc_actuator_scope
from evaluation.controllers import area_meter_finalization as meters,physical_ramp_branches
from evaluation.controllers import joint_owner_game,joint_owner_neighbors,area_follower_objective as joint
from evaluation.controllers.sdmpc_tangent_surrogate import Query

p=argparse.ArgumentParser();p.add_argument('--mode',required=True,choices=('freeway_only','urban_only'))
p.add_argument('--output',required=True);p.add_argument('--scalar',action='store_true')
p.add_argument('--capture',default='D:/VISSIM_analysis/20261013_solo355_local/projected.pkl')
a=p.parse_args();x=pickle.loads(Path(a.capture).read_bytes())
c,s,f,h,m=x['args'];cfg=c.nash_solver.cfg;policy=cfg.network.sdmpc_options
config=json.loads(Path('diagnostics/solo355_20261012/'+a.mode+'_config.json').read_text(encoding='utf-8-sig'))
policy['actuator_scope']=sdmpc_actuator_scope.configure(config['adapter']['sdmpc_actuator_scope'],cfg)
# This bounded worker integration explicitly excludes the unqualified global
# state registry and cache. It is not the production optimizer policy.
for key in ('central_multiplier','response_cap_cache','fast_primitives','prediction_hotpath',
            'stock_geometry_hotpath','receiving_geometry_cache','prediction_cache','compact_audit',
            'persistent_urban_fifo','array_urban_pipeline','array_transport','spatial_receiving'):
    policy[key]=False
policy.update(regional_prediction_prototype=a.mode,surrogate_reuse=True,tangent_backend='reverse-v1',derivative_workers=1)
boundary=regional.boundary_requests(x['obs']['merged']['obs150_derived'],a.mode,s.time_sec,cfg.network.ramps,s.lane_freeway_runtime.offramps)
local=regional.project_state(s,cfg,a.mode,boundary)
reference=meters.prepare_held_actual_reference(h,cfg)
if a.mode=='freeway_only':physical_ramp_branches.configure_operating_bounds(local,cfg,reference)
plan={'controllers':{signal[2:]:node for signal,node in cfg.network.signal_actuation_contract['nodes'].items()}}
ownership=joint_owner_game.build_ownership(cfg,m,plan,segment_dsd_controls=adapter._segment_dsd_controls)
box=joint_owner_neighbors.build_fixed_move_box(ownership,h,cfg,joint.joint_decision_move_limits(c.nash_solver))
coord=sdmpc_sequence.SequenceCoordinates(cfg,reference,box,policy)
template=dict(owned=(SimpleNamespace(cfg=cfg),local,reference,f),runtime={'_PHASE_VECTOR_FOLLOWER':{}},
    action=reference,axes=coord.axes,green_vectors=coord.green_vectors,horizon=3,
    bootstrap=dict(x['kwargs']['worker_bootstrap'],runtime_sources={}),costs_order=(*coord.owners,'PASSIVE_OMEGA'))
query=Query(template,lambda *_:None,lambda stage,**kw:print(stage,kw,flush=True))
start=time.perf_counter()
try:
    item=query.evaluate([reference],derivatives=not a.scalar)[0]
    receipt=None if a.scalar else query.derivative(reference)
    coverage=item['model_constraint_coverage']
    assert coverage['schema']=='regional-model-constraint-coverage/v1' and coverage['complete']
    remote=cfg.network.signals if a.mode=='freeway_only' else cfg.network.freeway_links
    assert all(owner not in item['sdmpc_omega_partition']['costs'] for owner in remote)
    assert abs(item['sdmpc_omega_partition']['total_veh_h']-item['objective_veh_h'])<1e-7
    if receipt:
        assert len(receipt['cost_jacobian'])==len(template['costs_order'])
        assert len(receipt['resource_jacobian'])==2 and not receipt['fallback_reasons']
        for row in receipt['cost_jacobian']+receipt['resource_jacobian']:
            assert len(row)==len(coord.axes) and all(math.isfinite(v) for v in row)
        assert all(owner not in template['costs_order'] for owner in remote)
        inactive=0 if a.mode=='freeway_only' else 1
        assert receipt['resources'][inactive]==0 and all(v==0 for v in receipt['resource_jacobian'][inactive])
    record=dict(stage='regional_query_prototype',native_runs=0,production_dispatch=False,
        input_isolation_qualified=False,mode=a.mode,axes=len(coord.axes),elapsed_sec=time.perf_counter()-start,
        response=item,derivative=receipt)
    Path(a.output).write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps({k:record[k] for k in ('stage','mode','axes','elapsed_sec')}))
finally:query.close()
