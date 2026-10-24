"""One instrumented replay to separate52 storage, upstream supply and shared-head flow."""
import os
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[name]='1'
import copy,gzip,hashlib,importlib.util,json,pickle,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
H=HERE.parent.parent
OUT=HERE/'replay3300'
TUNING=HERE.parent/'urban_clock277/config_fw5_urban10.json'
F=Path('E:/VISSIM_runs/20261008_coupling268_window_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())

def save(name,value):
    (OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')

def main():
    assert not OUT.exists()
    assert not any((p/'STOP').exists() for p in (ROOT,H,HERE,HERE.parent))
    closed=read('E:/VISSIM_runtime/20261008_coupling268_vsl_three/queue_state.json')['conditions']['window']
    assert closed['normal_sim_done']==8100 and closed['owners_closed'] and closed['native_exit_code']==0
    prior=read(HERE.parent/'validation278/unseen3300_fw5_urban10/response_validation.json')
    pins={str(p):sha(p) for p in (ROOT/'evaluation/controllers').glob('*.py')}
    for path,digest in prior['source_pins'].items():
        assert sha(path)==digest,path
    pins[str(TUNING)]=sha(TUNING)
    pins[str(Path(__file__))]=sha(__file__)
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    sys.argv=['verify.py','--at','3300','--out',str(OUT),'--no-prediction','--cold-prices',
        '--tuning',str(TUNING),'--decisions',str(F)]
    loader=importlib.util.spec_from_file_location('flow279_verifier',H.parent/'urban260/verify.py')
    v=importlib.util.module_from_spec(loader);loader.loader.exec_module(v)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc_pfo,sdmpc_sequence as seq
    from evaluation.controllers import physical_ramp_branches as ramps,signal_actuation_contract as signals
    from evaluation.controllers.control_area_objective import get_ledger
    from evaluation.controllers.area_runtime import model_inventory
    from src.controllers import rollout_endpoint as endpoint
    from src.models.state import ControlAction
    original_main=adapter.main
    def wrapped_main():
        captured={}
        bound,forecast=ramps.configure_operating_bounds,adapter.demand_from_state
        def capture_bound(state,cfg,reference):
            captured.update(state=state,cfg=cfg)
            return bound(state,cfg,reference)
        def capture_forecast(*args,**kwargs):
            result=forecast(*args,**kwargs);captured['forecast']=result;return result
        ramps.configure_operating_bounds=capture_bound;adapter.demand_from_state=capture_forecast
        def audit(*args,**kwargs):
            state,cfg=captured['state'],captured['cfg']
            assert state.time_sec==3300 and cfg.simulation.T_f_sec==5 and cfg.simulation.T_u_sec==10
            blocks=[]
            for at in (3300,3450,3600):
                path=F/f'action_{at:06}.json'
                assert path.with_suffix('.json.applied').exists() and sha(path)==prior['command_pins'][str(path)]
                command=seq.first_action(adapter.control_from_json(path,cfg,ControlAction))
                signals.validate_writer(command,cfg,adapter.load_signal_group_actuation_plan(),'experiment')
                blocks.append(command)
            action=seq.pack(blocks)
            (OUT/'initial.pickle').write_bytes(pickle.dumps((cfg,state,action,captured['forecast']),protocol=5))
            start=time.perf_counter()
            with seq.prediction_scope(action,cfg,3300,3) as visits:
                point=endpoint.evaluate_price_point(state,action,copy.deepcopy(captured['forecast']),(),
                    endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
            assert not point.aborted and len(point.states)==3 and visits==[0,1,2]
            response=point.control_area_response
            assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
            assert abs(float(point.ttt)-prior['predicted_omega_ttt_veh_h'])<1e-8
            states=[]
            for current in (state,*point.states):
                ledger=get_ledger(current);ledger.assert_stocks(model_inventory(current,cfg))
                states.append(dict(time_sec=current.time_sec,stocks=ledger.stocks))
            save('stocks.json',states)
            (OUT/'response.json.gz').write_bytes(gzip.compress(json.dumps(response,allow_nan=False).encode('utf8')))
            assert all(sha(path)==digest for path,digest in pins.items())
            save('summary.json',dict(status='complete_equivalent_instrumented_replay',wall_sec=time.perf_counter()-start,
                omega_ttt_veh_h=point.ttt,prior_ttt_veh_h=prior['predicted_omega_ttt_veh_h'],source_pins=pins,
                new_predictions=1,new_fits=0,new_native_runs=0,new_full_selections=0))
            print('INSTRUMENTED_RESPONSE_COMPLETE',point.ttt,flush=True)
            raise v.Done()
        sdmpc_pfo.solve=audit
        return original_main()
    adapter.main=wrapped_main
    v.main()

if __name__=='__main__':main()
