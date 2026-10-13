"""Exactly one fixed hold/city pair with326 head caps; no re-optimization."""
from pathlib import Path
import hashlib,importlib.util,json,pickle
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_head326 import candidate as c

HERE=Path(__file__).resolve().parent;A=HERE.parent
OUT=Path('E:/VISSIM_analysis/20261010_sc12_head326/forecast2400')
BASE=Path('E:/VISSIM_analysis/20261010_sc10_north325/forecast2400')
spec=importlib.util.spec_from_file_location('gate325_base_for326',A/'sc10_north325/run.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
module=base.module;module.CASE=HERE;module.OUT=OUT;old=module.install_geometry


def apply(cfg,state):
    geometry=old(cfg,state);before=pickle.dumps(state,protocol=5)
    receipt=c.install(cfg)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    receipt['owner_binding']=c.refresh_local(adapter._PHASE_VECTOR_FOLLOWER['ref'],cfg)
    assert pickle.dumps(state,protocol=5)==before
    module.save('head_application.json',receipt)
    return dict(geometry,sc12_head326=receipt)

module.install_geometry=apply
if __name__=='__main__':
    assert not OUT.exists(),'Preserve any prior attempt'
    tests=(HERE/'tests.log').read_text(encoding='utf8')
    assert 'Ran 6 tests' in tests and 'OK' in tests
    previous=json.loads((BASE/'summary.json').read_bytes())
    for p,h in previous['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    OUT.parent.mkdir(parents=True,exist_ok=True)
    from src.controllers import rollout_endpoint as endpoint
    evaluate=endpoint.evaluate_price_point;checks=[]
    def checked(*args,**kw):
        point=evaluate(*args,**kw);gate=getattr(point.states[-1],base.c.ATTR)
        remaining=sum(gate['pending'].values())+sum(gate['ready'].values())
        assert abs(gate['received']-gate['discharged']-remaining)<1e-7
        assert all(not(r['green_sec']==0 and r['discharged']>1e-8) for r in gate['history'])
        checks.append(dict(received=gate['received'],discharged=gate['discharged'],remaining=remaining))
        return point
    endpoint.evaluate_price_point=checked
    try:
        with base.prior.prior.base.prior.branch() as br,base.prior.prior.base.prior.enabled() as transport,base.c.enabled() as gate,c.enabled():
            module.main()
    finally:endpoint.evaluate_price_point=evaluate
    assert len(checks)==2
    module.save('gate_checks.json',dict(zip(('hold','city'),checks)))
    summary=json.loads((OUT/'summary.json').read_bytes())
    summary['source_pins'].update(previous['source_pins'])
    summary['source_pins'].update(json.loads((OUT/'head_application.json').read_bytes())['source_pins'])
    summary.update(production_adopted=False,new_candidate_sets=1,new_fits=0,
        inherited_311_service_fit_count=summary.pop('fits'),branch_service315=br,
        sc12_head326=True,scope='SC12 north shared three-head cap and one-head right-turn bound',
        limitations=['Nominal1400/head is a provisional prior, not calibrated saturation.',
                    'Existing aggregate proportional multi-receiver sharing is conservative; dedicated through lanes and lane FIFO are not resolved.',
                    'SC10 current-speed ETA and source admission uncertainty remain unchanged.',
                    'Development state fixed-command diagnostic only; no AD/unused-state/full SDMPC qualification.'])
    module.save('summary.json',summary)
