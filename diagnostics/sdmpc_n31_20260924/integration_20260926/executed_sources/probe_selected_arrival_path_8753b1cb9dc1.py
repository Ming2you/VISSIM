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


def probe_levers(captured, reference, output):
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
    box = neighbors.build_fixed_move_box(ownership,reference,cfg,limits)
    coord = sequence.SequenceCoordinates(cfg,reference,box,cfg.network.sdmpc_options)
    anchor = coord.encode(reference)
    candidates = {'held_actual': coord.decode(anchor,reference)}
    east_axes = [(j,a) for j,a in enumerate(coord.axes) if a['owner']=='FW_E']
    for kind in ('meter','vsl'):
        keys = list(dict.fromkeys(a['key'] for j,a in east_axes if a['kind']==kind))
        for key in keys:
            z = anchor.copy()
            for j,a in east_axes:
                if a['kind']!=kind or a['key']!=key:
                    continue
                if kind=='meter':
                    initial=reference.diagnostics['rw_meter_green_'+key]
                    value=max(cfg.network.physical_ramp_branches['minimum_green_sec'],
                              initial-(a['block']+1)*limits['meter_green_sec'])
                else:
                    initial=reference.vsl[key]
                    value=max(min(cfg.freeway_follower.vsl_set),initial-20.)
                assert value in a['allowed'], (key,value,a['allowed'])
                z[j]=(value-initial)/a['scale']
            candidates[kind+'_'+key]=coord.decode(z,reference)
    results={}
    for name,action in candidates.items():
        receipt=coord.validate(action)
        started=time.perf_counter()
        point=endpoint.evaluate_price_point(state,action,copy.deepcopy(captured['forecast'][:3]),(),
            endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
        assert not point.aborted and len(point.states)==3
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
        item=dict(wall_sec=time.perf_counter()-started,ttt_omega_veh_h=point.ttt,
                  tracked_outside_residence_veh_h=sum(outside.values()),
                  ttt_with_tracked_outside_veh_h=point.ttt+sum(outside.values()),
                  control_area=point.control_area,cost_by_stock=costs,
                  outside_cost_by_stock={k:v for k,v in outside.items() if v},ramps=ramp_rows,
                  validation=receipt,commands=[dict(vsl=c.vsl,green_times=c.green_times,offsets=c.offsets,
                      meters={r:c.diagnostics['rw_meter_green_'+r] for r in cfg.network.ramps})
                      for c in sequence.actions(action,3)])
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
                start_sec=state.time_sec,duration_sec=450,actual_reference_only=True,
                city_signals_held=True,limits=limits,results=results,optimizer_iterations=0,
                native_started=False,future_observation_inputs=False,
                outside_cost_scope='Only outside cohorts in sampled model stocks; not a native uninserted-vehicle audit',
                quantity_constraints='Physical/writer/inter-block checks only; NP/NUF budget selection not evaluated')
    (output/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')


def main():
    sim_sec = int(next((x.split('=',1)[1] for x in sys.argv[1:] if x.startswith('--at=')), '900'))
    if sim_sec not in (900,1050,1200):
        raise ValueError('Only the existing recorded decision times are supported')
    trace_mode = '--trace' in sys.argv[1:]
    initialize_only = '--initialize-only' in sys.argv[1:]
    gate_audit = '--gate-audit' in sys.argv[1:]
    pooled_green = '--pooled-green' in sys.argv[1:]
    warm_heads = '--warm-head-history' in sys.argv[1:]
    unique_head = '--head-turn-10633' in sys.argv[1:]
    lever_probe = '--lever-probe450' in sys.argv[1:]
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
    recorded_mode = '--recorded' in sys.argv[1:] or native_priors or canonical_prior or pooled_green or warm_heads
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
    output = HERE / name
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
        result = configure(*args, **kwargs)
        captured.update(state=result[0], cfg=args[1], tuning=args[2], mapping=args[3], raw=args[4],
                        detector=result[1], metadata=result[2])
        return result

    def capture_forecast(*args, **kwargs):
        result = forecast_fn(*args, **kwargs)
        captured['forecast'] = result
        raise Ready()

    previous = Path('D:/VISSIM_runs/20260924_sd31_gain/sdmpc31_g_gain_s29_r3/'
                    'decisions_sdmpc31_g_gain_s29_r3') / f'action_{sim_sec-150:06d}.json'
    state_path = HERE / f'selected_init{sim_sec}_final/state_{sim_sec:06d}.json'
    tuning_path = HERE / 'selected/config_n31_v2.json'
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
        from evaluation.controllers.obs150_observation import merge_into_state
        from evaluation.controllers import obs150_contract as oc
        # Recompute only observation metadata from already completed windows.
        # Actual action files/receipts and all adapter control inputs are unchanged.
        folder=previous.parent; prior=None; prototype=copy.deepcopy(cfg)
        history_dir=output/'head_history';history_dir.mkdir(exist_ok=True)
        for end in range(150,sim_sec,150):
            state_file=folder/f'state_{end:06d}.json'
            derived_file=folder/'obs150'/f'derived_{end:06d}.json'
            source=json.loads(state_file.read_bytes())
            derived=json.loads(derived_file.read_bytes())
            assert derived['window']==dict(start_s=end-150,end_s=end)
            assert end<=sim_sec-150
            historical=merge_into_state(source,derived)
            # The cached result must still refer to the captured bundle.
            assert derived['inputs']['raw_sha256']==oc.canonical_sha256(source['obs150'])
            meta=observe_heads(original,copy.deepcopy(prototype),historical,prior,caps,plan,distribute,options)
            meta['sim_sec']=end
            prior=history_dir/f'head_prior_{end:06d}.json'
            envelope=dict(run_provenance=historical['run_provenance'],metadata=meta,
                          diagnostic_observation_only=True,actual_commands_rewritten=False)
            prior.write_text(json.dumps(envelope,ensure_ascii=False,allow_nan=False),encoding='utf-8')
            history_inputs.append({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (state_file,derived_file)})
        return observe_heads(original,cfg,raw,prior,caps,plan,distribute,options)
    if warm_heads:
        head_service_resources.observe=warm_observer
    runtime_setup.configure_runtime = capture_runtime
    adapter.demand_from_state = capture_forecast
    started = time.perf_counter()
    try:
        adapter.main()
        raise AssertionError('Adapter did not reach forecast capture')
    except Ready:
        pass
    finally:
        runtime_setup.configure_runtime = configure
        adapter.demand_from_state = forecast_fn
        head_service_resources.observe=observe_heads
    initialization_sec = time.perf_counter()-started

    from src.models.state import ControlAction
    from src.controllers import rollout_endpoint as endpoint
    from evaluation.controllers import area_meter_finalization as meters
    from evaluation.controllers.sdmpc_tangent_worker import state_error
    cfg, state = captured['cfg'], captured['state']
    assert cfg.network.sdmpc_options is not None
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
        movement_capacity_veh_h={k:v for k,v in cfg.network.movement_capacity_by_movement_veh_h.items() if k.startswith('SC1004_')},
        head_resources=getattr(cfg.network,'head_service_resources',None),
        diagnostic_head_history_inputs=history_inputs,
        metadata={k:v for k,v in captured['metadata'].items() if k.startswith(('head_','movement_capacity_by_lanes','movement_capacity_perimeter','physical_unsignalized_authority'))},
        capacity_configuration=captured['tuning']['urban'].get('capacity',{}))
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
    if lever_probe:
        probe_levers(captured,action,output)
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
        assert derived['removals']['window_total']==0
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
                physical_initial_owners={p:a for p,a in state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link'].items()
                                        if a.get('storage:'+storage,0)>0},
                storage_capacity=cfg.network.urban_link_storage_veh[storage],
                greens={k:v for k,v in action.green_times.items() if 'SC1004' in k},
                offsets={k:v for k,v in action.offsets.items() if 'SC1004' in k},
                actual_head_window=[h for h in derived['head_window']['heads'] if h['sc']=='1004'],
                initial_model_observation_summary=state.local_observation_summary,
                response=response)
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
            observed_merge = observed_start+observed_arrival-observed_end
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
                predicted=dict(arrival=predicted_arrival,head=predicted_head,merge=predicted_merge,final_stock=predicted_end),
                stock_conservation_residual_veh=residual)
            sources={r['source'] for r in transfers if r['target']=='ramp:'+ramp}
            rows[ramp]['predicted_arrival_by_source']={str(source):sum(r['vehicles'] for r in transfers
                if r['target']=='ramp:'+ramp and r['source']==source) for source in sorted(sources)}
            rows[ramp]['prediction_minus_actual_veh']={k:rows[ramp]['predicted'][k]-v for k,v in rows[ramp]['actual'].items()}
        report.update(purpose='Recorded-command one-step response validation, not causal control-gain validation',
                      ramps=rows, future_target_only=True, removals=derived['removals'],
                      actual_merge_method='Initial connector stock + corrected entry crossings - final connector stock; zero removals',
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
