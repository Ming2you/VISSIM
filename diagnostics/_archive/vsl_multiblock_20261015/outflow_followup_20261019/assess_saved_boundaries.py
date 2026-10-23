"""New multizone boundary evidence from saved states; no rollout or FZP scan."""
import os
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from collections import defaultdict

OUT = Path(__file__).resolve().parent
HERE = OUT.parent
PACK = Path('D:/VISSIM_packages/vsl_multizone355_20261015')
OLD = Path('E:/VISSIM_analysis/20261011_vsl_response349/cached_off2250_flow_review_v1')
RUN = Path('D:/VISSIM_runs/20261016_vsl_multizone2250_repaired_s29/selected/decisions_sdmpc31_g_2250_selected_s29')
PINS = {}


def read(p):
    p = Path(p)
    raw = p.read_bytes()
    PINS[str(p)] = hashlib.sha256(raw).hexdigest()
    return json.loads(raw)


def main():
    assert not (OUT/'summary.json').exists(), 'Reuse completed evidence; do not overwrite'
    sys.path[:0] = [str(PACK/'diagnostics/vsl_response349'), str(PACK), str(PACK/'vendor/NumSim-mine')]
    from assess import targets
    import assess
    from evaluation.controllers import offramp_routing as routing
    for path in (Path(__file__), Path(assess.__file__), Path(routing.__file__)):
        PINS[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    proof = read(HERE/'native_analysis_repaired_20261016/summary.json')
    closure = read(HERE/'native_analysis_repaired_20261016/runtime_closure.json')
    assert proof['counterfactual_valid'] and proof['existing_forecast_comparison_qualified']
    assert closure['all_owned_processes_closed'] and closure['wrapper_closed'] and closure['owner_exit_code'] == 0
    old = read(OLD/'summary.json')
    old_snapshots = read(OLD/'physical31_snapshots.json')
    model_summary = read(HERE/'matched_off2250_v3/summary.json')
    horizon = read(HERE/'native_analysis_repaired_20261016/horizon_summary.json')
    config = PACK/'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/vsl_schedules_20261015/config.json'
    tuning = read(config)
    assert PINS[str(config)] == model_summary['model_config_sha256']
    inventory = read(PACK/tuning['freeway']['offramp_route_inventory'])
    mapping_path = PACK/inventory['mapping']['path']
    mapping = read(mapping_path)
    assert PINS[str(mapping_path)] == inventory['mapping']['sha256']
    actual, pins = targets(RUN, 2250, config)
    PINS.update(pins)
    by_case = {'hold': [x['actual'] for x in old_snapshots['hold']], 'single90': [x['actual'] for x in old_snapshots['vsl90']], 'selected': actual}
    predictions = {x['name']: x['snapshots'] for x in model_summary['results']}
    raw = [read(RUN/f'state_{t:06d}.json') for t in (2250, 2400, 2550, 2700)]
    detector_path = Path(raw[0]['obs150']['detector_config']['path'])
    blob = detector_path.read_bytes()
    PINS[str(detector_path)] = hashlib.sha256(blob).hexdigest()
    assert all(x['obs150']['detector_config']['sha256'] == PINS[str(detector_path)] for x in raw)
    refs = defaultdict(list)
    for row in csv.DictReader(blob.decode('utf-8-sig').splitlines()):
        if row['role'] in ('source', 'chain_end', 'off_entry', 'through', 'meter_head', 'ramp_arrival'):
            refs[row['boundary_ref']].append(row['dcm_no'])
    flows = {ref: [sum(x['obs150']['detectors'][k] for k in keys) for x in raw[1:]] for ref, keys in refs.items()}
    for ref, keys in refs.items():
        cumulative = [sum(x['obs150']['detectors_cum'][k] for k in keys) for x in raw]
        assert flows[ref] == [b-a for a, b in zip(cumulative, cumulative[1:])], ref
    off = ['off_entry:'+x for x in ('10481', '10483', '10643', '10682')]
    flows['off_all:FW_E'] = [sum(flows[k][i] for k in off) for i in range(3)]
    old_cases = old['cases']
    all_flows = {'hold': old_cases['hold']['direct_detector_flows150'], 'single90': old_cases['vsl90']['direct_detector_flows150'], 'selected': flows}
    for case, snapshots in by_case.items():
        assert [x['time_sec'] for x in snapshots] == [2250, 2400, 2550, 2700]
        for fw in ('FW_E', 'FW_W'):
            assert snapshots[0]['n'][fw] == by_case['hold'][0]['n'][fw]
            assert max(abs(x-y) for x, y in zip(predictions[case][0]['n'][fw], snapshots[0]['n'][fw])) < 1e-7
    rows, cells = [], []
    for case in ('single90', 'selected'):
        for i, end in enumerate((150, 300, 450), 1):
            a, b = all_flows['hold'], all_flows[case]
            row = {'case': case, 'horizon_sec': end}
            for label, ref, model_key in [('source', 'source:FW_E', 'source_accepted'), ('terminal', 'chain_end:FW_E', 'terminal_outflow'), ('off', 'off_all:FW_E', 'offramp_outflow')]:
                row[label+'_native_delta'] = sum(b[ref][:i])-sum(a[ref][:i])
                row[label+'_model_delta'] = horizon['model'][case][str(end)][model_key]-horizon['model']['hold'][str(end)][model_key]
            row['east_stock_native_delta'] = sum(by_case[case][i]['n']['FW_E'])-sum(by_case['hold'][i]['n']['FW_E'])
            row['east_stock_model_delta'] = sum(predictions[case][i]['n']['FW_E'])-sum(predictions['hold'][i]['n']['FW_E'])
            row['unresolved_delta_balance_remainder_NOT_merge'] = row['east_stock_native_delta']-row['source_native_delta']+row['terminal_native_delta']+row['off_native_delta']
            row.update(horizon['comparisons'][case][str(end)])
            rows.append(row)
    regions = {'all': range(31), 'approach14_18': range(14,19), 'bottleneck19_23': range(19,24), 'downstream24_30': range(24,31)}
    absolute = []
    for case, snapshots in by_case.items():
        for i, obs in enumerate(snapshots):
            pred = predictions[case][i]
            for region, indices in regions.items():
                n = sum(obs['n']['FW_E'][c] for c in indices)
                pn = sum(pred['n']['FW_E'][c] for c in indices)
                v = math.fsum((obs['speed']['FW_E'][c] or 0)*obs['n']['FW_E'][c] for c in indices)/n if n else None
                pv = math.fsum(pred['speed']['FW_E'][c]*pred['n']['FW_E'][c] for c in indices)/pn if pn else None
                absolute.append(dict(case=case, elapsed=i*150, region=region, native_n=n, model_n=pn, stock_error=pn-n, native_v=v, model_v=pv, native_stopped=sum(obs['stopped']['FW_E'][c] for c in indices)))
            for c in range(31):
                cells.append(dict(case=case, elapsed=i*150, cell=c, native_n=obs['n']['FW_E'][c], model_n=pred['n']['FW_E'][c], native_v=obs['speed']['FW_E'][c], model_v=pred['speed']['FW_E'][c]))
    for p, digest in PINS.items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest() == digest, p
    report = dict(status='completed_new_saved_boundary_evidence', previous_goal_turn='progress: native comparison completed and narrowed late model penalty', new_native=0, new_forecasts=0, new_fzp_scans=0, coefficient_changes=0, production_edits=0,
                  rows=rows, absolute_operating_points=absolute, cell_records=cells, selected_detector_flows150=flows, native_snapshots=by_case,
                  qualification='Reuses qualified identical prefix, actual execution and owner closure; future observed states are evaluation targets only.',
                  limitations=['Detector crossings are not model-face fluxes; face location offsets remain.', 'Balance remainder is not an independently observed merge count.', 'Native inside-cell boundary crossings are still unavailable.', 'No small-sign fitting; no universal VSL gain or8100 policy benefit.'], source_pins=PINS)
    (OUT/'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps({'rows': rows, 'absolute450': [x for x in absolute if x['elapsed']==450 and x['region'] in ('all','bottleneck19_23')], 'pins_checked': len(PINS)}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
