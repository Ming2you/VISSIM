"""Diagnostic-only array evaluation of the existing local68 partial-FIFO law.

The ordered cohort population, lane tags, release clock and all source debits
remain in Python. Only prefix/accepted arithmetic is compiled. No tiny mass is
dropped and no vehicle state is pooled. Not installed in the current run.
"""
from bisect import bisect_right
from collections import defaultdict
import numpy as np
from numba import njit
from evaluation.controllers import route_choice_corridor as rc
from evaluation.controllers.sdmpc_tangent_transport import Packed,_put
from evaluation.controllers.sdmpc_tangent_spatial import (
    _constant,_value,_add,_subtract,_multiply,_minimum)

@njit(cache=True,nogil=True,fastmath=False)
def arithmetic(values,refs,kinds,products,prefixes,queries,remaining,passed,fraction,
               counters,parents,weights,ties):
    zero=_constant(0.);one=_constant(1.)
    for n,s,out in products:
        _put(values,refs,kinds,out,_multiply(_value(values,refs,kinds,n),
             _value(values,refs,kinds,s),counters,parents,weights))
    for previous,item,out in prefixes:
        _put(values,refs,kinds,out,_add(_value(values,refs,kinds,previous),
             _value(values,refs,kinds,item),counters,parents,weights))
    for k in range(len(queries)):
        owner,n,s,ahead,connecting=queries[k]
        coverage=_minimum(one,_value(values,refs,kinds,ahead),counters,ties)
        amount=_multiply(_value(values,refs,kinds,n),_value(values,refs,kinds,s),counters,parents,weights)
        f=_value(values,refs,kinds,fraction) if connecting else zero
        accepted=_multiply(amount,_subtract(one,_multiply(coverage,
            _subtract(one,f,counters,parents,weights),counters,parents,weights),
            counters,parents,weights),counters,parents,weights)
        _put(values,refs,kinds,remaining[k],_subtract(amount,accepted,counters,parents,weights))
        j=passed[owner]
        _put(values,refs,kinds,j,_add(_value(values,refs,kinds,j),accepted,counters,parents,weights))

def advance(state,cfg,plan,actual,step):
    spec=cfg.network.known_legsplit_routes
    if not spec.get('local_queue_gate'):return
    local=state.known_legsplit_route_state;ramp=spec['entry_lane_receiving']['ramp']
    requested=plan['requests'].get(ramp,0.)
    fraction=min(1.,actual.get(ramp,0.)/requested) if requested>0 else 0.
    pack=Packed();frac=pack.row([fraction])[0];zero=pack.row([0.])[0]
    blocked=defaultdict(list);products=[]
    for b in local['cohorts']:
        if b['target']==ramp and b['due']<=step and 'lane68' in b:
            for lane,share in b['lane68']['shares'].items():
                n,s,out=pack.row([b['vehicles'],share,0.])
                products.append((n,s,out))
                blocked[lane].append((tuple(b['lane68']['order']),out))
    prefix={};prefix_ops=[]
    for lane,rows in blocked.items():
        rows.sort(key=lambda row:row[0]);orders=[];counts=[zero]
        for order,n in rows:
            out=pack.row([0.])[0];prefix_ops.append((counts[-1],n,out))
            orders.append(order);counts.append(out)
        prefix[lane]=(orders,counts)
    owners=[];queries=[];rem_slots=[];pass_slots=[];lanes=[]
    for c in local['cohorts']:
        if not c.get('local68_queue') or c['due']>step:continue
        owner=len(owners);owners.append(c);pass_slots.extend(pack.row([0.]))
        tag=c['lane68'];owner_lanes=[]
        for lane,share in tag['shares'].items():
            orders,counts=prefix.get(lane,([], [zero]))
            ahead=counts[bisect_right(orders,tuple(tag['order']))]
            n,s,out=pack.row([c['vehicles'],share,0.]);rem_slots.append(out)
            connecting=not ('lateral_access_rate_per_sec' in spec and lane not in spec['entry_lane_receiving']['ramp_lanes'])
            queries.append((owner,n,s,ahead,int(connecting)));owner_lanes.append(lane)
        lanes.append(owner_lanes)
    arrays=pack.arrays()
    capacity=32+2*len(products)+8*len(queries)
    counters=np.zeros(4,dtype=np.int64)
    parents=np.zeros((capacity,2),dtype=np.int64);weights=np.zeros((capacity,2))
    ties=np.zeros((max(1,len(queries)),2),dtype=np.int64);discrete=np.zeros(0,dtype=np.int64)
    index=lambda rows,width:np.asarray(rows,dtype=np.int64).reshape((-1,width))
    arithmetic(*arrays,index(products,3),index(prefix_ops,3),index(queries,5),
        np.asarray(rem_slots,dtype=np.int64),np.asarray(pass_slots,dtype=np.int64),frac,
        counters,parents,weights,ties)
    prior_count_keys=set(pack.trace.counts) if pack.trace is not None else set()
    pack.finish(counters,parents,weights,ties,discrete)
    # Packed.finish publishes zero counters too. Preserve the original sparse
    # counter representation, without deleting any event or nonzero count.
    if pack.trace is not None:
        for key in set(pack.trace.counts)-prior_count_keys:
            if pack.trace.counts[key]==0:del pack.trace.counts[key]
    passed_values=pack.restore(pass_slots);remaining_values=pack.restore(rem_slots)
    released={};offset=0
    for c,keys,passed in zip(owners,lanes,passed_values):
        remaining=dict(zip(keys,remaining_values[offset:offset+len(keys)]));offset+=len(keys)
        if passed<=0:continue
        tag=c['lane68'];c['vehicles']-=passed
        if c['vehicles']>rc.EPS:
            c['lane68']={**tag,'shares':{lane:n/c['vehicles'] for lane,n in remaining.items() if n>0}}
        due=step+c['downstream_steps'];key=(c['target'],due)
        released[key]=released.get(key,0.)+passed
    for (target,due),amount in released.items():
        local['cohorts'].append(dict(target=target,vehicles=amount,due=due,source='local68_passed'))
        pending=state.urban_storage_release_buffer.setdefault(spec['storage'],{})
        pending[due]=pending.get(due,0.)+amount
    local['local68_passed_veh']=local.get('local68_passed_veh',0.)+sum(released.values())
