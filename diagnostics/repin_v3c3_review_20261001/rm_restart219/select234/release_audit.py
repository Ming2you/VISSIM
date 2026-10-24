"""Three saved-state scalar checks: selected command and two legal RM releases."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import sys
import time

D = Path(__file__).resolve().parent
ROOT = D.parents[3]
I = ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
SELECTED = I/'closedloop_recorded4500_select_rm234_projection_fix'
RESULT = D/'release_v2'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


class Complete(BaseException):
    pass


def save(name, value):
    (RESULT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def main():
    assert not RESULT.exists(), 'Preserve prior attempt'
    RESULT.mkdir()
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    os.environ.update(PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
        NUMSIM_REPO_ROOT=str(ROOT/'vendor/NumSim-mine'), OPENBLAS_NUM_THREADS='1',
        OMP_NUM_THREADS='1', RW_DECISION_FAIL_FAST='1', RW_MAINLINE_SG_ONLY='1',
        RW_OFFSET_WRITER='experiment', RW_RAMP_AMBER_SEC='0')
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.GetCurrentProcess.restype = ctypes.c_void_p
    k.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    assert k.SetPriorityClass(k.GetCurrentProcess(), 0x4000)
    prior = json.loads((D/'protocol.json').read_bytes())
    assert all(sha(ROOT/p)==h for p,h in prior['source_sha256'].items())
    selected_path = SELECTED/'unused_action.json'
    joint_path = SELECTED/'unused_action.joint.json'
    saved = json.loads(joint_path.read_bytes())['selection']
    pins = {str(p):sha(p) for p in (selected_path,joint_path,Path(__file__))}
    save('release_protocol.json', dict(start_sec=4500, seed=29, horizon_sec=450,
        maximum_scalar_predictions=3, optimizer_calls=0, native_runs=0, fzp_reads=0,
        actions=['selected','RM_C10480:release','RM_C10681:release'],
        quantities='Saved selected NP/NUF caps unchanged', coefficients_changed=False,
        reason='Distinguish quantity caps from physical resource rejection after initialization repair',
        source_pins=pins, parent_protocol_sha256=sha(D/'protocol.json')))
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
    from evaluation.controllers import sdmpc, sdmpc_pfo, sdmpc_sequence as sequence
    from evaluation.controllers import area_leader_objective as constraints
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    old_replay = probe.replay_vsl_history
    probe.replay_vsl_history = lambda *a,**kw: old_replay(*a,**kw,allow_missing_current_online=True)

    def audit(reference, coord, policy, options, evaluate, derivative, quantities, check_budget, emit):
        from src.models.state import ControlAction
        cfg = coord.cfg
        selected = adapter.control_from_json(selected_path, cfg, ControlAction)
        coord.validate(selected)
        neighbors = dict(sdmpc.meter_neighbors(coord, selected))
        actions = {'selected':selected, **{name:neighbors[name] for name in ('RM_C10480:release','RM_C10681:release')}}
        follower = adapter._PHASE_VECTOR_FOLLOWER['ref']
        items = evaluate(list(actions.values()), derivatives=False)
        assert len(items)==3
        rows = {}
        for (name,action),item in zip(actions.items(),items):
            q = constraints.shared_quantity_constraints(follower,action,item['quantities'],
                start_sec=4500,horizon_steps=3,np_mode='cap',target_np_veh=selected.N_P_star,
                np_tolerance_veh=saved['final_constraints']['np']['tolerance'],
                nuf_mode='cap',target_nuf_veh_h=selected.N_UF_star,
                nuf_tolerance_veh_h=saved['final_constraints']['nuf']['tolerance'])
            rows[name] = dict(objective_veh_h=item['objective_veh_h'],
                delta_from_selected_veh_h=item['objective_veh_h']-saved['selected_objective'],
                constraints=q, physical_model_feasible=sdmpc_pfo.model_feasible(item,options['shared_tolerance']),
                coverage=item['model_constraint_coverage'],resource_summary=item['resource_summary'],
                commands=[{r:a.diagnostics['rw_meter_green_'+r] for r in cfg.network.ramps}
                          for a in sequence.actions(action,3)],
                omega_partition=item['sdmpc_omega_partition'])
        error=rows['selected']['objective_veh_h']-saved['selected_objective']
        save('release_assessment.json',dict(results=rows,selected_reproduction_error_veh_h=error,
            predictions=3,optimizer_calls=0,native_runs=0,gain_qualified=False,
            scope='Continuous control model only; fixed selected city/VSL, caps, current state and forecast'))
        assert abs(error)<1e-7, error
        raise Complete()

    sdmpc_pfo.solve = audit
    sys.argv = [probe.__file__, *[x.replace('rm234_projection_fix','rm234_release_audit_v2') for x in prior['argv']]]
    started=time.perf_counter()
    try:
        probe.main()
    except Complete:
        unchanged=all(sha(ROOT/p)==h for p,h in prior['source_sha256'].items()) and all(sha(Path(p))==h for p,h in pins.items())
        assert unchanged
        save('release_completion.json',dict(status='completed_diagnostic_only',wall_sec=time.perf_counter()-started,
            predictions=3,optimizer_calls=0,native_runs=0,source_unchanged=True))
    else:
        raise AssertionError('Diagnostic PFO entry was not reached')


if __name__=='__main__':
    main()
