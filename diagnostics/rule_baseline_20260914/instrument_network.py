"""Declare native lane detectors; canonical provenance owns runtime byte edits.

This preparation helper reads XML without serializing the physical network.
It never overwrites the source network or creates a second controller path.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from evaluation.controllers import network_provenance as provenance


def build_mapping(network_bytes, control_mapping, *, to_sec=10800):
    root = ET.fromstring(network_bytes)
    links = {int(row.get('no')): row for row in root.find('links')}
    dsds = {int(row.get('no')): row for row in root.find('desSpeedDecisions')}
    used_points = {int(row.get('no')) for row in root.find('dataCollectionPoints')}
    used_measurements = {int(row.get('no')) for row in root.find('dataCollectionMeasurements')}
    stations = []; address_points = {}; next_point = 910001; next_measurement = 910001

    def station(role, target, link_no, position_m, lane_numbers, **metadata):
        nonlocal next_point, next_measurement
        link = links[link_no]
        coordinates = [(float(row.get('x')), float(row.get('y')), float(row.get('zOffset', '0')))
                       for row in link.findall('./geometry/linkPolyPts/linkPolyPoint')]
        length = sum(math.dist(a, b) for a, b in zip(coordinates, coordinates[1:]))
        if not 0 <= position_m < length:
            raise ValueError('Detector position is outside its original link geometry')
        if not lane_numbers or any(not 1 <= lane <= len(link.find('lanes')) for lane in lane_numbers):
            raise ValueError('Detector lane is absent from original network')
        point_ids = []; measurement_ids = []
        for lane in lane_numbers:
            address = (link_no, lane, position_m)
            if address not in address_points:
                while next_point in used_points: next_point += 1
                address_points[address] = next_point
                used_points.add(next_point); next_point += 1
            while next_measurement in used_measurements: next_measurement += 1
            point_ids.append(address_points[address]); measurement_ids.append(next_measurement)
            used_measurements.add(next_measurement); next_measurement += 1
        stations.append({'id': f'{role}_{target}', 'role': role, 'target': target,
                         'link_no': link_no, 'position_m': position_m,
                         'lane_numbers': lane_numbers, 'point_ids': point_ids,
                         'measurement_ids': measurement_ids, **metadata})

    for ramp in control_mapping['ramp_meters']:
        connector = links[int(ramp['connector'])]
        merge = connector.find('toLinkEndPt')
        receiver, lane = map(int, merge.get('lane').split())
        merge_position = float(merge.get('pos'))
        if receiver != ramp['to_link']:
            raise ValueError('Ramp mapping receiver differs from original network')
        station('ramps', ramp['id'], receiver, merge_position + 50.0,
                list(range(1, len(links[receiver].find('lanes')) + 1)),
                connector_no=int(ramp['connector']), merge_position_m=merge_position,
                downstream_distance_m=50.0, merge_receiver_first_lane=lane,
                location_basis='50m downstream of physical connector endpoint; exploratory placement')

    for segment in control_mapping['segments']:
        if segment['model_segment_index'] not in (0, 5, 10, 15): continue
        heads = segment.get('dsd_by_lane') or {}
        if not heads: continue
        rows = [dsds[int(value['dsd_no'])] for _, value in sorted(heads.items(), key=lambda item: int(item[0]))]
        addresses = [(int(row.get('lane').split()[0]), float(row.get('pos'))) for row in rows]
        if len(set(addresses)) != 1:
            raise ValueError('VSL head lane decisions do not share one station')
        link, position = addresses[0]
        station('vsl_zones', f"{segment['model_link']}__seg{segment['model_segment_index']}",
                link, position, [int(row.get('lane').split()[1]) for row in rows],
                controlled_dsd_ids=[int(row['dsd_no']) for row in segment['dsds']],
                primary_dsd_ids=[int(row.get('no')) for row in rows],
                location_basis='exact primary installed dsd_by_lane position; old extra DSDs share the zone command')
    return {'schema': 'rule-native-detectors/v1', 'from_sec': 0, 'interval_sec': 150,
            'to_sec': to_sec, 'stations': stations,
            'vsl_heads': {'FW_E': [0, 5, 10, 15], 'FW_W': [0, 5, 10, 15]},
            'source_network_sha256': hashlib.sha256(network_bytes).hexdigest(),
            'measurement_contract': {
                'name': 'RULE|{role}|{target}|lane{lane_no}', 'points_per_measurement': 1,
                'vehicles': 'Vehs(Current,Last,All), completed interval count; flow_vph=3600*count/interval_sec',
                'speed': 'SpeedAvgArith(Current,Last,All); combine lanes weighted by Vehs, preserve empty-lane missing speed',
                'time_occupancy': 'OccupRate has SimulationRun,TimeInterval,VehicleClass subattributes; percent 0..100; singleton lane point',
                'occupancy_interval_status': 'Installed docs say last simulation step despite result subattributes; native smoke must establish completed-interval behavior',
                'lane_aggregation': 'Keep each lane separately including merge/exit-side lane1; lane mean OccupRate is explicit arithmetic mean, never multilanepoint union',
                'critical_occupancy': '15 percent is exploratory, not empirically fitted',
                'alinea_gain': '70 veh/h per percentage point is exploratory, not fitted'}}


def instrument_network(source_bytes, groups, declaration):
    """Return a runtime copy after exact reversible-whitelist verification."""
    result = provenance.prepare_recording_bytes(source_bytes, groups, rule_detectors=declaration)
    provenance.validate_recording_bytes(source_bytes, result, groups, rule_detectors=declaration)
    edits = sorted(provenance._recording_edits(source_bytes, groups) +
                   provenance._detector_edits(source_bytes, declaration))
    offset = 0; reversals = []
    for start, end, replacement in edits:
        reversals.append((start + offset, start + offset + len(replacement), source_bytes[start:end]))
        offset += len(replacement) - (end - start)
    restored = result
    for start, end, original in reversed(reversals):
        restored = restored[:start] + original + restored[end:]
    if restored != source_bytes:
        raise ValueError('Detector and recording transformation did not reverse to exact source bytes')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--network', type=Path, required=True)
    parser.add_argument('--control-mapping', type=Path, required=True)
    parser.add_argument('--mapping-out', type=Path, required=True)
    parser.add_argument('--to-sec', type=int, default=10800)
    args = parser.parse_args()
    if args.mapping_out.exists(): raise FileExistsError(args.mapping_out)
    data = args.network.read_bytes()
    mapping = json.loads(args.control_mapping.read_text(encoding='utf-8-sig'))
    declaration = build_mapping(data, mapping, to_sec=args.to_sec)
    # Parse/validate the same declaration used by the canonical writer.
    provenance._detector_edits(data, declaration)
    args.mapping_out.parent.mkdir(parents=True, exist_ok=True)
    args.mapping_out.write_text(json.dumps(declaration, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'stations': len(declaration['stations']),
                      'lane_measurements': sum(len(row['measurement_ids']) for row in declaration['stations']),
                      'output': str(args.mapping_out)}))


if __name__ == '__main__': main()
