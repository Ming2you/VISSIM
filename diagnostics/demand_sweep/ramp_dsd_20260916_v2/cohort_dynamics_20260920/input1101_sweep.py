"""Bounded input1101 experiment, using the existing native runner/extractor."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import shutil
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
from diagnostics.fast_fixed_profile import prepare
from diagnostics.capture_native_runtime_errors import parse_bytes

OUT = HERE / 'input1101_sweep_v1'
BASE = HERE / 'native_v1/none_s23'


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def prepare_cases():
    OUT.mkdir(exist_ok=False)
    source = BASE / 'source/baseline.inpx'
    source_bytes = source.read_bytes()
    reference = ET.fromstring(source_bytes)
    inputs = reference.findall('./vehicleInputs/vehicleInput')
    selected = [n for n in inputs if n.get('no') == '1101']
    assert len(selected) == 1 and selected[0].get('link') == '69'
    timetable = selected[0].findall('./timeIntVehVols/timeIntervalVehVolume')
    assert len(timetable) == 6
    decisions = {n.get('no'): n for n in reference.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic')}
    for decision, destinations, weights in [
        ('1134', ['120', '75', '2', '10640'], ['2 0:3', '2 0:3', '2 0:3', '']),
        ('1138', ['47', '56', '67'], ['', '', '']),
    ]:
        routes = decisions[decision].findall('./vehRoutSta/vehicleRouteStatic')
        assert [r.get('destLink') for r in routes] == destinations
        assert [r.get('relFlow') for r in routes] == weights
    baseline_receipt = json.loads((BASE / 'run/run.json').read_text(encoding='utf-8-sig'))
    assert baseline_receipt['completed'] and baseline_receipt['terminal_sec'] == 3000
    audit = {'source': str(source), 'source_sha256': hashlib.sha256(source_bytes).hexdigest(),
             'baseline_run': str(BASE / 'run'), 'seed': 23, 'terminal_s': 3000,
             'changed': 'Only six input1101 volume attributes; all other XML attributes/children unchanged',
             'scope': 'Whole input1101 reduction, including FW_W/FW_E/through/71 destinations; not destination-isolated',
             'cases': {}}
    demand_rows = []
    for label, factor in [('baseline', 1.0), ('p90', .9), ('p80', .8)]:
        for v in timetable:
            q = float(v.get('volume')) * factor
            demand_rows.append({'case': label, 'interval_start_s': int(v.get('timeInt').split()[1]) / 1000,
                                'input1101_vph': q, 'FW_W_vph': q * .3, 'FW_E_vph': q * .3,
                                'through75_vph': q * .3, 'via71_total_vph': q * .1,
                                'via71_left_vph': q / 30, 'via71_straight_vph': q / 30,
                                'via71_right_vph': q / 30})
        if label == 'baseline':
            continue
        folder = OUT / label
        target = folder / 'source'
        target.mkdir(parents=True)
        root = ET.fromstring(source_bytes)
        inp = next(n for n in root.findall('./vehicleInputs/vehicleInput') if n.get('no') == '1101')
        volumes = inp.findall('./timeIntVehVols/timeIntervalVehVolume')
        for old, new in zip(timetable, volumes):
            new.set('volume', format(float(old.get('volume')) * factor, '.10g'))
        network = target / 'baseline.inpx'
        network.write_bytes(b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding='utf-8'))
        # Restoring the six values must restore the entire original XML tree.
        for old, new in zip(timetable, volumes):
            new.set('volume', old.get('volume'))
        assert ET.tostring(root) == ET.tostring(reference)
        for name in {v[6:] for n in reference.iter() for v in n.attrib.values() if v.startswith('#data#')}:
            assert Path(name).name == name
            shutil.copy2(source.parent / name, target / name)
        profile = json.loads((BASE / 'profile.json').read_text(encoding='utf-8-sig'))
        assert not profile['meter_commands'] and not profile['vsl_commands']
        profile['network_sha256'] = hashlib.sha256(network.read_bytes()).hexdigest()
        save(folder / 'profile.json', profile)
        meta = prepare(network, folder / 'profile.json', folder / 'prepared')
        assert meta['command_rows'] == 0 and meta['demand_rows'] == 0
        audit['cases'][label] = {'input_factor': factor, 'network_sha256': profile['network_sha256'],
                                 'only_six_volume_changes': True}
    assert source.read_bytes() == source_bytes
    save(OUT / 'preparation.json', audit)
    with (OUT / 'configured_demand.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(demand_rows[0]))
        writer.writeheader()
        writer.writerows(demand_rows)
    print(json.dumps(audit, ensure_ascii=False), flush=True)


def analyze_cases():
    from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.urban_drain import extract
    out = OUT / 'analysis'
    out.mkdir(exist_ok=False)
    summary = {}
    for label in ['baseline', 'p90', 'p80']:
        run = BASE / 'run' if label == 'baseline' else OUT / label / 'run'
        rows, proof = extract(run, start=1800, end=3000)
        save(out / (label + '_evidence.json'), proof)
        with (out / (label + '.csv')).open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        runtime = parse_bytes((run / 'baseline_001.err').read_bytes())
        save(out / (label + '_runtime_errors.json'), runtime)
        assert not runtime['unparsed_removal_lines']
        case = {'runtime_counts_entire_run': runtime['counts'], 'windows': {}}
        for start, end in [(1800, 2850), (2400, 2850), (2400, 3000)]:
            w = [r for r in rows if start <= r['time_s'] < end]
            groups = {}
            for name, prefix, lanes in [('link71', 'urban_sg', (2, 5)), ('off10643', 'off_lane', (1, 2))]:
                initial = sum(w[0][f'{prefix}{g}_n'] for g in lanes)
                flows = {kind: sum(r.get(f'{prefix}{g}_{kind}', 0) for r in w for g in lanes)
                         for kind in ['arrivals', 'departures', 'removals']}
                stock = [sum(r[f'{prefix}{g}_n'] for g in lanes) for r in w]
                stopped = [sum(r[f'{prefix}{g}_stopped'] for g in lanes) for r in w]
                groups[name] = {**flows, 'initial_n': initial,
                    'end_n': initial + flows['arrivals'] - flows['departures'] - flows['removals'],
                    'mean_n': sum(stock) / len(w), 'max_n': max(stock),
                    'mean_stopped_n': sum(stopped) / len(w),
                    'local_ttt_veh_h': sum(stock) / 3600,
                    'abnormal_loss_pct_of_visits': 100 * flows['removals'] / (initial + flows['arrivals'])}
            case['windows'][f'{start}-{end}'] = groups
        summary[label] = case
        print(label, json.dumps(case['windows']['1800-2850']), flush=True)
    save(out / 'summary.json', summary)


def analyze_origins():
    from collections import Counter, defaultdict
    source = ET.parse(BASE / 'source/baseline.inpx').getroot()
    source_links = defaultdict(list)
    for node in source.findall('./vehicleInputs/vehicleInput'):
        source_links[int(node.get('link'))].append(int(node.get('no')))
    results = {}
    for case in ['baseline', 'p90', 'p80']:
        run = BASE / 'run' if case == 'baseline' else OUT / case / 'run'
        origin, previous = {}, {}
        visits, off_visits = Counter(), Counter()
        active = False
        with (run / 'vissim_eval/baseline_001.fzp').open('rb') as stream:
            for line in stream:
                if not active:
                    active = line.startswith(b'$VEHICLE:')
                    continue
                p = line.split(b';', 3)
                if len(p) < 4:
                    continue
                t = float(p[0])
                if t > 2850:
                    break
                vid, link = int(p[1]), int(p[2])
                origin.setdefault(vid, link)
                old = previous.get(vid)
                if 1800 <= t <= 2850:
                    if link == 71 and (t == 1800 or old != 71):
                        visits[origin[vid]] += 1
                    if link == 10643 and (t == 1800 or old != 10643):
                        off_visits[origin[vid]] += 1
                previous[vid] = link
        runtime = json.loads((OUT / f'analysis/{case}_runtime_errors.json').read_text(encoding='utf-8-sig'))
        results[case] = {
            'scope': '1800-frame vehicles plus entries through2850, visits include returns; first native link used to identify source',
            'link71_visits': [{'first_link': k, 'vehicle_inputs': source_links.get(k, []), 'visits': n} for k, n in visits.most_common()],
            'off10643_visits': [{'first_link': k, 'vehicle_inputs': source_links.get(k, []), 'visits': n} for k, n in off_visits.most_common()],
            'input_remainders': [{'input': r['input_no'], 'remaining': r['remaining_vehicles']} for r in runtime['events'] if r['kind'] == 'unfinished_vehicle_input'],
            'warnings': runtime['counts'],
        }
        print(case, sum(visits.values()), flush=True)
    save(OUT / 'analysis/observed_origins.json', results)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'analyze', 'origins'])
    args = parser.parse_args()
    {'prepare': prepare_cases, 'analyze': analyze_cases, 'origins': analyze_origins}[args.action]()
