"""Capture the exact331 model and canonical SDMPC coordinates; no rollout."""
from pathlib import Path
import copy, hashlib, importlib.util, json, pickle, sys

HERE=Path(__file__).resolve().parent; A=HERE.parent; H=A.parent; ROOT=HERE.parents[4]
BASE=A/'transfer331/build3300_v2'; OUT=HERE/'capture_v2'
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,value):
    (OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')

def main():
    assert not OUT.exists(), 'Preserve prior capture'
    assert not any((p/'STOP').exists() for p in (ROOT,H,A,HERE))
    proof=read(BASE/'summary.json'); assert proof['status']=='complete'
    pins=dict(proof['source_pins'])
    for p,h in pins.items(): assert sha(p)==h,p
    for p in (BASE/'canonical.pickle',BASE/'initial.pickle',BASE/'summary.json',Path(__file__)):
        pins[str(p)]=sha(p)
    sys.argv=['verify.py','--at','3300','--out',str(OUT),'--no-prediction','--cold-prices',
              '--tuning',str(A/'flow279/config_10686_free.json'),'--decisions',proof['source']]
    spec=importlib.util.spec_from_file_location('worker334_capture_verifier',H.parent/'urban260/verify.py')
    verifier=importlib.util.module_from_spec(spec); spec.loader.exec_module(verifier)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter, sdmpc_pfo, sdmpc_tangent
    from evaluation.controllers import physical_ramp_branches as ramps, sdmpc_sequence as seq, signal_actuation_contract as signals
    from evaluation.controllers.sdmpc_tangent_surrogate import Query
    from src.models.state import ControlAction
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.response332.commands import pair
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_phase305.candidate import hook
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.branch_service315.candidate import enabled as branch
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_transport317.candidate import enabled as transport
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc10_north325.candidate import enabled as north
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.native_routes329.candidate import enabled as routes
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc107_shared316.candidate import refresh_local
    original=adapter.main; captured={}; done=False
    def wrapped():
        bound,forecast=ramps.configure_operating_bounds,adapter.demand_from_state
        def capture_bound(state,cfg,reference):
            captured.update(state=state,cfg=cfg)
            return bound(state,cfg,reference)
        def capture_forecast(*a,**kw):
            value=forecast(*a,**kw);captured['forecast']=value;return value
        ramps.configure_operating_bounds=capture_bound;adapter.demand_from_state=capture_forecast
        def audit(reference,coord,policy,options,evaluate,derivative,*unused):
            nonlocal done
            query=derivative.__self__
            assert isinstance(query,Query) and query.stats()['total_rollouts']==0
            old_request=pickle.loads(query.template)
            cfg,state=captured['cfg'],captured['state']
            basecfg,basestate,baseforecast=pickle.loads((BASE/'canonical.pickle').read_bytes())
            parity=dict(cfg=equal(cfg,basecfg),state=equal(state,basestate),forecast=equal(captured['forecast'],baseforecast))
            save('bootstrap_parity.json',parity);assert all(parity.values()),parity
            frozen_cfg,state,forecast=pickle.loads((BASE/'initial.pickle').read_bytes())
            assert equal(forecast,captured['forecast'])
            assert all(equal(v,getattr(frozen_cfg,k)) for k,v in vars(cfg).items() if k!='network')
            keys=set(vars(cfg.network))|set(vars(frozen_cfg.network))
            changed=sorted(k for k in keys if not equal(getattr(cfg.network,k,None),getattr(frozen_cfg.network,k,None)))
            assert set(vars(cfg.network))<=set(vars(frozen_cfg.network))
            for k in changed:setattr(cfg.network,k,copy.deepcopy(getattr(frozen_cfg.network,k)))
            assert equal(cfg,frozen_cfg)
            follower=adapter._PHASE_VECTOR_FOLLOWER['ref']
            binding=refresh_local(follower,cfg)
            cap_path=A/'decision285/full3300_current/unused.json'
            cap=adapter.control_from_json(cap_path,cfg,ControlAction);pins[str(cap_path)]=sha(cap_path)
            action=seq.pack(pair(reference,cfg,cap)['hold'])
            coord.validate(action)
            for b in seq.actions(action,3): signals.validate_writer(b,cfg,adapter.load_signal_group_actuation_plan(),'experiment')
            request=sdmpc_tangent.prepare_request(follower,state,forecast[:3],reference,action,coord,old_request['bootstrap'])
            request['diagnostic_stock_costs']=True
            request['surrogate_context_sha256']=hashlib.sha256(pickle.dumps((request['owned'],request['runtime'],request['bootstrap'],3),protocol=5)).hexdigest()
            assert request['horizon']==3 and cfg.simulation.T_c_sec==150 and len(coord.axes)==213
            assert cfg.simulation.T_u_sec==10
            data=pickle.dumps(request,protocol=5);(OUT/'request.pickle').write_bytes(data)
            assert all(sha(p)==h for p,h in pins.items())
            save('summary.json',dict(status='complete',request_sha256=hashlib.sha256(data).hexdigest(),
                source_pins=pins,network_fields=changed,local_binding=binding,bootstrap_exact=True,
                cfg_state_forecast_exact=True,axes=len(coord.axes),writer_blocks=3,forecast_count=0,
                model='331/329 fixed, same as332',anchor='isolated10681 hold g2/2/2, other3150 controls and285 caps',
                simulation=vars(cfg.simulation),production_adopted=False))
            done=True;raise verifier.Done()
        sdmpc_pfo.solve=audit
        return original()
    adapter.main=wrapped
    with branch(),transport(),north(),routes(),hook('source_path_current_physical_speed'): verifier.main()
    assert done
    print('CAPTURE334_DONE: exact331 model,213 axes,zero rollouts',flush=True)

if __name__=='__main__':main()
