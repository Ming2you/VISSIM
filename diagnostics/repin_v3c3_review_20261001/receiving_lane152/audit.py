"""Separate lane21 receiving closure from its autonomous state errors.

Cached endpoint movements are labels, never autonomous rollout inputs.
"""
import collections
import csv
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE = Path(__file__).resolve().parent


def main():
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    from evaluation.controllers import lane_plant_runtime as lpr
    assert not (HERE/'assessment.json').exists(), 'Preserve completed diagnostic'
    context, _, _ = common.setup()
    protected = h.read(h.R/'transition150/replay/protocol.json')
    pins = dict(protected['protected_sha256'])
    def read(path):
        pins[str(path)] = h.sha(path)
        return h.read(path)
    manifest = h.R/'lane_state132/eval_01/manifest.json'
    read(manifest)
    cfg = lpr.load_sources(manifest)['component']._config('FW_E', context['parameters']['by_direction']['FW_E'])
    fd = cfg.network.freeway_segment_params['FW_E'][21]
    length, jam, critical = fd['segment_length_km'], cfg.network.rho_max, fd['rho_crit']
    capacity = critical*fd['v_free']*math.exp(-1/fd['metanet_a_m'])
    wave = capacity/(jam-critical)
    def supply(n):
        return min(max(0., jam*length-n), max(0., min(capacity, wave*(jam-n/length)))/3600)
    h.save(HERE/'protocol.json', dict(
        previous_goal_turn='NO_PROGRESS: prior response explained151 without new work. Current live process check empty.',
        question='132 aggregate receiving check may hide lane1 mismatch. Compare measured lane states, endpoint lane movements and corrected148 autonomous supply on the same450s.',
        prior_checked=['Claude P_PLANT FIFO and per-lane distinction', '124 shared receiving', '132 receiving_check aggregate only', '135 cap removal failed', '148 corrected context', '150/151 first30 lane budget'],
        budget=dict(new_forecasts=0, fits=0, native=0, FZP=0, full_run_analysis=0),
        interpretation='Observed-state receiving is conditional5s quadrature, not a rigorous continuous-time bound. Stable endpoint lanes cannot rule out lane-change-and-return within5s. Label ambiguity explicitly. No future inputs to a forecast.',
        constraints='No coefficient/physics changes, capacity bonus, repeated grid, production adoption or push.',
        protected_sha256=protected['protected_sha256'], STOP=protected['STOP']))
    events = read(h.F/'merge_speed_audit/events.json')
    records = {r['arm']: r for r in common.records(False)}
    rows, steps, witnesses = [], [], []
    for arm in ('release', 'release_vsl90'):
        document = read(h.F/'flow67'/f'{arm}_frames.json.gz')
        fields = document['fields']
        frames = {round(float(t), 6): {int(k): dict(zip(fields, v)) for k, v in data.items()}
                  for t, data in document['frames'].items()}
        times = sorted(frames)
        assert len(times) == 91 and times[0] == 2670.1 and times[-1] == 3120.1
        trace = read(h.R/'transition150/replay'/f'corrected148_{arm}_trace.json.gz')
        flowfile = Path(records[arm]['truth'])/'flows_30s.csv'
        pins[str(flowfile)] = h.sha(flowfile)
        truth = list(csv.DictReader(flowfile.open(encoding='utf-8-sig')))
        merges = [e for e in events if e['arm'] == arm and e['ramp'] == 'RM_C10490']
        for lo, hi in zip(times, times[1:]):
            a, b = frames[lo], frames[hi]
            crossing = [v for v in a.keys() & b.keys() if a[v]['cell'] <= 20 < b[v]['cell']]
            stable = collections.Counter(a[v]['lane'] for v in crossing if a[v]['lane'] == b[v]['lane'])
            ambiguous = [v for v in crossing if a[v]['lane'] != b[v]['lane']]
            merged = [e for e in merges if abs(e['lo']-lo) < 1e-6 and abs(e['hi']-hi) < 1e-6]
            # All10490 vehicles enter physical lane1; post-entry lane changes
            # do not change the receiving lane used by the actual node.
            mm = len(merged)
            for lane in (1, 2, 3):
                current = [v for v in a.values() if v['cell'] == 21 and v['lane'] == lane]
                future = [v for v in b.values() if v['cell'] == 21 and v['lane'] == lane]
                item = dict(arm=arm, lo=lo, hi=hi, lane=lane, n0=len(current), n1=len(future),
                    current_v=sum(v['speed_kmh'] for v in current)/len(current) if current else None,
                    stable_endpoint_through=stable[lane], ambiguous_endpoint_through=len(ambiguous),
                    physical_merge=mm if lane == 1 else 0,
                    supply_left5=supply(len(current))*5,
                    supply_trapezoid5=(supply(len(current))+supply(len(future)))*2.5,
                    density_independent_capacity5=capacity*5/3600)
                if lane == 1:
                    z = [x for x in trace if lo+1e-6 < x['time_s'] <= hi+1e-6]
                    assert len(z) == 5
                    item.update(predicted_supply=sum(x['receiving_before_merge'] for x in z),
                        predicted_admissions=sum(x['accepted_through']+x['accepted_merge'] for x in z),
                        predicted_mean_n=sum(x['downstream_lane_n'] for x in z)/5)
                steps.append(item)
            witnesses.extend(dict(arm=arm, lo=lo, vehicle=v, before=a[v], after=b[v]) for v in ambiguous)
        for start, end in ((2670.1, 2700.1), (2670.1, 2820.1), (2820.1, 2970.1), (2970.1, 3120.1)):
            native = [x for x in truth if x['road'] == 'FW_E' and int(x['cell']) == 21
                      and start+1e-6 < float(x['window_end_s']) <= end+1e-6]
            actual_through = sum(float(x['upstream_crossings']) for x in native)
            actual_merge = sum(float(x['ramp_merges']) for x in native)
            scope = [x for x in steps if x['arm'] == arm and start-1e-6 <= x['lo'] < end-1e-6]
            known_through = sum(x['stable_endpoint_through'] for x in scope)
            ambiguous = sum(x['ambiguous_endpoint_through'] for x in scope if x['lane'] == 1)
            known_merge = sum(x['physical_merge'] for x in scope)
            assert known_through+ambiguous == actual_through, (arm, start, known_through, ambiguous, actual_through)
            assert known_merge == actual_merge, (arm, start, known_merge, actual_merge)
            for lane in (1, 2, 3):
                z = [x for x in scope if x['lane'] == lane]
                values = {k: sum(x[k] for x in z) for k in ('stable_endpoint_through', 'physical_merge', 'supply_left5', 'supply_trapezoid5', 'density_independent_capacity5')}
                values.update(stable_endpoint_admissions=values['stable_endpoint_through']+values['physical_merge'],
                              lane_assignment_ambiguous=ambiguous)
                if lane == 1:
                    values.update({k: sum(x[k] for x in z) for k in ('predicted_supply', 'predicted_admissions')})
                rows.append(dict(arm=arm, start=start, end=end, lane=lane,
                    observed_mean_n=sum(x['n0'] for x in z)/len(z), **values))
    for p, digest in pins.items():
        assert h.sha(p) == digest, p
    assert h.sha(protected['STOP']['path']) == protected['STOP']['sha256']
    h.save(HERE/'assessment.json', dict(status='complete_cached_lane_receiving_diagnostic',
        fd=fd, capacity_vph_per_lane=capacity, wave_kmh=wave, rows=rows,
        all_total_endpoint_crossings_and_merges_match_native_csv=True,
        predictions=0, coefficient_changes=0, production_adoption=False, goal_complete=False))
    h.save(HERE/'steps.json', steps)
    h.save(HERE/'ambiguous_endpoint_lanes.json', witnesses)
    h.save(HERE/'pins.json', pins)
    for x in rows:
        if x['lane'] == 1: print(x)


def lane_balance():
    """Bracket boundary-lane assignment; do not call endpoint lanes exact."""
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    assert not (HERE/'lane_balance.json').exists()
    pins = h.read(HERE/'pins.json')
    def read(p):
        pins[str(p)] = h.sha(p)
        return h.read(p)
    events = read(h.F/'merge_speed_audit/events.json')
    records = {r['arm']: r for r in common.records(False)}
    allrows = []
    for arm in ('release', 'release_vsl90'):
        doc = read(h.F/'flow67'/f'{arm}_frames.json.gz')
        frames = {round(float(t), 6): {int(k): dict(zip(doc['fields'], v)) for k, v in f.items()}
                  for t, f in doc['frames'].items()}
        times = sorted(frames)
        flowfile = Path(records[arm]['truth'])/'flows_30s.csv'
        pins[str(flowfile)] = h.sha(flowfile)
        truth = list(csv.DictReader(flowfile.open(encoding='utf-8-sig')))
        native = []
        for lo, hi in zip(times, times[1:]):
            a, b = frames[lo], frames[hi]
            merges = [e for e in events if e['arm'] == arm and e['ramp'] == 'RM_C10490'
                      and abs(e['lo']-lo) < 1e-6 and abs(e['hi']-hi) < 1e-6]
            common_ids = a.keys() & b.keys()
            inc = [(a[v]['lane'], b[v]['lane']) for v in common_ids if a[v]['cell'] <= 20 < b[v]['cell']]
            out = [(a[v]['lane'], b[v]['lane']) for v in common_ids if a[v]['cell'] <= 21 < b[v]['cell']]
            for e in merges:
                v = int(e['vehicle'])
                assert v in b and v not in a
                assert b[v]['cell'] >= 21
                if b[v]['cell'] > 21: out.append((1, b[v]['lane']))
            def counts(pairs):
                stable = sum(x == y == 1 for x, y in pairs)
                ambiguous = sum(x != y and 1 in (x, y) for x, y in pairs)
                return stable, ambiguous
            ii, ia = counts(inc); oo, oa = counts(out)
            stay = [(a[v]['lane'], b[v]['lane']) for v in common_ids if a[v]['cell'] == b[v]['cell'] == 21]
            lateral = sum(y == 1 and x != 1 for x, y in stay)-sum(x == 1 and y != 1 for x, y in stay)
            native.append(dict(lo=lo, hi=hi,
                n0=sum(v['cell'] == 21 and v['lane'] == 1 for v in a.values()),
                n1=sum(v['cell'] == 21 and v['lane'] == 1 for v in b.values()),
                incoming_stable=ii, incoming_ambiguous=ia, outgoing_stable=oo, outgoing_ambiguous=oa,
                total_incoming=len(inc), total_outgoing=len(out), merge=len(merges),
                same_cell_lateral_net=lateral))
        pred = read(h.R/'spatial_context148/forecast/training'/f's67_late_{arm}.json.gz')
        model = [x for x in pred['diagnostics']['roads'][0]['joint_lane_region']['rows'] if x['cell'] == 21 and x['lane'] == 1]
        n0 = sum(v['cell'] == 21 and v['lane'] == 1 for v in frames[times[0]].values())
        prev = n0
        for x in model:
            x['n_before'] = prev
            x['lateral_net'] = x['n_veh']-prev-x['mainline_in_veh']-x['merge_veh']+x['mainline_out_veh']
            prev = x['n_veh']
        for lo, hi in ((2670.1, 2700.1), (2670.1, 2820.1), (2820.1, 2970.1), (2970.1, 3120.1)):
            z = [x for x in native if lo-1e-6 <= x['lo'] < hi-1e-6]
            t = [x for x in truth if x['road'] == 'FW_E' and int(x['cell']) == 21
                 and lo+1e-6 < float(x['window_end_s']) <= hi+1e-6]
            actual = {k: sum(x[k] for x in z) for k in z[0] if k not in ('lo', 'hi', 'n0', 'n1')}
            for label, field in [('total_incoming', 'upstream_crossings'), ('total_outgoing', 'downstream_crossings'), ('merge', 'ramp_merges')]:
                assert actual[label] == sum(float(x[field]) for x in t), (arm, lo, label, actual[label], sum(float(x[field]) for x in t))
            actual.update(n_start=z[0]['n0'], n_end=z[-1]['n1'])
            delta = actual['n_end']-actual['n_start']
            lower = delta-actual['incoming_stable']-actual['incoming_ambiguous']-actual['merge']+actual['outgoing_stable']
            upper = delta-actual['incoming_stable']-actual['merge']+actual['outgoing_stable']+actual['outgoing_ambiguous']
            actual['lateral_net_endpoint_envelope'] = [lower, upper]
            m = [x for x in model if lo+1e-6 < x['time_s'] <= hi+1e-6]
            predicted = {k: sum(x[k] for x in m) for k in ('mainline_in_veh', 'mainline_out_veh', 'merge_veh', 'lateral_net')}
            predicted.update(n_start=m[0]['n_before'], n_end=m[-1]['n_veh'])
            assert abs(predicted['n_end']-predicted['n_start']-predicted['mainline_in_veh']-predicted['merge_veh']+predicted['mainline_out_veh']-predicted['lateral_net']) < 1e-8
            allrows.append(dict(arm=arm, start=lo, end=hi, actual=actual, predicted=predicted))
    for p, digest in pins.items(): assert h.sha(p) == digest, p
    h.save(HERE/'lane_balance.json', dict(rows=allrows,
        meaning='Native totals exactly match30s CSV. Lane envelopes allow a boundary lane to equal either observed endpoint lane. They cannot exclude unobserved multiple lane changes within5s, and are not exact microscopic lane flows. Same-cell net alone is not total lane exchange.',
        new_forecasts=0, input_sha256=pins))
    for x in allrows: print(x)


if __name__ == '__main__':
    import sys
    lane_balance() if '--balance' in sys.argv else main()
