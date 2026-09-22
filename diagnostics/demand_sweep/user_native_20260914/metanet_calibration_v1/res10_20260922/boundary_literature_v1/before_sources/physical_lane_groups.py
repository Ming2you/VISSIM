"""Opt-in conserved mainline lane groups for component-model qualification.

Uses the installed METANET FD and speed equations. No capacity bonus or reward.
Only an explicitly supplied current snapshot / past exchange profile enables it;
the production coupled model does not infer these states from aggregate means.
"""
from __future__ import annotations
import copy
import math


def hadi_receiving_vph(rho, jam, critical, capacity, wave, theta, *, capacity_critical=False):
    """Rate PER LANE, before physical space cap.

    Optional Wang--Niu Eq4 ties the congested wave to Q'/(jam-critical).
    Neither law changes physical jam storage or rewards a control command.
    """
    if (any(not math.isfinite(x) for x in (rho,jam,critical,capacity,wave,theta))
            or rho<0 or not 0<critical<jam or min(capacity,wave)<=0 or not 0<=theta<1):
        raise ValueError('Invalid Hadiuzzaman receiving parameters')
    reduced=capacity*(1.-theta if rho>critical else 1.)
    if capacity_critical and rho>critical:wave=reduced/(jam-critical)
    return max(0.,min(reduced,wave*(jam-rho)))


def hadi_desired_speed(fd_target, command, mode, active):
    """Eq8. command uses ONE law for nominal and reduced VSL commands.

    paper_switch diagnoses Eq3/Eq8 switching, which can increase desired
    speed at activation independently of any physical control benefit.
    """
    if mode=='command' or (mode=='paper_switch' and active):return command
    if mode in ('fd_cap','paper_switch'):return fd_target
    raise ValueError('Unknown Hadiuzzaman relaxation mode')


def receiving_limited_speed(predicted, previous, requested, accepted, seconds, reaction_seconds):
    """Diagnostic response to an already allocated downstream receiving limit.

    Does not alter fluxes or create capacity. It is a closure to validate, not
    an identity between local mean speed and a cell-boundary crossing rate.
    """
    values=(predicted,previous,requested,accepted,seconds,reaction_seconds)
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in values) or seconds<=0:
        raise ValueError('Invalid receiving-speed response operands')
    if accepted>requested+1e-7:raise ValueError('Accepted through flow exceeds requested flow')
    if not requested or accepted>=requested-1e-12:return predicted
    target=min(predicted,previous*accepted/requested)
    gain=1. if reaction_seconds==0 else -math.expm1(-seconds/reaction_seconds)
    return predicted+gain*(target-predicted)


def junction_mean_speed(flow, velocity_moment, fallback):
    """Eq9 virtual inlet, using accepted entering amounts (common dt)."""
    if any(not math.isfinite(x) or x<0 for x in (flow,velocity_moment,fallback)):
        raise ValueError('Invalid junction flow/speed')
    return velocity_moment/flow if flow else fallback


def junction_downstream_density(densities):
    """Eq10 virtual outlet. An empty set/zero-density outlets give zero."""
    if any(not math.isfinite(x) or x<0 for x in densities):
        raise ValueError('Invalid junction density')
    return sum(x*x for x in densities)/sum(densities) if sum(densities) else 0.


def off_operational_factors(widths, access, stock, capacity, gamma, b):
    """Exact smooth Eq22 one-lane loss, allocated to exit-accessible groups.

    These are sending-width factors, NOT physical storage widths. Retained
    vehicles still occupy the same road and cannot disappear with a lane loss.
    Unlike the legacy helper there is no forced jump at stock==capacity.
    """
    if (len(widths)!=len(access) or any(not math.isfinite(x) or x<=0 for x in widths)
            or any(not math.isfinite(x) or x<0 for x in access)
            or not math.isfinite(stock) or stock<0
            or any(not math.isfinite(x) or x<=0 for x in (capacity,gamma,b))):
        raise ValueError('Invalid off-ramp operational-width inputs')
    available=sum(w for w,a in zip(widths,access) if a>0)
    if available<1.:raise ValueError('Eq22 requires at least one exit-accessible lane')
    loss=-math.expm1(-((stock/(gamma*capacity))**b)/b)
    return [1.-loss/available if a>0 else 1. for a in access]


def lane_entry_speed_loss(requests, speeds, before, after, gamma):
    """Extra recipient-follower loss, separate from advected vehicle momentum.

    Only accepted slower entrants can impose this loss. Empty recipient lanes
    have no existing follower to disrupt. The coefficient is fitted to native
    follower events, not to the sign of a controller objective difference.
    """
    return [gamma*sum(row[k]*max(0.,speeds[k]-speeds[g]) for g,row in enumerate(requests))/after[k]
            if before[k]>0 and after[k]>0 else 0. for k in range(len(speeds))]


def advected_speed(stock, speed, outgoing, incoming_moment, new_stock):
    """Vehicle-weighted velocity after accepted longitudinal transfers."""
    if outgoing > stock+1e-7 or min(stock, outgoing, new_stock, incoming_moment) < -1e-7:
        raise ArithmeticError('Invalid mass for speed advection')
    return ((max(0.,stock-outgoing)*speed+incoming_moment)/new_stock
            if new_stock>1e-9 else speed)


class StateDependentExchange:
    """Bounded empirical hazards from current traffic state, with no lever bonus."""
    feature_names = ['donor_speed','recipient_minus_donor_speed','donor_density','recipient_density']

    def __init__(self, model, widths):
        self.model = copy.deepcopy(model)
        if (not isinstance(model,dict) or model.get('schema')!='state-dependent-exchange/v1'
                or model.get('feature_names')!=self.feature_names):
            raise ValueError('Unknown state-dependent exchange schema / features')
        for name in ['center','scale','lower','upper','coefficients']:
            values=model.get(name)
            if not isinstance(values,list) or len(values)!=4 or any(
                    isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in values):
                raise ValueError('Invalid exchange feature coefficients / domain')
        if any(x<=0 for x in model['scale']) or any(a>=b for a,b in zip(model['lower'],model['upper'])):
            raise ValueError('Invalid exchange feature scale or bounds')
        expected={f'{i}:{g}:{k}' for i,ws in enumerate(widths)
                  for g in range(len(ws)) for k in range(len(ws)) if abs(g-k)==1}
        intercepts=model.get('log_intercepts')
        if not isinstance(intercepts,dict) or set(intercepts)!=expected or any(
                isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in intercepts.values()):
            raise ValueError('Missing or invalid exchange address intercepts')
        cap=model.get('max_rate_per_sec')
        if isinstance(cap,bool) or not isinstance(cap,(int,float)) or not math.isfinite(cap) or cap<=0:
            raise ValueError('Invalid exchange hazard bound')
        self.clipped_feature_values=0
        self.feature_values=0

    def rates(self, stocks, speeds, lengths, widths):
        m=self.model
        result=[[[0.]*len(ws) for _ in ws] for ws in widths]
        for i,ws in enumerate(widths):
            rho=[n/(lengths[i]*w) for n,w in zip(stocks[i],ws)]
            for g in range(len(ws)):
                for k in range(len(ws)):
                    if abs(g-k)!=1:continue
                    raw=[speeds[i][g],speeds[i][k]-speeds[i][g],rho[g],rho[k]]
                    if any(not math.isfinite(x) for x in raw):raise ValueError('Nonfinite exchange state')
                    bounded=[min(b,max(a,x)) for a,b,x in zip(m['lower'],m['upper'],raw)]
                    self.clipped_feature_values+=sum(a!=b for a,b in zip(raw,bounded))
                    self.feature_values+=len(raw)
                    value=m['log_intercepts'][f'{i}:{g}:{k}']+sum(
                        beta*(x-c)/s for beta,x,c,s in zip(m['coefficients'],bounded,m['center'],m['scale']))
                    result[i][g][k]=math.exp(min(math.log(m['max_rate_per_sec']),value))
        return result


class PhysicalLaneGroups:
    def __init__(self, spec, state, cfg, accounting, *, exchange_model=None, interruption_gamma=None,
                 destination_policy=None, momentum_advection=False, port_travel=None,
                 position_aware_initial=False, upstream_exit_inventory=None, ramp_conflict_through_inventory=None,
                 branch_partition=None, partition_exchange=False, partition_speed_context=False):
        self.spec = copy.deepcopy(spec)
        self.a = accounting
        self.road = spec['road']
        self.port_response=copy.deepcopy((getattr(cfg.network,'freeway_port_response',{}) or {}).get(self.road,{}))
        self.port_response_rows=[]
        if self.port_response:
            if set(self.port_response)!={'merge_speed','diverge_density','spillback'}:
                raise ValueError('Explicit complete port-response switches required')
            if any(type(self.port_response[k]) is not bool for k in ('merge_speed','diverge_density')):
                raise ValueError('Junction switches must be boolean')
            spill=self.port_response['spillback']
            if spill is not None and (not isinstance(spill,dict) or set(spill)!={'mode','gamma','b'}
                    or spill['mode'] not in ('replace_fifo','envelope')
                    or any(isinstance(spill[k],bool) or not isinstance(spill[k],(int,float))
                           or not math.isfinite(spill[k]) or spill[k]<=0 for k in ('gamma','b'))):
                raise ValueError('Invalid operational spillback response')
        self.widths = spec['widths']
        self.matrices = spec['matrices']
        self.rates = spec['exchange_rates_per_sec']
        self.lengths = accounting.cell_lengths_km(cfg, self.road, len(self.widths))
        self.dt = cfg.simulation.T_f_h
        self.sec = cfg.simulation.T_f_sec
        self.hadi=copy.deepcopy((getattr(cfg.network,'freeway_hadiuzzaman',{}) or {}).get(self.road))
        self.vsl_fd_response=copy.deepcopy((getattr(cfg.network,'freeway_vsl_fd_response',{}) or {}).get(self.road))
        self.receiving_speed_response=copy.deepcopy((getattr(cfg.network,'freeway_receiving_speed_response',{}) or {}).get(self.road))
        if self.receiving_speed_response is not None:
            if not isinstance(self.receiving_speed_response,dict) or set(self.receiving_speed_response)!={'reaction_seconds'}:
                raise ValueError('Explicit receiving-speed reaction time required')
            receiving_limited_speed(1.,1.,1.,1.,self.sec,self.receiving_speed_response['reaction_seconds'])
            if self.hadi is None or not self.hadi.get('ctm'):
                raise ValueError('Receiving-speed response requires the explicit receiving model')
        if self.vsl_fd_response is not None:
            from evaluation.controllers.freeway_fd import literature_vsl_parameters
            literature_vsl_parameters(self.vsl_fd_response,100.,30.,2.,100.,120.)
            if getattr(cfg.network,'vsl_fd_two_branch',False):
                raise ValueError('Literature exponential FD cannot also use two-branch FD')
        self.hadi_audit=None
        if self.hadi is not None:
            if (not {'ctm','relaxation','cells'}<=set(self.hadi)
                    or set(self.hadi)-{'ctm','relaxation','cells','relaxation_cells','congested_branch'}
                    or self.hadi.get('congested_branch','fixed_wave') not in ('fixed_wave','capacity_critical')
                    or type(self.hadi['ctm']) is not bool
                    or self.hadi['relaxation'] not in ('fd_cap','command','paper_switch')
                    or len(self.hadi['cells'])!=len(self.widths)):
                raise ValueError('Explicit complete Hadiuzzaman configuration required')
            scope=self.hadi.get('relaxation_cells',list(range(len(self.widths))))
            if len(set(scope))!=len(scope) or any(type(i) is not int or not 0<=i<len(self.widths) for i in scope):
                raise ValueError('Invalid fixed VSL-equipped cell scope')
            self.hadi_scope=set(scope)
            for row in self.hadi['cells']:
                if set(row)!={'capacity_vphpl','wave_kmh','rho_critical','theta'}:
                    raise ValueError('Explicit per-cell receiving coefficients required')
                hadi_receiving_vph(0,cfg.network.rho_max,row['rho_critical'],row['capacity_vphpl'],row['wave_kmh'],row['theta'])
            self.hadi_audit=dict(receiving_steps=0,limited_group_steps=0,accepted_veh=0.,
                max_budget_violation_veh=0.,desired_calls=0,desired_changed=0,
                max_target_increase_kmh=0.,origin_wait_veh_h=0.,boundaries={})
        self.ramp_conflict_through_inventory=set(ramp_conflict_through_inventory or ())
        if self.ramp_conflict_through_inventory:
            if port_travel is None or self.ramp_conflict_through_inventory-set(spec['ramp_access']):
                raise ValueError('Through-inventory conflict requires physical ramp origin stocks and port lengths')
            for ramp in self.ramp_conflict_through_inventory:
                i=spec['ramp_access'][ramp]['cell']
                if sum(p['cell']==i for p in spec['ramp_access'].values())!=1:
                    raise ValueError('Through-inventory conflict supports one merge per cell')
                merge_distance=self.lengths[i]-port_travel['ramp_remaining_km'][ramp]
                if any(port_travel['off_distance_km'][o]>=merge_distance for o,p in spec['off_access'].items() if p['cell']==i):
                    raise ValueError('Excluded off-ramp destinations must leave before this merge')
        net = cfg.network
        if spec['schema'] != 'physical-mainline-lane-groups/v1':
            raise ValueError('Unknown lane-group schema')
        if spec['observation_end_s'] != state.time_sec:
            raise ValueError('Lane groups must be observed at the forecast cutoff')
        if getattr(net, 'freeway_buffer_segments', 0) or getattr(net, 'offramp_route_inventory', None):
            raise ValueError('Lane-group component does not support external buffers / another route inventory')
        if float(getattr(net,'capacity_drop_discharge_phi',1.)) != 1.:
            raise ValueError('Lane-group candidate has no additional capacity-drop closure')
        self.n, self.v = [], []
        for i,ws in enumerate(self.widths):
            if any(not math.isfinite(w) or w <= 0 for w in ws):
                raise ValueError('Invalid group width')
            if abs(sum(ws)-state.freeway_effective_lanes[self.road][i]) > 1e-8:
                raise ValueError('Group widths disagree with physical geometry')
            rows = spec['initial_groups'][i]
            if len(rows) != len(ws): raise ValueError('Incomplete group snapshot')
            n = [float(r['n_veh']) for r in rows]
            v = [float(r['v_kmh']) if r['v_kmh'] is not None else state.freeway_speed[self.road][i] for r in rows]
            if any(not math.isfinite(x) or x < 0 for x in n+v): raise ValueError('Invalid group snapshot')
            aggregate = state.freeway_density[self.road][i]*self.lengths[i]*sum(ws)
            if abs(sum(n)-aggregate) > 1e-7: raise ValueError('Initial lane/aggregate stock mismatch')
            if sum(n) and abs(sum(a*b for a,b in zip(n,v))/sum(n)-state.freeway_speed[self.road][i]) > 1e-7:
                raise ValueError('Initial lane/aggregate speed mismatch')
            self.n.append(n);self.v.append(v)
            rate = self.rates[i]
            if len(rate)!=len(ws) or any(len(r)!=len(ws) for r in rate): raise ValueError('Exchange matrix shape')
            if any(not math.isfinite(x) or x<0 for r in rate for x in r): raise ValueError('Exchange rate')
        if len(self.matrices)!=len(self.widths)-1: raise ValueError('Incomplete longitudinal topology')
        for i,matrix in enumerate(self.matrices):
            if len(matrix)!=len(self.widths[i]) or any(len(r)!=len(self.widths[i+1]) for r in matrix):
                raise ValueError('Longitudinal matrix shape')
            if any(any(not math.isfinite(x) or x<0 for x in r) or sum(r)>1.+1e-9 for r in matrix):
                raise ValueError('Invalid longitudinal lane mapping')
        for key,expected in [('ramp_access',net.ramps),('off_access',net.off_ramps)]:
            if set(spec[key])!=set(expected):raise ValueError('Incomplete physical port access')
            for port,access in spec[key].items():
                i=access['cell'];weights=access['weights']
                if len(weights)!=len(self.widths[i]) or sum(weights)<=0 or any(x<0 for x in weights):
                    raise ValueError('Invalid port group access')
        # Branch destinations persist until that branch actually accepts them.
        # Initial labels and arriving labels are inferred from past branch ratios,
        # not from a future trajectory or a current vehicle route oracle.
        self.off = {o:[0.]*len(self.n[p['cell']]) for o,p in spec['off_access'].items()}
        self.initialized_destinations = False
        self.rows = []
        self.max_residual = 0.
        self.exchange_model = StateDependentExchange(exchange_model,self.widths) if exchange_model is not None else None
        if interruption_gamma is not None and (isinstance(interruption_gamma,bool)
                or not isinstance(interruption_gamma,(float,int)) or not math.isfinite(interruption_gamma)
                or not 0<=interruption_gamma<=1):
            raise ValueError('Lane-entry interruption coefficient must be finite in0..1')
        self.interruption_gamma=interruption_gamma
        if destination_policy not in (None, 'prefer_exit', 'clear_ending_lane'):
            raise ValueError('Unknown physical lane destination policy')
        if destination_policy == 'clear_ending_lane' and interruption_gamma is not None:
            raise ValueError('Mandatory lane transfer/follower loss combination is not qualified')
        self.destination_policy = destination_policy
        if type(momentum_advection) is not bool:
            raise ValueError('Velocity moment advection must be boolean')
        self.momentum_advection = momentum_advection
        self.port_travel = copy.deepcopy(port_travel)
        self.ramp_origin = {}
        if type(position_aware_initial) is not bool or (position_aware_initial and port_travel is None):
            raise ValueError('Position-aware branch initialization requires port travel geometry')
        self.initial_off_eligible = copy.deepcopy(spec['initial_off_eligible']) if position_aware_initial else None
        if port_travel is not None:
            if (set(port_travel) != {'ramp_remaining_km','off_distance_km'}
                    or set(port_travel['ramp_remaining_km']) != set(spec['ramp_access'])
                    or set(port_travel['off_distance_km']) != set(spec['off_access'])):
                raise ValueError('Incomplete within-cell port geometry')
            self.ramp_origin = copy.deepcopy(spec['initial_ramp_origin'])
            if set(self.ramp_origin) != set(spec['ramp_access']):
                raise ValueError('All current same-cell ramp origins must be observed')
            for r, p in spec['ramp_access'].items():
                i=p['cell'];values=self.ramp_origin[r];length=port_travel['ramp_remaining_km'][r]
                if (len(values)!=len(self.n[i]) or any(not math.isfinite(x) or x<0 for x in values)
                        or not 0 < length <= self.lengths[i]):
                    raise ValueError('Invalid ramp origin stock/remaining length')
            for o,p in spec['off_access'].items():
                if not 0 < port_travel['off_distance_km'][o] <= self.lengths[p['cell']]:
                    raise ValueError('Invalid off-ramp within-cell distance')
            for i,ns in enumerate(self.n):
                for g,n in enumerate(ns):
                    if sum(v[g] for r,v in self.ramp_origin.items() if spec['ramp_access'][r]['cell']==i)>n+1e-7:
                        raise ValueError('Ramp-origin tags exceed current group stock')
        if self.initial_off_eligible is not None:
            if set(self.initial_off_eligible)!=set(self.off):
                raise ValueError('Current pre-exit stock required for every off-ramp')
            for o,values in self.initial_off_eligible.items():
                i=spec['off_access'][o]['cell']
                if len(values)!=len(self.n[i]):raise ValueError('Pre-exit stock group shape')
                for g,n in enumerate(values):
                    origins=sum(v[g] for r,v in self.ramp_origin.items() if spec['ramp_access'][r]['cell']==i)
                    if not math.isfinite(n) or n<0 or n+origins>self.n[i][g]+1e-7:
                        raise ValueError('Pre-exit stock contradicts current stock / downstream ramp origins')
        # First-exit intent is a subset of the existing physical vehicles. Its
        # source fraction is configured routing, not the observed served ratio.
        self.upstream_exit_inventory = copy.deepcopy(upstream_exit_inventory or {})
        if (not isinstance(self.upstream_exit_inventory,dict) or len(self.upstream_exit_inventory)>1
                or (self.upstream_exit_inventory and self.initial_off_eligible is None)):
            raise ValueError('First-exit inventory requires a single port and current pre-exit positions')
        self.upstream_off = {};self.intent_access = {}
        self.intent_initial = {};self.intent_entered = {};self.intent_exited = {}
        self.max_intent_residual = 0.
        for o,beta in self.upstream_exit_inventory.items():
            if (o not in self.off or isinstance(beta,bool) or not isinstance(beta,(int,float))
                    or not math.isfinite(beta) or not 0<=beta<=1):
                raise ValueError('Invalid first-exit source fraction')
            stop=spec['off_access'][o]['cell']
            if (stop<=0 or any(p['cell']<=stop for key,p in spec['off_access'].items() if key!=o)
                    or any(p['cell']<stop for p in spec['ramp_access'].values())
                    or any(abs(sum(row)-1.)>1e-8 for matrix in self.matrices[:stop] for row in matrix)):
                raise ValueError('Only the first exit, before intervening ports or ending lanes, is supported')
            access=[None]*(stop+1);access[stop]=[bool(w) for w in spec['off_access'][o]['weights']]
            for i in range(stop-1,-1,-1):
                access[i]=[any(w and access[i+1][k] for k,w in enumerate(row)) for row in self.matrices[i]]
            self.intent_access[o]=access
            self.upstream_off[o]=[[0.]*len(ns) for ns in self.n[:stop]]
            for i in range(stop+1):
                eligible=self.initial_off_eligible[o] if i==stop else self.n[i]
                stock=self.off[o] if i==stop else self.upstream_off[o][i]
                needed=beta*sum(eligible)
                for reachable in (True,False):
                    indices=[g for g,x in enumerate(access[i]) if x==reachable]
                    total=sum(eligible[g] for g in indices);take=min(needed,total)
                    for g in indices:stock[g]=take*eligible[g]/total if total else 0.
                    needed-=take
            self.intent_initial[o]=sum(map(sum,self.upstream_off[o]))+sum(self.off[o])
            self.intent_entered[o]=0.;self.intent_exited[o]=0.

        # A canonical cell may straddle a diverge. Keep spatial stocks on each
        # side, so a blocked exit cannot stop vehicles that already passed it.
        self.partitions={};self.partition_rows=[];self.max_partition_residual=0.
        selected=branch_partition or []
        if type(partition_speed_context) is not bool or (partition_speed_context and not selected):
            raise ValueError('Physical speed context requires a boolean and branch partitions')
        self.partition_speed_context=partition_speed_context
        if type(partition_exchange) is not bool or (partition_exchange and not selected):
            raise ValueError('Spatial exchange requires a boolean and branch partitions')
        if not isinstance(selected,list) or len(selected)!=len(set(selected)) or set(selected)-set(self.off):
            raise ValueError('Invalid physical branch partition ports')
        if selected and (port_travel is None or self.initial_off_eligible is None or
                         momentum_advection or exchange_model is not None or interruption_gamma is not None):
            raise ValueError('Branch partition requires port positions and unmodified lane transport')
        initial=spec.get('branch_partition_initial',{})
        if set(initial)!=set(selected):raise ValueError('Branch partition snapshot/config mismatch')
        for off in selected:
            i=spec['off_access'][off]['cell'];length=port_travel['off_distance_km'][off]
            if (i in self.partitions or sum(p['cell']==i for p in spec['off_access'].values())!=1
                    or not 0<length<self.lengths[i]):raise ValueError('Partition requires one interior exit per cell')
            if i>=len(self.matrices) or any(abs(sum(row)-1.)>1e-8 for row in self.matrices[i]):
                raise ValueError('Partition requires continuing downstream lanes')
            for ramp,p in spec['ramp_access'].items():
                if p['cell']==i and self.lengths[i]-port_travel['ramp_remaining_km'][ramp]<=length:
                    raise ValueError('Partition requires same-cell merges downstream of its exit')
            part=dict(off=off,pre_length=length,post_length=self.lengths[i]-length)
            if partition_exchange:
                observed=initial[off].get('exchange',{})
                if observed.get('observation_end_s')!=state.time_sec:
                    raise ValueError('Spatial exchange must end at the current observation cutoff')
                matrices=observed.get('rates_per_sec',{})
                size=len(self.n[i])
                if set(matrices)!= {'pre','post'}:
                    raise ValueError('Spatial exchange requires both sides')
                for matrix in matrices.values():
                    if (len(matrix)!=size or any(len(row)!=size for row in matrix)
                            or any(not math.isfinite(r) or r<0 or (g==k and r!=0)
                                   for g,row in enumerate(matrix) for k,r in enumerate(row))):
                        raise ValueError('Invalid spatial exchange rate matrix')
                part['exchange_rates']=copy.deepcopy(matrices)
            for side in ('pre','post'):
                rows=initial[off][side]
                if len(rows)!=len(self.n[i]):raise ValueError('Partition group snapshot shape')
                for key,target in [('n_veh','n'),('v_kmh','v')]:
                    values=[float(r[key]) for r in rows]
                    if any(not math.isfinite(x) or x<0 for x in values):raise ValueError('Invalid partition observation')
                    part[side+'_'+target]=values
            for g,n in enumerate(self.n[i]):
                pre,post=part['pre_n'][g],part['post_n'][g]
                if abs(pre+post-n)>1e-7 or abs(pre-self.initial_off_eligible[off][g])>1e-7:
                    raise ValueError('Partition/current stock mismatch')
                if n and abs((pre*part['pre_v'][g]+post*part['post_v'][g])/n-self.v[i][g])>1e-7:
                    raise ValueError('Partition/current speed mismatch')
                if sum(v[g] for r,v in self.ramp_origin.items() if spec['ramp_access'][r]['cell']==i)>post+1e-7:
                    raise ValueError('Downstream origins exceed post-branch stock')
                if any(part[s+'_n'][g]>net.rho_max*part[s+'_length']*self.widths[i][g]+1e-7 for s in ('pre','post')):
                    raise ValueError('Observed branch partition exceeds physical storage')
            self.partitions[i]=part

    def _hadi_room(self, i, stock, length, cfg):
        row=self.hadi['cells'][i]
        return [min(max(0.,cfg.network.rho_max*length*w-n),self.dt*w*hadi_receiving_vph(
            n/(length*w),cfg.network.rho_max,row['rho_critical'],row['capacity_vphpl'],row['wave_kmh'],row['theta'],
            capacity_critical=self.hadi.get('congested_branch','fixed_wave')=='capacity_critical'))
            for n,w in zip(stock,self.widths[i])]

    def _literature_target(self, cell, rho, target, command, active, cfg):
        if self.vsl_fd_response is None or not active:
            return target
        from evaluation.controllers.freeway_fd import literature_vsl_parameters
        net=cfg.network
        rows=(getattr(net,'freeway_segment_params',{}) or {}).get(self.road,())
        row=rows[cell] if cell<len(rows) else {}
        vf,critical,shape=literature_vsl_parameters(self.vsl_fd_response,
            row.get('v_free',net.v_free),row.get('rho_crit',net.rho_crit),
            row.get('metanet_a_m',net.metanet_a_m),float(command),max(cfg.freeway_follower.vsl_set))
        if critical>=row.get('rho_max',net.rho_max):
            raise ValueError('VSL-induced FD critical density exceeds physical jam density')
        return vf*math.exp(-((max(0.,rho)/critical)**shape)/shape)

    def _hadi_target(self, cell, fd_target, command, active):
        if self.hadi is None or cell not in self.hadi_scope:return fd_target
        value=hadi_desired_speed(fd_target,command,self.hadi['relaxation'],active)
        a=self.hadi_audit;a['desired_calls']+=1;a['desired_changed']+=abs(value-fd_target)>1e-8
        a['max_target_increase_kmh']=max(a['max_target_increase_kmh'],value-fd_target)
        return value

    def free_space(self, cfg):
        result=[[max(0.,cfg.network.rho_max*self.lengths[i]*w-n)
                 for w,n in zip(ws,self.n[i])] for i,ws in enumerate(self.widths)]
        for i,p in self.partitions.items():
            result[i]=[max(0.,cfg.network.rho_max*p['pre_length']*w-n) for w,n in zip(self.widths[i],p['pre_n'])]
        if self.hadi is not None and self.hadi['ctm']:
            for i,stock in enumerate(self.n):
                p=self.partitions.get(i)
                result[i]=self._hadi_room(i,p['pre_n'] if p else stock,p['pre_length'] if p else self.lengths[i],cfg)
        return result

    def _ramp_space(self, i, cfg):
        if i not in self.partitions:return self.free_space(cfg)[i]
        p=self.partitions[i]
        if self.hadi is not None and self.hadi['ctm']:return self._hadi_room(i,p['post_n'],p['post_length'],cfg)
        return [max(0.,cfg.network.rho_max*p['post_length']*w-n) for w,n in zip(self.widths[i],p['post_n'])]

    def ramp_supply(self, ramp, cfg):
        p=self.spec['ramp_access'][ramp];i=p['cell'];weights=p['weights'];s=sum(weights)
        room=self._ramp_space(i,cfg)
        # Fixed physical receiving shares: no borrowing space from another lane.
        return min(room[g]/(w/s)/self.dt for g,w in enumerate(weights) if w)

    def conflict_vph_per_lane(self, ramp):
        p=self.spec['ramp_access'][ramp];i=p['cell']
        if i in self.partitions:
            part=self.partitions[i]
            return sum(w*part['post_n'][g]*part['post_v'][g]/(part['post_length']*self.widths[i][g])
                       for g,w in enumerate(p['weights']))/sum(p['weights'])
        # The merge target group's current flow, not the whole segment mean.
        return sum(w*self.n[i][g]*self.v[i][g]/(self.lengths[i]*self.widths[i][g])
                   for g,w in enumerate(p['weights']))/sum(p['weights'])

    def ramp_lane_conditions(self, ramp, groups, cfg):
        """Receiving space and conflicting flow for explicit connector lanes.

        Shared groups partition their finite space; lane budgets never borrow
        the space of an inaccessible group. This does not create a capacity.
        """
        p=self.spec['ramp_access'][ramp];i=p['cell'];widths=self.widths[i]
        if (not isinstance(groups,(list,tuple)) or not groups or any(type(g) is not int or
                g<0 or g>=len(widths) or not p['weights'][g] for g in groups)):
            raise ValueError('Ramp lane mapping must use accessible physical groups')
        room=self._ramp_space(i,cfg)
        result=[dict(group=g,space_vph=room[g]/groups.count(g)/self.dt,
            conflicting_vph=self.n[i][g]*self.v[i][g]/(self.lengths[i]*widths[g])) for g in groups]
        if i in self.partitions:
            if ramp in self.ramp_conflict_through_inventory:raise ValueError('Partition/conflict origin exclusion not qualified')
            part=self.partitions[i]
            for row in result:
                g=row['group'];row['conflicting_vph']=part['post_n'][g]*part['post_v'][g]/(part['post_length']*widths[g])
        if ramp in self.ramp_conflict_through_inventory:
            self._initialize_destinations(cfg)
            for row in result:
                g=row['group'];origin=self.ramp_origin[ramp][g]
                exiting=sum(v[g] for o,v in self.off.items() if self.spec['off_access'][o]['cell']==i)
                through=self.n[i][g]-origin-exiting
                if through < -1e-7:raise ArithmeticError('Conflict source/destination stocks overlap')
                through=max(0.,through)
                row.update(conflicting_vph=through*self.v[i][g]/(self.lengths[i]*widths[g]),
                    conflict_basis='Through inventory excludes same-merge origins and prior exits',
                    total_group_stock_veh=self.n[i][g],same_merge_origin_veh=origin,
                    prior_exit_stock_veh=exiting,conflicting_stock_veh=through)
        return result

    def _initialize_destinations(self,cfg):
        if self.initialized_destinations:return
        ratios={o:cfg.network.off_ramp_split_ratio[o] for o in self.off}
        initial_labels=self.n
        if self.port_travel is not None:
            initial_labels=[[n-sum(v[g] for r,v in self.ramp_origin.items() if self.spec['ramp_access'][r]['cell']==i)
                for g,n in enumerate(ns)] for i,ns in enumerate(self.n)]
        self._label(initial_labels,ratios,self.initial_off_eligible)
        self.initialized_destinations=True

    def _label(self, arrivals, ratios, eligible_by_off=None):
        for i,amounts in enumerate(arrivals):
            available=list(amounts)
            ports=[o for o,p in self.spec['off_access'].items() if p['cell']==i and o not in self.upstream_off]
            if sum(ratios[o] for o in ports)>1.+1e-9:raise ValueError('Branch split exceeds one')
            for o in ports:
                eligible=eligible_by_off[o] if eligible_by_off is not None else None
                needed=sum(eligible if eligible is not None else amounts)*ratios[o]
                weights=self.spec['off_access'][o]['weights']
                # Prefer physically accessible groups; retain excess destinations
                # in the other groups until a conserved lateral transfer occurs.
                tiers = ([g for g,w in enumerate(weights) if w],
                         [g for g,w in enumerate(weights) if not w])
                if self.destination_policy is not None and i < len(self.matrices):
                    ending = [g for g,w in enumerate(weights) if w and not sum(self.matrices[i][g])]
                    tiers = (ending, [g for g in tiers[0] if g not in ending], tiers[1])
                for indices in tiers:
                    accessible=([min(available[g],eligible[g]) for g in range(len(available))]
                                if eligible is not None else available)
                    capacity=sum(accessible[g] for g in indices)
                    take=min(needed,capacity)
                    for g in indices:
                        x=take*accessible[g]/capacity if capacity else 0.
                        self.off[o][g]+=x;available[g]-=x
                    needed-=take
                if needed>1e-7:raise ArithmeticError('Could not conserve branch destination labels')

    def advance(self, state, control, demand, cfg, *, offramp_capacity_veh_h,
                ramp_release_veh_h, offramp_group_capacity_veh_h=None, ramp_group_release_veh_h=None,
                ramp_entry_speed_kmh=None, junction_ramp_speeds=None, offramp_start_state=None, **unused):
        a,mn,net=self.a,self.a._mn,cfg.network
        if float(getattr(demand,'incident_capacity_factor',1.)) != 1.:
            raise ValueError('Lane-group candidate has not qualified incident capacity changes')
        road=self.road;dt=self.dt;count=len(self.n)
        before=copy.deepcopy(self.n);oldv=copy.deepcopy(self.v)
        part_before=copy.deepcopy(self.partitions)
        post_free={i:self._ramp_space(i,cfg) for i in self.partitions}
        part_in_moment={i:[0.]*len(self.n[i]) for i in self.partitions}
        rates=(self.exchange_model.rates(before,oldv,self.lengths,self.widths)
               if self.exchange_model is not None else self.rates)
        ratios={o:net.off_ramp_split_ratio[o] for o in self.off}
        self._initialize_destinations(cfg)
        free=self.free_space(cfg)
        hadi_budget=copy.deepcopy(free) if self.hadi is not None else None
        if self.hadi is not None:self.hadi_audit['origin_wait_veh_h']+=state.mainline_origin_queue[road]*dt
        port_response=self.port_response
        if port_response:
            if set(offramp_start_state or {})!=set(self.off):raise ValueError('Missing causal off-ramp state')
            if port_response['merge_speed'] and set(junction_ramp_speeds or {})!=set(self.spec['ramp_access']):
                raise ValueError('Missing modelled ramp inlet speeds')
        incoming=[[0.]*len(ns) for ns in self.n]
        junction_moment=copy.deepcopy(incoming) if port_response.get('merge_speed') else None
        incoming_moment=copy.deepcopy(incoming) if self.momentum_advection else None
        ramp_in=copy.deepcopy(incoming)
        ramp_moment=copy.deepcopy(incoming) if ramp_entry_speed_kmh is not None else None
        if ramp_entry_speed_kmh is not None:
            if (not isinstance(ramp_entry_speed_kmh,dict) or set(ramp_entry_speed_kmh)!=set(ramp_release_veh_h)
                    or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0
                           for v in ramp_entry_speed_kmh.values())):
                raise ValueError('Explicit entry speed required for every supplied ramp')
        if ramp_group_release_veh_h is not None and set(ramp_group_release_veh_h)-set(ramp_release_veh_h):
            raise ValueError('Unknown ramp in group release')
        for ramp,q in ramp_release_veh_h.items():
            p=self.spec['ramp_access'][ramp];i=p['cell'];ws=p['weights']
            group_rates=(ramp_group_release_veh_h or {}).get(ramp)
            if group_rates is not None:
                if (len(group_rates)!=len(ws) or any(not math.isfinite(x) or x<0 or (x and not w)
                        for x,w in zip(group_rates,ws)) or abs(sum(group_rates)-q)>1e-7):
                    raise ValueError('Physical group releases must preserve the ramp flow and access')
            for g,w in enumerate(ws):
                x=group_rates[g]*dt if group_rates is not None else q*dt*w/sum(ws)
                receiving=post_free[i] if i in self.partitions else free[i]
                if x>receiving[g]+1e-7:raise ArithmeticError('Ramp exceeds shared target-group receiving space')
                receiving[g]=max(0.,receiving[g]-x);incoming[i][g]+=x;ramp_in[i][g]+=x
                if junction_moment is not None:junction_moment[i][g]+=x*junction_ramp_speeds[ramp]
                entry_speed=oldv[i][g] if ramp_moment is None else ramp_entry_speed_kmh[ramp]
                if ramp_moment is not None:ramp_moment[i][g]+=x*entry_speed
                if incoming_moment is not None:
                    incoming_moment[i][g]+=x*entry_speed
        sending=[[min(n,n*v/self.lengths[i]*dt) for n,v in zip(ns,oldv[i])] for i,ns in enumerate(self.n)]
        through=copy.deepcopy(sending);offreq={};offsent={}
        ramp_sending={}
        if self.port_travel is not None:
            for r,stock in self.ramp_origin.items():
                i=self.spec['ramp_access'][r]['cell'];length=self.port_travel['ramp_remaining_km'][r]
                speeds=part_before[i]['post_v'] if i in part_before else oldv[i]
                ramp_sending[r]=[min(n,n*speeds[g]*dt/length) for g,n in enumerate(stock)]
            for i,ns in enumerate(self.n):
                for g,n in enumerate(ns):
                    residual=n-sum(v[g] for o,v in self.off.items() if self.spec['off_access'][o]['cell']==i)-sum(
                        v[g] for r,v in self.ramp_origin.items() if self.spec['ramp_access'][r]['cell']==i)
                    if residual < -1e-7:raise ArithmeticError('Origin and destination stocks overlap')
                    through[i][g]=min(max(0.,residual),max(0.,residual)*oldv[i][g]*dt/self.lengths[i])+sum(
                        v[g] for r,v in ramp_sending.items() if self.spec['ramp_access'][r]['cell']==i)
        pre_through={}
        for i,p in part_before.items():
            pre_through[i]=[]
            for g,n in enumerate(p['pre_n']):
                residual=n-self.off[p['off']][g]
                origins=sum(v[g] for r,v in self.ramp_origin.items() if self.spec['ramp_access'][r]['cell']==i)
                post=p['post_n'][g]-origins
                if min(residual,post)<-1e-7:raise ArithmeticError('Partition tags exceed spatial stock')
                pre_through[i].append(min(max(0.,residual),max(0.,residual)*p['pre_v'][g]*dt/p['pre_length']))
                through[i][g]=min(max(0.,post),max(0.,post)*p['post_v'][g]*dt/p['post_length'])+sum(
                    v[g] for r,v in ramp_sending.items() if self.spec['ramp_access'][r]['cell']==i)
        for o,stock in self.off.items():
            p=self.spec['off_access'][o];i=p['cell']
            offreq[o]=[sending[i][g]*n/self.n[i][g] if self.n[i][g] else 0. for g,n in enumerate(stock)]
            if self.port_travel is not None:
                length=self.port_travel['off_distance_km'][o]
                speeds=part_before[i]['pre_v'] if i in part_before else oldv[i]
                offreq[o]=[min(n,n*speeds[g]*dt/length) for g,n in enumerate(stock)]
            else:
                for g,x in enumerate(offreq[o]):through[i][g]-=x
            eligible=[x if p['weights'][g] else 0. for g,x in enumerate(offreq[o])]
            requested=sum(eligible);cap=max(0.,offramp_capacity_veh_h[o])*dt
            offsent[o]=[x*min(1.,cap/requested) if requested else 0. for x in eligible]
            if offramp_group_capacity_veh_h and o in offramp_group_capacity_veh_h:
                limits = offramp_group_capacity_veh_h[o]
                if len(limits) != len(eligible) or any(not math.isfinite(x) or x < 0 for x in limits):
                    raise ValueError('Invalid off-ramp receiving capacities by group')
                accepted = [min(x, q*dt) for x, q in zip(eligible, limits)]
                factor = min(1., cap/sum(accepted)) if sum(accepted) else 0.
                offsent[o] = [x*factor for x in accepted]
        self.last_off_sent = copy.deepcopy(offsent)
        through_requests=copy.deepcopy(through) if self.port_travel is not None else None
        if self.port_travel is not None:
            sending=[[x+sum(v[g] for o,v in offreq.items() if self.spec['off_access'][o]['cell']==i)
                for g,x in enumerate(row)] for i,row in enumerate(through)]
        # Partial FIFO: only the group sharing the blocked branch is impeded.
        fifo=[[1.]*len(ns) for ns in self.n]
        for o,requests in offreq.items():
            i=self.spec['off_access'][o]['cell']
            for g,x in enumerate(requests):
                if x>0. and self.spec['off_access'][o]['weights'][g]:
                    fifo[i][g]=min(fifo[i][g],offsent[o][g]/x)
        speed_fifo=copy.deepcopy(fifo)
        operational=[[1.]*len(ns) for ns in self.n]
        for o,p in self.spec['off_access'].items():
            if not port_response:break
            i=p['cell'];hard=list(fifo[i]);spill=port_response['spillback'];obs=offramp_start_state[o]
            if spill is not None:
                factors=off_operational_factors(self.widths[i],p['weights'],obs['n_veh'],obs['capacity_veh'],spill['gamma'],spill['b'])
                operational[i]=factors
                fifo[i]=factors if spill['mode']=='replace_fifo' else [min(a,b) for a,b in zip(hard,factors)]
                if spill['mode']=='replace_fifo':speed_fifo[i]=[1.]*len(hard)
            self.port_response_rows.append(dict(kind='spillback',time_s=state.time_sec,cell=i,connector=o,
                off_n_veh=obs['n_veh'],off_capacity_veh=obs['capacity_veh'],physical_lanes=sum(self.widths[i]),
                operational_lanes=sum(w*f for w,f in zip(self.widths[i],operational[i])),
                original_fifo=hard,used_fifo=list(fifo[i]),speed_fifo=list(speed_fifo[i]),mode='existing_fifo' if spill is None else spill['mode']))
        cross={i:[min(x*fifo[i][g],post_free[i][g]) for g,x in enumerate(row)] for i,row in pre_through.items()}
        through=[[max(0.,x)*(1. if i in self.partitions else fifo[i][g]) for g,x in enumerate(row)] for i,row in enumerate(through)]
        outgoing=[[0.]*len(ns) for ns in self.n]
        intent_before=copy.deepcopy(self.upstream_off)
        inter=[]
        for i,matrix in enumerate(self.matrices):
            requests=[[through[i][g]*w for w in row] for g,row in enumerate(matrix)]
            accepted=0.
            for k in range(len(self.n[i+1])):
                total=sum(r[k] for r in requests)
                factor=min(1.,free[i+1][k]/total) if total else 0.
                for g,row in enumerate(requests):
                    x=row[k]*factor;outgoing[i][g]+=x;incoming[i+1][k]+=x;accepted+=x
                    if junction_moment is not None:
                        junction_moment[i+1][k]+=x*(part_before[i]['post_v'][g] if i in part_before else oldv[i][g])
                    if i+1 in part_in_moment:
                        source_v=part_before[i]['post_v'][g] if i in part_before else oldv[i][g]
                        part_in_moment[i+1][k]+=x*source_v
                    if incoming_moment is not None:incoming_moment[i+1][k]+=x*oldv[i][g]
                    for o,stocks in intent_before.items():
                        if i>=len(stocks):continue
                        y=x*stocks[i][g]/before[i][g] if before[i][g] else 0.
                        self.upstream_off[o][i][g]-=y
                        target=self.off[o] if i+1==len(stocks) else self.upstream_off[o][i+1]
                        target[k]+=y
            inter.append(accepted)
        terminal_cap=net.freeway_capacity_veh_h*sum(self.widths[-1])/net.freeway_lanes*dt
        terminal=sum(through[-1])
        if not getattr(net,'terminal_zero_gradient',False):terminal=min(terminal,terminal_cap)
        for g,x in enumerate(through[-1]):outgoing[-1][g]=terminal*x/sum(through[-1]) if sum(through[-1]) else 0.
        requested=max(0.,demand.freeway_mainline[road])*dt
        entry_request=requested+state.mainline_origin_queue[road]
        entry=min(entry_request,net.freeway_capacity_veh_h*dt,sum(free[0]))
        for g,x in enumerate(free[0]):incoming[0][g]+=entry*x/sum(free[0]) if sum(free[0]) else 0.
        for o,beta in self.upstream_exit_inventory.items():
            for g,x in enumerate(free[0]):
                self.upstream_off[o][0][g]+=beta*entry*x/sum(free[0]) if sum(free[0]) else 0.
            self.intent_entered[o]+=beta*entry
        if incoming_moment is not None:
            for g,x in enumerate(free[0]):
                incoming_moment[0][g]+=(entry*x/sum(free[0]) if sum(free[0]) else 0.)*net.v_free
        state.mainline_origin_queue[road]=entry_request-entry
        off_by_group=[[0.]*len(ns) for ns in self.n]
        for o,values in offsent.items():
            i=self.spec['off_access'][o]['cell']
            for g,x in enumerate(values):self.off[o][g]-=x;off_by_group[i][g]+=x
            if o in self.intent_exited:self.intent_exited[o]+=sum(values)
        for i,ns in enumerate(self.n):
            for g in range(len(ns)):
                ns[g]+=incoming[i][g]-outgoing[i][g]-off_by_group[i][g]
                if incoming_moment is not None:
                    self.v[i][g]=advected_speed(before[i][g],oldv[i][g],
                        outgoing[i][g]+off_by_group[i][g],incoming_moment[i][g],ns[g])
                elif ramp_moment is not None and ramp_in[i][g]:
                    # Replace only the newly accepted ramp vehicles' assumed
                    # recipient speed. Other transport retains its existing law.
                    self.v[i][g]=advected_speed(ns[g]-ramp_in[i][g],oldv[i][g],
                        0.,ramp_moment[i][g],ns[g])
        for i,p in self.partitions.items():
            for g in range(len(self.n[i])):
                p['pre_n'][g]+=incoming[i][g]-ramp_in[i][g]-cross[i][g]-off_by_group[i][g]
                p['post_n'][g]+=ramp_in[i][g]+cross[i][g]-outgoing[i][g]
                old=part_before[i]
                p['pre_v'][g]=advected_speed(old['pre_n'][g],old['pre_v'][g],cross[i][g]+off_by_group[i][g],
                    part_in_moment[i][g],p['pre_n'][g])
                p['post_v'][g]=advected_speed(old['post_n'][g],old['post_v'][g],outgoing[i][g],
                    cross[i][g]*old['pre_v'][g]+(ramp_in[i][g]*old['post_v'][g]
                    if ramp_moment is None else ramp_moment[i][g]),p['post_n'][g])
        if self.port_travel is not None:
            for r,stock in self.ramp_origin.items():
                p=self.spec['ramp_access'][r];i=p['cell']
                for g in range(len(stock)):
                    removed=outgoing[i][g]*ramp_sending[r][g]/through_requests[i][g] if through_requests[i][g] else 0.
                    stock[g]-=removed
                    if ramp_group_release_veh_h is not None and r in ramp_group_release_veh_h:
                        stock[g]+=ramp_group_release_veh_h[r][g]*dt
                    else:
                        stock[g]+=ramp_release_veh_h[r]*dt*p['weights'][g]/sum(p['weights'])
            # These four physical ramps join AFTER this cell's off-ramp. They
            # cannot turn back into it; the harness checks that ordering.
            self._label([[max(0.,x-ramp_in[i][g]) for g,x in enumerate(row)] for i,row in enumerate(incoming)],ratios)
        else:
            self._label(incoming,ratios)
        # Each exchange is constrained by donor stock and receiver space. Both
        # destination labels and speed moments move with those vehicles.
        exchanges=[]
        interruption=[]
        for i,ns in enumerate(self.n):
            branch_stocks={o:v for o,v in self.off.items() if self.spec['off_access'][o]['cell']==i}
            branch_stocks.update({o:rows[i] for o,rows in self.upstream_off.items() if i<len(rows)})
            branch_before={o:list(v) for o,v in branch_stocks.items()}
            origin_before={r:list(v) for r,v in self.ramp_origin.items() if self.spec['ramp_access'][r]['cell']==i}
            def can_move(o,g,k):
                weights=(self.intent_access[o][i] if o in self.intent_access
                         else self.spec['off_access'][o]['weights'])
                access=[j for j,w in enumerate(weights) if w]
                return min(abs(k-j) for j in access)<=min(abs(g-j) for j in access)
            movable=[[max(0.,ns[g]-sum(stock[g] for o,stock in branch_before.items() if not can_move(o,g,k)))
                      for k in range(len(ns))] for g in range(len(ns))]
            request=[[ns[g]*(1.-math.exp(-sum(rates[i][g])*self.sec))*r/sum(rates[i][g])
                      if sum(rates[i][g]) else 0. for r in rates[i][g]] for g in range(len(ns))]
            for g,row in enumerate(request):
                for k in range(len(ns)):row[k]*=movable[g][k]/ns[g] if ns[g] else 0.
            spatial_request=None
            spatial_movable=None;spatial_before=None
            if i in self.partitions:
                p=self.partitions[i]
                spatial_request={side:[[0.]*len(ns) for _ in ns] for side in ('pre','post')}
                if 'exchange_rates' in p:
                    spatial_before={s:list(p[s+'_n']) for s in ('pre','post')}
                    spatial_movable=[[max(0.,p['pre_n'][g]-sum(stock[g] for o,stock in branch_before.items()
                                       if not can_move(o,g,k))) for k in range(len(ns))] for g in range(len(ns))]
                    for side in ('pre','post'):
                        for g,row in enumerate(p['exchange_rates'][side]):
                            rate=sum(row)
                            for k,r in enumerate(row):
                                donor=spatial_movable[g][k] if side=='pre' else p['post_n'][g]
                                spatial_request[side][g][k]=donor*(1.-math.exp(-rate*self.sec))*r/rate if rate else 0.
                        for k in range(len(ns)):
                            total=sum(row[k] for row in spatial_request[side])
                            room=max(0.,net.rho_max*p[side+'_length']*self.widths[i][k]-p[side+'_n'][k])
                            factor=min(1.,room/total) if total else 0.
                            for g in range(len(ns)):spatial_request[side][g][k]*=factor
                    request=[[sum(spatial_request[s][g][k] for s in ('pre','post'))
                              for k in range(len(ns))] for g in range(len(ns))]
                else:
                    for g,row in enumerate(request):
                        for k,x in enumerate(row):
                            post=x*p['post_n'][g]/movable[g][k] if movable[g][k] else 0.
                            spatial_request['post'][g][k]=post;spatial_request['pre'][g][k]=max(0.,x-post)
                    for k in range(len(ns)):
                        factors=[1.]
                        for side in ('pre','post'):
                            total=sum(row[k] for row in spatial_request[side])
                            room=max(0.,net.rho_max*p[side+'_length']*self.widths[i][k]-p[side+'_n'][k])
                            if total:factors.append(room/total)
                        factor=min(factors)
                        for g in range(len(ns)):
                            request[g][k]*=factor
                            for side in ('pre','post'):spatial_request[side][g][k]*=factor
            for k in range(len(ns)):
                total=sum(r[k] for r in request)
                room=max(0.,net.rho_max*self.lengths[i]*self.widths[i][k]-ns[k])
                for g in range(len(ns)):request[g][k]*=min(1.,room/total) if total else 0.
            if spatial_request is not None:
                for g,row in enumerate(request):
                    for k,x in enumerate(row):
                        if abs(x-sum(spatial_request[s][g][k] for s in ('pre','post')))>1e-7:
                            raise ArithmeticError('Partition lateral allocation mismatch')
                for side,transfers in spatial_request.items():
                    old=list(p[side+'_n']);vel=list(p[side+'_v']);mom=[n*v for n,v in zip(old,vel)]
                    for g,row in enumerate(transfers):
                        for k,x in enumerate(row):
                            p[side+'_n'][g]-=x;p[side+'_n'][k]+=x;mom[g]-=x*vel[g];mom[k]+=x*vel[g]
                    p[side+'_v']=[mom[g]/n if n>1e-9 else vel[g] for g,n in enumerate(p[side+'_n'])]
            carrier_v=list(self.v[i]) if self.momentum_advection or ramp_moment is not None else oldv[i]
            pre=list(ns);moment=[n*v for n,v in zip(pre,carrier_v)]
            for g,row in enumerate(request):
                for k,x in enumerate(row):
                    ns[g]-=x;ns[k]+=x;moment[g]-=x*carrier_v[g];moment[k]+=x*carrier_v[g]
                    for o,stock in branch_before.items():
                        amount=x if spatial_movable is None else spatial_request['pre'][g][k]
                        donor=movable[g][k] if spatial_movable is None else spatial_movable[g][k]
                        y=amount*stock[g]/donor if donor and can_move(o,g,k) else 0.
                        branch_stocks[o][g]-=y;branch_stocks[o][k]+=y
                    for r,stock in origin_before.items():
                        amount=x if spatial_before is None else spatial_request['post'][g][k]
                        donor=movable[g][k] if spatial_before is None else spatial_before['post'][g]
                        y=amount*stock[g]/donor if donor else 0.
                        self.ramp_origin[r][g]-=y;self.ramp_origin[r][k]+=y
            exchanges.append(sum(map(sum,request)))
            if self.interruption_gamma is not None:
                interruption.append(lane_entry_speed_loss(request,oldv[i],pre,ns,self.interruption_gamma))
            for g,n in enumerate(ns):
                if n>1e-9:self.v[i][g]=moment[g]/n
            if self.destination_policy == 'clear_ending_lane' and i < len(self.matrices):
                continuing = [g for g,row in enumerate(self.matrices[i]) if sum(row)>0]
                for g,row in enumerate(self.matrices[i]):
                    if sum(row)>0:continue
                    # Only through-destined stock must leave a lane with no
                    # downstream continuation. No exit labels are transferred.
                    through_stock = max(0.,ns[g]-sum(
                        stock[g] for off,stock in self.off.items() if self.spec['off_access'][off]['cell']==i))
                    targets = [k for k in continuing if abs(k-g)==1]
                    if not targets:continue
                    k=targets[0]
                    lane_change_request=through_stock*min(1.,oldv[i][g]*dt/self.lengths[i])
                    amount=min(lane_change_request,max(0.,net.rho_max*self.lengths[i]*self.widths[i][k]-ns[k]))
                    if amount:
                        self.v[i][k]=(ns[k]*self.v[i][k]+amount*self.v[i][g])/(ns[k]+amount)
                        for r,stock in self.ramp_origin.items():
                            if self.spec['ramp_access'][r]['cell']!=i:continue
                            moved=amount*stock[g]/through_stock if through_stock else 0.
                            stock[g]-=moved;stock[k]+=moved
                        ns[g]-=amount;ns[k]+=amount;exchanges[-1]+=amount
        projections=0
        for i,ns in enumerate(self.n):
            for g,n in enumerate(ns):
                rho=before[i][g]/(self.lengths[i]*self.widths[i][g])
                if i+1<count:
                    weights=self.matrices[i][g];weight=sum(weights)
                    down=sum(w*before[i+1][k]/(self.lengths[i+1]*self.widths[i+1][k]) for k,w in enumerate(weights))/weight if weight else rho
                    if i+1 in part_before and weight:
                        p=part_before[i+1]
                        down=sum(w*p['pre_n'][k]/(p['pre_length']*self.widths[i+1][k]) for k,w in enumerate(weights))/weight
                else:down=rho if getattr(net,'terminal_zero_gradient',False) else min(rho,net.rho_crit)
                if i:
                    weights=[row[g] for row in self.matrices[i-1]]
                    up=sum(w*oldv[i-1][k] for k,w in enumerate(weights))/sum(weights) if sum(weights) else oldv[i][g]
                    if i-1 in part_before and sum(weights):
                        up=sum(w*part_before[i-1]['post_v'][k] for k,w in enumerate(weights))/sum(weights)
                else:up=net.v_free
                if junction_moment is not None and any(p['cell']==i for p in self.spec['ramp_access'].values()):
                    original_up=up
                    up=junction_mean_speed(incoming[i][g],junction_moment[i][g],up)
                    self.port_response_rows.append(dict(kind='merge_speed',time_s=state.time_sec,cell=i,group=g,
                        accepted_in_veh=incoming[i][g],accepted_ramp_veh=ramp_in[i][g],velocity_moment=junction_moment[i][g],before_kmh=original_up,after_kmh=up))
                if self.momentum_advection:
                    # Already carried with accepted flow; avoid counting the
                    # usual Euler convection term a second time.
                    up=self.v[i][g]
                vsl=mn.segment_vsl(control,road,i,cfg)
                active=vsl<max(cfg.freeway_follower.vsl_set)-.5
                if i in self.partitions:
                    p=self.partitions[i];old=part_before[i]
                    densities={s:old[s+'_n'][g]/(old[s+'_length']*self.widths[i][g]) for s in ('pre','post')}
                    for side in ('pre','post'):
                        local_rho=densities[side];length=old[side+'_length']
                        downstream=densities['post'] if side=='pre' else down
                        if side=='pre' and port_response.get('diverge_density') and self.spec['off_access'][p['off']]['weights'][g]:
                            obs=offramp_start_state[p['off']];external=obs['density_by_group'][g]
                            downstream=junction_downstream_density([downstream,external])
                            self.port_response_rows.append(dict(kind='diverge_density',time_s=state.time_sec,cell=i,group=g,
                                before_density=densities['post'],off_density=external,after_density=downstream))
                        if self.partition_speed_context:
                            mn.segment_vsl(control,road,i,cfg,physical_length_km=length,segment_end=side=='post')
                        veq=mn.effective_desired_speed_kmh(local_rho,net.v_free,net.rho_crit,vsl,net.alpha_vsl,active,
                            net.metanet_a_m,getattr(net,'vsl_fd_two_branch',False),net.rho_max,float(getattr(net,'rho_crit_two_branch',0.) or 0.))
                        velocity=p[side+'_v'][g];remaining=dt;substeps=0
                        veq=self._hadi_target(i,veq,vsl,active)
                        veq=self._literature_target(i,local_rho,veq,vsl,active,cfg)
                        # Accepted longitudinal/lateral flux already carried
                        # velocity. Do not advect the upstream speed again,
                        # especially when the branch passed zero vehicles.
                        # The remaining ODE is relaxation and anticipation;
                        # subdivision keeps the relaxation weight <=1.
                        while remaining>1e-12:
                            tau=net.metanet_tau_h
                            if self.partition_speed_context:
                                # Each equation call consumes the adapter's
                                # segment context; rearm for every ODE stage.
                                mn.segment_vsl(control,road,i,cfg,physical_length_km=length,segment_end=side=='post')
                                rows=(getattr(net,'freeway_segment_params',{}) or {}).get(str(road),[])
                                params=rows[i] if i<len(rows) else {}
                                tau=float(params.get('metanet_tau_h',tau))
                                from evaluation.controllers.freeway_fd import cell_state_response
                                response=cell_state_response(net,road,i)
                                if response:
                                    from evaluation.controllers.freeway_fd import state_response_coefficients
                                    tau,_=state_response_coefficients(response,velocity,veq,local_rho,downstream,
                                        float(params.get('rho_crit',net.rho_crit)),tau,mn.select_anticipation_nu(local_rho,net,vsl))
                                if not math.isfinite(tau) or tau<=0:raise ValueError('Invalid effective relaxation time')
                            h=min(remaining,tau)
                            velocity=mn.metanet_speed_update_kmh(velocity,velocity,local_rho,downstream,veq,h,length,
                                net.metanet_tau_h,mn.select_anticipation_nu(local_rho,net,vsl),net.metanet_kappa_veh_km_lane,net.v_min)
                            remaining-=h;substeps+=1
                            if substeps>1000 or not math.isfinite(velocity):raise ArithmeticError('Partition speed integration failed')
                        if side=='post' and ramp_in[i][g]:
                            velocity-=net.metanet_delta_merge*ramp_in[i][g]*old['post_v'][g]/(
                                length*self.widths[i][g]*(local_rho+net.metanet_kappa_veh_km_lane))
                        if side=='pre' and speed_fifo[i][g]<1. and old['pre_n'][g]>0:
                            velocity=min(velocity,(cross[i][g]+off_by_group[i][g])/dt*length/old['pre_n'][g])
                        if side=='post' and self.receiving_speed_response is not None:
                            prior=velocity
                            velocity=receiving_limited_speed(velocity,old['post_v'][g],through[i][g],outgoing[i][g],
                                self.sec,self.receiving_speed_response['reaction_seconds'])
                            if velocity!=prior:self.port_response_rows.append(dict(kind='receiving_speed',time_s=state.time_sec,
                                cell=i,group=g,side=side,requested_veh=through[i][g],accepted_veh=outgoing[i][g],
                                previous_kmh=old['post_v'][g],before_kmh=prior,after_kmh=max(net.v_min,velocity),
                                reaction_seconds=self.receiving_speed_response['reaction_seconds']))
                        p[side+'_v'][g]=max(net.v_min,velocity)
                    speed=sum(p[s+'_n'][g]*p[s+'_v'][g] for s in ('pre','post'))/n if n else p['post_v'][g]
                    residual=p['pre_n'][g]+p['post_n'][g]-n
                    self.max_partition_residual=max(self.max_partition_residual,abs(residual))
                    for side in ('pre','post'):
                        q=p[side+'_n'][g]
                        if q < -1e-7 or q>net.rho_max*p[side+'_length']*self.widths[i][g]+1e-7:
                            raise ArithmeticError('Branch partition violates physical storage')
                    if self.off[p['off']][g]>p['pre_n'][g]+1e-7:
                        raise ArithmeticError('Exit destination left pre-branch stock without exiting')
                    if sum(v[g] for r,v in self.ramp_origin.items() if self.spec['ramp_access'][r]['cell']==i)>p['post_n'][g]+1e-7:
                        raise ArithmeticError('Ramp origin left post-branch stock without departing')
                    self.partition_rows.append(dict(time_s=state.time_sec+self.sec,cell=i,group=g,
                        pre_n=p['pre_n'][g],post_n=p['post_n'][g],pre_v=p['pre_v'][g],post_v=p['post_v'][g],
                        internal_cross_veh=cross[i][g],fifo=fifo[i][g],mainline_out_veh=outgoing[i][g],off_out_veh=off_by_group[i][g]))
                else:
                    if port_response.get('diverge_density'):
                        extras=[offramp_start_state[o]['density_by_group'][g] for o,p in self.spec['off_access'].items()
                                if p['cell']==i and p['weights'][g]]
                        if extras:
                            original_down=down;down=junction_downstream_density([down]+extras)
                            self.port_response_rows.append(dict(kind='diverge_density',time_s=state.time_sec,cell=i,group=g,
                                before_density=original_down,off_density=extras,after_density=down))
                    veq=mn.effective_desired_speed_kmh(rho,net.v_free,net.rho_crit,vsl,net.alpha_vsl,active,
                        net.metanet_a_m,getattr(net,'vsl_fd_two_branch',False),net.rho_max,float(getattr(net,'rho_crit_two_branch',0.) or 0.))
                    veq=self._hadi_target(i,veq,vsl,active)
                    veq=self._literature_target(i,rho,veq,vsl,active,cfg)
                    speed=mn.metanet_speed_update_kmh(self.v[i][g],up,rho,down,veq,dt,self.lengths[i],
                        net.metanet_tau_h,mn.select_anticipation_nu(rho,net,vsl),net.metanet_kappa_veh_km_lane,net.v_min)
                    if ramp_in[i][g]:
                        speed-=net.metanet_delta_merge*ramp_in[i][g]*oldv[i][g]/(
                            self.lengths[i]*self.widths[i][g]*(rho+net.metanet_kappa_veh_km_lane))
                    if self.interruption_gamma is not None:
                        speed-=interruption[i][g]
                    if speed_fifo[i][g]<1. and before[i][g]>0:
                        speed=min(speed,(outgoing[i][g]+off_by_group[i][g])/dt*self.lengths[i]/before[i][g])
                    if self.receiving_speed_response is not None:
                        prior=speed
                        speed=receiving_limited_speed(speed,oldv[i][g],through[i][g],outgoing[i][g],
                            self.sec,self.receiving_speed_response['reaction_seconds'])
                        if speed!=prior:self.port_response_rows.append(dict(kind='receiving_speed',time_s=state.time_sec,
                            cell=i,group=g,side='whole',requested_veh=through[i][g],accepted_veh=outgoing[i][g],
                            previous_kmh=oldv[i][g],before_kmh=prior,after_kmh=max(net.v_min,speed),
                            reaction_seconds=self.receiving_speed_response['reaction_seconds']))
                self.v[i][g]=max(net.v_min,speed)
                projections+=int(speed<=net.v_min)
                branch=sum(stock[g] for o,stock in self.off.items() if self.spec['off_access'][o]['cell']==i)
                upstream=sum(rows[i][g] for rows in self.upstream_off.values() if i<len(rows))
                origins=sum(stock[g] for r,stock in self.ramp_origin.items() if self.spec['ramp_access'][r]['cell']==i)
                if origins < -1e-7 or upstream < -1e-7 or origins+branch+upstream > n+1e-7:
                    raise ArithmeticError('Origin/destination inventory exceeds physical stock')
                if not math.isfinite(n) or n < -1e-7 or branch < -1e-7 or branch>n+1e-7:
                    raise ArithmeticError('Lane-group or destination conservation failure')
                if n>net.rho_max*self.lengths[i]*self.widths[i][g]+1e-7:
                    raise ArithmeticError('Lane group exceeds physical storage')
                self.rows.append({'time_s':state.time_sec+self.sec,'cell':i,'group':g,
                    'n_veh':n,'v_kmh':self.v[i][g],'branch_veh':branch,'exchanged_veh':exchanges[i],
                    'longitudinal_in_veh':incoming[i][g]-ramp_in[i][g],
                    'merge_in_veh':ramp_in[i][g],'mainline_out_veh':outgoing[i][g],
                    'off_out_veh':off_by_group[i][g]})
                if self.interruption_gamma is not None:
                    self.rows[-1]['lane_entry_follower_loss_kmh']=interruption[i][g]
                if self.port_travel is not None:self.rows[-1]['ramp_origin_veh']=origins
                if self.upstream_off:self.rows[-1]['upstream_exit_veh']=upstream
            residual=sum(ns)-sum(before[i])-sum(incoming[i])+sum(outgoing[i])+sum(off_by_group[i])
            self.max_residual=max(self.max_residual,abs(residual))
        if self.max_residual>1e-7:raise ArithmeticError('Lane-group continuity')
        if self.max_partition_residual>1e-7:raise ArithmeticError('Branch partition continuity')
        if self.hadi is not None:
            audit=self.hadi_audit
            for i,row in enumerate(incoming):
                observed=[x-ramp_in[i][g] if i in part_before else x for g,x in enumerate(row)]
                limits=hadi_budget[i]
                if i in part_before:
                    observed+=[x+ramp_in[i][g] for g,x in enumerate(cross[i])]
                    p=part_before[i]
                    limits+=(self._hadi_room(i,p['post_n'],p['post_length'],cfg) if self.hadi['ctm'] else [
                        max(0.,net.rho_max*p['post_length']*w-n) for w,n in zip(self.widths[i],p['post_n'])])
                violation=max([0.]+[x-b for x,b in zip(observed,limits)])
                audit['max_budget_violation_veh']=max(audit['max_budget_violation_veh'],violation)
                if violation>1e-7:raise ArithmeticError('Shared CTM receiving budget exceeded')
                audit['receiving_steps']+=len(observed);audit['accepted_veh']+=sum(observed)
                bound=audit['boundaries'].setdefault(str(i),dict(received_veh=0.,near_budget_steps=0))
                bound['received_veh']+=sum(row);bound['near_budget_steps']+=sum(b>0 and abs(x-b)<1e-7 for x,b in zip(observed,limits))
                audit['limited_group_steps']+=sum(b>0 and abs(x-b)<1e-7 for x,b in zip(observed,limits))
        for o,stocks in self.upstream_off.items():
            residual=(self.intent_initial[o]+self.intent_entered[o]-self.intent_exited[o]
                      -sum(map(sum,stocks))-sum(self.off[o]))
            self.max_intent_residual=max(self.max_intent_residual,abs(residual))
        if self.max_intent_residual>1e-7:raise ArithmeticError('First-exit intention continuity')
        state.freeway_density[road]=[sum(ns)/(self.lengths[i]*sum(self.widths[i])) for i,ns in enumerate(self.n)]
        state.freeway_speed[road]=[sum(n*v for n,v in zip(ns,self.v[i]))/sum(ns) if sum(ns) else sum(self.v[i])/len(ns) for i,ns in enumerate(self.n)]
        state.freeway_flow[road]=[sum(n*v for n,v in zip(ns,self.v[i]))/self.lengths[i] for i,ns in enumerate(self.n)]
        if port_response.get('spillback'):
            # Operational q uses accessible sending width. Geometry, rho and
            # storage retain their physical widths for exact count accounting.
            state.freeway_flow[road]=[sum(n*v*f for n,v,f in zip(ns,self.v[i],operational[i]))/self.lengths[i]
                                      for i,ns in enumerate(self.n)]
        ledger=a._area.get_ledger(state)
        for i,ns in enumerate(before):
            for g,n in enumerate(ns):
                resource=f'{road}:cell:{i}:group:{g}'
                space=max(0.,net.rho_max*self.lengths[i]*self.widths[i][g]-n)
                ledger.record_resource_allocation('freeway_lane_group_receiving',resource,space,
                    {'mainline':incoming[i][g]-ramp_in[i][g],'ramp':ramp_in[i][g]})
                ledger.record_resource_allocation('freeway_lane_group_sending',resource,sending[i][g],
                    {'mainline':outgoing[i][g],'offramp':off_by_group[i][g]})
        for i,x in enumerate(inter):
            ledger.record_resource_allocation('freeway_mainline_sending',f'{road}:cell:{i}',sum(through[i]),{f'{road}:cell:{i}':x})
        ledger.record_resource_allocation('freeway_terminal_sending',road,sum(through[-1]),{f'{road}:cell:{count-1}':terminal})
        ledger.record_resource_allocation('freeway_entry_request',road,entry_request,{'origin:'+road:entry})
        for o,values in offsent.items():
            ledger.record_resource_allocation('freeway_offramp_sending',o,sum(offreq[o]),{f'{road}:cell:{self.spec["off_access"][o]["cell"]}':sum(values)})
        a._area.emit_transfer(state,cfg,'external:mainline:'+road,'origin:'+road,requested,source_inside=False,target_inside=False)
        a._area.emit_transfer(state,cfg,'origin:'+road,'freeway:'+road,entry,target_inside=True)
        for ramp,q in ramp_release_veh_h.items():a._area.emit_transfer(state,cfg,'merge_pending:'+ramp,'freeway:'+road,q*dt,target_inside=True)
        a._area.emit_transfer(state,cfg,'freeway:'+road,'external:terminal:'+road,terminal,source_inside=True,target_inside=False)
        ledger.complete_constraint_coverage('freeway_allocator')
        return sum(map(sum,self.n))*dt, {'density_projection_count':0,'speed_projection_count':projections,
            'density_exceedance_count':sum(r>net.rho_crit for r in state.freeway_density[road])}
