"""Experimental line/constraint intersection and quantization event handling.

Only a linearized feasible interval is computed. Physical feasibility and
objective improvement MUST still be evaluated by the original traffic model.
"""
import math
import numpy as np

def intersect_line(z,d,lower,upper,G,glo,ghi,A,rlo,rhi,tol=1e-9):
    z=np.asarray(z,dtype=float);d=np.asarray(d,dtype=float)
    if z.ndim!=1 or d.shape!=z.shape or not np.isfinite(z).all() or not np.isfinite(d).all():
        raise ValueError('Invalid line')
    lo,hi=0.,1.
    def intersect(values,slopes,lows,highs):
        nonlocal lo,hi
        for q,p,l,h in zip(values,slopes,lows,highs):
            if abs(p)<=1e-13:
                if q<l-tol or q>h+tol:raise ValueError('Line cannot satisfy a fixed constraint')
                continue
            a=(l-q)/p;b=(h-q)/p
            lo=max(lo,min(a,b));hi=min(hi,max(a,b))
    intersect(z,d,lower,upper)
    if len(G):intersect(G@z,G@d,glo,ghi)
    if len(A):intersect(np.zeros(len(A)),A@d,rlo,rhi)
    if hi<lo-tol or hi<0 or lo>1:raise ValueError('No linearized feasible line interval')
    lo=max(0.,lo);hi=min(1.,hi)
    if hi<lo:hi=lo
    return lo,hi

def target_alpha(lo,hi,gradient,d,proximal):
    """Minimize explicit local scalar proxy, not the nonlinear objective."""
    slope=float(np.dot(gradient,d));curvature=float(proximal*np.dot(d,d))
    if not math.isfinite(slope) or not math.isfinite(curvature) or curvature<0:
        raise ValueError('Invalid line objective')
    raw=(-slope/curvature if curvature>1e-18 else (hi if slope<0 else lo))
    return min(hi,max(lo,raw)),slope,curvature

def candidate_alphas(coord,z,d,lo,hi,target):
    """Order grid/phase-margin events by distance from the local target."""
    values={float(target),float(lo),float(hi)}
    slopes=[]
    for j,a in enumerate(coord.axes):
        speed=float(d[j]*a['scale'])
        if a['kind'] in ('green','offset') and abs(speed)>1e-10:slopes.append(abs(speed))
        if a['kind'] not in ('meter','vsl') or abs(speed)<=1e-10:continue
        anchor=float(a['reference_value']+z[j]*a['scale'])
        for boundary in a['allowed']:
            x=(float(boundary)-anchor)/speed
            if lo-1e-10<=x<=hi+1e-10:
                for value in (x,x-1e-9,x+1e-9):
                    if lo<=value<=hi:values.add(float(value))
    # Native phase values are rounded to 1 ms. This is a single conservative
    # margin candidate, not an assertion of exact nearest mixed-integer repair.
    if slopes:
        margin=min(.01,.0011/max(slopes))
        for value in (target-margin,target+margin):
            if lo<=value<=hi:values.add(float(value))
    return sorted(values,key=lambda x:(abs(x-target),-x))
