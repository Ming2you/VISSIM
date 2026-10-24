"""Verify206 input timing, four logistic optima and output scores without refitting."""
import ast
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent;R=HERE.parent;ROOT=R.parents[1]
def read(p):
    b=p.read_bytes();return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    assert not (HERE/'verification.json').exists()
    protocol=read(HERE/'protocol.json');summary=read(HERE/'summary.json')
    rows=read(HERE/'rows.json.gz');models=read(HERE/'frozen_models.json')
    old=read(R/'state_information92/protocol.json')
    files={k:ROOT/v['path'] for k,v in old['inputs'].items() if not k.startswith('67')}
    files.update({f'67_{arm}':R/'blocking176'/f'{arm}_frames.json.gz'
                  for arm in ('hold','release','hold_vsl90','release_vsl90')})
    path=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/baseline_reproduction_20260929/cellwise_calibration/freeway_first/route_inventory/mapping31.json'
    length=np.diff(read(path)['freeway_model_links']['FW_E']['segment_bounds_m'])/1000
    max_feature_error=0.;feature_checks=0;by_group=defaultdict(list)
    for case,file in files.items():
        d=read(file);ix={key:j for j,key in enumerate(d['fields'])};rich='speed' in ix
        speed=ix['speed' if rich else 'speed_kmh'];position=ix['x' if rich else 'x_m']
        frames={round(float(t),6):f for t,f in d['frames'].items()}
        groups={}
        for t,fr in frames.items():
            temp=defaultdict(list)
            for z in fr.values():temp[int(z[ix['cell']]),int(z[ix['lane']])].append(z[speed])
            groups[t]={k:(len(v)/length[k[0]],sum(v)/len(v)) for k,v in temp.items()}
        selected=[z for z in rows if z['case']==case]
        for r in selected:
            fr=frames[r['t']];past=frames[round(r['t']-5,6)];future=frames[round(r['t']+5,6)]
            z=fr[r['id']];lead=fr[r['leader']];p=past[r['id']];lp=past[r['leader']]
            lane,cell=r['lane'],r['cell'];own=groups[r['t']][cell,lane];down=groups[r['t']][cell+1,lane]
            expected=[z[speed],own[0],own[1],down[0],down[1],lead[speed],
                      math.log1p(lead[position]-z[position]),z[speed]-p[speed],lead[speed]-lp[speed]]
            max_feature_error=max(max_feature_error,max(abs(a-b) for a,b in zip(expected,r['x'])))
            feature_checks+=len(expected)
            assert r['state']==('restart' if z[speed]<5 else 'stop')
            assert r['y']==int(future[r['id']][speed]>=5 if r['state']=='restart' else future[r['id']][speed]<5)
            by_group[case,r['state'],r['t'],cell,lane].append(r)
    assert max_feature_error<1e-10
    optimum=[];prediction_error=0.;score_error=0.
    for key,m in models.items():
        state,name=key.split('_');p=len(m['mean'])
        rr=[z for z in rows if z['case'].startswith('29') and z['state']==state]
        sizes=Counter((z['case'],z['t'],z['cell'],z['lane']) for z in rr)
        w=np.array([1/sizes[z['case'],z['t'],z['cell'],z['lane']] for z in rr]);y=np.array([z['y'] for z in rr])
        raw=np.array([z['x'][:p] for z in rr]);mu=np.average(raw,axis=0,weights=w)
        sd=np.maximum(1e-8,np.sqrt(np.average((raw-mu)**2,axis=0,weights=w)))
        assert max(abs(mu-m['mean']))<1e-10 and max(abs(sd-m['sd']))<1e-10
        x=np.c_[np.ones(len(rr)),(raw-mu)/sd];beta=np.array(m['beta']);reg=np.r_[0.,np.ones(p)]
        prob=1/(1+np.exp(-(x@beta)))
        gradient=x.T@(w*(prob-y))+reg*beta
        projected=beta-np.clip(beta-gradient,-10,10)
        assert max(abs(projected))<.002
        objective=lambda b:float(w@(np.logaddexp(0,x@b)-y*(x@b))+.5*np.sum(reg*b*b))
        assert abs(objective(beta)-m['loss'])<1e-7
        finite=[]
        for j in range(p+1):
            e=np.zeros(p+1);e[j]=1e-4
            finite.append((objective(beta+e)-objective(beta-e))/(2e-4))
        assert max(abs(np.array(finite)-gradient))<1e-4
        optimum.append(dict(key=key,rows=len(rr),projected_gradient=float(max(abs(projected))),
                            finite_gradient_error=float(max(abs(np.array(finite)-gradient)))))
    for r in rows:
        for name in ('current','memory'):
            m=models[r['state']+'_'+name];p=len(m['mean'])
            logit=m['beta'][0]+sum(b*(x-mu)/sd for b,x,mu,sd in zip(m['beta'][1:],r['x'][:p],m['mean'],m['sd']))
            expected=1/(1+math.exp(-logit))
            prediction_error=max(prediction_error,abs(expected-r[name]))
    for s in summary['scores']:
        groups=[g for key,g in by_group.items() if key[:2]==(s['case'],s['state'])]
        for name in ('current','memory'):
            brier=sum(sum((r[name]-r['y'])**2 for r in g)/len(g) for g in groups)/len(groups)
            score_error=max(score_error,abs(brier-s[name+'_brier']))
    assert prediction_error<1e-12 and score_error<1e-12
    source=R/'neighbor_information194/check.py'
    functions=lambda p:{n.name:ast.dump(n,include_attributes=False) for n in ast.parse(p.read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef)}
    before=functions(HERE/'check_before206.py.txt');after=functions(source)
    assert all(after[k]==v for k,v in before.items())
    for p,digest in protocol['input_sha256'].items():assert sha(Path(p))==digest
    for p,digest in protocol['source_sha256'].items():assert sha(ROOT/p)==digest
    stop=Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
    assert sha(stop)=='91b2163b02b01447242909dee8e7f773d18e76a6594bd9db8de64d2a48246fc3'
    assert sha(HERE/'frozen_models.json')==summary['frozen_sha256']
    result=dict(status='PASS',rows=len(rows),feature_checks=feature_checks,feature_error=max_feature_error,
        optimum=optimum,prediction_error=prediction_error,brier_error=score_error,
        prior_functions_AST_unchanged=True,input_pins=len(protocol['input_sha256']),core_files=len(protocol['source_sha256']),
        source_sha256={str(p):sha(p) for p in (Path(__file__),source)},goal='ACTIVE_NOT_QUALIFIED')
    (HERE/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('source_sha256','optimum')}))

if __name__=='__main__':main()
