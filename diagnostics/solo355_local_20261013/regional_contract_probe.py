"""Own-region registry and budget integration; not input-isolation qualification."""
import os
os.environ['RW_OFFSET_WRITER']='experiment'
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
p.add_argument('--output',required=True)
p.add_argument('--entry-only',action='store_true')
p.add_argument('--capture',default='D:/VISSIM_analysis/20261013_solo355_local/projected.pkl')
a=p.parse_args();x=pickle.loads(Path(a.capture).read_bytes())
c,s,f,h,m=x['args'];cfg=c.nash_solver.cfg;policy=cfg.network.sdmpc_options
config=json.loads(Path('diagnostics/solo355_20261012/'+a.mode+'_config.json').read_text(encoding='utf-8-sig'))
policy['actuator_scope']=sdmpc_actuator_scope.configure(config['adapter']['sdmpc_actuator_scope'],cfg)
# This bounded integration uses the regional registry and excludes unqualified
# global caches/hotpaths. It is not the production optimizer policy.
for key in ('central_multiplier','response_cap_cache','fast_primitives','prediction_hotpath',
            'stock_geometry_hotpath','receiving_geometry_cache','prediction_cache','compact_audit',
            'persistent_urban_fifo','array_urban_pipeline','array_transport','spatial_receiving'):
    policy[key]=False
policy.update(regional_prediction_prototype=a.mode,surrogate_reuse=True,tangent_backend='reverse-v1',derivative_workers=1,
    central_multiplier=True,budget_caps=True,pfo_each_interval=True)
boundary=regional.boundary_requests(x['obs']['merged']['obs150_derived'],a.mode,s.time_sec,cfg.network.ramps,s.lane_freeway_runtime.offramps)
local=regional.project_state(s,cfg,a.mode,boundary)
reference=meters.prepare_held_actual_reference(h,cfg)
if a.mode=='freeway_only':reference.N_P_star=0.
else:reference.N_UF_star=0.
if a.mode=='freeway_only':physical_ramp_branches.configure_operating_bounds(local,cfg,reference)
plan={'controllers':{signal[2:]:node for signal,node in cfg.network.signal_actuation_contract['nodes'].items()}}
ownership=joint_owner_game.build_ownership(cfg,m,plan,segment_dsd_controls=adapter._segment_dsd_controls)
box=joint_owner_neighbors.build_fixed_move_box(ownership,h,cfg,joint.joint_decision_move_limits(c.nash_solver))
coord=sdmpc_sequence.SequenceCoordinates(cfg,reference,box,policy)
from evaluation.controllers.urban_storage_guard import operating_seed
actual_reference=reference
reference=operating_seed(coord,actual_reference,policy)
from evaluation.controllers.sdmpc_tangent import prepare_request
template=prepare_request(c.nash_solver,local,f,actual_reference,reference,coord,
    dict(x['kwargs']['worker_bootstrap'],runtime_sources={}))
from unittest.mock import patch
with patch.object(type(c.nash_solver._wu),'_coupling',side_effect=AssertionError('global coupling forbidden')):
    callbacks,context,fingerprint=joint._joint_runtime_callbacks(c.nash_solver,local,f,h,reference,m,{},
        reference=actual_reference,total_budget=None,directional={},tolerance=1e-7,regional_mode=a.mode)
assert callbacks['move_box'].entries == box.entries
if a.entry_only:
    from evaluation.controllers import sdmpc,sdmpc_pfo
    class ReachedPFO(Exception):pass
    budget=joint.DecisionBudget(150.,unlimited_time=True)
    stopped=False
    with patch.object(sdmpc_pfo,'solve',side_effect=ReachedPFO), patch.object(
            type(c.nash_solver._wu),'_coupling',side_effect=AssertionError('global coupling forbidden')):
        try:
            sdmpc.solve(c,local,f,h,m,options=x['kwargs']['options'],runtime_sources={},
                worker_bootstrap=dict(x['kwargs']['worker_bootstrap'],runtime_sources={}),
                budget=budget,progress=None,previous_path=x['kwargs']['previous_path'])
        except ReachedPFO:stopped=True
    assert stopped
    record=dict(stage='regional_solver_entry_to_pfo',mode=a.mode,reached_pfo=True,
        optimizer_executed=False,traffic_rollouts=0,native_runs=0,input_isolation_qualified=False)
    Path(a.output).write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(record))
    raise SystemExit
query=Query(template,lambda *_:None,lambda stage,**kw:print(stage,kw,flush=True))
start=time.perf_counter()
try:
    item=query.evaluate([reference],derivatives=True)[0]
    receipt=query.derivative(reference)
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
    import copy
    from evaluation.controllers import sdmpc_budget
    from evaluation.controllers.sdmpc_regional_contracts import quantity_constraints
    options=x['kwargs']['options']
    seed,initialization=sdmpc_budget.initialize(template['owned'][0],local,reference,item,options)
    assert (seed.N_P_star if a.mode=='freeway_only' else seed.N_UF_star)==0.
    query.bind_warm_budget(reference,seed,options)
    bound=query.evaluate([seed],derivatives=True)[0]
    assert query.stats()['total_rollouts']==1
    assert len(bound['central_physical']['names'])>0
    names=bound['central_physical']['names']
    if a.mode=='freeway_only':
        assert not any('urban' in name or '/storage/' in name for name in names)
    else:
        assert not any('freeway' in name or '/lane_inventory/' in name or '/ramp_queue/' in name for name in names)
    for row in receipt['central_physical']['jacobian']:
        assert len(row)==len(coord.axes) and all(math.isfinite(v) for v in row)
    def validate(q):
        return quantity_constraints(template['owned'][0],seed,q,start_sec=local.time_sec,horizon_steps=3,
            np_mode='cap',target_np_veh=seed.N_P_star,np_tolerance_veh=0.,
            nuf_mode='cap',target_nuf_veh_h=seed.N_UF_star,nuf_tolerance_veh_h=0.)
    constraint=validate(bound['quantities'])
    assert constraint['feasible']
    corruptions=[]
    for label,edit in (
        ('clock',lambda q:q.update(end_sec=q['end_sec']+10)),
        ('missing_samples',lambda q:q['coverage'].update(samples=0)),
        ('opposite_region',lambda q:q.update(region='urban_only' if a.mode=='freeway_only' else 'freeway_only')),
        ('wrong_aggregate',lambda q:q.update(np_actual=q['np_actual']+10))):
        bad=copy.deepcopy(bound['quantities']);edit(bad)
        try:validate(bad)
        except ValueError:corruptions.append(label)
        else:raise AssertionError('Accepted corrupt quantity '+label)
    hold=joint.validate_actual_decision_hold(c.nash_solver,local,seed,bound,
        callbacks=callbacks,context=context,source_fingerprint='offline-regional-contract-probe',
        options=options)
    assert hold['feasible']
    assert len(hold['command_evidence']['owner_physical_sha256'])==19
    assert set(hold['final_score']['local_base_costs'])==set(coord.owners)
    writer_blocks=hold['command_evidence']['regional_prediction_blocks']
    assert len(writer_blocks)==3 and all(row['ordered_row_count']>0 for row in writer_blocks)
    sequence_proof=coord.validate(seed)
    record=dict(writer_blocks=writer_blocks,control_sequence=sequence_proof,
        final_command_feasible=hold['feasible'],stage='regional_registry_budget_contract',native_runs=0,production_dispatch=False,
        input_isolation_qualified=False,mode=a.mode,axes=len(coord.axes),elapsed_sec=time.perf_counter()-start,
        state_constraint_count=len(names), rejected_quantity_corruptions=corruptions,
        initialization=initialization,quantity_constraints=constraint,
        response=bound,derivative=receipt)
    Path(a.output).write_text(json.dumps(record,indent=2,default=lambda value: vars(value)),encoding='utf-8')
    print(json.dumps({k:record[k] for k in ('stage','mode','axes','elapsed_sec')}))
finally:query.close()
