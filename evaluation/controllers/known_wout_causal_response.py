"""Reusable causal W_out/ramp receiving candidate, not activated by default.

These are the previously tested receiving/turnover/source-mixture equations,
with unchanged parameters. Enable explicitly only after known route and lane
initialization. No diagnostic modules are imported by this module.
This receiving-only approximation is not a microscopic lane-gap or full LTM.
"""
from evaluation.controllers import route_choice_corridor as rc
from evaluation.controllers.physical_urban_transport import ReceivingEnvelope

FIELD = '_known_wout_departure_memory'


def configure(cfg, tuning, state):
    """Opt in after canonical route/lane initialization, in parent and workers."""
    option = tuning.get('urban', {}).get('known_wout_causal_lane_response')
    if option is None:
        return {}
    if not isinstance(option, dict) or set(option) != {'wave_m_s'}:
        raise ValueError('Causal W_out response requires one explicit wave_m_s')
    wave = rc._positive(option['wave_m_s'], 'causal W_out wave_m_s')
    spec = getattr(cfg.network, 'known_legsplit_routes', None)
    if (not spec or not spec.get('connector_queue_gate')
            or 'lateral_access_rate_per_sec' not in spec):
        raise ValueError('Causal W_out response requires connector queue and lane access')
    geometry = spec['entry_lane_receiving']
    ramp = geometry['ramp']
    sources = [name for name, splits in cfg.network.boundary_out_ramp_split.items()
               if ramp in splits.get('ramps', {})]
    if (ramp != 'RM_C10681' or geometry['ramp_lanes'] != {'1': 0, '2': 1}
            or cfg.network.on_ramp_to_movement[ramp]
            or ramp not in cfg.network.gate_onramp_queue_ramps
            or sources != [spec['storage']]):
        raise ValueError('Causal W_out response requires the single proved10681 source')
    buffer = state.lane_ramp_runtime.buffers[ramp]
    if buffer.lane_exchange_rates is not None:
        raise ValueError('Causal receiving has no ramp lateral-history model')
    lanes = buffer._lane_buffers
    if (len(lanes) != 2 or any(b.lanes != 1 or b.head_position_m <= 0
                            or hasattr(b, '_spatial_entry') for b in lanes)):
        raise ValueError('Causal receiving requires two fresh positive-length ramp lanes')
    for lane in lanes:
        attach(lane, wave)
        lane._causal_receiving_enabled = True
    spec['causal_lane_response'] = dict(option)
    return {'known_wout_causal_lane_response': 1.,
            'known_wout_receiving_wave_m_s': wave}


def bind_source_request(state, spec, requests):
    """Use the current eligible source mixture, not historical arrival shares."""
    geometry = spec['entry_lane_receiving']
    ramp = geometry['ramp']
    buffer = state.lane_ramp_runtime.buffers[ramp]
    if abs(state.ramp_queue[ramp]-buffer.snapshot()['connector_veh']) > 1e-7:
        raise ValueError('Causal W_out response cannot absorb an outside ramp backlog')
    counts, shares = mixture(state.known_legsplit_route_state['plan']['rows'], geometry)
    if abs(sum(counts)-requests.get(ramp, 0.)) > 1e-7:
        raise ValueError('Current source lanes do not cover the ramp request')
    if shares is not None:
        buffer.lane_arrival_shares = shares


def attach(buffer,wave):
    if buffer.lanes!=1 or buffer.head_position_m<=0:
        raise ValueError('Positive-length lane-resolved prehead required')
    if hasattr(buffer,'_spatial_entry'):raise ValueError('Duplicate spatial receiving installation')
    env=ReceivingEnvelope(buffer.head_position_m,buffer.spacing_m,buffer._speed_mps,wave,
        [pos for pos,speed,lane in buffer.initial_cohorts if pos<=buffer.head_position_m])
    buffer._spatial_entry={'envelope':env,'start':buffer.time_sec,'departures':[0.],
        'admitted_start':buffer.cumulative_admitted_veh,'interval_end':buffer.time_sec,'dt':0.}

def offer(buffer,original_room):
    x=buffer._spatial_entry;dt=x['dt']
    if not dt:return 0.
    elapsed=x['interval_end']-x['start']
    if 'departure_times' in x:
        from bisect import bisect_right
        stop=bisect_right(x['departure_times'],elapsed-dt+1e-8)
        available=x['envelope'].offer(elapsed,dt,x['admitted_start'],x['departures'][:stop],
                                      departure_times=x['departure_times'][:stop])
    else:
        past=x['departures'][:int(elapsed-dt)+1]
        available=x['envelope'].offer(elapsed,dt,x['admitted_start'],past)
    # Multiple reads/commits cannot spend the same one-second flow budget twice.
    used=buffer.cumulative_admitted_veh-x['admitted_start']
    if used < -1e-8:raise ArithmeticError('Cumulative admissions went backwards')
    return min(original_room,max(0.,available-used))

def advance(state, cfg, step):
    spec=cfg.network.known_legsplit_routes
    rate=spec.get('lateral_access_rate_per_sec')
    if rate is None:return
    geometry=spec['entry_lane_receiving']; ramp=geometry['ramp']
    prior=getattr(state,FIELD,None)
    if prior is not None:
        assert prior['step']==step-1, 'Never reuse an old departure opportunity'
    slots=prior['departed'] if prior is not None else {}
    occupied=rc._known_lane_occupancy(state,spec,step)
    pending=[];departed={};ledger=rc.get_ledger(state)
    for lane,target in (('3','2'),('4','3')):
        cap=geometry['road_capacity_veh'][target]
        room=max(0.,cap-occupied[target])
        probability=-rc.math.expm1(-rate*cfg.simulation.T_u_sec*min(1.,room/cap))
        rows=[];donors=0.
        for c in state.known_legsplit_route_state['cohorts']:
            if c['target']!=ramp or c['due']>step:continue
            share=c['lane68']['shares'].get(lane,0.)
            if share<=0 or c['vehicles']<=0:continue
            rows.append((c,share));donors+=c['vehicles']*share
        if donors<=0:continue
        attempt=max(donors*probability,min(donors,slots.get(target,0.)))
        accepted=min(room,attempt)
        # Retain the old proportional source allocation; only demand changes.
        fraction=accepted/donors if accepted<donors else 1.
        for c,share in rows:pending.append((c,lane,target,share*fraction))
        departed[lane]=accepted
        if ledger is not None and ledger.captures_response:
            ledger.record_resource_allocation('known_wout_lateral_receiving','68:'+target,room,
                                               {'lane:68:'+lane:accepted})
    for c,lane,target,fraction in pending:
        shares=dict(c['lane68']['shares'])
        shares[lane]-=fraction;shares[target]=shares.get(target,0.)+fraction
        c['lane68']={**c['lane68'],'shares':{k:v for k,v in shares.items() if v>0}}
    setattr(state,FIELD,dict(step=step,departed=departed))

def _lane_stocks(state, spec):
    """Only exit-eligible owners modified by the current commit, per lane."""
    result={}
    for c in state.known_legsplit_route_state['cohorts']:
        if c['target']!=spec['entry_lane_receiving']['ramp'] and not c.get('local68_queue'):
            continue
        for lane,share in c.get('lane68',{}).get('shares',{}).items():
            result[lane]=result.get(lane,0.)+c['vehicles']*share
    return result

def mixture(rows, geometry):
    counts = [0.] * len(geometry['ramp_lanes'])
    for cohort, amount in rows:
        if cohort['target'] != geometry['ramp'] or amount <= 0:
            continue
        shares = cohort['lane68']['shares']
        eligible = sum(shares.get(lane, 0.) for lane in geometry['ramp_lanes'])
        assert eligible > 0
        for lane, index in geometry['ramp_lanes'].items():
            counts[index] += amount * shares.get(lane, 0.) / eligible
    total = sum(counts)
    return counts, tuple(n / total for n in counts) if total else None

def begin_receiving_interval(buffer, start_sec, duration_sec):
    """Called after the ordinary begin; keep only contiguous past head flow."""
    memory = buffer._spatial_entry
    if duration_sec<=0 or duration_sec>memory['envelope'].lag:
        raise ValueError('Ramp interval must be positive and no longer than receiving wave lag')
    if duration_sec!=1 and 'departure_times' not in memory:
        if len(memory['departures'])!=int(start_sec-memory['start'])+1:
            raise ValueError('Noncontiguous causal head history')
        memory['departure_times']=list(range(len(memory['departures'])))
    if 'departure_times' in memory:
        if (len(memory['departures'])!=len(memory['departure_times'])
                or abs(memory['departure_times'][-1]-(start_sec-memory['start']))>1e-8):
            raise ValueError('Noncontiguous causal head timestamps')
    elif len(memory['departures']) != int(start_sec-memory['start'])+1:
        raise ValueError('Noncontiguous causal head history')
    memory.update(admitted_start=buffer.cumulative_admitted_veh,
                  interval_end=start_sec+duration_sec, dt=duration_sec)


def record_head_service(buffer):
    memory=buffer._spatial_entry
    memory['departures'].append(buffer.cumulative_head_service_veh)
    if 'departure_times' in memory:
        memory['departure_times'].append(memory['interval_end']-memory['start'])


def record_source_departures(state, before, after, step):
    """After ordinary source debits; never create or accumulate unused credit."""
    memory = getattr(state, FIELD, None)
    if memory is None or memory['step'] != step:
        assert all(abs(before.get(k,0)-after.get(k,0)) < 1e-7 for k in set(before)|set(after))
        setattr(state, FIELD, dict(step=step, departed={}))
    else:
        for lane in set(before)|set(after):
            departed = before.get(lane,0)-after.get(lane,0)
            assert departed >= -1e-7
            memory['departed'][lane] = memory['departed'].get(lane,0)+max(0.,departed)

