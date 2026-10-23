"""Two preregistered three-coefficient fits; no VSL data, grid, or rollout."""
import hashlib,json,math
from pathlib import Path
import numpy as np
from scipy.optimize import nnls

A=Path(__file__).resolve().parent;O=A/'refine15_calibration';PINS={}
def read(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return json.loads(b)
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')

def main():
    assert not (O/'fit.json').exists(),'Reuse fitted parameters'
    protocol=read(O/'protocol.json');assert protocol['budgets']['fits']==2
    data=read(O/'native_hold_cells.json');audit=read(A/'refine15_update_audit.json')
    params=audit['parent_parameters'];old=audit['state_response']
    tau=old['relaxation']['acceleration_sec'];assert tau==old['relaxation']['deceleration_sec']
    beta0=np.array([1/tau,old['anticipation']['downstream_ge_local']/tau,old['anticipation']['downstream_lt_local']/tau])
    def desired(rho):return params['v_free']*math.exp(-(max(0.,rho)/params['rho_crit'])**params['metanet_a_m']/params['metanet_a_m'])
    assert abs(desired(audit['rows'][0]['rho'])-audit['rows'][0]['desired_kmh'])<1e-10
    output={};predictors={}
    for resolution in ('parent','refined'):
        rows=[]
        for first,second in zip(data['rows'],data['rows'][1:]):
            dt=second['time']-first['time'];assert abs(dt-5)<1e-7
            if resolution=='refined':
                ns,vs=first['n'],first['speed'];nextn,nextv=second['n'],second['speed'];lengths=np.array(data['length_m'])/1000
            else:
                def aggregate(r):return [r['n'][0],sum(r['n'][1:4]),r['n'][4]],[r['speed'][0],sum(n*v for n,v in zip(r['n'][1:4],r['speed'][1:4]))/sum(r['n'][1:4]),r['speed'][4]]
                ns,vs=aggregate(first);nextn,nextv=aggregate(second);lengths=np.array([data['length_m'][0],sum(data['length_m'][1:4]),data['length_m'][4]])/1000
            for i in range(1,len(ns)-1):
                length=lengths[i];rho=ns[i]/(4*length);down=ns[i+1]/(4*lengths[i+1]);v=vs[i]
                conv=v*(vs[i-1]-v)/(3600*length)
                pressure=-(down-rho)/(length*(rho+params['metanet_kappa_veh_km_lane']))
                x=[desired(rho)-v,pressure if down>=rho else 0.,pressure if down<rho else 0.]
                rows.append(dict(start=first['time'],end=second['time'],part=i,initial_v=v,next_v=nextv[i],conv=conv,x=x,y=(nextv[i]-v)/dt-conv,weight=min(ns[i],nextn[i]),dt=dt))
        train=[r for r in rows if r['start']>=protocol['training']['start_sec']-1e-7 and r['end']<=protocol['training']['end_sec']+1e-7]
        valid=[r for r in rows if r['start']>=protocol['validation']['start_sec']-1e-7 and r['end']<=protocol['validation']['end_sec']+1e-7]
        assert len(train)==(720 if resolution=='refined' else 240) and len(valid)==(267 if resolution=='refined' else 89)
        X=np.array([r['x'] for r in train]);y=np.array([r['y'] for r in train]);w=np.array([r['weight'] for r in train],float)
        scale=np.sqrt(np.average(X*X,axis=0,weights=w));assert min(scale)>0
        design=X/scale*np.sqrt(w[:,None]);target=y*np.sqrt(w)
        rank=int(np.linalg.matrix_rank(design));assert rank==3
        scaled,residual=nnls(design,target);beta=scaled/scale
        gradient=design.T@(design@scaled-target)
        tolerance=1e-7*max(1.,float(np.linalg.norm(design))*float(np.linalg.norm(target)))
        assert min(gradient)>=-tolerance and max(abs(scaled*gradient))<=tolerance
        identifiable=bool(beta[0]>1e-10 and np.isfinite(beta).all())
        fitted=dict(tau_sec=float(1/beta[0]),nu_downstream_ge=float(beta[1]/beta[0]),nu_downstream_lt=float(beta[2]/beta[0])) if identifiable else None
        def metrics(samples,b):
            ww=np.array([r['weight'] for r in samples],float)
            pred=np.array([max(5.,r['initial_v']+r['dt']*(r['conv']+float(np.dot(r['x'],b)))) for r in samples])
            truth=np.array([r['next_v'] for r in samples]);error=pred-truth
            return dict(weighted_speed_rmse_kmh=float(np.sqrt(np.average(error**2,weights=ww))),weighted_bias_kmh=float(np.average(error,weights=ww)),speed_floor_predictions=int(sum(pred<=5+1e-8)),rows=len(samples))
        scored={part:dict(transferred_parent=metrics(samples,beta0),fitted=metrics(samples,beta)) for part,samples in [('training',train),('validation',valid)]}
        qualifies=bool(identifiable and scored['validation']['fitted']['weighted_speed_rmse_kmh']<=.9*scored['validation']['transferred_parent']['weighted_speed_rmse_kmh'])
        output[resolution]=dict(coefficients=fitted,linear_parameters=beta.tolist(),normalized_design_condition=float(np.linalg.cond(design)),rank=rank,nnls_residual=float(residual),kkt_gradient=gradient.tolist(),scores=scored,qualifies_for_autonomous_forecast=qualifies)
        predictors[resolution]=rows
    PINS[str(Path(__file__))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report=dict(status='completed_two_baseline_resolution_fits',fits=2,new_forecasts=0,new_native=0,new_optimizer_runs=0,coefficient_grid=0,
        results=output,source_pins=PINS,production_changed=False,candidate_adopted=False,goal_complete=False,
        next='If refined qualifies, evaluate one autonomous hold110/twozone90 pair at fixed0.625s internal cap,450s horizon,macroFW5/U10; compare to the completed same-grid transferred-parameter pair. No further fit on validation or VSL outcomes.',
        limitations=['One-step observed-state regression is not an autonomous predictive trajectory.',
            'Refined fit shares three dynamic coefficients across three compartments; equilibrium FD unchanged.',
            'Parameter identifiability and holdout improvement do not prove cross-seed or VSL response validity.'])
    for p,h in PINS.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
    save(O/'fit.json',report)
    print(json.dumps(output,indent=2))
if __name__=='__main__':main()
