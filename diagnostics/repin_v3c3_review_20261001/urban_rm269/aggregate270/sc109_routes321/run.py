"""Two autonomous fixed-command responses with current initial route tags."""
from pathlib import Path
import hashlib,importlib.util,json
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_routes321.candidate import install,TARGET
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal

HERE=Path(__file__).resolve().parent;A=HERE.parent
OUT=Path('E:/VISSIM_analysis/20261010_sc109_routes321/forecast2400')
spec=importlib.util.spec_from_file_location('initial320_base',A/'sc109_initial320/run.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
module=base.module;module.CASE=HERE;module.OUT=OUT
old=module.install_geometry

def apply(cfg,state):
    geom=old(cfg,state)
    _,_,raw,frame,network,inside,lanes=module.inputs()
    result,receipt=install(cfg,state,raw,frame,network,geom['initial_calendar320'])
    changed={k for k,v in vars(result).items() if not equal(v,vars(state)[k])}
    assert changed=={'urban_movement_queue','local_observation_summary','gate_initial_route_tags','_control_area_ledger'},changed
    for key in changed:setattr(state,key,getattr(result,key))
    module.save('current_routes.json',receipt)
    return dict(geom,initial_routes321=receipt)

module.install_geometry=apply
if __name__=='__main__':
    OUT.parent.mkdir(parents=True,exist_ok=True)
    from src.controllers import rollout_endpoint as endpoint
    original_evaluate=endpoint.evaluate_price_point
    tag_checks=[]
    def evaluate(*args,**kwargs):
        point=original_evaluate(*args,**kwargs)
        assert len(point.states)==3
        checks=[dict(time_sec=s.time_sec,remaining=s.gate_initial_route_tags.get(TARGET,{})) for s in point.states]
        assert all(x['remaining']=={} for x in checks),'Known initial tags were not consumed exactly once'
        tag_checks.append(checks)
        return point
    endpoint.evaluate_price_point=evaluate
    try:
        with base.prior.branch() as br,base.prior.enabled() as receipts:module.main()
    finally:endpoint.evaluate_price_point=original_evaluate
    summary=json.loads((OUT/'summary.json').read_bytes())
    geom=json.loads((OUT/'source_geometry.json').read_bytes())
    route=json.loads((OUT/'current_routes.json').read_bytes())
    for stage,names in {'sc109_initial320':['run.py','candidate.py'],'sc109_transport317':['run.py','candidate.py','config.json'],
                        'sc107_shared316':['run.py','candidate.py','config.json'],'branch_service315':['candidate.py','config.json']}.items():
        for name in names:
            p=A/stage/name;summary['source_pins'][str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    for key in ('network_path','factor_path'):
        p=Path(geom[key]);summary['source_pins'][str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    summary['source_pins'].update(route['source_pins'])
    assert receipts and len({x['source'] for x in receipts})==4
    assert len(tag_checks)==2
    module.save('transport_receipts.json',receipts)
    module.save('route_tag_consumption.json',tag_checks)
    summary.update(branch_service315=br,source_transport317=True,initial_calendar320=True,initial_routes321=True,
                   new_coefficient_fits=0,production_adopted=False,inherited_311_service_fit_count=summary.pop('fits'),
                   candidate_scope='Known current initial turns; unchanged320 ETA and source forecast')
    module.save('summary.json',summary)
