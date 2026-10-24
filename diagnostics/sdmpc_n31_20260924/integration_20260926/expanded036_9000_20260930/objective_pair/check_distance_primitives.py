"""Two fixed-command450 forecasts: scalar baseline vs passive travel observer.

No new native run, objective change, coefficient fit or future observation.
An incomplete distance subtotal explicitly fails whole-Omega qualification.
"""
import copy
import ctypes
import hashlib
import json
import math
from pathlib import Path
import sys
import time

from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
from evaluation.controllers import runtime_setup, obs150_contract as oc
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers import physical_ramp_branches as branches, sdmpc_sequence as sequence
from evaluation.controllers import omega_distance as distance
from evaluation.controllers.control_area_objective import get_ledger
from evaluation.controllers.lane_ramp_runtime import LaneRampRuntime
from evaluation.controllers.lane_urban_runtime import LaneUrbanRuntime
from evaluation.controllers.sdmpc_tangent_worker import state_error
from src.models.state import ControlAction
from src.controllers import rollout_endpoint as endpoint

HERE = Path(__file__).resolve().parent


def load(path): return json.loads(path.read_bytes())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    reward_check='--reward-check' in sys.argv
    local_upstream_motion = '--local-upstream-motion' in sys.argv
    cumulative_motion = '--cumulative-motion' in sys.argv or local_upstream_motion
    ordinary_audit = '--ordinary-audit' in sys.argv
    ordinary_motion = '--ordinary-motion' in sys.argv or ordinary_audit or cumulative_motion
    direct_motion = '--direct-motion' in sys.argv or ordinary_motion
    owned_motion = '--owned-motion' in sys.argv or direct_motion
    choice_motion = '--route-choice-motion' in sys.argv or owned_motion
    native_motion = '--native-motion' in sys.argv or choice_motion
    result_file = HERE/('distance_ordinary_audit_result.json' if ordinary_audit else
                       'distance_ordinary_result.json' if ordinary_motion else
                       'distance_direct_result.json' if direct_motion else
                       'distance_owned_result.json' if owned_motion else
                       'distance_route_choice_result.json' if choice_motion else
                       'distance_native_motion_result.json' if native_motion else 'distance_primitives_result.json')
    output_tag=next((x.split('=',1)[1] for x in sys.argv if x.startswith('--output-tag=')),None)
    if output_tag:
        if not output_tag.replace('_','').isalnum():raise ValueError('Invalid diagnostic tag')
        result_file=HERE/('distance_'+output_tag+'_result.json')
    if result_file.exists(): raise FileExistsError(result_file)
    kernel = ctypes.windll.kernel32
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x4000)
    folder = Path('D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
    tuning_path = probe.HERE/'baseline_reproduction_20260929/cellwise_calibration/coupled_expanded_joint/candidate_config.json'
    prior = probe.HERE/'closedloop_recorded3600_budget_check_selected_meter_e036_10681_r2'
    files = [tuning_path, folder/'state_003600.json', folder/'action_003600.json',
             Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')]
    from evaluation.controllers import native_input_routes, native_input_prehead, sdmpc_aggregate, route_choice_corridor, shared_approach, sc2001_corridor, urban_flow_accounting, lane_offramp_runtime, lane_urban_runtime, native_internal_input, lane_plant_runtime
    files += [Path(m.__file__) for m in (distance, branches, sequence, runtime_setup,
                                       native_input_routes, native_input_prehead, sdmpc_aggregate, route_choice_corridor,
                                       shared_approach, sc2001_corridor, urban_flow_accounting,
                                       lane_offramp_runtime,lane_urban_runtime,native_internal_input,lane_plant_runtime)]
    pins = {str(p): sha(p) for p in files}
    captured = {}
    configure, forecast_fn, writer = runtime_setup.configure_runtime, adapter.demand_from_state, oc.write_derived
    from evaluation.controllers import native_input_routes, native_input_prehead
    init_routes, init_prehead = native_input_routes.initialize, native_input_prehead.initialize
    init_choice = route_choice_corridor.initialize
    saved_initializers = []
    for provider,module,name in [('shared_approach',shared_approach,'initialize'),
                                 ('sc2001_corridor',sc2001_corridor,'initialize'),
                                 ('direct_exit',route_choice_corridor,'_configure_direct_transport'),
                                 ('known_legsplit',route_choice_corridor,'initialize_known_legsplit')]:
        fn = getattr(module,name)
        def wrapped(*args,_fn=fn,_provider=provider,**kwargs):
            captured[_provider+'_raw'] = args[2]
            return _fn(*args,**kwargs)
        saved_initializers.append((module,name,fn))
        setattr(module,name,wrapped)
    def capture_choice(*args, **kwargs):
        captured['choice_raw'] = args[2]
        return init_choice(*args, **kwargs)
    def capture_routes(*args, **kwargs):
        captured['route_raw'] = args[2]
        return init_routes(*args, **kwargs)
    def capture_prehead(*args, **kwargs):
        captured['prehead_raw'] = args[2]
        return init_prehead(*args, **kwargs)
    def capture(*args, **kwargs):
        result = configure(*args, **kwargs)
        captured.update(state=result[0], cfg=args[1]); return result
    def forecast(*args, **kwargs):
        result = forecast_fn(*args, **kwargs); captured['forecast'] = result; return result
    def read_only(raw, derived):
        obs = raw[oc.RAW_STATE_KEY]; p = oc.resolve(obs, oc.derived_path(obs['sim_sec']))
        assert p.read_bytes() == oc.derived_bytes(derived)
        pins[str(p)] = sha(p)
        return p
    runtime_setup.configure_runtime, adapter.demand_from_state, oc.write_derived = capture, forecast, read_only
    native_input_routes.initialize, native_input_prehead.initialize = capture_routes, capture_prehead
    route_choice_corridor.initialize = capture_choice
    try:
        sys.argv = [str(Path(probe.__file__)), '--closedloop-recorded', '--at=3600',
            '--initialize-only', '--warm-head-history', '--replay-vsl-history',
            '--recording-dir='+str(folder), '--tuning-json='+str(tuning_path),
            '--probe-label='+('distance_'+output_tag if output_tag else 'distance_ordinary_audit_v1' if ordinary_audit else
                             'distance_ordinary_v1' if ordinary_motion else
                             'distance_direct_v1' if direct_motion else
                             'distance_owned_v1' if owned_motion else
                             'distance_route_choice_v1' if choice_motion else
                             'distance_native_motion_v1' if native_motion else 'distance_primitives_v1')]
        probe.main()
    finally:
        runtime_setup.configure_runtime, adapter.demand_from_state, oc.write_derived = configure, forecast_fn, writer
        native_input_routes.initialize, native_input_prehead.initialize = init_routes, init_prehead
        route_choice_corridor.initialize = init_choice
        for module,name,fn in saved_initializers:
            setattr(module,name,fn)
    state, cfg = captured['state'], captured['cfg']
    initial = state.copy()
    reference = sequence.first_action(adapter.control_from_json(folder/'action_003600.json', cfg, ControlAction))
    saved = load(prior/'selected.json')
    commands = []
    for row in saved['commands']:
        c = branches.candidate_from_greens(reference, reference, cfg, row['meters'])
        assert c.green_times == row['green_times'] and c.offsets == row['offsets'] and c.vsl == row['vsl']
        commands.append(c)
    action = sequence.pack(commands)
    def predict():
        start = time.perf_counter()
        with sequence.prediction_scope(action, cfg, state.time_sec, 3) as visits:
            point = endpoint.evaluate_price_point(state, action, captured['forecast'][:3], (),
                endpoint.ObjectiveSpec(cfg, depth_override=3, box_walk=False, score_mode='raw'), capture_response=True)
        assert visits == [0, 1, 2] and not point.aborted
        return point, time.perf_counter()-start
    baseline, base_wall = predict()
    assert abs(baseline.ttt-saved['execution']['ttt_omega_veh_h']) < 1e-7
    print(json.dumps(dict(stage='baseline_complete', ttt=baseline.ttt, seconds=base_wall)), flush=True)
    if reward_check:
        return check_reward(captured,state,cfg,action,baseline,base_wall,result_file,pins)

    parts, missing, times, port_modes = {}, {}, [], {}
    ramp_advance, urban_advance = LaneRampRuntime.advance, LaneUrbanRuntime.advance
    membership = state.lane_offramp_runtime.membership
    seeded = {}
    if native_motion:
        state._omega_travel_reservations = distance.TravelReservations(3600.,4050.,membership)
        if ordinary_motion:
            network=probe.HERE/'selected/network/native_seed29.inpx'
            pins[str(network)]=sha(network)
            state._omega_travel_reservations.ordinary_catalog=distance.urban_path_catalog(network,cfg)
        seeded['native_input_routes'] = distance.seed_native_routes(state,cfg,captured['route_raw'])
        seeded['native_input_prehead'] = distance.seed_native_prehead(state,cfg,captured['prehead_raw'])
        if choice_motion:
            seeded['route_choice_corridor'] = distance.seed_route_choice(state,cfg,captured['choice_raw'])
        if owned_motion:
            for provider in ('shared_approach','sc2001_corridor','known_legsplit'):
                seeded[provider] = distance.seed_owned_reservations(state,cfg,captured[provider+'_raw'],provider)
        if direct_motion:
            seeded['direct_exit'] = distance.seed_direct(state,cfg,captured['direct_exit_raw'])
        if local_upstream_motion:
            seeded['local_upstream']=distance.seed_local_upstream(state,cfg)
    covered = {'freeway:'+r for r in cfg.network.freeway_links}
    covered |= {'origin:'+r for r in cfg.network.freeway_links}  # outside; zero distance
    covered |= {'ramp:'+r for r in cfg.network.ramps}
    covered |= {'storage:'+row['storage'] for off, row in state.lane_offramp_runtime.descriptions.items() if off != '10643'}
    covered |= {'storage:'+v for k,v in state.lane_urban_runtime.local_storage.items() if k != 10700}
    if choice_motion:
        covered |= {'storage:'+key for key in cfg.network.route_choice_corridor['capacity_veh']}
    if owned_motion:
        covered |= {'storage:'+s['storage'] for s in (cfg.network.shared_approach,
                    cfg.network.sc2001_corridor,cfg.network.known_legsplit_routes)}
    if direct_motion:
        covered.add('storage:'+cfg.network.direct_exit_legsplit['storage'])
        covered.add('transit:gate:'+cfg.network.physical_gate_travel['source'])
    if local_upstream_motion:
        covered.add('storage:'+state.lane_urban_runtime.origin)
    def add(rows):
        for stock, value in rows.items():
            if not math.isfinite(value) or value < 0: raise ValueError('Invalid distance: '+stock)
            parts[stock] = parts.get(stock, 0.)+value
    def before_ramp(self, s, control, demand, freeway, *, service):
        start = s.time_sec
        if times and start != times[-1]+1: raise ValueError('Missing/double distance interval')
        times.append(start)
        add(distance.freeway_distance(s, cfg, 1.))
        add({'ramp:'+name: distance.ramp_distance(p, start, start+1., membership)
             for name,p in self.buffers.items()})
        runtime = s.lane_offramp_runtime
        for off, p in runtime.ports.items():
            row = runtime.descriptions[off]
            port_modes[off] = p.entry_accel_mps2
            add({'storage:'+row['storage']: distance.delayed_port_distance(p, row['connector'], start, start+1., membership)})
        for stock, cohorts in get_ledger(s).stocks.items():
            if stock not in covered and cohorts['inside'] > 0:
                missing[stock] = max(missing.get(stock, 0.), cohorts['inside'])
        return ramp_advance(self, s, control, demand, freeway, service=service)
    def after_urban(self, *args, **kwargs):
        result = urban_advance(self, *args, **kwargs)
        add(distance.local_cell_distance(self.port.urban, membership))
        return result
    LaneRampRuntime.advance, LaneUrbanRuntime.advance = before_ramp, after_urban
    ordinary_original=distance.record_ordinary_movement
    ordinary_errors={}
    def audit_ordinary(s,cfg,m,n,step,due):
        try:
            return ordinary_original(s,cfg,m,n,step,due)
        except distance.DistanceCoverageError as error:
            row=ordinary_errors.setdefault(m,dict(error=str(error),vehicles=0.,first_step=step,calls=0))
            row['vehicles']+=n;row['calls']+=1
    if ordinary_audit:
        distance.record_ordinary_movement=audit_ordinary
    try:
        observed, observed_wall = predict()
    finally:
        LaneRampRuntime.advance, LaneUrbanRuntime.advance = ramp_advance, urban_advance
        distance.record_ordinary_movement=ordinary_original
    assert times == list(range(3600, 4050))
    assert observed.ttt == baseline.ttt and observed.objective == baseline.objective
    assert observed.control_area_response == baseline.control_area_response
    native_receipt = None
    if native_motion:
        final = observed.states[-1]._omega_travel_reservations
        native_receipt = dict(initial_reservations=seeded,
            counts=final.reservation_counts,
            distance_by_provider_stock_veh_km={provider+'|'+stock:value
                for (provider,stock),value in final.by_provider_stock.items()},
            geometry_bounds_by_provider_stock={provider+'|'+stock:value
                for (provider,stock),value in final.geometry_bounds_by_stock.items()},
            aggregate_predictor=cfg.network.sdmpc_options.get('aggregate_predictor'),
            scope='Named route cohorts and explicitly covered private stores; native tagged subsets do not cover entire shared storage')
        for (provider,stock),value in final.by_provider_stock.items(): add({stock:value})
        # Compare ALL original state fields, excluding only the new passive
        # observer itself, whose accounting is tested separately.
        for predicted in observed.states:
            del predicted._omega_travel_reservations
        del state._omega_travel_reservations
    max_state_error = state_error(baseline.states, observed.states)
    initial_error = state_error(initial, state)
    assert max_state_error == initial_error == 0.
    cumulative_receipt=None
    if cumulative_motion:
        local=observed.states[-1].lane_urban_runtime
        lanes=[('10643',local.off_storage,p) for p in local.port.lanes]
        if local.side_port is not None:lanes.append(('10700',local.local_storage[10700],local.side_port))
        cumulative_receipt=[]
        for link,stock,lane in lanes:
            before=copy.deepcopy(vars(lane))
            coarse=distance.cumulative_lane_distance(lane,3600.,4050.,link,membership)
            fine=distance.cumulative_lane_distance(lane,3600.,4050.,link,membership,spatial_step_m=1.)
            assert vars(lane).keys()==before.keys()
            assert lane.departure_history==before['departure_history'] and lane.arrivals==before['arrivals']
            cumulative_receipt.append(dict(link=link,stock=stock,distance_veh_km=coarse,
                refined_veh_km=fine,quadrature_difference_veh_km=coarse-fine,
                initial=lane.initial,admitted=lane.admitted,departed=lane.departed,terminal_stock=lane.stock))
            add({'storage:'+stock:coarse})
    receipt = dict(scope='full_control_area_omega', coverage_complete=False,
        covered_subtotal_veh_km=math.fsum(parts.values()), distance_by_stock_veh_km=parts,
        unresolved_positive_stocks=missing,
        unresolved_transport=['ordinary urban storage/queue motion', 'native gate and direct-exit routes',
                              '10643 and10700 cumulative interior motion'])
    try:
        distance.require_complete_coverage(receipt)
    except distance.DistanceCoverageError:
        incomplete_rejected = True
    else: raise AssertionError('Partial subtotal was incorrectly accepted as full Omega')
    for p,h in pins.items(): assert sha(Path(p)) == h
    result = dict(stage='primitive_validation_complete_full_omega_pending', receipt=receipt,
        ttt_omega_veh_h=baseline.ttt, objective_veh_h=baseline.objective,
        scalar_response_and_trajectory_exact=True, max_state_error=max_state_error,
        initial_state_error=initial_error, full_omega_scoring_rejected=incomplete_rejected,
        baseline_seconds=base_wall, observed_seconds=observed_wall, observed_intervals=len(times),
        delayed_port_acceleration_modes=port_modes, pins=pins, new_native_runs=0,
        native_motion=native_receipt,
        cumulative_motion=cumulative_receipt,
        ordinary_unresolved_accepted_movements=ordinary_errors,
        fixed_command_rollouts=2, optimizer_iterations=0, objective_modified=False,
        definition='Mainline left-state N*v, exact fixed-speed ramp/port travel; localCTM left-edge finite-volume displacement. Incomplete coverage, not a fullOmega TVD result.')
    result_file.write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps(dict(stage=result['stage'], subtotal=receipt['covered_subtotal_veh_km'],
                         uncovered_positive_stocks=len(missing), exact=True)), flush=True)


def check_reward(captured,state,cfg,anchor,baseline,base_wall,result_file,pins):
    """Three physical candidates; provisional beta for offline diagnostics only."""
    from evaluation.controllers.sdmpc import omega_costs
    spec=dict(schema=distance.REWARD_SCHEMA,weight_h_per_km=1/110,
              initial_transport=distance.COMMON_INITIAL)
    distance.configure_reward({'adapter':{'sdmpc_distance_reward':spec}},cfg)
    prior=load(HERE/'distance_boundary_gate_v2_result.json')
    seeded=state.copy();seeded._omega_travel_reservations=distance.TravelReservations(3600.,4050.,state.lane_offramp_runtime.membership)
    seeded._omega_travel_reservations.ordinary_catalog=cfg.network.sdmpc_distance_catalog
    distance.seed_native_routes(seeded,cfg,captured['route_raw'])
    distance.seed_native_prehead(seeded,cfg,captured['prehead_raw'])
    distance.seed_route_choice(seeded,cfg,captured['choice_raw'])
    for provider in ('shared_approach','sc2001_corridor','known_legsplit'):
        distance.seed_owned_reservations(seeded,cfg,captured[provider+'_raw'],provider)
    distance.seed_direct(seeded,cfg,captured['direct_exit_raw'])
    distance.seed_local_upstream(seeded,cfg)
    known_initial=math.fsum(seeded._omega_travel_reservations.by_provider_stock.values())
    controls=sequence.actions(anchor,3)
    candidates={'held':anchor}
    previous=controls[0];changed=[]
    for k,g in enumerate((8.,6.,4.)):
        greens={r:controls[k].diagnostics['rw_meter_green_'+r] for r in cfg.network.ramps};greens['RM_C10681']=g
        c=branches.candidate_from_greens(controls[k],previous,cfg,greens);changed.append(c);previous=c
    candidates['rm10681_8_6_4']=sequence.pack(changed)
    changed=[c.copy() for c in controls]
    for c in changed:
        for cell,head in enumerate(cfg.network.freeway_vsl_zone_head_of_cell['FW_E']):
            if head==13:c.vsl['FW_E__seg'+str(cell)]=100.
        c.vsl['FW_E']=100.
    candidates['vsl100']=sequence.pack(changed)
    results={}
    for name,action in candidates.items():
        start=time.perf_counter()
        with sequence.prediction_scope(action,cfg,state.time_sec,3) as visits:
            point=endpoint.evaluate_price_point(state,action,captured['forecast'][:3],(),
                endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
        assert visits==[0,1,2] and not point.aborted
        local,partition=omega_costs(point,cfg)
        receipt=point.control_area['distance_reward']
        if name=='held':
            assert point.ttt==baseline.ttt and point.control_area_response==baseline.control_area_response
            assert abs(receipt['shifted_tvd_veh_km']+known_initial-prior['receipt']['covered_subtotal_veh_km'])<1e-7
            for s in point.states:del s._omega_travel_reservations
            assert state_error(baseline.states,point.states)==0
        row=dict(ttt_omega_veh_h=point.ttt,selection_score_veh_h=point.objective,
            distance=receipt,partition=partition,seconds=time.perf_counter()-start)
        results[name]=row
        path=result_file.with_name(result_file.stem+'_'+name+'.json');assert not path.exists()
        path.write_text(json.dumps(row,indent=2,allow_nan=False),encoding='utf8')
        print(json.dumps(dict(case=name,ttt=point.ttt,shifted_distance=receipt['shifted_tvd_veh_km'],score=point.objective)),flush=True)
    for p,h in pins.items():assert sha(Path(p))==h,p
    result=dict(stage='full_area_distance_difference_scalar_check',results=results,
        known_initial_distance_veh_km=known_initial,known_initial_primitives_reused_exactly=True,
        held_on_off_all_original_states_flows_ttt_exact=True,physical_rollouts=4,
        reward_spec=spec,weight_is_offline_diagnostic_only=True,native_runs=0,optimizer_iterations=0,
        absolute_model_distance_available=False,
        pending='Independent state, actual AD worker and writer-final-score verification before operational use.')
    result_file.write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf8')


def check_selected_components():
    """Three fixed physical forecasts, selected city unchanged; no new solver."""
    kernel=ctypes.windll.kernel32
    kernel.GetCurrentProcess.restype=ctypes.c_void_p
    kernel.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    tag=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--output-tag=')),'v1')
    if not tag.replace('_','').isalnum():raise ValueError('Invalid diagnostic tag')
    result_file=HERE/('distance_components_'+tag+'.json')
    if result_file.exists():raise FileExistsError(result_file)
    selected_dir=probe.HERE/'closedloop_recorded2700_select_distance_s47_v1'
    previous_physical=probe.HERE/'closedloop_recorded2700_select_check_distance_s47_v1/summary.json'
    tuning=HERE/'distance_diagnostic_config.json'
    pins={str(p):sha(p) for p in (previous_physical,tuning,selected_dir/'unused_action.json',
        selected_dir/'unused_action.joint_written.json',Path(__file__),Path(distance.__file__),
        Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP'))}
    original=probe.probe_levers
    def evaluate(captured,reference,output,*,selected_path,**kwargs):
        from evaluation.controllers import signal_actuation_contract as signals
        from evaluation.controllers.sdmpc import omega_costs
        state,cfg=captured['state'],captured['cfg']
        assert state.time_sec==2700 and selected_path.resolve()==(selected_dir/'unused_action.json').resolve()
        selected=sequence.actions(adapter.control_from_json(selected_path,cfg,ControlAction),3)
        reference=sequence.first_action(reference)
        old=load(previous_physical);held=old['results']['held_actual'];both=old['results']['selected']
        for row in held['commands']:
            assert row['green_times']==reference.green_times and row['offsets']==reference.offsets and row['vsl']==reference.vsl
            assert row['meters']=={r:reference.diagnostics['rw_meter_green_'+r] for r in cfg.network.ramps}
        for c,row in zip(selected,both['commands']):
            assert c.green_times==row['green_times'] and c.offsets==row['offsets'] and c.vsl==row['vsl']
        token=distance.reward_token(cfg.network.sdmpc_distance_reward)
        assert both['control_area']['distance_reward']['specification_sha256']==token
        results={'city_plus_both':both}
        for name,use_rm,use_vsl in [('city_only',False,False),('city_plus_rm',True,False),('city_plus_vsl',False,True)]:
            commands=[];previous=reference
            for block,s in enumerate(selected):
                c=s.copy();c.vsl=dict(s.vsl if use_vsl else reference.vsl)
                rates=s if use_rm else reference
                greens={r:rates.diagnostics['rw_meter_green_'+r] for r in cfg.network.ramps}
                c=branches.candidate_from_greens(c,previous,cfg,greens)
                signals.validate_control(c,cfg)
                assert c.green_times==s.green_times and c.offsets==s.offsets
                assert c.vsl['FW_E__seg0']==c.vsl['FW_W__seg0']==110.
                assert all(v in cfg.freeway_follower.vsl_set for v in c.vsl.values())
                assert all(abs(c.vsl[k]-previous.vsl[k])<=cfg.freeway_follower.max_vsl_step for k in c.vsl)
                commands.append(c);previous=c
            action=sequence.pack(commands);start=time.perf_counter()
            with sequence.prediction_scope(action,cfg,state.time_sec,3) as visits:
                point=endpoint.evaluate_price_point(state,action,captured['forecast'][:3],(),
                    endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
            assert visits==[0,1,2] and not point.aborted
            _,partition=omega_costs(point,cfg)
            costs={};outside=0.
            for row in point.control_area_response['residence']:
                for stock,n in row['inside_veh'].items():
                    costs[stock]=costs.get(stock,0.)+n*row['dt_h']
                    out=row['model_stock_veh'][stock]-n;assert out>=-1e-7
                    outside+=max(0.,out)*row['dt_h']
            assert abs(sum(costs.values())-point.ttt)<1e-7
            ramps={}
            for ramp in cfg.network.ramps:
                flow=point.control_area['predicted_ramp_merge']['rate_veh_h_by_ramp'][ramp]/8.
                arrival=sum(t['vehicles'] for t in point.control_area_response['transfers'] if t['target']=='ramp:'+ramp)
                end=point.states[-1].ramp_queue[ramp]
                residual=state.ramp_queue[ramp]+arrival-flow-end;assert abs(residual)<1e-7
                ramps[ramp]=dict(arrival=arrival,merge=flow,final_stock=end,residual=residual)
            value=dict(ttt_omega_veh_h=point.ttt,tracked_outside_residence_veh_h=outside,
                ttt_with_tracked_outside_veh_h=point.ttt+outside,control_area=point.control_area,
                cost_by_stock=costs,ramps=ramps,partition=partition,seconds=time.perf_counter()-start,
                commands=[dict(green_times=c.green_times,offsets=c.offsets,vsl=c.vsl,
                    meters={r:c.diagnostics['rw_meter_green_'+r] for r in cfg.network.ramps}) for c in commands])
            results[name]=value
            case=result_file.with_name(result_file.stem+'_'+name+'.json');assert not case.exists()
            case.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf8')
            print(json.dumps(dict(case=name,ttt=point.ttt,outside=outside,score=point.objective)),flush=True)
        for p,h in pins.items():assert sha(Path(p))==h,p
        result=dict(results=results,pins=pins,initial_time=state.time_sec,city_commands_fixed=True,
            interpretation='Incremental changes around existing active RM, not all meters open vs ALINEA.',
            new_physical_forecasts=3,reused_selected_forecasts=1,optimizer_iterations=0,new_native_runs=0,
            future_observation_inputs=False,weight_diagnostic_only=True,
            quantity_caps_certified=False)
        result_file.write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf8')
    probe.probe_levers=evaluate
    try:
        sys.argv=[str(Path(probe.__file__)),'--closedloop-recorded','--at=2700','--selection-check',
            '--warm-head-history','--replay-vsl-history',
            '--recording-dir=D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47',
            '--fixed-replay-summary='+str(probe.HERE/'native_rm_observation2700_writerfix_v3/analysis/summary.json'),
            '--tuning-json='+str(tuning),'--selection-reference='+str(selected_dir),
            '--probe-label=distance_parts47_'+tag]
        probe.main()
    finally:probe.probe_levers=original


if __name__ == '__main__':
    check_selected_components() if '--selected-components' in sys.argv else main()
