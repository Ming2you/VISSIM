"""Inspect the existing cell21 receiving ceiling; no new physical forecasts."""
import csv
import hashlib
import math
from pathlib import Path

from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
from diagnostics.repin_v3c3_review_20261001.lane_state132 import prepare as audit
from evaluation.controllers import lane_plant_runtime as lpr


def main():
    out = audit.HERE / 'receiving_check.json'
    assert not out.exists(), 'Preserve completed result'
    context, replay, Obs = common.setup()
    targets = audit.load_targets()
    catalog = audit.read(audit.F.parent / 'data_catalog.json')['checked_records']
    records = [r for r in catalog if r['case'] == 's29_late'] + common.records(False)
    candidates = [('fixed', context['component'], audit.R / 'merge_response129/eval_00'),
        ('lane_fit', lpr.load_sources(audit.HERE / 'eval_01/manifest.json')['component'], audit.HERE / 'eval_01')]
    rows, constants = [], {}
    for label, model, folder in candidates:
        cfg = model._config('FW_E', context['parameters']['by_direction']['FW_E'])
        fd = cfg.network.freeway_segment_params['FW_E'][21]
        jam, length = cfg.network.rho_max, fd['segment_length_km']
        critical = fd['rho_crit']
        capacity = critical * fd['v_free'] * math.exp(-1/fd['metanet_a_m'])
        wave = capacity/(jam-critical)
        constants[label] = dict(effective_fd=fd, jam=jam, capacity_per_lane_vph=capacity, wave_kmh=wave)
        for rec in records:
            key = rec['case'], rec['arm']
            path = Path(rec['truth']) / 'flows_30s.csv'
            audit.PINS[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
            flows = list(csv.DictReader(path.open(encoding='utf-8-sig')))
            pred = audit.read(folder / (key[0] + '_' + key[1] + '.json.gz'))
            region = pred['diagnostics']['roads'][0]['joint_lane_region']
            for block in range(3):
                start, end = round(rec['cutoff']+150*block, 1), round(rec['cutoff']+150*(block+1), 1)
                xs = [x for x in flows if x['road']=='FW_E' and int(x['cell'])==21
                    and start+1e-6 < float(x['window_end_s']) <= end+1e-6]
                assert len(xs) == 5
                actual = sum(float(x['upstream_crossings'])+float(x['ramp_merges']) for x in xs)
                budgets = [x for x in region['receiving_rows'] if start-1e-6 <= x['time_s'] < end-1e-6]
                allocations = [x for x in region['rows'] if x['cell']==21 and start+1e-6 < x['time_s'] <= end+1e-6]
                assert len(budgets)==len(allocations)==450
                consumed = sum(x['mainline_in_veh']+x['merge_veh'] for x in allocations)
                budget = sum(x['accepted_budget_veh'] for x in budgets)
                assert consumed <= budget+1e-7
                right_sampled = None
                if key in targets:
                    sampled = []
                    for t, states in targets[key]['samples'].items():
                        if start+1e-6 < t <= end+1e-6:
                            for lane in (1, 2, 3):
                                n = states[21, lane][0]
                                sampled.append(min(max(0.,jam*length-n),
                                    max(0.,min(capacity,wave*(jam-n/length)))/3600)*5)
                    assert len(sampled)==90
                    right_sampled = sum(sampled)
                rows.append(dict(model=label, case=key[0], arm=key[1], start=start, end=end,
                    native_total_admissions=actual, density_independent_max=capacity*3*150/3600,
                    native_exceeds_fixed_max=actual>capacity*3*150/3600+1e-9,
                    predicted_state_budget=budget, predicted_accepted=consumed,
                    observed_state_right5s_budget=right_sampled))
    for path, expected in audit.PINS.items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==expected
    audit.save(out, dict(constants=constants, rows=rows, input_sha256=audit.PINS,
        interpretation='Receiving includes through21 arrivals plus10490 merge, not off-entry. Observed-state5s right quadrature is a conditional estimate, not a rigorous time-varying supply bound. Only3Q is density-independent in this model. No capacity/parameter change or forecast.',
        model_source='Exact124 class equations92..95/109..119; effective runtime FD, not raw JSON values.'))
    print([(z['model'],z['arm'],z['native_total_admissions'],z['density_independent_max'],
        z['predicted_state_budget'],z['observed_state_right5s_budget']) for z in rows
        if z['case']=='s67_late' and z['start']==2820.1])


if __name__ == '__main__':
    main()
