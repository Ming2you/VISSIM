"""Independent source, physical-feature and ridge-fit checks for213."""
import ast
from collections import Counter, defaultdict
import math
from pathlib import Path
import numpy as np
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    protocol=h.read(HERE/'protocol.json');rows=h.read(HERE/'rows.json.gz')
    model=h.read(HERE/'frozen_model.json');summary=h.read(HERE/'summary.json')
    before=(HERE/'check.py.before.txt').read_text(encoding='utf8')
    now=(h.R/'neighbor_information194/check.py').read_text(encoding='utf8')
    def functions(s):
        return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)}
    aa,bb=functions(before),functions(now)
    assert all(bb[k]==v for k,v in aa.items()) and set(bb)-set(aa)=={'variance213'}
    original=h.read(h.R/'neighbor_information194/rows.json.gz')
    assert len(rows)==len(original)==79188
    for new,old in zip(sorted(rows,key=lambda r:(r['case'],r['t'],r['id'])),sorted(original,key=lambda r:(r['case'],r['t'],r['id']))):
        assert new['x'][:-1]==old['x']
        assert all(new[k]==v for k,v in old.items() if k!='x')
    mapping=h.F/'route_inventory/mapping31.json'
    bounds=h.read(mapping)['freeway_model_links']['FW_E']['segment_bounds_m']
    lengths=np.diff(bounds)/1000
    paths=[Path(p) for p in protocol['input_sha256'] if p.endswith('_frames.json.gz')]
    observed=h.read(HERE/'moments.json.gz');max_error=0.
    for case in sorted({r['case'] for r in observed}):
        seed,arm=case.split('_',1)
        file=next(p for p in paths if (p.name==f's{seed}_{arm}_frames.json.gz' if seed!='67' else p.name==f'{arm}_frames.json.gz'))
        data=h.read(file);ix={s:i for i,s in enumerate(data['fields'])}
        vi=ix.get('speed',ix.get('speed_kmh'));ci=ix['cell'];li=ix['lane']
        frames={round(float(t),6):list(fr.values()) for t,fr in data['frames'].items()}
        for r in observed:
            if r['case']!=case:continue
            fr=frames[r['t']];c=r['cell'];lane=r['lane']
            vectors=[[z[vi] for z in fr if z[ci]==cell and z[li]==lane] for cell in (c,c+1)]
            own,down=vectors
            # Sum-of-squares identity, distinct from np.var in the extractor.
            v0=sum(own)/len(own);v1=sum(down)/len(down)
            var0=sum(v*v for v in own)/len(own)-v0*v0
            var1=sum(v*v for v in down)/len(down)-v1*v1
            rho0=len(own)/lengths[c];rho1=len(down)/lengths[c+1]
            # SI computation and conversion back to km/h over5s.
            p0=(rho0/1000)*(var0/3.6**2);p1=(rho1/1000)*(var1/3.6**2)
            prediction=-5*(p1-p0)/((rho0/1000)*500*(lengths[c]+lengths[c+1]))*3.6
            max_error=max(max_error,abs(prediction-r['pressure5']))
            assert abs(prediction-r['pressure5'])<1e-9
    train=[r for r in rows if r['case'].startswith('29')]
    x=np.array([r['x'] for r in train]);y=np.array([r['y'] for r in train])
    sizes=Counter((r['case'],r['t'],r['cell'],r['lane']) for r in train)
    w=np.array([1/sizes[r['case'],r['t'],r['cell'],r['lane']] for r in train])
    means=np.average(x,axis=0,weights=w)
    sd=np.maximum(1e-8,np.sqrt(np.average((x-means)**2,axis=0,weights=w)))
    assert np.allclose(means,model['mean'],rtol=0,atol=1e-11)
    assert np.allclose(sd,model['sd'],rtol=0,atol=1e-11)
    a=np.column_stack([np.ones(len(x)),(x-means)/sd])
    penalty=np.eye(18)[1:]
    aa=np.vstack([a*np.sqrt(w[:,None]),penalty]);yy=np.r_[y*np.sqrt(w),np.zeros(17)]
    beta=np.linalg.lstsq(aa,yy,rcond=None)[0]
    if beta[-1]<0:
        beta=np.r_[np.linalg.lstsq(aa[:,:-1],yy,rcond=None)[0],0.]
    error=float(max(abs(beta-np.array(model['beta']))));assert error<1e-8
    assert h.sha(HERE/'frozen_model.json')==summary['frozen_sha256']
    assert all(h.sha(Path(p))==sha for p,sha in protocol['input_sha256'].items())
    assert all(h.sha(h.ROOT/p)==sha for p,sha in protocol['source_sha256'].items())
    assert h.sha(protocol['STOP']['path'])==protocol['STOP']['sha256']
    result=dict(status='PASS',unchanged_helper_functions=len(functions(before)),original_rows_exact=len(rows),
        independently_checked_moments=len(observed),max_SI_feature_error=max_error,independent_QR_beta_error=error,
        production_files_preserved=len(protocol['source_sha256']),input_sha_preserved=True,STOP_preserved=True)
    h.save(HERE/'verification.json',result)
    print(result)


if __name__=='__main__':main()
