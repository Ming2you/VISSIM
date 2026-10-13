"""Finite route/stage inventories for the ordinary urban route corridors.

Arrival and route-choice motion use declared coarse bins; physical receipts,
shared head service and receiver acceptance keep the fine coupling clock.
This replaces cohort-order FIFO by proportional sharing among ready route
classes. Current routes/sources/head-passed tags are retained. It is a model
approximation, not an exact implementation optimization or native certificate.
"""
import math
from collections import defaultdict
from evaluation.controllers import route_choice_corridor as rc
from evaluation.controllers.sdmpc_aggregate_transport import IntervalBins, fraction

KEY='aggregate_routes'


def configure_branch_service(cfg,rates):
    """Bind declared physical branch budgets to the pickled corridor specs.

    Values are supplied calibration, not fitted from the current state. One
    group is shared by all its route/source tags; downstream and signal-head
    constraints still limit the accepted flow in advance_one.
    """
    if not isinstance(rates,dict):
        raise ValueError('Aggregate branch service requires a rate mapping')
    if not rates:return {}
    available={}
    for spec in rc._specs(cfg):
        for branch in spec['branches'].values():
            group='branch:'+branch['service_group']
            key=str(spec['decision'])+':'+group
            if key in available and available[key][0] is not spec:
                raise ValueError('Physical branch service has ambiguous decision ownership')
            available[key]=(spec,group)
    prepared=[]
    for key,rate in rates.items():
        if (key not in available or isinstance(rate,bool) or not isinstance(rate,(int,float))
                or not math.isfinite(rate) or rate<=0):
            raise ValueError('Unknown branch or invalid aggregate service rate')
        spec,group=available[key]
        existing=spec.get('aggregate_branch_service_veh_h',{})
        if group in existing and existing[group]!=rate:
            raise ValueError('Aggregate branch service was already configured differently')
        prepared.append((spec,group,rate))
    # Validate the complete declaration before changing any live spec.
    for spec,group,rate in prepared:
        spec.setdefault('aggregate_branch_service_veh_h',{})[group]=rate
    return dict(route_corridor_branch_service_veh_h=dict(rates))


def configure(cfg,tuning,state):
    dt=tuning.get('urban',{}).get('route_corridor_aggregate_step_sec')
    rates=tuning.get('urban',{}).get('route_corridor_branch_service_veh_h',{})
    if dt is None:
        if rates or rates is None:
            raise ValueError('Branch service requires the aggregate route clock')
        return {}
    if type(dt) is not int or dt not in (1,10):
        raise ValueError('Route aggregate requires explicit1s or10s arrivals')
    if getattr(cfg.network,'sdmpc_distance_reward',None):
        raise ValueError('Aggregate route distance accounting is not connected')
    if cfg.simulation.T_u_sec!=1 or cfg.simulation.T_f_sec!=1:
        raise ValueError('Route aggregate keeps fine physical receiving/service clocks')
    if not getattr(cfg.network,'route_choice_corridor',None):
        raise ValueError('Route aggregate needs verified corridor geometry')
    local=state.route_choice_corridor_state
    if KEY in local:raise ValueError('Route aggregate initialized twice')
    service_metadata=configure_branch_service(cfg,rates)
    obj=Routes(state,cfg,dt)
    local[KEY]=obj;local['cohorts']=[]
    cfg.network.route_corridor_aggregate_step_sec=dt
    rc._check(state,cfg.network.route_choice_corridor)
    return dict(route_corridor_aggregate_step_sec=dt,route_corridor_aggregate_classes=len(obj.bins.labels),
                **service_metadata)


class Routes:
    @staticmethod
    def label(c):
        return (c['storage'],c['stage'],c['route'],c['source'],
                c.get('native_service_passed'),tuple(c.get('possible_routes',())))

    def __init__(self,state,cfg,dt):
        rows=state.route_choice_corridor_state['cohorts']
        self.start=int(state.time_sec);self.dt=dt
        self.horizon=cfg.mpc.horizon_steps*cfg.simulation.T_c_sec
        if self.horizon%dt or cfg.simulation.T_c_sec%dt:
            raise ValueError('Route intervals must divide control and prediction horizon')
        labels={self.label(c) for c in rows};self.by_decision={};self.updates=0
        weights=defaultdict(float);speed_sum=defaultdict(float)
        for c in rows:
            n=c['vehicles'];weights[c['storage']]+=n;speed_sum[c['storage']]+=n*c['speed_kph']
        for spec in rc._specs(cfg):
            sources={c['source'] for c in rows if c['storage'] in spec['capacity_veh']}
            sources.update(spec['turns']);sources.update('generated_input:'+k for k in spec.get('generated_inputs',{}))
            if spec.get('shared_continuation'):sources.add('shared69:2')
            for source in sources:
                for gate in (None,False,True):
                    labels.add((spec['prefix_storage'],'prechoice',None,source,gate,()))
                    for route,branch in spec['branches'].items():
                        labels.add((spec['prefix_storage'],'prefix_tagged',route,source,gate,()))
                        if branch['mode']!='free_storage':
                            labels.add((spec['local_storage'],'local_tagged',route,source,None,()))
            # One physical service group cannot have inconsistent capacities.
            services={}
            for route,branch in spec['branches'].items():
                key='branch:'+branch['service_group'];rate=spec['per_lane_capacity_veh_h']*branch['lanes']
                rate=spec.get('aggregate_branch_service_veh_h',{}).get(key,rate)
                if key in services and services[key]!=rate:
                    raise ValueError('Aggregate route shared service has inconsistent branch capacities')
                services[key]=rate
        self.bins=IntervalBins(sorted(labels,key=repr),self.start,self.horizon,dt)
        stores=cfg.network.route_choice_corridor['capacity_veh']
        self.by_storage={s:[j for j,label in enumerate(self.bins.labels) if label[0]==s] for s in stores}
        self.speed={s:rc._speed(state,cfg,speed_sum[s]/weights[s] if weights[s] else None) for s in stores}
        for spec in rc._specs(cfg):
            self.by_decision[spec['decision']]=[j for j,label in enumerate(self.bins.labels) if label[0] in spec['capacity_veh']]
        for c in rows:self.add(c)
        self.bins.verify()

    def add(self,c):
        key=self.label(c)
        if key not in self.bins.index:raise ValueError('Aggregate route receipt outside compiled catalog')
        self.bins.add(key,c['due'],c['vehicles'])

    def stock(self,storage):return sum(self.bins.total(j) for j in self.by_storage[storage])

    def unknown(self):
        return sum(self.bins.total(j) for j,k in enumerate(self.bins.labels) if k[1]=='unknown')

    def begin(self,step):
        if (step-self.start)%self.dt==0:
            self.bins.advance(step);self.updates+=1
        if step==self.start+self.horizon-1:self.bins.verify()

    def change(self,j,amount):
        self.bins.waiting[j]+=amount
        if self.bins.waiting[j]<-1e-7:raise ArithmeticError('Aggregate route overdrew ready stock')

    def advance_one(self,state,control,cfg,step,spec):
        from src.models import urban_queue_model as uqm
        from evaluation.controllers.fixed_signal_schedule import _union_green_overlap
        indices=self.by_decision[spec['decision']]
        if (step-self.start)%self.dt==0:
            for j in indices:
                storage,stage,route,source,gate,possible=self.bins.labels[j]
                n=self.bins.waiting[j]
                if stage!='prechoice' or n<=0:continue
                self.change(j,-n)
                for route,branch in spec['branches'].items():
                    distance=branch['branch_position_m']-spec['decision_position_m']
                    due=rc._due(cfg,step,distance,self.speed[storage])
                    self.bins.add((storage,'prefix_tagged',route,source,gate,()),due,n*branch['share'])
        requests=[];transferred=defaultdict(float)
        for j in indices:
            storage,stage,route,source,gate,possible=self.bins.labels[j]
            amount=self.bins.waiting[j]
            if stage in ('prechoice','unknown') or amount<=0:continue
            branch=spec['branches'][route]
            if stage=='local_tagged' and branch['mode']=='typed_queue':
                movement=spec['local_movements'][route]
                self.change(j,-amount);state.urban_link_storage[storage]+=amount
                state.urban_movement_queue[movement]=state.urban_movement_queue.get(movement,0.)+amount
                rc.emit_transfer(state,cfg,'storage:'+storage,'movement:'+movement,amount,preserve_area=True)
                transferred['local_queue:'+route]+=amount
                continue
            exit_=spec['local_exits'].get(route) if stage=='local_tagged' else None
            target=exit_['target'] if exit_ else branch['destination']
            group='exit:'+exit_['connector'] if exit_ else 'branch:'+branch['service_group']
            rate=exit_['service_veh_h'] if exit_ else spec['per_lane_capacity_veh_h']*branch['lanes']
            if not exit_:
                rate=spec.get('aggregate_branch_service_veh_h',{}).get(group,rate)
            native=spec.get('native_fixed_service')
            if native and 'calibrated_service_veh_h' in native:rate=native['calibrated_service_veh_h']
            requests.append(dict(j=j,source=storage,route=route,target=target,group=group,
                amount=amount,capacity=rate*cfg.simulation.T_u_h,head=bool(native) and gate is not True,
                direct=bool(exit_) or branch['mode']=='free_storage'))
        if not requests:
            rc._check(state,spec);return dict(transferred)
        group_total=defaultdict(float);caps={}
        for r in requests:
            group_total[r['group']]+=r['amount'];caps[r['group']]=r['capacity']
        for r in requests:r['offer']=r['amount']*fraction(caps[r['group']],group_total[r['group']])
        native=spec.get('native_fixed_service');head_cap=None
        if native:
            start_sec=step*cfg.simulation.T_u_sec
            green=_union_green_overlap(rc._native_program(native),(native['signal_group'],),
                start_sec,start_sec+cfg.simulation.T_u_sec,native['controller_offset_sec'])
            head_cap=native.get('calibrated_service_veh_h',spec['per_lane_capacity_veh_h']*native['lanes'])*green/3600.
            scale=fraction(head_cap,sum(r['offer'] for r in requests if r['head']))
            for r in requests:
                if r['head']:r['offer']*=scale
        target_total=defaultdict(float)
        for r in requests:target_total[r['target']]+=r['offer']
        room={t:uqm._effective_available_space(state,cfg,t) for t in target_total}
        groups=defaultdict(dict);targets=defaultdict(dict);head_sources={};head_used=0.
        departed=0.
        for r in requests:
            n=r['offer']*fraction(room[r['target']],target_total[r['target']])
            j=r['j'];storage,stage,route,source,gate,possible=self.bins.labels[j]
            key=str(j)+':'+str(source)
            groups[r['group']][key]=n;targets[r['target']][key]=n
            if r['head']:head_sources[key]=n;head_used+=n
            if n<=0:continue
            self.change(j,-n);state.urban_link_storage[storage]+=n;state.urban_link_storage[r['target']]-=n
            rc.emit_transfer(state,cfg,'storage:'+storage,'storage:'+r['target'],n,preserve_area=True)
            transferred[r['group']]+=n;departed+=n
            if r['direct']:
                due=step+uqm._link_delay_steps(state,cfg,r['target'])
                uqm._schedule(state.urban_arrival_buffer,r['target'],due,n)
                uqm._schedule(state.urban_storage_release_buffer,r['target'],due,n)
            else:
                distance=rc._segments_distance(spec['local_travel_segments'][route][spec['local_connector']])
                due=rc._due(cfg,step,distance,self.speed[r['target']])
                self.bins.add((r['target'],'local_tagged',route,source,None,()),due,n)
        ledger=rc.get_ledger(state)
        if ledger is not None and ledger.captures_response:
            for key,sources in groups.items():ledger.record_resource_allocation('route_choice_branch_service',spec['decision']+':'+key,caps[key],sources)
            for target,sources in targets.items():ledger.record_resource_allocation('route_choice_receiving','storage:'+target,room[target],sources)
            if native:ledger.record_resource_allocation('native_fixed_head_service','SC'+str(native['controller'])+':SG'+str(native['signal_group']),head_cap,head_sources)
        local=state.route_choice_corridor_state;local['departed_veh']+=departed
        if native:local.setdefault('native_service_used_veh',{})[spec['decision']]=head_used
        rc._check(state,spec)
        return dict(transferred)
