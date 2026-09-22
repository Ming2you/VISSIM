"""Fused numeric local transport: request, allocation, FIFO movement and checks.

The native lists below are contiguous arrays of numeric records (integer label,
value, reverse node, active flag). No Python Dual is created inside a step.
The query-owned FIFO buffers remain the state/snapshot boundary. This does not
change the one-second model, route identities, receiving budgets or optimizer.
"""
from collections import Counter, defaultdict
import math
import time
import numpy as np
from numba import njit, types
from numba.typed import List
from evaluation.controllers.sdmpc_tangent_spatial import (
    _constant as C, _add, _subtract, _multiply, _divide, _minimum, _maximum,
    _branch, _operation)
from evaluation.controllers.sdmpc_tangent_transport import Packed, _ordered_sum
from evaluation.controllers.sdmpc_tangent_fifo import get

STATS = dict(calls=0, kernel_sec=0., wall_sec=0., nodes=0, packet_inputs=0,
             packet_outputs=0, python_packet_reads=0)
EPS=1e-9
PACKET_TYPE=types.Tuple((types.int64,types.float64,types.int64,types.boolean))
QUEUE_TYPE=types.ListType(PACKET_TYPE)


@njit(cache=True)
def add(a,b,t):return _add(a,b,t[0],t[1],t[2])
@njit(cache=True)
def sub(a,b,t):return _subtract(a,b,t[0],t[1],t[2])
@njit(cache=True)
def mul(a,b,t):return _multiply(a,b,t[0],t[1],t[2])
@njit(cache=True)
def div(a,b,t):return _divide(a,b,t[0],t[1],t[2])
@njit(cache=True)
def low(a,b,t):return _minimum(a,b,t[0],t[3])
@njit(cache=True)
def high(a,b,t):return _maximum(a,b,t[0],t[3])
@njit(cache=True)
def branch(a,b,t):_branch(a,b,t[0],t[3])
@njit(cache=True)
def amount(packet):return packet[1],packet[2],packet[3]
@njit(cache=True)
def packet(label,a):return label,a[0],a[1],a[2]
@njit(cache=True)
def empty_packets():return List.empty_list(PACKET_TYPE)
@njit(cache=True)
def empty_values():return [(0.,0,False) for _ in range(0)]
@njit(cache=True)
def empty_requests():return [(0,0,0.,0,False) for _ in range(0)]

@njit(cache=True)
def lookup(mapping,key):
    return mapping[key] if key in mapping else C(0.)


@njit(cache=True)
def fsum(items,t):
    # CPython math.fsum partials and final half-even correction, finite inputs.
    partials=np.empty(len(items));size=0;first=True;node=0;dual=False
    for a in items:
        x=a[0];i=0
        for j in range(size):
            y=partials[j]
            if abs(x)<abs(y):x,y=y,x
            hi=x+y;lo=y-(hi-x)
            if lo!=0.:partials[i]=lo;i+=1
            x=hi
        partials[i]=x;size=i+1
        if a[2]:
            if first:node=a[1];first=False
            else:
                j=t[0][0]
                if j>=len(t[1]):raise ValueError('Urban tape exhausted')
                t[1][j,0]=node;t[1][j,1]=a[1];t[2][j,0]=1.;t[2][j,1]=1.
                t[0][0]+=1;node=-j-1
            dual=True
    hi=0.;lo=0.
    if size:
        size-=1;hi=partials[size]
        while size:
            x=hi;size-=1;y=partials[size];hi=x+y;lo=y-(hi-x)
            if lo!=0.:break
        if size and ((lo<0. and partials[size-1]<0.) or (lo>0. and partials[size-1]>0.)):
            y=lo*2.;x=hi+y
            if y==x-hi:hi=x
    return hi,node,dual


@njit(cache=True)
def ordered(items,t):
    v=np.empty(len(items));r=np.empty(len(items),np.int64);k=np.empty(len(items),np.bool_)
    for j,a in enumerate(items):v[j],r[j],k[j]=a
    return _ordered_sum(v,r,k,t[0],t[1],t[2])


@njit(cache=True)
def stock(q,t):return fsum([amount(p) for p in q],t)


@njit(cache=True)
def append(q,label,a,groups,t):
    branch(a,C(-EPS),t)
    if a[0]<-EPS or not math.isfinite(a[0]):raise ValueError('Invalid labelled mass')
    branch(a,C(EPS),t)
    if a[0]<=EPS:return
    if len(q) and groups[q[-1][0]]==groups[label]:q[-1]=packet(q[-1][0],add(amount(q[-1]),a,t))
    else:q.append(packet(label,a))


@njit(cache=True)
def take(q,a,cached_stock,t):
    branch(a,C(-EPS),t)
    invalid=a[0]<-EPS
    if not invalid:
        limit=add(cached_stock,C(1e-7),t);branch(a,limit,t);invalid=a[0]>limit[0]
    if invalid:raise ArithmeticError('FIFO overdraw')
    out=empty_packets();used=0
    while True:
        branch(a,C(EPS),t)
        if a[0]<=EPS or used==len(q):break
        p=q[used];d=low(a,amount(p),t);out.append(packet(p[0],d))
        a=sub(a,d,t);left=sub(amount(p),d,t);q[used]=packet(p[0],left)
        branch(left,C(EPS),t)
        if left[0]<=EPS:used+=1
    if used:del q[:used]
    return out


@njit(cache=True)
def take_label(q,label,a,indexed,groups,t):
    available=0.
    for p in q:
        if groups[p[0]]!=groups[label] or p[1]<0.:continue
        available+=p[1]
        if indexed:
            branch(a,C(available+1e-7),t)
            if a[0]<=available+1e-7:break
    branch(a,C(-EPS),t);invalid=a[0]<-EPS
    if not invalid:
        branch(a,C(available+1e-7),t);invalid=a[0]>available+1e-7
    if invalid:raise ArithmeticError('Lateral label overdraw')
    remaining=a
    for j in range(len(q)):
        p=q[j]
        if groups[p[0]]!=groups[label] or p[1]<0.:continue
        moved=low(amount(p),remaining,t);remaining=sub(remaining,moved,t)
        left=sub(amount(p),moved,t);branch(left,C(EPS),t)
        if left[0]>EPS:
            if not indexed:left=sub(amount(p),moved,t)
            q[j]=packet(p[0],left)
        else:q[j]=(p[0],-1.,0,False)
        if indexed:
            branch(remaining,C(0.),t)
            if remaining[0]==0.:break
    if not indexed:
        live=[p for p in q if p[1]>=0.];q.clear();q.extend(live)


@njit(cache=True)
def counts(q,groups,t):
    result={0:C(0.)};result.clear()
    for p in q:
        label=groups[p[0]];result[label]=add(lookup(result,label),amount(p),t)
    return result


@njit(cache=True)
def compact(q,behaviors,groups,t):
    out=empty_packets();run={0:C(0.)};run.clear();first={0:0};first.clear();previous=-1
    for p in q:
        behavior=behaviors[p[0]]
        if behavior!=previous:
            for label,a in run.items():out.append(packet(first[label],a))
            run.clear();first.clear();previous=behavior
        label=groups[p[0]]
        if label not in first:first[label]=p[0]
        run[label]=add(lookup(run,label),amount(p),t)
    for label,a in run.items():out.append(packet(first[label],a))
    q.clear();q.extend(out)


@njit(cache=True)
def route(source,label,receiving,metadata,lateral_access,green,t):
    # Metadata records (base target/reason, optional lateral target, signal group).
    target,reason,other,signal=metadata[source,label]
    if not lateral_access and other>=0:
        room=receiving[other];branch(room,C(EPS),t)
        if room[0]>EPS:return other,1
    if signal>=0 and not green[signal]:return -1,5
    if target == -2:raise ValueError('Unknown destination has no unique physical exit')
    return target,reason


@njit(cache=True,nogil=True)
def pipeline(queues,ncells,old_n,cap,dx,speed,wave,rate,signal,green,exit_room,
             finite_exit,metadata,display_destination,groups,required,neighbors,rates,fractions,behaviors,
             lateral_access,indexed_lateral,do_compact,defer,prefer,footprints,
             spacing,external_targets,source_order,target_order,move_source_ids,initial,admitted,
             departed,movements,vehicle_seconds,t):
    nq=len(queues);nt=len(target_order)
    receiving=[high(C(0.),low(C(rate),mul(C(wave/dx[i]),sub(C(cap[i]),old_n[i],t),t),t),t)
               for i in range(ncells)]
    sending=[low(C(rate),mul(C(speed/dx[i]),old_n[i],t),t) for i in range(ncells)]
    for i in range(ncells,nq):sending.append(stock(queues[i],t))
    cached_stock=old_n.copy()
    for i in range(ncells,nq):cached_stock.append(sending[i])
    stock_valid=np.ones(nq,np.bool_)
    initial_send=sending.copy();initial_recv=receiving.copy()
    additions=[empty_packets() for _ in range(ncells)]
    transfers=[(0,0,-1,empty_packets()) for _ in range(0)]
    blocked=[(0,0) for _ in range(0)]
    if lateral_access:
        requests=[empty_requests() for _ in range(ncells)];targets=[0 for _ in range(0)]
        for source in range(ncells):
            budget=sending[source];q=queues[source]
            for p in q:
                label=p[0];n=amount(p);mandatory=required[source,label]
                offers=[(0,C(0.)) for _ in range(0)]
                if mandatory>=0:
                    if defer[label] or prefer:
                        forward,reason=route(source,q[0][0],receiving,metadata,lateral_access,green,t)
                        threshold=receiving[mandatory] if prefer else C(0.)
                        if reason==0:
                            bound=add(threshold,C(EPS),t);room=receiving[forward] if forward>=0 else C(0.)
                            branch(room,bound,t)
                            if room[0]>bound[0]:continue
                    offers.append((mandatory,low(n,budget,t)))
                else:
                    total=rates[source,label,2]
                    quantity=low(budget,mul(n,C(fractions[source,label]),t),t)
                    if total:
                        for side in range(2):
                            r=rates[source,label,side]
                            if r>0.:offers.append((neighbors[source,side],div(mul(quantity,C(r),t),C(total),t)))
                for target,offered in offers:
                    if footprints[label]>=0.:
                        target_n=lookup(counts(queues[target],groups,t),groups[label]);branch(target_n,C(EPS),t)
                        if target_n[0]<=EPS:
                            free=sub(C(cap[target]),old_n[target],t)
                            needed=footprints[label]/spacing-EPS;branch(free,C(needed),t)
                            if free[0]<needed:continue
                    branch(offered,C(EPS),t)
                    if offered[0]>EPS:
                        room=receiving[target];branch(room,C(EPS),t)
                        if room[0]>EPS:
                            if not len(requests[target]):targets.append(target)
                            requests[target].append((source,label,offered[0],offered[1],offered[2]))
                            budget=sub(budget,offered,t)
                branch(budget,C(EPS),t)
                if budget[0]<=EPS:break
        changed=np.zeros(ncells,np.bool_)
        for target in targets:
            req=requests[target];total=ordered([(p[2],p[3],p[4]) for p in req],t)
            fraction=low(C(1.),div(receiving[target],total,t),t)
            for source,label,dv,dr,dk in req:
                n=mul((dv,dr,dk),fraction,t);branch(n,C(EPS),t)
                if n[0]<=EPS:continue
                take_label(queues[source],label,n,indexed_lateral,groups,t);changed[source]=True
                stock_valid[source]=False
                packets=empty_packets();packets.append(packet(label,n))
                transfers.append((source,target,-1,packets));additions[target].extend(packets)
                sending[source]=sub(sending[source],n,t)
                key=(move_source_ids[source],target,1);movements[key]=add(lookup(movements,key),n,t)
            receiving[target]=high(C(0.),sub(receiving[target],mul(total,fraction,t),t),t)
        if indexed_lateral:
            for source in range(ncells):
                if changed[source]:
                    live=[p for p in queues[source] if p[1]>=0.]
                    queues[source].clear();queues[source].extend(live)
    active=np.ones(nq,np.bool_)
    while np.any(active):
        requests=[empty_requests() for _ in range(nt)]
        target_display=np.full(nt,-1,np.int64)
        for source in source_order:
            if not active[source]:continue
            q=queues[source]
            if not len(q):continue
            branch(sending[source],C(EPS),t)
            if sending[source][0]<=EPS:continue
            if source>=ncells:target,reason=external_targets[source-ncells],2
            else:target,reason=route(source,q[0][0],receiving,metadata,lateral_access,green,t)
            if target<0:blocked.append((source,reason));continue
            demand=C(0.);available=sending[source]
            if target>=ncells and source<ncells and signal[source][0]>=0.:
                available=low(available,signal[source],t);branch(available,C(EPS),t)
                if available[0]<=EPS:continue
            for p in q:
                nxt=external_targets[source-ncells] if source>=ncells else route(source,p[0],receiving,metadata,lateral_access,green,t)[0]
                if nxt!=target:break
                demand=add(demand,low(amount(p),sub(available,demand,t),t),t)
                limit=sub(available,C(EPS),t);branch(demand,limit,t)
                if demand[0]>=limit[0]:break
            if not len(requests[target]) and source<ncells and display_destination[source,q[0][0]]:
                target_display[target]=q[0][0]
            requests[target].append((source,0,demand[0],demand[1],demand[2]))
        active[:]=False
        for target in target_order:
            req=requests[target]
            if not len(req):continue
            total=fsum([(p[2],p[3],p[4]) for p in req],t)
            fraction=(low(C(1.),div(exit_room[target-ncells],total,t),t) if finite_exit else C(1.)) if target>=ncells else low(C(1.),div(receiving[target],total,t),t)
            for source,unused,dv,dr,dk in req:
                a=mul((dv,dr,dk),fraction,t);branch(a,C(EPS),t)
                if a[0]<=EPS:continue
                if not stock_valid[source]:cached_stock[source]=stock(queues[source],t)
                got=take(queues[source],a,cached_stock[source],t);stock_valid[source]=False
                transfers.append((source,target,target_display[target],got))
                sending[source]=sub(sending[source],a,t)
                if source>=ncells:
                    for p in got:
                        label=groups[p[0]];admitted[label]=add(lookup(admitted,label),amount(p),t)
                if target>=ncells:
                    if source<ncells and signal[source][0]>=0.:signal[source]=high(C(0.),sub(signal[source],a,t),t)
                    for p in got:
                        label=groups[p[0]];departed[label]=add(lookup(departed,label),amount(p),t)
                else:additions[target].extend(got)
                for p in got:
                    reason=2 if source>=ncells else route(source,p[0],receiving,metadata,lateral_access,green,t)[1]
                    key=(move_source_ids[source],target,reason);movements[key]=add(lookup(movements,key),amount(p),t)
                branch(fraction,C(1.-EPS),t)
                if fraction[0]>=1.-EPS:active[source]=True
            if target<ncells:receiving[target]=high(C(0.),sub(receiving[target],mul(total,fraction,t),t),t)
            elif finite_exit:exit_room[target-ncells]=high(C(0.),sub(exit_room[target-ncells],mul(total,fraction,t),t),t)
    for target in range(ncells):
        for p in additions[target]:
            append(queues[target],p[0],amount(p),groups,t)
            if p[1]>EPS:stock_valid[target]=False
    if do_compact:
        for i in range(ncells):compact(queues[i],behaviors,groups,t);stock_valid[i]=False
    final_n=[cached_stock[i] if stock_valid[i] else stock(queues[i],t) for i in range(ncells)]
    vehicle_seconds=add(vehicle_seconds,div(add(ordered(old_n,t),ordered(final_n,t),t),C(2.),t),t)
    now={0:C(0.)};now.clear()
    for i in range(ncells):
        for label,a in counts(queues[i],groups,t).items():
            now[label]=add(a,now[label],t) if label in now else a
    labels=set(now)|set(initial)|set(admitted)|set(departed)
    for label in labels:
        residual=add(sub(sub(lookup(now,label),lookup(initial,label),t),lookup(admitted,label),t),lookup(departed,label),t)
        branch(residual,C(0.),t)
        absolute=residual if residual[0]>=0. else mul(residual,C(-1.),t)
        branch(absolute,C(1e-7),t)
        if absolute[0]>1e-7:raise ArithmeticError('Destination/vehicle conservation failed')
    for i,n in enumerate(final_n):
        branch(n,C(-EPS),t)
        valid=n[0]>=-EPS
        if valid:branch(n,C(cap[i]+1e-7),t);valid=n[0]<=cap[i]+1e-7
        if not valid:raise ArithmeticError('Finite lane cell storage failed')
    return transfers,blocked,initial_send,initial_recv,final_n,vehicle_seconds


@njit(cache=True)
def pack_queues(v,r,k,ids,lengths):
    queues=List.empty_list(QUEUE_TYPE)
    for i in range(len(lengths)):
        q=empty_packets()
        for j in range(lengths[i]):q.append((ids[i,j],v[i,j],r[i,j],k[i,j]))
        queues.append(q)
    return queues


@njit(cache=True)
def unpack_queues(queues):
    width=max([len(q) for q in queues]+[0]);n=len(queues)
    v=np.zeros((n,width));r=np.zeros((n,width),np.int64);k=np.zeros((n,width),np.bool_)
    ids=np.zeros((n,width),np.int64);lengths=np.empty(n,np.int64)
    for i,q in enumerate(queues):
        lengths[i]=len(q)
        for j,p in enumerate(q):ids[i,j],v[i,j],r[i,j],k[i,j]=p
    return v,r,k,ids,lengths


REASONS=('forward','lateral','entry','exit','unrouted_exit','signal','past_turn','lane_access','unresolved_continuation')


def step(urban,external,exit_receiving,indexed_lateral):
    """Enter/leave the object boundary once for a complete physical step."""
    started=time.perf_counter()
    from evaluation.controllers.sdmpc_prediction_cache import active
    cache=active()
    owner=cache.urban_pipelines.get(urban)
    if owner is None:owner=Owner(urban);cache.urban_pipelines[urban]=owner
    result=owner.step(urban,external,exit_receiving,indexed_lateral)
    STATS['calls']+=1;STATS['wall_sec']+=time.perf_counter()-started
    return result


class Owner:
    def __init__(self,urban):
        self.labels={};self.names=[];self.workspace=None;self.meta_key=None
        self.identities={};self.identity_names=[];self.groups=[]
        self.urban=urban;self.native=None;self.pack=None;self.movement_sources=[]
        self.original_type=type(urban)
        self.changed=set();self.exposed=set();self.pending_public=set()

    def export_cell(self,index,buffer):
        from evaluation.controllers.sdmpc_tangent_urban_store import export_cell
        export_cell(self,index,buffer)

    def publish(self,name):
        from evaluation.controllers.sdmpc_tangent_urban_store import publish
        publish(self,name)

    def publish_all(self):
        for name in tuple(self.pending_public):self.publish(name)

    def restore_type(self):
        object.__setattr__(self.urban,'__class__',self.original_type)

    def label(self,label):
        # Numeric equality identifies the same vehicle, but int/float spelling
        # remains observable in route-event keys. Keep both contracts.
        key=(label,tuple(type(value) for value in label))
        if key not in self.labels:
            if label not in self.identities:
                self.identities[label]=len(self.identity_names);self.identity_names.append(label)
            self.labels[key]=len(self.names);self.names.append(label);self.groups.append(self.identities[label])
        return self.labels[key]

    def geometry(self,u,keys,targets):
        index={k:i for i,k in enumerate(keys)};ti={k:i for i,k in enumerate(targets)}
        n=len(keys);m=len(self.names)
        meta=np.full((n,m,4),-1,np.int64);required=np.full((n,m),-1,np.int64)
        display=np.zeros((n,m),np.bool_)
        neighbors=np.full((n,2),-1,np.int64);rates=np.zeros((n,m,3));fractions=np.zeros((n,m))
        behaviors=np.empty(m,np.int64);defer=np.zeros(m,np.bool_);footprints=np.full(m,-1.)
        behavior_ids={}
        for l,label in enumerate(self.names):
            dest=label[0];fallback=u.continuation and (label in u.unrouted_labels or label==(None,'unrouted'))
            behavior=(dest,fallback);behaviors[l]=behavior_ids.setdefault(behavior,len(behavior_ids))
            selected=getattr(u,'defer_destinations',None)
            defer[l]=getattr(u,'defer_mandatory_while_forward_open',False) and (selected is None or dest in selected)
            fp=getattr(u,'lateral_start_footprints',None)
            if fp:footprints[l]=fp.get(label[1],fp[None])
            for i,(road,lane,cell) in enumerate(keys):
                need=u.exits[dest]['lanes'] if road==71 and dest is not None else None
                mandatory=need and lane not in need and not(dest==10642 and cell>1)
                if mandatory:required[i,l]=index[(road,lane+(1 if lane<min(need) else -1),cell)]
                for side,other in enumerate((lane-1,lane+1)):
                    neighbors[i,side]=index.get((road,other,cell),-1)
                    if neighbors[i,side]>=0 and (not need or other in need):
                        rates[i,l,side]=u.exchange_rates.get((road,lane,other,dest),0.)
                rates[i,l,2]=sum(rates[i,l,:2]);fractions[i,l]=-math.expm1(-rates[i,l,2])
                target=None;reason='forward';signal=-1;other=-1;resolved=False
                if road==71:
                    deadline=1 if dest==10642 else len(u.edges[71])-2
                    if dest==10642 and cell>deadline:reason='past_turn';resolved=True
                    else:
                        if need and lane not in need:
                            other=index[(road,lane+(1 if lane<min(need) else -1),cell)]
                            if cell>=deadline:reason='lane_access';resolved=True
                        if not resolved and dest==10642 and lane==1 and cell==deadline:
                            target=('exit',10642);reason='exit';resolved=True
                        if not resolved and fallback and cell==1 and lane in u.exits[10642]['lanes'] and 10642 in u.fallback_exits:
                            target=('exit',10642);reason='unrouted_exit';resolved=True
                        if not resolved and cell==len(u.edges[road])-2:
                            signal=0 if lane<=3 else 1;resolved=True;reason='exit';target=('exit',dest)
                            display[i,l]=dest is not None
                            if fallback:
                                display[i,l]=False
                                possible=[d for d in u.fallback_exits if lane in u.exits[d]['lanes'] and u.exits[d]['position_m']>u.edges[71][-2]]
                                target=('exit',min(possible,key=lambda d:u.exits[d]['position_m'])) if possible else None
                                reason='unrouted_exit' if possible else 'unresolved_continuation'
                if not resolved:
                    if cell<len(u.edges[road])-2:target=(road,lane,cell+1)
                    elif road==126:target=(10641,lane,0)
                    elif road==10641:target=(71,lane+1,0)
                    else:raise ValueError('Missing urban array route')
                meta[i,l]=(ti[target] if target is not None else -1,REASONS.index(reason),other,signal)
        return meta,display,required,neighbors,rates,fractions,behaviors,defer,footprints

    def step(self,u,external,exit_receiving,indexed_lateral):
        from evaluation.controllers.sdmpc_tangent_urban_store import advance
        return advance(self,u,external,exit_receiving,indexed_lateral)


def amount_py(p):return p[1],p[2],p[3]
