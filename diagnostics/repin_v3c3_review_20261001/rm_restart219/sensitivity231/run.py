"""Bounded initial-speed sensitivity, using canonical recorded-command initialization."""
import copy
import ctypes
import hashlib
import json
import math
import sys
import time
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = D.parents[3]
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
BASE = D.parent / 'independent230/replay_v2'
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def save(name, value):
    (D / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def run(captured, candidates, coord, output):
    from evaluation.controllers import sdmpc_sequence as sequence
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    from src.controllers import rollout_endpoint as endpoint
    state, cfg = captured['state'], captured['cfg']
    assert state.time_sec == 2250 and len(captured['forecast']) == 3
    protocol = load(BASE / 'protocol.json')
    base_output = Path(protocol['output'])
    baseline = {arm: load(base_output / (arm + '.json')) for arm in ('rm', 'both')}
    old = baseline['rm']['physical_cell_states'][0]
    assert old['speed_kmh']['FW_E'] == list(state.freeway_speed['FW_E'])
    assert old['density']['FW_E'] == list(state.freeway_density['FW_E'])
    inventory = model_inventory(state, cfg)
    get_ledger(state).assert_stocks(inventory)
    # A single smooth pulse. It changes only speed, never stock, routes or inputs.
    pulse = {cell: math.sin(math.pi * (cell - 18) / 8) for cell in range(19, 26)}
    assert max(pulse.values()) == 1.0
    rows = []
    for arm in ('rm', 'both'):
        action = candidates[arm]
        coord.validate(action)
        for block, command in enumerate(sequence.actions(action, 3)):
            expected = baseline[arm]['commands'][block]
            assert command.vsl == expected['vsl'] and command.green_times == expected['green_times']
            assert command.offsets == expected['offsets']
            assert {r: command.diagnostics['rw_meter_green_' + r] for r in cfg.network.ramps} == expected['meters']
        for direction in (-1, 1):
            trial = copy.deepcopy(state)
            trial.freeway_speed['FW_E'] = list(trial.freeway_speed['FW_E'])
            for cell, amplitude in pulse.items():
                trial.freeway_speed['FW_E'][cell] += direction * amplitude
                assert trial.freeway_speed['FW_E'][cell] > 5
            assert model_inventory(trial, cfg) == inventory
            get_ledger(trial).assert_stocks(inventory)
            started = time.perf_counter()
            with sequence.prediction_scope(action, cfg, trial.time_sec, 3) as visits:
                point = endpoint.evaluate_price_point(trial, action, copy.deepcopy(captured['forecast']), (),
                    endpoint.ObjectiveSpec(cfg, depth_override=3, box_walk=False, score_mode='raw'), capture_response=True)
            assert visits == [0, 1, 2] and not point.aborted and len(point.states) == 3
            response = point.control_area_response
            cost = sum(r['dt_h'] * sum(r['inside_veh'].values()) for r in response['residence'])
            assert abs(cost - point.ttt) < 1e-7
            resource = max((r['exceedance_veh'] for r in response['resource_allocations']), default=0)
            assert resource < 1e-7
            terminal = sum(r['vehicles'] for r in response['transfers']
                           if r['source'] == 'freeway:FW_E' and r['target'] == 'external:terminal:FW_E')
            snapshots = []
            for s, reference in zip(point.states, baseline[arm]['physical_cell_states'][1:]):
                inv = model_inventory(s, cfg)
                get_ledger(s).assert_stocks(inv)
                speed_delta = [v - b for v, b in zip(s.freeway_speed['FW_E'], reference['speed_kmh']['FW_E'])]
                snapshots.append(dict(time_sec=s.time_sec, speeds=list(s.freeway_speed['FW_E']),
                    speed_delta=speed_delta, maximum_absolute_speed_delta=max(map(abs, speed_delta)),
                    east_stock=inv['freeway:FW_E']))
            row = dict(arm=arm, direction=direction, initial_speed_pulse=pulse,
                ttt_omega_veh_h=point.ttt, cost_delta_veh_h=point.ttt-baseline[arm]['ttt_omega_veh_h'],
                east_terminal_veh=terminal, snapshots=snapshots, maximum_resource_exceedance_veh=resource,
                wall_sec=time.perf_counter()-started)
            rows.append(row)
            save('results.json', rows)
            print(json.dumps({k: row[k] for k in ('arm', 'direction', 'cost_delta_veh_h', 'east_terminal_veh', 'wall_sec')}), flush=True)
    assert len(rows) == 4
    assert old['speed_kmh']['FW_E'] == list(state.freeway_speed['FW_E'])
    save('completion.json', dict(status='COMPLETE_DIAGNOSTIC_NOT_CALIBRATION', forecasts=4,
        results=rows, autonomous_prediction_qualification=False, native_runs=0, fit_calls=0,
        optimizer_calls=0, FZP_reads=0,
        limitations=['Artificial initial speed perturbations, not additional native observations.',
            'One prescribed smooth mode and one amplitude are not a full stability spectrum or uncertainty bound.',
            'No parameter correction is inferred from this experiment alone.']))


def main():
    assert not (D / 'protocol.json').exists()
    p = load(BASE / 'protocol.json')
    assert all(sha(ROOT / path) == h for path, h in p['source_sha256'].items())
    assert sha(BASE / 'candidate_config.json') == p['config_sha256']
    assert sha(Path(p['STOP']['path'])) == p['STOP']['sha256']
    save('protocol.json', dict(start_sec=2250, seed=71, duration_sec=450, max_forecasts=4,
        cells=list(range(19,26)), amplitude_kmh=1.0, perturbation='smooth half-sine +/- speed pulse; stock unchanged',
        source_sha256=p['source_sha256'], config_sha256=p['config_sha256'], existing_STOP=p['STOP'],
        baseline_protocol_sha256=sha(BASE/'protocol.json'), baseline_output=p['output'],
        native_runs=0, fits=0, outcome_calibration=False, future_observation_inputs=False))
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.GetCurrentProcess.restype=ctypes.c_void_p
    k.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
    from evaluation.controllers import obs150_contract as oc
    original = probe.probe_levers
    def capture(*args, **kwargs):
        return original(*args, prepared_probe_callback=run, **kwargs)
    def existing(raw, derived):
        obs=raw[oc.RAW_STATE_KEY]; path=oc.resolve(obs,oc.derived_path(obs['sim_sec']))
        assert path.read_bytes()==oc.derived_bytes(derived)
        return path
    probe.probe_levers=capture
    oc.write_derived=existing
    proof=I/'native_rm_observation2700_s71_four84/analysis/observation_reuse.json'
    receipt=load(proof)
    sys.argv=[str(Path(probe.__file__)), '--closedloop-recorded', '--at=2250', '--warm-head-history',
        '--replay-vsl-history', '--trace-ramp=RM_C10681', '--output-suffix=rm231_speed_pulse_s71',
        '--recording-dir='+receipt['recording_dir'], '--four-arm-receipt='+str(proof),
        '--tuning-json='+str(BASE/'candidate_config.json')]
    probe.main()
    assert all(sha(ROOT/path)==h for path,h in p['source_sha256'].items())
    assert sha(Path(p['STOP']['path']))==p['STOP']['sha256']


if __name__ == '__main__':
    main()
