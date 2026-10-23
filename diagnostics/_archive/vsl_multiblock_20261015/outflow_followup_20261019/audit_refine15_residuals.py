"""Localize saved trajectory errors and their already measured sensitivity.

No model rollout, parameter update or observed future boundary injection.
The unconstrained tangent projection is diagnostic, not an achievable fit.
"""
import os
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import hashlib, json, math, sys
from pathlib import Path
import numpy as np
A = Path(__file__).resolve().parent
O = A/'refine15_regime_fit_v3'
ROOT = Path('D:/VISSIM_packages/vsl_multizone355_20261015')
PINS = {}
CELLS = ['14', '15a', '15b', '15c', '16', '17', '18']
PARAMS = ['rho_crit', 'metanet_a_m', 'tau_sec', 'nu_ge', 'nu_lt']
def read(p):
    b = p.read_bytes(); PINS[str(p)] = hashlib.sha256(b).hexdigest()
    return json.loads(b)
def frame(p):
    r = p['refinement']
    return {'n':[p['n']['FW_E'][14],*[sum(x.values()) for x in r['routes']],*p['n']['FW_E'][16:19]],
            'speed':[p['speed']['FW_E'][14],*r['speed'],*p['speed']['FW_E'][16:19]]}
def stats(pred, obs):
    result=[]
    for j,c in enumerate(CELLS):
        row={'cell':c}
        for key in ('n','speed'):
            x=np.array([p[key][j]-q[key][j] for p,q in zip(pred,obs)])
            row[key+'_rmse']=float(np.sqrt(np.mean(x*x)))
            row[key+'_bias']=float(np.mean(x))
            row[key+'_sse']=float(x@x)
        row['normalized_sse']=row['n_sse']/100+row['speed_sse']/400
        result.append(row)
    total=sum(x['normalized_sse'] for x in result)
    for r in result:r['error_share']=r['normalized_sse']/total if total else 0.
    return result
def main():
    out=A/'refine15_residual_audit.json';assert not out.exists()
    decision=read(O/'decision.json')
    for p,h in decision['evidence'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    truth=read(O/'training_truth.json');training=[]
    def prediction(label,at):
        if label=='baseline' and at in (1650,2250):
            return read(A/'refine15_joint_fit'/('fitted_1650.json' if at==1650 else 'validation_hold.json'))
        return read(O/f'{label}_{at}.json')
    for label in ('baseline','fitted1','fitted2'):
        pred=[];obs=[]
        for at in (1650,2250,2850):
            p=prediction(label,at)['frames'];q=truth[str(at)]
            training.append(dict(label=label,start=at,cells=stats(p,q)))
            pred+=p;obs+=q
        training.append(dict(label=label,start='all',cells=stats(pred,obs)))
    evaluations=read(O/'training_evaluations.json');bylabel={x['label']:x for x in evaluations}
    def vector(label):
        error={k:[] for k in ('n','speed')}
        for at in (1650,2250,2850):
            for p,q in zip(prediction(label,at)['frames'],truth[str(at)]):
                for key in error:error[key].extend(x-y for x,y in zip(p[key],q[key]))
        return np.r_[np.array(error['n'])/10/math.sqrt(63),np.array(error['speed'])/20/math.sqrt(63)]
    tangent=[]
    for iteration,base in ((1,'baseline'),(2,'fitted1')):
        r=vector(base);z=np.array(bylabel[base]['relative']);columns=[]
        for j,param in enumerate(PARAMS):
            label=f'probe{iteration}_{param}';h=bylabel[label]['relative'][j]-z[j]
            assert abs(h)>.001
            columns.append((vector(label)-r)/h)
        J=np.column_stack(columns);u,s,vh=np.linalg.svd(J,full_matrices=False)
        assert np.allclose(s,read(O/'updates.json')[iteration-1]['data_jacobian_singular_values'],rtol=1e-8,atol=1e-10)
        projection=u@(u.T@r);residual=r-projection
        sensitivity=[]
        for j,cell in enumerate(CELLS):
            indices=[k*7+j for k in range(9)]+[63+k*7+j for k in range(9)]
            sensitivity.append(dict(cell=cell,residual_energy=float(r[indices]@r[indices]),
                tangent_residual_energy=float(residual[indices]@residual[indices]),
                column_norms={p:float(np.linalg.norm(J[indices,k])) for k,p in enumerate(PARAMS)}))
        tangent.append(dict(iteration=iteration,at=base,loss=float(r@r),
            unconstrained_tangent_removable_fraction=float(projection@projection/(r@r)),
            singular_values=s.tolist(),cells=sensitivity,
            feasible_or_nonlinear_achievability_claimed=False))
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    from evaluation.controllers import offramp_routing as route
    c=read(ROOT/'diagnostics/repin_v3c3_review_20261001/unrouted10646/route_contract.json')
    rt=route.compile_inventory(c,read(ROOT/c['mapping']['path']));bs=rt['bounds']['FW_E']
    def spatial(path):
        raw=read(path);assert raw['vehicle_records']['complete'];groups=[[] for _ in CELLS]
        for v in raw['vehicle_records']['records']:
            if str(v['link_no']) not in rt['physical']:continue
            road,pos,i=route._position(rt,v['link_no'],v['position_m'])
            if road!='FW_E' or not 14<=i<=18:continue
            j=0 if i==14 else 1+min(2,int(3*(pos-bs[15])/(bs[16]-bs[15]))) if i==15 else i-12
            groups[j].append(v['speed_kph'])
        assert all(groups)
        return dict(n=[len(g) for g in groups],speed=[sum(g)/len(g) for g in groups])
    independent=[];contrast=[]
    for seed,arms in ((67,('release','release_vsl90')),(71,('rm','both'))):
        folder=A/f'refine15_independent_s{seed}';summary=read(folder/'summary.json');receipt=read(folder/'fixed_replay_receipt.json')
        observed={}
        for arm in arms:
            nativefolder=Path(receipt['candidate_actions'][arm][0]).parent
            observed[arm]=[spatial(nativefolder/f"state_{summary['start']+t:06d}.json") for t in (150,300,450)]
        for variant in ('original','fitted'):
            predicted={}
            for arm in arms:
                predicted[arm]=[frame(x) for x in read(folder/f'{variant}_{arm}_snapshots.json')[1:]]
                independent.append(dict(seed=seed,variant=variant,arm=arm,cells=stats(predicted[arm],observed[arm])))
            def delta(d):
                return [{k:[b-a for a,b in zip(left[k],right[k])] for k in ('n','speed')}
                        for left,right in zip(d[arms[0]],d[arms[1]])]
            pd,qd=delta(predicted),delta(observed)
            contrast.append(dict(seed=seed,variant=variant,cells=stats(pd,qd),predicted_delta=pd,observed_delta=qd))
    result=dict(status='completed_saved_residual_localization',training=training,tangent=tangent,
                independent=independent,contrast=contrast,source_pins=PINS,new_forecasts=0,new_fits=0,new_native=0,
                candidate_adopted=False,goal_complete=False,
                limitations=['Tangent projection is local and ignores physical parameter bounds; not evidence of attainable improvement.',
                             'Seed67/71 were not used in this fit but their results have been seen during development.',
                             'State residuals locate disagreement; they do not by themselves prove which physical term is wrong.'])
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps(dict(tangent=[{k:r[k] for k in ('iteration','unconstrained_tangent_removable_fraction')} for r in tangent],
                         training_fitted=[x for x in training if x['label']=='fitted2' and x['start']=='all'],
                         contrast=contrast),indent=2))
if __name__=='__main__':main()
