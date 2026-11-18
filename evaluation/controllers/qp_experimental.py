"""Opt-in QP alternatives. No traffic model or control-state reduction."""
import time
import numpy as np

def violation(x,lower,upper,G,glo,ghi):
    if not np.isfinite(x).all():return float('inf')
    v=G@x
    return float(max(np.max(lower-x,initial=0.),np.max(x-upper,initial=0.),
                     np.max(glo-v,initial=0.),np.max(v-ghi,initial=0.)))

def fixed_reduce(solve,center,gradient,proximal,lower,upper,G,glo,ghi,options):
    center,gradient,lower,upper,glo,ghi=map(lambda x:np.asarray(x,dtype=float),(center,gradient,lower,upper,glo,ghi))
    G=np.asarray(G,dtype=float);fixed=lower==upper;free=~fixed
    if not np.any(fixed):return solve(center,gradient,proximal,lower,upper,G,glo,ghi,options)
    result=np.zeros(len(lower));result[fixed]=lower[fixed]
    if not np.any(free):
        err=violation(result,lower,upper,G,glo,ghi)
        return result,dict(success=bool(err<=1e-7),constraint_violation=err,iterations=0,
             message='all fixed; checked full constraints',reduced_free=0,reduced_fixed=int(fixed.sum()))
    A=G[:,free];shift=G[:,fixed]@result[fixed];lo=glo-shift;hi=ghi-shift
    empty=~np.any(A!=0,axis=1)
    if np.any(lo[empty]>1e-7) or np.any(hi[empty]<-1e-7):
        err=violation(result,lower,upper,G,glo,ghi)
        return result,dict(success=False,constraint_violation=err,iterations=0,
            message='fixed-only row inconsistent',reduced_free=int(free.sum()),reduced_fixed=int(fixed.sum()))
    prox=np.asarray(proximal); subprox=prox if prox.ndim==0 else prox[free]
    sol,info=solve(center[free],gradient[free],subprox,lower[free],upper[free],A[~empty],lo[~empty],hi[~empty],options)
    result[free]=sol;err=violation(result,lower,upper,G,glo,ghi)
    info=dict(info,original_variables=len(lower),reduced_free=int(free.sum()),reduced_fixed=int(fixed.sum()),
              original_rows=len(G),retained_rows=int((~empty).sum()),constraint_violation=err)
    info['success']=bool(info['success'] and err<=1e-7)
    return result,info

def highs_qp(center,gradient,proximal,lower,upper,G,glo,ghi,options):
    """Experimental SciPy-private HiGHS QP API, includes matrix setup time."""
    from scipy.optimize._highspy import _core as c
    from scipy.sparse import csc_matrix
    started=time.perf_counter();center=np.asarray(center,float);gradient=np.asarray(gradient,float)
    lower=np.asarray(lower,float);upper=np.asarray(upper,float);G=np.asarray(G,float);n=len(center)
    rho=float(proximal)
    if not np.isfinite(rho) or rho<=0:raise ValueError('Requires scalar positive proximal')
    model=c.HighsModel();lp=model.lp_;lp.num_col_=n;lp.num_row_=len(G)
    lp.col_cost_=gradient-rho*center;lp.col_lower_=lower;lp.col_upper_=upper
    lp.row_lower_=np.asarray(glo,float);lp.row_upper_=np.asarray(ghi,float)
    mat=csc_matrix(G);lp.a_matrix_.format_=c.MatrixFormat.kColwise
    lp.a_matrix_.num_col_=n;lp.a_matrix_.num_row_=len(G)
    lp.a_matrix_.start_=mat.indptr.astype(np.int32);lp.a_matrix_.index_=mat.indices.astype(np.int32);lp.a_matrix_.value_=mat.data
    h=model.hessian_;h.dim_=n;h.format_=c.HessianFormat.kTriangular
    h.start_=np.arange(n+1,dtype=np.int32);h.index_=np.arange(n,dtype=np.int32);h.value_=np.full(n,rho)
    # SciPy linprog can initialize HiGHS' process-global scheduler before this
    # call. Do not force a conflicting thread count or reset that scheduler.
    solver=c._Highs();solver.setOptionValue('output_flag',False)
    solver.setOptionValue('time_limit',3.)
    solver.setOptionValue('primal_feasibility_tolerance',1e-8);solver.setOptionValue('dual_feasibility_tolerance',1e-8)
    status=solver.passModel(model);setup=time.perf_counter()-started
    if status==c.HighsStatus.kError:raise RuntimeError('HiGHS passModel failed')
    # Same initial point as the original QP; HiGHS may treat this as a hint.
    warm=np.clip(center,lower,upper);solver.setSolution(n,np.arange(n,dtype=np.int32),warm)
    t=time.perf_counter();run_status=solver.run();solve=time.perf_counter()-t
    state=solver.getModelStatus();sol=solver.getSolution();x=np.asarray(sol.col_value,dtype=float)
    if x.shape!=(n,):x=warm
    err=violation(x,lower,upper,G,np.asarray(glo),np.asarray(ghi))
    ok=bool(run_status!=c.HighsStatus.kError and state==c.HighsModelStatus.kOptimal and err<=1e-7)
    return x,dict(success=ok,message=str(state),constraint_violation=err,iterations=int(solver.getInfo().qp_iteration_count),
                  solver='scipy_private_highs_qp',setup_seconds=setup,solve_seconds=solve,
                  objective=float(gradient@x+.5*rho*np.sum((x-center)**2)))
