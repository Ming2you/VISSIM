"""Two exact actuator-model predictions of the completed selected and held plan."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import hashlib, importlib.util, json, sys, time
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=Path('D:/VISSIM_runtime/20261012_adopted355_vsl_three/frozen/sdmpc31_ca181e84_202610121132')
DEC=Path('E:/VISSIM_runs/20261012_adopted355_optimized_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
TUNING=ROOT/'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native413_adopted355/optimized_config.json'
OUT=HERE/'exact_selected3300_v2'
SELECTED=HERE/'full_selection3300/unused.json'
read=lambda p:json.loads(Path(p).read_bytes())
def main():
    assert not OUT.exists() and read(HERE/'full_selection3300/completion.json')['status']=='complete'
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    os.environ['NUMSIM_REPO_ROOT']=str(ROOT/'vendor/NumSim-mine')
    verify=ROOT/'diagnostics/repin_v3c3_review_20261001/urban260/verify.py'
    sys.argv=[str(verify),'--at','3300','--out',str(OUT),'--tuning',str(TUNING),'--decisions',str(DEC),'--full-selection']
    spec=importlib.util.spec_from_file_location('exact_selected_verifier',verify)
    verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
    from evaluation.controllers import physical_ramp_branches as ramps,sdmpc_pfo,sdmpc_sequence as seq
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,area_follower_objective as shared
    from evaluation.controllers import area_leader_objective as constraints,signal_actuation_contract as signals
    from src.models.state import ControlAction
    captured={};bounds=ramps.configure_operating_bounds;forecast=adapter.demand_from_state
    def operating_bounds(state,cfg,reference):
        # solve() owns a deep copy of follower/state/config. Capture that context,
        # after initialization, rather than the earlier adapter configuration.
        result=bounds(state,cfg,reference);captured.update(state=state,cfg=cfg);return result
    def demand(*a,**kw):
        result=forecast(*a,**kw);captured['forecast']=result;return result
    ramps.configure_operating_bounds=operating_bounds;adapter.demand_from_state=demand
    def run(reference,coord,policy,options,evaluate,derivative,quantities,check_budget,emit):
        state,cfg=captured['state'],captured['cfg']
        selected=adapter.control_from_json(SELECTED,cfg,ControlAction)
        seed=reference.copy();seed.N_P_star=selected.N_P_star;seed.N_UF_star=selected.N_UF_star
        follower=adapter._PHASE_VECTOR_FOLLOWER['ref'];assert follower.cfg is cfg
        rows=[]
        for name,action in [('held',seed),('selected',selected)]:
            proof=coord.validate(action)
            for block in seq.actions(action,3):signals.validate_writer(block,cfg,adapter.load_signal_group_actuation_plan(),'experiment')
            began=time.perf_counter()
            batch=shared.evaluate_shared_owner_batch(follower,state,seed,captured['forecast'],[action],horizon_steps=3)
            assert batch['endpoint_calls']==1 and batch['requested']==1
            item=batch['results'][0]
            quantity=constraints.shared_quantity_constraints(follower,action,item['quantities'],start_sec=3300,horizon_steps=3,
                np_mode='cap',target_np_veh=selected.N_P_star,np_tolerance_veh=options['shared_tolerance'],
                nuf_mode='cap',target_nuf_veh_h=selected.N_UF_star,nuf_tolerance_veh_h=options['shared_tolerance'])
            row=dict(name=name,objective_veh_h=item['objective_veh_h'],seconds=time.perf_counter()-began,
                physical_feasible=sdmpc_pfo.model_feasible(item,options['shared_tolerance']),
                quantity_constraints=quantity,control_sequence=proof,resource_summary=item['resource_summary'],
                owner_costs=item['sdmpc_omega_partition']['costs'])
            rows.append(row)
            (OUT/'progress.json').write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n',encoding='utf8')
            print(name,row['objective_veh_h'],row['physical_feasible'],quantity['feasible'],flush=True)
        report=dict(status='complete',rows=rows,native_runs=0,full_optimizer_runs=0,predictions=2,
            selected_minus_held_veh_h=rows[1]['objective_veh_h']-rows[0]['objective_veh_h'],
            selected_sha256=hashlib.sha256(SELECTED.read_bytes()).hexdigest(),
            scope='Exact discrete actuator-model validation under unchanged selected caps; not native performance')
        (OUT/'summary.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf8')
        raise verifier.Done()
    sdmpc_pfo.solve=run
    try:
        verifier.main()
        assert (OUT/'summary.json').exists()
    except BaseException as exc:
        import traceback
        if OUT.exists():(OUT/'failure_preserved.json').write_text(json.dumps(dict(error=repr(exc),traceback=traceback.format_exc()),indent=2)+'\n',encoding='utf8')
        raise
if __name__=='__main__':main()
