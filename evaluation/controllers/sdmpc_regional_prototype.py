"""Experimental cut-boundary regional predictor; not a production controller.

Connector entrance is the interface: onramps belong to freeway, offramps to
urban. The last closed detector window supplies a constant arrival *request*,
never a receiving capacity. Downstream outlets use an explicitly open boundary.
Unadmitted requests remain in a counted external arrival backlog.
"""
from __future__ import annotations

import copy
import math
from types import SimpleNamespace


FREEWAY_FIELDS = frozenset((
    'freeway_density', 'freeway_speed', 'freeway_flow', 'freeway_effective_lanes',
    'mainline_origin_queue', 'ramp_queue', 'lane_freeway_runtime',
    'lane_ramp_runtime', 'offramp_route_inventory_state', '_component_vsl_exposure',
))
URBAN_FIELDS = frozenset((
    'urban_queue', 'boundary_queue', 'urban_movement_queue', 'urban_link_storage',
    'urban_link_speed_kph', 'urban_arrival_buffer', 'urban_storage_release_buffer',
    'urban_inflow_transit_buffer', 'offramp_transit_buffer', 'gate_initial_route_tags',
    'gate_future_route_tags', 'gate_future_accounting', 'shared_approach_state',
    'sc2001_corridor_state', 'route_choice_corridor_state', 'native_internal_input_state',
    'native_input_route_state', 'native_input_prehead_state', 'lane_urban_runtime',
    'lane_offramp_runtime', 'sc1001_approach', 'known_legsplit_route_state',
    'direct_exit_route_state', '_sc10_north325',
))


def owns_stock(mode, stock):
    freeway = stock.startswith(('freeway:', 'origin:', 'ramp:', 'merge_pending:'))
    return freeway if mode == 'freeway_only' else not freeway


def boundary_requests(derived, mode, now, ramps, offramps):
    """Only the last closed entrance counts leave the collector boundary."""
    window = derived['window']
    start, end = window['start_s'], window['end_s']
    if end != now or not 0 < end-start <= 150:
        raise ValueError('Regional boundary requires the closed current/past window')
    role, names = ('ramp_arrival', ramps) if mode == 'freeway_only' else ('off_entry', offramps)
    result = {}
    for name in names:
        ref = role+':'+name
        row = derived['boundaries'][ref]
        if row['role'] != role or row['boundary_ref'] != ref or not row['lane_exact']:
            raise ValueError('Regional inlet lacks exact entrance crossing evidence')
        counts = [float(r['cross']) for r in row['lanes']]
        if (any(not math.isfinite(n) or n < 0 for n in counts)
                or abs(sum(counts)-row['cross']) > 1e-9):
            raise ValueError('Invalid regional crossing count')
        result[name] = dict(rate_veh_h=float(row['cross'])*3600/(end-start),
                            lane_rates_veh_h=[n*3600/(end-start) for n in counts])
    return dict(mode=mode, start_sec=start, end_sec=end, inlets=result,
                forecast='last closed entrance crossing rate, frozen for horizon',
                outlet='open boundary; downstream storage/spillback unobserved',
                measured_flow_is_capacity=False)


def project_state(original, cfg, mode, boundary):
    from src.models.state import TrafficState
    from evaluation.controllers.control_area_objective import ModelAreaLedger
    from evaluation.controllers.area_runtime import model_inventory
    if mode not in ('freeway_only', 'urban_only') or boundary['mode'] != mode:
        raise ValueError('Unknown regional mode')
    if boundary['end_sec'] != original.time_sec:
        raise ValueError('Stale regional boundary observation')
    net = cfg.network
    state = TrafficState(freeway_density={}, freeway_speed={}, freeway_flow={},
                         ramp_queue={}, urban_queue={}, boundary_queue={}, time_sec=original.time_sec)
    # Shape-only shells permit unchanged component APIs; no remote observations
    # or remote runtime objects are copied into these shells.
    for key in ('freeway_density', 'freeway_flow'):
        setattr(state, key, {r:[0.]*len(net.freeway_segment_length_profile_km[r]) for r in net.freeway_links})
    state.freeway_speed = {r:[net.v_free]*len(v) for r,v in state.freeway_density.items()}
    state.freeway_effective_lanes = copy.deepcopy(net.freeway_segment_lanes)
    state.mainline_origin_queue = dict.fromkeys(net.freeway_links, 0.)
    state.ramp_queue = dict.fromkeys(net.ramps, 0.)
    state.urban_queue = dict.fromkeys(net.movement_links, 0.)
    state.boundary_queue = dict.fromkeys(net.movement_links, 0.)
    state.urban_movement_queue = dict.fromkeys(net.urban_movements, 0.)
    state.urban_link_storage = dict(net.urban_link_storage_veh)
    allowed = FREEWAY_FIELDS if mode == 'freeway_only' else URBAN_FIELDS
    owned = copy.deepcopy({name:getattr(original,name) for name in allowed if hasattr(original,name)})
    for name,value in owned.items():
        setattr(state,name,value)
    if mode == 'freeway_only':
        for name,row in boundary['inlets'].items():
            buffer=state.lane_ramp_runtime.buffers[name]
            rates=row['lane_rates_veh_h']
            if len(rates)!=buffer.lanes:
                raise ValueError('Boundary lanes differ from owned physical ramp lanes')
            total=sum(rates)
            # No current crossing means no new request. Uniform is a static,
            # causal zero-count convention, never an inherited urban offer.
            buffer.lane_arrival_shares=tuple(q/total for q in rates) if total else tuple([1./buffer.lanes]*buffer.lanes)
    if mode == 'urban_only':
        state.lane_ramp_runtime = OpenRampOutlet(original.lane_ramp_runtime, cfg)
        state.local_observation_summary = {'urban_link_speed_kph': copy.deepcopy(original.local_observation_summary['urban_link_speed_kph'])}
    state.regional_boundary = copy.deepcopy(boundary)
    state.regional_arrival_backlog = dict.fromkeys(boundary['inlets'], 0.)
    inventory = model_inventory(state, cfg)
    old = original._control_area_ledger.stocks
    cohorts = {}
    for key, amount in inventory.items():
        if owns_stock(mode,key):
            cohorts[key] = copy.deepcopy(old.get(key, {'inside':0., 'outside':0.}))
        else:
            if abs(amount)>1e-8:
                raise ValueError('Remote stock survived projection: '+key)
            cohorts[key] = dict(inside=0., outside=0.)
    state._control_area_ledger = ModelAreaLedger(cohorts)
    state._control_area_ledger.assert_stocks(inventory)
    return state


class OpenRampLane:
    """No remote inventory: static outlet offer, consumed by the urban allocator."""
    def __init__(self, offer):
        self.offer = offer

    def current_admission_space(self):
        return self.offer

    def snapshot(self):
        return dict(connector_veh=0., upstream_travelling_veh=0., head_ready_veh=0.,
                    outside_component_backlog_veh=0.)


class OpenRampBuffer(OpenRampLane):
    def __init__(self, physical, offer):
        super().__init__(offer)
        # Only surveyed geometry is retained. No speed, cohort, queue, service
        # history or receiving-wave state from the freeway connector is read.
        self.lanes=physical.lanes
        self.head_position_m=physical.head_position_m
        self.spacing_m=physical.spacing_m
        self.lane_arrival_shares=tuple([1./self.lanes]*self.lanes)
        self._lane_buffers=[OpenRampLane(offer/self.lanes) for _ in range(self.lanes)]


class OpenRampOutlet:
    def __init__(self, physical, cfg):
        self.buffers={r:OpenRampBuffer(b,cfg.network.ramp_capacity_veh_h[r]*cfg.simulation.T_u_h)
                      for r,b in physical.buffers.items()}

    def receiving_space(self, state, name):
        return max(0.,self.buffers[name].offer-state.ramp_queue[name])


def plan_coverage(ledger,start,duration,scopes,offramps,mode):
    """Declare only the allocators actually present in this regional plant."""
    if not ledger.captures_response:return
    previous=ledger._response_clock
    for sec in range(int(start),int(start+duration),10):
        if mode=='urban_only':
            ledger.begin_response_step('urban',sec,sec+10)
            for scope in scopes:ledger.expect_constraint_coverage(scope)
            ledger.begin_response_step('landing',sec,sec+10)
            for scope in ('offramp_landing',*('offramp_landing:'+r for r in offramps)):
                ledger.expect_constraint_coverage(scope)
        else:
            for t in (sec,sec+5):
                ledger.begin_response_step('freeway',t,t+5)
                for scope in ('physical_ramp_release','freeway_allocator'):
                    ledger.expect_constraint_coverage(scope)
    ledger._response_clock=previous
    ledger._response['constraint_intervals'].append(dict(start_sec=start,end_sec=start+duration,
        T_u_sec=10.,T_f_sec=5.,exchange='regional-cut10',region=mode))


def urban_interval(state, control, demand, cfg):
    from evaluation.controllers import area_freeway_accounting as accounting
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import emit_transfer
    ledger=state._control_area_ledger;ports=state.lane_offramp_runtime
    start=state.time_sec
    scopes=['urban_allocator','lane_urban_allocator','physical_offramp_drain']
    scopes.extend(k for k in ('shared_approach','sc2001_corridor') if getattr(cfg.network,k,None))
    if getattr(cfg.network,'leg_ramp_split_enabled',False) and getattr(cfg.network,'boundary_out_ramp_split',None):
        scopes.append('legsplit_allocator')
    if getattr(cfg.network,'route_choice_corridor',None):scopes.append('route_choice_allocator')
    if getattr(cfg.network,'native_internal_inputs',None):
        scopes.extend(('native_route_queue','native_prehead_queue','native_input_generation','native_prehead_residual'))
    plan_coverage(ledger,start,cfg.simulation.T_c_sec,scopes,tuple(ports.descriptions),'urban_only')
    for sec in range(int(start),int(start+cfg.simulation.T_c_sec),10):
        state.time_sec=sec
        ledger.begin_response_step('urban',sec,sec+10)
        accounting._cp.urban_substep(state,control,demand,cfg,urban_step_index=sec//10,ramp_release_veh_h={})
        for name,n in state.ramp_queue.items():
            emit_transfer(state,cfg,'ramp:'+name,None,n,target_inside=False)
            state.ramp_queue[name]=0.
        ledger.assert_stocks(model_inventory(state,cfg))
        caps,groups=ports.capacities(state,cfg,duration_sec=10)
        flows={};lane_counts=[]
        for off,row in state.regional_boundary['inlets'].items():
            offered=state.regional_arrival_backlog[off]+row['rate_veh_h']/360.
            accepted=min(offered,caps[off]/360.)
            if off=='10643':
                total=sum(row['lane_rates_veh_h'])
                shares=[q/total for q in row['lane_rates_veh_h']] if total else [0.5,0.5]
                accepted=min([accepted]+[groups[off][j]/360./share for j,share in enumerate(shares) if share])
                lane_counts=[accepted*share for share in shares]
            flows[off]=accepted*360.
            state.regional_arrival_backlog[off]=offered-accepted
        # Incoming route labels are unobserved; use the existing unrouted
        # branch law explicitly, retaining all tags on already owned vehicles.
        routes={row['road']:dict(end_sec=sec+10,ports={}) for row in ports.descriptions.values()}
        for off,row in ports.descriptions.items():
            routes[row['road']]['ports'][off]={'boundary|unrouted|'+off:flows[off]/360.}
        ledger.begin_response_step('landing',sec,sec+10)
        ports.land(state,cfg,sec+10,flows,{'10643':lane_counts},duration_sec=10,
                   source_owners=dict.fromkeys(flows),route_receipts=routes)
        ledger.assert_stocks(model_inventory(state,cfg))
        ledger.begin_response_step('urban',sec,sec+10)
        ledger.residence(tuple(k for k in ledger.stocks if owns_stock('urban_only',k)),10./3600.)
    state.time_sec=start+cfg.simulation.T_c_sec


def freeway_interval(state, control, demand, cfg):
    """Existing ramp and METANET components, without any urban step/predictor."""
    from evaluation.controllers import sdmpc_continuous
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import emit_transfer
    from evaluation.controllers.multirate_coupling import (
        prepare_ramp_admission_windows, ramp_admission_windows)
    fw, ramps, ledger = state.lane_freeway_runtime, state.lane_ramp_runtime, state._control_area_ledger
    start = state.time_sec
    services = sdmpc_continuous.ramp_services(control,cfg,ramps.cycle_sec)
    # Fixed static open-outlet approximation. No urban queue, speed, measured
    # discharge history, receiving stock or future service is queried.
    caps = {off:cfg.network.freeway_capacity_veh_h for off in fw.offramps}
    plan_coverage(ledger,start,cfg.simulation.T_c_sec,(),(),'freeway_only')
    for sec in range(int(start),int(start+cfg.simulation.T_c_sec),5):
        if (sec-start)%10==0:
            admission_windows=prepare_ramp_admission_windows(ramps,sec)
        state.time_sec=sec
        ledger.begin_response_step('freeway',sec,sec+5)
        release,groups,_=ramps.advance(state,control,demand,fw,service=services)
        ledger._response.setdefault('regional_merge_frames',[]).append(dict(
            start_sec=sec,end_sec=sec+5,actual_ramp_release_veh_h=copy.deepcopy(release)))
        ledger.complete_constraint_coverage('physical_ramp_release')
        ramps.finish(state)
        _,flows,_=fw.advance_macro(state,control,demand,ramp_releases=release,
            off_capacities=caps,ramp_group_releases=groups,
            off_group_capacities={'10643':[caps['10643']/2,caps['10643']/2,0.]})
        for off,rate in flows.items():
            emit_transfer(state,cfg,'freeway:'+fw.offramps[off]['road'],None,
                          rate/720.,target_inside=False)
        if (sec-start)%10==5:
            with ramp_admission_windows(admission_windows):
                for name,row in state.regional_boundary['inlets'].items():
                    offered=state.regional_arrival_backlog[name]+row['rate_veh_h']/360.
                    room=ramps.receiving_space(state,name)
                    admitted=min(offered,room)
                    state.regional_arrival_backlog[name]=offered-admitted
                    state.ramp_queue[name]+=admitted
                    ramps.buffers[name].admit_current(admitted)
                    emit_transfer(state,cfg,None,'ramp:'+name,admitted,source_inside=True,target_inside=True)
                    ledger.record_resource_allocation('regional_ramp_inlet',name,room,{name:admitted})
        ramps.assert_mirror(state)
        ledger.assert_stocks(model_inventory(state,cfg))
        if (sec-start)%10==5:
            ledger.begin_response_step('urban',sec-5,sec+5)
            ledger.residence(tuple(k for k in ledger.stocks if owns_stock('freeway_only',k)),10./3600.)
    state.time_sec=start+cfg.simulation.T_c_sec


def predict(state, cfg, forecast, action):
    """Prototype scalar/AD endpoint. No optimizer or production dispatch yet."""
    from evaluation.controllers.control_area_objective import ModelAreaLedger
    from evaluation.controllers.sdmpc_sequence import actions
    mode=state.regional_boundary['mode']
    candidate=copy.deepcopy(state)
    candidate._control_area_ledger=ModelAreaLedger(copy.deepcopy(state._control_area_ledger.stocks),
        capture_response=True,indexed_coverage=True,primal_audit=True)
    states=[]
    for control,demand in zip(actions(action,3),forecast):
        step=freeway_interval if mode=='freeway_only' else urban_interval
        # Regional native entry forecasts only. Cross-region requests are the
        # separate immutable boundary record, never remote demand forecasts.
        demand=copy.deepcopy(demand)
        if mode=='freeway_only':
            demand.urban_boundary=dict.fromkeys(demand.urban_boundary,0.)
        else:
            demand.freeway_mainline=dict.fromkeys(demand.freeway_mainline,0.)
            demand.freeway_lane_loss={};demand.incident_capacity_factor=1.
        demand.ramp_arrival=dict.fromkeys(demand.ramp_arrival,0.)
        step(candidate,control,demand,cfg)
        states.append(candidate.copy())
    ledger=candidate._control_area_ledger
    response=ledger.response()
    coverage=response['constraint_coverage']
    intervals=response['constraint_intervals']
    complete=(len(intervals)==3 and all(r.get('region')==mode for r in intervals)
              and bool(coverage) and all(r['expected'] and r['completed'] and not r['missing_constraints'] for r in coverage))
    response['schema']='regional-control-area-response/v1'
    response['model_constraint_coverage']=dict(schema='regional-model-constraint-coverage/v1',
        region=mode,complete=complete,schedule_complete=complete,
        expected_visits=sum(r['expected'] for r in coverage),
        completed_visits=sum(r['completed'] for r in coverage),
        conditional_model_feasibility_witness=complete,
        claim_scope='Owned-region original allocation/state checks and finite boundary admission; no remote prediction or native certificate',
        remote_frames_required=False,missing_constraints=sorted({k for r in coverage for k in r['missing_constraints']}))
    response['conditional_model_feasibility_witness']=complete
    area=dict(ttt_veh_h=ledger.ttt_veh_h,ttd_veh=ledger.ttd_veh,entered_veh=ledger.entered_veh,
        beta_seconds=0.,near_score_veh_h=ledger.ttt_veh_h,additional_cost_veh_h=0.,
        event_count=ledger.event_count,flow_counts=dict(ledger.flow_counts),region=mode,
        prediction_approximation='Cut-boundary adopted interior dynamics; frozen last-window inlet request and static open outlet',
        far_disabled=True,legacy_partial_ttt_pruning_disabled=True)
    return SimpleNamespace(objective=ledger.ttt_veh_h,ttt=ledger.ttt_veh_h,states=states,ledger=ledger,
        control_area=area,control_area_response=response,aborted=False,
        rejected_arrival_backlog=copy.deepcopy(candidate.regional_arrival_backlog))


def quantities(point, state, cfg):
    """Own accepted service only; the absent resource is explicitly inactive."""
    mode=state.regional_boundary['mode'];end=point.states[-1].time_sec
    response=point.control_area_response
    if not response['model_constraint_coverage']['complete']:
        raise ValueError('Incomplete regional allocation coverage')
    owners={};rates={};vehicles={}
    if mode=='urban_only':
        cursor=state.time_sec
        for sample in (r for r in response['residence'] if r['stage']=='urban'):
            if (sample['start_sec']!=cursor or sample['end_sec']!=cursor+10
                    or sample['dt_h']!=10./3600.):
                raise ValueError('Missing local urban residence frame')
            cursor=sample['end_sec']
        if cursor!=end:raise ValueError('Incomplete local urban quantity horizon')
        owners={s:dict(net_inflow_veh=0., accepted_event_count=0,
            by_kind_veh=dict.fromkeys(('boundary_in','off_ramp','boundary_out','on_ramp','internal'),0.))
            for s in cfg.network.signals}
        sign={'boundary_in':1.,'off_ramp':1.,'boundary_out':-1.,'on_ramp':-1.,'internal':0.}
        for row in response['transfers']:
            route=row['route_key']
            if not isinstance(route,str) or not route.startswith('movement:'):continue
            spec=cfg.network.urban_movements[route[len('movement:'):]]
            offset=(row['start_sec']-state.time_sec)/10.
            if (row['stage']!='urban' or offset!=int(offset) or not 0<=offset<(end-state.time_sec)/10.
                    or row['end_sec']!=row['start_sec']+10
                    or not math.isfinite(row['vehicles']) or row['vehicles']<0):
                raise ValueError('Invalid local accepted movement clock/count')
            if spec['signal'] in owners:
                owner=owners[spec['signal']]
                owner['net_inflow_veh']+=sign[spec['kind']]*row['vehicles']
                owner['accepted_event_count']+=1
                owner['by_kind_veh'][spec['kind']]+=row['vehicles']
    else:
        vehicles=dict.fromkeys(cfg.network.ramps,0.)
        cursor=state.time_sec
        for frame in response['regional_merge_frames']:
            if frame['start_sec']!=cursor or frame['end_sec']!=cursor+5:
                raise ValueError('Missing local freeway merge frame')
            if set(frame['actual_ramp_release_veh_h']) != set(vehicles):
                raise ValueError('Incomplete local merge ramp catalog')
            for ramp,rate in frame['actual_ramp_release_veh_h'].items():
                if not math.isfinite(rate) or rate < 0:
                    raise ValueError('Invalid local accepted merge rate')
                vehicles[ramp]+=rate/720.
            cursor=frame['end_sec']
        if cursor!=end:raise ValueError('Incomplete local merge horizon')
        rates={r:n*3600/(end-state.time_sec) for r,n in vehicles.items()}
    return dict(schema='regional-accepted-quantities/v1',region=mode,owners=owners,
        start_sec=state.time_sec,end_sec=end,
        coverage=dict(region=mode, complete=True,
            sample_sec=5. if mode=='freeway_only' else 10.,
            samples=len(response.get('regional_merge_frames',[])) if mode=='freeway_only'
                else len([r for r in response['residence'] if r['stage']=='urban']),
            configured_movement_count=len(cfg.network.urban_movements) if mode=='urban_only' else 0),
        active_resource='NP' if mode=='urban_only' else 'NUF',
        np_actual=math.fsum(v['net_inflow_veh'] for v in owners.values()),
        nuf_actual=math.fsum(rates.values()),
        predicted_ramp_merge=dict(rate_veh_h_by_ramp=rates,accepted_vehicles_by_ramp=vehicles,
            active=mode=='freeway_only',boundary='ramp_to_mainline',remote_prediction=False))
