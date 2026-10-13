"""Two fixed450s forecasts; inherit316 and change new transport alone."""
from pathlib import Path
import hashlib,importlib.util,json,pickle
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.branch_service315.candidate import enabled as branch
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_transport317.candidate import install,enabled

HERE=Path(__file__).resolve().parent;A=HERE.parent
OUT=Path('E:/VISSIM_analysis/20261010_sc109_transport317/forecast2400')
spec=importlib.util.spec_from_file_location('shared316_harness',A/'sc107_shared316/run.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
module=prior.module;module.CASE=HERE;module.OUT=OUT
old=module.install_geometry

def apply(cfg,state):
    base=old(cfg,state);before=pickle.dumps(state,protocol=5);receipt=install(cfg,state)
    assert pickle.dumps(state,protocol=5)==before
    module.save('source_geometry.json',receipt)
    return dict(base,source_transport317=receipt)

module.install_geometry=apply

if __name__=='__main__':
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with branch() as br,enabled() as receipts:module.main()
    summary=json.loads((OUT/'summary.json').read_bytes());geom=json.loads((OUT/'source_geometry.json').read_bytes())
    for p in (A/'sc107_shared316/candidate.py',A/'sc107_shared316/config.json',A/'sc107_shared316/run.py',A/'branch_service315/candidate.py',A/'branch_service315/config.json',Path(geom['network_path']),Path(geom['factor_path'])):
        summary['source_pins'][str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    assert receipts and len({x['source'] for x in receipts})==4
    module.save('transport_receipts.json',receipts)
    summary.update(branch_service315=br,source_transport317=True,new_coefficient_fits=0,production_adopted=False,
        inherited_311_service_fit_count=summary.pop('fits'),candidate_scope='Physical path transport for new accepted receipts only')
    module.save('summary.json',summary)
