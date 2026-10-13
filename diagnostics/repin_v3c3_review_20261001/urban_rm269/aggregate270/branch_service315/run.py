"""Two original311 fixed-command forecasts with one scoped branch rate."""
from pathlib import Path
import hashlib,importlib.util,json,sys
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.branch_service315.candidate import enabled

HERE=Path(__file__).resolve().parent;A=HERE.parent
OUT=Path('E:/VISSIM_analysis/20261010_branch_service315/forecast2400')
PREV=A/'sc108_geometry311'
sys.path.insert(0,str(PREV))
spec=importlib.util.spec_from_file_location('branch315_existing_harness',PREV/'run.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.CASE=HERE;module.OUT=OUT

if __name__=='__main__':
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with enabled() as receipt:module.main()
    summary=json.loads((OUT/'summary.json').read_bytes())
    for p in (HERE/'candidate.py',HERE/'config.json',Path(receipt['evidence']),PREV/'run.py'):
        summary['source_pins'][str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    summary.update(branch_service315=receipt,new_coefficient_fits=0,production_adopted=False,
        inherited_311_service_fit_count=summary.pop('fits'),candidate_scope='Only1129 bypass service; same other flow, routes, stock, clocks and receiving')
    module.save('summary.json',summary)
