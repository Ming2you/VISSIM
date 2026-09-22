"""One-second conservative coupling for the explicitly enabled lane plant."""
from __future__ import annotations
import math


def run_interval(state,control,demand,cfg):
    from evaluation.controllers import area_freeway_accounting as accounting
    from evaluation.controllers import area_meter_finalization
    from evaluation.controllers.control_area_objective import get_ledger,integrate_residence
    from evaluation.controllers.area_runtime import model_inventory
    cp=accounting._cp
    sim=cfg.simulation
    if sim.T_u_sec!=1 or sim.T_f_sec!=1:
        raise ValueError('Lane plant requires one-second urban and freeway steps')
    freeway=state.lane_freeway_runtime
    ramps=state.lane_ramp_runtime
    ports=state.lane_offramp_runtime
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
    ledger.plan_constraint_interval(start,1,1,1,sim.K_cf,scopes,
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
            sec=int(start)+index
            state.time_sec=sec
            ledger.begin_response_step('freeway',sec,sec+1)
            release,group_release,receipts=ramps.advance(state,control,demand,freeway,service=services)
            ledger.complete_constraint_coverage('physical_ramp_release')
            ledger.begin_response_step('urban',sec,sec+1)
            cost,ur=cp.urban_substep(state,control,demand,cfg,urban_step_index=sec,ramp_release_veh_h=release)
            urban_cost+=cost
            urban_rows.append(ur)
            ramps.finish(state)
            capacity,group_capacity=ports.capacities(state,cfg)
            ledger.begin_response_step('freeway',sec,sec+1)
            cost,off_flows,by_road=freeway.advance(state,control,demand,
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
            local=freeway.lanes['FW_E']
            lane_amounts={'10643':local.last_off_sent['10643'][:2]}
            if math.fsum(local.last_off_sent['10643'][2:])>1e-8:
                raise ArithmeticError('10643 admission came from an inaccessible mainline group')
            ledger.begin_response_step('landing',sec,sec+1)
            accepted+=ports.land(state,cfg,sec+1,off_flows,lane_amounts)
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
        rows_per_cycle=max(1,int(cfg.network.cycle_length)),
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
