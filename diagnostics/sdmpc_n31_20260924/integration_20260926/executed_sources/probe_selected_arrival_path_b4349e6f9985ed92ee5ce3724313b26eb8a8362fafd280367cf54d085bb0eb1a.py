"""Causal wiring probe using the canonical adapter and endpoint; no VISSIM/fitting.

Intercept after runtime/SDMPC configuration and forecast construction, before
optimization. Perturb only the redundant exogenous ramp-arrival field. This
does not perturb physical urban route arrivals or prove their accuracy.
"""
from __future__ import annotations

import copy
import csv
import gzip
import hashlib
import json
import os
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def probe_controller_derivatives(captured, reference, coord, evaluate, derivative, quantities,
                                 output, sources):
    """One actual-controller AD and nine independent continuous scalar checks.

    Infinitesimal FD commands bypass native quantization, exactly like the AD
    seeding. They diagnose two columns, not feasible commands or a new optimum.
    """
    import pickle
    import numpy as np
    from evaluation.controllers import sdmpc_sequence as sequence
    from evaluation.controllers.sdmpc_tangent import checked_matrices
    from evaluation.controllers.sdmpc_tangent_surrogate import Query

    protocol_path = HERE/'closedloop9000_d4e2_analysis/controller_derivative_check/protocol.json'
    protocol = json.loads(protocol_path.read_bytes())
    query = derivative.__self__
    assert isinstance(query, Query) and query.stats()['total_rollouts'] == 0
    cfg = captured['cfg']
    assert captured['state'].time_sec == 4500 and cfg.mpc.horizon_steps == 3
    z = coord.encode(reference)
    for j,axis in enumerate(coord.axes):
        if axis['kind']=='meter' and axis['key']=='RM_C10484':
            z[j] = ((8.,6.,4.)[axis['block']]-axis['reference_value'])/axis['scale']
    anchor = coord.decode(z, reference)
    coord.validate(anchor)
    for k,action in enumerate(sequence.actions(anchor,3)):
        assert action.green_times == reference.green_times and action.offsets == reference.offsets
        assert action.vsl == reference.vsl
        for ramp in cfg.network.ramps:
            key = 'rw_meter_green_'+ramp
            expected = (8.,6.,4.)[k] if ramp=='RM_C10484' else reference.diagnostics[key]
            assert action.diagnostics[key] == expected
    source_pins = {str(p):hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in (*sources,protocol_path,Path(__file__))}
    history_receipt = output/'vsl_history_replay.json'
    source_pins.update(json.loads(history_receipt.read_bytes())['original_files'])
    selected_axes = []
    trials = [anchor]
    trial_names = ['independent_anchor']
    # Physical units: seconds of meter GREEN and km/h of the VSL command.
    # Jacobians are w.r.t. normalized z, so h_z = h_physical / axis.scale.
    for spec in protocol['axes']:
        matches = [(j,a) for j,a in enumerate(coord.axes)
                   if all(a[key]==spec[key] for key in ('kind','key','block'))]
        assert len(matches)==1
        j,axis = matches[0]
        row = dict(axis, index=j, steps=spec['steps'],
                   step_unit='green_sec' if axis['kind']=='meter' else 'km_h', trials=[])
        for step in spec['steps']:
            indices=[]
            for sign in (-1,1):
                controls=sequence.actions(anchor,3)
                control=controls[axis['block']]
                if axis['kind']=='meter':
                    control.diagnostics['rw_meter_green_'+axis['key']] += sign*step
                else:
                    speed=control.vsl[axis['key']]+sign*step
                    for cell,head in enumerate(cfg.network.freeway_vsl_zone_head_of_cell[axis['owner']]):
                        if head==axis['head']:
                            control.vsl[f"{axis['owner']}__seg{cell}"]=speed
                    control.vsl[axis['owner']]=min(control.vsl[f"{axis['owner']}__seg{i}"]
                        for i in range(len(cfg.network.freeway_vsl_zone_head_of_cell[axis['owner']])))
                action=sequence.pack(controls)
                delta=coord.encode(action)-coord.encode(anchor)
                expected=np.zeros(len(coord.axes));expected[j]=sign*step/axis['scale']
                assert np.max(abs(delta-expected))<1e-12
                indices.append(len(trials));trials.append(action)
                trial_names.append(f"{axis['key']}_block{axis['block']}_{sign*step:+g}")
            row['trials'].append(dict(step_physical=step,step_z=step/axis['scale'],indices=indices))
        selected_axes.append(row)
    assert len(trials)==protocol['max_independent_scalar_rollouts']==9
    def write(name,value):
        (output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    write('protocol.json',dict(protocol,files=source_pins,axes=selected_axes,
        command_scope='Native-valid anchor only; FD points are continuous diagnostics, never applied',
        scalar_workers=3,optimizer_iterations=0,native_started=False))
    started=time.perf_counter()
    item=evaluate([anchor],derivatives=True)[0]
    receipt=derivative(anchor)
    owners=(*coord.owners,'PASSIVE_OMEGA')
    def costs(item):return np.array([item['sdmpc_omega_partition']['costs'][p] for p in owners])
    gradient,resource_gradient,fallback=checked_matrices(receipt,costs(item),quantities(anchor,item),
        coord.axes,protocol['primal_abs_tolerance'],allow_surrogate=True)
    assert not fallback and query.stats()['tangent_rollouts']==protocol['max_ad_rollouts']==1
    write('ad_columns.json',dict(owners=owners,resources=['NP_veh','NUF_veh_h'],
        columns=[dict(axis=a,costs=gradient[:,a['index']].tolist(),
                      resources=resource_gradient[:,a['index']].tolist()) for a in selected_axes],
        costs=costs(item).tolist(),resource_values=quantities(anchor,item).tolist(),
        trace=receipt['trace'],derivative_scope=receipt['derivative_scope'],
        transformed_source_sha256=receipt['transformed_source_sha256']))
    # A fresh query cannot reuse the AD primal as an alleged scalar witness.
    independent=Query(pickle.loads(query.template),query.check_budget,query.emit,runner=query.runner)
    assert independent.context_token==query.context_token
    scalar=[]
    try:
        for begin in range(0,len(trials),3):
            scalar.extend(independent.evaluate(trials[begin:begin+3],derivatives=False))
            write('scalar_responses.json',dict(names=trial_names[:len(scalar)],results=scalar))
    finally:
        independent.close()
    f0=costs(scalar[0]);q0=quantities(anchor,scalar[0])
    primal_cost_error=float(np.max(abs(costs(item)-f0)))
    primal_resource_error=float(np.max(abs(quantities(anchor,item)-q0)))
    rows=[]
    for axis in selected_axes:
        j=axis['index']
        comparisons=[]
        for trial in axis['trials']:
            minus,plus=trial['indices'];h=trial['step_z']
            fm,fp=costs(scalar[minus]),costs(scalar[plus])
            qm,qp=(quantities(trials[idx],scalar[idx]) for idx in (minus,plus))
            dc,dq=(fp-fm)/(2*h),(qp-qm)/(2*h)
            close_c=np.isclose(dc,gradient[:,j],atol=protocol['cost_gradient_atol'],rtol=protocol['gradient_rtol'])
            close_q=np.isclose(dq,resource_gradient[:,j],atol=protocol['resource_gradient_atol'],rtol=protocol['gradient_rtol'])
            comparisons.append(dict(step_physical=trial['step_physical'],step_z=h,
                central_costs=dc.tolist(),left_costs=((f0-fm)/h).tolist(),right_costs=((fp-f0)/h).tolist(),
                central_resources=dq.tolist(),left_resources=((q0-qm)/h).tolist(),right_resources=((qp-q0)/h).tolist(),
                omega_ad_per_z=float(sum(gradient[:,j])),omega_fd_per_z=float(sum(dc)),
                max_cost_error=float(np.max(abs(dc-gradient[:,j]))),
                max_resource_error=float(np.max(abs(dq-resource_gradient[:,j]))),
                cost_matches=close_c.tolist(),resource_matches=close_q.tolist(),
                all_match=bool(np.all(close_c) and np.all(close_q))))
        rows.append(dict(axis=axis,comparisons=comparisons))
    pins_unchanged=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==sha for p,sha in source_pins.items())
    assert pins_unchanged
    stats=independent.stats()
    assert stats['scalar_rollouts']==9 and stats['tangent_rollouts']==0
    report=dict(status='complete',start_sec=4500,horizon_sec=450,files=source_pins,
        primal_cost_max_error=primal_cost_error,primal_resource_max_error=primal_resource_error,
        primal_outputs_match=max(primal_cost_error,primal_resource_error)<=protocol['primal_abs_tolerance'],
        full_primal_trajectory_audited=False,rows=rows,
        all_checked_gradients_match=all(c['all_match'] for row in rows for c in row['comparisons']),
        ad_query=query.stats(),independent_scalar_query=stats,wall_sec=time.perf_counter()-started,
        optimizer_iterations=0,native_started=False,calibration_changed=False,files_unchanged=pins_unchanged,
        scope='Two continuous columns at one anchor; not all-axis AD certification, an optimizer result, or native gain validation')
    write('summary.json',report)
    print(json.dumps({k:report[k] for k in ('status','primal_outputs_match','all_checked_gradients_match','wall_sec')}),flush=True)


def probe_levers(captured, reference, output, *, only_reference=False, selected_path=None,
                 meter_only=False, signal_exchange=False, meter_ramp=None, vsl_zone=None,
                 trace_response=False):
    """Small legal one-lever sequences, using the installed SDMPC decoder.

    This is sensitivity diagnosis, not selection, calibration, or a native
    counterfactual: all candidates hold the last actually applied city action.
    """
    from evaluation.controllers import joint_owner_game as owners
    from evaluation.controllers import joint_owner_neighbors as neighbors
    from evaluation.controllers import sdmpc_sequence as sequence
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from src.controllers import rollout_endpoint as endpoint
    cfg, state = captured['cfg'], captured['state']
    # Previous prediction blocks were never applied. Match SDMPC.solve's
    # first_action handling before constructing this decision's reference.
    reference = sequence.first_action(reference)
    plan = {'controllers': {s[2:]: n for s,n in cfg.network.signal_actuation_contract['nodes'].items()}}
    ownership = owners.build_ownership(cfg,captured['mapping'],plan,
                                      segment_dsd_controls=adapter._segment_dsd_controls)
    # City coordinates are fixed only for this isolated response probe.
    limits = dict(green_sec=0.,offset_sec=0.,vsl_kmh=cfg.freeway_follower.max_vsl_step,
                  meter_green_sec=cfg.network.physical_ramp_branches['max_green_change_sec'])
    if signal_exchange:
        from types import SimpleNamespace
        from evaluation.controllers.area_follower_objective import joint_decision_move_limits
        assert selected_path is None
        # Reuse the controller's actual move bound; keep offsets fixed here.
        limits=joint_decision_move_limits(SimpleNamespace(cfg=cfg,offset_marginal_price_trust_sec=0.))
    box = neighbors.build_fixed_move_box(ownership,reference,cfg,limits)
    coord = sequence.SequenceCoordinates(cfg,reference,box,cfg.network.sdmpc_options)
    anchor = coord.encode(reference)
    candidates = {'held_actual': coord.decode(anchor,reference)}
    if signal_exchange and not only_reference:
        for name,changes in (
                ('SC1001_p1_from_p4', {'p1':1.,'p4':-1.}),
                ('SC1001_p2_from_p4', {'p2':1.,'p4':-1.}),
                ('SC1001_p2_from_p3', {'p2':1.,'p3':-1.}),
                ('SC1001_p1p2_from_p4', {'p1':.5,'p2':.5,'p4':-1.})):
            action=reference.copy()
            for phase,fraction in changes.items():
                key='SC1001_'+phase
                action.green_times[key]+=fraction*limits['green_sec']
            candidates[name]=sequence.pack([action.copy() for _ in range(3)])
            coord.validate(candidates[name])
    east_axes = [(j,a) for j,a in enumerate(coord.axes) if a['owner']=='FW_E']
    for kind in (() if only_reference or selected_path is not None or signal_exchange else
                 ('vsl',) if vsl_zone is not None else ('meter',) if meter_only else ('meter','vsl')):
        keys = list(dict.fromkeys(a['key'] for j,a in east_axes if a['kind']==kind))
        if meter_ramp is not None:
            assert meter_only and kind=='meter' and meter_ramp in keys
            keys=[meter_ramp]
        if vsl_zone is not None:
            assert not meter_only and meter_ramp is None and kind=='vsl' and vsl_zone in keys
            keys=[vsl_zone]
        for key in keys:
            for profile in (('restrict', 'release') if vsl_zone is not None else
                            ('flat8', 'progressive') if meter_only else ('progressive',)):
                z = anchor.copy()
                for j,a in east_axes:
                    if a['kind']!=kind or a['key']!=key:
                        continue
                    if kind=='meter':
                        initial=reference.diagnostics['rw_meter_green_'+key]
                        blocks = 1 if profile == 'flat8' else a['block']+1
                        value=max(cfg.network.physical_ramp_branches['minimum_green_sec'],
                                  initial-blocks*limits['meter_green_sec'])
                    else:
                        initial=reference.vsl[key]
                        value=(min(max(cfg.freeway_follower.vsl_set),initial+20.)
                               if profile=='release' else
                               max(min(cfg.freeway_follower.vsl_set),initial-20.))
                    assert value in a['allowed'], (key,value,a['allowed'])
                    z[j]=(value-initial)/a['scale']
                suffix = '_'+profile if meter_only or vsl_zone is not None else ''
                candidates[kind+'_'+key+suffix]=coord.decode(z,reference)
    selected_proof=None
    if selected_path is not None:
        from src.models.state import ControlAction
        receipt_path=selected_path.with_suffix('.joint_written.json')
        selected_proof=json.loads(receipt_path.read_bytes())
        assert selected_proof['written_command_binding_passed']
        assert selected_proof['action_json']['sha256']==hashlib.sha256(selected_path.read_bytes()).hexdigest()
        candidates['selected']=adapter.control_from_json(selected_path,cfg,ControlAction)
    results={}
    initial_gate_stats=copy.deepcopy(getattr(state,'gate_future_accounting',None))
    for name,action in candidates.items():
        # Selected urban commands were checked by the actual SDMPC writer;
        # this isolated-lever coordinate box intentionally freezes the city.
        receipt=selected_proof if name=='selected' else coord.validate(action)
        started=time.perf_counter()
        with sequence.prediction_scope(action,cfg,state.time_sec,3) as visits:
            point=endpoint.evaluate_price_point(state,action,copy.deepcopy(captured['forecast'][:3]),(),
                endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
        assert visits == [0,1,2], 'Each explicit control block must actually be evaluated'
        assert not point.aborted and len(point.states)==3
        assert getattr(state,'gate_future_accounting',None)==initial_gate_stats
        response=point.control_area_response
        costs={};outside={}
        for row in response['residence']:
            for key,n in row['inside_veh'].items():
                costs[key]=costs.get(key,0.)+row['dt_h']*n
                out=row['model_stock_veh'][key]-n
                assert out>=-1e-7
                outside[key]=outside.get(key,0.)+row['dt_h']*max(0.,out)
        assert abs(sum(costs.values())-point.ttt)<1e-7
        ramp_rows={}
        for ramp in cfg.network.ramps:
            arrivals=sum(t['vehicles'] for t in response['transfers'] if t['target']=='ramp:'+ramp)
            merges=sum(t['vehicles'] for t in response['transfers']
                       if t['source']=='ramp:'+ramp and t['target']=='merge_pending:'+ramp)
            ending=point.states[-1].ramp_queue[ramp]
            residual=state.ramp_queue[ramp]+arrivals-merges-ending
            assert abs(residual)<1e-7
            ramp_rows[ramp]=dict(arrival=arrivals,merge=merges,final_stock=ending,residual=residual)
        item=dict(wall_sec=time.perf_counter()-started,executed_control_blocks=visits,ttt_omega_veh_h=point.ttt,
                  tracked_outside_residence_veh_h=sum(outside.values()),
                  ttt_with_tracked_outside_veh_h=point.ttt+sum(outside.values()),
                  control_area=point.control_area,cost_by_stock=costs,
                  outside_cost_by_stock={k:v for k,v in outside.items() if v},ramps=ramp_rows,
                  validation=receipt,commands=[dict(vsl=c.vsl,green_times=c.green_times,offsets=c.offsets,
                      meters={r:c.diagnostics['rw_meter_green_'+r] for r in cfg.network.ramps})
                      for c in sequence.actions(action,3)])
        if initial_gate_stats is not None:
            item['gate_future_final_accounting']=point.states[-1].gate_future_accounting
        if trace_response:
            movements={k:v for k,v in cfg.network.urban_movements.items() if k.startswith('SC1004_')}
            origins=set(['SC1004_W_out']) | {v['origin'] for v in movements.values()}
            storage=origins & cfg.network.urban_link_storage_veh.keys()
            trace=dict(start_sec=state.time_sec,forecast_boundary=[d.urban_boundary for d in captured['forecast'][:3]],
                origins_without_urban_storage=sorted(origins-storage),
                movements=movements,capacities_veh_h={k:cfg.network.movement_capacity_by_movement_veh_h[k] for k in movements},
                green={k:v for k,v in reference.green_times.items() if k.startswith('SC1004_')},
                offsets={k:v for k,v in reference.offsets.items() if '1004' in k},
                states=[dict(time_sec=s.time_sec,queue={k:s.urban_movement_queue.get(k,0.) for k in movements},
                    storage={k:cfg.network.urban_link_storage_veh[k]-s.urban_link_storage[k] for k in storage})
                    for s in (state,*point.states)],
                transfers=[r for r in response['transfers']
                    if any('SC1004' in (r.get(k) or '') or 'RM_C10681' in (r.get(k) or '') for k in ('source','target'))],
                resources=[r for r in response['resource_allocations'] if 'SC1004' in r['resource']])
            with gzip.open(output/(name+'_arrival_trace.json.gz'),'wt',encoding='utf-8') as stream:
                json.dump(trace,stream,ensure_ascii=False,allow_nan=False)
        if signal_exchange:
            movements={k:v for k,v in cfg.network.urban_movements.items() if k.startswith('SC1001_')}
            transfers={}
            for row in response['transfers']:
                if not any('SC1001' in (row[key] or '') for key in ('source','target')):
                    continue
                key=(row['source'],row['target'],row['route_key'])
                transfers[key]=transfers.get(key,0.)+row['vehicles']
            item['signal_audit']=dict(movement_specs=movements,
                movement_capacity_veh_h={m:cfg.network.movement_capacity_by_movement_veh_h[m] for m in movements},
                movement_queues_by_time={str(s.time_sec):{k:v for k,v in s.urban_movement_queue.items()
                    if k.startswith('SC1001_')} for s in (state,*point.states)},
                transfers=[dict(source=k[0],target=k[1],route_key=k[2],vehicles=v)
                           for k,v in sorted(transfers.items(),key=lambda pair:tuple(x or '' for x in pair[0]))])
        if results:
            baseline=results['held_actual']
            item['delta_ttt_omega_veh_h']=item['ttt_omega_veh_h']-baseline['ttt_omega_veh_h']
            item['delta_with_tracked_outside_veh_h']=item['ttt_with_tracked_outside_veh_h']-baseline['ttt_with_tracked_outside_veh_h']
            item['delta_merge_by_ramp']={r:v['merge']-baseline['ramps'][r]['merge'] for r,v in ramp_rows.items()}
        results[name]=item
        (output/(name+'.json')).write_text(json.dumps(item,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
        print(json.dumps(dict(case=name,wall_sec=item['wall_sec'],ttt=point.ttt,
                              delta=item.get('delta_ttt_omega_veh_h'))),flush=True)
        del point,response
    report=dict(purpose='Legal one-lever 450s predicted response; native gain NOT validated',
                only_held_reference=only_reference,
                start_sec=state.time_sec,duration_sec=450,actual_reference_only=True,
                city_signals_held=not signal_exchange,limits=limits,results=results,optimizer_iterations=0,
                native_started=False,future_observation_inputs=False,
                outside_cost_scope='Only outside cohorts in sampled model stocks; not a native uninserted-vehicle audit',
                quantity_constraints='Physical/writer/inter-block checks only; NP/NUF budget selection not evaluated')
    if signal_exchange:
        report.update(purpose='SC1001 finite green exchanges, other signals/offsets/RM/VSL held; model response only',
                      isolated_signal='SC1001')
    if selected_path is not None:
        source=json.loads(selected_path.with_suffix('.joint.json').read_bytes())['selection']
        report.update(purpose='Two fixed sequences in the canonical execution model; compare selected surrogate gain, no refit or VISSIM',
            city_signals_held=False,selected_path=str(selected_path),selection_completed_before_validation=True,
            surrogate=dict(held_ttt=source['held_objective'],selected_ttt=source['selected_objective'],
                           delta_ttt=source['selected_objective']-source['held_objective']))
    (output/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')


def probe_selected_meter(captured, reference, coord, options, evaluate, selected_path, output):
    """Three fixed candidates around a completed selection; never optimize or apply."""
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers import sdmpc_sequence as sequence, sdmpc_pfo
    from evaluation.controllers import area_leader_objective as constraints
    from src.models.state import ControlAction
    from src.controllers import rollout_endpoint as endpoint
    cfg, state = captured['cfg'], captured['state']
    saved = json.loads(selected_path.with_suffix('.joint.json').read_bytes())['selection']
    binding = json.loads(selected_path.with_suffix('.joint_written.json').read_bytes())
    assert binding['written_command_binding_passed']
    assert binding['action_json']['sha256'] == hashlib.sha256(selected_path.read_bytes()).hexdigest()
    selected = adapter.control_from_json(selected_path, cfg, ControlAction)
    coord.validate(selected)
    ramp = 'RM_C10484'
    assert reference.diagnostics['rw_meter_green_'+ramp] == 10
    original = sequence.actions(selected, 3)
    assert all(c.diagnostics['rw_meter_green_'+ramp] == 10 for c in original)
    candidates = {'selected': selected}
    for profile in ('flat8', 'progressive'):
        z = coord.encode(selected)
        for j, axis in enumerate(coord.axes):
            if axis['kind'] != 'meter' or axis['key'] != ramp:
                continue
            value = 8 if profile == 'flat8' else 8-2*axis['block']
            assert value in axis['allowed']
            z[j] = (value-reference.diagnostics['rw_meter_green_'+ramp])/axis['scale']
        trial = coord.decode(z, selected)
        coord.validate(trial)
        for before, after in zip(original, sequence.actions(trial, 3)):
            assert before.green_times == after.green_times and before.offsets == after.offsets
            assert before.vsl == after.vsl
            assert all(before.ramp_metering[r] == after.ramp_metering[r] for r in cfg.network.ramps if r != ramp)
        candidates[profile] = trial
    items = evaluate(list(candidates.values()), derivatives=False)
    follower = adapter._PHASE_VECTOR_FOLLOWER['ref']
    def budget(action, quantities):
        return constraints.shared_quantity_constraints(follower, action, quantities,
            start_sec=state.time_sec, horizon_steps=3,
            np_mode='cap', target_np_veh=saved['final_constraints']['np']['target'],
            np_tolerance_veh=saved['final_constraints']['np']['tolerance'],
            nuf_mode='cap', target_nuf_veh_h=saved['final_constraints']['nuf']['target'],
            nuf_tolerance_veh_h=saved['final_constraints']['nuf']['tolerance'])
    results = {}
    for (name, action), item in zip(candidates.items(), items):
        model = dict(ttt_omega_veh_h=item['objective_veh_h'],
            quantities=budget(action, item['quantities']),
            physical_model_feasible=sdmpc_pfo.model_feasible(item, options['shared_tolerance']))
        started = time.perf_counter()
        with sequence.prediction_scope(action, cfg, state.time_sec, 3) as visits:
            point = endpoint.evaluate_price_point(state, action, copy.deepcopy(captured['forecast'][:3]), (),
                endpoint.ObjectiveSpec(cfg, depth_override=3, box_walk=False, score_mode='raw'), capture_response=True)
        assert visits == [0,1,2] and not point.aborted and len(point.states) == 3
        response = point.control_area_response
        physical_quantities = constraints.shared_urban_quantities(follower, response, start_sec=state.time_sec, horizon_steps=3)
        outside = sum(row['dt_h']*sum(max(0.,row['model_stock_veh'][key]-n) for key,n in row['inside_veh'].items()) for row in response['residence'])
        ramps = {}
        for r in cfg.network.ramps:
            arrivals = sum(x['vehicles'] for x in response['transfers'] if x['target']=='ramp:'+r)
            merges = sum(x['vehicles'] for x in response['transfers'] if x['source']=='ramp:'+r and x['target']=='merge_pending:'+r)
            final = point.states[-1].ramp_queue[r]
            residual = state.ramp_queue[r]+arrivals-merges-final
            assert abs(residual)<1e-7
            ramps[r] = dict(arrivals=arrivals,merges=merges,final_stock=final,residual=residual)
        execution = dict(ttt_omega_veh_h=point.ttt, tracked_outside_veh_h=outside,
            quantities=budget(action,physical_quantities), ramps=ramps,
            conditional_model_feasibility_witness=response.get('conditional_model_feasibility_witness'),
            model_constraint_coverage=response.get('model_constraint_coverage'),
            resource_max_exceedance=max((x['exceedance_veh'] for x in response['resource_allocations']),default=0.),
            wall_sec=time.perf_counter()-started)
        results[name] = dict(surrogate=model,execution=execution,commands=[
            dict(vsl=c.vsl,green_times=c.green_times,offsets=c.offsets,
                meters={r:c.diagnostics['rw_meter_green_'+r] for r in cfg.network.ramps}) for c in sequence.actions(action,3)])
        (output/(name+'.json')).write_text(json.dumps(results[name],ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
        print(json.dumps(dict(case=name,surrogate=model['ttt_omega_veh_h'],execution=point.ttt,
                             quantity_feasible=execution['quantities']['feasible'])),flush=True)
    assert abs(results['selected']['surrogate']['ttt_omega_veh_h']-saved['selected_objective'])<1e-7
    old = json.loads((selected_path.parent.with_name(selected_path.parent.name.replace('_select_','_select_check_'))/'summary.json').read_bytes())
    assert abs(results['selected']['execution']['ttt_omega_veh_h']-old['results']['selected']['ttt_omega_veh_h'])<1e-7
    for name, result in results.items():
        for kind in ('surrogate','execution'):
            result[kind]['delta_ttt_omega_veh_h']=result[kind]['ttt_omega_veh_h']-results['selected'][kind]['ttt_omega_veh_h']
    report=dict(start_sec=state.time_sec,horizon_sec=450,results=results,
        selected_surrogate_and_execution_reproduced=True,selected_city_vsl_unchanged=True,
        selected_budget_caps_frozen=True,surrogate_rollouts=3,execution_rollouts=3,
        optimizer_iterations=0,native_started=False,gain_qualified=False,
        scope='10484 only at the already selected city/VSL sequence; compare real actuator sequence and fixed current PFO caps, no calibration/native')
    (output/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')


def probe_meter_tail(captured, reference, output, *, ramp='RM_C10484', reference_dir=None):
    """Two fixed legal paths past450s; diagnostic only, no MPC horizon change."""
    from src.controllers import rollout_endpoint as endpoint
    from evaluation.controllers import physical_ramp_branches as branches
    from evaluation.controllers import sdmpc_sequence as sequence
    original_cfg,initial=captured['cfg'],captured['state'];reference=sequence.first_action(reference)
    assert original_cfg.mpc.horizon_steps==3 and original_cfg.simulation.T_c_sec==150
    # TimeBins collapse all arrivals beyond their declared end into one final
    # slot. Allocate the diagnostic horizon BEFORE the first rollout; never
    # extend or reuse a state whose future due times were already collapsed.
    for name in ('native_input_route_state','native_input_prehead_state'):
        assert 'aggregate' not in getattr(initial,name,{}), 'Need the original uncollapsed observation state'
    cfg=copy.deepcopy(original_cfg)
    cfg.mpc.horizon_steps=6
    spec=cfg.network.physical_ramp_branches['ramps'][ramp]
    reference_dir=reference_dir or HERE/'closedloop3000_meter2700_sequence_v1'
    paths={'held':[10]*6,'progressive':[8,6,4,2,2,2]}
    protocol=dict(ramp=ramp,paths=paths,initial_time=initial.time_sec,
        existing_mpc_horizon_sec=450,diagnostic_duration_sec=900,
        demand='Original three causal forecast intervals; repeat interval3 thereafter, no future observed inputs.',
        purpose='Does the legal green change sequence enter an effective metering range only after the current horizon?',
        caveat='Fixed-command sensitivity only; later demand is uncertain. No optimizer, NP/NUF candidate-feasibility or native-gain qualification.',
        service_by_green_vph=spec['service_by_green_veh_h'],new_native_runs=0,production_changed=False,
        diagnostic_route_bin_horizon_sec=900,source_files={str(p):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (Path(__file__),reference_dir/'held_actual.json',reference_dir/('meter_'+ramp+'_progressive.json'))})
    (output/'tail_protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    results={}
    for name,greens in paths.items():
        state=initial;previous=reference;rows=[]
        for block,green in enumerate(greens):
            wanted={r:previous.diagnostics['rw_meter_green_'+r] for r in cfg.network.ramps}
            wanted[ramp]=green
            action=branches.candidate_from_greens(previous,previous,cfg,wanted)
            assert action.vsl==reference.vsl and action.green_times==reference.green_times and action.offsets==reference.offsets
            before=state.time_sec;started=time.perf_counter()
            demand=copy.deepcopy(captured['forecast'][min(block,2)])
            point=endpoint.evaluate_price_point(state,action,[demand],(),
                endpoint.ObjectiveSpec(cfg,depth_override=1,box_walk=False,score_mode='raw'),capture_response=True)
            assert not point.aborted and len(point.states)==1 and abs(point.states[0].time_sec-before-150)<1e-8
            response=point.control_area_response;outside=0.;inside=0.
            for residence in response['residence']:
                inside+=sum(residence['inside_veh'].values())*residence['dt_h']
                for key,n in residence['inside_veh'].items():
                    extra=residence['model_stock_veh'][key]-n
                    assert extra>=-1e-7
                    outside+=max(0.,extra)*residence['dt_h']
            assert abs(inside-point.ttt)<1e-7
            arrivals=sum(t['vehicles'] for t in response['transfers'] if t['target']=='ramp:'+ramp)
            merges=sum(t['vehicles'] for t in response['transfers']
                       if t['source']=='ramp:'+ramp and t['target']=='merge_pending:'+ramp)
            ending=point.states[0].ramp_queue[ramp]
            residual=state.ramp_queue[ramp]+arrivals-merges-ending
            assert abs(residual)<1e-7
            row=dict(block=block,start_sec=before,end_sec=before+150,green_sec=green,
                ttt_omega_veh_h=point.ttt,tracked_outside_veh_h=outside,
                target_arrivals_veh=arrivals,target_merges_veh=merges,target_end_stock=ending,
                conservation_residual=residual,wall_sec=time.perf_counter()-started)
            rows.append(row);state=point.states[0];previous=action
            (output/(name+'_progress.json')).write_text(json.dumps(rows,indent=2),encoding='utf-8')
            print(json.dumps(dict(arm=name,block=block,green=green,ttt=point.ttt,merge=merges)),flush=True)
            del point,response
        old_name='held_actual' if name=='held' else 'meter_'+ramp+'_progressive'
        old=json.loads((reference_dir/(old_name+'.json')).read_text())
        assert abs(sum(r['ttt_omega_veh_h'] for r in rows[:3])-old['ttt_omega_veh_h'])<1e-7,'First450s must match the prior three-block evaluation'
        assert abs(sum(r['target_merges_veh'] for r in rows[:3])-old['ramps'][ramp]['merge'])<1e-7
        results[name]=rows
    comparisons=[]
    for count in (3,4,5,6):
        delta=lambda key:sum(r[key] for r in results['progressive'][:count])-sum(r[key] for r in results['held'][:count])
        comparisons.append(dict(duration_sec=count*150,delta_omega_ttt_veh_h=delta('ttt_omega_veh_h'),
            delta_tracked_outside_veh_h=delta('tracked_outside_veh_h'),delta_target_merges_veh=delta('target_merges_veh')))
    assert original_cfg.mpc.horizon_steps==3
    (output/'summary.json').write_text(json.dumps(dict(protocol=protocol,results=results,comparisons=comparisons,
        first450_parity_passed=True,new_native_runs=0,production_changed=False),indent=2),encoding='utf-8')


def replay_head_history(observe_heads, original, cfg, raw, caps, plan, distribute, options,
                        *, folder, sim_sec, output, history_inputs):
    """Rebuild only causal observation metadata; never rewrite native actions."""
    from evaluation.controllers.obs150_observation import merge_into_state
    from evaluation.controllers import obs150_contract as oc
    prior=None; prototype=copy.deepcopy(cfg)
    history_dir=output/'head_history';history_dir.mkdir(exist_ok=True)
    for end in range(150,sim_sec,150):
        state_file=folder/f'state_{end:06d}.json'
        derived_file=folder/'obs150'/f'derived_{end:06d}.json'
        source=json.loads(state_file.read_bytes());derived=json.loads(derived_file.read_bytes())
        assert derived['window']==dict(start_s=end-150,end_s=end)
        assert end<=sim_sec-150
        historical=merge_into_state(source,derived)
        assert derived['inputs']['raw_sha256']==oc.canonical_sha256(source['obs150'])
        meta=observe_heads(original,copy.deepcopy(prototype),historical,prior,caps,plan,distribute,options)
        meta['sim_sec']=end
        prior=history_dir/f'head_prior_{end:06d}.json'
        prior.write_text(json.dumps(dict(run_provenance=historical['run_provenance'],metadata=meta,
            diagnostic_observation_only=True,actual_commands_rewritten=False),
            ensure_ascii=False,allow_nan=False),encoding='utf-8')
        history_inputs.append({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (state_file,derived_file)})
    return observe_heads(original,cfg,raw,prior,caps,plan,distribute,options)


def probe_closedloop_meters(*, tail=False, selected_sec=None, signal_probe=False, head_phase=False,
                           head_service=False, service_reference=False):
    """Bounded response audit on a completed native state; no optimizer."""
    from evaluation.controllers import runtime_setup
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    if selected_sec is not None:
        assert not tail and selected_sec in (4500,6000)
    assert not signal_probe or selected_sec is not None
    assert not head_phase or signal_probe
    assert not head_service or signal_probe and not head_phase
    assert not service_reference or signal_probe and not (head_service or head_phase)
    period,sim_sec=(9000,selected_sec) if selected_sec is not None else (3000,2700)
    runs=Path('D:/VISSIM_runs/20260927_sd31_closedloop9000' if period==9000 else
              'D:/VISSIM_runs/20260926_sd31_closedloop3000_v2')
    status=json.loads((HERE/f'closedloop{period}_status.json').read_text(encoding='utf-8-sig'))
    assert status['stage'] in ('both_native_complete_unanalyzed', 'complete_analyzed_gain_not_qualified',
                               'requested_native_arms_complete_unanalyzed')
    assert not (runs/'STOP').exists()
    folder=runs/f'sdmpc/decisions_sdmpc31_sdmpc{period}_s29'
    state_path,previous=folder/f'state_{sim_sec:06d}.json',folder/f'action_{sim_sec-150:06d}.json'
    selected_path=folder/f'action_{sim_sec:06d}.json' if selected_sec is not None and not signal_probe else None
    output=HERE/(f'closedloop9000_SC1001_{sim_sec}_response' if signal_probe else
                 f'closedloop9000_selected{sim_sec}_response' if selected_sec is not None else
                 'closedloop3000_meter2700_tail_diagnostic_v2' if tail else 'closedloop3000_meter2700_sequence_v1')
    if head_phase:
        output=output.with_name(output.name+'_head_phase')
    if head_service:
        output=output.with_name(output.name+'_service10698')
    if service_reference:
        output=output.with_name(output.name+'_service_reference')
    assert not output.exists(), 'Preserve completed or failed probe; inspect before rerunning'
    output.mkdir()
    tuning_path=HERE/'selected/config_n31_v2.json'
    if head_phase or head_service:
        tuning=json.loads(tuning_path.read_bytes())
        if head_phase:tuning['urban']['queue']['attribution']='head_phase'
        if head_service:
            tuning['urban']['capacity']['head_resource_contract']=str((HERE/'head_service_resource_10698.json').relative_to(ROOT))
        tuning_path=output/'tuning_candidate.json'
        tuning_path.write_text(json.dumps(tuning,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    paths=(state_path,previous,tuning_path)+((selected_path,selected_path.with_suffix('.joint.json'),
                                           selected_path.with_suffix('.joint_written.json'))
                                          if selected_path is not None else ())
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    captured={}
    configure,forecast_fn=runtime_setup.configure_runtime,adapter.demand_from_state
    class Ready(BaseException):
        pass
    def capture_runtime(*args,**kwargs):
        result=configure(*args,**kwargs)
        captured.update(state=result[0],cfg=args[1],mapping=args[3],metadata=result[2])
        return result
    def capture_forecast(*args,**kwargs):
        captured['forecast']=forecast_fn(*args,**kwargs)
        raise Ready()
    sys.argv=[str(Path(adapter.__file__)), '--state-json',str(state_path),
        '--previous-action-json',str(previous),'--out-action-json',str(output/'unused.json'),
        '--out-action-csv',str(output/'unused.csv'),
        '--mapping-json',str(ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'),
        '--detector-mapping-json',str(ROOT/'evaluation/real_world_modi_control_ver2_20260907/detector_local_mapping_ver2_20260907.json'),
        '--calibration-json',str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'),
        '--tuning-json',str(tuning_path),'--controller','wu-link']
    for key,value in dict(RW_DECISION_FAIL_FAST='1',RW_MAINLINE_SG_ONLY='1',
                         RW_OFFSET_WRITER='experiment',RW_RAMP_AMBER_SEC='0').items():
        os.environ[key]=value
    runtime_setup.configure_runtime,adapter.demand_from_state=capture_runtime,capture_forecast
    from evaluation.controllers import head_service_resources
    observe_heads=head_service_resources.observe
    history_inputs=[]
    def warm_observer(original,cfg,raw,previous_path,caps,plan,distribute,options):
        return replay_head_history(observe_heads,original,cfg,raw,caps,plan,distribute,options,
            folder=folder,sim_sec=sim_sec,output=output,history_inputs=history_inputs)
    if head_service:head_service_resources.observe=warm_observer
    try:
        adapter.main()
        raise AssertionError('Adapter did not reach forecast capture')
    except Ready:
        pass
    finally:
        runtime_setup.configure_runtime,adapter.demand_from_state=configure,forecast_fn
        head_service_resources.observe=observe_heads
    assert captured['state'].time_sec==sim_sec
    assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    if head_service or service_reference:
        (output/'head_service_receipt.json').write_text(json.dumps(dict(history_inputs=history_inputs,
            current_sec=sim_sec,metadata=captured['metadata'],
            movement_capacity_veh_h=captured['cfg'].network.movement_capacity_by_movement_veh_h,
            resources=captured['cfg'].network.head_service_resources,
            files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [
                HERE/'head_service_resource_10698.json',Path(__file__),
                ROOT/'evaluation/controllers/head_service_resources.py',
                ROOT/'evaluation/controllers/signal_head_observation.py']}),ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'source_receipt.json').write_text(json.dumps(dict(files=hashes,
        actual_previous_command=str(previous),native_started=False,optimizer_iterations=0,
        purpose=('SC1001 four finite green exchanges versus held; no new optimization.' if signal_probe else
                 'Held versus previously selected450s sequence; no new optimization.' if selected_path else
                 'Two fixed900s paths for10484 only; original450s MPC unchanged.' if tail else
                 'Held versus each east meter8/8/8 and8/6/4. All other commands held; no coefficient fit.')),indent=2),encoding='utf-8')
    from src.models.state import ControlAction
    action=adapter.control_from_json(previous,captured['cfg'],ControlAction)
    if tail:probe_meter_tail(captured,action,output)
    else:probe_levers(captured,action,output,meter_only=True,selected_path=selected_path,
                     signal_exchange=signal_probe,only_reference=service_reference)


def replay_vsl_history(initialize, context, raw, state, cfg, output):
    """Rebuild a trial model's past cohorts without changing native evidence."""
    from types import SimpleNamespace as NS
    from evaluation.controllers import obs150_contract as oc
    from evaluation.controllers.lane_plant_runtime import bin_frame
    obs=raw[oc.RAW_STATE_KEY];cutoff=int(obs['sim_sec']);directory=Path(obs['directory'])
    history=output/'vsl_history';history.mkdir(exist_ok=False)
    pins={};checks=[]
    def read(path):
        data=path.read_bytes();pins[str(path)]=hashlib.sha256(data).hexdigest()
        return json.loads(data)
    readback=directory/'vsl_readback.csv';pins[str(readback)]=hashlib.sha256(readback.read_bytes()).hexdigest()
    for end in range(150,cutoff+1,150):
        source=read(directory/f'state_{end:06d}.json')
        observed=source[oc.RAW_STATE_KEY]
        assert observed['run_id']==obs['run_id'] and Path(observed['directory']).resolve()==directory.resolve()
        derived=read(directory/'obs150'/f'derived_{end:06d}.json')
        assert derived['window']==dict(start_s=end-150,end_s=end)
        assert derived['inputs']['raw_sha256']==oc.canonical_sha256(observed)
        if end==cutoff:
            target_state=state;inputs=raw
        else:
            frame=oc.load_frame(oc.resolve(observed,observed['frames']['current']['path']),
                                observed['frames']['current']['sha256'],end)
            target_state=NS(lane_freeway_runtime=state.lane_freeway_runtime,
                            freeway_density={},freeway_effective_lanes={})
            for road in state.lane_freeway_runtime.configs:
                cells,rows,dropped=bin_frame(context['geometry'],frame['vehicles'],road,drop_before_start=True)
                assert not dropped
                lanes=[cell['lane_km']/cell['length_km'] for cell in cells]
                target_state.freeway_effective_lanes[road]=lanes
                target_state.freeway_density[road]=[len(row)/(cell['length_km']*lane)
                                                   for row,cell,lane in zip(rows,cells,lanes)]
            inputs={oc.RAW_STATE_KEY:observed,oc.MERGED_DERIVED_KEY:derived}
        metadata=initialize(context,inputs,target_state,cfg,history_directory=history)
        expected=read(directory/'obs150'/f'vsl_cohorts_{end:06d}.json')
        actual=json.loads((history/f'vsl_cohorts_{end:06d}.json').read_bytes())
        for key in ('run_id','cutoff','frame_sha256','derived_sha256','applied_readbacks_sha256','cohorts','audit'):
            assert actual[key]==expected[key], ('Rebuilt physical VSL history differs',end,key)
        checks.append(dict(cutoff=end,cohorts_exact=True,audit_exact=True))
    for path,digest in pins.items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
    receipt=dict(cutoff=cutoff,manifest_sha256=context['manifest_sha256'],checks=checks,
                 original_files_unchanged=True,original_files=pins,
                 scope='Measured past replay only; no model rollout, relabelled old cache or future observations')
    (output/'vsl_history_replay.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return metadata


def prepare_vsl_release_commands(captured, previous, output):
    """Replay one actual history, then hold/release only the saved S13 VSL."""
    import shutil
    from src.models.state import ControlAction
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers import sdmpc_sequence as sequence
    cfg=captured['cfg']; start=6000; end=6450
    assert captured['state'].time_sec==start
    source=HERE/'closedloop_recorded6000_lever450_VSL_FW_E__seg13_detached/summary.json'
    prediction=json.loads(source.read_bytes())
    assert prediction['start_sec']==start and prediction['duration_sec']==450
    payload=json.loads(previous.read_bytes())
    reference=sequence.first_action(adapter.control_from_json(previous,cfg,ControlAction))
    assert reference.vsl['FW_E__seg13']==90
    actuation=adapter.adapter_actuation_settings(captured['calibration'],captured['tuning'])
    segment=adapter.repo_imports(ROOT/'vendor/NumSim-mine')[-1]
    plan=adapter.load_signal_group_actuation_plan()
    pins={str(source):hashlib.sha256(source.read_bytes()).hexdigest()}
    def rows(path):
        with path.open(encoding='utf-8-sig',newline='') as stream:
            return [{k:v for k,v in row.items() if k!='metadata'} for row in csv.DictReader(stream)]
    original_rows=rows(previous.with_suffix('.csv'))
    for arm,key in (('hold','held_actual'),('release','vsl_FW_E__seg13_release')):
        dest=output/arm/'commands';dest.mkdir(parents=True)
        predicted=prediction['results'][key]
        assert predicted['validation']['all_actuator_and_step_constraints_checked']
        for sec in (1,*range(150,start,150)):
            src=previous.parent/f'action_{sec:06d}'
            if sec>=900:
                assert src.with_suffix('.json.applied').is_file(), src
            for suffix in ('.json','.csv'):
                p=src.with_suffix(suffix);pins[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
                shutil.copy2(p,dest/p.name)
        for block,sec in enumerate(range(start,end+1,150)):
            command=predicted['commands'][min(block,2)]
            assert command['green_times']==reference.green_times and command['offsets']==reference.offsets
            assert command['meters']=={r:reference.diagnostics['rw_meter_green_'+r] for r in cfg.network.ramps}
            current=reference.copy();current.vsl=command['vsl']
            stem=dest/f'action_{sec:06d}'
            adapter.write_action_csv(stem.with_suffix('.csv'),current,cfg,captured['mapping'],segment,
                payload['metadata'],actuation,signal_group_plan_table=plan,offset_writer='experiment')
            stem.with_suffix('.json').write_text(json.dumps(adapter.control_to_json_dict(current,payload['metadata']),
                ensure_ascii=False),encoding='utf-8')
            actual=rows(stem.with_suffix('.csv'));assert len(actual)==len(original_rows)
            changed=[]
            for old,new in zip(original_rows,actual):
                if old!=new:
                    assert old['kind']==new['kind']=='vsl' and old['id']==new['id']=='RW_FW_E_S13'
                    assert float(old['speed_kph'])==90 and float(new['speed_kph'])==110
                    assert {k:v for k,v in old.items() if k!='speed_kph'}=={k:v for k,v in new.items() if k!='speed_kph'}
                    changed.append(int(new['dsd_no']))
            assert bool(changed)==(arm=='release')
        pins.update({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.iterdir()})
    network=HERE/'selected/network/native_seed29.inpx'
    digest=hashlib.sha256(network.read_bytes()).hexdigest()
    assert digest=='64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
    protocol=dict(start_sec=start,end_sec=end,seed=29,arms=['hold','release'],network=str(network),
        network_sha256=digest,command_pins=pins,original_run=str(previous.parent.parent),
        prediction_source=str(source),prediction_sha256=pins[str(source)],
        predicted_delta_omega_veh_h=prediction['results']['vsl_FW_E__seg13_release']['delta_ttt_omega_veh_h'],
        predicted_delta_tracked_total_veh_h=prediction['results']['vsl_FW_E__seg13_release']['delta_with_tracked_outside_veh_h'],
        controls='Replay actual1..5850; hold all commands or release only RW_FW_E_S13 from90 to110 during6000..6450.',
        warmup_application_proof='Warmup has no Python .applied marker; require native readback/LDP and exact original FZP prefix.',
        native_started=False,controller_optimization=False,future_observation_inputs=False,
        scope='Common actual SDMPC history,450s VSL-only hold/release response; not a new closed-loop policy or NC comparison')
    (output/'protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(prepared=str(output),native_started=False,rollouts=0)),flush=True)


def prepare_native_commands(captured, previous, output):
    """Freeze a finite paired replay using the canonical command writer."""
    if captured['state'].time_sec==6000:
        return prepare_vsl_release_commands(captured,previous,output)
    import shutil
    from src.models.state import ControlAction
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers import sdmpc_sequence as sequence
    cfg=captured['cfg'];start=1200;end=1650
    selected=HERE/'select1200v3/unused_action.json'
    action=adapter.control_from_json(selected,cfg,ControlAction)
    payload=json.loads(selected.read_bytes())
    tuning=captured['tuning']
    actuation=adapter.adapter_actuation_settings(captured['calibration'],tuning)
    segment=adapter.repo_imports(ROOT/'vendor/NumSim-mine')[-1]
    plan=adapter.load_signal_group_actuation_plan()
    pins={}
    for arm in ('hold','selected'):
        dest=output/arm/'commands';dest.mkdir(parents=True)
        for sec in (1,150,300,450,600,750,900,1050):
            for suffix in ('.json','.csv'):
                src=previous.parent/f'action_{sec:06d}{suffix}'
                pins[str(src)]=hashlib.sha256(src.read_bytes()).hexdigest()
                shutil.copy2(src,dest/src.name)
        controls=sequence.actions(action,3)
        for block,sec in enumerate((1200,1350,1500,1650)):
            stem=dest/f'action_{sec:06d}'
            if arm=='hold':
                for suffix in ('.json','.csv'):
                    shutil.copy2(previous.with_suffix(suffix),stem.with_suffix(suffix))
            else:
                current=controls[min(block,2)]
                adapter.write_action_csv(stem.with_suffix('.csv'),current,cfg,captured['mapping'],segment,
                    payload['metadata'],actuation,signal_group_plan_table=plan,offset_writer='experiment')
                stem.with_suffix('.json').write_text(json.dumps(
                    adapter.control_to_json_dict(current,payload['metadata']),ensure_ascii=False),encoding='utf-8')
        def physical_rows(path):
            with path.open(encoding='utf-8-sig',newline='') as f:
                return [{k:v for k,v in row.items() if k!='metadata'} for row in csv.DictReader(f)]
        if arm=='selected':
            assert physical_rows(dest/'action_001200.csv')==physical_rows(selected.with_suffix('.csv'))
        pins.update({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.iterdir()})
    network=HERE/'selected/network/native_seed29.inpx'
    assert hashlib.sha256(network.read_bytes()).hexdigest()=='64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
    protocol=dict(start_sec=start,end_sec=end,seed=29,arms=['hold','selected'],network=str(network),
        network_sha256=hashlib.sha256(network.read_bytes()).hexdigest(),command_pins=pins,
        selected_action=str(selected),selected_action_sha256=hashlib.sha256(selected.read_bytes()).hexdigest(),
        controls='Replay actual1..1050; hold1050 or execute preselected3blocks from1200. The1650 command affects no evaluated future interval.',
        native_started=False,controller_optimization=False,future_observation_inputs=False,
        scope='Matched native response check of a completed SDMPC decision, not closed-loop performance')
    (output/'protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(prepared=str(output),native_started=False,rollouts=0)),flush=True)


def main():
    signal_probe=next((x.split('=',1)[1] for x in sys.argv[1:]
                      if x.startswith('--closedloop-signal-probe=')),None)
    if signal_probe is not None:
        probe_closedloop_meters(selected_sec=int(signal_probe),signal_probe=True,
                               head_phase='--head-phase-queues' in sys.argv[1:],
                               head_service='--head-service10698' in sys.argv[1:],
                               service_reference='--head-service-reference' in sys.argv[1:])
        return
    selected_probe=next((x.split('=',1)[1] for x in sys.argv[1:]
                         if x.startswith('--closedloop-selected-probe=')),None)
    if selected_probe is not None:
        probe_closedloop_meters(selected_sec=int(selected_probe))
        return
    if '--closedloop-meter-tail' in sys.argv[1:]:
        probe_closedloop_meters(tail=True)
        return
    if '--closedloop-meter-probe' in sys.argv[1:]:
        probe_closedloop_meters()
        return
    sim_sec = int(next((x.split('=',1)[1] for x in sys.argv[1:] if x.startswith('--at=')), '900'))
    closedloop_recorded = '--closedloop-recorded' in sys.argv[1:]
    selected_meter_check = '--selected-meter-check' in sys.argv[1:]
    derivative_check = '--derivative-check' in sys.argv[1:]
    if derivative_check and selected_meter_check:raise ValueError('Choose one controller diagnostic')
    held_budget_check = '--held-budget-check' in sys.argv[1:] or selected_meter_check or derivative_check
    recording_dir=next((Path(x.split('=',1)[1]) for x in sys.argv[1:]
                        if x.startswith('--recording-dir=')),None)
    tuning_override=next((Path(x.split('=',1)[1]) for x in sys.argv[1:]
                         if x.startswith('--tuning-json=')),None)
    if recording_dir is not None and not closedloop_recorded:
        raise ValueError('An explicit recording directory requires closedloop recorded mode')
    recorded_times = (4500,) if selected_meter_check or derivative_check else (2700,3750,6000,8400) if held_budget_check else (3600,3750,4500,6000)
    if sim_sec not in (recorded_times if closedloop_recorded else (900,1050,1200)):
        raise ValueError('Only the existing recorded decision times are supported')
    trace_mode = '--trace' in sys.argv[1:]
    initialize_only = '--initialize-only' in sys.argv[1:]
    gate_audit = '--gate-audit' in sys.argv[1:]
    gate_initial = '--gate-initial' in sys.argv[1:]
    gate_future = '--gate-future' in sys.argv[1:]
    gate_lanes = '--gate-lanes' in sys.argv[1:]
    if gate_lanes and not gate_initial:raise ValueError('Gate lane capacity requires reviewed gate initialization')
    if gate_future and not gate_initial:raise ValueError('Future gate requires initial route preservation')
    gate_default = '--gate-default' in sys.argv[1:]
    if gate_initial and gate_default:raise ValueError('Choose enabled or disabled gate comparison')
    pooled_green = '--pooled-green' in sys.argv[1:]
    warm_heads = '--warm-head-history' in sys.argv[1:]
    warm_vsl = '--replay-vsl-history' in sys.argv[1:]
    if warm_vsl and not closedloop_recorded:raise ValueError('VSL replay requires a closed native recording')
    unique_head = '--head-turn-10633' in sys.argv[1:]
    lever_probe = '--lever-probe450' in sys.argv[1:]
    east_meters_only = '--east-meters-only' in sys.argv[1:]
    meter_tail = '--meter-tail900' in sys.argv[1:]
    tail_reference_dir=next((Path(x.split('=',1)[1]) for x in sys.argv[1:]
                            if x.startswith('--tail-reference-dir=')),None)
    if tail_reference_dir is not None and not meter_tail:
        raise ValueError('A tail reference belongs only to the fixed900s diagnostic')
    meter_ramp=next((x.split('=',1)[1] for x in sys.argv[1:] if x.startswith('--meter-ramp=')),None)
    if meter_ramp is not None and not (lever_probe or meter_tail):raise ValueError('A focused meter requires the existing lever or tail probe')
    vsl_zone=next((x.split('=',1)[1] for x in sys.argv[1:] if x.startswith('--vsl-zone=')),None)
    if vsl_zone is not None and (not lever_probe or meter_ramp is not None):
        raise ValueError('A focused VSL requires the lever probe and cannot be combined with a focused meter')
    if east_meters_only and (not lever_probe or meter_ramp is not None or vsl_zone is not None):
        raise ValueError('The four east-meter probe requires only --lever-probe450')
    held_probe = '--held450' in sys.argv[1:]
    lever_probe = lever_probe or held_probe
    select_mode = '--select' in sys.argv[1:]
    selection_check = '--selection-check' in sys.argv[1:]
    recorded_selection_check = '--recorded-selection-check' in sys.argv[1:]
    if recorded_selection_check and not (closedloop_recorded and selection_check):
        raise ValueError('A native recorded selection requires closedloop --selection-check')
    prepare_native = '--prepare-native-commands' in sys.argv[1:]
    if meter_tail and (not closedloop_recorded or sim_sec not in (4500,6000) or meter_ramp not in ('RM_C10681','RM_C10484')
                       or lever_probe or held_probe or select_mode or selection_check or prepare_native
                       or trace_mode or initialize_only or gate_audit or held_budget_check):
        raise ValueError('The tail check uses only a recorded4500/6000s10681/10484 state and its matching450s reference')
    if meter_tail and (sim_sec != 6000 or tuning_override is not None) and tail_reference_dir is None:
        raise ValueError('An explicit matching450s reference is required for this tail diagnostic')
    if held_budget_check and (not closedloop_recorded or select_mode or selection_check or
                              prepare_native or lever_probe or trace_mode or initialize_only or gate_audit):
        raise ValueError('Held-budget check requires one recorded state and no other probe mode')
    if prepare_native and (sim_sec not in (1200,6000) or select_mode or selection_check or lever_probe
                           or (sim_sec==6000 and not closedloop_recorded)):
        raise ValueError('Prepare only the1200s selection or the saved6000s VSL release')
    if selection_check and (select_mode or trace_mode or initialize_only or gate_audit or lever_probe):
        raise ValueError('Selection check evaluates only the saved held and selected sequences')
    if select_mode and (trace_mode or initialize_only or gate_audit or lever_probe):
        raise ValueError('Select runs the actual controller; do not combine with intercepted prediction modes')
    canonical_prior = '--canonical-prior' in sys.argv[1:]
    physical_travel = '--physical-travel' in sys.argv[1:]
    if physical_travel and not canonical_prior:
        raise ValueError('Physical travel comparison requires canonical native priors')
    ready_only = '--ready-arrivals' in sys.argv[1:]
    north_modes=[mode for flag,mode in (('--native-north','both'),('--north-bypass-only','bypass'),
                                       ('--north-prior-only','prior')) if flag in sys.argv[1:]]
    if len(north_modes)>1:raise ValueError('Choose one north-path diagnostic intervention')
    north_mode=north_modes[0] if north_modes else None
    native_north = north_mode is not None
    north_authority = '--north-authority' in sys.argv[1:]
    north_past_floor = '--north-past-floor' in sys.argv[1:]
    if north_authority and native_north:
        raise ValueError('Canonical authority and post-initialization north interventions are separate probes')
    if north_past_floor and (not north_authority or sim_sec != 1200):
        raise ValueError('Past-only service evidence is reviewed for north authority at1200 only')
    native_priors = '--native-priors' in sys.argv[1:]
    recorded_mode = closedloop_recorded or '--recorded' in sys.argv[1:] or native_priors or canonical_prior or pooled_green or warm_heads
    from evaluation.controllers import runtime_setup
    from evaluation.controllers import vissim_stackelberg_adapter as adapter

    name = 'recorded_ramp_native_prior900' if native_priors else 'recorded_ramp_response900' if recorded_mode else 'arrival_path_probe'
    if canonical_prior:
        name='recorded_ramp_canonical_prior900'
    if ready_only:
        name+='_ready'
    if physical_travel:
        name+='_travel'
    if native_north:
        name+='_north'
        if north_mode!='both':name+='_'+north_mode
    if north_authority:
        name+='_north_authority'
    if north_past_floor:
        # Keep Windows history paths below MAX_PATH; this flag requires authority.
        name=name.replace('_north_authority','_north_floor')
    if pooled_green:
        name+='_pool4'
    if unique_head:
        name+='_head10633'
    if warm_heads:
        name+='_history'
    name=name.replace('900',str(sim_sec))
    if trace_mode:
        name += '_trace'
    if initialize_only:
        name += '_init'
    if lever_probe:
        name += '_lever450'
    if gate_audit:
        name='gate_audit'+str(sim_sec)
    if gate_initial or gate_default:
        if not (canonical_prior and physical_travel and north_authority and pooled_green and unique_head and warm_heads):
            raise ValueError('Gate comparison requires the reviewed full diagnostic baseline')
        name=('gate_initial' if gate_initial else 'gate_default')+str(sim_sec)+('_init' if initialize_only else '_trace' if trace_mode else '')
        if gate_future:name=name.replace('gate_initial','gate_future')
        if gate_lanes:name=name.replace(str(sim_sec),'_lanes'+str(sim_sec))
        if held_probe:name+='_held450'
    if select_mode:name='select'+str(sim_sec)
    if select_mode and '--activation-restored' in sys.argv[1:]:name+='v2'
    if select_mode and '--np-domain-restored' in sys.argv[1:]:name='select'+str(sim_sec)+'v3'
    if selection_check:name='select'+str(sim_sec)+'v3_check'
    if prepare_native:name='native_pair'+str(sim_sec)
    if closedloop_recorded:
        name='closedloop_recorded'+str(sim_sec)+('_prior' if canonical_prior else '')
        if physical_travel:name+='_travel'
        if trace_mode:name+='_trace'
        if initialize_only:name+='_init'
        if lever_probe:name+='_lever450'+('_'+meter_ramp if meter_ramp else '_VSL_'+vsl_zone if vsl_zone else '')
        if select_mode:name+='_select'
        if selection_check:name+='_select_check'
        if held_budget_check:name+='_budget_check'
        if selected_meter_check:name+='_selected_meter'
        if derivative_check:name+='_derivatives'
        if prepare_native:name+='_native_vsl_release'
        if meter_tail:name+='_meter900_'+meter_ramp
    label = next((x.split('=',1)[1] for x in sys.argv[1:] if x.startswith('--probe-label=')), '')
    if label and not all(c.isalnum() or c in '_-' for c in label):
        raise ValueError('Probe label must be a simple directory suffix')
    output = HERE / (name + ('_' + label if label else ''))
    if (label or select_mode or selection_check or prepare_native or closedloop_recorded) and output.exists():
        raise ValueError('Preserve the previous selection attempt; inspect it before another decision')
    output.mkdir(exist_ok=True)
    captured = {}
    configure = runtime_setup.configure_runtime
    forecast_fn = adapter.demand_from_state

    class Ready(BaseException):
        pass

    def capture_runtime(*args, **kwargs):
        if canonical_prior or pooled_green or unique_head or north_authority:
            args=list(args)
            args[2]=copy.deepcopy(args[2])
        if canonical_prior:
            args[2]['urban']['known_wout_native_choice_prior']=True
            args[2]['urban']['known_wout_physical_travel']=physical_travel
        if pooled_green:
            args[2]['urban']['capacity']['head_green_exposure_windows']=4
        if unique_head:
            args[2]['urban']['capacity']['head_resource_contract']=str((HERE/'head_service_resource_10633.json').relative_to(ROOT))
        if north_authority:
            args[2]['urban']['movements']['physical_phase_authority']=str((HERE/'physical_phase_authority_10625.json').relative_to(ROOT))
        if gate_initial:
            args[2]['urban'].setdefault('ramp',{})['initial_native_gate_routes']=True
            args[2]['urban']['ramp']['native_gate_travel']=gate_future
            if gate_lanes:
                # Existing1-lane nominal1800 is explicit; this changes the
                # connector lane multiplier, not a fitted saturation rate.
                args[2]['urban']['ramp']['gate_entry_capacity_per_lane_veh_h']=1800.
        result = configure(*args, **kwargs)
        captured.update(state=result[0], cfg=args[1], tuning=args[2], mapping=args[3], raw=args[4],calibration=args[7],
                        detector=result[1], metadata=result[2])
        return result

    def capture_forecast(*args, **kwargs):
        result = forecast_fn(*args, **kwargs)
        captured['forecast'] = result
        if select_mode or held_budget_check:
            return result
        raise Ready()

    previous = Path('D:/VISSIM_runs/20260924_sd31_gain/sdmpc31_g_gain_s29_r3/'
                    'decisions_sdmpc31_g_gain_s29_r3') / f'action_{sim_sec-150:06d}.json'
    state_path = HERE / f'selected_init{sim_sec}_final/state_{sim_sec:06d}.json'
    if closedloop_recorded:
        folder=recording_dir or Path('D:/VISSIM_runs/20260927_sd31_closedloop9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
        previous=folder/f'action_{sim_sec-150:06d}.json'
        state_path=folder/f'state_{sim_sec:06d}.json'
        assert previous.with_suffix('.json.applied').is_file() and state_path.is_file()
    tuning_path = tuning_override or HERE / 'selected/config_n31_v2.json'
    selected_path = HERE / (f'closedloop_recorded{sim_sec}_select' if closedloop_recorded
                            else f'select{sim_sec}v3') / 'unused_action.json'
    if label:
        selected_path = selected_path.parent.with_name(selected_path.parent.name+'_'+label)/selected_path.name
    if recorded_selection_check:
        selected_path = folder/f'action_{sim_sec:06d}.json'
        assert selected_path.with_suffix('.json.applied').is_file()
        provenance = json.loads(next(folder.parent.glob('run_provenance_*.json')).read_bytes())
        assert hashlib.sha256(tuning_path.read_bytes()).hexdigest() == provenance['files']['tuning']['sha256']
        assert provenance['files']['network']['sha256'] == '64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
    elif selection_check or selected_meter_check:
        pins=json.loads((selected_path.parent/'summary.json').read_bytes())['files']
        for source in (state_path,tuning_path,previous,selected_path):
            assert hashlib.sha256(source.read_bytes()).hexdigest()==pins[str(source)], source
    sys.argv = [str(Path(adapter.__file__)),
                '--state-json', str(state_path),
                '--previous-action-json', str(previous),
                '--out-action-json', str(output/'unused_action.json'),
                '--out-action-csv', str(output/'unused_action.csv'),
                '--mapping-json', str(ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'),
                '--detector-mapping-json', str(ROOT/'evaluation/real_world_modi_control_ver2_20260907/detector_local_mapping_ver2_20260907.json'),
                '--calibration-json', str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'),
                '--tuning-json', str(tuning_path), '--controller', 'wu-link']
    for key, value in dict(RW_DECISION_FAIL_FAST='1', RW_MAINLINE_SG_ONLY='1',
                           RW_OFFSET_WRITER='experiment', RW_RAMP_AMBER_SEC='0').items():
        os.environ[key] = value
    from evaluation.controllers import head_service_resources
    observe_heads=head_service_resources.observe
    history_inputs=[]
    def warm_observer(original,cfg,raw,previous_path,caps,plan,distribute,options):
        return replay_head_history(observe_heads,original,cfg,raw,caps,plan,distribute,options,
            folder=previous.parent,sim_sec=sim_sec,output=output,history_inputs=history_inputs)
    if warm_heads:
        head_service_resources.observe=warm_observer
    from evaluation.controllers import vsl_exposure_history
    initialize_vsl=vsl_exposure_history.initialize
    if warm_vsl:
        vsl_exposure_history.initialize=lambda context,raw,state,cfg: replay_vsl_history(
            initialize_vsl,context,raw,state,cfg,output)
    runtime_setup.configure_runtime = capture_runtime
    adapter.demand_from_state = capture_forecast
    from evaluation.controllers import sdmpc_pfo
    pfo_solve = sdmpc_pfo.solve
    def capture_held_budget(reference, coord, policy, options, evaluate, derivative,
                            quantities, check_budget, emit):
        if derivative_check:
            assert warm_heads and warm_vsl and tuning_override is not None
            probe_controller_derivatives(captured,reference,coord,evaluate,derivative,quantities,
                output,(state_path,previous,tuning_path,
                        *(Path(p) for row in history_inputs for p in row)))
            captured['held_budget_checked']=True
            raise Ready()
        if selected_meter_check:
            probe_selected_meter(captured,reference,coord,options,evaluate,selected_path,output)
            captured['held_budget_checked']=True
            raise Ready()
        # Evaluate precisely the controller's original held action, then stop
        # before PFO or SDMPC optimization. No actuator or coefficient changes.
        source = previous.parent / f'action_{sim_sec:06d}.joint.json'
        saved = json.loads(source.read_bytes())['selection']
        item = evaluate([reference], derivatives=False)[0]
        actual = quantities(reference, item)
        caps = [saved['final_constraints'][key]['target'] for key in ('np','nuf')]
        tolerances = [saved['final_constraints'][key]['tolerance'] for key in ('np','nuf')]
        coord.validate(reference)
        physical = sdmpc_pfo.model_feasible(item, options['shared_tolerance'])
        checked = {key:dict(actual=float(value), cap=cap, tolerance=tol,
                           satisfied=bool(value <= cap+tol))
                   for key,value,cap,tol in zip(('np','nuf'),actual,caps,tolerances)}
        error = item['objective_veh_h'] - saved['held_objective']
        report = dict(start_sec=sim_sec, model=item['prediction_model'],
            original_held_objective=saved['held_objective'], reproduced_held_objective=item['objective_veh_h'],
            held_objective_error=error, objective_reproduced=abs(error)<1e-7,
            selected_objective=saved['selected_objective'],
            selected_minus_held=saved['selected_objective']-item['objective_veh_h'],
            held_omega_partition=item['sdmpc_omega_partition']['costs'],
            selected_omega_partition=saved['omega_partition']['costs'],
            quantities_at_selected_caps=checked, physical_model_feasible=physical,
            held_feasible_at_selected_caps=physical and all(q['satisfied'] for q in checked.values()),
            controller_iterations=0, scalar_rollouts=1, native_started=False,
            files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                   (state_path,previous,tuning_path,source)},
            scope='Saved original held command tested against the actually selected NP/NUF caps; no new optimum or native-gain claim')
        (output/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
        print(json.dumps({k:report[k] for k in ('start_sec','held_objective_error',
            'selected_minus_held','held_feasible_at_selected_caps','quantities_at_selected_caps')}),flush=True)
        captured['held_budget_checked']=True
        raise Ready()
    if held_budget_check:
        sdmpc_pfo.solve = capture_held_budget
    started = time.perf_counter()
    try:
        adapter.main()
        if not select_mode:
            raise AssertionError('Adapter did not reach forecast capture')
    except Ready:
        pass
    finally:
        runtime_setup.configure_runtime = configure
        adapter.demand_from_state = forecast_fn
        head_service_resources.observe=observe_heads
        vsl_exposure_history.initialize=initialize_vsl
        sdmpc_pfo.solve = pfo_solve
    initialization_sec = time.perf_counter()-started

    if held_budget_check:
        assert captured.get('held_budget_checked'), 'Original PFO entry was not reached'
        return

    if select_mode:
        action_path=output/'unused_action.json'
        report_path=output/'unused_action.joint.json'
        budget_path=output/'unused_action.decision_budget.json'
        report=json.loads(report_path.read_bytes())
        budget=json.loads(budget_path.read_bytes())
        assert report['completed'] and budget['output_completed']
        receipt=dict(purpose='One actual SDMPC decision on a saved state; no VISSIM command applied',
            start_sec=sim_sec,controller_wall_sec=initialization_sec,
            native_started=False,gain_qualified=False,
            physics='Plant specified by the pinned tuning file; see plant_manifest',
            plant_manifest=captured['tuning']['freeway']['lane_plant'],
            options='Existing solver horizon, iterations, prices, constraints and action ranges unchanged',
            files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                   (state_path,tuning_path,previous,action_path,report_path,budget_path)})
        (output/'summary.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(receipt,ensure_ascii=False),flush=True)
        return

    from src.models.state import ControlAction
    from src.controllers import rollout_endpoint as endpoint
    from evaluation.controllers import area_meter_finalization as meters
    from evaluation.controllers.sdmpc_tangent_worker import state_error
    cfg, state = captured['cfg'], captured['state']
    assert cfg.network.sdmpc_options is not None
    if prepare_native:
        prepare_native_commands(captured,previous,output)
        return
    if gate_audit:
        from src.models import urban_queue_model as uqm
        names=[m for m,s in cfg.network.urban_movements.items() if s.get('origin')=='in_SC1001_W']
        audit=dict(start_sec=sim_sec,
            source_specs={m:cfg.network.urban_movements[m] for m in names},
            cached_specs={m:uqm.movement_specs(cfg)[m] for m in names},
            capacities={m:cfg.network.movement_capacity_by_movement_veh_h[m] for m in names},
            gate_metadata={k:v for k,v in adapter._LEGSPLIT_LAST.items() if k.startswith('gate_onramp_beta_')},
            forecast_urban_boundary=[d.urban_boundary for d in captured['forecast']],
            raw_demand=captured['raw'].get('demand'),
            raw_far=captured['raw'].get('local_observation',{}).get('far_measurement'),
            urban_movement_queue={m:state.urban_movement_queue[m] for m in names},
            urban_link_storage=state.urban_link_storage,
            storage_release_buffer=state.urban_storage_release_buffer,
            urban_boundary_buffer=getattr(state,'urban_boundary_release_buffer',None),
            boundary_queue=state.boundary_queue,
            projection=state.local_observation_summary,
            native_ramp_regions=captured['metadata'].get('physical_ramp_observed_regions'),
            current_routes=captured['raw'].get('vehicle_routes'),
            current_vehicles=[r for r in captured['raw']['vehicle_records']['records']
                              if str(r['link_no']) in ('32','10778','129','127','10482','10490')],
            source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (state_path,tuning_path,previous)})
        (output/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
        print(json.dumps(dict(audit=str(output),forecasts_run=0,initialization_sec=initialization_sec)))
        return
    runtime_evidence=dict(
        initial_sec=state.time_sec,
        initial_source_sha256=hashlib.sha256(state_path.read_bytes()).hexdigest(),
        unresolved_movement_routes={m:dict(spec=s,initial_queue=state.urban_movement_queue.get(m,0.),
            route=cfg.network.control_area_routes.get('movement:'+m),
            forecast_boundary=[d.urban_boundary.get(s.get('origin'),0.) for d in captured['forecast']])
            for m,s in cfg.network.urban_movements.items()
            if cfg.network.control_area_routes.get('movement:'+m,{}).get('inside_to_inside') is None
            and cfg.network.control_area_routes.get('movement:'+m,{}).get('outside_to_inside') is None
            and type(cfg.network.control_area_routes.get('movement:'+m,{}).get('target_inside')) is not bool},
        gate_future_travel=captured['metadata'].get('gate_future_travel'),
        gate_entry_capacity_veh_h=captured['metadata'].get('gate_entry_capacity_veh_h'),
        gate_initial_route_metadata={k:v for k,v in captured['metadata'].items() if k.startswith('gate_initial_')},
        gate_initial_route_evidence=getattr(state,'gate_initial_route_evidence',None),
        gate_initial_route_tags=getattr(state,'gate_initial_route_tags',None),
        posthead_receiving=getattr(state.lane_ramp_runtime,'receiving_observations',{}),
        movement_capacity_veh_h={k:v for k,v in cfg.network.movement_capacity_by_movement_veh_h.items() if k.startswith('SC1004_')},
        head_resources=getattr(cfg.network,'head_service_resources',None),
        diagnostic_head_history_inputs=history_inputs,
        metadata={k:v for k,v in captured['metadata'].items() if k.startswith(('head_','movement_capacity_by_lanes','movement_capacity_perimeter','physical_unsignalized_authority'))},
        capacity_configuration=captured['tuning']['urban'].get('capacity',{}))
    runtime_evidence['unresolved_projection_sources']={link:allocation
        for link,allocation in state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link'].items()
        if any(stock.startswith('movement:') and stock.removeprefix('movement:') in runtime_evidence['unresolved_movement_routes']
               and count for stock,count in allocation.items())}
    (output/'runtime.json').write_text(json.dumps(runtime_evidence,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    if initialize_only:
        print(json.dumps({'initialized':str(output),'wall_sec':initialization_sec}))
        return
    if ready_only:
        # Diagnostic only: quantify the second travel-rate gate after the
        # existing release buffer has already declared a vehicle arrived.
        old_rate=adapter._legsplit_wout_rate
        adapter._legsplit_wout_rate=lambda net,link,speed: (3600./cfg.simulation.T_u_sec
            if link=='SC1004_W_out' else old_rate(net,link,speed))
    prior_comparison = None
    north_proof = None
    north_service = None
    if north_authority:
        spec=cfg.network.urban_movements['SC1004_N_SC1003_to_W']
        assert spec['unsignalized'] is True and spec['phase']=='SC1004_p1'
    if north_past_floor:
        evidence_path=HERE/'north_past_crossings1200.json'
        evidence=json.loads(evidence_path.read_bytes())
        assert evidence['cutoff_sec']==sim_sec and evidence['max_observed_sec']<=sim_sec
        pin=cfg.network.physical_ramp_branches['network']
        assert evidence['network']['sha256']==pin['sha256']
        rates=[evidence['windows'][str(t)]['10625']['achieved_lower_bound_vph'] for t in (1050,1200)]
        assert all(x>0 for x in rates)
        movement='SC1004_N_SC1003_to_W'
        before=cfg.network.movement_capacity_by_movement_veh_h[movement]
        floor=min(rates)
        cfg.network.movement_capacity_by_movement_veh_h[movement]=max(before,floor)
        north_service=dict(source=str(evidence_path.relative_to(ROOT)),sha256=hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
            before_vph=before,after_vph=max(before,floor),past_windows=[(900,1050),(1050,1200)],
            observed_only_lower_bound_vph=floor,saturation_identified=False,
            online_observation_channel_available=False,production_enabled=False)
    if native_north:
        from evaluation.controllers.offramp_routing import _weight
        pin=cfg.network.physical_ramp_branches['network']
        network=ROOT/pin['path']
        assert hashlib.sha256(network.read_bytes()).hexdigest()==pin['sha256']
        tree=ET.parse(network).getroot()
        choice=tree.find(".//vehicleRoutingDecisionStatic[@no='1125']")
        assert choice.get('link')=='46' and choice.get('allVehTypes')=='true' and choice.get('routeChoiceMeth')=='STATIC'
        targets={'1':('SC1004_N_SC1003_to_W','10625'),
                 '2':('SC1004_N_SC1003_to_S','10626'),
                 '3':('SC1004_N_SC1003_to_E_SC1005','10627')}
        routes=choice.findall('./vehRoutSta/vehicleRouteStatic')
        assert {r.get('no') for r in routes}==set(targets)
        weights={r.get('no'):_weight(r) for r in routes}
        for r in routes:
            assert r.find('./linkSeq/intObjectRef').get('key')==targets[r.get('no')][1]
        edge=tree.find("./links/link[@no='10625']/fromLinkEndPt")
        assert edge.get('lane')=='46 1'
        heads=[h.attrib for h in tree.findall('./signalHeads/signalHead')
               if h.get('lane')=='46 1']
        assert heads and all(float(h['pos'])>float(edge.get('pos')) for h in heads)
        assert not [h for h in tree.findall('./signalHeads/signalHead') if h.get('lane','').startswith('10625 ')]
        north_proof=dict(before={m:dict(cfg.network.urban_movements[m]) for m,c in targets.values()},
                         native_weights=weights,connector=10625,source_position_m=float(edge.get('pos')),heads=heads)
        if north_mode in ('both','prior'):
            for k,(m,c) in targets.items():cfg.network.urban_movements[m]['beta']=weights[k]/sum(weights.values())
        if north_mode in ('both','bypass'):
            cfg.network.urban_movements['SC1004_N_SC1003_to_W']['phase']=''
        north_proof['capacity_vph_unchanged']=cfg.network.movement_capacity_by_movement_veh_h['SC1004_N_SC1003_to_W']
        north_proof['mode']=north_mode
        north_proof['scope']='Diagnostic single-factor or combined future turn weights/pre-head bypass; original projected queue and service capacity held; not production calibration'
    if native_priors:
        from evaluation.controllers.offramp_routing import _weight
        assert cfg.network.known_legsplit_routes['storage']=='SC1004_W_out'
        pin=cfg.network.physical_ramp_branches['network']
        network=ROOT/pin['path']
        assert hashlib.sha256(network.read_bytes()).hexdigest()==pin['sha256']
        tree=ET.parse(network).getroot()
        assert [float(x.get('start')) for x in tree.findall(".//timeIntervalSet[@no='VEHICLEROUTESTATIC']/timeInts/timeInterval")]==[0.]
        decision=tree.find(".//vehicleRoutingDecisionStatic[@no='1135']")
        assert decision.get('link')=='68' and decision.get('allVehTypes')=='true' and decision.get('routeChoiceMeth')=='STATIC'
        routes=decision.findall('./vehRoutSta/vehicleRouteStatic')
        assert {r.get('no') for r in routes}=={'2','3','4'}
        weights={r.get('no'):_weight(r) for r in routes}
        total=sum(weights.values())
        before=copy.deepcopy(cfg.network.boundary_out_ramp_split['SC1004_W_out'])
        after=dict(free=weights['3']/total,ramps=dict(RM_C10646=weights['2']/total,RM_C10681=weights['4']/total))
        cfg.network.boundary_out_ramp_split['SC1004_W_out']=after
        prior_comparison=dict(network=pin,decision=1135,weights=weights,before=before,after=after,
                              scope='Future eligible1135 choices only; existing known destinations and1130:3 free cohort unchanged',
                              production_configuration_changed=False)
    action = meters.prepare_held_actual_reference(
        adapter.control_from_json(previous, cfg, ControlAction), cfg)
    if meter_tail:
        reference_dir=tail_reference_dir or HERE/'closedloop_recorded6000_lever450_RM_C10681_detached'
        source_paths=(state_path,previous,tuning_path)
        receipt=dict(files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths},
                     actual_reference=str(previous),new_native_runs=0,optimizer_iterations=0)
        (output/'source_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        probe_meter_tail(captured,action,output,ramp=meter_ramp,reference_dir=reference_dir)
        assert receipt['files']=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}
        return
    if selection_check:
        probe_levers(captured,action,output,selected_path=selected_path)
        return
    if lever_probe:
        probe_levers(captured,action,output,only_reference=held_probe,
                     meter_only=meter_ramp is not None or east_meters_only,meter_ramp=meter_ramp,vsl_zone=vsl_zone,
                     trace_response=trace_mode)
        return
    if recorded_mode:
        previous = previous.with_name(f'action_{sim_sec:06d}.json')
        assert previous.with_suffix('.json.applied').is_file()
        action = meters.prepare_held_actual_reference(
            adapter.control_from_json(previous, cfg, ControlAction), cfg)
    keys = list(cfg.network.ramps)
    assert len(keys) == 8
    masked = list(cfg.network.gate_onramp_queue_ramps)
    report = dict(purpose='Field-consumption probe, not gain qualification or forecast calibration',
                  controller_configuration='wu-link/SDMPC', simulation_started=False,
                  initialization_sec=initialization_sec, start_sec=state.time_sec,
                  duration_sec=cfg.simulation.T_c_sec,
                  physical_ramps=keys, zeroed_exogenous_ramps=masked,
                  exogenous_movement_receivers=cfg.network.on_ramp_to_movement,
                  actual_urban_routes_unchanged=True,
                  diagnostic_native_prior=prior_comparison,
                  canonical_native_prior=cfg.network.known_legsplit_routes.get('future_choice_weights'),
                  canonical_physical_travel=cfg.network.known_legsplit_routes.get('physical_travel'),
                  pooled_green_windows=getattr(cfg.network,'head_green_exposure_windows',0),
                  diagnostic_head_history_inputs=history_inputs,
                  diagnostic_native_north=north_proof,
                  canonical_north_authority=north_authority,
                  diagnostic_north_past_service=north_service,
                  diagnostic_remove_second_travel_gate=ready_only,
                  inputs={str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p):
                          hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in (state_path,tuning_path,previous)}, cases={})
    points = {}
    cases = (('recorded',1.),) if recorded_mode else (('original',1.),('zero_proxy',0.),('hundredfold_proxy',100.))
    for name, factor in cases:
        demand = copy.deepcopy(captured['forecast'][:1])
        demand[0].ramp_arrival = {k:v*factor for k,v in demand[0].ramp_arrival.items()}
        started = time.perf_counter()
        point = endpoint.evaluate_price_point(state, action, demand, (),
            endpoint.ObjectiveSpec(cfg, depth_override=1, box_walk=False, score_mode='raw'),
            capture_response=True)
        assert not point.aborted and len(point.states)==1
        points[name] = point
        report['cases'][name] = dict(wall_sec=time.perf_counter()-started,
            ramp_arrival_vph=demand[0].ramp_arrival,
            ttt_omega_veh_h=point.ttt, objective=point.objective,
            control_area=point.control_area,
            final_ramp_queue=point.states[-1].ramp_queue)
        print(json.dumps(dict(case=name,wall_sec=report['cases'][name]['wall_sec'],
                              ttt_omega_veh_h=point.ttt)),flush=True)
    if recorded_mode:
        point = points['recorded']
        # Future observations are opened ONLY after prediction, as targets.
        future_path = previous.with_name(f'state_{sim_sec+150:06d}.json')
        derived_path = previous.parent/f'obs150/derived_{sim_sec+150:06d}.json'
        future = json.loads(future_path.read_bytes())
        derived = json.loads(derived_path.read_bytes())
        assert derived['window']==dict(start_s=sim_sec,end_s=sim_sec+150)
        assert derived['removals']['window_total']==len(derived['removals']['rows'])
        raw = captured['raw']
        for source in (raw,future):
            assert source['vehicle_records']['complete']
        with (HERE/'selected/obs150/obs150_detectors_v2.csv').open(encoding='utf-8-sig',newline='') as f:
            detectors = list(csv.DictReader(f))
        response = point.control_area_response
        if trace_mode:
            storage='SC1004_W_out'
            moves={m:v for m,v in cfg.network.urban_movements.items() if m.startswith('SC1004_')}
            def local_snapshot(s):
                return dict(movement_queue={m:s.urban_movement_queue.get(m,0.) for m in moves},
                    storage_free=s.urban_link_storage[storage],
                    pending=s.urban_storage_release_buffer.get(storage,{}),
                    known_routes=s.known_legsplit_route_state)
            trace=dict(movements=moves,initial=local_snapshot(state),final=local_snapshot(point.states[-1]),
                **({'gate_future_final_accounting':point.states[-1].gate_future_accounting}
                   if hasattr(point.states[-1],'gate_future_accounting') else {}),
                physical_initial_owners={p:a for p,a in state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link'].items()
                                        if a.get('storage:'+storage,0)>0},
                storage_capacity=cfg.network.urban_link_storage_veh[storage],
                greens={k:v for k,v in action.green_times.items() if 'SC1004' in k},
                offsets={k:v for k,v in action.offsets.items() if 'SC1004' in k},
                actual_head_window=[h for h in derived['head_window']['heads'] if h['sc']=='1004'],
                initial_model_observation_summary=state.local_observation_summary,
                response=response)
            if getattr(state.lane_ramp_runtime,'conflict_snapshot',{}):
                trace['ramp_conflict_snapshot']=state.lane_ramp_runtime.conflict_snapshot
            if hasattr(state,'gate_initial_route_evidence'):
                trace['gate_initial_route_evidence']=state.gate_initial_route_evidence
            with gzip.open(output/'trace.json.gz','wt',encoding='utf-8') as f:
                json.dump(trace,f,ensure_ascii=False,allow_nan=False)
        rows = {}
        for ramp in keys:
            link = int(ramp.removeprefix('RM_C'))
            def stock(source):
                return sum(int(v['link_no'])==link for v in source['vehicle_records']['records'])
            observed_start,observed_end = stock(raw),stock(future)
            assert abs(state.ramp_queue[ramp]-observed_start)<1e-7
            observed_arrival = derived['boundaries']['ramp_arrival:'+ramp]['cross']
            head_refs = {r['boundary_ref'] for r in detectors
                         if r['role']=='meter_head' and int(r['link'])==link}
            observed_head = sum(derived['boundaries'][ref]['cross'] for ref in head_refs)
            removed=sum(int(row['link'])==link for row in derived['removals']['rows'])
            observed_merge = observed_start+observed_arrival-observed_end-removed
            transfers = response['transfers']
            predicted_arrival = sum(r['vehicles'] for r in transfers if r['target']=='ramp:'+ramp)
            predicted_merge = sum(r['vehicles'] for r in transfers
                                  if r['source']=='ramp:'+ramp and r['target']=='merge_pending:'+ramp)
            predicted_head = sum(r['accepted_total_veh'] for r in response['resource_allocations']
                                 if r['kind']=='physical_ramp_head_service' and r['resource'].split(':')[0]==ramp)
            predicted_end = point.states[-1].ramp_queue[ramp]
            residual=observed_start+predicted_arrival-predicted_merge-predicted_end
            assert abs(residual)<1e-7, (ramp,residual)
            rows[ramp]=dict(initial_stock_veh=observed_start,
                actual=dict(arrival=observed_arrival,head=observed_head,merge=observed_merge,final_stock=observed_end),
                native_ramp_removals_veh=removed,
                predicted=dict(arrival=predicted_arrival,head=predicted_head,merge=predicted_merge,final_stock=predicted_end),
                stock_conservation_residual_veh=residual)
            sources={r['source'] for r in transfers if r['target']=='ramp:'+ramp}
            rows[ramp]['predicted_arrival_by_source']={str(source):sum(r['vehicles'] for r in transfers
                if r['target']=='ramp:'+ramp and r['source']==source) for source in sorted(sources)}
            rows[ramp]['prediction_minus_actual_veh']={k:rows[ramp]['predicted'][k]-v for k,v in rows[ramp]['actual'].items()}
        report.update(purpose='Recorded-command one-step response validation, not causal control-gain validation',
                      ramps=rows, future_target_only=True, removals=derived['removals'],
                      actual_merge_method='Initial connector stock + corrected entry crossings - final connector stock - native connector removals',
                      limitations=[f'Single recorded seed29 window{sim_sec}-{sim_sec+150}; no independent seed or prevention/recovery result.',
                                   'Recorded action includes urban green/offset and VSL changes; no lever-isolated inference.',
                                   'Native applied receipt checked; LDP/readback verification is reused from the prior run audit.'])
        report['target_inputs']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (future_path,derived_path)}
        (output/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(dict(summary=str(output/'summary.json'),ramps=rows)),flush=True)
        return
    baseline = points['original']
    for name in ('zero_proxy','hundredfold_proxy'):
        point = points[name]
        error = state_error(baseline.states,point.states)
        report['cases'][name]['all_stored_state_max_error'] = error
        report['cases'][name]['ttt_difference_veh_h'] = point.ttt-baseline.ttt
        report['cases'][name]['objective_difference'] = point.objective-baseline.objective
    report['proxy_has_no_physical_effect_in_this_probe'] = all(
        report['cases'][n]['all_stored_state_max_error']==0. and
        report['cases'][n]['objective_difference']==0.
        for n in ('zero_proxy','hundredfold_proxy'))
    report['limitations'] = [
        f'One recorded state at {sim_sec}s and one held 150s interval; not congestion/gain validation.',
        'Does not prove endogenous urban-to-ramp demand is correct.',
        'Leader proposal/initialization may still consume the unmasked proxy forecast.',
        'No parameter, demand configuration, physical model or controller search changed.']
    (output/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(summary=str(output/'summary.json'),
                          proxy_invariant=report['proxy_has_no_physical_effect_in_this_probe'])),flush=True)


if __name__ == '__main__':
    main()
