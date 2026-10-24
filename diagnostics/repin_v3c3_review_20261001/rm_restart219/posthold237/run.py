"""Use the production adapter after an actually applied error-hold command.

No fabricated price receipt, optimizer, native run, or future observation input.
"""
import copy
import ctypes
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time

BASE=Path(__file__).resolve().parent
PREPARE='--prepare-native' in sys.argv[1:]
D=BASE.parent/'native238' if PREPARE else BASE
ROOT=D.parents[3]
F=Path('D:/VISSIM_runs/20261005_rm219_fixed90_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
AT=4650
CONFIG=D.parent/'budget235/config.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())


def save(name,value):
    (D/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


class Complete(BaseException):pass


def main():
    if PREPARE:D.mkdir(exist_ok=True)
    assert not (D/'protocol.json').exists(), 'Preserve prior attempts'
    os.chdir(ROOT)
    os.environ.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',
        NUMSIM_REPO_ROOT=str(ROOT/'vendor/NumSim-mine'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',
        RW_DECISION_FAIL_FAST='1',RW_MAINLINE_SG_ONLY='1',RW_OFFSET_WRITER='experiment',RW_RAMP_AMBER_SEC='0')
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=ctypes.c_void_p
    kernel.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    sys.path.insert(0,str(ROOT))
    old_pins=read(D.parent/'reselect236/protocol.json')['source_sha256']
    changed='diagnostics/sdmpc_n31_20260924/integration_20260926/probe_selected_arrival_path.py'
    assert sha(BASE/'probe_selected_arrival_path.py.before')==old_pins[changed]
    assert all(sha(ROOT/p)==h for p,h in old_pins.items() if p!=changed)
    pins={p:sha(ROOT/p) for p in old_pins}
    execution_path=D.parent/'analysis/sdmpc/execution.json'
    execution=read(execution_path)
    assert execution['native_execution_passed'] and execution['terminal_sec']==9000
    assert Path(execution['run_directory']).resolve()==F.parent.resolve()
    previous=F/f'action_{AT-150:06d}.json'
    raw=read(previous)
    assert raw['metadata']['controller_status']=='hold_previous_error'
    assert raw['run_provenance']['run_id']==execution['run_id']
    chain_path=D.parent/'reselect236/hold_chain.json'
    chain=read(chain_path)
    row=next(r for r in chain['records'] if r['sim_sec']==AT-150)
    assert row['action_sha256']==sha(previous) and row['physical_command_unchanged']
    assert row['price_loader_accepts_hold'] and not Path(str(previous)+'.applied').exists()
    missing=[]
    for sec in range(150,AT+1,150):
        if not (F/f'obs150/vsl_cohorts_{sec:06d}.json').exists():
            failure=F/f'action_{sec:06d}.error.txt'
            assert 'Current lane/full-network projection differs on physical link 10483' in failure.read_text(encoding='utf-8-sig')
            missing.append(sec);pins[str(failure)]=sha(failure)
    assert missing==[4500,4650]
    for p in (Path(__file__),execution_path,chain_path,previous,previous.with_suffix('.csv'),F/f'state_{AT:06d}.json'):
        pins[str(p)]=sha(p)
    save('protocol.json',dict(purpose='Production initialization and bounded actual-command predictions after native error-hold',
        at_sec=AT,horizon_sec=450,source_sha256=pins,known_missing_online_cutoffs=missing,
        observation_inputs_end_sec=AT,future_native_validation_receipt_used_only_for_command_proof=True,
        max_scalar_predictions=0 if PREPARE else 3,max_discrete_actuator_predictions=2 if PREPARE else 0,
        optimizer_calls=0,native_runs=0,new_fzp_reads=0,fit=0,
        prior_turn='PROGRESS: full236 selection/writer and native hold chain verified',
        scope='Caps inherited only for diagnostic comparison; fresh PFO budgets are not computed'))
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,obs150_contract as oc
    from evaluation.controllers import runtime_setup,head_service_resources,vsl_exposure_history
    from evaluation.controllers import sdmpc,sdmpc_pfo,sdmpc_sequence as sequence
    from evaluation.controllers import area_leader_objective as constraints
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
    captured={}; query_ref=[]; history_inputs=[]
    configure=runtime_setup.configure_runtime
    def capture_runtime(*args,**kwargs):
        result=configure(*args,**kwargs)
        captured.update(state=result[0],cfg=args[1],tuning=args[2],mapping=args[3],raw=args[4],metadata=result[2],calibration=args[7])
        return result
    runtime_setup.configure_runtime=capture_runtime
    demand=adapter.demand_from_state
    def capture_forecast(*args,**kwargs):
        result=demand(*args,**kwargs);captured['forecast']=result
        return result
    adapter.demand_from_state=capture_forecast
    def read_only(raw,derived):
        p=oc.resolve(raw[oc.RAW_STATE_KEY],oc.derived_path(derived['sim_sec']))
        assert p.read_bytes()==oc.derived_bytes(derived)
        return p
    oc.write_derived=read_only
    observe=head_service_resources.observe
    def warm_heads(original,cfg,raw,previous_path,caps,plan,distribute,options):
        return probe.replay_head_history(observe,original,cfg,raw,caps,plan,distribute,options,
            folder=F,sim_sec=AT,output=D,history_inputs=history_inputs)
    head_service_resources.observe=warm_heads
    initialize=vsl_exposure_history.initialize
    vsl_exposure_history.initialize=lambda context,raw,state,cfg:probe.replay_vsl_history(
        initialize,context,raw,state,cfg,D,known_missing_online_cutoffs=missing)
    price_loader=sdmpc.load_prices
    def record_prices(*args,**kwargs):
        prices,receipt=price_loader(*args,**kwargs)
        save('prior_prices.json',dict(prices=prices.tolist(),receipt=receipt))
        return prices,receipt
    sdmpc.load_prices=record_prices
    def audit(reference,coord,policy,options,evaluate,derivative,quantities,check_budget,emit):
        query=derivative.__self__;query_ref.append(query)
        if PREPARE:
            from diagnostics.repin_v3c3_review_20261001.rm_restart219.native238.prepare_commands import prepare
            prepare(captured,reference,coord,options)
            raise Complete()
        neighbors=dict(sdmpc.meter_neighbors(coord,reference))
        cases=[('hold',reference),('release10480',neighbors['RM_C10480:release']),
               ('release10681',neighbors['RM_C10681:release'])]
        for _,action in cases:coord.validate(action)
        items=evaluate([a for _,a in cases],derivatives=False)
        report={}
        follower=adapter._PHASE_VECTOR_FOLLOWER['ref']
        for (name,action),item in zip(cases,items):
            assert sdmpc_pfo.model_feasible(item,options['shared_tolerance'])
            q=constraints.shared_quantity_constraints(follower,action,item['quantities'],
                start_sec=AT,horizon_steps=3,np_mode='cap',target_np_veh=action.N_P_star,
                np_tolerance_veh=options['np_tolerance_veh'],nuf_mode='cap',target_nuf_veh_h=action.N_UF_star,
                nuf_tolerance_veh_h=policy['pfo_cap_options']['nuf_tolerance_veh_h'])
            commands=[{r:a.diagnostics['rw_meter_green_'+r] for r in coord.cfg.network.ramps}
                      for a in sequence.actions(action,3)]
            report[name]=dict(omega_ttt_veh_h=item['objective_veh_h'],
                delta_from_hold=item['objective_veh_h']-items[0]['objective_veh_h'],
                costs=item['sdmpc_omega_partition'],quantities_at_inherited_caps=q,
                model_physical_feasible=True,commands=commands)
            with gzip.open(D/f'{name}_response.json.gz','wt',encoding='utf-8') as stream:json.dump(item,stream)
            save(name+'_action.json',vars(action))
        state,cfg=captured['state'],captured['cfg']
        from evaluation.controllers.area_runtime import model_inventory
        from evaluation.controllers.control_area_objective import get_ledger
        get_ledger(state).assert_stocks(model_inventory(state,cfg))
        save('assessment.json',dict(cases=report,price_recovery=read(D/'prior_prices.json'),
            lane_port_10483_stock=cfg.network.urban_link_storage_veh['lane_off_10483']-state.urban_link_storage['lane_off_10483'],
            source_state_sec=state.time_sec,initial_ledger_passed=True,derivative_axes=len(coord.axes),
            full_optimizer_recovery_checked=False,native_started=False,
            scope='Production history/initialization reached PFO entry after actual error-hold; three physical predictions only'))
        raise Complete()
    sdmpc_pfo.solve=audit
    sys.argv=[adapter.__file__,'--state-json',str(F/f'state_{AT:06d}.json'),
        '--previous-action-json',str(previous),'--out-action-json',str(D/'unused_action.json'),
        '--out-action-csv',str(D/'unused_action.csv'),
        '--mapping-json',str(ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'),
        '--detector-mapping-json',str(ROOT/'evaluation/real_world_modi_control_ver2_20260907/detector_local_mapping_ver2_20260907.json'),
        '--calibration-json',str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'),
        '--tuning-json',str(CONFIG),'--controller','wu-link']
    save('launch.json',dict(pid=os.getpid(),started_epoch=time.time(),argv=sys.argv))
    started=time.perf_counter()
    try:adapter.main()
    except Complete:pass
    else:raise AssertionError('Expected diagnostic stop before optimization')
    assert all(sha(ROOT/p)==h for p,h in pins.items())
    stats=query_ref[0].stats()
    assert stats['closed'] and not stats['owned_workers_alive'] and stats['failed_batches']==0
    assert stats['scalar_rollouts']==(0 if PREPARE else 3) and stats['tangent_rollouts']==0
    save('completion.json',dict(status='native_commands_and_actuator_prediction_prepared' if PREPARE else 'post_hold_prediction_complete_not_native_qualified',
        wall_sec=time.perf_counter()-started,sources_unchanged=True,query=stats,native_runs=0))
    print(json.dumps(dict(status='complete',wall_sec=time.perf_counter()-started),ensure_ascii=False))


if __name__=='__main__':main()
