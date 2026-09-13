"""Read only existing selected-frame caches; no FZP, model, or COM access."""
from collections import Counter
import csv
import gzip
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'diagnostics/startup_gui_three_arm_spatial_v1'
OUT = ROOT / 'diagnostics/lane_opportunity_4725'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def member(no, row, ref):
    return {'vehicle': no, 'pos_m': row[2], 'speed_kmh': row[3],
            'signed_position_difference_m': round(row[2] - ref, 8)}


def lane_detail(frame, lane, ref):
    rows = sorted(((no, r) for no, r in frame.items() if r[0] == 71 and r[1] == lane),
                  key=lambda item: (item[1][2], item[0]))
    ahead = [(no, r) for no, r in rows if r[2] >= ref]
    behind = [(no, r) for no, r in rows if r[2] < ref]
    return {'n': len(rows), 'stopped_n': sum(r[3] <= 1 for no, r in rows),
            'stopped_behind_n': sum(r[3] <= 1 for no, r in behind),
            'nearest_ahead': member(*ahead[0], ref) if ahead else None,
            'nearest_behind': member(*behind[-1], ref) if behind else None,
            'all': [member(no, r, ref) for no, r in reversed(rows)]}


def green(windows, key, sec):
    return any(a <= sec < b for a, b in windows[key])


def native_geometry(path):
    tree = ET.parse(path).getroot()
    selected = {}
    for e in tree.findall('.//links/link'):
        if e.get('no') not in ('10641', '10634', '10635', '71', '126'):
            continue
        row = {'attributes': dict(e.attrib), 'lanes': len(e.findall('./lanes/lane'))}
        for tag in ('fromLinkEndPt', 'toLinkEndPt'):
            node = e.find(tag)
            if node is not None:
                row[tag] = dict(node.attrib)
        selected[e.get('no')] = row
    assert selected['10641']['fromLinkEndPt']['lane'] == '126 1'
    assert selected['10641']['toLinkEndPt']['lane'] == '71 2'
    assert selected['10641']['lanes'] == 2
    assert selected['10635']['fromLinkEndPt']['lane'] == '71 4'
    assert selected['10635']['lanes'] == 2
    decision = next(e for e in tree.iter('vehicleRoutingDecisionStatic') if e.get('no') == '1126')
    route = next(e for e in decision.iter('vehicleRouteStatic') if e.get('no') == '1')
    path = [decision.get('link')] + [e.get('key') for e in route.findall('./linkSeq/intObjectRef')] + [route.get('destLink')]
    assert path == ['10643', '126', '10641', '71', '10635', '47']
    selected['route1126_1'] = {'decision_attributes': dict(decision.attrib),
                              'route_attributes': dict(route.attrib), 'ordered_path': path}
    return selected


def analyze(arm, pins):
    folder = SOURCE / arm / '900_1050'
    paths = [folder / name for name in ('diagnosis.json', 'summary.json',
                                       'arm_selected_frames.json.gz')]
    for p in paths:
        pins[str(p.relative_to(ROOT))] = sha(p)
    doc, summary = load(paths[0]), load(paths[1])
    assert sha(paths[2]) == doc['run']['fzp']['selected_cache_sha256'] == summary['cache_sha256']
    with gzip.open(paths[2], 'rt', encoding='utf-8') as f:
        frames = {int(t): {int(no): r for no, r in rows.items()} for t, rows in json.load(f).items()}
    assert sorted(frames) == list(range(900, 1051))
    assert all(len(r) == 4 for f in frames.values() for r in f.values())
    network = Path(doc['network_path'])
    pins[str(network.relative_to(ROOT))] = sha(network)
    assert sha(network) == doc['network_sha256']
    geo = native_geometry(network)
    signal = doc['run']['green_windows']
    blocker = next(r for r in summary['near_head_green_stopped_cohorts'] if r['vehicle'] == 4725)
    # Retain all inspected seconds, including the early approach and removal boundary.
    seconds = []
    for sec in range(915, 996):
        target = frames[sec].get(4725)
        ref = target[2] if target and target[0] == 71 else 73.39
        seconds.append({'sec': sec, 'target': target, 'reference_pos_m': ref,
                        'reference_is_target_position': bool(target and target[0] == 71),
                        'SG2_GREEN': green(signal, '1004:2', sec),
                        'SG5_GREEN': green(signal, '1004:5', sec),
                        'lanes': {str(lane): lane_detail(frames[sec], lane, ref) for lane in range(1, 6)}})
    assert all(frames[t].get(4725) == [71, 3, 73.39, 0.0] for t in range(929, 974))
    assert 4725 not in frames[974]
    transitions, lane_changes = [], []
    relevant = {71, 10641, 10634, 10635}
    for sec in range(901, 1051):
        old, new = frames[sec - 1], frames[sec]
        for no in sorted(set(old) | set(new)):
            a, b = old.get(no), new.get(no)
            if a and b and a[0] == b[0] == 71 and a[1] != b[1]:
                lane_changes.append({'vehicle': no, 'lower_sec': sec - 1, 'upper_sec': sec,
                                     'from_lane': a[1], 'to_lane': b[1], 'positions_m': [a[2], b[2]]})
            if ((a and a[0] in relevant) or (b and b[0] in relevant)) and (not a or not b or a[0] != b[0]):
                transitions.append({'vehicle': no, 'lower_sec': sec - 1, 'upper_sec': sec,
                                    'from': a, 'to': b,
                                    'absent_means': 'not in selected cache, not proof of global removal' if not a or not b else None})
    partitions = []
    for start, end in ((900, 929), (929, 969), (969, 974), (974, 992), (992, 1050)):
        rows = [r for r in transitions if start < r['upper_sec'] <= end]
        inflows = [r for r in rows if r['to'] and r['to'][0] == 71]
        exits = [r for r in rows if r['from'] and r['from'][0] == 71]
        changes = [r for r in lane_changes if start < r['upper_sec'] <= end]
        inventory = {}
        for lane in range(1, 6):
            first = sum(r[0] == 71 and r[1] == lane for r in frames[start].values())
            last = sum(r[0] == 71 and r[1] == lane for r in frames[end].values())
            entered = sum(r['to'][1] == lane for r in inflows)
            exited = sum(r['from'][1] == lane for r in exits)
            lateral_in = sum(r['to_lane'] == lane for r in changes)
            lateral_out = sum(r['from_lane'] == lane for r in changes)
            residual = first + entered - exited + lateral_in - lateral_out - last
            assert residual == 0
            inventory[str(lane)] = dict(initial=first, entered=entered, exited=exited,
                                         lateral_in=lateral_in, lateral_out=lateral_out, final=last, residual=residual)
        partitions.append({'window': [start, end], 'bracket_rule': 'start < upper_sec <= end',
                           'lane_stock_balance': inventory,
                           'road71_entries_by_from_and_lane': dict(Counter(
                               f"{r['from'][0] if r['from'] else 'outside-selected'}:lane{r['to'][1]}" for r in inflows)),
                           'road71_exits_by_lane_and_to': dict(Counter(
                               f"lane{r['from'][1]}:{r['to'][0] if r['to'] else 'absent-selected'}" for r in exits)),
                           'connector_landings': dict(Counter(
                               f"{r['from'][0]}->{r['to'][0]}" for r in rows
                               if r['from'] and r['to'] and r['from'][0] in (10634, 10635)))})
    return {'arm': arm, 'native_geometry': geo, 'head_geometry71': doc['head_geometry']['71'],
            'available71_distance_m': float(geo['10635']['fromLinkEndPt']['pos']) - float(geo['10641']['toLinkEndPt']['pos']),
            'green_windows': {key: signal[key] for key in ('1004:2', '1004:5')},
            'target_full_selected_track': [[t, *f[4725]] for t, f in frames.items() if 4725 in f],
            'prior_qualified_blocker': blocker, 'seconds': seconds,
            'transitions': transitions, 'lane_changes': lane_changes, 'partitions': partitions}


def main():
    pins = {str(Path(__file__).resolve().relative_to(ROOT)): sha(Path(__file__).resolve())}
    arms = [analyze(arm, pins) for arm in ('baseline', 'lcd10635_2000')]
    changes = [p for p, digest in pins.items() if sha(ROOT / p) != digest]
    assert not changes
    out = {'schema': '4725-selected-cache-lane-opportunity/v1', 'source_sha256': pins,
           'source_changes': changes, 'fzp_or_com_or_model_read': False,
           'cache_row_fields': ['link', 'lane', 'position_m', 'speed_kmh'],
           'definitions': {'stopped': 'sampled speed <= 1 km/h',
                           'position_difference': 'recorded POS difference; vehicle length/lateral position absent, not bumper clearance or accepted gap',
                           'lane_changes': 'same ID/link71 at consecutive 1s samples with different integer lane; timing is bracket only',
                           'queue': 'stopped counts by lane; not a calibrated causal queue or guaranteed service eligibility',
                           'removal': 'only prior explicit native ERR certificate proves global removal; selected-cache absence alone does not',
                           'comparability': 'same fixed written action, network change active from t0; no common OD/state/cohort counterfactual assumed'},
           'arms': arms}
    OUT.mkdir(exist_ok=True)
    (OUT / 'evidence.json').write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    with (OUT / 'lane_timeseries.csv').open('w', newline='', encoding='utf-8') as f:
        keys = ['arm', 'sec', 'target_link', 'target_lane', 'target_pos', 'target_speed',
                'SG2_GREEN', 'SG5_GREEN', 'lane', 'n', 'stopped_n', 'stopped_behind_n',
                'ahead_id', 'ahead_delta_m', 'ahead_speed', 'behind_id', 'behind_delta_m', 'behind_speed']
        writer = csv.DictWriter(f, fieldnames=keys); writer.writeheader()
        for arm in arms:
            for row in arm['seconds']:
                target = row['target'] or [None] * 4
                for lane, data in row['lanes'].items():
                    a, b = data['nearest_ahead'] or {}, data['nearest_behind'] or {}
                    writer.writerow(dict(zip(keys, [arm['arm'], row['sec'], *target, row['SG2_GREEN'], row['SG5_GREEN'],
                        lane, data['n'], data['stopped_n'], data['stopped_behind_n'],
                        a.get('vehicle'), a.get('signed_position_difference_m'), a.get('speed_kmh'),
                        b.get('vehicle'), b.get('signed_position_difference_m'), b.get('speed_kmh')])) )
    print(json.dumps({'output': str(OUT), 'source_changes': changes,
                      'arms': [{'arm': a['arm'], 'seconds': len(a['seconds']), 'stock_balance_pass': True} for a in arms]}))


if __name__ == '__main__':
    main()
