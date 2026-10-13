"""Separate current SC6 stock, later arrivals and aggregate route reassignment.

Closed detector identities are diagnostic labels only, never forecast inputs.
No FZP scan, new prediction, optimization or simulation is performed.
"""
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
H = HERE.parent
ROOT = HERE.parents[3]
PINS = {}
SUPPORT = {138, 10209, 1210018302, 1220015100, 1220018301, 1220018302}


def read(path):
    raw = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(raw).hexdigest()
    return json.loads(raw)


def main():
    assert not (HERE / 'assessment.json').exists(), 'Preserve completed evidence'
    path = H / 'sc12_source/audit.py'
    loader = importlib.util.spec_from_file_location('closed_sc6_head_audit', path)
    helper = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(helper)
    helper.LINKS = {'SC6_S': 1210018302}
    net = read(H / 'sc101_recombined/forecast2400/network.json')
    state = read(H / 'sc101_recombined/forecast2400/state.json')
    source = 'SC12_to_SC6'
    moves = {m: row for m, row in net['urban_movements'].items()
             if row['origin'] == source}
    ready = {m: state['urban_movement_queue'][m] for m in moves}
    residual = sum(state['urban_arrival_buffer'][source].values())
    assert abs(sum(ready.values()) + residual - 82) < 1e-7
    assert source not in state.get('gate_initial_route_tags', {})
    initial_split = {m: ready[m] + residual * row['beta'] for m, row in moves.items()}
    arms = {}
    all_initial_records = []
    for arm in ('hold', 'selected'):
        folder = helper.NATIVE / arm / f'decisions_sdmpc31_g_2400_{arm}_s29'
        raw = read(folder / 'state_002400.json')
        assert raw['sim_sec'] == 2400 and raw['vehicle_records']['complete']
        initial = {v['veh_no']: v for v in raw['vehicle_records']['records']}
        assert len(initial) == len(raw['vehicle_records']['records'])
        local = {n: v for n, v in initial.items() if v['link_no'] in SUPPORT}
        assert len(local) == 82
        all_initial_records.append(raw['vehicle_records']['records'])
        location = Counter((v['link_no'], v['lane_no'], bool(v['stopped'])) for v in local.values())
        seen = set()
        initial_head = Counter()
        rows = []
        witnesses = []
        for end in (2550, 2700, 2850):
            counts, events = helper.heads_and_entries(folder, end)
            identities = [n for lane, n, t in events['SC6_S']]
            assert len(identities) == len(set(identities)), 'Duplicated head passage'
            assert not seen.intersection(identities), 'Repeated head passage between windows'
            seen.update(identities)
            categories = Counter()
            for lane, n, t in events['SC6_S']:
                phase = 'p1' if lane in (1, 2, 3) else 'p2'
                assert lane in (1, 2, 3, 4)
                origin = 'initial_SC6' if n in local else 'initial_elsewhere' if n in initial else 'not_in_initial'
                categories[(phase, origin)] += 1
                if n in local:
                    initial_head[phase] += 1
                    witnesses.append(dict(vehicle=n, head_time=t, head_lane=lane,
                        initial_link=local[n]['link_no'], initial_lane=local[n]['lane_no']))
            rows.append(dict(end_sec=end, head=counts['SC6_S'],
                by_phase={p: {o: categories[p, o] for o in ('initial_SC6', 'initial_elsewhere', 'not_in_initial')}
                          for p in ('p1', 'p2')}))
        arms[arm] = dict(initial_stock=82, initial_routes_captured='vehicle_routes' in raw,
            initial_by_link_lane=[dict(link=k[0], lane=k[1], stopped=k[2], vehicles=v)
                                  for k, v in sorted(location.items())],
            windows=rows, initial_stock_head_total=dict(initial_head),
            initial_stock_not_seen_at_head=sorted(set(local) - seen), initial_head_witnesses=witnesses)
    assert all_initial_records[0] == all_initial_records[1], 'Pair current vehicle records differ'
    predicted_p1 = sum(v for m, v in initial_split.items() if moves[m]['phase'] == 'SC6_p1')
    predicted_p2 = sum(v for m, v in initial_split.items() if moves[m]['phase'] == 'SC6_p2')
    # A current-lane projection exists already; do not count it as new work or
    # insert measured future destinations into the autonomous initialization.
    old = read(H / 'arrival_head/assessment.json')
    refs = [path, Path(__file__), ROOT / 'evaluation/controllers/observation_projection.py',
            H.parent / 'upstream_worklog/02_urban_b2/diag_c3_r2/U7.md',
            H.parent / 'upstream_worklog/02_urban_b2/diag_c3/C3_DIAGNOSIS_CHECK.md']
    for p in refs:
        PINS[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    PINS.update(helper.PINS)
    report = dict(status='closed_initial_cohort_diagnosis_complete',
        interval_sec=[2400, 2850], exact_pair_current_records=True,
        initial_projection=dict(ready=ready, residual_veh=residual,
            reservations=state['urban_arrival_buffer'][source], implied_full_clearance_by_movement=initial_split,
            implied_full_clearance_by_phase=dict(p1=predicted_p1, p2=predicted_p2)),
        arms=arms,
        interpretation=[
            'Implied model split is eventual assignment of the initial stock, not a prediction of crossing time.',
            'The global origin beta is applied again to residual initial vehicles, despite their lane-dependent initial queue composition.',
            'Native head phase labels are retrospective diagnostics. Current route intent is absent from these raw observations.',
            'Initial elsewhere and not-in-initial categories do not identify the entering source or its route.',
            'Existing arrival_head tested terminal-road lane/position projection. Its limited scope and negative joint-gain result must be reused, not called a new solution.',
            'This distinguishes an urban initialization error from RM10681 receiving. It does not qualify the joint controller gain.'
        ],
        next='Review the existing SC6 terminal-road projection separately from SC101; no new rates or whole-corridor travel calibration from this audit.',
        new_predictions=0, new_native=0, production_changes=0, fitted_coefficients=0,
        previous_arrival_head_status=old.get('status'), source_pins=PINS)
    (HERE / 'assessment.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')
    print(json.dumps(dict(status=report['status'], model_initial_phase=report['initial_projection']['implied_full_clearance_by_phase'],
        native_initial_phase={a: v['initial_stock_head_total'] for a, v in arms.items()},
        unobserved={a: len(v['initial_stock_not_seen_at_head']) for a,v in arms.items()},
        first150={a:v['windows'][0]['by_phase'] for a,v in arms.items()}), ensure_ascii=False))


if __name__ == '__main__':
    main()
