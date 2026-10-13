"""Reconstruct two saved states with fixed329 diagnostics; zero forecasts.

The legacy311 runner hardcodes2400. Reuse its component functions, not its
snapshot loader or exact nonzero-change assumptions. No production edits.
"""
from pathlib import Path
import argparse, copy, hashlib, importlib.util, json, os, pickle, sys, time
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.transfer331.inputs import load, require_past
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.transfer331 import gate_coverage
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal

HERE=Path(__file__).resolve().parent;A=HERE.parent;H=A.parent;ROOT=HERE.parents[4]
TUNING=A/'flow279/config_10686_free.json'
PREVIOUS=Path('E:/VISSIM_analysis/20261010_rm_response330/forecast2400_v2')
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--at',type=int,choices=(2400,3300),required=True)
    ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    at=args.at;out=args.out.resolve()
    assert not out.exists(),'Preserve previous attempts'
    assert not any((p/'STOP').exists() for p in (ROOT,H,A,HERE))
    source=(Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
            if at==2400 else Path(read(A/'decision285/full_decision_execution.json')['decisions']))
    # Old STOP applies to native reruns, not reading these closed observations.
    raw,frame,pins=load(source,at)
    old=read(PREVIOUS/'summary.json')
    for p,h in old['source_pins'].items():assert sha(p)==h,p
    pins.update(old['source_pins'])
    for p in (*HERE.glob('*.py'),*HERE.glob('tests*.log'),HERE/'plan.json',source/f'action_{at-150:06}.json'):
        pins[str(p)]=sha(p)
    sys.argv=['verify.py','--at',str(at),'--out',str(out),'--no-prediction',
              '--cold-prices','--tuning',str(TUNING),'--decisions',str(source)]
    spec=importlib.util.spec_from_file_location('transfer331_verifier',H.parent/'urban260/verify.py')
    verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
    save=lambda n,v:(out/n).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc_pfo,physical_ramp_branches as ramps
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_phase305.candidate import hook,validate_turns
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306 import candidate as initial306
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.sc101_recombined import candidate as service304
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_composite308 import candidate as service308
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc108_side310 import candidate as service310
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc108_geometry311 import candidate as geometry311
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc107_shared316 import candidate as shared316
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_transport317 import candidate as transport317
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_initial320 import candidate as timing320
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_routes321 import candidate as routes321
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc16_aggregate323 import candidate as aggregate323
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc10_north325 import candidate as gate325
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.native_routes329 import candidate as routes329
    network_path=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    network=network_path.read_bytes();pins[str(network_path)]=sha(network_path)
    sides,mp=routes321.membership();pins[str(mp)]=sha(mp)
    lanes=adapter._contiguous_stopline_queue(raw,per_lane=True)
    original=adapter.main;captured={};steps=[];done=False
    def wrapped():
        bound=ramps.configure_operating_bounds;forecast=adapter.demand_from_state
        def capture_bound(state,cfg,reference):
            captured.update(state=state,cfg=cfg,reference=reference)
            return bound(state,cfg,reference)
        def capture_forecast(*a,**kw):
            value=forecast(*a,**kw);captured['forecast']=value;return value
        ramps.configure_operating_bounds=capture_bound;adapter.demand_from_state=capture_forecast
        def prepare(reference,coord,policy,options,*unused):
            nonlocal done
            cfg,state=captured['cfg'],captured['state']
            assert state.time_sec==at and cfg.simulation.T_f_sec==5 and cfg.simulation.T_u_sec==10
            def stock(s):return {side:sum(v[side] for v in get_ledger(s).stocks.values()) for side in ('inside','outside')}
            initial=stock(state)
            assert initial['inside']==sum(sides[str(v['link_no'])] for v in raw['vehicle_records']['records'])
            (out/'canonical.pickle').write_bytes(pickle.dumps((cfg,state,captured['forecast']),protocol=5))
            def record(name,value):
                save(name+'.json',value);steps.append(name);save('steps.json',steps)
                get_ledger(state).assert_stocks(model_inventory(state,cfg))
                assert all(abs(stock(state)[k]-v)<1e-7 for k,v in initial.items()),name
            def replace(result):
                nonlocal state
                state=result;captured['state']=state
            record('service304',service304.install(cfg,at))
            validate_turns(cfg.network)
            result,receipt=initial306.project(state,cfg,raw,frame,network,sides[initial306.LINK],lanes)
            replace(result);record('initial306',receipt)
            # Historical support is frozen, not a current2400 state input.
            require_past(2400,at)
            receipt=service308.install(cfg,2400)
            record('service308',dict(receipt,support_snapshot_sec=2400,applied_at_sec=at))
            record('service310',service310.install(cfg,at))
            record('geometry311',geometry311.install(cfg,state))
            receipt=shared316.install(cfg)
            receipt['owner_binding']=shared316.refresh_local(adapter._PHASE_VECTOR_FOLLOWER['ref'],cfg)
            record('shared316',receipt)
            record('transport317',transport317.install(cfg,state))
            timing=timing320.install(cfg,state,raw,frame,network,lanes);record('timing320',timing)
            result,receipt=routes321.install(cfg,state,raw,frame,network,timing)
            replace(result);record('routes321',receipt)
            result,receipt=aggregate323.install(cfg,state,raw,frame,network,lanes)
            replace(result);record('aggregate323',receipt)
            with gate_coverage.enabled(network) as coverage:
                result,receipt=gate325.install(cfg,state,raw,frame,network,lanes)
            save('gate_coverage.json',coverage)
            replace(result);record('gate325',receipt)
            record('routes329',routes329.install(cfg,network))
            (out/'initial.pickle').write_bytes(pickle.dumps((cfg,state,captured['forecast']),protocol=5))
            if at==2400:
                prior_cfg,prior_state,prior_forecast=pickle.loads((PREVIOUS/'initial.pickle').read_bytes())
                state_diff=[k for k in set(vars(state))|set(vars(prior_state)) if not equal(getattr(state,k,None),getattr(prior_state,k,None))]
                cfg_diff=[k for k in set(vars(cfg.network))|set(vars(prior_cfg.network)) if not equal(getattr(cfg.network,k,None),getattr(prior_cfg.network,k,None))]
                comparison=dict(state_differences=state_diff,network_differences=cfg_diff,
                                forecast_equal=equal(captured['forecast'][:3],prior_forecast))
                save('parity2400.json',comparison)
                assert not state_diff and not cfg_diff and comparison['forecast_equal'],comparison
            assert all(sha(p)==h for p,h in pins.items())
            save('summary.json',dict(status='complete',at_sec=at,initial_mass=initial,final_mass=stock(state),
                source=str(source),source_pins=pins,installations=steps,forecasts=0,ad=0,optimizer=0,
                native_runs=0,new_fits=0,production_adopted=False,future_observation_inputs=False,
                limitations=['This verifies assimilation only; forecast/AD/SDMPC integration is not yet verified.',
                             'Frozen historical support values are not new3300 measurements or independent seed evidence.']))
            done=True
            raise verifier.Done()
        sdmpc_pfo.solve=prepare
        return original()
    adapter.main=wrapped
    start=time.perf_counter()
    try:
        with hook('source_path_current_physical_speed'):
            verifier.main()
        assert done
    except BaseException as exc:
        if out.exists():save('failure.json',dict(type=type(exc).__name__,error=str(exc),completed_steps=steps))
        raise
    print('TRANSFER331_INITIALIZED',at,'seconds',time.perf_counter()-start,flush=True)

if __name__=='__main__':main()
