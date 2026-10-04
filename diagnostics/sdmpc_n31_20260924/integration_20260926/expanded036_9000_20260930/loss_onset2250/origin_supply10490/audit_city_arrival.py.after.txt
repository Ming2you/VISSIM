"""Bounded recorded-state forecast instrumentation; no future traffic inputs."""
import ctypes
import gzip
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
I = HERE.parent.parent
U = I.parents[2]
AT = int(sys.argv[1])
assert AT in (2250, 3600)
INIT_ONLY = '--init-only' in sys.argv[2:]
AFTER = '--after' in sys.argv[2:]
PHYSICAL_SPEED = '--physical-speed' in sys.argv[2:]
ALL_RAMPS = '--all-ramp-ledger' in sys.argv[2:]
CONFIG_OVERRIDE = next((a.split('=', 1)[1] for a in sys.argv[2:] if a.startswith('--audit-config=')), None)
LABEL_OVERRIDE = next((a.split('=', 1)[1] for a in sys.argv[2:] if a.startswith('--audit-label=')), None)
if ALL_RAMPS:
    assert PHYSICAL_SPEED and not INIT_ONLY
if CONFIG_OVERRIDE or LABEL_OVERRIDE:
    assert PHYSICAL_SPEED and ALL_RAMPS and LABEL_OVERRIDE
    assert LABEL_OVERRIDE.isalnum(), 'A simple unique audit label is required'
SERVICE329 = '--service329' in sys.argv[2:] or PHYSICAL_SPEED
HEAD_LANE = '--head-lane' in sys.argv[2:] or SERVICE329
HEAD_PHASE = '--head-phase' in sys.argv[2:] or HEAD_LANE
LABEL = str(AT)+('_init' if INIT_ONLY else '')+('_after' if AFTER else '')+('_hl' if HEAD_LANE else '_hp' if HEAD_PHASE else '')
if SERVICE329:
    assert not INIT_ONLY and not AFTER
    LABEL = str(AT)+'_svc'
if PHYSICAL_SPEED:
    LABEL = str(AT)+'_ps'
if ALL_RAMPS:
    LABEL += '_all8'
if LABEL_OVERRIDE:
    LABEL += '_'+LABEL_OVERRIDE
OUT = HERE / 'city_path' / LABEL
OUT.mkdir(parents=True, exist_ok=False)
ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
from evaluation.controllers import obs150_contract as oc


def verify_existing(raw, derived):
    obs = raw[oc.RAW_STATE_KEY]
    path = oc.resolve(obs, oc.derived_path(obs['sim_sec']))
    assert path.read_bytes() == oc.derived_bytes(derived)
    return path


oc.write_derived = verify_existing
helper = I / 'probe_selected_arrival_path.py'
spec = importlib.util.spec_from_file_location('city_path_probe', helper)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
original = module.probe_levers
tuning = I / 'baseline_reproduction_20260929/cellwise_calibration/coupled_expanded_joint/candidate_config.json'
if PHYSICAL_SPEED:
    tuning = HERE/'physical_speed/candidate_config.json'
elif SERVICE329:
    tuning = HERE/'service329/candidate_config.json'
elif HEAD_PHASE:
    document = json.loads(tuning.read_bytes())
    assert not document['urban']['queue'].get('attribution')
    document['urban']['queue']['attribution'] = 'head_phase'
    if HEAD_LANE:
        document['urban']['queue']['head_lane_contract'] = str((HERE/'city_path/head_lane_support.json').relative_to(U))
    candidate = HERE/('city_path/head_lane_config.json' if HEAD_LANE else 'city_path/head_phase_config.json')
    data = (json.dumps(document,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    if candidate.exists():
        assert candidate.read_bytes()==data
    else:
        candidate.write_bytes(data)
    tuning = candidate
if CONFIG_OVERRIDE:
    tuning = Path(CONFIG_OVERRIDE).resolve(strict=True)
    assert tuning.is_relative_to(U)


def relevant(key):
    return any(s in str(key) for s in (
        ('SC1001', 'SC1002', 'SC1003', 'SC1004', 'RM_C', 'freeway:', 'offramp:', 'origin:')
        if ALL_RAMPS else ('SC1001', 'SC1002', 'RM_C10484')))


def snapshot(state, cfg):
    return dict(time_sec=state.time_sec,
        urban_link_speed_kph={k:v for k,v in state.urban_link_speed_kph.items() if relevant(k)},
        queue={k:v for k,v in state.urban_movement_queue.items() if relevant(k)},
        storage={k:cfg.network.urban_link_storage_veh[k]-v for k,v in state.urban_link_storage.items() if relevant(k)},
        arrival_buffer={k:v for k,v in state.urban_arrival_buffer.items() if relevant(k)},
        release_buffer={k:v for k,v in state.urban_storage_release_buffer.items() if relevant(k)})


def audit(captured, reference, output, **kwargs):
    from src.controllers import rollout_endpoint as endpoint
    from src.models import urban_queue_model as uqm
    cfg, state = captured['cfg'], captured['state']
    if ALL_RAMPS:
        (OUT/'ramp_initial.json').write_text(json.dumps(dict(
            queue=state.ramp_queue,
            buffers={r:dict(metadata=b.metadata(),snapshot=b.snapshot())
                     for r,b in state.lane_ramp_runtime.buffers.items()},
            branches=cfg.network.physical_ramp_branches),indent=2)+'\n',encoding='utf-8')
    if HEAD_PHASE:
        summary = state.local_observation_summary
        (OUT/'projection.json').write_text(json.dumps(dict(
            diagnostics=summary['projection_diagnostics'],
            queue=state.urban_movement_queue,storage_available=state.urban_link_storage,
            ramp_queue=state.ramp_queue),indent=2,allow_nan=False)+'\n',encoding='utf-8')
    if SERVICE329:
        (OUT/'service_projection.json').write_text(json.dumps(dict(
            movement_capacity=cfg.network.movement_capacity_by_movement_veh_h,
            head_resources=cfg.network.head_service_resources),indent=2,allow_nan=False)+'\n',encoding='utf-8')
    effective = {}
    for key, value in vars(cfg.network).items():
        if isinstance(value, dict):
            selected = {k:v for k,v in value.items() if relevant(k)}
            if selected:
                try:
                    json.dumps(selected, allow_nan=False)
                except (TypeError, ValueError):
                    continue
                effective[key] = selected
    (OUT/'initial.json').write_text(json.dumps(dict(state=snapshot(state,cfg),network=effective,
        simulation=vars(cfg.simulation),
        travel_parameters={k:getattr(cfg.network,k) for k in ('urban_avg_speed_km_h','urban_avg_vehicle_length_m')},
        forecast_boundary=[d.urban_boundary for d in captured['forecast']],
        future_observation_inputs=False),indent=2,allow_nan=False)+'\n',encoding='utf-8')
    if PHYSICAL_SPEED:
        (OUT/'physical_speed.json').write_text(json.dumps(dict(
            observed=state.local_observation_summary['urban_link_speed_kph'],
            direct_transport=cfg.network.direct_exit_legsplit,
            initial_routes=state.direct_exit_route_state),indent=2)+'\n',encoding='utf-8')
    delay_original = uqm._link_delay_steps
    delay_rows = {}

    def delay(s,c,link):
        n = delay_original(s,c,link)
        if relevant(link):
            key = (s.time_sec,link,n)
            delay_rows[key] = delay_rows.get(key,0)+1
        return n

    eval_original = endpoint.evaluate_price_point
    calls = []

    def evaluate(*args, **kw):
        assert not calls, 'Only one held forecast is authorized per state'
        point = eval_original(*args,**kw)
        calls.append(point.ttt)
        response = point.control_area_response
        record = dict(ttt=point.ttt,states=[snapshot(s,cfg) for s in point.states],
            transfers=[r for r in response['transfers'] if relevant(r['source']) or relevant(r['target'])],
            resources=[r for r in response['resource_allocations'] if relevant(r['resource'])
                or any(relevant(k) for k in r.get('accepted_by_source_veh',{}))],
            residence=[{**{k:v for k,v in r.items() if k not in ('model_stock_veh','inside_veh')},
                'model_stock_veh':{k:v for k,v in r['model_stock_veh'].items() if relevant(k)}}
                for r in response['residence']],
            delay_calls=[dict(time_sec=t,link=k,delay_steps=n,calls=v) for (t,k,n),v in delay_rows.items()])
        if ALL_RAMPS:
            record['ramp_snapshots'] = [dict(time_sec=s.time_sec,queue=s.ramp_queue,
                buffers={r:b.snapshot() for r,b in s.lane_ramp_runtime.buffers.items()})
                for s in point.states]
        with gzip.open(OUT/'trace.json.gz','wt',encoding='utf-8') as stream:
            json.dump(record,stream,allow_nan=False)
        return point

    uqm._link_delay_steps = delay
    endpoint.evaluate_price_point = evaluate
    try:
        if INIT_ONLY:
            print(json.dumps(dict(initialization_saved=True,forecasts=0)))
            return
        result = original(captured,reference,output,**kwargs)
        assert len(calls) == 1
        return result
    finally:
        uqm._link_delay_steps = delay_original
        endpoint.evaluate_price_point = eval_original
        pins = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            [Path(__file__),helper,tuning,U/'evaluation/controllers/urban_flow_accounting.py',
             U/'evaluation/controllers/observation_projection.py',
             U/'evaluation/controllers/runtime_setup.py',
             U/'evaluation/controllers/vissim_stackelberg_adapter.py',
             U/'evaluation/controllers/head_service_resources.py',
             U/'evaluation/controllers/lane_plant_runtime.py',
             U/'evaluation/controllers/route_choice_corridor.py',
             U/'evaluation/controllers/physical_ramp_boundary.py',
             U/'evaluation/controllers/lane_ramp_runtime.py',
             U/'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py',
             U/'vendor/NumSim-mine/src/models/urban_queue_model.py']}
        (OUT/'receipt.json').write_text(json.dumps(dict(forecast_count=len(calls),ttt=calls,
            future_observation_inputs=False,new_native=0,coefficient_fits=0,pins=pins),indent=2)+'\n',encoding='utf-8')


module.probe_levers = audit
sys.argv = [str(helper),'--closedloop-recorded',f'--at={AT}','--lever-probe450','--held450',
    '--meter-ramp=RM_C10484','--warm-head-history','--replay-vsl-history',
    '--recording-dir=D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29',
    '--tuning-json='+str(tuning),f'--probe-label=city{LABEL}']
module.main()
