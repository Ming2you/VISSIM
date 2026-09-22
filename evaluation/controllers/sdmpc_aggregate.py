"""Fixed-horizon fractional route inventories for the SDMPC predictor.

Route identity, signal gates, receiving, head travel and accepted service remain
explicit. Historical cohort IDs are replaced by route/stage/time-bin masses.
The last bin holds arrivals strictly beyond this prediction horizon; it cannot
be reused for a longer prediction. No vehicle mass or derivative is truncated.
"""
from __future__ import annotations
import math
from collections import defaultdict
import numpy as np
from evaluation.controllers.sdmpc_dual import primal


def enabled(cfg):
    return (getattr(cfg.network,'sdmpc_options',None) or {}).get('aggregate_predictor') == 'route-bins-v1'


class TimeBins:
    def __init__(self, labels, start, steps):
        self.labels=tuple(labels);self.index={key:i for i,key in enumerate(labels)}
        self.start=int(start);self.end=self.start+int(steps)
        self.last=self.start-1
        # Slot zero is already ready; final slot never matures in this horizon.
        self.future=np.zeros((len(labels),int(steps)+2),dtype=object)
        self.waiting=np.zeros(len(labels),dtype=object)
        self.pending=np.zeros(len(labels),dtype=object)

    def add(self,key,due,amount):
        if not math.isfinite(primal(amount)) or primal(amount)<0:raise ValueError('Invalid aggregate arrival')
        j=self.index[key]
        slot=max(0,min(int(due)-self.start,self.future.shape[1]-1))
        if due<=self.last:
            self.waiting[j]+=amount
        else:
            self.future[j,slot]+=amount;self.pending[j]+=amount

    def advance(self,step):
        if step!=self.last+1 or step>self.end:
            raise ValueError('Aggregate predictor clock/horizon mismatch')
        slot=max(0,step-self.start)
        for j in range(len(self.labels)):
            n=self.future[j,slot]
            self.waiting[j]+=n;self.pending[j]-=n;self.future[j,slot]=0.
        self.last=step

    def total(self,j):return self.waiting[j]+self.pending[j]

    def verify(self):
        for j in range(len(self.labels)):
            actual=math.fsum(primal(v) for v in self.future[j,:])
            if not math.isclose(primal(actual),primal(self.pending[j]),rel_tol=0,abs_tol=1e-8):
                raise ValueError('Aggregate time bins lost pending mass')
            if self.waiting[j]<-1e-8:raise ValueError('Negative aggregate waiting mass')


def _clock(state,cfg,local):
    start=local['last_step']+1
    end=round((state.time_sec+cfg.mpc.horizon_steps*cfg.simulation.T_c_sec)/cfg.simulation.T_u_sec)
    return start,max(0,end-start)


def routes(state,cfg):
    from evaluation.controllers import native_input_routes as legacy
    local=state.native_input_route_state
    if 'aggregate' not in local:
        inputs=legacy._inputs(cfg)
        labels=[(no,k) for no,row in inputs.items() for k in range(len(row['route_stages']))]
        start,steps=_clock(state,cfg,local)
        bins=TimeBins([(no,k,p) for no,k in labels for p in (0,1)],start,steps)
        q=dict.fromkeys(labels,0.)
        for c in local.pop('cohorts'):
            key=(c['input'],c['stage'])
            if c['queued']:q[key]+=c['vehicles']
            else:bins.add((*key,int(c.get('native_gate_passed',False))),c['due'],c['vehicles'])
        local['aggregate']=dict(bins=bins,queue=q)
    return local,local['aggregate'],legacy._inputs(cfg)


def _validate_tags(state,cfg,grouped,expected):
    for (kind,key),n in grouped.items():
        if not math.isfinite(primal(n)) or primal(n)<-1e-8:raise ValueError('Aggregate tag is negative/nonfinite')
        actual=(state.urban_movement_queue.get(key,0.) if kind=='queue' else
                cfg.network.urban_link_storage_veh[key]-state.urban_link_storage[key])
        if n>actual+1e-8:raise ValueError('Aggregate tags exceed physical '+kind+': '+key)
    if not math.isclose(primal(sum(grouped.values())),primal(expected),rel_tol=0,abs_tol=1e-8):
        raise ValueError('Aggregate tagged vehicle conservation failed')


def route_check(state,cfg):
    local,a,inputs=routes(state,cfg);b=a['bins'];grouped=defaultdict(float)
    for (no,k),n in a['queue'].items():
        stage=inputs[no]['route_stages'][k]
        grouped['queue',stage['movement']]+=n
        grouped['storage',stage['origin']]+=sum(b.total(b.index[no,k,p]) for p in (0,1))
    _validate_tags(state,cfg,grouped,local['initial_veh']+local['received_veh']-local['completed_veh'])
    if local['last_step']>=b.end-1:b.verify()


def route_generate(state,cfg,no,vehicles,step):
    from evaluation.controllers import native_input_routes as legacy
    local,a,inputs=routes(state,cfg)
    if no not in inputs:return False
    if local['last_step']!=step:raise ValueError('Aggregate generation clock mismatch')
    a['bins'].add((no,0,0),step+legacy._travel(state,cfg,inputs[no]['route_stages'][0]),vehicles)
    local['received_veh']+=vehicles;route_check(state,cfg);return True


def route_advance(state,cfg,step):
    from evaluation.controllers import native_input_routes as legacy
    from evaluation.controllers.control_area_objective import emit_transfer,get_ledger
    from src.models import urban_queue_model as uqm
    local,a,inputs=routes(state,cfg);b=a['bins'];b.advance(step)
    ledger=get_ledger(state);capture=ledger is not None and ledger.captures_response
    for no,k in a['queue']:
        stage=inputs[no]['route_stages'][k];gate=stage.get('native_fixed_gate')
        for phase in (0,1):
            j=b.index[no,k,phase];waiting=b.waiting[j]
            if waiting<=0:continue
            if gate and phase==0:
                start=step*cfg.simulation.T_u_sec
                green=legacy._first_native_green(gate,start,start+cfg.simulation.T_u_sec)
                if capture:
                    eligible=waiting if green is not None else 0.
                    ledger.record_resource_allocation('native_timing_eligibility',
                        'SC'+str(gate['controller'])+':SG'+str(gate['signal_group']),eligible,
                        {'input:'+no+':stage:'+str(k):eligible})
                if green is not None:
                    due=math.ceil(green/cfg.simulation.T_u_sec)+legacy._travel(state,cfg,stage,gate['post_gate_distance_m'])
                    b.waiting[j]=0.;b.add((no,k,1),due,waiting)
                continue
            movement,origin=stage['movement'],stage['origin']
            queue=state.urban_movement_queue.get(movement,0.)
            available=max(0.,uqm._queue_max(cfg,movement,cfg.network.urban_movements[movement])-queue)
            n=min(waiting,available)
            if capture:ledger.record_resource_allocation('native_route_queue_receiving','movement:'+movement,
                available,{'input:'+no+':stage:'+str(k):n})
            if n<=0:continue
            b.waiting[j]-=n;a['queue'][no,k]+=n
            state.urban_link_storage[origin]+=n;state.urban_movement_queue[movement]=queue+n
            emit_transfer(state,cfg,'storage:'+origin,'movement:'+movement,n,preserve_area=True)
    local['last_step']=step;route_check(state,cfg)
    return {'native_input_route_tagged_veh':sum(a['queue'].values())+sum(b.waiting)+sum(b.pending)}


def route_accept(state,cfg,movement,vehicles,step):
    from evaluation.controllers import native_input_routes as legacy
    from src.models import urban_queue_model as uqm
    local,a,inputs=routes(state,cfg);b=a['bins']
    keys=[key for key,n in a['queue'].items() if n>0 and inputs[key[0]]['route_stages'][key[1]]['movement']==movement]
    if not keys:return False
    if local['last_step']!=step:raise ValueError('Aggregate accepted route clock mismatch')
    before=state.urban_movement_queue.get(movement,0.)+vehicles
    if sum(a['queue'][key] for key in keys)>before+1e-8:raise ValueError('Aggregate queue overdraw')
    intermediate=0.
    for no,k in keys:
        accepted=vehicles*a['queue'][no,k]/before if before else 0.
        a['queue'][no,k]-=accepted
        if accepted>0 and k+1<len(inputs[no]['route_stages']):
            c=legacy._transit_cohort(no,k+1,accepted,step,state,cfg)
            b.add((no,k+1,0),c['due'],accepted);intermediate+=accepted
        else:local['completed_veh']+=accepted
    ordinary=max(0.,vehicles-intermediate);target=cfg.network.urban_movements[movement]['receiving_link']
    due=step+uqm._link_delay_steps(state,cfg,target)
    if ordinary:
        if target in uqm.approach_routing(cfg):uqm._schedule(state.urban_arrival_buffer,target,due,ordinary)
        uqm._schedule(state.urban_storage_release_buffer,target,due,ordinary)
    route_check(state,cfg);return True


def preheads(state,cfg):
    from evaluation.controllers import native_input_prehead as legacy
    local=state.native_input_prehead_state;inputs=legacy._inputs(cfg)
    if 'aggregate' not in local:
        labels=[];keys=[]
        for no,row in inputs.items():
            labels.append((no,None,'decision'))
            for tag in row['prehead_spec']['branches']:
                keys.append((no,tag));labels.extend([(no,tag,'approach'),(no,tag,'release')])
        start,steps=_clock(state,cfg,local);b=TimeBins(labels,start,steps)
        q=dict.fromkeys(keys,0.);blocked=dict.fromkeys(keys,0.)
        for c in local.pop('cohorts'):
            no,tag,n=c['input'],c['route'],c['vehicles']
            if c['stage']!='queue':b.add((no,tag,c['stage']),c['due'],n)
            elif not c['passed_first']:blocked[no,tag]+=n
            elif c['ready']<=start:q[no,tag]+=n
            else:b.add((no,tag,'release'),c['ready'],n)
        local['aggregate']=dict(bins=b,queue=q,blocked=blocked)
    return local,local['aggregate'],inputs


def prehead_check(state,cfg):
    local,a,inputs=preheads(state,cfg);b=a['bins'];grouped=defaultdict(float)
    for no,row in inputs.items():
        spec=row['prehead_spec'];grouped['storage',spec['origin']]+=b.total(b.index[no,None,'decision'])
        for tag,branch in spec['branches'].items():
            grouped['storage',spec['origin']]+=b.total(b.index[no,tag,'approach'])
            grouped['queue',branch['movement']]+=a['queue'][no,tag]+a['blocked'][no,tag]+b.total(b.index[no,tag,'release'])
    _validate_tags(state,cfg,grouped,local['initial_veh']+local['generated_veh']-local['departed_scope_veh'])
    if local['last_step']>=b.end-1:b.verify()


def prehead_generate(state,cfg,no,vehicles,step):
    from evaluation.controllers import native_input_prehead as legacy
    local,a,inputs=preheads(state,cfg)
    if no not in inputs:return False
    if local['last_step']!=step:raise ValueError('Aggregate pre-head generation clock mismatch')
    spec=inputs[no]['prehead_spec'];distance=sum(s['stop']-s['start'] for s in spec['segments_to_decision'])
    a['bins'].add((no,None,'decision'),legacy._due(state,cfg,spec['origin'],step,distance),vehicles)
    local['generated_veh']+=vehicles;prehead_check(state,cfg);return True


def prehead_advance(state,cfg,step):
    from evaluation.controllers import native_input_prehead as legacy
    from evaluation.controllers.control_area_objective import emit_transfer,get_ledger
    from src.models import urban_queue_model as uqm
    local,a,inputs=preheads(state,cfg);b=a['bins']
    if local['finished_step']!=step-1:raise ValueError('Aggregate first-head step incomplete')
    b.advance(step);local['last_step']=step;local['wn_actual']={}
    ledger=get_ledger(state);capture=ledger is not None and ledger.captures_response
    for no,row in inputs.items():
        spec=row['prehead_spec'];j=b.index[no,None,'decision'];n=b.waiting[j];b.waiting[j]=0.
        for tag,branch in spec['branches'].items():
            b.add((no,tag,'approach'),legacy._due(state,cfg,spec['origin'],step,spec['decision_to_head_m']),n*branch['probability'])
            release=b.index[no,tag,'release'];a['queue'][no,tag]+=b.waiting[release];b.waiting[release]=0.
            j=b.index[no,tag,'approach'];waiting=b.waiting[j]
            if waiting<=0:continue
            movement=branch['movement'];queue=state.urban_movement_queue.get(movement,0.)
            available=max(0.,uqm._queue_max(cfg,movement,cfg.network.urban_movements[movement])-queue)
            n_in=min(waiting,available)
            if capture:ledger.record_resource_allocation('native_prehead_queue_receiving','movement:'+movement,
                available,{'input:'+no+':route:'+str(tag):n_in})
            if n_in<=0:continue
            b.waiting[j]-=n_in
            target=a['blocked'] if movement==spec['left_movement'] else a['queue']
            target[no,tag]+=n_in
            state.urban_link_storage[spec['origin']]+=n_in;state.urban_movement_queue[movement]=queue+n_in
            emit_transfer(state,cfg,'storage:'+spec['origin'],'movement:'+movement,n_in,preserve_area=True)
    prehead_check(state,cfg)
    return {'native_prehead_tagged_veh':sum(a['queue'].values())+sum(a['blocked'].values())+sum(b.waiting)+sum(b.pending)}


def _blocked(a,inputs,movement):
    b=a['bins']
    return sum(n+b.total(b.index[no,tag,'release']) for (no,tag),n in a['blocked'].items()
               if inputs[no]['prehead_spec']['branches'][tag]['movement']==movement)


def prehead_limit(state,cfg,movement,available,intended,step):
    local,a,inputs=preheads(state,cfg)
    return min(intended,max(0.,available-_blocked(a,inputs,movement)))


def prehead_accept(state,cfg,movement,vehicles,step):
    local,a,inputs=preheads(state,cfg)
    if local['last_step']!=step:raise ValueError('Aggregate pre-head service clock mismatch')
    if any(movement in r['prehead_spec']['wn_movements'] for r in inputs.values()):
        local['wn_actual'][movement]=local['wn_actual'].get(movement,0.)+vehicles
    before=state.urban_movement_queue.get(movement,0.)+vehicles-_blocked(a,inputs,movement)
    if vehicles>before+1e-8:raise ValueError('Aggregate blocked head discharged early')
    for (no,tag),n in a['queue'].items():
        if inputs[no]['prehead_spec']['branches'][tag]['movement']!=movement:continue
        accepted=vehicles*n/before if before>0 else 0.
        a['queue'][no,tag]-=accepted;local['departed_scope_veh']+=accepted
    prehead_check(state,cfg)


def prehead_finish(state,control,cfg,step):
    from evaluation.controllers import native_input_prehead as legacy
    from evaluation.controllers.control_area_objective import get_ledger
    from src.models import urban_queue_model as uqm
    local,a,inputs=preheads(state,cfg);b=a['bins'];served=overdraw=0.
    if local['last_step']!=step or local['finished_step']!=step-1:raise ValueError('Aggregate head finish clock mismatch')
    ledger=get_ledger(state);capture=ledger is not None and ledger.captures_response
    for no,row in inputs.items():
        spec=row['prehead_spec'];reference=cfg.network.urban_movements[spec['capacity_reference_movement']]
        first=dict(reference,phase=spec['first_phase'])
        budget=uqm._phase_green_fraction(control,cfg,first,urban_step_index=step)*cfg.simulation.T_u_h*spec['physical_head_lanes']*uqm._movement_capacity_flow(control,cfg,spec['capacity_reference_movement'],reference)
        consumed=sum(local['wn_actual'].get(m,0.) for m in spec['wn_movements'])
        remaining=max(0.,budget-consumed);overdraw+=max(0.,consumed-budget)
        keys=[key for key in a['blocked'] if key[0]==no];total=sum(a['blocked'][key] for key in keys)
        accepted=min(total,remaining);sources={}
        for key in keys:
            n=accepted*a['blocked'][key]/total if total else 0.
            a['blocked'][key]-=n
            b.add((*key,'release'),legacy._due(state,cfg,spec['origin'],step,spec['interhead_distance_m']),n)
            source='input:'+no+':movement:'+spec['left_movement'];sources[source]=sources.get(source,0.)+n
        served+=accepted
        if capture:ledger.record_resource_allocation('residual_tag_service',spec['origin']+':'+spec['first_phase'],remaining,sources)
    local['first_head_service_veh']+=served;local['existing_wn_budget_overdraw_veh']+=overdraw
    local['finished_step']=step;prehead_check(state,cfg)
    return {'native_prehead_first_service_veh':served,'native_prehead_existing_wn_budget_overdraw_veh':overdraw}
