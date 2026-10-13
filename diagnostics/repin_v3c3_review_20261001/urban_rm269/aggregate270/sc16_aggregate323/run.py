"""One hold/city pair with the frozen323 past-supported aggregate candidate."""
from pathlib import Path
import hashlib,importlib.util,json
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc16_aggregate323.candidate import install,SOURCE
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal

HERE=Path(__file__).resolve().parent;A=HERE.parent
OUT=Path('E:/VISSIM_analysis/20261010_sc16_aggregate323/forecast2400')
spec=importlib.util.spec_from_file_location('routes321_base',A/'sc109_routes321/run.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
module=prior.module;module.CASE=HERE;module.OUT=OUT
old=module.install_geometry

def apply(cfg,state):
    geometry=old(cfg,state)
    _,_,raw,frame,network,_,lanes=module.inputs()
    result,receipt=install(cfg,state,raw,frame,network,lanes)
    changed={k for k,v in vars(result).items() if not equal(v,vars(state)[k])}
    assert changed=={'urban_movement_queue','local_observation_summary','gate_initial_route_tags','_control_area_ledger'}
    for k in changed:setattr(state,k,getattr(result,k))
    module.save('sc16_application.json',receipt)
    return dict(geometry,sc16_aggregate323=receipt)

module.install_geometry=apply
if __name__=='__main__':
    assert 'Ran 5 tests' in (HERE/'tests.log').read_text(encoding='utf8')
    assert 'OK' in (HERE/'tests.log').read_text(encoding='utf8')
    assert not OUT.exists(),'Preserve any previous attempt'
    OUT.parent.mkdir(parents=True,exist_ok=True)
    from src.controllers import rollout_endpoint as endpoint
    evaluate=endpoint.evaluate_price_point;checks=[]
    def checked(*args,**kwargs):
        point=evaluate(*args,**kwargs)
        tags=[dict(sec=s.time_sec,sc16=s.gate_initial_route_tags.get(SOURCE,{}),
                   sc109=s.gate_initial_route_tags.get('SC108_to_SC109',{})) for s in point.states]
        assert len(tags)==3 and all(not x['sc16'] and not x['sc109'] for x in tags)
        checks.append(tags);return point
    endpoint.evaluate_price_point=checked
    try:
        with prior.base.prior.branch() as br,prior.base.prior.enabled() as receipts:module.main()
    finally:endpoint.evaluate_price_point=evaluate
    summary=json.loads((OUT/'summary.json').read_bytes())
    assert len(checks)==2
    for stage,names in {'sc109_routes321':['run.py','candidate.py'],'sc109_initial320':['run.py','candidate.py'],
                       'sc109_transport317':['run.py','candidate.py','config.json'],
                       'sc107_shared316':['run.py','candidate.py','config.json'],
                       'branch_service315':['candidate.py','config.json'],'sc12_initial306':['candidate.py']}.items():
        for name in names:
            p=A/stage/name;summary['source_pins'][str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    for n in ('support.json','sc16_application.json'):
        report=json.loads((HERE/n if n=='support.json' else OUT/n).read_bytes())
        summary['source_pins'].update(report['source_pins'])
    assert receipts and len({r['source'] for r in receipts})==4
    module.save('transport_receipts.json',receipts);module.save('route_tag_consumption.json',checks)
    summary.update(sc16_aggregate323=True,production_adopted=False,branch_service315=br,
        inherited_311_service_fit_count=summary.pop('fits'),new_candidate_sets=1,
        candidate_scope='Past terminal composition and left service; current lane ownership; unchanged upstream service and ETA')
    module.save('summary.json',summary)
