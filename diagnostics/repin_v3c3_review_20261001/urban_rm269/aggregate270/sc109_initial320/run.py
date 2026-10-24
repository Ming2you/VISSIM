"""Two autonomous fixed450s responses; inherit317 and retime current arrivals."""
from pathlib import Path
import hashlib
import importlib.util
import json
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_initial320.candidate import install

HERE=Path(__file__).resolve().parent;A=HERE.parent
OUT=Path('E:/VISSIM_analysis/20261010_sc109_initial320/forecast2400')
spec=importlib.util.spec_from_file_location('transport317_base',A/'sc109_transport317/run.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
module=prior.module;module.CASE=HERE;module.OUT=OUT
old=module.install_geometry


def apply(cfg,state):
    base=old(cfg,state)
    _,_,raw,frame,network,inside,lanes=module.inputs()
    receipt=install(cfg,state,raw,frame,network,lanes)
    module.save('initial_calendar.json',receipt)
    return dict(base,initial_calendar320=receipt)


module.install_geometry=apply
if __name__=='__main__':
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with prior.branch() as br,prior.enabled() as receipts:module.main()
    summary=json.loads((OUT/'summary.json').read_bytes())
    geom=json.loads((OUT/'source_geometry.json').read_bytes())
    for p in (A/'sc109_transport317/run.py',A/'sc109_transport317/candidate.py',A/'sc109_transport317/config.json',
              A/'sc107_shared316/candidate.py',A/'sc107_shared316/config.json',A/'sc107_shared316/run.py',
              A/'branch_service315/candidate.py',A/'branch_service315/config.json',Path(geom['network_path']),Path(geom['factor_path'])):
        summary['source_pins'][str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    assert receipts and len({x['source'] for x in receipts})==4
    module.save('transport_receipts.json',receipts)
    summary.update(branch_service315=br,source_transport317=True,initial_calendar320=True,new_coefficient_fits=0,
                   production_adopted=False,inherited_311_service_fit_count=summary.pop('fits'),
                   candidate_scope='Current SC109 residual arrival timestamps only; no future traffic input')
    module.save('summary.json',summary)
