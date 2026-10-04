"""Localize169 macro-response errors using the same30s inventory quadrature."""
import csv
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent
PAIRS=(('hold','release'),('release','release_vsl90'))

def integrate(a,b):
    out=[]
    for i in range(31):
        old=0.;total=0.;before=2670.1
        for t in (round(2700.1+30*k,1) for k in range(15)):
            d=b[t,i]-a[t,i]
            total+=(old+d)/2*(t-before)/3600
            old=d;before=t
        out.append(total)
    return out

def main():
    assert not (HERE/'response_location.json').exists()
    pins={str(Path(__file__)):h.sha(__file__)}
    def read(p):pins[str(p)]=h.sha(p);return h.read(p)
    native={}
    for arm in ('hold','release','release_vsl90'):
        p=h.I/'heldout67_freeway_20260930/observations'/arm/'cells_30s.csv'
        pins[str(p)]=h.sha(p)
        with p.open(encoding='utf-8-sig') as f:
            native[arm]={(round(float(r['time_s']),1),int(r['cell'])):float(r['n_veh']) for r in csv.DictReader(f) if r['road']=='FW_E'}
        assert all(native[arm][2670.1,i]==native['hold'][2670.1,i] for i in range(31))
    results=[]
    for label,folder,sub in [('148','spatial_context148','training'),('158','coupled_recovery158','training'),
                             ('168','state_lateral168','state'),('169','recovery_lateral169','state')]:
        root=h.R/folder/'forecast'/sub
        rows={r['arm']:r for r in read(root/'rows.json') if r['case']=='s67_late'}
        states={}
        for arm in ('hold','release','release_vsl90'):
            pred=read(root/f's67_late_{arm}.json.gz')
            states[arm]={(round(r['time_s'],1),r['cell']):r['n_veh'] for r in pred['cells']}
        for left,right in PAIRS:
            actual=integrate(native[left],native[right]);modeled=integrate(states[left],states[right])
            components={kind:{k:rows[right][kind][k]-rows[left][kind][k] for k in ('ttt','mainline_ttt','ramp_ttt','off_ttt')} for kind in ('actual','predicted')}
            assert abs(sum(actual)-components['actual']['mainline_ttt'])<1e-8
            assert abs(sum(modeled)-components['predicted']['mainline_ttt'])<1e-8
            for kind in components:
                c=components[kind]
                assert abs(c['ttt']-c['mainline_ttt']-c['ramp_ttt']-c['off_ttt'])<1e-8
            cells=[dict(cell=i,actual=actual[i],predicted=modeled[i],error=modeled[i]-actual[i]) for i in range(31)]
            groups=[dict(cells=list(ii),actual=sum(actual[i] for i in ii),predicted=sum(modeled[i] for i in ii)) for ii in (range(19),[19],range(20,26),range(26,31))]
            results.append(dict(model=label,left=left,right=right,cells=cells,groups=groups,components=components))
    for p,d in pins.items():assert h.sha(p)==d,p
    h.save(HERE/'response_location.json',dict(results=results,input_sha256=pins,
        definition='Matched common initial state2670.1..3120.1,30s trapezoid used by the original component evaluator. In-region cost only, not Omega or external waiting. Per-cell error attribution is inventory accounting, not causal contribution.',
        new_forecasts=0,new_fits=0))
    for r in results:
        if r['model']=='169':
            print(r['left'],r['right'],r['components'],r['groups'])
            print('largest errors',sorted(r['cells'],key=lambda z:abs(z['error']),reverse=True)[:8])

if __name__=='__main__':main()
