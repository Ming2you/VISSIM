"""One canonical continuous prediction / derivative column; no optimizer."""
import copy
import ctypes
import json
import inspect
import numpy as np
import pickle
from pathlib import Path
import sys

from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
from evaluation.controllers import obs150_contract as oc, sdmpc_terminal as terminal
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers import sdmpc_sequence as sequence
from evaluation.controllers.sdmpc_tangent import _evaluate_single
from src.models.state import ControlAction

HERE = Path(__file__).resolve().parent


def main():
    component_mode='--selected-components' in sys.argv
    distance_mode='--distance-reward' in sys.argv
    tag=next((v.split('=',1)[1] for v in sys.argv if v.startswith('--tag=')),'v1')
    result_file=(HERE.parent/'objective_pair'/('distance_worker_'+tag+'.json') if distance_mode else HERE/'worker_summary.json')
    if component_mode:result_file=HERE.parent/'objective_pair'/('distance_component_surrogate_'+tag+'.json')
    if result_file.exists():raise FileExistsError(result_file)
    k = ctypes.windll.kernel32
    k.GetCurrentProcess.restype = ctypes.c_void_p
    k.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    assert k.SetPriorityClass(k.GetCurrentProcess(), 0x4000)
    original = probe.probe_selected_meter
    writer = oc.write_derived
    def read_only(raw, derived):
        obs = raw[oc.RAW_STATE_KEY]; p = oc.resolve(obs, oc.derived_path(obs['sim_sec']))
        assert p.read_bytes() == oc.derived_bytes(derived)
        return p
    def check(captured, reference, coord, options, evaluate, selected_path, output, **kwargs):
        if component_mode:
            component_query(captured,reference,coord,options,evaluate,selected_path,result_file)
            return
        query = inspect.getclosurevars(evaluate).nonlocals['query']
        request = pickle.loads(query.template)
        cfg = request['owned'][0].cfg
        if distance_mode:
            from evaluation.controllers import omega_distance as distance
            reward=dict(schema=distance.REWARD_SCHEMA,weight_h_per_km=1/110,initial_transport=distance.COMMON_INITIAL)
            distance.configure_reward({'adapter':{'sdmpc_distance_reward':reward}},cfg)
            token=distance.reward_token(reward)
            cfg.network.sdmpc_options['distance_reward_sha256']=token
        else:
            source = json.loads((HERE/'candidate_config.json').read_bytes())
            terminal.configure(source, cfg)
            token=terminal.specification_token(cfg.network.sdmpc_terminal_cost)
            cfg.network.sdmpc_options['terminal_cost_sha256'] = token
        action = adapter.control_from_json(selected_path, cfg, ControlAction)
        if sequence.KEY not in action.diagnostics: action = sequence.pack(sequence.actions(action, 3))
        coord.validate(action)
        request['action'] = action
        request['reverse_worker_limit'] = 1
        axis = next(j for j,a in enumerate(coord.axes) if a['kind']=='meter' and a['key']=='RM_C10681' and a['block']==0)
        # Reverse mode uses one complete tape, as in the actual controller.
        # Compare an independent scalar request, not a claim of optimization.
        request['surrogate_evaluation'] = 'scalar'
        scalar = _evaluate_single(request)
        request['surrogate_evaluation'] = 'ad'
        receipt = _evaluate_single(request)
        tolerance = cfg.network.sdmpc_options['tangent_primal_abs_tolerance']
        errors = {key: float(np.max(np.abs(np.asarray(scalar[key])-np.asarray(receipt[key])))) for key in ('costs','resources')}
        scalar_state = scalar['surrogate_prediction']['central_physical']['values']
        ad_state = receipt['surrogate_prediction']['central_physical']['values']
        errors['central_state'] = float(np.max(np.abs(np.asarray(scalar_state)-np.asarray(ad_state))))
        assert max(errors.values()) <= tolerance and len(receipt['ad_axes']) == len(coord.axes)
        assert any('sdmpc_terminal.py' in name for name in receipt['transformed_source_sha256'])
        if distance_mode:assert any('omega_distance.py' in name for name in receipt['transformed_source_sha256'])
        result = dict(axis=coord.axes[axis], costs_order=request['costs_order'],
            costs=receipt['costs'], cost_jacobian=receipt['cost_jacobian'], resources=receipt['resources'],
            resource_jacobian=receipt['resource_jacobian'],
            checked_primal_errors=errors, central_state_values_checked=len(scalar_state),
            complete_primal_state_match=False, derivative_axes=len(receipt['ad_axes']),
            scalar_rollouts=scalar['scalar_rollouts'], tangent_rollouts=receipt['tangent_rollouts'],
            scalar_seconds=scalar['wall_sec_including_spawn'], ad_seconds=receipt['wall_sec_including_spawn'],
            prediction=scalar['surrogate_prediction'],
            transformed_source_sha256=receipt['transformed_source_sha256'],
            reward_mode='distance' if distance_mode else 'terminal',specification_sha256=token,
            new_optimization=False, native_runs=0)
        result_file.write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps(dict(worker_pass=True, objective=sum(receipt['costs']), errors=errors)), flush=True)
    probe.probe_selected_meter = check
    oc.write_derived = read_only
    try:
        tuning = probe.HERE/'baseline_reproduction_20260929/cellwise_calibration/coupled_expanded_joint/candidate_config.json'
        sys.argv = [str(Path(probe.__file__)), '--closedloop-recorded', '--at=3600',
            '--selected-meter-check', '--selected-meter-ramp=RM_C10681', '--recorded-selection-check',
            '--warm-head-history', '--replay-vsl-history',
            '--recording-dir=D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29',
            '--tuning-json='+str(tuning), '--probe-label='+('distance_worker_'+tag if distance_mode else 'terminal_worker_v2')]
        if component_mode:
            sys.argv=[str(Path(probe.__file__)),'--closedloop-recorded','--at=2700',
                '--selected-local-neighbors',
                '--warm-head-history','--replay-vsl-history',
                '--recording-dir=D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47',
                '--fixed-replay-summary='+str(probe.HERE/'native_rm_observation2700_writerfix_v3/analysis/summary.json'),
                '--selection-reference='+str(probe.HERE/'closedloop_recorded2700_select_distance_s47_v1'),
                '--selection-execution-reference='+str(probe.HERE/'closedloop_recorded2700_select_check_distance_s47_v1'),
                '--tuning-json='+str(HERE.parent/'objective_pair/distance_diagnostic_config.json'),
                '--probe-label=distance_cmp_surrogate_'+tag]
        probe.main()
    finally:
        probe.probe_selected_meter, oc.write_derived = original, writer


def component_query(captured,reference,coord,options,evaluate,selected_path,result_file):
    """Two scalar requests with the actual controller query and fixed caps."""
    import hashlib
    from evaluation.controllers import physical_ramp_branches as branches
    from evaluation.controllers import area_leader_objective as constraints,sdmpc_pfo
    folder=HERE.parent/'objective_pair'
    saved=json.loads(selected_path.with_suffix('.joint.json').read_bytes())['selection']
    cfg,state=captured['cfg'],captured['state']
    action=adapter.control_from_json(selected_path,cfg,ControlAction)
    coord.validate(action)
    previous=sequence.first_action(reference);commands=[]
    for full in sequence.actions(action,3):
        c=full.copy();c.vsl=dict(reference.vsl)
        greens={r:reference.diagnostics['rw_meter_green_'+r] for r in cfg.network.ramps}
        c=branches.candidate_from_greens(c,previous,cfg,greens)
        assert c.green_times==full.green_times and c.offsets==full.offsets
        commands.append(c);previous=c
    city=sequence.pack(commands);coord.validate(city)
    physical=json.loads((folder/'distance_components_v1_city_only.json').read_bytes())
    for c,row in zip(commands,physical['commands']):
        assert c.vsl==row['vsl'] and c.green_times==row['green_times'] and c.offsets==row['offsets']
        assert row['meters']=={r:c.diagnostics['rw_meter_green_'+r] for r in cfg.network.ramps}
    candidates={'selected_all':action,'selected_city_only':city}
    items=evaluate(list(candidates.values()),derivatives=False)
    follower=adapter._PHASE_VECTOR_FOLLOWER['ref'];results={}
    for (name,command),item in zip(candidates.items(),items):
        q=constraints.shared_quantity_constraints(follower,command,item['quantities'],
            start_sec=state.time_sec,horizon_steps=3,np_mode='cap',
            target_np_veh=saved['final_constraints']['np']['target'],
            np_tolerance_veh=saved['final_constraints']['np']['tolerance'],nuf_mode='cap',
            target_nuf_veh_h=saved['final_constraints']['nuf']['target'],
            nuf_tolerance_veh_h=saved['final_constraints']['nuf']['tolerance'])
        results[name]=dict(objective_veh_h=item['objective_veh_h'],
            ttt_omega_veh_h=item['control_area']['ttt_veh_h'],
            shifted_tvd_veh_km=item['control_area']['distance_reward']['shifted_tvd_veh_km'],
            quantities=q,conditional_model_feasible=sdmpc_pfo.model_feasible(item,options['shared_tolerance']),
            owner_partition=item['sdmpc_omega_partition'])
    assert abs(results['selected_all']['objective_veh_h']-saved['selected_objective'])<1e-7
    assert abs(results['selected_all']['ttt_omega_veh_h']-saved['omega_partition']['near_ttt_veh_h'])<1e-7
    pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        (selected_path,selected_path.with_suffix('.joint.json'),folder/'distance_components_v1_city_only.json',Path(__file__))}
    result=dict(results=results,pins=pins,original_selected_scalar_score_exact=True,
        new_surrogate_forecasts=2,new_native_runs=0,optimizer_iterations=0,new_physical_forecasts=0,
        native_gain_claimed=False,weight_diagnostic_only=True)
    result_file.write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf8')
    print(json.dumps({k:{f:v[f] for f in ('objective_veh_h','ttt_omega_veh_h','conditional_model_feasible')} for k,v in results.items()}),flush=True)


if __name__ == '__main__': main()
