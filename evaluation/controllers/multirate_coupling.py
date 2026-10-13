"""Opt-in FW5/urban10 coupling with counted endpoint exchange buffers.

Explicit lagged interfaces: urban drainage cannot create early freeway room;
new city/ramp and freeway/off-ramp receipts become physical at the10s end.
METANET still advances twice. Short urban cells retain their1s numerics.
Omega residence uses one declared10s right-endpoint quadrature, not a mixture
of twice-counted component integrals. This is a coarse model approximation.
"""
from __future__ import annotations
import copy
import math
from contextlib import contextmanager


def configure(cfg,tuning,state):
    option=(tuning or {}).get('urban',{}).get('multirate_exchange_sec')
    if option is None:return {}
    if type(option) is not int or option!=10:
        raise ValueError('Urban multirate exchange must be explicitly10s')
    if (cfg.simulation.T_f_sec!=5 or cfg.simulation.T_c_sec%10 or
            not getattr(cfg.network,'multirate_freeway_exchange_enabled',False)):
        raise ValueError('Urban10 requires the configured aggregate freeway5 clock')
    from evaluation.controllers.multirate_urban_clock import rebase_projection
    result=rebase_projection(cfg,state)
    cfg.network.multirate_joint_clock_enabled=True
    return {**result,'prediction_exchange':'FW5/urban10 lagged finite boundaries',
            'whole_urban_scheduler_qualified':False,'omega_quadrature_sec':10}


class OffReceivingBudget:
    """Causal start-stock room, shared by both5s freeway steps.

    For10643 a zero-drain copy gives a conservative cumulative wave bound.
    No future urban outflow supplies a freeway receiving offer in this block.
    The real ports are not mutated until their urban service/endpoint landing.
    """
    def __init__(self,ports,state,start):
        self.room={off:state.urban_link_storage[r['storage']] for off,r in ports.descriptions.items()}
        self.used=dict.fromkeys(self.room,0.);self.lane_used=[0.,0.]
        self.lane_bounds=[[],[]];self.lane_rate=[]
        for p in ports.local_port.lanes:
            if p.time!=start:raise ValueError('Stale off-ramp receiving history')
            q=copy.deepcopy(p);self.lane_rate.append(q.envelope.qmax)
            q.release(start,5,0.)
            self.lane_bounds[0].append(min(q.capacity-q.stock,q.receiving(5)))
            q.release(start+5,5,0.)
            self.lane_bounds[1].append(min(q.capacity-q.stock,q.receiving(10)))

    def offer(self,half):
        if half not in (0,1):raise ValueError('Only two5s receiving queries per block')
        lanes=[max(0.,min(bound-used,5*rate)) for bound,used,rate in
               zip(self.lane_bounds[half],self.lane_used,self.lane_rate)]
        counts={off:max(0.,room-self.used[off]) for off,room in self.room.items()}
        counts['10643']=min(counts['10643'],math.fsum(lanes))
        return ({off:n*720. for off,n in counts.items()}, {'10643':[n*720. for n in lanes]+[0.]})

    def consume(self,flows,lanes,half):
        caps,groups=self.offer(half)
        for off,rate in flows.items():
            n=rate/720.
            if n<0 or n>caps[off]/720.+1e-7:raise ArithmeticError('Repeated off-ramp receiving room')
            self.used[off]+=n
        if abs(sum(lanes)-flows['10643']/720.)>1e-7:
            raise ArithmeticError('10643 accepted lane counts differ from total')
        for g,n in enumerate(lanes):
            if n<0 or n>groups['10643'][g]/720.+1e-7:
                raise ArithmeticError('10643 reused its causal lane budget')
            self.lane_used[g]+=n


def prepare_ramp_admission_windows(ramps,start):
    """Current10s urban receiving, using only closed past head history.

    The ordinary ramp solver owns two5s physical steps. Its last5s offer has
    already been spent when the next urban step starts; reusing that offer
    spuriously blocks arrivals. Keep a separate cumulative10s admission window
    with no forecast head departures, and commit that same budget at its end.
    """
    from evaluation.controllers.known_wout_causal_response import begin_receiving_interval
    result=[]
    for buffer in ramps.buffers.values():
        for child in getattr(buffer,'_lane_buffers',[buffer]):
            if not getattr(child,'_causal_receiving_enabled',False):continue
            original=child._spatial_entry
            try:
                child._spatial_entry=copy.deepcopy(original)
                begin_receiving_interval(child,start,10)
                result.append((child,child._spatial_entry))
            finally:child._spatial_entry=original
    return result


@contextmanager
def ramp_admission_windows(windows):
    previous=[(child,child._spatial_entry) for child,_ in windows]
    try:
        for child,window in windows:child._spatial_entry=window
        yield
    finally:
        for child,window in previous:child._spatial_entry=window


def plan_coverage(ledger,start,duration,scopes,off_ramps):
    """Declare actual nonnested visits; never manufacture a K_fu ratio."""
    if not ledger.captures_response:return
    rows=ledger._response['constraint_intervals']
    if rows and not math.isclose(rows[-1]['end_sec'],start,abs_tol=1e-9):
        raise ValueError('Noncontiguous multirate constraint interval')
    previous=ledger._response_clock
    try:
        for sec in range(int(start),int(start+duration),10):
            ledger.begin_response_step('urban',sec,sec+10)
            for scope in scopes:ledger.expect_constraint_coverage(scope)
            ledger.begin_response_step('landing',sec,sec+10)
            for scope in ('offramp_landing',*('offramp_landing:'+r for r in off_ramps)):
                ledger.expect_constraint_coverage(scope)
            for sub in (sec,sec+5):
                ledger.begin_response_step('freeway',sub,sub+5)
                for scope in ('physical_ramp_release','freeway_allocator'):
                    ledger.expect_constraint_coverage(scope)
    finally:ledger._response_clock=previous
    rows.append(dict(start_sec=start,end_sec=start+duration,T_u_sec=10.,T_f_sec=5.,
                     exchange='endpoint10',urban_scopes=list(scopes),off_ramps=list(off_ramps)))


def run_interval(state,control,demand,cfg):
    from evaluation.controllers import area_freeway_accounting as accounting,area_meter_finalization
    from evaluation.controllers.control_area_objective import get_ledger,emit_transfer,integrate_residence
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.lane_coupling import lane_amounts_10643
    sim=cfg.simulation;fw=state.lane_freeway_runtime;ramps=state.lane_ramp_runtime;ports=state.lane_offramp_runtime
    if (sim.T_u_sec!=10 or sim.T_f_sec!=5 or fw.lanes or sim.T_c_sec%10
            or state.time_sec%10 or state.time_sec!=fw.time_sec
            or any(c.simulation.T_f_sec!=5 for c in fw.configs.values())
            or getattr(cfg.network,'sdmpc_distance_reward',None)):
        raise ValueError('Unsupported coarse coupled prediction clock/model')
    if any(getattr(state,'multirate_exchange_pending',{}).values()):
        raise ValueError('Uncommitted previous exchange interval')
    area_meter_finalization.finalize(control,cfg)
    ledger=get_ledger(state);cp=accounting._cp;start=state.time_sec
    scopes=['urban_allocator','lane_urban_allocator','physical_offramp_drain']
    scopes.extend(k for k in ('shared_approach','sc2001_corridor') if getattr(cfg.network,k,None))
    if getattr(cfg.network,'leg_ramp_split_enabled',False) and getattr(cfg.network,'boundary_out_ramp_split',None):scopes.append('legsplit_allocator')
    if getattr(cfg.network,'route_choice_corridor',None):scopes.append('route_choice_allocator')
    if getattr(cfg.network,'native_internal_inputs',None):
        scopes.extend(('native_route_queue','native_prehead_queue','native_input_generation','native_prehead_residual'))
    plan_coverage(ledger,start,sim.T_c_sec,scopes,tuple(ports.descriptions))
    if getattr(cfg.network,'_sdmpc_continuous_prediction',False):
        from evaluation.controllers.sdmpc_continuous import ramp_services
        services=ramp_services(control,cfg,ramps.cycle_sec)
    else:
        services={}
        for name,row in cfg.network.physical_ramp_branches['ramps'].items():
            green=control.diagnostics['rw_meter_green_'+name]
            services[name]=dict(mode='GREEN' if green else 'RED',green_sec=green,
                service_veh=row['service_by_green_veh_h'][str(int(green))]*ramps.cycle_sec/3600.)
    pending=state.multirate_exchange_pending={}
    fw_cost=urban_cost=accepted=0.;fw_rows=[];urban_rows=[]
    try:
        for sec in range(int(start),int(start+sim.T_c_sec),10):
            state.time_sec=sec;budget=OffReceivingBudget(ports,state,sec)
            ramp_windows=prepare_ramp_admission_windows(ramps,sec)
            old_ramps=dict(state.ramp_queue)
            ledger.begin_response_step('urban',sec,sec+10)
            # Empty physical merge map: the5s ramp solver alone owns merges.
            with ramp_admission_windows(ramp_windows):
                cost,ur=cp.urban_substep(state,control,demand,cfg,urban_step_index=sec//10,ramp_release_veh_h={})
            urban_cost+=cost;urban_rows.append(ur)
            new_ramps={name:state.ramp_queue[name]-old for name,old in old_ramps.items()}
            for name,n in new_ramps.items():
                if n<-1e-8:raise ArithmeticError('Urban step secretly debited a physical ramp')
                n=max(0.,n);new_ramps[name]=n;state.ramp_queue[name]=old_ramps[name]
                key='transit:exchange:ramp:'+name;pending[key]=n
                emit_transfer(state,cfg,'ramp:'+name,key,n,preserve_area=True)
            ramps.assert_mirror(state)
            ledger.assert_stocks(model_inventory(state,cfg))
            off_owners={off:'transit:exchange:off:'+off for off in ports.descriptions}
            routes={};merged=0.
            for half in (0,1):
                t=sec+half*5;state.time_sec=t
                ledger.begin_response_step('freeway',t,t+5)
                release,group_release,_=ramps.advance(state,control,demand,fw,service=services)
                merged+=sum(release.values())/720.
                ledger.complete_constraint_coverage('physical_ramp_release')
                ramps.finish(state)
                caps,groups=budget.offer(half)
                # The freeway sees start-block off stock plus earlier accepted
                # traffic, not space freed by urban service in its future.
                real_room={r['storage']:state.urban_link_storage[r['storage']] for r in ports.descriptions.values()}
                for off,row in ports.descriptions.items():state.urban_link_storage[row['storage']]=budget.room[off]-budget.used[off]
                try:
                    cost,flows,by_road=fw.advance_macro(state,control,demand,ramp_releases=release,
                        off_capacities=caps,ramp_group_releases=group_release,off_group_capacities=groups)
                finally:state.urban_link_storage.update(real_room)
                fw_cost+=cost
                lanes=lane_amounts_10643(fw,flows,groups,cfg.network,duration_sec=5)
                budget.consume(flows,lanes,half)
                for off,rate in flows.items():
                    key=off_owners[off];n=rate/720.;pending[key]=pending.get(key,0.)+n
                    emit_transfer(state,cfg,'freeway:'+ports.descriptions[off]['road'],key,n,preserve_area=True)
                for road,receipt in state.offramp_route_inventory_state['last_offramp_receipts'].items():
                    if receipt['end_sec']!=t+5:raise ValueError('Stale freeway destination receipt')
                    dest=routes.setdefault(road,dict(end_sec=sec+10,ports={}))
                    for off,packets in receipt['ports'].items():
                        values=dest['ports'].setdefault(off,{})
                        for route,n in packets.items():values[route]=values.get(route,0.)+n
                ledger.assert_stocks(model_inventory(state,cfg))
                row={}
                for road,values in by_road.items():
                    for key,value in values.items():
                        if isinstance(value,(int,float)):row[key]=row.get(key,0.)+value
                row.update(mainline_origin_queue_total_veh=sum(state.mainline_origin_queue.values()),
                    offramp_flow_total=sum(flows.values()),ramp_queue_total=sum(state.ramp_queue.values()),
                    ramp_queue_overflow_count=float(sum(q>cfg.network.ramp_queue_cap(r)+1e-8 for r,q in state.ramp_queue.items())))
                fw_rows.append(row);ledger.record_freeway_operands(state,control,release,multirate_exchange=True)
            ledger.begin_response_step('landing',sec,sec+10)
            accepted+=ports.land(state,cfg,sec+10,{off:n*360. for off,n in budget.used.items()},
                {'10643':budget.lane_used},duration_sec=10,source_owners=off_owners,route_receipts=routes)
            for key in off_owners.values():pending[key]=0.
            with ramp_admission_windows(ramp_windows):
                for name,n in new_ramps.items():
                    state.ramp_queue[name]+=n;ramps.buffers[name].admit_current(n)
                    key='transit:exchange:ramp:'+name
                    emit_transfer(state,cfg,key,'ramp:'+name,n,preserve_area=True);pending[key]=0.
            ramps.assert_mirror(state);ledger.assert_stocks(model_inventory(state,cfg))
            ledger.begin_response_step('urban',sec,sec+10)
            integrate_residence(state,cfg,tuple(ledger.stocks),10./3600.)
            ur['multirate_actual_merge_veh']=merged
    finally:state.time_sec=start
    diagnostics=cp._aggregate_freeway_diagnostics(fw_rows,interval_h=sim.T_c_h,
        rows_per_cycle=max(1,int(cfg.network.cycle_length/5)),
        queue_cap_veh=sum(cfg.network.ramp_queue_cap(r) for r in cfg.network.ramps))
    diagnostics.update(cp.aggregate_urban_diagnostics(urban_rows,cfg,control,interval_h=sim.T_c_h))
    diagnostics.update(lane_plant_active=True,coupling_nested_order_active=0.,coupling_multirate_endpoint_active=1.,
        coupling_freeway_substeps=float(sim.K_cf),coupling_urban_substeps=float(sim.K_cu),
        coupling_offramp_arrivals_accepted_veh=accepted,coupling_offramp_arrivals_rejected_veh=0.)
    if getattr(cfg.network,'control_area_pack_completed_response_records',False):
        from evaluation.controllers.sdmpc_tangent_audit import compact_enabled
        ledger.pack_completed_response_records(compact=compact_enabled(cfg))
    return cp.CoupledStepResult(freeway_ttt=fw_cost,urban_ttt=urban_cost,diagnostics=diagnostics)
