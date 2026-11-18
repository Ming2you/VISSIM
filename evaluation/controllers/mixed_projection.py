"""Bounded L1 projection onto actuator grids and linearized constraints.

One feasibility candidate only. Original nonlinear traffic checks remain
mandatory; optimality is not claimed when a solver limit is reached.
"""
import time
import numpy as np
from scipy.optimize import Bounds,LinearConstraint,milp
from scipy.sparse import csc_matrix,diags,eye,hstack,vstack

STEPS={'green':1.,'offset':1.,'meter':2.,'vsl':10.}

def project(coord,target,z,A,rlo,rhi,time_limit=3.):
    started=time.perf_counter();n=len(coord.axes);target=np.asarray(target,dtype=float);z=np.asarray(z,dtype=float)
    if target.shape!=(n,) or z.shape!=(n,) or not np.isfinite(target).all() or not np.isfinite(z).all():
        raise ValueError('Invalid projection anchor or target')
    unit=np.ones(n);integ=np.zeros(2*n,dtype=np.uint8);weight=np.empty(n)
    for j,a in enumerate(coord.axes):
        kind=a['kind'];scale=float(a['scale']);weight[j]=scale/STEPS[kind]
        if kind in ('meter','vsl'):
            grid=1. if kind=='meter' else 10.
            allowed=sorted(set(float(v) for v in a['allowed']))
            if not allowed or any(abs((v-a['reference_value'])/grid-round((v-a['reference_value'])/grid))>1e-8 for v in allowed):
                raise ValueError('Nonuniform or nonaligned actuator grid')
            steps=[round((v-a['reference_value'])/grid) for v in allowed]
            if steps != list(range(steps[0],steps[-1]+1)):
                raise ValueError('Grid has gaps; cannot use integer relaxation')
            unit[j]=grid/scale;integ[j]=1
    bounds=Bounds(np.r_[coord.lower/unit,np.zeros(n)],np.r_[coord.upper/unit,np.full(n,np.inf)])
    D=diags(unit,format='csc');I=eye(n,format='csc');Z=csc_matrix((len(coord.G),n));R=csc_matrix((len(A),n))
    rows=[hstack([csc_matrix(coord.G)@D,Z],format='csc'),hstack([csc_matrix(A)@D,R],format='csc'),
          hstack([D,-I],format='csc'),hstack([-D,-I],format='csc')]
    matrix=vstack(rows,format='csc');Az=A@z
    low=np.r_[coord.glo,rlo+Az,np.full(n,-np.inf),np.full(n,-np.inf)]
    high=np.r_[coord.ghi,rhi+Az,target,-target]
    res=milp(np.r_[np.zeros(n),weight],integrality=integ,bounds=bounds,
             constraints=LinearConstraint(matrix,low,high),
             options={'time_limit':float(time_limit),'mip_rel_gap':0.01})
    record=dict(seconds=time.perf_counter()-started,status=int(res.status),message=str(res.message),
        solver_success=bool(res.success),mip_gap=float(res.mip_gap) if getattr(res,'mip_gap',None) is not None else None,
        objective=float(res.fun) if res.fun is not None else None,integer_axes=int(integ.sum()),
        scope='L1 normalized distance; actuator grids and linearized constraints only')
    if res.x is None:return None,record
    point=unit*np.asarray(res.x[:n]);residual=A@(point-z)
    if (not np.isfinite(point).all() or not coord.valid(point,tolerance=1e-7)
            or np.any(residual<rlo-1e-7) or np.any(residual>rhi+1e-7)):
        record['rejected']='linear feasibility check';return None,record
    return point,record
