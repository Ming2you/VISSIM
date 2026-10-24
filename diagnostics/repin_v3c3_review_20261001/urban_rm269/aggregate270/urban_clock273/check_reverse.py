"""Fresh-process check of the actual transformed coarse boundary module."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[k]='1'
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]


def main():
    from evaluation.controllers.sdmpc_tangent_runtime import install
    finder=install(ROOT,backend='reverse-v1')
    from evaluation.controllers.lane_offramp_runtime import SharedSignalApproach
    from evaluation.controllers.multirate_urban_boundary import advance_shared_interval
    lanes={'1':dict(capacity_veh=30.,service_veh_h=3600.,movements=['straight'])}
    entries={'city':[dict(lane='1',movement='straight',share=1.,delay_sec=5)]}
    initial=[dict(lane='1',source='city',movement='straight',vehicles=20.,ready_sec=100)]
    approach=SharedSignalApproach(lanes,entries,initial,100)
    trace=finder.ad.Trace([1.]);green=finder.ad.Dual(.4,{0:1.},trace)
    rows=advance_shared_interval(approach,100,10,lambda start,duration:{'1':green},{'straight':30.})
    values=[sum(r['vehicles'] for r in rows),approach.stock(),approach.residence_veh_h]
    jac=trace.jacobian(values,workers=1)[:,0].tolist()
    expected=[10.,-10.,-50./3600.]
    assert max(abs(a-b) for a,b in zip(jac,expected))<1e-10
    assert any(p.endswith('multirate_urban_boundary.py') for p in finder.source_hashes)
    result=dict(status='passed_transformed_component_reverse',outputs=['departed_veh','end_stock_veh','residence_veh_h'],
        values=[finder.ad.primal(v) for v in values],derivative_per_green_fraction=jac,expected=expected,
        operations=trace.result()['operations'],transformed_sources=finder.source_hashes,
        scope='One unconstrained ten-second boundary service,not whole-plant or all-axis validation')
    (HERE/'reverse_component.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='transformed_sources'},ensure_ascii=False))


if __name__=='__main__':main()
