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


def _probe_tape_vectors(p1,p2,w1,w2,seeds,axes,weights,axis,outputs):
    """One-axis JVP and summed-output adjoint; diagnostic only."""
    tangent=np.zeros(len(p1),dtype=np.float64)
    adjoint=np.zeros(len(p1),dtype=np.float64)
    for j in range(len(seeds)):
        if axes[j]==axis:tangent[seeds[j]]+=weights[j]
    for j in range(1,len(p1)):
        tangent[j]+=w1[j]*tangent[p1[j]]+w2[j]*tangent[p2[j]]
    for node in outputs:
        if node:adjoint[node]+=1.
    for j in range(len(p1)-1,0,-1):
        value=adjoint[j]
        if value:
            if p1[j]:adjoint[p1[j]]+=value*w1[j]
            if p2[j]:adjoint[p2[j]]+=value*w2[j]
    return tangent,adjoint


class ExactBranchProbe:
    """Observe existing choices on one private tape, never replace a branch.

    Node aliases mean a selected-node adjoint can include other uses. It is a
    connectivity filter, not causal attribution of the recorded min/max call.
    Compiled kernels report their Python emission site; that limit is explicit.
    """
    def __init__(self,trace,axis,max_records):
        import sys
        from evaluation.controllers import sdmpc_tangent_reverse as ad
        if type(axis) is not int or axis not in trace.steps or max_records!=200000:
            raise ValueError('Invalid bounded exact-branch diagnostic')
        self.trace=trace;self.axis=axis;self.rows=[];self.seen=0;self.dropped=0
        self.original=trace.branch;self.sites={};mask=1<<axis
        def observed(a,b,*,discrete=False,output_connected=False):
            result=self.original(a,b,discrete=discrete,output_connected=output_connected)
            if ad.PRIMAL_GUARD:return result
            aa=isinstance(a,ad.Dual);bb=isinstance(b,ad.Dual)
            support=(a.support if aa else 0)|(b.support if bb else 0)
            if not support&mask:return result
            av=ad.primal(a);bv=ad.primal(b)
            na=a.node if aa else 0;nb=b.node if bb else 0
            if av!=bv or na==nb:return result
            self.seen+=1
            if len(self.rows)>=max_records:
                self.dropped+=1;return result
            frame=sys._getframe(1)
            for _ in range(8):
                if frame is None:break
                name=frame.f_code.co_filename.replace('\\','/')
                if not name.endswith(('/sdmpc_tangent_reverse.py','/sdmpc_dual.py','/sdmpc_tangent_summary.py')):break
                frame=frame.f_back
            if frame is None:site=('unknown','unknown',0);context={}
            else:
                site=(frame.f_code.co_filename.replace('\\','/'),frame.f_code.co_name,frame.f_lineno)
                local=frame.f_locals
                context={k:v for k,v in local.items() if k in ('time_sec','time_s','sim_sec','start_sec','end_sec','now','t0','t1','ramp','mid','road','cell','i','key','phase') and type(v) in (str,int,float)}
                state=local.get('state')
                if state is not None and type(getattr(state,'time_sec',None)) in (int,float):context['state_time_sec']=state.time_sec
            site_id=self.sites.setdefault(site,len(self.sites))
            self.rows.append((len(trace.p1),na,nb,av,output_connected,discrete,site_id,context))
            return result
        trace.branch=observed

    def finish(self,outputs,expected_derivative):
        import numba
        from collections import Counter
        from evaluation.controllers import sdmpc_tangent_reverse as ad
        self.trace.branch=self.original
        trace=self.trace
        vectors=[np.frombuffer(v,dtype=d) for v,d in ((trace.p1,np.int64),(trace.p2,np.int64),
            (trace.w1,np.float64),(trace.w2,np.float64),(trace.seed_nodes,np.int64),(trace.seed_axes,np.int64),(trace.seed_weights,np.float64))]
        output_nodes=np.array([v.node if isinstance(v,ad.Dual) else 0 for v in outputs],dtype=np.int64)
        tangent,adjoint=numba.njit(cache=False,fastmath=False)(_probe_tape_vectors)(*vectors,self.axis,output_nodes)
        actual=float(sum(tangent[n] for n in output_nodes));assert abs(actual-expected_derivative)<1e-7
        sites={v:dict(file=k[0],function=k[1],line=k[2]) for k,v in self.sites.items()}
        relevant=[];counts=Counter()
        for order,na,nb,value,connected,discrete,site,context in self.rows:
            da,db=float(tangent[na]),float(tangent[nb])
            if abs(da-db)<1e-10:continue
            counts[(site,'different_tangent')]+=1
            reaches=bool(adjoint[na]!=0 or adjoint[nb]!=0)
            if reaches:counts[(site,'output_node_connected')]+=1
            relevant.append(dict(node_order=order,a_node=na,b_node=nb,value=value,
                a_derivative=da,b_derivative=db,a_output_adjoint=float(adjoint[na]),b_output_adjoint=float(adjoint[nb]),
                minmax_call=connected,discrete=discrete,output_node_connected=reaches,site=sites[site],context=context))
        return dict(axis=self.axis,exact_dependent_comparisons=self.seen,recorded=len(self.rows),dropped=self.dropped,
            different_tangent_count=len(relevant),jvp_sum=actual,expected_derivative=expected_derivative,
            sites=[dict(**sites[s],different_tangent=counts[s,'different_tangent'],output_node_connected=counts[s,'output_node_connected']) for s in sites if counts[s,'different_tangent']],
            first_different_tangent=relevant[:100],
            first_output_connected=[r for r in relevant if r['output_node_connected']][:100],
            limitations=['Primal choices and every tape edge unchanged; this observer does not calculate directional derivatives.',
                'Exact comparisons only; near ties and discrete jumps away from equality are not screened.',
                'Selected-node aliases can have other output uses; connectivity is not per-call causal attribution.',
                'Compiled-array operations report their emission location; not every internal branch calls this Python hook.'])


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
