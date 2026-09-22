"""Lossless offline SDMPC evidence; never a native application receipt."""
from pathlib import Path
import hashlib
import json
import math
import os
import pickle
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
TAG = '__sdmpc_evidence_type__'


def json_evidence(value):
    """Keep string-keyed records readable and encode tuple keys without collisions."""
    if value is None or type(value) in (str, bool, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError('Nonfinite qualification evidence')
        return float(value)
    if type(value) is list:
        return [json_evidence(v) for v in value]
    if type(value) is tuple:
        return {TAG: 'tuple', 'items': [json_evidence(v) for v in value]}
    if type(value) is bytes:
        return {TAG: 'bytes', 'hex': value.hex()}
    if type(value) is dict:
        if all(type(k) is str for k in value) and TAG not in value:
            return {k: json_evidence(v) for k, v in value.items()}
        return {TAG: 'mapping', 'items': [[json_evidence(k), json_evidence(v)]
                                         for k, v in value.items()]}
    raise TypeError('Unsupported qualification evidence: ' + type(value).__name__)


def restore_evidence(value):
    """Inverse for inspection/tests; no executable object deserialization."""
    if isinstance(value, list):
        return [restore_evidence(v) for v in value]
    if isinstance(value, dict):
        kind = value.get(TAG)
        if kind == 'tuple':
            return tuple(restore_evidence(v) for v in value['items'])
        if kind == 'bytes':
            return bytes.fromhex(value['hex'])
        if kind == 'mapping':
            return {restore_evidence(k): restore_evidence(v) for k, v in value['items']}
        if kind is not None:
            raise ValueError('Unknown qualification evidence encoding')
        return {k: restore_evidence(v) for k, v in value.items()}
    return value


def atomic_json(path, value):
    text = json.dumps(json_evidence(value), indent=2, allow_nan=False)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(text + '\n', encoding='utf-8')
    temporary.replace(path)


def save_solution(target, response, selection, adapter):
    # Preserve the actual returned objects before JSON conversion. This local
    # checkpoint is evidence, never an authorization to bypass qualification.
    packed = pickle.dumps({'response': response, 'selection': selection}, protocol=5)
    temporary = target / 'solution.pickle.tmp'
    temporary.write_bytes(packed)
    temporary.replace(target / 'solution.pickle')
    command = adapter.control_to_json_dict(response['control'], {
        'controller_variant': 'wu-link', 'sdmpc_active': True,
        'sdmpc_state': selection['price_state'],
        'sdmpc_constraints': selection['final_constraints'],
        'joint_leader_selection': selection,
    })
    # Exercise the native command's existing JSON serializer, without applying it.
    json.dumps(command, allow_nan=False)
    return dict(response={**response, 'control': vars(response['control'])},
                selection=selection, native_command_preview=command,
                native_command_json_serializable=True,
                solution_checkpoint_sha256=hashlib.sha256(packed).hexdigest())


def run(here, entry, lane):
    statepath, previouspath = map(Path, sys.argv[1:3])
    target = here / sys.argv[3]
    target.mkdir(exist_ok=False)
    started = time.perf_counter()
    report = dict(schema='offline-sdmpc-qualification/v2', completed=False,
                  native_command_applied=False, scope=__doc__, pid=os.getpid())
    budget = None
    pins = {}
    error = None
    atomic_json(target / 'started.json', report)
    try:
        from evaluation.controllers import vissim_stackelberg_adapter as a, sdmpc
        from evaluation.controllers import area_follower_objective as joint, area_meter_finalization as meters
        from scripts.offline_harness_20260904 import build
        from src.models.state import TrafficState, ControlAction, segment_vsl
        from src.models.demand import DemandStep
        if lane:
            from evaluation.controllers import lane_plant_runtime
            observe = lane_plant_runtime.observe_live
            lane_plant_runtime.observe_live = lambda c, r: observe(c, r, use_checkpoint=False)
        cfg, state, raw, metadata, det, cal, tuning = build(
            a, TrafficState, here / 'config_candidate.json', statepath, previouspath)
        options = a.joint_owner_game_settings(tuning, cfg, 'wu-link')
        sdmpc.configure(tuning, cfg)
        sdmpc.install_cost_ownership(cfg, det)
        controller = a.build_priced_wu_link_controller(cfg, tuning)
        a.install_vissim_terminal_cost_objective(controller, cfg, tuning)
        a.install_price_worker_bootstrap(controller, raw, det)
        previous = a.control_from_json(previouspath, cfg, ControlAction)
        forecast = a.demand_from_state(raw, cfg, DemandStep, cfg.mpc.horizon_steps, cal, det)
        reference = meters.prepare_held_actual_reference(previous, cfg)
        reference, _ = joint.expand_shared_vsl_action(reference, cfg, segment_vsl_func=segment_vsl)
        mapping = a.load_optional_json(str(ROOT / tuning['mapping_json']))
        paths = [Path(entry), Path(__file__), here / 'config_candidate.json', statepath, previouspath,
                 ROOT / tuning['freeway']['lane_plant'] if lane else here / 'parameter_transfer.json',
                 *sorted((ROOT / 'evaluation/controllers').glob('*.py'))]
        pins = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        bootstrap = {'state_json': {'network_path': str(Path(raw['network_path']).resolve())},
                     'detector_mapping': det, 'runtime_sources': pins}
        budget = joint.DecisionBudget(options['decision_time_budget_sec'],
            reserve_sec=options['finalization_reserve_sec'], unlimited_time=True)
        report.update(source_sha256=pins, current_state_sec=state.time_sec,
            actual_reference_sec=json.loads(previouspath.read_text(encoding='utf-8'))['metadata']['sim_sec'],
            workers=options['response_parallel_workers'])
        atomic_json(target / 'started.json', report)

        def progress(row):
            event = {'wall_sec': time.perf_counter() - started, **row}
            with (target / 'progress.jsonl').open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(event, allow_nan=False) + '\n')
            print(json.dumps(event, allow_nan=False), flush=True)

        response, selection = sdmpc.solve(controller, state, forecast, reference, mapping,
            options=options, runtime_sources=pins, worker_bootstrap=bootstrap, budget=budget,
            progress=progress, previous_path=previouspath)
        report.update(save_solution(target, response, selection, a))
        report['completed'] = True
    except Exception as exc:
        error = exc
        report['error'] = dict(type=type(exc).__name__, message=str(exc), traceback=traceback.format_exc())
    finally:
        try:
            query = getattr(budget, 'response_query', None)
            if query is not None:
                query.close()
                report['query'] = query.stats()
            report['source_changes'] = [p for p, h in pins.items()
                if not Path(p).is_file() or hashlib.sha256(Path(p).read_bytes()).hexdigest() != h]
            if report['source_changes']:
                raise ValueError('Qualification sources changed: ' + str(report['source_changes']))
        except Exception as exc:
            error = error or exc
            report['finalization_error'] = dict(type=type(exc).__name__, message=str(exc), traceback=traceback.format_exc())
        report['completed'] = report['completed'] and error is None
        report['wall_sec'] = time.perf_counter() - started
        try:
            atomic_json(target / 'result.json', report)
        except Exception as exc:
            error = error or exc
            atomic_json(target / 'failure.json', dict(completed=False, native_command_applied=False,
                error=dict(type=type(exc).__name__, message=str(exc), traceback=traceback.format_exc()),
                source_sha256=pins, wall_sec=report['wall_sec']))
        if error is not None:
            raise error

