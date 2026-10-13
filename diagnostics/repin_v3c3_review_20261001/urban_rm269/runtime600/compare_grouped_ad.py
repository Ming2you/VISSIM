"""Read one completed AD and retained scalar/AD responses; no new predictions."""
import hashlib
import json
from pathlib import Path
import pickle
import sys
import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from compare_physical_summary import compare


def main():
    out=HERE/'whole_transfer/ad_grouped_v2'
    assert not (out/'comparison.json').exists(),'Preserve completed comparison'
    receipt=json.loads((out/'execution.json').read_bytes())
    assert receipt['status']=='complete_pending_comparison' and receipt['exit_code']==0
    for name,expected in receipt['source_pins'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==expected,name
    scalar=pickle.loads((HERE/'whole_transfer/scalar_grouped/result.pickle').read_bytes())
    current=pickle.loads((out/'result.pickle').read_bytes())
    previous=pickle.loads((HERE/'hot_validation/ad.result.pickle').read_bytes())
    assert 'error' not in current and current['ad_axes']==list(range(213)) and not current['fallback_reasons']
    physical=compare(scalar['surrogate_prediction'],current['surrogate_prediction'])
    matrices={}
    for name,x,y in [('owner_costs',previous['cost_jacobian'],current['cost_jacobian']),
                     ('np_nuf',previous['resource_jacobian'],current['resource_jacobian']),
                     ('physical_states',previous['central_physical']['jacobian'],current['central_physical']['jacobian'])]:
        x,y=np.asarray(x),np.asarray(y)
        assert x.shape==y.shape and np.isfinite(x).all() and np.isfinite(y).all(),name
        differences=np.abs(x-y)
        close=np.isclose(x,y,atol=1e-7,rtol=1e-8)
        indices=np.dstack(np.unravel_index(np.argsort(differences.ravel())[-5:][::-1],x.shape))[0]
        matrices[name]=dict(shape=list(x.shape),close=bool(close.all()),different_entries=int((~close).sum()),
            max_absolute_error=float(differences.max(initial=0.)),
            largest=[dict(index=[int(i),int(j)],before=float(x[i,j]),after=float(y[i,j])) for i,j in indices])
    assert previous['central_physical']['names']==current['central_physical']['names']
    result=dict(status='complete_physical_scalar_ad_validation',physical_comparison=physical,
        matrices=matrices,all_jacobians_close=all(m['close'] for m in matrices.values()),
        external_process_wall_sec=receipt['wall_sec'],
        tangent_sec=current.get('tangent_sec'),reverse_sec=current.get('reverse_sec'),
        ad_axes=213,fallback_axes=0,new_predictions=0,full_selections=0,native_runs=0,
        limitations=['One saved2400s state and command; complete600s decision target is still unverified.',
                     'Different source bookkeeping counts are recorded separately from all physical values.',
                     'A changed active-branch Jacobian requires review; no optimizer convergence is claimed.'])
    (out/'comparison.json').write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('status','external_process_wall_sec','tangent_sec','reverse_sec','all_jacobians_close')}))
    print(json.dumps(matrices))

if __name__=='__main__':main()
