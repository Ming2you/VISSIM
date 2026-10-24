"""One canonical actuator rollout of the repaired saved-stage selection."""
import copy
import ctypes
import hashlib
import json
import os
from pathlib import Path
import pickle
import sys
import time
from types import SimpleNamespace as NS

D=Path(__file__).resolve().parent
ROOT=D.parents[3]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
OUT=D/'execution_v2'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def save(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def main():
    assert not OUT.exists(), 'Preserve previous check'
    completed=json.loads((D/'postsearch/completion.json').read_bytes())
    assert completed['source_unchanged']
    pins=json.loads((D/'postsearch/protocol.json').read_bytes())['source_sha256']
    assert all(sha(ROOT/p)==h for p,h in pins.items())
    selected=D/'postsearch/selected_action.pkl'
    pins[str(selected)]=sha(selected)
    pins[str(Path(__file__))]=sha(Path(__file__))
    OUT.mkdir()
    os.chdir(ROOT)
    os.environ.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',
        NUMSIM_REPO_ROOT=str(ROOT/'vendor/NumSim-mine'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',
        RW_DECISION_FAIL_FAST='1',RW_MAINLINE_SG_ONLY='1',RW_OFFSET_WRITER='experiment',RW_RAMP_AMBER_SEC='0')
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.GetCurrentProcess.restype=ctypes.c_void_p
    k.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
    sys.path.insert(0,str(ROOT))
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
    from evaluation.controllers import sdmpc_sequence as sequence
    from evaluation.controllers import area_leader_objective as constraints
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    replay=probe.replay_vsl_history
    probe.replay_vsl_history=lambda *a,**kw:replay(*a,**kw,allow_missing_current_online=True)
    original_levers=probe.probe_levers

    def execute(captured,candidates,coord,output):
        from src.controllers import rollout_endpoint as endpoint
        action=pickle.loads(selected.read_bytes())
        cfg,state=captured['cfg'],captured['state']
        assert set(candidates)=={'held_actual'} and state.time_sec==4500
        started=time.perf_counter()
        with sequence.prediction_scope(action,cfg,state.time_sec,3) as visits:
            point=endpoint.evaluate_price_point(state,action,copy.deepcopy(captured['forecast']),(),
                endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
        assert visits==[0,1,2] and not point.aborted and len(point.states)==3
        response=point.control_area_response
        save('forecast_completed.json',dict(ttt_omega_veh_h=point.ttt,wall_sec=time.perf_counter()-started,
            blocks=visits,scope='Forecast completed; quantity and ledger verification still pending'))
        local={s:NS(signal=s,movements=[m for m,v in cfg.network.urban_movements.items() if v['signal']==s],
                    kind_of={m:v['kind'] for m,v in cfg.network.urban_movements.items() if v['signal']==s})
               for s in cfg.network.signals}
        fw={road:NS(link=road,owned_ramps=[r for r in cfg.network.ramps if cfg.network.ramp_to_freeway[r]==road])
            for road in cfg.network.freeway_links}
        follower=NS(cfg=cfg,_local_models=local,_local_freeway_models=fw)
        raw=constraints.shared_urban_quantities(follower,response,start_sec=4500,horizon_steps=3)
        q=constraints.shared_quantity_constraints(follower,action,raw,start_sec=4500,horizon_steps=3,
            np_mode='cap',target_np_veh=action.N_P_star,np_tolerance_veh=1e-7,
            nuf_mode='cap',target_nuf_veh_h=action.N_UF_star,nuf_tolerance_veh_h=1e-7)
        held_path=I/'closedloop_recorded4500_lever450_rm233_projection_after_4500_held/held_actual.json'
        held=json.loads(held_path.read_bytes())
        held_commands=[dict(vsl=a.vsl,green_times=a.green_times,offsets=a.offsets,
            meters={r:a.diagnostics['rw_meter_green_'+r] for r in cfg.network.ramps})
            for a in sequence.actions(candidates['held_actual'],3)]
        assert held_commands==held['commands'], 'Reused held commands differ'
        from evaluation.controllers.area_runtime import model_inventory
        from evaluation.controllers.control_area_objective import get_ledger
        for saved in (state,*point.states):get_ledger(saved).assert_stocks(model_inventory(saved,cfg))
        outside=sum(r['dt_h']*sum(max(0.,r['model_stock_veh'][key]-n) for key,n in r['inside_veh'].items()) for r in response['residence'])
        save('assessment.json',dict(ttt_omega_veh_h=point.ttt,held_execution_veh_h=held['ttt_omega_veh_h'],
            delta_from_held_execution_veh_h=point.ttt-held['ttt_omega_veh_h'],held_source=str(held_path),held_source_sha256=sha(held_path),
            tracked_outside_residence_veh_h=outside,delta_tracked_outside_veh_h=outside-held['tracked_outside_residence_veh_h'],
            constraints=q,model_constraint_coverage=response['model_constraint_coverage'],
            conditional_model_feasibility_witness=response['conditional_model_feasibility_witness'],
            resource_max_exceedance_veh=max((r['exceedance_veh'] for r in response['resource_allocations']),default=0.),
            wall_sec=time.perf_counter()-started,blocks=visits,new_predictions=1,native_runs=0,fit=0,
            saved_state_ledger_checks=4,reused_held_commands_match=True,
            scope='Discrete signal timing within the existing plant, not VISSIM. Reuse233 held forecast: same state/history/physical config, only upper search count differs.'))

    def wrapped(captured,reference,output,**kwargs):
        return original_levers(captured,reference,output,**kwargs,prepared_probe_callback=execute)
    probe.probe_levers=wrapped
    protocol=json.loads((D/'protocol.json').read_bytes())
    argv=['--held450' if x=='--select' else x.replace('rm235_three_budgets','rm235_exact_selected_v2') for x in protocol['argv']]
    save('protocol.json',dict(source_sha256=pins,maximum_predictions=1,optimizer_iterations=0,native_runs=0,fzp_reads=0,argv=argv))
    sys.argv=[probe.__file__,*argv]
    started=time.perf_counter()
    probe.main()
    assert all(sha(ROOT/p)==h for p,h in pins.items())
    assert (OUT/'assessment.json').exists()
    save('completion.json',dict(status='actuator_model_check_complete_not_native_validation',
        wall_sec=time.perf_counter()-started,source_unchanged=True,native_runs=0))


if __name__=='__main__':main()
