"""Reuse311 fixed-command harness; insert only current SC107 head partition."""
import hashlib,importlib.util,json,sys
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc107_head313.candidate import install,register_owner

HERE=Path(__file__).resolve().parent;A=HERE.parent
OUT=Path('E:/VISSIM_analysis/20261010_sc107_head313/forecast2400_v3')
PREV=A/'sc108_geometry311'
sys.path.insert(0,str(PREV))
spec=importlib.util.spec_from_file_location('sc108_geometry311_harness',PREV/'run.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.CASE=HERE;module.OUT=OUT
original=module.install_geometry


def apply(cfg,state):
    geometry=original(cfg,state)
    old=json.loads((A/'sc107_composition312/assessment.json').read_bytes())
    paths=old['source_pins']
    state_path=next(p for p in paths if p.endswith('state_002400.json'))
    raw=json.loads(Path(state_path).read_bytes())
    frame_path=Path(state_path).parent/raw['obs150']['frames']['current']['path']
    frame=json.loads(frame_path.read_bytes())
    network=next(p for p in paths if p.endswith('.inpx'))
    for path in (state_path,network):assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==paths[path]
    receipt=install(cfg,state,raw,frame,Path(network).read_bytes())
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    receipt['owner_binding']=register_owner(adapter._PHASE_VECTOR_FOLLOWER['ref'],cfg)
    receipt['source_pins']={str(p):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in (state_path,frame_path,network,HERE/'candidate.py',PREV/'run.py')}
    module.save('sc107_initial_application.json',receipt)
    return dict(geometry,sc107_current_head_partition=receipt)


module.install_geometry=apply
if __name__=='__main__':
    OUT.parent.mkdir(parents=True,exist_ok=True)
    module.main()
    receipt=json.loads((OUT/'sc107_initial_application.json').read_bytes())
    summary=json.loads((OUT/'summary.json').read_bytes())
    for p,h in receipt['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
    summary['source_pins'].update(receipt['source_pins'])
    summary.update(sc107_current_cohort=receipt,new_coefficient_fits=0,production_adopted=False,
        inherited_311_service_fit_count=summary.pop('fits'),candidate_scope='Known current post-diverge head cohort only; future approach beta/head assignment unchanged; unresolved current stock retained')
    module.save('summary.json',summary)
