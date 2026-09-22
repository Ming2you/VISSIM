"""Lossless immutable column storage for completed primal audit records.

All checks still run at their original allocation sites. Numeric columns are
IEEE doubles with no rounding; identities and source order are retained. The
public response is reconstructed with the original dictionaries and row order.
Transfers (which may carry AD values) keep their original pickle representation.
"""
from array import array
from dataclasses import dataclass
from functools import wraps
import pickle
import numpy as np


# Only isolated scalar/tangent witnesses compare all saved traffic states.
# Native-actuator candidate queries keep the cheaper existing pickle path.
WITNESS_PROCESS = False


def compact_enabled(cfg):
    return WITNESS_PROCESS and (getattr(cfg.network,'sdmpc_options',None) or {}).get('compact_audit',False)


def guard(function):
    """Only for the three audited read-only checks below, never a flow law."""
    @wraps(function)
    def wrapped(*args,**kwargs):
        from evaluation.controllers import sdmpc_tangent_reverse as ad
        previous=ad.PRIMAL_GUARD
        ad.PRIMAL_GUARD=True
        try:
            result=function(*args,**kwargs)
            return ad.primal(result) if isinstance(result,ad.Dual) else result
        finally:
            ad.PRIMAL_GUARD=previous
    return wrapped


def install_guards():
    from evaluation.controllers import physical_ramp_boundary as ramps,route_choice_corridor as routes
    # _stocks has no side effects or stock cache. _check and _known_check
    # inspect tags without initializing, copying or updating a traffic state.
    ramps.PhysicalRampBoundary._check_conservation=guard(ramps.PhysicalRampBoundary._check_conservation)
    routes._check=guard(routes._check)
    routes._known_check=guard(routes._known_check)

ALLOCATION_KEYS = ('stage','start_sec','end_sec','kind','resource','available_veh',
                   'accepted_by_source_veh','accepted_total_veh','exceedance_veh')
BOUND_KEYS = ('stage','start_sec','end_sec','kind','resource','value_veh','upper_veh')


def _finite(values):
    if not np.isfinite(values).all():
        raise ValueError('Nonfinite compact audit value')


def _numeric_mask(values):
    mask=0
    for i,value in enumerate(values):
        if type(value) is float:
            continue
        if type(value) is int and abs(value)<=2**53:
            mask|=1<<i
        else:
            raise ValueError('Compact audit requires plain primal numbers without precision loss')
    return mask


@dataclass(frozen=True, slots=True, eq=False)
class AuditBlock:
    transfers: bytes
    allocation_ids: tuple
    allocation_values: bytes
    bound_ids: tuple
    bound_values: bytes

    def __deepcopy__(self, memo):
        return self

    def unpack(self):
        allocations=[]
        values=iter(np.frombuffer(self.allocation_values,dtype=np.float64).tolist())
        for stage,kind,resource,sources,mask in self.allocation_ids:
            start,end,available,total,exceedance=next(values),next(values),next(values),next(values),next(values)
            accepted=dict(zip(sources,values))
            if mask:
                start,end,available,total,exceedance=[int(v) if mask&(1<<i) else v
                    for i,v in enumerate((start,end,available,total,exceedance))]
                for i,key in enumerate(sources,5):
                    if mask&(1<<i):accepted[key]=int(accepted[key])
            allocations.append(dict(stage=stage,start_sec=start,end_sec=end,kind=kind,resource=resource,
                available_veh=available,accepted_by_source_veh=accepted,
                accepted_total_veh=total,exceedance_veh=exceedance))
        bounds=[]
        values=iter(np.frombuffer(self.bound_values,dtype=np.float64).tolist())
        for stage,kind,resource,mask in self.bound_ids:
            start,end,value,upper=next(values),next(values),next(values),next(values)
            if mask:
                start,end,value,upper=[int(v) if mask&(1<<i) else v
                    for i,v in enumerate((start,end,value,upper))]
            bounds.append(dict(stage=stage,start_sec=start,end_sec=end,kind=kind,resource=resource,
                               value_veh=value,upper_veh=upper))
        return dict(transfers=pickle.loads(self.transfers),resource_allocations=allocations,state_bounds=bounds)


def pack(records):
    if records.keys() != {'transfers','resource_allocations','state_bounds'}:
        raise ValueError('Unknown compact audit record family')
    allocation_ids=[];allocation_values=array('d');bound_ids=[];bound_values=array('d')
    for row in records['resource_allocations']:
        if type(row) is not dict or tuple(row) != ALLOCATION_KEYS:
            raise ValueError('Unknown allocation schema for compact audit')
        stage,kind,resource=[row[k] for k in ('stage','kind','resource')]
        sources=row['accepted_by_source_veh']
        if (any(type(v) is not str for v in (stage,kind,resource)) or type(sources) is not dict
                or any(type(k) is not str for k in sources)):
            raise ValueError('Compact audit requires plain named identities')
        values=[row[k] for k in ('start_sec','end_sec','available_veh','accepted_total_veh','exceedance_veh')]
        values.extend(sources.values())
        mask=_numeric_mask(values)
        allocation_ids.append((stage,kind,resource,tuple(sources),mask))
        allocation_values.extend(values)
    for row in records['state_bounds']:
        if type(row) is not dict or tuple(row) != BOUND_KEYS:
            raise ValueError('Unknown state bound schema for compact audit')
        identities=tuple(row[k] for k in ('stage','kind','resource'))
        values=[row[k] for k in ('start_sec','end_sec','value_veh','upper_veh')]
        if any(type(v) is not str for v in identities):
            raise ValueError('Compact state bounds require plain identities and primal values')
        mask=_numeric_mask(values)
        bound_ids.append((*identities,mask));bound_values.extend(values)
    _finite(np.frombuffer(allocation_values,dtype=np.float64))
    _finite(np.frombuffer(bound_values,dtype=np.float64))
    return AuditBlock(pickle.dumps(records['transfers'],protocol=5),tuple(allocation_ids),
                      allocation_values.tobytes(),tuple(bound_ids),bound_values.tobytes())


def error(a,b):
    """Return a numeric maximum, or None when the full recursive path is needed.

No tolerance and no rows are skipped. Identity/source order differences use
the original dict comparator, where mapping order is not a state difference.
Transfer comparison remains the original route/clock-aware ledger comparison.
"""
    if a.allocation_ids!=b.allocation_ids or a.bound_ids!=b.bound_ids:
        return None
    maximum=0.
    for x,y,expected in ((a.allocation_values,b.allocation_values,
                          sum(5+len(row[3]) for row in a.allocation_ids)),
                         (a.bound_values,b.bound_values,4*len(a.bound_ids))):
        xx,yy=np.frombuffer(x,dtype=np.float64),np.frombuffer(y,dtype=np.float64)
        if len(xx)!=expected or len(yy)!=expected:
            raise ValueError('Compact audit shape differs from its full identities')
        _finite(xx);_finite(yy)
        if len(xx):maximum=max(maximum,float(np.max(np.abs(xx-yy))))
    return maximum
