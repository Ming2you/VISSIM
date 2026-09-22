"""Query-owned numeric FIFO storage retained across physical transport stages.

Labels and ordering are unchanged. Kernels edit values and derivative references;
legacy objects are reconstructed only for their readers and state snapshots.
This is a partial plant backend, not a replacement for the network predictor.
"""
from array import array
from collections import Counter, deque
import math
import sys
import time
import numpy as np
from numba import njit
from evaluation.controllers.sdmpc_tangent_spatial import (
    _constant, _value, _add, _subtract, _minimum, _branch)
from evaluation.controllers.sdmpc_tangent_transport import _put, Packed

STATS=dict(buffers=0,kernel_calls=0,kernel_sec=0.,exports=0,snapshots=0,
           reads=0,buffer_mutation_reuses=0,workspace_allocations=0,
           generated_nodes=0,max_live_rows=0)


@njit(cache=True,fastmath=False)
def _take(v,r,k,n,amount,c,p,w,ties,outv,outr,outk):
    used=0
    while True:
        _branch(amount,_constant(1e-9),c,ties)
        if amount[0]<=1e-9 or used==n:break
        old=_value(v,r,k,used)
        moved=_minimum(amount,old,c,ties)
        _put(outv,outr,outk,used,moved)
        amount=_subtract(amount,moved,c,p,w)
        left=_subtract(old,moved,c,p,w)
        _put(v,r,k,used,left)
        _branch(left,_constant(1e-9),c,ties)
        if left[0]<=1e-9:used+=1
        else:
            # The original while rechecks the remaining request once.
            _branch(amount,_constant(1e-9),c,ties)
            if amount[0]>1e-9:
                raise ArithmeticError('Partially consumed FIFO still has a positive request')
            return used,used+1
    return used,used


@njit(cache=True,fastmath=False)
def _lateral(v,r,k,ids,alive,n,label,amount,indexed,c,p,w,ties):
    available=0.
    for j in range(n):
        if alive[j] and ids[j]==label:
            available+=v[j]
            if indexed:
                _branch(amount,_constant(available+1e-7),c,ties)
                if amount[0]<=available+1e-7:break
    _branch(amount,_constant(-1e-9),c,ties)
    invalid=amount[0]<-1e-9
    if not invalid:
        _branch(amount,_constant(available+1e-7),c,ties)
        invalid=amount[0]>available+1e-7
    if invalid:raise ArithmeticError('Lateral label overdraw')
    remaining=amount
    for j in range(n):
        if not alive[j] or ids[j]!=label:continue
        old=_value(v,r,k,j)
        moved=_minimum(old,remaining,c,ties)
        remaining=_subtract(remaining,moved,c,p,w)
        left=_subtract(old,moved,c,p,w)
        _branch(left,_constant(1e-9),c,ties)
        if left[0]>1e-9:
            # Unindexed take_label evaluates n-moved once for its test and
            # again for the retained fragment; keep that original tape order.
            if not indexed:left=_subtract(old,moved,c,p,w)
            _put(v,r,k,j,left)
        else:alive[j]=False
        if indexed:
            _branch(remaining,_constant(0.),c,ties)
            if remaining[0]==0.:break


@njit(cache=True,fastmath=False)
def _reduce(v,r,k,groups,n,size,c,p,w,ov,orr,ok):
    for j in range(size):_put(ov,orr,ok,j,_constant(0.))
    for j in range(n):
        group=groups[j]
        _put(ov,orr,ok,group,_add(_value(ov,orr,ok,group),_value(v,r,k,j),c,p,w))


def ad_module():return sys.modules.get('evaluation.controllers.sdmpc_tangent_reverse')


def enabled_cache():
    from evaluation.controllers.sdmpc_prediction_cache import active
    cache=active()
    return cache if cache is not None and cache.fifo_enabled else None


def get(queue,*,create=True):
    cache=enabled_cache()
    if cache is None:return None
    old=cache.array_fifos.get(queue)
    if old is None and create:
        old=Buffer(object.__getattribute__(queue,'__dict__')['q'])
        cache.array_fifos[queue]=old
    return old


class PacketView:
    """Read-only legacy view: all mutation goes through the checked FIFO API."""
    def __init__(self,buffer):self.buffer=buffer
    def __len__(self):return self.buffer.n
    def __iter__(self):
        b=self.buffer
        for j in range(b.n):yield (b.labels[j],b.number(j))
    def __getitem__(self,index):
        if not isinstance(index,int):raise TypeError('FIFO packet view requires an integer index')
        b=self.buffer;index=index+b.n if index<0 else index
        if not 0<=index<b.n:raise IndexError(index)
        return (b.labels[index],b.number(index))


class Buffer:
    def __init__(self,packets):
        self.trace=None;self.supports={0:0};self.n=0
        self.v=np.empty(8);self.r=np.zeros(8,dtype=np.int64);self.k=np.zeros(8,dtype=np.bool_)
        self.labels=[];self.stock_value=None;self.view=PacketView(self);self.mutations=0
        self.scratch=None
        self.replace(packets)
        STATS['buffers']+=1

    def ensure(self,n):
        if n<=len(self.v):return
        size=max(n,2*len(self.v))
        for field in ('v','r','k'):
            old=getattr(self,field);new=np.zeros(size,dtype=old.dtype);new[:self.n]=old[:self.n]
            setattr(self,field,new)

    def encode(self,value):
        ad=ad_module()
        if ad is not None and isinstance(value,ad.Dual):
            if self.trace is None:self.trace=value.trace
            if self.trace is not value.trace:raise ValueError('Persistent FIFO mixed reverse tapes')
            self.supports[value.node]=value.support
            return value.value,value.node,True
        value=float(value)
        if not math.isfinite(value):raise ValueError('Nonfinite persistent FIFO value')
        return value,0,False

    def number(self,j):return self.decode(self.v[j],self.r[j],self.k[j])

    def decode(self,v,r,k):
        STATS['reads']+=1
        if not k:return float(v)
        return ad_module().Dual._result(v,int(r),self.supports[int(r)],self.trace)

    def dirty(self):
        self.stock_value=None;self.mutations+=1
        if self.mutations>1:STATS['buffer_mutation_reuses']+=1

    def replace(self,packets):
        packets=list(packets);self.ensure(len(packets));self.labels=[]
        for j,(label,amount) in enumerate(packets):
            self.labels.append(label);self.v[j],self.r[j],self.k[j]=self.encode(amount)
        self.n=len(packets);self.dirty()
        STATS['max_live_rows']=max(STATS['max_live_rows'],self.n)

    def materialize(self):
        STATS['exports']+=1
        return deque([label,amount] for label,amount in self.view)

    def stock(self):
        ad=ad_module();guard=bool(ad is not None and ad.PRIMAL_GUARD)
        if self.stock_value is not None and not guard:return self.stock_value
        total=math.fsum(self.v[:self.n])
        active=np.flatnonzero(self.k[:self.n])
        if not len(active):result=total
        elif guard:result=ad.Dual._result(total,0,0,self.trace)
        else:
            first=int(active[0]);node=int(self.r[first]);support=self.supports[node]
            if self.trace.frozen:raise ValueError('Frozen persistent FIFO tape')
            for j in active[1:]:
                other=int(self.r[j]);support|=self.supports[other]
                # Exactly MathProxy.fsum's direct ordered node chain.
                node=self.trace.node(node,other,1.,1.)
            self.supports[node]=support
            result=ad.Dual._result(total,node,support,self.trace)
        if not guard:self.stock_value=result
        return result

    def writable(self):
        ad=ad_module()
        if self.trace is not None and (self.trace.frozen or ad.PRIMAL_GUARD):
            raise ValueError('Persistent FIFO mutation inside frozen/read-only trace')

    def workspace(self):
        self.writable()
        size=64+8*self.n
        if self.scratch is None or len(self.scratch[1])<size:
            self.scratch=(np.zeros(4,dtype=np.int64),np.zeros((size,2),dtype=np.int64),
                np.zeros((size,2)),np.zeros((size,2),dtype=np.int64))
            STATS['workspace_allocations']+=1
        self.scratch[0][:]=0
        return self.scratch

    def finish(self,workspace,*outputs):
        c,p,w,ties=workspace;n=int(c[0]);STATS['generated_nodes']+=n
        if self.trace is None:
            if n or c[1] or c[2]:raise ValueError('Scalar FIFO unexpectedly created a tape')
            return
        pack=Packed();pack.trace=self.trace;pack.supports=self.supports
        pack.finish(c,p,w,ties,np.empty(0,dtype=np.int64))
        self.supports=pack.supports
        for refs in (self.r[:self.n],*outputs):
            negative=refs<0;refs[negative]=pack.start-refs[negative]-1

    def append(self,label,amount):
        # Public input guards execute in the original, instrumented FIFO method.
        encoded=self.encode(amount);self.writable()
        if self.n and self.labels[-1]==label:
            value=self.number(self.n-1)+amount
            self.v[self.n-1],self.r[self.n-1],self.k[self.n-1]=self.encode(value)
        else:
            self.ensure(self.n+1);self.labels.append(label)
            self.v[self.n],self.r[self.n],self.k[self.n]=encoded;self.n+=1
        self.dirty();STATS['max_live_rows']=max(STATS['max_live_rows'],self.n)

    def take(self,amount):
        encoded=self.encode(amount);ws=self.workspace()
        ov=np.empty(self.n);orr=np.zeros(self.n,dtype=np.int64);ok=np.zeros(self.n,dtype=np.bool_)
        started=time.perf_counter()
        removed,emitted=_take(self.v,self.r,self.k,self.n,encoded,*ws,ov,orr,ok)
        STATS['kernel_sec']+=time.perf_counter()-started;STATS['kernel_calls']+=1
        self.finish(ws,orr)
        result=[(self.labels[j],self.decode(ov[j],orr[j],ok[j])) for j in range(emitted)]
        if removed:
            for field in ('v','r','k'):
                a=getattr(self,field);a[:self.n-removed]=a[removed:self.n]
            del self.labels[:removed];self.n-=removed
        self.dirty()
        return result

    def reduce(self,groups,labels):
        groups=np.asarray(groups,dtype=np.int64);size=len(labels);ws=self.workspace()
        ov=np.empty(size);orr=np.zeros(size,dtype=np.int64);ok=np.zeros(size,dtype=np.bool_)
        started=time.perf_counter()
        _reduce(self.v,self.r,self.k,groups,self.n,size,*ws[:3],ov,orr,ok)
        STATS['kernel_sec']+=time.perf_counter()-started;STATS['kernel_calls']+=1
        self.finish(ws,orr)
        return ov,orr,ok

    def counts(self):
        ad=ad_module()
        if ad is not None and ad.PRIMAL_GUARD:
            result=Counter()
            for label,n in self.view:result[label]+=n
            return result
        labels={}
        groups=[labels.setdefault(label,len(labels)) for label in self.labels]
        ov,orr,ok=self.reduce(groups,labels)
        return Counter({label:self.decode(ov[j],orr[j],ok[j]) for label,j in labels.items()})

    def compact(self,behavior):
        labels=[];groups=[];run={};previous=object()
        for label in self.labels:
            key=behavior(label)
            if key!=previous:run={};previous=key
            if label not in run:run[label]=len(labels);labels.append(label)
            groups.append(run[label])
        ov,orr,ok=self.reduce(groups,labels)
        self.n=len(labels);self.labels=labels
        self.v[:self.n]=ov;self.r[:self.n]=orr;self.k[:self.n]=ok;self.dirty()

    def lateral(self,indexed=False):return Lateral(self,indexed)


class Lateral:
    def __init__(self,buffer,indexed):
        self.buffer=buffer;self.indexed=indexed;self.closed=False
        self.ids_map={};self.ids=np.asarray([self.ids_map.setdefault(label,len(self.ids_map))
            for label in buffer.labels],dtype=np.int64)
        self.alive=np.ones(buffer.n,dtype=np.bool_)

    def take(self,label,amount):
        if self.closed:raise ValueError('Closed lateral FIFO phase')
        b=self.buffer;encoded=b.encode(amount);ws=b.workspace()
        started=time.perf_counter()
        _lateral(b.v,b.r,b.k,self.ids,self.alive,b.n,self.ids_map.get(label,-1),encoded,
                 self.indexed,*ws)
        STATS['kernel_sec']+=time.perf_counter()-started;STATS['kernel_calls']+=1
        b.finish(ws)
        return [(label,amount)]

    def commit(self):
        if self.closed:raise ValueError('Closed lateral FIFO phase')
        b=self.buffer;indices=np.flatnonzero(self.alive)
        for field in ('v','r','k'):
            a=getattr(b,field);a[:len(indices)]=a[indices]
        b.labels=[b.labels[j] for j in indices];b.n=len(indices);b.dirty();self.closed=True
