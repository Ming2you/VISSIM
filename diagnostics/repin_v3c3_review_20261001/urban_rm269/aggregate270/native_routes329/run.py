"""One450s hold/city pair, only proven future RD33 route choices."""
from pathlib import Path
import hashlib,importlib.util,json,pickle,os
from datetime import datetime,timezone
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.native_routes329 import candidate as c

HERE=Path(__file__).resolve().parent;A=HERE.parent
OUT=Path('E:/VISSIM_analysis/20261010_native_routes329/forecast2400')
BASE=Path('E:/VISSIM_analysis/20261010_sc10_north325/forecast2400')
spec=importlib.util.spec_from_file_location('gate325_base_for329',A/'sc10_north325/run.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
module=base.module;module.CASE=HERE;module.OUT=OUT;old=module.install_geometry


def apply(cfg,state):
    geom=old(cfg,state);before=pickle.dumps(state,protocol=5)
    _,_,_,_,network,_,_=module.inputs()
    receipt=c.install(cfg,network)
    assert pickle.dumps(state,protocol=5)==before
    module.save('future_route_application.json',receipt)
    return dict(geom,native_routes329=receipt)


module.install_geometry=apply
if __name__=='__main__':
    assert not OUT.exists(),'Preserve any previous attempt'
    tests=(HERE/'tests.log').read_text(encoding='utf8')
    assert 'Ran 6 tests' in tests and 'OK' in tests
    previous=json.loads((BASE/'summary.json').read_bytes())
    for p,h in previous['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    OUT.parent.mkdir(parents=True,exist_ok=True)
    receipt=HERE/'launch.json';assert not receipt.exists(),'One bounded launch only'
    receipt.write_text(json.dumps(dict(pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat(),
        native_runs=0,forecasts450=2,output=str(OUT)),indent=2)+'\n',encoding='utf8')
    from src.controllers import rollout_endpoint as endpoint
    evaluate=endpoint.evaluate_price_point;checks=[]
    def checked(*args,**kw):
        point=evaluate(*args,**kw);gate=getattr(point.states[-1],base.c.ATTR)
        remaining=sum(gate['pending'].values())+sum(gate['ready'].values())
        assert abs(gate['received']-gate['discharged']-remaining)<1e-7
        assert all(not(r['green_sec']==0 and r['discharged']>1e-8) for r in gate['history'])
        checks.append(dict(received=gate['received'],discharged=gate['discharged'],remaining=remaining,
            route_tags_remaining={str(k):v for k,v in point.states[-1].gate_initial_route_tags.get(base.c.TARGET,{}).items()}))
        return point
    endpoint.evaluate_price_point=checked
    try:
        with base.prior.prior.base.prior.branch() as br,base.prior.prior.base.prior.enabled() as transport,base.c.enabled() as gate,c.enabled() as routes:
            module.main()
    finally:endpoint.evaluate_price_point=evaluate
    assert len(checks)==2 and routes
    module.save('gate_checks.json',dict(zip(('hold','city'),checks)))
    module.save('future_route_receipts.json',routes)
    module.save('unmodified_source_receipts.json',gate)
    summary=json.loads((OUT/'summary.json').read_bytes())
    for p,h in previous['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    summary['source_pins'].update(previous['source_pins'])
    summary['source_pins'].update(json.loads((OUT/'future_route_application.json').read_bytes())['source_pins'])
    summary.update(production_adopted=False,new_candidate_sets=1,new_fits=0,
        inherited_311_service_fit_count=summary.pop('fits'),branch_service315=br,
        native_routes329=True,scope='Future SC6 north/west accepted volume through static RD33; expected aggregate routes',
        limitations=['SC6 east has an existing route ending downstream of RD33; its continuation remains unqualified and unchanged.',
                    'Expected declared route shares, not realization of random choices or per-lane lateral gap/FIFO.',
                    'Development state fixed-command diagnostic only; no AD/unused-state/full SDMPC qualification.',
                    'Source admission, SC10 ETA, SC12 service budgets unchanged;326 nominal caps and328 source smoothing excluded.'])
    module.save('summary.json',summary)
    print('DONE329',summary['results']['city']['omega_ttt_veh_h']-summary['results']['hold']['omega_ttt_veh_h'],flush=True)

