"""Persistent native urban records; materialize only public reads/snapshots.

No store is attached to a TrafficState. The active prediction owns it. Public
mutators first synchronize their FIFO and mark that cell for re-import; public
counter access conservatively re-imports that counter on the next step.
"""
from collections import Counter, defaultdict
import math
import time
import numpy as np
from numba import njit, types
from numba.typed import List, Dict
from evaluation.controllers.sdmpc_tangent_fifo import Buffer, get, ad_module
from evaluation.controllers.sdmpc_tangent_transport import Packed

PUBLIC=('initial','admitted','departed','movements','vehicle_seconds')
STATS=dict(native_reuses=0,cell_exports=0,cell_imports=0,counter_exports=0,counter_imports=0)


def owner_of(urban):
    from evaluation.controllers.sdmpc_prediction_cache import active
    cache=active()
    if cache is None or not cache.urban_pipeline_enabled:return None
    owner=cache.urban_pipelines.get(urban)
    return owner if owner is not None and owner.native is not None else None


class PipelineBuffer(Buffer):
    def __getattribute__(self,name):
        if name in ('v','r','k','labels','n','view'):
            fields=object.__getattribute__(self,'__dict__')
            if fields.get('native_pending',False):fields['native_owner'].export_cell(fields['native_index'],self)
        return object.__getattribute__(self,name)

    def encode(self,value):
        fields=object.__getattribute__(self,'__dict__')
        if fields.get('native_pending',False):fields['native_owner'].export_cell(fields['native_index'],self)
        return super().encode(value)

    def dirty(self):
        super().dirty()
        fields=object.__getattribute__(self,'__dict__')
        if 'native_owner' in fields:fields['native_owner'].changed.add(fields['native_index'])


@njit(cache=True)
def queue_arrays(q):
    n=len(q);v=np.empty(n);r=np.empty(n,np.int64);k=np.empty(n,np.bool_);labels=np.empty(n,np.int64)
    for i,p in enumerate(q):labels[i],v[i],r[i],k[i]=p
    return v,r,k,labels


@njit(cache=True)
def native_refs(queues,initial,admitted,departed,movements,stocks,cost):
    refs=[0];packets=0
    for q in queues:
        packets+=len(q)
        for p in q:
            if p[3]:refs.append(p[2])
    for counter in (initial,admitted,departed):
        for a in counter.values():
            if a[2]:refs.append(a[1])
    for a in movements.values():
        if a[2]:refs.append(a[1])
    for a in stocks:
        if a[2]:refs.append(a[1])
    if cost[2]:refs.append(cost[1])
    return np.asarray(refs,np.int64),packets


@njit(cache=True)
def remap_value(a,start):return a[0],start-a[1]-1 if a[1]<0 else a[1],a[2]


@njit(cache=True)
def remap_owned(queues,initial,admitted,departed,movements,stocks,cost,start):
    packets=0
    for q in queues:
        packets+=len(q)
        for i,p in enumerate(q):
            if p[2]<0:q[i]=(p[0],p[1],start-p[2]-1,p[3])
    for counter in (initial,admitted,departed):
        for key in counter:counter[key]=remap_value(counter[key],start)
    for key in movements:movements[key]=remap_value(movements[key],start)
    for i in range(len(stocks)):stocks[i]=remap_value(stocks[i],start)
    return remap_value(cost,start),packets


def decode(owner,a):
    value,ref,kind=a
    if not kind:return float(value)
    node=owner.pack.resolve(ref)
    return ad_module().Dual._result(value,node,owner.pack.supports[node],owner.pack.trace)


def export_cell(owner,index,buffer):
    # Clear first so Buffer.ensure does not recursively request another export.
    fields=object.__getattribute__(buffer,'__dict__');fields['native_pending']=False
    v,r,k,labels=queue_arrays(owner.native[index]);buffer.ensure(len(v));buffer.n=len(v)
    buffer.v[:len(v)]=v;buffer.r[:len(v)]=r;buffer.k[:len(v)]=k
    buffer.labels=[owner.names[j] for j in labels]
    buffer.trace=owner.pack.trace;buffer.supports=owner.pack.supports
    STATS['cell_exports']+=1


def publish(owner,name):
    if name not in owner.pending_public:return
    from evaluation.controllers.sdmpc_tangent_urban import REASONS
    fields=object.__getattribute__(owner.urban,'__dict__')
    if name=='vehicle_seconds':value=decode(owner,owner.cost)
    elif name=='movements':
        value=Counter({(owner.movement_sources[a],owner.targets[b],REASONS[reason]):decode(owner,n)
            for (a,b,reason),n in owner.moves.items()})
    else:
        value=Counter({owner.identity_names[label]:decode(owner,n)
            for label,n in owner.counters[('initial','admitted','departed').index(name)].items()})
    fields[name]=value;owner.pending_public.remove(name);STATS['counter_exports']+=1


def pack_buffers(owner,buffers):
    from evaluation.controllers.sdmpc_tangent_urban import pack_queues
    n=len(buffers);width=max([b.n for b in buffers]+[0])
    v=np.zeros((n,width));r=np.zeros((n,width),np.int64);k=np.zeros((n,width),np.bool_)
    ids=np.zeros((n,width),np.int64);lengths=np.asarray([b.n for b in buffers],np.int64)
    for i,b in enumerate(buffers):
        v[i,:b.n]=b.v[:b.n];r[i,:b.n]=b.r[:b.n];k[i,:b.n]=b.k[:b.n]
        ids[i,:b.n]=[owner.label(label) for label in b.labels]
    return pack_queues(v,r,k,ids,lengths)


def advance(o,u,external,exit_receiving,indexed_lateral):
    from evaluation.controllers import sdmpc_tangent_urban as engine
    keys=list(u.cells);nc=len(keys);sources=keys+[('external',name) for name in external]
    targets=keys+[('exit',name) for name in u.exits]+[('exit',None)]
    if exit_receiving is not None and (set(exit_receiving)!=set(u.exits) or
            any(not math.isfinite(getattr(n,'value',n)) or n<0 for n in exit_receiving.values())):
        raise ValueError('Invalid physical urban exit receiving budget')
    first=o.native is None
    if not first and (tuple(keys)!=o.keys or targets!=o.targets):
        raise ValueError('Urban geometry changed inside one prediction')
    public=object.__getattribute__(u,'__dict__')
    changed=list(range(nc)) if first else sorted(o.changed)
    cells=list(u.cells.values());external_queues=[q for target,q in external.values()]
    if len({id(q) for q in cells+external_queues})!=len(cells)+len(external_queues):
        raise ValueError('Array transport requires distinct offered FIFO objects')
    cell_buffers=[get(cells[i]) for i in changed];external_buffers=[get(q) for q in external_queues]
    incoming=cell_buffers+external_buffers
    for b in incoming:
        for label in b.labels:o.label(label)
    refresh=set(PUBLIC) if first else set(o.exposed)
    for name in refresh & {'initial','admitted','departed'}:
        for label in public[name]:o.label(label)
    pack=Packed();counter_indices={name:pack.row(public[name].values())
        for name in ('initial','admitted','departed','movements') if name in refresh}
    changed_stock=pack.row([cells[i].stock for i in changed])
    cost_index=pack.row([public['vehicle_seconds']])[0] if 'vehicle_seconds' in refresh else None
    fraction_at=getattr(u.program,'service_fraction_at',None)
    signal_indices=pack.row([u.capacity_rate*fraction_at(u.time+1,2 if key[1]<=3 else 5,controller_offset_sec=u.offset)
        if fraction_at is not None and key[0]==71 and key[2]==len(u.edges[71])-2 else -1. for key in keys])
    exit_indices=pack.row([exit_receiving[d] if exit_receiving is not None else 0. for d in u.exits]+[0.])
    pack.arrays()
    for b in incoming:
        if b.trace is not None:
            if pack.trace is None:pack.trace=b.trace
            if pack.trace is not b.trace:raise ValueError('Urban arrays mixed prediction tapes')
            for ref in np.unique(b.r[:b.n][b.k[:b.n]]):pack.supports[int(ref)]=b.supports[int(ref)]
    if not first and o.pack.trace is not None:
        if pack.trace is None:pack.trace=o.pack.trace
        if pack.trace is not o.pack.trace:raise ValueError('Urban store changed prediction tapes')
    if pack.trace is not None and (pack.trace.frozen or ad_module().PRIMAL_GUARD):
        raise ValueError('Urban array mutation of read-only tape')
    def item(i):return float(pack.values[i]),int(pack.refs[i]),bool(pack.kinds[i])
    def values(indices):return List([item(i) for i in indices])
    value_type=types.Tuple((types.float64,types.int64,types.boolean))
    def counter(name):
        result=Dict.empty(types.int64,value_type)
        for label,i in zip(public[name],counter_indices[name]):result[o.identities[label]]=item(i)
        STATS['counter_imports']+=1
        return result
    if first:
        o.keys=tuple(keys);o.targets=targets;o.counters=[counter(name) for name in ('initial','admitted','departed')]
        o.stocks=values(changed_stock);o.cost=item(cost_index)
    else:
        STATS['native_reuses']+=1
        for j,name in enumerate(('initial','admitted','departed')):
            if name in refresh:o.counters[j]=counter(name)
        for j,i in enumerate(changed):o.stocks[i]=item(changed_stock[j])
        if cost_index is not None:o.cost=item(cost_index)
    for source in sources:
        if source not in o.movement_sources:o.movement_sources.append(source)
    if 'movements' in refresh:
        for a,b,reason in public['movements']:
            if a not in o.movement_sources:o.movement_sources.append(a)
    si={key:i for i,key in enumerate(o.movement_sources)};ti={key:i for i,key in enumerate(targets)}
    if 'movements' in refresh:
        o.moves=Dict.empty(types.UniTuple(types.int64,3),value_type)
        for (a,b,reason),i in zip(public['movements'],counter_indices['movements']):
            o.moves[si[a],ti[b],engine.REASONS.index(reason)]=item(i)
        STATS['counter_imports']+=1
    incoming_native=pack_buffers(o,incoming)
    if first:
        o.native=incoming_native;o.buffers=cell_buffers
        object.__setattr__(u,'__class__',type(u)._array_variant)
    else:
        for j,i in enumerate(changed):o.native[i]=incoming_native[j]
        while len(o.native)>nc:o.native.pop()
        for j in range(len(changed),len(incoming_native)):o.native.append(incoming_native[j])
    STATS['cell_imports']+=len(changed)
    o.changed.clear();o.exposed.clear()
    refs,npackets=native_refs(o.native,*o.counters,o.moves,o.stocks,o.cost)
    if not first:
        for ref in np.unique(refs):
            ref=int(ref)
            if ref not in pack.supports:pack.supports[ref]=o.pack.supports[ref]
    meta_key=(tuple(keys),tuple(targets),len(o.names),exit_receiving is not None)
    if o.meta_key!=meta_key:
        o.meta=o.geometry(u,keys,targets);o.meta_key=meta_key
        if exit_receiving is not None:
            meta=o.meta[0]
            for i,key in enumerate(keys):
                possible=[d for d,e in u.exits.items() if key[1] in e['lanes'] and e['position_m']>u.edges[key[0]][-2]]
                mask=meta[i,:,0]==ti['exit',None]
                if np.any(mask):meta[i,mask,0]=ti['exit',possible[0]] if len(possible)==1 else -2
    meta,display,required,neighbors,rates,fractions,behaviors,defer,footprints=o.meta
    size=max(8192,160*(npackets+len(o.names)+len(o.moves)+1))
    if o.workspace is None or len(o.workspace[1])<size:
        o.workspace=(np.zeros(4,np.int64),np.zeros((size,2),np.int64),np.zeros((size,2)),np.zeros((size,2),np.int64))
    o.workspace[0][:]=0
    green=np.asarray([u.program.state_at(u.time+1,sg,controller_offset_sec=u.offset)=='GREEN' for sg in (2,5)])
    started=time.perf_counter()
    result=engine.pipeline(o.native,nc,o.stocks,np.asarray([u.cap[x] for x in keys]),np.asarray([u.dx[x] for x in keys]),
        u.speed,u.wave,u.capacity_rate,values(signal_indices),green,values(exit_indices),exit_receiving is not None,
        meta,display,np.asarray(o.groups,np.int64),required,neighbors,rates,fractions,behaviors,
        u.lateral_access,indexed_lateral,u.compact_equal_behavior,defer,getattr(u,'prefer_more_receiving_space',False),footprints,u.spacing,
        np.asarray([ti[target] for target,q in external.values()],np.int64),
        np.asarray(sorted(range(len(sources)),key=lambda i:str(sources[i])),np.int64),
        np.asarray(sorted(range(len(targets)),key=lambda i:str(targets[i])),np.int64),
        np.asarray([si[source] for source in sources],np.int64),*o.counters,o.moves,o.cost,o.workspace)
    engine.STATS['kernel_sec']+=time.perf_counter()-started;engine.STATS['nodes']+=int(o.workspace[0][0])
    pack.finish(*o.workspace,np.empty(0,np.int64));o.pack=pack
    transfers,blocked,sending,receiving,final_n,cost=result
    o.stocks=List(final_n)
    o.cost,nout=remap_owned(o.native,*o.counters,o.moves,o.stocks,cost,pack.start)
    for i,b in enumerate(o.buffers):
        if first:
            b.__class__=PipelineBuffer;b.__dict__.update(native_owner=o,native_index=i)
        b.__dict__.update(native_pending=True,trace=pack.trace,supports=pack.supports,stock_value=decode(o,o.stocks[i]))
    for j,b in enumerate(external_buffers):
        export_cell(o,nc+j,b);b.dirty()
    u.last_sending_limits={key:decode(o,a) for key,a in zip(sources,sending)}
    u.last_receiving_limits={key:decode(o,a) for key,a in zip(keys,receiving)}
    u.last_transfers=[];accepted=defaultdict(list)
    for source,target,display_label,packets in transfers:
        out=tuple((o.names[p[0]],decode(o,engine.amount_py(p))) for p in packets)
        target_key=('exit',o.names[display_label][0]) if display_label>=0 else targets[target]
        u.last_transfers.append((sources[source],target_key,out))
        if source>=nc:accepted[sources[source][1]].extend(out)
    for source,reason in blocked:u.blocked_seconds[sources[source],engine.REASONS[reason]]+=1
    o.pending_public.update(('admitted','departed','movements','vehicle_seconds'))
    u.time+=1;u.checks+=1
    engine.STATS['packet_inputs']+=npackets;engine.STATS['packet_outputs']+=nout
    return dict(accepted)
