"""Literal native interaction labels and matched vehicle responses; no fitting."""
import collections
import gzip
import hashlib
import json
import math
from pathlib import Path

A = Path(__file__).resolve().parent
H = A.parent
O = A / 'interaction_response'
PINS = {}


def read(path):
    raw = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def describe(values):
    if not values:
        return dict(n=0)
    x = sorted(values)
    q = lambda p: x[round((len(x) - 1) * p)]
    return dict(n=len(x), mean=math.fsum(x) / len(x), median=q(.5), p10=q(.1), p90=q(.9),
                unchanged=sum(abs(v) < 1e-8 for v in x))


def main():
    assert not (O / 'assessment.json').exists()
    done = read(O / 'completion.json')
    cases = {case: read(O / (case + '_records.json.gz')) for case in ('hold', 'single90', 'selected')}
    by_case = {case: {(r[0], r[1]): r for r in doc['rows']} for case, doc in cases.items()}
    base = by_case['hold']
    prefixes = {}
    for case, data in by_case.items():
        prefixes[case] = all({key: row for key, row in data.items() if key[0] == t}
                             == {key: row for key, row in base.items() if key[0] == t} for t in (2240.1, 2245.1))
    assert all(prefixes.values())
    distributions = []
    for case, doc in cases.items():
        for lo, hi, region in ((14, 18, 'approach'), (19, 25, 'bottleneck')):
            for block in range(3):
                rows = [r for r in doc['rows'] if lo <= r[2] <= hi and 2250 + 150 * block <= r[0] < 2400 + 150 * block]
                classes = collections.Counter(r[8] for r in rows)
                constrained = [r for r in rows if r[8] != 'Free']
                distributions.append(dict(case=case, region=region, block=block, samples=len(rows),
                    states=dict(classes), free_fraction=classes['Free'] / len(rows),
                    speed=describe([r[5] for r in rows]), desired=describe([r[6] for r in rows]),
                    acceleration=describe([r[7] for r in rows]),
                    constrained_desired_minus_speed=describe([r[6] - r[5] for r in constrained])))
    matches = []
    detail = []
    for case in ('single90', 'selected'):
        groups = collections.defaultdict(list)
        first = {}
        data = by_case[case]
        for key, r in sorted(data.items()):
            if r[0] < 2250 or key not in base:
                continue
            b = base[key]
            if r[6] >= b[6] - 5:
                continue
            # Only the first observed desired-speed reduction per vehicle.
            if r[1] in first:
                continue
            first[r[1]] = key
            prior_key = (round(r[0] - 5, 1), r[1])
            before = base.get(prior_key)
            other_before = data.get(prior_key)
            pre_identical = before is not None and other_before is not None and before == other_before
            same_target = b[9:11] == r[9:11]
            similar = b[2:4] == r[2:4] and abs(b[4] - r[4]) <= .5 and abs(b[5] - r[5]) <= .5 and same_target
            record = dict(case=case, time=r[0], vehicle=r[1], cell=r[2],
                base_state=b[8], selected_state=r[8], pre_state=before[8] if before else None,
                pre_identical=pre_identical, similar_instant_state=similar,
                speed_delta=r[5] - b[5], desired_delta=r[6] - b[6], acceleration_delta=r[7] - b[7],
                position_delta=r[4] - b[4], same_target=same_target,
                base_speed=b[5], selected_desired=r[6], base_acceleration=b[7], selected_acceleration=r[7])
            detail.append(record)
            groups['all_first_exposures'].append(record)
            if pre_identical:
                groups['identical_previous_observation'].append(record)
            if similar:
                groups['similar_current_observation'].append(record)
                groups['similar_current_' + b[8]].append(record)
            if r[0] == 2250.1:
                groups['first_native_frame_' + b[8]].append(record)
        for group, rows in groups.items():
            matches.append(dict(case=case, group=group, n=len(rows),
                acceleration_delta=describe([r['acceleration_delta'] for r in rows]),
                desired_delta=describe([r['desired_delta'] for r in rows]),
                speed_delta=describe([r['speed_delta'] for r in rows])))
    resources = []
    for case, path in [('hold', H / 'matched_off2250_v3/hold_response.json.gz'),
                       ('single90', H / 'matched_off2250_v3/single90_response.json.gz'),
                       ('selected', H / 'matched_off2250_v3/selected_response.json.gz'),
                       ('refined_boundary_selected', A / 'refine_boundary_fit/development_selected_response.json.gz')]:
        response = read(path)
        for cell in range(14, 26):
            for block in range(3):
                rows = [r for r in response['resource_allocations'] if r['kind'] == 'freeway_mainline_sending'
                        and r['resource'] == f'FW_E:cell:{cell}' and 2250 + block * 150 <= r['start_sec'] < 2400 + block * 150]
                assert abs(sum(r['end_sec'] - r['start_sec'] for r in rows) - 150) < 1e-7
                offered = math.fsum(r['available_veh'] for r in rows)
                accepted = math.fsum(r['accepted_total_veh'] for r in rows)
                resources.append(dict(case=case, cell=cell, block=block, offered=offered, accepted=accepted,
                    unmet=offered - accepted,
                    restricted_seconds=math.fsum(r['end_sec'] - r['start_sec'] for r in rows if r['available_veh'] - r['accepted_total_veh'] > 1e-8)))
    output = dict(status='complete_new_interaction_and_sending_audit', prefix_frames_identical=prefixes,
        distributions=distributions, first_exposure_matches=matches, resources=resources,
        new_native=0, new_forecasts=0, fits=0, production_edits=0,
        limitations=[
            'Five-second samples are correlated within vehicles; sample counts are not independent experiments.',
            'Free/Follow/Brake labels are recorded native states, not inferred from a speed threshold.',
            'A matched vehicle is not a controlled microscopic counterfactual after leaders/gaps diverge.',
            'Similar-current-state filters are descriptive and condition on post-intervention quantities.',
            'No causal coefficient or universal suppression rule is identified by this comparison.',
            'Resource availability is a model request; no restriction means the receiving constraint did not reduce it, not that native capacity is unlimited.',
        ], source_pins=PINS)
    (O / 'first_exposures.json').write_text(json.dumps(detail, indent=2, allow_nan=False) + '\n', encoding='utf8')
    (O / 'assessment.json').write_text(json.dumps(output, indent=2, allow_nan=False) + '\n', encoding='utf8')
    print(json.dumps(dict(prefix=prefixes, matches=matches,
                         cell18=[r for r in resources if r['cell'] == 18]), indent=2))


if __name__ == '__main__':
    main()
