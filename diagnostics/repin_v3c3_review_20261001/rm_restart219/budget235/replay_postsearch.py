"""Replay only the repaired finite stage on the two already solved budgets."""
import copy
import ctypes
import hashlib
import json
import os
from pathlib import Path
import pickle
import sys
import time

D=Path(__file__).resolve().parent
ROOT=D.parents[3]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
SOURCE=I/'closedloop_recorded4500_select_rm235_three_budgets'
OUT=D/'postsearch'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


class Complete(BaseException):pass


def save(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def main():
    assert not OUT.exists(), 'Preserve prior attempt'
    OUT.mkdir()
    old=json.loads((D/'protocol.json').read_bytes())
    pins=dict(old['source_sha256'])
    key='evaluation/controllers/sdmpc.py'
    assert sha(D/'sdmpc_before_budget_audit.py.txt')==pins[key]
    pins[key]=sha(ROOT/key)
    assert all(sha(ROOT/p)==h for p,h in pins.items())
    pins[str(Path(__file__))]=sha(Path(__file__))
    saved=json.loads((SOURCE/'unused_action.joint.json').read_bytes())['selection']
    assert len(saved['candidates'])==3
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
    from evaluation.controllers import sdmpc,sdmpc_pfo,sdmpc_sequence as sequence
    from evaluation.controllers import area_leader_objective as constraints
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    import numpy as np
    replay=probe.replay_vsl_history
    probe.replay_vsl_history=lambda *a,**kw:replay(*a,**kw,allow_missing_current_online=True)

    def audit(reference,coord,policy,options,evaluate,derivative,quantities,check_budget,emit):
        from src.models.state import ControlAction
        follower=adapter._PHASE_VECTOR_FOLLOWER['ref']
        source_action=adapter.control_from_json(SOURCE/'unused_action.json',coord.cfg,ControlAction)
        actions=[];targets=[]
        for row,recovery in zip(saved['candidates'],saved['central_multiplier']):
            if not row['feasible']:continue
            seed=source_action.copy()
            seed.N_P_star,seed.N_UF_star=row['np_cap'],row['nuf_target']
            action=coord.decode(np.array(recovery['selected_point']),seed)
            coord.validate(action)
            actions.append(action);targets.append(row)
        assert len(actions)==2
        items=evaluate(actions,derivatives=False)
        errors=[item['objective_veh_h']-row['objective'] for item,row in zip(items,targets)]
        save('incumbent_reproduction.json',dict(errors_veh_h=errors,targets=targets))
        assert max(abs(e) for e in errors)<1e-7,errors
        incumbents=[(a,item,None) for a,item in zip(actions,items)]
        def quantity(a,item):
            return constraints.shared_quantity_constraints(follower,a,item['quantities'],
                start_sec=4500,horizon_steps=3,np_mode='cap',target_np_veh=a.N_P_star,
                np_tolerance_veh=options['np_tolerance_veh'],nuf_mode='cap',target_nuf_veh_h=a.N_UF_star,
                nuf_tolerance_veh_h=policy['pfo_cap_options']['nuf_tolerance_veh_h'])
        def feasible(a,item):
            return quantity(a,item)['feasible'] and sdmpc_pfo.model_feasible(item,options['shared_tolerance'])
        best,proof=sdmpc.audit_meter_budget_candidates(coord,incumbents[0],incumbents,
            policy['objective_tolerance'],evaluate,feasible)
        action,item,_=best
        validation=coord.validate(action)
        (OUT/'selected_action.pkl').write_bytes(pickle.dumps(action,protocol=5))
        save('selected_action.json',vars(action))
        save('assessment.json',dict(audit=proof,objective=item['objective_veh_h'],
            old_selected_objective=saved['selected_objective'],
            delta_from_old_selection=item['objective_veh_h']-saved['selected_objective'],
            constraints=quantity(action,item),model_physical_feasible=sdmpc_pfo.model_feasible(item,options['shared_tolerance']),
            validation=validation,commands=[{r:a.diagnostics['rw_meter_green_'+r] for r in coord.cfg.network.ramps}
                                          for a in sequence.actions(action,3)],
            omega_partition=item['sdmpc_omega_partition'],incumbent_reproduction_errors=errors,
            query=derivative.__self__.stats(),native_runs=0,optimizer_iterations=0,
            scope='Repaired finite stage on independently solved saved235 budgets; continuous model, not a complete new optimization or native validation'))
        raise Complete()

    sdmpc_pfo.solve=audit
    argv=[x.replace('rm235_three_budgets','rm235_postsearch') for x in old['argv']]
    save('protocol.json',dict(source_sha256=pins,max_incumbent_predictions=2,max_neighbor_predictions=40,
        source_selection=str(SOURCE),optimizer_iterations=0,native_runs=0,fzp_reads=0,fit=0,
        coefficients_changed=False,caps='Existing solved235 fixed caps; none expanded to fit a candidate',argv=argv))
    sys.argv=[probe.__file__,*argv]
    started=time.perf_counter()
    try:probe.main()
    except Complete:
        assert all(sha(ROOT/p)==h for p,h in pins.items())
        save('completion.json',dict(status='finite_stage_replayed_not_native_qualified',wall_sec=time.perf_counter()-started,source_unchanged=True))
    else:raise AssertionError('PFO diagnostic entry not reached')


if __name__=='__main__':main()
