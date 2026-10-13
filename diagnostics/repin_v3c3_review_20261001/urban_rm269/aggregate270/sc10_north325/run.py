"""One existing hold/city pair; no optimization, native or refitting."""
from pathlib import Path
import hashlib,importlib.util,json
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc10_north325 import candidate as c
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal

HERE=Path(__file__).resolve().parent;A=HERE.parent
OUT=Path('E:/VISSIM_analysis/20261010_sc10_north325/forecast2400')
spec=importlib.util.spec_from_file_location('sc16_base323',A/'sc16_aggregate323/run.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
module=prior.module;module.CASE=HERE;module.OUT=OUT;old=module.install_geometry

def apply(cfg,state):
    geom=old(cfg,state)
    _,_,raw,frame,network,_,lanes=module.inputs()
    result,receipt=c.install(cfg,state,raw,frame,network,lanes)
    changed={k for k,v in vars(result).items() if k not in vars(state) or not equal(v,vars(state)[k])}
    assert changed=={'urban_arrival_buffer','urban_storage_release_buffer','urban_movement_queue','local_observation_summary',
                     'gate_initial_route_tags','_control_area_ledger',c.ATTR},changed
    for k in changed:setattr(state,k,getattr(result,k))
    module.save('north_gate_application.json',receipt)
    return dict(geom,sc10_north325=receipt)

module.install_geometry=apply
if __name__=='__main__':
    assert not OUT.exists(),'Preserve previous attempts'
    assert 'Ran 6 tests' in (HERE/'tests.log').read_text(encoding='utf8') and 'OK' in (HERE/'tests.log').read_text(encoding='utf8')
    OUT.parent.mkdir(parents=True,exist_ok=True)
    from src.controllers import rollout_endpoint as endpoint
    evaluate=endpoint.evaluate_price_point;checks=[]
    def checked(*args,**kwargs):
        p=evaluate(*args,**kwargs);gate=getattr(p.states[-1],c.ATTR)
        history=gate['history'];assert len(history)==45
        assert not any(r['green_sec']==0 and r['discharged']>1e-8 for r in history)
        remaining=sum(gate['pending'].values())+sum(gate['ready'].values())
        assert abs(gate['received']-gate['discharged']-remaining)<1e-7
        check=dict(received=gate['received'],discharged=gate['discharged'],remaining=remaining,
                   history=history,initial_known_route_tags_at_blocks=[s.gate_initial_route_tags.get(c.TARGET,{}) for s in p.states])
        assert all(not x for x in check['initial_known_route_tags_at_blocks'])
        checks.append(check);return p
    endpoint.evaluate_price_point=checked
    try:
        with prior.prior.base.prior.branch() as br,prior.prior.base.prior.enabled() as transport,c.enabled() as north:
            module.main()
    finally:endpoint.evaluate_price_point=evaluate
    assert len(checks)==2 and north
    module.save('north_gate_checks.json',dict(zip(('hold','city'),checks)))
    module.save('north_gate_receipts.json',north)
    summary=json.loads((OUT/'summary.json').read_bytes())
    base=json.loads(Path('E:/VISSIM_analysis/20261010_sc16_aggregate323/forecast2400/summary.json').read_bytes())
    for p,h in base['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    summary['source_pins'].update(base['source_pins'])
    report=json.loads((OUT/'north_gate_application.json').read_bytes());summary['source_pins'].update(report['source_pins'])
    summary.update(production_adopted=False,new_candidate_sets=1,new_fits=0,
        inherited_311_service_fit_count=summary.pop('fits'),branch_service315=br,
        sc10_north325=True,candidate_scope='Existing source-owned aggregate fixed-gate dynamics and current turns',
        limitations=['Nominal4200veh/h gate service is uncalibrated; actual binding is reported.',
                    'Parent storage is finite; intermediate lane-by-lane FIFO/spacing is not modeled.',
                    'Current-speed ETA has20km/h floor for initial motion; future ETA uses existing speed floor.',
                    'No independent native signal-state verification or whole gain qualification from unit tests alone.'])
    module.save('summary.json',summary)
