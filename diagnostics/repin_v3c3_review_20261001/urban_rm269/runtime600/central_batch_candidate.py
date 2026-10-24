"""Diagnostic only: share tape reads across independent tangent columns.

No change to the running benchmark or the production controller. Each column
retains its own seed order and multiply/add order. Peak tangent elements stay
at or below the existing workers-times-tape allocation.
"""
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from numba import njit
from evaluation.controllers.sdmpc_tangent_constraints import _mark_ancestors

mark=njit(cache=True,nogil=True)(_mark_ancestors)

@njit(cache=True,nogil=True,fastmath=False)
def sweep(p1,p2,w1,w2,sn,sa,sw,outputs,axes,starts):
    tangent=np.zeros((len(p1),len(axes)),dtype=np.float64)
    for k in range(len(sn)):
        for j in range(len(axes)):
            if sa[k]==axes[j]:tangent[sn[k],j]+=sw[k]
    for i in range(min(starts),len(p1)):
        a,b,x,y=p1[i],p2[i],w1[i],w2[i]
        for j in range(len(axes)):
            if i>=starts[j]:tangent[i,j]+=x*tangent[a,j]+y*tangent[b,j]
    return tangent[outputs]

def columns(arrays,unique,n,workers,width=4):
    p1,p2,w1,w2,sn,sa,sw=arrays
    live=np.zeros(len(p1),dtype=np.uint8);live[unique]=1
    mark(p1,p2,live);live[0]=1
    keep=np.flatnonzero(live);remap=np.zeros(len(p1),dtype=np.int64)
    remap[keep]=np.arange(len(keep),dtype=np.int64)
    seeds=live[sn].astype(bool)
    compact=(np.ascontiguousarray(remap[p1[keep]]),np.ascontiguousarray(remap[p2[keep]]),
             np.ascontiguousarray(w1[keep]),np.ascontiguousarray(w2[keep]),
             np.ascontiguousarray(remap[sn[seeds]]),np.ascontiguousarray(sa[seeds]),np.ascontiguousarray(sw[seeds]))
    outputs=np.ascontiguousarray(remap[unique])
    finite=bool(np.isfinite(compact[2]).all() and np.isfinite(compact[3]).all())
    start={}
    for node,axis in zip(compact[4].tolist(),compact[5].tolist()):start[axis]=min(start.get(axis,node),node)
    if not finite:start={axis:1 for axis in range(n)}
    axes=sorted(start)
    width=max(1,min(width,workers))
    groups=[np.asarray(axes[j:j+width],dtype=np.int64) for j in range(0,len(axes),width)]
    sweep(*(a[:1] if i<4 else a[:0] for i,a in enumerate(compact)),np.zeros(1,dtype=np.int64),np.array([0]),np.array([1]))
    def group(g):return g,sweep(*compact,outputs,g,np.array([max(1,start[int(a)]) for a in g],dtype=np.int64))
    result=np.zeros((len(unique),n),dtype=np.float64)
    with ThreadPoolExecutor(max_workers=max(1,workers//width)) as pool:
        for axes,values in pool.map(group,groups):result[:,axes]=values
    return result
