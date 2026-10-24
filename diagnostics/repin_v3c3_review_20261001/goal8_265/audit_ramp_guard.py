"""Read saved observations/commands to audit the existing ramp storage guard.

No FZP scan, parameter fit, controller optimization, COM, or native run.
"""
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
DECISIONS = Path('D:/VISSIM_runs/20261006_urban_storage40_fixed90_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29')


def main():
    inputs = {}

    def read(path):
        data = path.read_bytes()
        inputs[str(path)] = hashlib.sha256(data).hexdigest()
        return json.loads(data)

    network = read(HERE / 'rounding_5100/network.json')
    spec = network['physical_ramp_branches']
    bounds = read(HERE / 'rounding_5100/bounds.json')
    execution = read(HERE / 'current_native_analysis_to8100/sdmpc/execution.json')
    assert execution['native_execution_passed'] and execution['terminal_sec'] == 8100
    assert execution['decision_recovery']['passed']
    verified_holds = execution['decision_recovery']['holds']
    raw = read(DECISIONS / 'state_005100.json')
    path = Path(raw['network_path'])
    data = path.read_bytes()
    inputs[str(path)] = hashlib.sha256(data).hexdigest()
    assert inputs[str(path)] == spec['network']['sha256']
    heads = {(int(h.get('lane').split()[0]), int(h.get('lane').split()[1])): float(h.get('pos'))
             for h in ET.fromstring(data).iter('signalHead')}
    rows = []
    replay_matches = []
    for at in range(900, 8100, 150):
        raw = read(DECISIONS / f'state_{at:06}.json')
        previous = read(DECISIONS / f'action_{at-150:06}.json')
        action_path = DECISIONS / f'action_{at:06}.json'
        action = read(action_path)
        if not action_path.with_suffix('.json.applied').is_file():
            # Error holds have no successful optimization commit marker. Use the
            # existing copied-command and native execution proof, not a fake marker.
            assert str(at) in verified_holds
            assert action['metadata']['controller_status'] == 'hold_previous_error'
        records = raw['vehicle_records']
        assert records['complete'] and records['paused_at_sim_sec'] == at
        expected = read(HERE / f'rounding_{at}/bounds.json') if at in (5100, 6450) else None
        for ramp, observed in bounds['ramps'].items():
            connector = int(ramp.split('C')[1])
            lanes = []
            resolved = len(observed['lanes']) > 1
            # The production runtime splits selected receiving nodes by lane;
            # other ramps use one reservoir for all physical lanes.
            head = min(pos for (link, _), pos in heads.items() if link == connector)
            for lane in observed['lanes']:
                number = lane['lane']
                count = sum(v['link_no'] == connector and (not resolved or v['lane_no'] == number)
                            and v['position_m'] <= head for v in records['records'])
                lanes.append(dict(lane=number, prehead_veh=count,
                                  capacity_veh=lane['capacity_veh'],
                                  fill_fraction=count / lane['capacity_veh']))
            old = previous['diagnostics']['rw_meter_green_' + ramp]
            actual = action['diagnostics']['rw_meter_green_' + ramp]
            trigger = any(v['fill_fraction'] >= spec['storage_release_guard']['trigger_fraction']-1e-10 for v in lanes)
            floor = spec['minimum_green_sec']
            if trigger:
                floor = max(floor, min(spec['cycle_sec'], old + spec['max_green_change_sec']))
            result = dict(previous_green_sec=old, minimum_green_sec=floor,
                          triggered=trigger, lanes=lanes)
            if expected is not None:
                assert result == expected['ramps'][ramp], (at, ramp, result, expected['ramps'][ramp])
                replay_matches.append([at, ramp])
            rows.append(dict(sim_sec=at, ramp=ramp, **result, actual_green_sec=actual,
                             reservoir_scope='per_lane' if resolved else 'all_lanes_combined',
                             controller_status=action['metadata'].get('controller_status', 'ok'),
                             violates_current_storage_floor=actual < floor - 1e-9))
    breaches = [r for r in rows if r['violates_current_storage_floor']]
    summary = dict(control_times=len(rows)//8, ramp_command_checks=len(rows),
                   triggered_checks=sum(r['triggered'] for r in rows),
                   breaches=len(breaches),
                   breach_times=sorted({r['sim_sec'] for r in breaches}),
                   breach_ramps=sorted({r['ramp'] for r in breaches}),
                   canonical_initialized_bounds_matches=len(replay_matches),
                   breaches_after_error_hold=sum(r['controller_status']=='hold_previous_error' for r in breaches))
    result = dict(summary=summary, breaches=breaches, rows=rows, source_pins=inputs,
                  native_evidence='Reuse completed 1..8100 native LDP/VSL proof; CSV alone is not execution evidence.',
                  limitations=['Observed occupancy guard, not predictive spillback prevention.',
                               'Guard breach is a command-policy failure, not proof of its TTT effect.',
                               'Per-lane nominal capacity is the unchanged initialized model capacity.',
                               'Vehicle deletion or continuous queue geometry is not inferred from snapshots.',
                               'LSA coverage failure retained; approved native LDP substitute used.'])
    (HERE / 'ramp_guard_audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False))
    for r in breaches:
        print(r['sim_sec'], r['ramp'], r['actual_green_sec'], r['minimum_green_sec'], r['controller_status'])


if __name__ == '__main__':
    main()
