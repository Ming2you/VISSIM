"""Experimental opt-in screening; never removes traffic states or controls."""
import math
import time
import numpy as np

STEPS={'green':1.,'offset':1.,'meter':2.,'vsl':10.}

def group(axis):
    return (axis['kind'],axis['key']) if axis['kind'] in ('meter','vsl') else ('signal',axis['owner'])

def select(coord, reference, cost_jacobian, resource_jacobian, threshold):
    started=time.perf_counter(); threshold=float(threshold)
    if not math.isfinite(threshold) or threshold<0: raise ValueError('Invalid adaptive threshold')
    n=len(coord.axes); cost=np.asarray(cost_jacobian,dtype=float); res=np.asarray(resource_jacobian,dtype=float)
    if cost.ndim!=2 or res.ndim!=2 or cost.shape[1]!=n or res.shape[1]!=n or not np.isfinite(cost).all() or not np.isfinite(res).all():
        raise ValueError('Incomplete initial sensitivity')
    scores={}; conservative=set()
    for j,a in enumerate(coord.axes):
        key=group(a);scores.setdefault(key,0.)
        if a.get('block',0)!=0: continue
        val=abs(float(cost[:,j].sum()))*STEPS[a['kind']]/float(a['scale'])
        scores[key]=max(scores[key],val)
        # A zero local derivative at an inactive VSL/open meter is not a proof
        # that a finite physical command has no effect. Keep it for the audit.
        if a['kind'] in ('vsl','meter') and not np.any(cost[:,j]) and not np.any(res[:,j]):
            conservative.add(key)
    selected={key for key,value in scores.items() if value>=threshold}|conservative
    if not selected: selected={max(scores,key=scores.get)}
    z=coord.encode(reference);active=[];inactive=[]
    for j,a in enumerate(coord.axes):
        if group(a) in selected:active.append(j)
        else:
            if not coord.lower[j]-1e-9<=z[j]<=coord.upper[j]+1e-9: raise ValueError('Invalid protected seed')
            coord.lower[j]=coord.upper[j]=z[j];inactive.append(j)
    coord.validate(reference)
    return dict(schema='adaptive-lever-selection/experimental-v1',threshold=threshold,
        selection_cost_sec=time.perf_counter()-started,selected_groups=sorted([list(x) for x in selected]),
        fixed_groups=sorted([list(x) for x in scores if x not in selected]),
        conservative_zero_response_groups=sorted([list(x) for x in conservative]),
        scores={'/'.join(k):v for k,v in scores.items()},active_axes=active,fixed_axes=inactive,
        scope='screen actuation only; complete network dynamics, objectives and physical constraints preserved')

def select_lagrangian(coord, reference, cost_jacobian, resource_jacobian, threshold,
                      *, residual, tolerance, dual, dual_step, resource_scale, proximal, qp_options, mandatory_groups=(), vsl_probe=None):
    """One current-cap dual update followed by groupwise feasible QP scoring.

    Resource sensitivities are scaled exactly as in the main coordinator. The
    updated multiplier is a single projected dual step, not a KKT certificate.
    Group QPs use linear signal/box constraints; plant checks remain mandatory.
    """
    from evaluation.controllers import sdmpc_central as central
    from evaluation.controllers.sdmpc import solve_qp
    started=time.perf_counter()
    costs=np.asarray(cost_jacobian,float);A=np.asarray(resource_jacobian,float)/np.asarray(resource_scale,float)[:,None]
    c=np.asarray(residual,float);eps=np.asarray(tolerance,float);dual=np.asarray(dual,float)
    if costs.shape[1]!=len(coord.axes) or A.shape[1]!=len(coord.axes) or not np.isfinite(costs).all() or not np.isfinite(A).all():
        raise ValueError('Invalid sensitivity matrices')
    z=coord.encode(reference); total=costs.sum(axis=0); proposal=np.zeros(len(z)); initial=central.signed_prices(dual)
    def subproblem(ix,gradient):
        G=coord.G[:,ix];active=np.any(G!=0,axis=1)
        return solve_qp(np.zeros(len(ix)),gradient,proximal,coord.lower[ix]-z[ix],coord.upper[ix]-z[ix],
                        G[active],(coord.glo-coord.G@z)[active],(coord.ghi-coord.G@z)[active],qp_options)
    for owner in coord.owners:
        ix=np.array([j for j,a in enumerate(coord.axes) if a['owner']==owner],dtype=int)
        if not len(ix):continue
        proposal[ix],receipt=subproblem(ix,total[ix]+(A.T@initial)[ix])
        if not receipt['success']:raise ValueError('Pre-selection owner QP failed: '+str(owner))
    updated=central.update_duals(dual,c+A@proposal,eps,dual_step,caps=True)
    prices=central.signed_prices(updated); g=total+A.T@prices
    if vsl_probe is None:
        raise ValueError('Finite-step VSL screening requires the prediction callback')
    vsl_scores,vsl_details=vsl_probe(prices,proximal,resource_scale)
    groups={};conservative=set()
    for j,a in enumerate(coord.axes):
        if a.get('block',0)!=0:continue
        key=group(a);groups.setdefault(key,[]).append(j)
        # Ramp zero-response protection remains unchanged. A VSL with a zero
        # local response is not automatically selected in this experiment.
        if a['kind'] == 'meter' and not np.any(costs[:,j]) and not np.any(resource_jacobian[:,j]):conservative.add(key)
    scores={}; group_steps={}; failed_groups={}
    for key,indices in groups.items():
        ix=np.asarray(indices,dtype=int)
        if key[0] == 'vsl':
            if key not in vsl_scores or not np.isfinite(vsl_scores[key]):
                raise ValueError('Missing finite-step VSL score: '+str(key))
            scores[key]=float(vsl_scores[key])
            group_steps['/'.join(key)]=vsl_details['/'.join(key)]
            continue
        step,receipt=subproblem(ix,g[ix])
        if not receipt['success']:
            # Score is unknown, not zero: retain the affected group and
            # record the failure, then perform the normal full validation.
            scores[key]=None
            failed_groups['/'.join(key)]=dict(receipt)
            continue
        scores[key]=max(0.,-float(g[ix]@step+.5*proximal*(step@step)))
        group_steps['/'.join(key)]=step.tolist()
    protection_changed={tuple(k) for k in mandatory_groups}
    if not protection_changed.issubset(scores):raise ValueError('Protection group not represented')
    mandatory={k for k in protection_changed if k[0] not in ('signal','vsl')}
    selected={k for k,v in scores.items() if v is not None and v>=float(threshold)}|conservative|{k for k,v in scores.items() if v is None}|mandatory
    if not selected:
        raise ValueError('No groups selected; retain verified prior/safe command')
    active=[];inactive=[]
    for j,a in enumerate(coord.axes):
        if group(a) in selected:active.append(j)
        else:coord.lower[j]=coord.upper[j]=z[j];inactive.append(j)
    coord.validate(reference)
    return dict(schema='adaptive-lagrangian-screen/experimental-v1',threshold=float(threshold),
        selection_cost_sec=time.perf_counter()-started,selected_groups=sorted([list(k) for k in selected]),
        fixed_groups=sorted([list(k) for k in scores if k not in selected]),active_axes=active,fixed_axes=inactive,
        conservative_zero_response_groups=sorted([list(k) for k in conservative]),
        mandatory_protection_groups=sorted([list(k) for k in mandatory]),
        protection_changed_groups=sorted([list(k) for k in protection_changed]),
        vsl_score_method='full_prediction_adjacent_legal_single_block',
        scores={'/'.join(k):v for k,v in scores.items()},group_steps=group_steps,failed_group_qps=failed_groups,
        initial_dual=dual.tolist(),updated_dual=updated.tolist(),initial_residual_scaled=c.tolist(),
        proposed_residual_scaled=(c+A@proposal).tolist(),tolerance_scaled=eps.tolist(),
        scope='first-block groupwise proximal Lagrangian predicted decrease; actuator bounds and signal constraints; one approximate dual update; full dynamics retained')
