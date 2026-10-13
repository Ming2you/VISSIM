"""Two diagnostic forecasts with measured future source admissions; never deploy."""
from pathlib import Path
import hashlib
import importlib.util
import json

from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.source_boundary318.conditional import substitute
from src.controllers import rollout_endpoint as endpoint

HERE=Path(__file__).resolve().parent
A=HERE.parent
OUT=Path('E:/VISSIM_analysis/20261010_source_boundary318/forecast2400')
spec=importlib.util.spec_from_file_location('source318_transport317_harness',A/'sc109_transport317/run.py')
prior=importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
module=prior.module
module.CASE=HERE
module.OUT=OUT


def main():
    audit=json.loads((HERE/'audit.json').read_bytes())
    for p,h in audit['source_pins'].items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    original=endpoint.evaluate_price_point
    receipts=[]

    def conditioned(state,action,forecast,*args,**kwargs):
        assert len(receipts)<2 and float(state.time_sec)==2400
        arm=('hold','city')[len(receipts)]
        counts={r:audit['comparison'][r][arm]['corrected_admissions_150s'] for r in ('FW_E','FW_W')}
        future=substitute(forecast,counts)
        receipts.append({'arm':arm,'start_sec':2400,'end_sec':2850,
                         'future_observation_inputs':True, 'admission_counts_150s':counts,
                         'original_vph':[d.freeway_mainline for d in forecast],
                         'conditioned_vph':[d.freeway_mainline for d in future]})
        return original(state,action,future,*args,**kwargs)

    OUT.parent.mkdir(parents=True,exist_ok=True)
    endpoint.evaluate_price_point=conditioned
    try:
        with prior.branch() as branch_receipt, prior.enabled() as transport_receipts:
            module.main()
    finally:
        endpoint.evaluate_price_point=original
    assert len(receipts)==2
    summary=json.loads((OUT/'summary.json').read_bytes())
    geometry=json.loads((OUT/'source_geometry.json').read_bytes())
    for p in (HERE/'audit.json',A/'sc109_transport317/run.py',A/'sc109_transport317/candidate.py',
              A/'sc107_shared316/candidate.py',A/'sc107_shared316/config.json',A/'sc107_shared316/run.py',
              A/'branch_service315/candidate.py',A/'branch_service315/config.json',Path(geometry['network_path']),Path(geometry['factor_path'])):
        summary['source_pins'][str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    summary.update(status='complete_conditional_future_source_diagnostic',
                   future_observation_inputs=True,autonomous_validation=False,
                   branch_service315=branch_receipt,source_transport317=True,
                   new_coefficient_fits=0,production_adopted=False,
                   inherited_311_service_fit_count=summary.pop('fits'),
                   candidate_scope='Oracle future source admissions only; no policy gain qualification')
    module.save('source_conditioning.json',receipts)
    module.save('transport_receipts.json',transport_receipts)
    module.save('summary.json',summary)
    print('SOURCE318_DONE conditional diagnosis, no autonomous gain claim',flush=True)


if __name__=='__main__':main()
