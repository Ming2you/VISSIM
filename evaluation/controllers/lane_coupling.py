"""Conservative coupling, with an explicit optional five-second freeway clock."""
from __future__ import annotations
import math


def split_10643(amount,group_capacity_veh_h,split,*,duration_sec=1.):
    """C5 / D-C (b): lane admissions [veh/step] of the aggregate 10643 off flow.

    Without mainline lane groups the plant knows only the total. The split
    holds the last closed window's observed lane shares over the horizon (a
    closure assumption; the observation itself is exact) and water-fills into
    the other lane when a share would exceed its lane's receiving room. The sum
    is exact (land(), lane_offramp_runtime.py:133-136) and each lane stays in
    its room whenever the total does, which caps['10643']=min(storage, sum of
    lanes) guarantees (lane_offramp_runtime.py:116-117).
    """
    if not isinstance(split,dict) or split.get('mode')!='observed_lane_shares_held':
        raise ValueError('10643 lane split requires the declared observed-share closure')
    if duration_sec not in (1,5,10):raise ValueError('Off-ramp split requires1/5/10s')
    share=split['shares'][0]
    rooms=[q/3600. if duration_sec==1 else q*duration_sec/3600. for q in group_capacity_veh_h[:2]]
    if math.fsum(group_capacity_veh_h[2:])>1e-8:
        raise ArithmeticError('10643 lane room reported for an inaccessible lane')
    if amount>rooms[0]+rooms[1]+1e-7:
        raise ArithmeticError('10643 aggregate admission exceeds both lane rooms')
    first=min(rooms[0],max(amount-rooms[1],amount*share))
    return [first,amount-first]


def lane_amounts_10643(freeway,off_flows,group_capacity,network,*,duration_sec=1.):
    """10643 lane admissions for land(): the FW_E lane groups report them
    (v1); without lane groups (v2) the declared observed-share split makes
    them (C5). Exactly one of the two sources must be declared."""
    if duration_sec not in (1,5,10):raise ValueError('Off-ramp lane amounts require1/5/10s')
    split=getattr(network,'lane_plant_10643_lane_split',None)
    if ('FW_E' in freeway.lanes)==(split is not None):
        raise ValueError('10643 lane amounts need exactly one source: FW_E lane groups or the declared lane split')
    if split is None:
        local=freeway.lanes['FW_E']
        if math.fsum(local.last_off_sent['10643'][2:])>1e-8:
            raise ArithmeticError('10643 admission came from an inaccessible mainline group')
        return local.last_off_sent['10643'][:2]
    amount=off_flows['10643']/3600. if duration_sec==1 else off_flows['10643']*duration_sec/3600.
    return split_10643(amount,group_capacity['10643'],split,duration_sec=duration_sec)


def run_interval(state,control,demand,cfg):
    if getattr(cfg.network,'multirate_joint_clock_enabled',False):
        from evaluation.controllers.multirate_coupling import run_interval as coarse_interval
        return coarse_interval(state,control,demand,cfg)
    from evaluation.controllers import area_freeway_accounting as accounting
    from evaluation.controllers import area_meter_finalization
    from evaluation.controllers.control_area_objective import get_ledger,integrate_residence
    from evaluation.controllers.area_runtime import model_inventory
    cp=accounting._cp
    sim=cfg.simulation
    if sim.T_u_sec!=1 or sim.T_f_sec not in (1,5):
        raise ValueError('Lane plant requires urban1s and freeway1/5s')
    duration=int(sim.T_f_sec)
    if duration==5 and not getattr(cfg.network,'multirate_freeway_exchange_enabled',False):
        raise ValueError('Five-second freeway coupling requires explicit opt-in')
    freeway=state.lane_freeway_runtime
    ramps=state.lane_ramp_runtime
    ports=state.lane_offramp_runtime
    if duration==5:
        if freeway.lanes or any(c.simulation.T_f_sec!=5 for c in freeway.configs.values()):
            raise ValueError('Five-second coupling requires matching aggregate road clocks')
        if getattr(cfg.network,'sdmpc_distance_reward',None):
            raise ValueError('Five-second coupling has not qualified the one-second distance observer')
    area_meter_finalization.finalize(control,cfg)
    ledger=get_ledger(state)
    start=state.time_sec
    if int(start)!=start or start!=freeway.time_sec:
        raise ValueError('Lane plant rollout clock differs from TrafficState')
    scopes=['urban_allocator','lane_urban_allocator','physical_offramp_drain']
    scopes.extend(k for k in ('shared_approach','sc2001_corridor') if getattr(cfg.network,k,None))
    if getattr(cfg.network,'leg_ramp_split_enabled',False) and getattr(cfg.network,'boundary_out_ramp_split',None):
        scopes.append('legsplit_allocator')
    if getattr(cfg.network,'route_choice_corridor',None):scopes.append('route_choice_allocator')
    if getattr(cfg.network,'native_internal_inputs',None):
        scopes.extend(('native_route_queue','native_prehead_queue','native_input_generation','native_prehead_residual'))
    ledger.plan_constraint_interval(start,1,duration,duration,sim.K_cf,scopes,
                                    off_ramps=tuple(ports.descriptions),physical_ramps=True)
    services={}
    for name,row in cfg.network.physical_ramp_branches['ramps'].items():
        green=control.diagnostics['rw_meter_green_'+name]
        # service_veh is the complete cycle's measured head passage, including
        # the selected10490 override. The buffer applies its actual RED clock.
        if not getattr(cfg.network, '_sdmpc_continuous_prediction', False):
            services[name]=dict(mode='GREEN' if green else 'RED',green_sec=green,
                service_veh=row['service_by_green_veh_h'][str(int(green))]*ramps.cycle_sec/3600.)
    if getattr(cfg.network, '_sdmpc_continuous_prediction', False):
        from evaluation.controllers.sdmpc_continuous import ramp_services
        services = ramp_services(control, cfg, ramps.cycle_sec)
    fw_cost=urban_cost=accepted=0.
    fw_rows=[];urban_rows=[]
    try:
        for index in range(sim.K_cf):
            sec=int(start)+index*duration
            state.time_sec=sec
            from evaluation.controllers.omega_distance import before_reward_step
            before_reward_step(state,cfg,demand)
            ledger.begin_response_step('freeway',sec,sec+duration)
            release,group_release,receipts=ramps.advance(state,control,demand,freeway,service=services)
            ledger.complete_constraint_coverage('physical_ramp_release')
            for urban_offset in range(duration):
                urban_sec=sec+urban_offset
                state.time_sec=urban_sec
                if urban_offset:before_reward_step(state,cfg,demand)
                ledger.begin_response_step('urban',urban_sec,urban_sec+1)
                cost,ur=cp.urban_substep(state,control,demand,cfg,urban_step_index=urban_sec,ramp_release_veh_h=release)
                urban_cost+=cost
                urban_rows.append(ur)
                # Fine urban arrivals consume the one finite macro ramp budget;
                # all retain the macro-end timestamp and cannot merge early.
                ramps.finish(state,keep_release=urban_offset+1<duration)
            state.time_sec=sec
            capacity,group_capacity=ports.capacities(state,cfg,duration_sec=duration)
            ledger.begin_response_step('freeway',sec,sec+duration)
            stepper=freeway.advance if duration==1 else freeway.advance_macro
            cost,off_flows,by_road=stepper(state,control,demand,
                ramp_releases=release,off_capacities=capacity,
                ramp_group_releases=group_release,off_group_capacities=group_capacity)
            fw_cost+=cost
            fw={}
            for road,row in by_road.items():
                for key,value in row.items():
                    if isinstance(value,(int,float)):fw[key]=fw.get(key,0.)+value
            fw['mainline_origin_queue_total_veh']=math.fsum(state.mainline_origin_queue.values())
            fw['offramp_flow_total']=math.fsum(off_flows.values())
            fw['ramp_queue_total']=math.fsum(state.ramp_queue.values())
            # Road kernels carry diagnostic reference ramp caps; the coupled
            # stocks use the current physical connector capacities instead.
            fw['ramp_queue_overflow_count']=float(sum(q>cfg.network.ramp_queue_cap(r)+1e-8
                for r,q in state.ramp_queue.items()))
            fw_rows.append(fw)
            lane_amounts={'10643':lane_amounts_10643(freeway,off_flows,group_capacity,cfg.network,duration_sec=duration)}
            ledger.begin_response_step('landing',sec,sec+duration)
            accepted+=ports.land(state,cfg,sec+duration,off_flows,lane_amounts,duration_sec=duration)
            integrate_residence(state,cfg,
                ['freeway:'+r for r in cfg.network.freeway_links]+
                ['origin:'+r for r in cfg.network.freeway_links],sim.T_f_h)
            if ledger.captures_response:ledger.assert_stocks(model_inventory(state,cfg))
            ledger.record_freeway_operands(state,control,release)
    finally:
        # The canonical rollout endpoint advances the public clock once byTc.
        # Internal physical buffers have already advanced each of its seconds.
        state.time_sec=start
    diagnostics=cp._aggregate_freeway_diagnostics(fw_rows,interval_h=sim.T_c_h,
        rows_per_cycle=max(1,int(cfg.network.cycle_length/duration)),
        queue_cap_veh=math.fsum(cfg.network.ramp_queue_cap(r) for r in cfg.network.ramps))
    diagnostics.update(cp.aggregate_urban_diagnostics(urban_rows,cfg,control,interval_h=sim.T_c_h))
    diagnostics.update(lane_plant_active=True,coupling_nested_order_active=1.,
        coupling_freeway_substeps=float(sim.K_cf),coupling_urban_substeps=float(sim.K_cu),
        coupling_offramp_arrivals_accepted_veh=accepted,coupling_offramp_arrivals_rejected_veh=0.)
    if getattr(cfg.network,'control_area_pack_completed_response_records',False):
        if (getattr(cfg.network,'sdmpc_options',None) or {}).get('compact_audit',False):
            from evaluation.controllers.sdmpc_tangent_audit import compact_enabled
            ledger.pack_completed_response_records(compact=compact_enabled(cfg))
        else:
            ledger.pack_completed_response_records()
    return cp.CoupledStepResult(freeway_ttt=fw_cost,urban_ttt=urban_cost,diagnostics=diagnostics)
