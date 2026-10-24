"""Read native XML and retained 150s frames only; never run or edit a model."""
from __future__ import annotations

import gzip
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NETWORK = ROOT / 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx'
EVIDENCE = ROOT / 'diagnostics/sc1004_first_control_window'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def length(link):
    pts = [(float(p.get('x')), float(p.get('y')))
           for p in link.findall('./geometry/linkPolyPts/linkPolyPoint')]
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def endpoint(link, name):
    e = link.find(name)
    if e is None:
        return None
    road, lane = e.get('lane').split()
    count = len(link.findall('./lanes/lane'))
    return {'link': road, 'lanes': list(range(int(lane), int(lane) + count)),
            'position_m': float(e.get('pos')), 'exact_xml_attributes': dict(e.attrib)}


def main():
    followup_path = EVIDENCE / 'followup_evidence.json'
    followup = json.loads(followup_path.read_text(encoding='utf-8'))
    err_path = Path(followup['native_removal4725']['source_path'])
    inputs = [NETWORK, followup_path, err_path,
              EVIDENCE / 'NC_selected_frames.json.gz',
              EVIDENCE / 'beta300_selected_frames.json.gz']
    before = {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in inputs}
    if sha(NETWORK) != followup['native_removal4725']['network_sha256']:
        raise ValueError('Native network differs from retained trajectory investigation')
    if sha(err_path) != followup['native_removal4725']['sha256']:
        raise ValueError('Original removal warning evidence changed')
    tree = ET.fromstring(NETWORK.read_bytes())
    links = {x.get('no'): x for x in tree.findall('./links/link')}
    selected = {'71', '47', '126', '10643', '10641', '10635'}
    selected.update(no for no, x in links.items()
                    if any(e is not None and e.get('lane').split()[0] == '71'
                           for e in (x.find('fromLinkEndPt'), x.find('toLinkEndPt'))))
    rows = []
    for no in sorted(selected, key=int):
        x = links[no]
        rows.append({'link': no, 'connector': x.find('fromLinkEndPt') is not None,
                     'exact_xml_attributes': dict(x.attrib), 'length2d_m': length(x),
                     'from': endpoint(x, 'fromLinkEndPt'), 'to': endpoint(x, 'toLinkEndPt'),
                     'lanes': [dict(v.attrib) for v in x.findall('./lanes/lane')]})
    routes = []
    for dec in tree.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic'):
        for route in dec.findall('./vehRoutSta/vehicleRouteStatic'):
            path = [dec.get('link')] + [r.get('key') for r in route.findall('./linkSeq/intObjectRef')] + [route.get('destLink')]
            if '10635' in path:
                routes.append({'decision': dict(dec.attrib), 'route': dict(route.attrib), 'ordered_path': path})
    heads = [dict(x.attrib) for x in tree.findall('./signalHeads/signalHead')
             if x.get('lane', '').startswith('71 ')]
    behavior = tree.find("./drivingBehaviors/drivingBehavior[@no='1']")
    behavior_type = tree.find("./linkBehaviorTypes/linkBehaviorType[@no='1']")
    if behavior is None or behavior_type is None:
        raise ValueError('Missing source driving behavior binding')
    path_lengths = [
        {'part': '10643 after decision1126', 'distance_m': length(links['10643']) - 23.341404233217531},
        {'part': '126 between connector endpoints', 'distance_m': 152.45634914466157 - 150.20880571595106},
        {'part': '10641', 'distance_m': length(links['10641'])},
        {'part': '71 before10635', 'distance_m': 80.886394942347508 - 3.195594170544656},
    ]
    observations = {}
    for arm in ('NC', 'beta300'):
        with gzip.open(EVIDENCE / f'{arm}_selected_frames.json.gz', 'rt', encoding='utf-8') as stream:
            frames = json.load(stream)
        observations[arm] = {}
        for vehicle in ('4725', '4387'):
            samples = [[int(t), *frame[vehicle]] for t, frame in frames.items() if vehicle in frame]
            samples.sort()
            events, previous = [], None
            for row in samples:
                key = (row[1], row[2], row[4] == 0.0)
                if key != previous:
                    events.append(row)
                    previous = key
            observations[arm][vehicle] = {'sample_fields': ['sec', 'link', 'lane', 'pos_m', 'speed_kph'],
                                         'first': samples[0], 'last': samples[-1],
                                         'link_lane_stopped_change_events': events}
    out = {
        'schema': 'native-lane-change-distance-audit/v1', 'source_sha256': before,
        'network_sha256': sha(NETWORK), 'producer_sha256': sha(Path(__file__)),
        'model_execution': False, 'com_access': False, 'fzp_scanned': False,
        'xml_links': rows, 'native_routes_using10635': routes, 'physical_heads71': heads,
        'link_behavior_type1': dict(behavior_type.attrib), 'driving_behavior1': dict(behavior.attrib),
        'path_distance_parts': path_lengths,
        'decision1126_to10635_centerline_distance_m': sum(r['distance_m'] for r in path_lengths),
        'last_lane_change_opportunity_length_m': path_lengths[-1]['distance_m'],
        'incoming10641_target_lanes': [2, 3], 'destination10635_source_lanes': [4, 5],
        'upstream_destination_lane_sets_disjoint': True,
        'emergency_distance_geometry_check': {
            'connector_start_m': 80.886394942347508, 'base_stop_distance_m': 5.0,
            'odd_lane_adjustment_m_from_PTV_document': 2.5,
            'unrounded_result_m': 80.886394942347508 - 5.0 - 2.5,
            'last_observed4725_position_m': 73.39,
            'scope': 'Geometric consistency only; manual also describes integer position handling, so this is not a bit-exact engine reproduction.'},
        'observations': observations, 'native_removal': followup['native_removal4725'],
        'proposed_single_change': {
            'xpath': "./links/link[@no='10635']/@lnChgDist", 'baseline': '1000', 'treatment': '2000',
            'status': 'proposal_only_no_network_file_written',
            'hold_fixed': ['lnChgDistIsPerLn=false', 'emergStopDist=5', 'drivingBehavior1.diffusTm=45',
                           'all lane maps and other connector distances', 'driver and route properties',
                           'seed13, SimPeriod1050, 1s recording, initial warmup and identical actual command schedule'],
            'interpretation': 'Distance-only sensitivity; baseline already covers the420.887m after native decision. It cannot add access to71 lanes4/5 upstream of10641. Route lookahead/combine are true, so earlier upstream behavior remains an empirical question.'},
        'official_documentation': [
            'https://cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/5_Netzbearbeiten/Strassennetz_Verb_str_Attr.htm',
            'https://cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/4_BasisdatenSim/FahrverhaltensparameterFahrstreifenwechsel_bearb.htm'],
    }
    out['source_changes'] = [name for name, digest in before.items() if sha(ROOT / name) != digest]
    if out['source_changes']:
        raise ValueError(out['source_changes'])
    target = ROOT / 'diagnostics/lane_change_10635_distance_audit.json'
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(target.relative_to(ROOT)), 'links': len(rows), 'routes': len(routes),
                      'route_distance_m': out['decision1126_to10635_centerline_distance_m'],
                      'source_changes': out['source_changes']}))


if __name__ == '__main__':
    main()
