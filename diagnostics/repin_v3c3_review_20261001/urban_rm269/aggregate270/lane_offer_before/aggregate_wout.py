"""Opt-in fixed-size lane/turn transport for the proved68/10681 corridor.

Transport/route choice/lateral movement advance on a coarse clock. Actual
external receipts remain on the existing fine coupling clock and debit the
same urban owner; neither extra vehicles nor a second cost owner is created.
The retained ramp boundary still resolves its finite receiving and head wave.
"""
import math
from collections import defaultdict
from evaluation.controllers import route_choice_corridor as rc
from evaluation.controllers.sdmpc_aggregate_transport import IntervalBins

KEY = 'aggregate_transport'


def configure(cfg, tuning, state):
    dt = tuning.get('urban', {}).get('known_wout_aggregate_step_sec')
    if dt is None:
        return {}
    if type(dt) is not int or dt not in (1, 10):
        raise ValueError('Aggregate W_out requires explicit1s or10s transport')
    spec = getattr(cfg.network, 'known_legsplit_routes', None)
    if not spec or not spec.get('causal_lane_response') or not spec.get('connector_queue_gate'):
        raise ValueError('Aggregate W_out requires the proved causal connector/lane boundary')
    if cfg.simulation.T_u_sec != 1 or cfg.simulation.T_f_sec != 1:
        raise ValueError('Aggregate port keeps the existing fine mainline/receipt clock')
    horizon = cfg.mpc.horizon_steps*cfg.simulation.T_c_sec
    if horizon%dt or cfg.simulation.T_c_sec%dt:
        raise ValueError('Aggregate updates must divide horizon and control interval')
    if getattr(cfg.network,'sdmpc_distance_reward',None):
        raise ValueError('Aggregate W_out distance accounting is not yet connected')
    local = state.known_legsplit_route_state
    if KEY in local:
        raise ValueError('Aggregate W_out initialization must occur once')
    obj = Wout(state, cfg, dt, int(horizon))
    local[KEY] = obj
    local['cohorts'] = []
    spec['aggregate_step_sec'] = dt
    obj.sync(state, cfg, int(state.time_sec))
    rc._known_check(state, cfg)
    return {'known_wout_aggregate_step_sec':dt, 'known_wout_aggregate_classes':len(obj.bins.labels)}


class Wout:
    def __init__(self, state, cfg, dt, horizon):
        spec = cfg.network.known_legsplit_routes
        geometry = spec['entry_lane_receiving']
        self.start = int(state.time_sec)
        self.dt = dt
        self.last_macro = None
        self.turns = tuple(sorted({'prechoice','unknown','free',*spec['future_choice_weights']}))
        places = [('68',str(l)) for l in geometry['road_capacity_veh']]
        places += [(c,str(l)) for c,e in geometry['connector_entries'].items() for l in e['lanes']]
        places += [('tail','0')]
        self.bins = IntervalBins([(p,l,t) for p,l in places for t in self.turns],self.start,horizon,dt)
        self.road_lanes = tuple(geometry['road_capacity_veh'])
        self.by_place = {(p,l):[self.bins.index[p,l,t] for t in self.turns] for p,l in places}
        self.departed_lanes = {l:0. for l in self.road_lanes}
        self.requested_lanes = {l:0. for l in self.road_lanes}
        self.actual_ramp_lanes = {l:0. for l in self.road_lanes}
        self.plan = None
        self.updates = 0
        # A stage's initial transport speed is its observed mass-weighted mean.
        # Later arrivals do not create extra speed/identity cohorts.
        speeds = defaultdict(float); weights = defaultdict(float)
        for c in state.known_legsplit_route_state['cohorts']:
            n=c['vehicles']; target=c['target']; due=c['due']
            if 'connector68' in c:
                tag=c['connector68']; place=tag['link']; due=tag['ready_step']
            elif 'lane68' in c and (target in (geometry['ramp'],'unknown','prechoice') or c.get('local68_queue') or self.start<c['lane68']['exit_step']):
                tag=c['lane68']; place='68'
            else:
                self.bins.add(('tail','0',target),due,n)
                continue
            if abs(sum(tag['shares'].values())-1.)>1e-8:
                raise ValueError('Aggregate seed lost physical lane fractions')
            for lane,share in tag['shares'].items():
                self.bins.add((place,lane,target),due,n*share)
            speeds[place]+=n*c.get('speed_kph',cfg.network.urban_avg_speed_km_h)
            weights[place]+=n
        self.speed = {p:rc._speed(state,cfg,speeds[p]/weights[p] if weights[p] else None) for p,l in places}
        self.check_capacity(cfg)

    def stock(self, place=None, lane=None):
        if place is None:
            return sum(self.bins.waiting)+sum(self.bins.pending)
        return sum(self.bins.total(j) for (p,l),ix in self.by_place.items()
                   if p==place and (lane is None or lane==l) for j in ix)

    def ready(self, place, lane, target):
        return self.bins.waiting[self.bins.index[place,lane,target]]

    def change_ready(self, place, lane, target, amount):
        j=self.bins.index[place,lane,target]
        self.bins.waiting[j]+=amount
        if self.bins.waiting[j]<-1e-7:
            raise ArithmeticError('Aggregate transport overdrew stage-ready stock')

    def check_capacity(self, cfg):
        g=cfg.network.known_legsplit_routes['entry_lane_receiving']
        for lane,cap in g['road_capacity_veh'].items():
            if self.stock('68',lane)>cap+1e-7:
                raise ArithmeticError('Aggregate68 stock exceeds its own lane capacity')
        for c,entry in g['connector_entries'].items():
            for lane in entry['lanes']:
                if self.stock(c,str(lane))>entry['capacity_per_lane_veh']+1e-7:
                    raise ArithmeticError('Aggregate connector exceeds its own lane capacity')

    def eligible(self, cfg):
        g=cfg.network.known_legsplit_routes['entry_lane_receiving']
        return (sum(self.ready('68',l,g['ramp']) for l in g['ramp_lanes'])
                +sum(self.ready('tail','0',t) for t in self.turns if t not in ('unknown','prechoice')))

    def sync(self, state, cfg, step):
        # Only a compatibility availability alias. Detailed ETA is held once in
        # bins; physically retained connector/road waiting is not an exit queue.
        n=self.stock()-self.eligible(cfg)
        if n < -1e-7:raise ArithmeticError('Aggregate eligible stock exceeds owner')
        storage=cfg.network.known_legsplit_routes['storage']
        state.urban_storage_release_buffer[storage]={step+1:max(0.,n)}

    def _due(self, cfg, step, distance, place):
        return rc._due(cfg,step,max(0.,distance),self.speed[place])

    def advance(self, state, cfg, step):
        if (step-self.start)%self.dt:
            self.sync(state,cfg,step)
            return
        if self.last_macro is not None and step!=self.last_macro+self.dt:
            raise ValueError('Aggregate transport clock is noncontiguous')
        self.bins.advance(step)
        spec=cfg.network.known_legsplit_routes;g=spec['entry_lane_receiving'];ramp=g['ramp']
        before=self.stock();ledger=rc.get_ledger(state)
        # Current prechoice stock branches once, without redrawing known routes.
        for lane in self.road_lanes:
            n=self.ready('68',lane,'prechoice')
            self.change_ready('68',lane,'prechoice',-n)
            for target,weight in spec['future_choice_weights'].items():
                if weight<=0:continue
                stop=(g['road_length_m'] if target!=ramp else spec['physical_travel']['destinations'][target][0]['stop'])
                due=self._due(cfg,step,stop-spec['choice_position_m'],'68')
                self.bins.add(('68',lane,target),due,n*weight)
        # Simultaneous bounded lateral movement, using actual previous-window
        # departures once, not accumulated unused opportunity credits.
        moves=[];room={l:max(0.,c-self.stock('68',l)) for l,c in g['road_capacity_veh'].items()}
        for source,target in (('3','2'),('4','3')):
            n=self.ready('68',source,ramp);cap=g['road_capacity_veh'][target]
            probability=-math.expm1(-spec['lateral_access_rate_per_sec']*self.dt*min(1.,room[target]/cap))
            offer=max(n*probability,min(n,self.departed_lanes[target]))
            accepted=min(room[target],offer);moves.append((source,target,accepted))
            if ledger is not None and ledger.captures_response:
                ledger.record_resource_allocation('known_wout_lateral_receiving','68:'+target,room[target],{'lane:68:'+source:accepted})
        for source,target,n in moves:
            self.change_ready('68',source,ramp,-n);self.change_ready('68',target,ramp,n)
        # Aggregate partial FIFO: actual admission fraction of the previous
        # interval opens the blocked part; independent lanes stay independent.
        passed_by_lane={l:0. for l in self.road_lanes}
        for lane in self.road_lanes:
            coverage=min(1.,self.ready('68',lane,ramp))
            asked=self.requested_lanes[lane]
            fraction=min(1.,self.actual_ramp_lanes[lane]/asked) if asked>0 else 0.
            if lane not in g['ramp_lanes']:fraction=0.
            for target in ('free','RM_C10646'):
                passed=self.ready('68',lane,target)*(1.-coverage*(1.-fraction))
                self.change_ready('68',lane,target,-passed)
                passed_by_lane[lane]+=passed
                distance=rc._known_remaining(spec['physical_travel']['destinations'][target],'68',g['road_length_m'])
                self.bins.add(('tail','0',target),self._due(cfg,step,distance,'68'),passed)
        # Connector lanes share the destination lane's actual finite room.
        for lane in self.road_lanes:
            donors=[(c,t) for c,e in g['connector_entries'].items() if int(lane) in e['lanes'] for t in self.turns]
            total=sum(self.ready(c,lane,t) for c,t in donors)
            space=max(0.,g['road_capacity_veh'][lane]-self.stock('68',lane))
            scale=rc._known_receiving_fraction(space,total)
            accepted_by_source=defaultdict(float)
            for c,target in donors:
                n=self.ready(c,lane,target)*scale
                self.change_ready(c,lane,target,-n)
                position=g['connector_entries'][c]['position_m']
                stop=(spec['choice_position_m'] if target=='prechoice' else
                      g['road_length_m'] if target!=ramp else spec['physical_travel']['destinations'][target][0]['stop'])
                self.bins.add(('68',lane,target),self._due(cfg,step,stop-position,'68'),n)
                accepted_by_source['connector:'+c]+=n
            if ledger is not None and ledger.captures_response:
                ledger.record_resource_allocation('known_wout_connector_to_road','68:'+lane,space,dict(accepted_by_source))
        self.departed_lanes=passed_by_lane
        self.requested_lanes={l:self.ready('68',l,ramp) for l in self.road_lanes}
        self.actual_ramp_lanes={l:0. for l in self.road_lanes}
        if abs(before-self.stock())>1e-7:raise ArithmeticError('Aggregate internal transport lost vehicles')
        self.check_capacity(cfg)
        self.last_macro=step;self.updates+=1
        self.sync(state,cfg,step)
        rc._known_check(state,cfg)

    def entry_limits(self,state,cfg,intended,step):
        spec=cfg.network.known_legsplit_routes;g=spec['entry_lane_receiving']
        requests=defaultdict(dict);result=dict(intended);lanes_by_source=defaultdict(dict)
        for m,lanes in g['incoming'].items():
            if m not in intended:continue
            result[m]=0.
            for l in lanes:requests[spec['incoming_movements'][m],str(l)][m]=intended[m]/len(lanes)
        ledger=rc.get_ledger(state)
        for (c,l),sources in requests.items():
            room=max(0.,g['connector_entries'][c]['capacity_per_lane_veh']-self.stock(c,l))
            factor=rc._known_receiving_fraction(room,sum(sources.values()))
            accepted={m:n*factor for m,n in sources.items()}
            for m,n in accepted.items():result[m]+=n;lanes_by_source[m][l]=n
            if ledger is not None and ledger.captures_response:
                ledger.record_resource_allocation('known_wout_connector_receiving',c+':'+l,room,{'movement:'+m:n for m,n in accepted.items()})
        local=state.known_legsplit_route_state
        local['entry_lane_shares']={m:{l:n/result[m] for l,n in row.items()} for m,row in lanes_by_source.items() if result[m]>0}
        local['entry_lane_step']=step
        return result

    def receive(self,row,state,cfg,step):
        if 'connector68' in row:
            tag=row['connector68']
            for l,share in tag['shares'].items():self.bins.add((tag['link'],l,row['target']),tag['ready_step'],row['vehicles']*share)
        else:self.bins.add(('tail','0',row['target']),row['due'],row['vehicles'])
        self.sync(state,cfg,step)
        self.check_capacity(cfg)

    def requests(self,state,cfg,step):
        if self.plan is not None:raise ValueError('Uncommitted aggregate W_out request')
        g=cfg.network.known_legsplit_routes['entry_lane_receiving'];ramp=g['ramp']
        rows={('68',l,ramp):self.ready('68',l,ramp) for l in g['ramp_lanes']}
        rows.update({('tail','0',t):self.ready('tail','0',t) for t in self.turns if t not in ('prechoice','unknown')})
        requests={t:sum(n for (_,_,target),n in rows.items() if t==target) for t in self.turns if t not in ('prechoice','unknown')}
        counts=[self.ready('68',l,ramp) for l in g['ramp_lanes']]
        total=sum(counts)
        if total>0:
            state.lane_ramp_runtime.buffers[ramp].lane_arrival_shares=tuple(n/total for n in counts)
        self.plan=dict(step=step,rows=rows,requests=requests)
        return requests

    def commit(self,state,cfg,receipts,step):
        spec=cfg.network.known_legsplit_routes;g=spec['entry_lane_receiving']
        actual=defaultdict(float)
        for source,target,n in receipts:
            if source==spec['storage']:actual[target or 'free']+=n
        if self.plan is None:
            if sum(actual.values())>1e-9:raise ValueError('Aggregate receipt without offer')
        else:
            if self.plan['step']!=step:raise ValueError('Stale aggregate transfer receipt')
            for t,n in actual.items():
                if n<0 or n>self.plan['requests'].get(t,0.)+1e-7:raise ValueError('Aggregate accepted more than requested')
            for (p,l,t),n in self.plan['rows'].items():
                total=self.plan['requests'][t]
                debit=n*(actual[t]/total) if total else 0.
                self.change_ready(p,l,t,-debit)
                if p=='68':
                    self.departed_lanes[l]+=debit
                    self.actual_ramp_lanes[l]+=debit
        state.known_legsplit_route_state['departed']+=sum(actual.values())
        self.plan=None
        self.sync(state,cfg,step)
        rc._known_check(state,cfg)
