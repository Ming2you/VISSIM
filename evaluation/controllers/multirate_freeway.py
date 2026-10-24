"""Five-second boundary exchange for aggregate physical METANET roads.

An accepted ramp packet is spread over the macro interval and consumed once.
Off-ramp rates stay bounded by the same finite macro receiving reservation.
All cells/roads share each internal time step; internal face fluxes therefore
cancel exactly. This first version is global subcycling, not cell-local LTS.
Enable explicitly after current-state projection; observation/native clocks
are unchanged. The urban physical solver in this stage still uses one second.
"""
from __future__ import annotations
import copy
import math


def configure(cfg,tuning,state):
    """Change prediction clocks only after one-second observation projection."""
    option=(tuning or {}).get('freeway',{}).get('multirate_exchange_sec')
    if option is None:return {}
    if isinstance(option,bool) or option!=5:
        raise ValueError('The qualified optional freeway macro duration is5seconds')
    runtime=getattr(state,'lane_freeway_runtime',None)
    if (runtime is None or runtime.lanes or cfg.simulation.T_u_sec!=1
            or cfg.simulation.T_f_sec!=1 or cfg.simulation.T_c_sec%5
            or state.time_sec%5 or state.time_sec!=runtime.time_sec
            or any(c.simulation.T_f_sec!=1 for c in runtime.configs.values())):
        raise ValueError('Five-second prediction requires a freshly projected aggregate road state and urban1s')
    if getattr(cfg.network,'sdmpc_distance_reward',None):
        raise ValueError('Five-second coupling has not qualified the distance observer')
    for buffer in state.lane_ramp_runtime.buffers.values():
        if getattr(buffer,'lane_exchange_rates',None):
            raise ValueError('Five-second ramp lane exchange is not implemented')
        for lane in getattr(buffer,'_lane_buffers',[buffer]):
            memory=getattr(lane,'_spatial_entry',None)
            if memory and memory['envelope'].lag<5:
                raise ValueError('Ramp receiving wave requires a shorter exchange')
    cfg.simulation.T_f=5.
    cfg.simulation.derived_time_ratios.update(K_fu=cfg.simulation.K_fu,
        K_cf=cfg.simulation.K_cf,K_cu=cfg.simulation.K_cu)
    cfg.network.multirate_freeway_exchange_enabled=True
    for road_cfg in runtime.configs.values():road_cfg.simulation.T_f=5.
    return dict(prediction_freeway_macro_sec=5.,prediction_urban_physical_sec=1.,
        prediction_freeway_internal_steps='shared advection/relaxation substeps; physical31cells retained',
        native_simulation_clock_changed=False)


def supports_joint_clock(cfg, state):
    """Keep legacy1s and explicitly configured aggregate5s joint execution."""
    if cfg.simulation.T_u_sec != 1:
        return (cfg.simulation.T_u_sec==10 and cfg.simulation.T_f_sec==5
                and getattr(cfg.network,'multirate_joint_clock_enabled',False)
                and getattr(cfg.network,'multirate_freeway_exchange_enabled',False)
                and state.lane_freeway_runtime.time_sec==state.time_sec)
    if cfg.simulation.T_f_sec == 1:
        return True
    runtime = getattr(state, 'lane_freeway_runtime', None)
    return (cfg.simulation.T_f_sec == 5
            and getattr(cfg.network, 'multirate_freeway_exchange_enabled', False)
            and runtime is not None and not runtime.lanes
            and bool(runtime.configs)
            and all(c.simulation.T_f_sec == 5 for c in runtime.configs.values()))


def time_limit(runtime, state):
    """Advection/relaxation screen, not a theorem for the full speed equation.

    Use actual modeled speeds (including speeds above the DSD) and each cell's
    tau. Integer substep selection is a numerical branch, not a control bonus.
    Empirical response/conservation checks are still required for anticipation.
    """
    from evaluation.controllers.freeway_geometry import cell_lengths_km
    limit=5.
    for road,cfg in runtime.configs.items():
        speeds=state.freeway_speed[road]
        lengths=cell_lengths_km(cfg.network,road,len(speeds))
        for i,(length,speed) in enumerate(zip(lengths,speeds)):
            # The integrator's grid is discrete; AD differentiates its equations
            # conditional on this same chosen grid.
            speed=getattr(speed,'_validation_primal',speed)
            if not math.isfinite(speed) or speed<0 or length<=0:
                raise ValueError('Invalid physical speed/length in multirate screen')
            if speed:limit=min(limit,.9*3600.*length/speed)
            rows=(getattr(cfg.network,'freeway_segment_params',{}) or {}).get(road)
            tau=rows[i].get('metanet_tau_h',cfg.network.metanet_tau_h) if rows else cfg.network.metanet_tau_h
            if not math.isfinite(tau) or tau<=0:raise ValueError('Invalid relaxation time')
            limit=min(limit,.5*3600.*tau)
    return limit


def advance(runtime,state,control,demand,*,ramp_releases,off_capacities,
            ramp_group_releases=None,off_group_capacities=None):
    """Return integrated cost, mean off rates and duration-weighted diagnostics.

    Caller owns exactly one macro ramp debit and final off-ramp landing.
    Per-road kernels and physical31cells are unchanged. Residence accounting
    for the full network remains the caller's macro endpoint quadrature.
    """
    from evaluation.controllers.control_area_objective import get_ledger
    if runtime.lanes:
        raise ValueError('Five-second macro currently supports aggregate physical roads only')
    if any(c.simulation.T_f_sec!=5 for c in runtime.configs.values()):
        raise ValueError('Declare the five-second freeway exchange clock explicitly')
    if state.time_sec!=runtime.time_sec:
        raise ValueError('Noncontiguous macro freeway clock')
    if (set(ramp_releases)!=set(runtime.ramps) or set(off_capacities)!=set(runtime.offramps)
            or any(not math.isfinite(q) or q<0 for q in (*ramp_releases.values(),*off_capacities.values()))):
        raise ValueError('Invalid or incomplete macro boundary flows')
    original=runtime.configs;start=state.time_sec;end=start+5.
    ledger=get_ledger(state)
    remaining=5.;cost=0.;off={o:0. for o in off_capacities};diagnostics={r:{} for r in runtime.roads}
    grid=[]
    route_receipts={}
    configs={r:copy.copy(c) for r,c in original.items()}
    for road,cfg in configs.items():cfg.simulation=copy.copy(original[road].simulation)
    runtime.configs=configs
    try:
        while remaining>1e-9:
            limit=time_limit(runtime,state)
            count=max(1,math.ceil(remaining/limit))
            dt=remaining/count
            for cfg in configs.values():cfg.simulation.T_f=dt
            state.time_sec=runtime.time_sec
            if ledger is not None:ledger.begin_response_step('freeway',state.time_sec,state.time_sec+dt)
            c,flows,rows=runtime.advance(state,control,demand,
                ramp_releases=ramp_releases,off_capacities=off_capacities,
                ramp_group_releases=ramp_group_releases,off_group_capacities=off_group_capacities,
                complete_ramp_packets=count==1,complete_allocator_scope=False)
            cost+=c
            for off_id,q in flows.items():off[off_id]+=q*dt/5.
            inventory=getattr(state,'offramp_route_inventory_state',None)
            if inventory is not None:
                for road in runtime.roads:
                    receipt=inventory['last_offramp_receipts'][road]
                    if abs(receipt['end_sec']-runtime.time_sec)>1e-7:
                        raise ArithmeticError('Route receipt does not close this internal step')
                    combined=route_receipts.setdefault(road,dict(end_sec=end,ports={}))
                    for port,packets in receipt['ports'].items():
                        if abs(math.fsum(packets.values())-flows[port]*dt/3600.)>1e-7:
                            raise ArithmeticError('Internal route receipt differs from accepted exit')
                        target=combined['ports'].setdefault(port,{})
                        for route,n in packets.items():target[route]=target.get(route,0.)+n
            for road,row in rows.items():
                if row.get('density_projection_count',0)>0:
                    raise ArithmeticError('Coarse mainline lost vehicle conservation by density clipping')
                for key,value in row.items():
                    if isinstance(value,(int,float)):
                        diagnostics[road][key]=diagnostics[road].get(key,0.)+value*dt/5.
            grid.append(dt);remaining-=dt
        if abs(runtime.time_sec-end)>1e-7:raise ArithmeticError('Macro freeway clock did not close')
        runtime.time_sec=end
        for off_id,q in off.items():
            if q>off_capacities[off_id]+1e-7:raise ArithmeticError('Macro exit reused finite receiving')
        if route_receipts:
            state.offramp_route_inventory_state['last_offramp_receipts'].update(route_receipts)
        if ledger is not None:
            ledger.begin_response_step('freeway',start,end)
            ledger.complete_constraint_coverage('freeway_allocator')
        runtime.last_macro_substeps_sec=tuple(grid)
        for road,row in diagnostics.items():
            row['multirate_freeway_internal_steps']=len(grid)
            row['multirate_freeway_macro_sec']=5.
        return cost,off,diagnostics
    finally:
        runtime.configs=original
        state.time_sec=start
