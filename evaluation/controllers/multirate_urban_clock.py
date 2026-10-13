"""Rebase a fresh observation's urban calendars onto ten-second ticks.

This prepares prediction state only. The opt-in multirate scheduler invokes
it after observation projection; default and native clocks stay unchanged.
Physical port/head/CTM clocks stay in absolute seconds. Urban step calendars
round forward, retaining the same counted owners and route/lane subsets.
"""
from __future__ import annotations
import copy
import math
from evaluation.controllers.sdmpc_aggregate_transport import IntervalBins


class UrbanTickBins(IntervalBins):
    """Preserve existing physical arrival bins while callers use urban ticks."""
    def add(self,key,due,amount):
        return super().add(key,due*self.input_tick_sec,amount)

    def advance(self,tick):
        return super().advance(tick*self.input_tick_sec)


def rebase_projection(cfg,state,duration_sec=10):
    """Prepare once, after1s observation projection and before any rollout.

    Build every replacement before committing. Rejection does not partially
    convert the supplied state. Native observation/provenance timestamps and
    physical component clocks are never rescaled. This function is not a
    declaration that the caller supports a full10s coupled urban rollout.
    """
    if duration_sec==1 and not isinstance(duration_sec,bool):return {'urban_clock_rebased':False}
    if isinstance(duration_sec,bool) or duration_sec!=10:
        raise ValueError('Urban prediction rebase supports the requested10s clock')
    now=state.time_sec
    if (cfg.simulation.T_u_sec!=1 or now%10 or cfg.simulation.T_c_sec%10
            or not math.isfinite(now) or int(now)!=now):
        raise ValueError('Urban rebase requires a fresh1s state aligned to10s')
    if getattr(cfg.network,'sdmpc_distance_reward',None) or getattr(state,'_omega_travel_reservations',None):
        raise ValueError('Urban clock rebase has not qualified distance reservations')
    counters=dict(calendar_entries=0,retimed_entries=0,max_delay_sec=0.)
    def tick(due):
        if isinstance(due,bool) or not math.isfinite(due) or int(due)!=due:
            raise ValueError('Urban calendar has a noninteger physical deadline')
        result=math.ceil(due/duration_sec)
        delay=result*duration_sec-due
        counters['calendar_entries']+=1
        counters['retimed_entries']+=bool(delay)
        counters['max_delay_sec']=max(counters['max_delay_sec'],delay)
        return result
    def add_values(left,right):
        if isinstance(right,dict):
            if not isinstance(left,dict):raise ValueError('Mixed urban calendar payloads')
            for key,value in right.items():
                if isinstance(value,dict):raise ValueError('Unexpected nested time payload')
                left[key]=left.get(key,0.)+value
            return left
        if isinstance(left,dict):raise ValueError('Mixed urban calendar payloads')
        return left+right
    def calendar(values):
        out={}
        for due,value in values.items():
            if due<now:raise ValueError('Fresh urban arrival calendar contains stale traffic')
            target=tick(due)
            if target in out:out[target]=add_values(out[target],value)
            else:out[target]=copy.deepcopy(value)
        return out
    def nested(values,depth):
        if depth==0:return calendar(values)
        return {key:nested(value,depth-1) for key,value in values.items()}
    def cohort(row):
        result=copy.deepcopy(row)
        for key in ('due','ready'):
            if key in result:result[key]=tick(result[key])
        if 'downstream_steps' in result:
            result['downstream_steps']=math.ceil(result['downstream_steps']/duration_sec)
        for tag,field in (('lane68','exit_step'),('connector68','ready_step')):
            if tag in result and field in result[tag]:result[tag][field]=tick(result[tag][field])
        return result
    replacements={}
    for name in ('urban_arrival_buffer','urban_storage_release_buffer','urban_inflow_transit_buffer','offramp_transit_buffer'):
        replacements[name]=nested(getattr(state,name),1)
    for name in ('gate_initial_route_tags','gate_future_route_tags'):
        if hasattr(state,name):replacements[name]=nested(getattr(state,name),1)
    local_names=('shared_approach_state','sc2001_corridor_state','route_choice_corridor_state',
        'native_internal_input_state','native_input_route_state','native_input_prehead_state')
    for name in local_names:
        if not hasattr(state,name):continue
        original=getattr(state,name)
        if original['last_step']!=now-1 or 'aggregate' in original:
            raise ValueError('Rebase requires an unadvanced observation: '+name)
        local=copy.deepcopy(original)
        local['last_step']=int(now/duration_sec)-1
        if 'finished_step' in local:
            if original['finished_step']!=now-1:raise ValueError('Unfinished pre-head service')
            local['finished_step']=local['last_step']
        if 'cohorts' in local:local['cohorts']=[cohort(row) for row in original['cohorts']]
        if name=='shared_approach_state':
            local['bins']=nested(original['bins'],1)
            if 'city_arrival_tags' in local:local['city_arrival_tags']=calendar(original['city_arrival_tags'])
        if name=='sc2001_corridor_state':local['bins']=nested(original['bins'],2)
        replacements[name]=local
    for name in ('known_legsplit_route_state','direct_exit_route_state'):
        if not hasattr(state,name):continue
        original=getattr(state,name)
        if original.get('plan') is not None or 'entry_lane_step' in original:
            raise ValueError('Cannot rebase an active receiving reservation')
        local=copy.deepcopy(original)
        local['cohorts']=[cohort(row) for row in original['cohorts']]
        replacements[name]=local
    for name,key in (('known_legsplit_route_state','aggregate_transport'),('route_choice_corridor_state','aggregate_routes')):
        local=replacements.get(name,{})
        if key not in local:continue
        obj=local[key]
        if (obj.start!=now or obj.dt!=10 or obj.bins.last!=-1
                or getattr(obj,'last_macro',None) is not None):
            raise ValueError('Urban rebase requires fresh10s physical transport bins')
        bins=object.__new__(UrbanTickBins)
        bins.__dict__.update(vars(obj.bins));bins.input_tick_sec=duration_sec
        obj.bins=bins;obj.start=int(now/duration_sec);obj.dt=1
        if hasattr(obj,'horizon'):obj.horizon=int(obj.horizon/duration_sec)
        obj.bins.verify()
    if hasattr(state,'lane_urban_runtime'):
        old=state.lane_urban_runtime
        if old.last_step!=now-1 or old.port.urban.time!=now:
            raise ValueError('Local urban model was already advanced')
        # Keep the shared port object and all physical FIFOs/geometry. Only its
        # urban step aliases are committed after every other check succeeds.
        lane_tags=calendar(old.arrival_tags)
    else:old=None
    ports=getattr(state,'lane_offramp_runtime',None)
    if ports is not None and ports.last_drain is not None:
        raise ValueError('Physical off-ramp drainage was already advanced')
    shared=getattr(state,'sc1001_approach',None)
    if shared is not None and shared.time!=now:
        raise ValueError('Shared physical approach was already advanced')
    # Gate travel was compiled into urban steps during1s projection. Rebasing
    # existing arrival calendars alone leaves newly generated traffic with
    # ten times its physical travel delay. Preserve that original duration.
    gate=getattr(cfg.network,'physical_gate_travel',None)
    if gate is not None:
        gate=copy.deepcopy(gate)
        for timing in gate['timings'].values():
            delay=timing['delay_steps']
            if type(delay) is not int or delay<1:raise ValueError('Invalid compiled gate delay')
            timing['delay_steps']=max(1,math.ceil(delay/duration_sec))
    for name,value in replacements.items():setattr(state,name,value)
    if old is not None:
        old.arrival_tags=lane_tags;old.last_step=int(now/duration_sec)-1
    cfg.simulation.T_u=duration_sec
    cfg.simulation.derived_time_ratios.update(K_fu=cfg.simulation.K_fu,
        K_cf=cfg.simulation.K_cf,K_cu=cfg.simulation.K_cu)
    cfg.network.multirate_urban_clock_sec=duration_sec
    if gate is not None:cfg.network.physical_gate_travel=gate
    return dict(urban_clock_rebased=True,urban_tick_sec=duration_sec,
        physical_component_clocks='unchanged absolute seconds',whole_urban_scheduler_qualified=False,**counters)
