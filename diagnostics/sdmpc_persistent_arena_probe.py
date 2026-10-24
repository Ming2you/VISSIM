"""Lifecycle probe, NOT the VISSIM/METANET predictor or a speed benchmark.

A two-stock conservation fixture tests persistent values/node IDs across
request/allocation/residence stages and three control blocks. Its traffic
equations deliberately do not claim to substitute for the full network.
"""
import copy
from pathlib import Path
import sys
import numpy as np
from numba import njit
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers.sdmpc_tangent_spatial import (
    _constant,_value,_add,_subtract,_multiply,_divide,_minimum,_maximum)
from evaluation.controllers.sdmpc_tangent_transport import _put,Packed

# Slots are state registers. Node IDs address immutable historical operations;
# overwriting a register must never overwrite its previous derivative node.
QA,QB,FLOW,OUT,TTT,ARRIVED,COMPLETED,U0,U1,U2 = range(10)


@njit(cache=True,fastmath=False)
def request_stage(v,r,k,u,arrival,c,p,w,ties):
    q=_add(_value(v,r,k,QA),_constant(arrival),c,p,w)
    _put(v,r,k,QA,q)
    _put(v,r,k,ARRIVED,_add(_value(v,r,k,ARRIVED),_constant(arrival),c,p,w))
    demand=_minimum(_maximum(_constant(0.),q,c,ties),
        _maximum(_constant(0.),_value(v,r,k,u),c,ties),c,ties)
    _put(v,r,k,FLOW,demand)


@njit(cache=True,fastmath=False)
def allocation_stage(v,r,k,capacity,service,c,p,w,ties):
    room=_maximum(_constant(0.),_subtract(_constant(capacity),_value(v,r,k,QB),c,p,w),c,ties)
    flow=_minimum(_value(v,r,k,FLOW),room,c,ties)
    _put(v,r,k,FLOW,flow)
    _put(v,r,k,QA,_subtract(_value(v,r,k,QA),flow,c,p,w))
    _put(v,r,k,QB,_add(_value(v,r,k,QB),flow,c,p,w))
    departed=_minimum(_value(v,r,k,QB),_constant(service),c,ties)
    _put(v,r,k,OUT,departed)
    _put(v,r,k,QB,_subtract(_value(v,r,k,QB),departed,c,p,w))
    _put(v,r,k,COMPLETED,_add(_value(v,r,k,COMPLETED),departed,c,p,w))


@njit(cache=True,fastmath=False)
def residence_stage(v,r,k,c,p,w):
    n=_add(_value(v,r,k,QA),_value(v,r,k,QB),c,p,w)
    cost=_divide(n,_constant(3600.),c,p,w)
    _put(v,r,k,TTT,_add(_value(v,r,k,TTT),cost,c,p,w))


class Arena:
    def __init__(self,initial,controls,capacity,service,*,steps=450):
        if len(initial)!=2 or len(controls)!=3 or steps!=450:
            raise ValueError('Probe requires two stocks and three 150s blocks')
        self.pack=Packed()
        self.pack.row([*initial,0.,0.,0.,0.,0.,*controls])
        self.v,self.r,self.k=self.pack.arrays()
        self.capacity,self.service=capacity,service
        self.c=np.zeros(4,dtype=np.int64)
        # Initial small buffers exercise growing the tape without changing IDs.
        self.p=np.zeros((32,2),dtype=np.int64);self.w=np.zeros((32,2))
        self.ties=np.zeros((32,2),dtype=np.int64)
        self.discrete=np.zeros(32,dtype=np.int64)
        self.step=0;self.closed=False;self.exports=0;self.growths=0
        self.initial_mass=float(self.v[QA]+self.v[QB])
        self.conservation_error=0.
        self.register_addresses=tuple(x.ctypes.data for x in (self.v,self.r,self.k))

    def reserve(self):
        required=max(int(self.c[0]),int(self.c[1]))+32
        if required<=len(self.p):return
        size=max(required,2*len(self.p))
        def extend(a):
            b=np.zeros((size,*a.shape[1:]),dtype=a.dtype);b[:len(a)]=a;return b
        self.p,self.w,self.ties,self.discrete=[extend(a) for a in (self.p,self.w,self.ties,self.discrete)]
        self.growths+=1

    def advance(self,step,arrival):
        if self.closed or step!=self.step or not 0<=step<450:
            raise ValueError('Closed arena or noncontiguous prediction clock')
        self.reserve()
        u=U0+step//150
        request_stage(self.v,self.r,self.k,u,arrival,self.c,self.p,self.w,self.ties)
        allocation_stage(self.v,self.r,self.k,self.capacity,self.service,self.c,self.p,self.w,self.ties)
        residence_stage(self.v,self.r,self.k,self.c,self.p,self.w)
        self.step+=1
        error=abs(self.initial_mass+self.v[ARRIVED]-self.v[COMPLETED]-self.v[QA]-self.v[QB])
        self.conservation_error=max(self.conservation_error,error)
        if error>1e-9 or min(self.v[QA],self.v[QB]) < -1e-9 or self.v[QB]>self.capacity+1e-9:
            raise ArithmeticError('Probe violates conservation or shared storage')

    def snapshot(self):
        # Only a numeric snapshot: no endpoint model objects are reconstructed.
        return dict(step=self.step,values=self.v.copy(),refs=self.r.copy(),kinds=self.k.copy(),
                    tape_length=int(self.c[0]))

    def export(self):
        if self.closed:raise ValueError('Arena was already exported')
        self.pack.finish(self.c,self.p,self.w,self.ties,self.discrete)
        result=self.pack.restore(range(len(self.v)))
        self.exports+=1;self.closed=True
        return result


def reference(initial,controls,capacity,service,arrivals):
    from evaluation.controllers import sdmpc_tangent_reverse as ad
    q1,q2=initial;flow=out=ttt=arrived=completed=0.
    checkpoints=[]
    for step,arrival in enumerate(arrivals):
        q1+=arrival;arrived+=arrival
        intended=ad.minimum(ad.maximum(0.,q1),ad.maximum(0.,controls[step//150]))
        room=ad.maximum(0.,capacity-q2)
        flow=ad.minimum(intended,room)
        q1-=flow;q2+=flow
        out=ad.minimum(q2,service);q2-=out;completed+=out
        ttt+=(q1+q2)/3600.
        if (step+1)%150==0:
            checkpoints.append([q1,q2,flow,out,ttt,arrived,completed,*controls])
    return checkpoints
