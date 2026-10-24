"""Read completed139 only: preserve failures and identify the remaining response.

No model call, fitting, FZP access, or native run. These are model-internal
mechanism changes, not causal attribution of the VISSIM response.
"""
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent


def read(p):
    data = p.read_bytes()
    return json.loads(gzip.decompress(data) if p.suffix == '.gz' else data)


def main():
    assert read(HERE/'status.json')['status'] == 'complete_macro_gate_failed'
    pins = {}

    def load(p):
        pins[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
        return read(p)

    tables = {}
    pressure = []
    for label, folder in [('frozen132', R/'lane_state132/autonomous_diagnostic/training'),
                          ('closing139', HERE/'training')]:
        tables[label] = {}
        for arm in ('hold', 'release', 'hold_vsl90', 'release_vsl90'):
            p = folder/f's67_late_{arm}.json.gz'
            pred = load(p)
            lane = pred['diagnostics']['roads'][0]['joint_lane_region']
            early = [x for x in lane['rows'] if x['lane'] == 1 and abs(x['time_s']-2700.1) < 1e-6]
            windows = []
            for start, end in [(2670.1, 2820.1), (2820.1, 2970.1), (2970.1, 3120.1)]:
                flow = [x for x in pred['flows'] if x['window_start_s'] >= start-1e-6 and x['window_end_s'] <= end+1e-6]
                junction = [x for x in lane['junction_rows'] if start-1e-6 <= x['time_s'] < end-1e-6]
                assert len(junction) == 150
                request = sum(x['off_request_veh'] for x in junction)
                accepted = sum(x['off_accepted_veh'] for x in junction)
                off = sum(x['off_departures'] for x in flow if x['cell'] == 20)
                assert abs(off-accepted) < 1e-7
                windows.append(dict(start=start, end=end, off_request=request, off_accepted=accepted,
                    reciprocal_cut=sum(x['off_before_veh']-x['off_accepted_veh'] for x in junction),
                    off_storage_limited_steps=sum(x['off_before_veh']+1e-9 < x['off_request_veh'] for x in junction),
                    through20=sum(x['downstream_crossings'] for x in flow if x['cell'] == 20),
                    merge21=sum(x['ramp_merges'] for x in flow if x['cell'] == 21),
                    merge23=sum(x['ramp_merges'] for x in flow if x['cell'] == 23)))
            tables[label][arm] = dict(first30_lane1=early, windows=windows)
            if label == 'closing139':
                trace = load(folder/f's67_late_{arm}_pressure.json.gz')
                assert len(trace) == 1350
                for g in (1, 2, 3):
                    for start, end in [(2670.1, 2820.1), (2820.1, 2970.1), (2970.1, 3120.1)]:
                        rr = [x for x in trace if x['lane'] == g and start+1e-6 < x['time_s'] <= end+1e-6]
                        assert len(rr) == 150
                        pressure.append(dict(arm=arm, lane=g, start=start, end=end,
                            limited_steps=sum(x['new_pressure'] > x['old_pressure']+1e-9 for x in rr),
                            mean_pressure_removed=sum(x['new_pressure']-x['old_pressure'] for x in rr)/150))
    # Native first30 recovery from the existing current-state population ledger.
    actual = load(R/'recovery_terms137/rows.json.gz') + load(R/'onset_reaction134/rows.json.gz')
    native_early = []
    for cell in range(19, 26):
        a = [x for x in actual if x['case'] == 's67_late' and x['arm'] == 'release'
             and x['cell'] == cell and x['lane'] == 1 and abs(x['time_s']-2695.1) < 1e-6]
        assert len(a) == 1, (cell, len(a))
        native_early.append(dict(cell=cell, n_veh=a[0]['n1'], v_kmh=a[0]['v1']))
    rows = load(HERE/'training/rows.json')
    checks = dict(max_conservation=max(x['conservation_max'] for x in rows),
        max_route_partition=max(x['route_error'] for x in rows),
        pressure_samples=sum(x['pressure139']['samples'] for x in rows),
        baseline_parity=load(HERE/'parity.json'))
    assert checks['max_conservation'] < 1e-7 and checks['max_route_partition'] < 1e-7
    result = dict(status='REJECTED_NOT_ADOPTED', forecast_scope='FW_E31+4on+4off, not Omega',
        tables=tables, native_first30_release_lane1=native_early, pressure=pressure, checks=checks,
        new_forecasts=0, new_native=0, new_FZP=0, input_sha256=pins)
    (HERE/'local_assessment.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(checks))
    print('native_first30', native_early)
    for label, arms in tables.items():
        for arm in ('release', 'release_vsl90'):
            print(label, arm, 'middle150', arms[arm]['windows'][1])
            if arm == 'release': print('first30', [(x['cell'],x['n_veh'],x['v_kmh']) for x in arms[arm]['first30_lane1']])


if __name__ == '__main__':
    main()
