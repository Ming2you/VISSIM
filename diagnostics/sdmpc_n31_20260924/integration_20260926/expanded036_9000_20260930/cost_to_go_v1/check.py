"""Bounded terminal-cost integration check on a completed recorded state.

No optimizer, COM, future native observations, or new VISSIM run. One reference
predicts group turnover to construct an explicitly provisional diagonal P.
All candidates use this same P, including the all-green ramp candidates.
"""
import copy
import ctypes
import hashlib
import json
import math
from pathlib import Path
import sys
import time

from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
from evaluation.controllers import runtime_setup, obs150_contract as oc
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers import physical_ramp_branches as branches, sdmpc_terminal as terminal
from evaluation.controllers import sdmpc_sequence as sequence
from evaluation.controllers.sdmpc import omega_costs
from evaluation.controllers.control_area_objective import get_ledger
from evaluation.controllers.sdmpc_tangent_worker import state_error
from src.models.state import ControlAction
from src.controllers import rollout_endpoint as endpoint

HERE = Path(__file__).resolve().parent
def load(path): return json.loads(path.read_bytes())
def save(name, value):
    (HERE/name).write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    kernel = ctypes.windll.kernel32
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x4000)
    folder = Path('D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
    tuning = probe.HERE/'baseline_reproduction_20260929/cellwise_calibration/coupled_expanded_joint/candidate_config.json'
    prior = probe.HERE/'closedloop_recorded3600_budget_check_selected_meter_e036_10681_r2'
    paths = [tuning, folder/'state_003600.json', folder/'action_003600.json',
             Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')]
    pins = {str(p): sha(p) for p in paths}
    payload = {}
    configure, forecast_fn, write = runtime_setup.configure_runtime, adapter.demand_from_state, oc.write_derived
    def capture(*args, **kwargs):
        result = configure(*args, **kwargs)
        payload.update(state=result[0], cfg=args[1])
        return result
    def forecast(*args, **kwargs):
        result = forecast_fn(*args, **kwargs); payload['forecast'] = result
        return result
    def verify_existing(raw, derived):
        obs = raw[oc.RAW_STATE_KEY]
        path = oc.resolve(obs, oc.derived_path(obs['sim_sec']))
        assert path.read_bytes() == oc.derived_bytes(derived)
        return path
    runtime_setup.configure_runtime, adapter.demand_from_state, oc.write_derived = capture, forecast, verify_existing
    try:
        sys.argv = [str(Path(probe.__file__)), '--closedloop-recorded', '--at=3600',
            '--initialize-only', '--warm-head-history', '--replay-vsl-history',
            '--recording-dir='+str(folder), '--tuning-json='+str(tuning), '--probe-label=terminal_v1']
        probe.main()
    finally:
        runtime_setup.configure_runtime, adapter.demand_from_state, oc.write_derived = configure, forecast_fn, write
    state, cfg = payload['state'], payload['cfg']
    assert state.time_sec == 3600 and cfg.mpc.horizon_steps == 3
    saved = load(prior/'selected.json')
    reference = sequence.first_action(adapter.control_from_json(folder/'action_003600.json', cfg, ControlAction))
    commands = []
    for row in saved['commands']:
        c = branches.candidate_from_greens(reference, reference, cfg, row['meters'])
        assert c.green_times == row['green_times'] and c.offsets == row['offsets'] and c.vsl == row['vsl']
        commands.append(c)
    anchor = sequence.pack(commands)
    def predict(action):
        start = time.perf_counter()
        with sequence.prediction_scope(action, cfg, state.time_sec, 3) as visits:
            point = endpoint.evaluate_price_point(state, action, payload['forecast'][:3], (),
                endpoint.ObjectiveSpec(cfg, depth_override=3, box_walk=False, score_mode='raw'), capture_response=True)
        assert visits == [0, 1, 2] and not point.aborted
        return point, time.perf_counter()-start
    baseline, wall = predict(anchor)
    assert abs(baseline.ttt-saved['execution']['ttt_omega_veh_h']) < 1e-7
    groups = terminal.group_owners(cfg)
    flows = dict.fromkeys(groups, 0.)
    for row in baseline.control_area_response['transfers']:
        if row['source'] is None or row['source'].startswith('external:'): continue
        g = terminal.group_for_stock(row['source'], cfg)
        dest = (terminal.group_for_stock(row['target'], cfg) if row['target'] is not None else None)
        if dest != g: flows[g] += row['vehicles']
    rates = {g: q/(450/3600) for g, q in flows.items()}
    spec = dict(schema=terminal.SCHEMA,
        p_diag_h_per_veh={g: 1/(2*q) if q > 0 else 0. for g, q in rates.items()},
        design='Provisional independent fluid-drain approximation P_g=1/(2*q_ref_g). '+
          'q_ref is total physical group departure rate in the fixed 3600s held-command 450s model forecast; '+
          'not measured capacity, not future native input, not a closed-loop stability design. '+
          'Zero-turnover groups have explicit zero P and are unqualified. Shared downstream travel and speed omitted.')
    tuning_with_terminal = load(tuning)
    tuning_with_terminal['adapter']['sdmpc_terminal_cost'] = spec
    save('candidate_config.json', tuning_with_terminal)
    save('design.json', dict(specification=spec, reference_rates_veh_h=rates,
        zero_turnover_groups=[g for g,q in rates.items() if q == 0],
        baseline_ttt=baseline.ttt, baseline_wall_sec=wall, baseline_matches_saved=True, pins=pins))
    terminal.configure(tuning_with_terminal, cfg)
    repeated, wall = predict(anchor)
    assert repeated.ttt == baseline.ttt
    assert repeated.control_area_response == baseline.control_area_response
    assert state_error(baseline.states, repeated.states) == 0
    candidates = {'held': anchor}
    controls, previous = [], reference
    for row in load(prior/'progressive.json')['commands']:
        c = branches.candidate_from_greens(previous, previous, cfg, row['meters'])
        controls.append(c); previous = c
    candidates['rm10681_8_6_4'] = sequence.pack(controls)
    for speed in (80., 100.):
        changed = [c.copy() for c in commands]
        for c in changed:
            for cell, head in enumerate(cfg.network.freeway_vsl_zone_head_of_cell['FW_E']):
                if head == 13: c.vsl['FW_E__seg'+str(cell)] = speed
            c.vsl['FW_E'] = speed
            assert speed in cfg.freeway_follower.vsl_set and abs(speed-reference.vsl['FW_E__seg13']) <= 10
            assert c.vsl['FW_E__seg0'] == c.vsl['FW_W__seg0'] == 110
        candidates['vsl'+str(int(speed))] = sequence.pack(changed)
    results = {}
    for name, action in candidates.items():
        point, seconds = (repeated, wall) if name == 'held' else predict(action)
        local, partition = omega_costs(point, cfg)
        terminal.validate_score(point.control_area, point.objective, cfg)
        ramps = {}
        for ramp in cfg.network.ramps:
            flow = point.control_area['predicted_ramp_merge']['rate_veh_h_by_ramp'][ramp]*450/3600
            arrivals = sum(r['vehicles'] for r in point.control_area_response['transfers'] if r['target'] == 'ramp:'+ramp)
            end = point.states[-1].ramp_queue[ramp]
            residual = state.ramp_queue[ramp]+arrivals-flow-end
            assert abs(residual) < 1e-7
            ramps[ramp] = dict(merge=flow, arrivals=arrivals, end=end, mass_residual=residual)
        terminal_cost = point.control_area['additional_cost_veh_h']
        row = dict(near_ttt_veh_h=point.ttt, terminal_cost_veh_h=terminal_cost,
            selection_score_veh_h=point.objective, terminal=point.control_area['terminal_cost'],
            partition=partition, ramps=ramps, elapsed_sec=seconds,
            max_resource_exceedance=max(r['exceedance_veh'] for r in point.control_area_response['resource_allocations']),
            constraints_coverage=point.control_area_response['model_constraint_coverage'])
        results[name] = row; save(name+'.json', row)
        print(json.dumps(dict(candidate=name, ttt=point.ttt, terminal=terminal_cost, score=point.objective)), flush=True)
    for path, digest in pins.items(): assert sha(Path(path)) == digest
    save('summary.json', dict(results=results, baseline_on_off_trajectory_exact=True,
        native_runs=0, physical_rollouts=5, optimizer_iterations=0, specification_sha256=terminal.specification_token(spec),
        rankings={str(w): sorted(results, key=lambda k: results[k]['near_ttt_veh_h']+w*results[k]['terminal_cost_veh_h']) for w in (0., .5, 1.)},
        scope='Fixed candidate response and scoring only; P is provisional, not a qualified future-cost estimator or native improvement.'))


def stress_check():
    """Five bounded450s forecasts, frozen P; no fitting or native execution."""
    kernel=ctypes.windll.kernel32
    kernel.GetCurrentProcess.restype=ctypes.c_void_p
    kernel.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    from evaluation.controllers import omega_distance as distance
    distance_mode='--distance-reward' in sys.argv
    tag=next((s.split('=',1)[1] for s in sys.argv if s.startswith('--stress-tag=')),'v1')
    out=(HERE.parent/'objective_pair'/('distance_stress_'+tag) if distance_mode else HERE/('stress_'+tag))
    if out.exists():raise FileExistsError(out)
    out.mkdir()
    tuning=HERE/'candidate_config.json'
    original=probe.HERE/'baseline_reproduction_20260929/cellwise_calibration/coupled_expanded_joint/candidate_config.json'
    configured=load(tuning); spec=configured['adapter']['sdmpc_terminal_cost']
    plain=copy.deepcopy(configured);del plain['adapter']['sdmpc_terminal_cost']
    assert plain==load(original)
    if distance_mode:
        spec=dict(schema=distance.REWARD_SCHEMA,weight_h_per_km=1/110,initial_transport=distance.COMMON_INITIAL)
        configured=copy.deepcopy(plain);configured['adapter']['sdmpc_distance_reward']=spec
    configure_objective=distance.configure_reward if distance_mode else terminal.configure
    token=distance.reward_token(spec) if distance_mode else terminal.specification_token(spec)
    pins={str(p):sha(p) for p in (tuning,original,HERE/'design.json',
        Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP'),Path(terminal.__file__))}
    if distance_mode:pins[str(Path(distance.__file__))]=sha(Path(distance.__file__))
    def write(name,value):
        p=out/(name+'.json');assert not p.exists()
        p.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf8')
    def initialize(folder,sec,label,extra=()):
        if distance_mode:label='distance_'+label
        payload={};configure,forecast_fn,writer=runtime_setup.configure_runtime,adapter.demand_from_state,oc.write_derived
        def capture(*args,**kwargs):
            result=configure(*args,**kwargs);payload.update(state=result[0],cfg=args[1]);return result
        def forecast(*args,**kwargs):
            result=forecast_fn(*args,**kwargs);payload['forecast']=result;return result
        def read_only(raw,derived):
            obs=raw[oc.RAW_STATE_KEY];p=oc.resolve(obs,oc.derived_path(obs['sim_sec']))
            assert p.is_file() and p.read_bytes()==oc.derived_bytes(derived),p
            pins[str(p)]=sha(p);return p
        runtime_setup.configure_runtime,adapter.demand_from_state,oc.write_derived=capture,forecast,read_only
        try:
            sys.argv=[str(Path(probe.__file__)),'--closedloop-recorded','--at='+str(sec),
                '--initialize-only','--warm-head-history','--replay-vsl-history',
                '--recording-dir='+str(folder),'--tuning-json='+str(original),
                '--probe-label='+label,*extra]
            probe.main()
        finally:
            runtime_setup.configure_runtime,adapter.demand_from_state,oc.write_derived=configure,forecast_fn,writer
        for p in (folder/f'state_{sec:06d}.json',folder/f'action_{sec-150:06d}.json'):pins[str(p)]=sha(p)
        payload['reference']=sequence.first_action(adapter.control_from_json(folder/f'action_{sec-150:06d}.json',payload['cfg'],ControlAction))
        return payload
    def evaluate(payload,action):
        state,cfg=payload['state'],payload['cfg'];start=time.perf_counter()
        with sequence.prediction_scope(action,cfg,state.time_sec,3) as visits:
            point=endpoint.evaluate_price_point(state,action,payload['forecast'][:3],(),
                endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
        assert visits==[0,1,2] and not point.aborted
        return point,time.perf_counter()-start
    def record(name,payload,point,seconds):
        cfg,state=payload['cfg'],payload['state']
        _,partition=omega_costs(point,cfg)
        terminal.validate_score(point.control_area,point.objective,cfg)
        ramps={}
        for ramp in cfg.network.ramps:
            merged=point.control_area['predicted_ramp_merge']['rate_veh_h_by_ramp'][ramp]*450/3600
            arrivals=sum(r['vehicles'] for r in point.control_area_response['transfers'] if r['target']=='ramp:'+ramp)
            end=point.states[-1].ramp_queue[ramp]
            residual=state.ramp_queue[ramp]+arrivals-merged-end
            assert abs(residual)<1e-7
            ramps[ramp]=dict(arrivals=arrivals,merged=merged,terminal_stock=end,mass_residual=residual)
        value=dict(ttt_omega_veh_h=point.ttt,
            selection_score_veh_h=point.objective,
            ramps=ramps,partition=partition,seconds=seconds,
            constraints_coverage=point.control_area_response['model_constraint_coverage'],
            initial_freeway_speed={k:list(v) for k,v in state.freeway_speed.items()})
        if distance_mode:
            value.update(distance_cost_veh_h=point.control_area['additional_cost_veh_h'],
                shifted_tvd_veh_km=point.control_area['distance_reward']['shifted_tvd_veh_km'],
                distance_reward=point.control_area['distance_reward'])
        else:value.update(terminal_cost_veh_h=point.control_area['additional_cost_veh_h'],terminal=point.control_area['terminal_cost'])
        write(name,value);print(json.dumps(dict(case=name,ttt=point.ttt,additional=point.control_area['additional_cost_veh_h'],score=point.objective)),flush=True)
        return value
    folder=Path('D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47')
    receipt=probe.HERE/'native_rm_observation2700_writerfix_v3/analysis/summary.json'
    prior=probe.HERE/'closedloop_recorded2700_lever450_trace10484_expanded_joint_s47_v1/summary.json'
    pins[str(receipt)]=sha(receipt);pins[str(prior)]=sha(prior)
    reuse=next((Path(s.split('=',1)[1]) for s in sys.argv if s.startswith('--reuse-strong=')),None)
    if distance_mode and reuse is not None:raise ValueError('Terminal result cannot substitute for distance verification')
    if reuse is not None:
        results={}
        for name,row in load(prior)['results'].items():
            path=reuse/('strong47_'+name+'.json'); pins[str(path)]=sha(path)
            value=load(path)
            assert abs(value['ttt_omega_veh_h']-row['ttt_omega_veh_h'])<1e-7
            assert abs(value['selection_score_veh_h']-value['ttt_omega_veh_h']-value['terminal_cost_veh_h'])<1e-7
            results['strong47_'+name]=value
            write('strong47_'+name,value)
    else:
        results=strong_cases(folder,receipt,prior,tag,initialize,configured,write,evaluate,record,configure_objective)
    folder=Path('D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
    payload=initialize(folder,7500,'ctg_cooldown29_'+tag)
    cfg=payload['cfg'];held=sequence.pack([payload['reference'].copy() for _ in range(3)])
    baseline,seconds=evaluate(payload,held)
    configure_objective(configured,cfg)
    point,seconds=evaluate(payload,held)
    assert point.ttt==baseline.ttt and point.control_area_response==baseline.control_area_response
    if distance_mode:
        physical_states=copy.deepcopy(point.states)
        for s in physical_states:delattr(s,'_omega_travel_reservations')
        assert state_error(physical_states,baseline.states)==0
    else:assert state_error(point.states,baseline.states)==0
    results['cooldown29_held']=record('cooldown29_held',payload,point,seconds)
    controls=[];previous=payload['reference']
    for _ in range(3):
        greens={r:float(payload['reference'].diagnostics['rw_meter_green_'+r]) for r in cfg.network.ramps}
        greens['RM_C10681']=max(0.,greens['RM_C10681']-2.)
        c=branches.candidate_from_greens(payload['reference'],previous,cfg,greens)
        for cell,head in enumerate(cfg.network.freeway_vsl_zone_head_of_cell['FW_E']):
            if head==13:c.vsl['FW_E__seg'+str(cell)]=100.
        c.vsl['FW_E']=100.
        assert c.vsl['FW_E__seg0']==c.vsl['FW_W__seg0']==110.
        controls.append(c);previous=c
    point,seconds=evaluate(payload,sequence.pack(controls))
    results['cooldown29_joint_restriction']=record('cooldown29_joint_restriction',payload,point,seconds)
    for p,h in pins.items():assert sha(Path(p))==h,p
    deltas={}
    for key,base in [('strong47_release_actual','strong47_held_actual'),('cooldown29_joint_restriction','cooldown29_held')]:
        fields=('ttt_omega_veh_h','distance_cost_veh_h','shifted_tvd_veh_km','selection_score_veh_h') if distance_mode else ('ttt_omega_veh_h','terminal_cost_veh_h','selection_score_veh_h')
        deltas[key]={k:results[key][k]-results[base][k] for k in fields}
    write('summary',dict(results=results,deltas=deltas,pins=pins,specification_sha256=token,
        objective_mode='distance' if distance_mode else 'terminal',weight_diagnostic_only=distance_mode,
        frozen_P=True,fit_evaluations=0,fixed_command_rollouts=3 if reuse else 5,reused_strong_cases=2 if reuse else 0,
        optimizer_iterations=0,new_native_runs=0,
        cooldown_held_on_off_all_states_flows_ttt_exact=True,
        qualification='Bounded physical response/scoring check; not a terminal-value accuracy or closed-loop gain guarantee.'))
    print(json.dumps(dict(deltas=deltas,frozen_P=True)),flush=True)


def strong_cases(folder,receipt,prior,tag,initialize,configured,write,evaluate,record,configure_objective=terminal.configure):
    payload=initialize(folder,2700,'ctg_strong47_'+tag,['--fixed-replay-summary='+str(receipt)])
    cfg=payload['cfg'];configure_objective(configured,cfg)
    # Match the historical probe: fixed replay stores a shared 110 km/h
    # command; expand it with the same installed logical-head mapping.
    from evaluation.controllers.area_follower_objective import expand_shared_vsl_action
    payload['reference'],expansion=expand_shared_vsl_action(payload['reference'],cfg,
        segment_vsl_func=adapter.repo_imports(probe.ROOT/'vendor/NumSim-mine')[-1])
    write('historical_vsl_expansion',expansion)
    results={}
    for name,row in load(prior)['results'].items():
        controls=[];previous=payload['reference']
        for command in row['commands']:
            c=branches.candidate_from_greens(payload['reference'],previous,cfg,command['meters'])
            for field in ('green_times','offsets','vsl'):
                actual=getattr(c,field);expected=command[field]
                mismatch={k:[actual.get(k),expected.get(k)] for k in actual.keys()|expected.keys() if actual.get(k)!=expected.get(k)}
                if mismatch:print(json.dumps(dict(field=field,mismatch=mismatch)),flush=True)
            assert c.green_times==command['green_times'] and c.offsets==command['offsets'] and c.vsl==command['vsl']
            controls.append(c);previous=c
        point,seconds=evaluate(payload,sequence.pack(controls))
        assert abs(point.ttt-row['ttt_omega_veh_h'])<1e-7
        assert point.control_area['cost_by_stock']==row['cost_by_stock'] if 'cost_by_stock' in point.control_area else True
        results['strong47_'+name]=record('strong47_'+name,payload,point,seconds)
    return results


if __name__ == '__main__':
    stress_check() if '--stress-check' in sys.argv else main()
