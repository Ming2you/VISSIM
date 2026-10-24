"""Audit the joint-lane sending/gap connection using completed148 records."""
import csv
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE = Path(__file__).resolve().parent


def main():
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    from evaluation.controllers.physical_ramp_boundary import gap_acceptance_supply_vph
    assert not (HERE/'audit.json').exists()
    pins = {}
    def read(p):
        pins[str(p)] = h.sha(p)
        return h.read(p)
    source = read(h.R/'spatial_context148/forecast/executed_function_sources.json')
    assert 'conflict_vph_per_lane' not in source['RouteLaneRegion']
    assert 'if lane_groups is not None:\n                            conflicting = lane_groups.conflict_vph_per_lane(ramp)' in source['rollout']
    bounds = read(h.F/'route_inventory/mapping31.json')['freeway_model_links']['FW_E']['segment_bounds_m']
    records = {r['arm']: r for r in common.records(False)}
    context, _, _ = common.setup()
    nodes = context['component'].ramp_receiving_nodes
    rows, ramp_windows = [], []
    for arm in ('release', 'release_vsl90'):
        trace = read(h.R/'transition150/replay'/f'corrected148_{arm}_trace.json.gz')
        states = {round(t['time_s'], 6): t for t in trace}
        pred = read(h.R/'spatial_context148/forecast/training'/f's67_late_{arm}.json.gz')
        fp = Path(records[arm]['truth'])/'ports_30s.csv'
        pins[str(fp)] = h.sha(fp)
        native = list(csv.DictReader(fp.open(encoding='utf-8-sig')))
        for r in pred['ramps']:
            ramp = r['ramp']
            if ramp not in ('RM_C10490', 'RM_C10484'): continue
            t = states[round(r['end_sec'], 6)]
            node = r['receiving_node']; upstream = 20 if ramp == 'RM_C10490' else 22
            n = t['lane_n']-t['off_n'] if upstream == 20 else t['n22_before']
            speed = t['old_speed'] if upstream == 20 else t['v22_before']
            length = (bounds[upstream+1]-bounds[upstream])/1000.
            conflict = n*min(1., speed/3600/length)*3600
            gap = gap_acceptance_supply_vph(conflict, nodes[ramp]['critical_gap_sec'], nodes[ramp]['followup_sec'])
            before_gap = node['unlimited_node_canonical_budget_vph']
            old_budget = min(before_gap, node['gap_supply_vph_per_lane'])/3600
            new_budget = min(before_gap, gap)/3600
            assert abs(old_budget-r['receiving_budget_veh']) < 1e-8
            # This is only the old-state local eligibility/resource comparison,
            # not a counterfactual autonomous accepted merge or gain estimate.
            eligible = r['eligible_merge_veh']
            rows.append(dict(arm=arm, ramp=ramp, time_s=r['end_sec'],
                upstream=upstream, lane=1, current_through_n=n, current_lane_speed=speed,
                old_conflict=node['conflicting_vph_per_lane'], current_lane_conflict=conflict,
                old_budget=old_budget, candidate_same_state_budget=new_budget,
                eligible=eligible, old_accepted=r['accepted_merge_veh'],
                candidate_same_state_eligible_cap=min(eligible, new_budget)))
        for connector in sorted({r['start']['connector_id'] for r in pred['ramps']}):
            for lo, hi in ((2670.1, 2700.1), (2670.1, 2820.1), (2820.1, 2970.1), (2970.1, 3120.1)):
                a = [x for x in native if x['connector'] == connector and lo+1e-6 < float(x['window_end_s']) <= hi+1e-6]
                p = [x for x in pred['ramps'] if x['start']['connector_id'] == connector and lo+1e-6 < x['end_sec'] <= hi+1e-6]
                truth = dict(start_n=float(a[0]['start_n_veh']), end_n=float(a[-1]['end_n_veh']),
                    arrivals=sum(float(x['arrivals_veh']) for x in a), merges=sum(float(x['departures_veh']) for x in a),
                    unresolved=sum(float(x['unresolved_absences_veh']) for x in a))
                assert truth['unresolved'] == 0
                assert abs(truth['start_n']+truth['arrivals']-truth['merges']-truth['end_n']) < 1e-8
                forecast = dict(start_n=p[0]['start']['connector_veh'], end_n=p[-1]['end']['connector_veh'],
                    arrivals=sum(x['admitted_arrivals_veh'] for x in p), merges=sum(x['accepted_merge_veh'] for x in p),
                    head_service=sum(x['head_service_veh'] for x in p), merge_ready_arrivals=sum(x['arrived_at_merge_veh'] for x in p))
                assert abs(forecast['start_n']+forecast['arrivals']-forecast['merges']-forecast['end_n']) < 1e-7
                ramp_windows.append(dict(arm=arm, connector=connector, lo=lo, hi=hi, actual=truth, predicted=forecast))
    groups = []
    for arm in ('release', 'release_vsl90'):
        for ramp in ('RM_C10490', 'RM_C10484'):
            z = [x for x in rows if x['arm'] == arm and x['ramp'] == ramp]
            assert len(z) == 450
            groups.append(dict(arm=arm, ramp=ramp, budget_changed_seconds=sum(abs(x['candidate_same_state_budget']-x['old_budget'])>1e-9 for x in z),
                eligible_cap_change_sum=sum(x['candidate_same_state_eligible_cap']-min(x['eligible'], x['old_budget']) for x in z),
                first=z[0]))
    protected = read(h.R/'transition150/replay/protocol.json')
    for p, digest in {**pins, **protected['protected_sha256']}.items(): assert h.sha(p) == digest, p
    assert h.sha(protected['STOP']['path']) == protected['STOP']['sha256']
    h.save(HERE/'audit.json', dict(groups=groups, ramp_windows=ramp_windows,
        connection_mismatch=True, budget='Cached audit only;no new forecasts or coefficients',
        interpretation='Joint route lanes drive mass/receiving but old rollout gap uses all-lane mean and historical exit ratio. Local budget comparison is not autonomous actual merge or TTT response. A lane sending request is not an observed gap process.',
        initial_arrival_timing_prior='103 and earlier posthead/head timing reviewed;do not repeat or adopt those rejected candidates.'))
    h.save(HERE/'audit_rows.json', rows)
    h.save(HERE/'pins.json', pins)
    for x in groups: print(x)


if __name__ == '__main__': main()
