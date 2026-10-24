"""Two fixed-command450s comparisons against315, no new native or fit."""
from pathlib import Path
import hashlib,importlib.util,json,sys
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.branch_service315.candidate import enabled
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc107_shared316.candidate import install,refresh_local

HERE=Path(__file__).resolve().parent;A=HERE.parent
OUT=Path('E:/VISSIM_analysis/20261010_sc107_shared316/forecast2400')
PREV=A/'sc108_geometry311'
sys.path.insert(0,str(PREV))
spec=importlib.util.spec_from_file_location('shared316_original_harness',PREV/'run.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.CASE=HERE;module.OUT=OUT
original=module.install_geometry


def apply(cfg,state):
    geometry=original(cfg,state)
    import pickle
    before=pickle.dumps(state,protocol=5)
    receipt=install(cfg)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    receipt['owner_binding']=refresh_local(adapter._PHASE_VECTOR_FOLLOWER['ref'],cfg)
    assert pickle.dumps(state,protocol=5)==before
    module.save('shared_head_application.json',receipt)
    return dict(geometry,sc107_shared_head=receipt)


module.install_geometry=apply
if __name__=='__main__':
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with enabled() as branch_receipt:module.main()
    summary=json.loads((OUT/'summary.json').read_bytes())
    for p in (HERE/'candidate.py',HERE/'config.json',A/'branch_service315/candidate.py',A/'branch_service315/config.json',Path(branch_receipt['evidence']),PREV/'run.py'):
        summary['source_pins'][str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    summary.update(branch_service315=branch_receipt,new_coefficient_fits=0,production_adopted=False,
        inherited_311_service_fit_count=summary.pop('fits'),candidate_scope='Share existingSC107_p3 envelope; all source tags and other conditions unchanged')
    module.save('summary.json',summary)
