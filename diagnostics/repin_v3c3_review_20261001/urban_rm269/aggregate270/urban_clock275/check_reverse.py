"""Differentiate the actual batched finite receiving boundary in isolation."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]


def main():
    output=HERE/'reverse_boundary.json'
    assert not output.exists(),'Completed component result must not be repeated'
    from evaluation.controllers.sdmpc_tangent_runtime import install
    finder=install(ROOT,backend='reverse-v1')
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.canonical_harness import DelayedPort
    from evaluation.controllers.multirate_urban_boundary import release_delayed_interval
    rows=[]
    for case in ('finite_room','service','late_arrival'):
        trace=finder.ad.Trace([1.]);p=DelayedPort(30.,100.,36.,[],100.,interval_service=True)
        p.ready=20.;p.initial=20.
        service=3600.;room=30.
        if case=='finite_room':room=finder.ad.Dual(3.,{0:1.},trace);expected=[1.,-1.,-7./3600.]
        elif case=='service':service=finder.ad.Dual(1800.,{0:1.},trace);expected=[10./3600.,-10./3600.,-50./3600.**2]
        else:
            p.ready=0.;p.pending=[[109.,10.]];p.initial=10.
            service=finder.ad.Dual(3600.,{0:1.},trace);expected=[1./3600.,-1./3600.,-.5/3600.**2]
        departed=release_delayed_interval(p,100.,10,service,room)
        values=[departed,p.stock,p.residence_veh_h]
        jac=trace.jacobian(values,workers=1)[:,0].tolist()
        assert max(abs(a-b) for a,b in zip(jac,expected))<1e-10,(case,jac,expected)
        rows.append(dict(case=case,values=[finder.ad.primal(v) for v in values],jacobian=jac,
                         expected=expected,operations=trace.result()['operations']))
    assert any(p.endswith('multirate_urban_boundary.py') for p in finder.source_hashes)
    assert any(p.endswith('canonical_harness.py') for p in finder.source_hashes)
    result=dict(status='passed_three_transformed_boundary_cases',rows=rows,
        scope='One axis each: finite receiving room, outlet service, late-arrival service. Not full-plant AD or SDMPC.',
        transformed_sources=finder.source_hashes)
    output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='transformed_sources'},ensure_ascii=False))


if __name__=='__main__':main()
