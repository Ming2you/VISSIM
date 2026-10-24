import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'): os.environ[k]='1'
import copy, ctypes, gzip, json, pickle, sys, time
from pathlib import Path
ROOT=Path(r'C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.worktrees/sd31-upstream-20260926')
D=ROOT/'diagnostics/repin_v3c3_review_20261001/spillback256/model_fixed'
F=Path(r'D:/VISSIM_runs/20261005_rm233_235_fixed90_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
AT=3150
read=lambda p:json.loads(p.read_bytes())
def save(name,value): (D/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
class Done(BaseException):pass
def main():
    D.mkdir(exist_ok=False);os.chdir(ROOT);sys.path.insert(0,str(ROOT))
    os.environ.update(NUMSIM_REPO_ROOT=str(ROOT/'vendor/NumSim-mine'),RW_MAINLINE_SG_ONLY='1',RW_OFFSET_WRITER='experiment',RW_RAMP_AMBER_SEC='0',PYTHONDONTWRITEBYTECODE='1',RW_DECISION_FAIL_FAST='1')
    k=ctypes.WinDLL('kernel32');k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32];assert k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,obs150_contract as oc,runtime_setup,head_service_resources,vsl_exposure_history,sdmpc_pfo,sdmpc_sequence as seq
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
    captured={};history=[];configure=runtime_setup.configure_runtime;demand=adapter.demand_from_state
    def runtime(*a,**kw):
        result=configure(*a,**kw);captured.update(state=result[0],cfg=a[1],tuning=a[2]);return result
    def forecast(*a,**kw):
        result=demand(*a,**kw);captured['forecast']=result;return result
    runtime_setup.configure_runtime=runtime;adapter.demand_from_state=forecast
    def readonly(raw,derived):
        p=oc.resolve(raw[oc.RAW_STATE_KEY],oc.derived_path(derived['sim_sec']));assert p.read_bytes()==oc.derived_bytes(derived);return p
    oc.write_derived=readonly
    observe=head_service_resources.observe
    def warm(original,cfg,raw,previous_path,caps,plan,distribute,options):
        return probe.replay_head_history(observe,original,cfg,raw,caps,plan,distribute,options,folder=F,sim_sec=AT,output=D,history_inputs=history)
    head_service_resources.observe=warm
    initialize=vsl_exposure_history.initialize
    vsl_exposure_history.initialize=lambda context,raw,state,cfg:probe.replay_vsl_history(initialize,context,raw,state,cfg,D,known_missing_online_cutoffs=[])
    def audit(reference,coord,policy,options,evaluate,derivative,quantities,check_budget,emit):
        from src.models.state import ControlAction
        from evaluation.controllers.physical_ramp_branches import candidate_from_greens
        from src.controllers import rollout_endpoint as endpoint
        from evaluation.controllers.area_runtime import model_inventory
        from evaluation.controllers.control_area_objective import get_ledger
        controls=[]
        for sec in (3150,3300,3450):
            row=read(F/f'action_{sec:06d}.json')
            c=seq.first_action(reference)
            for name in seq.FIELDS:
                if name!='diagnostics' and name in row:setattr(c,name,copy.deepcopy(row[name]))
            c.diagnostics={key:value for key,value in row['diagnostics'].items() if key.startswith('rw_meter_')}
            controls.append(c)
        released=[]
        for i,c in enumerate(controls):
            greens={r:c.diagnostics['rw_meter_green_'+r] for r in captured['cfg'].network.ramps}
            greens['RM_C10480']=2+2*i
            released.append(candidate_from_greens(c,released[-1] if released else seq.first_action(reference),captured['cfg'],greens))
        actions={'hold':seq.pack(controls),'release':seq.pack(released)}
        with (D/'capture.pkl').open('wb') as f:pickle.dump(dict(captured=captured,actions=actions,reference=reference),f,protocol=5)
        state=captured['state'];cfg=captured['cfg']
        save('initial.json',dict(time=state.time_sec,ramps=state.ramp_queue,storage={s:model_inventory(state,cfg)[s] for s in ['storage:SC1001_W_out','storage:lane_off_10483']},direct=state.direct_exit_route_state,travel=cfg.network.direct_exit_legsplit,physical=cfg.network.physical_ramp_branches['ramps']['RM_C10480']))
        for name,action in actions.items():
            started=time.perf_counter()
            with seq.prediction_scope(action,cfg,AT,3):
                point=endpoint.evaluate_price_point(copy.deepcopy(state),action,copy.deepcopy(captured['forecast']),(),endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
            assert not point.aborted and len(point.states)==3
            snapshots=[]
            for s in [state,*point.states]:
                inv=model_inventory(s,cfg);get_ledger(s).assert_stocks(inv)
                snapshots.append(dict(time=s.time_sec,inventory=inv,ramps=s.ramp_queue,direct=s.direct_exit_route_state,speed=s.freeway_speed))
            with gzip.open(D/(name+'_response.json.gz'),'wt',encoding='utf-8') as f:json.dump(point.control_area_response,f)
            save(name+'.json',dict(ttt=point.ttt,seconds=time.perf_counter()-started,snapshots=snapshots))
            print(name,point.ttt,time.perf_counter()-started,flush=True)
        raise Done()
    sdmpc_pfo.solve=audit
    sys.argv=[adapter.__file__,'--state-json',str(F/'state_003150.json'),'--previous-action-json',str(F/'action_003000.json'),'--out-action-json',str(D/'unused.json'),'--out-action-csv',str(D/'unused.csv'),'--mapping-json',str(ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'),'--detector-mapping-json',str(ROOT/'evaluation/real_world_modi_control_ver2_20260907/detector_local_mapping_ver2_20260907.json'),'--calibration-json',str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'),'--tuning-json',str(ROOT/'diagnostics/repin_v3c3_review_20261001/spillback256/config.json'),'--controller','wu-link']
    try:adapter.main()
    except Done:save('completion.json',dict(status='complete',predictions=2))
    else:raise AssertionError('Expected diagnostic stop')
if __name__=='__main__':main()
