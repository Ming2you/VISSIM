"""Prepare one opt-in physical head join; no network, demand or run mutation."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import argparse
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from evaluation.controllers.signal_head_observation import physical_groups

def read(p):
    return json.loads(p.read_bytes())

def write(p, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    if p.exists() and p.read_bytes() != data:
        raise ValueError('Do not overwrite different prepared evidence: ' + str(p))
    p.write_bytes(data)

def pin(p):
    return dict(path=p.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(p.read_bytes()).hexdigest())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--include-free-right', action='store_true')
    args = parser.parse_args()
    base = HERE.parent/'urban_area263/approaches_only'
    out = HERE/'head47'
    out.mkdir(exist_ok=True)
    contract = read(base/'evidence/head_resources.json')
    support = read(HERE.parent/'urban260/head_lane_support.json')
    name = 'SC1003_S_SC1004_to_N_SC1001'
    expected = dict(kind='internal', signal='SC1003', phase='SC1003_p1',
                    origin='SC1004_to_SC1003', receiving_link='SC1003_to_SC1001')
    support['movements'] = {name: dict(expected_spec=expected, from_link='47', connector='10493',
                                     to_link='40', lanes=[2, 3, 4])}
    write(out/'physical_support.json', support)
    plan = read(ROOT/'outputs/signal_group_actuation_plan_mainline_20260825.json')
    heads = physical_groups(str(ROOT/contract['network']['path']), plan)[('47', 'p1')]
    contract['schema'] = 'physical-head-resource-join/v10'
    contract['resources']['10493'] = dict(group='47|p1', heads=heads, mode='regular_unique',
        members={name: expected}, receiver=expected['receiving_link'], target_link='40',
        proof=pin(out/'physical_support.json'),
        disjoint_consumers={'SC1003_S_SC1004_to_E_SC105': dict(
            expected_spec={**expected, 'receiving_link': 'SC1003_to_SC105', 'turn': 'right'},
            path=['47', '10494', '426'], native_route='1122:2',
            destination_mapping=pin(ROOT/'evaluation/real_world_modi_control_ver2_20260907/detector_local_mapping_ver2_20260907.json'))})
    contract['scope'] = 'v9 plus verified 47 lanes2-4 straight head; lane1 right receives none of this measurement'
    write(out/'head_resources.json', contract)
    config = copy.deepcopy(read(base/'config.json'))
    config['urban']['capacity']['head_resource_contract'] = (out/'head_resources.json').relative_to(ROOT).as_posix()
    write(out/'config.json', config)
    write(out/'preparation.json', dict(base_config=pin(base/'config.json'), candidate_config=pin(out/'config.json'),
        changes=['urban.capacity.head_resource_contract'], additional_resource='10493',
        capacity_parameter_fit=False, green_exposure_pool_added=False, native_runs=0))
    if args.include_free_right:
        right = HERE/'head47_right'
        right.mkdir(exist_ok=True)
        previous = ROOT/config['urban']['movements']['physical_phase_authority']
        authority = read(previous)
        tree = ET.parse(ROOT/authority['network']['path'])
        node = tree.find("./links/link[@no='10494']")
        start, end = node.find('fromLinkEndPt'), node.find('toLinkEndPt')
        source_heads = []
        for head in tree.findall('./signalHeads/signalHead'):
            if head.get('lane').split()[0] == '47':
                source_heads.append(dict(head=head.get('no'), link='47', lane=int(head.get('lane').split()[1]),
                    pos_m=float(head.get('pos')), SC='SC'+head.get('sg').split()[0], SG=head.get('sg').split()[1],
                    all_vehicle_types=head.get('allVehTypes')=='true', compliance=float(head.get('complRate', 1))))
        authority['unsignalized_movements']['SC1003_S_SC1004_to_E_SC105'] = dict(
            expected_spec=dict(signal='SC1003', phase='SC1003_p1', kind='internal', origin='SC1004_to_SC1003',
                               receiving_link='SC1003_to_SC105', turn='right'),
            path=['47', '10494', '426'], connector=dict(id='10494', source_lane=int(start.get('lane').split()[1]),
                source_pos=float(start.get('pos')), target_lane=int(end.get('lane').split()[1]),
                target_pos=float(end.get('pos')), lanes=len(node.findall('./lanes/lane'))),
            source_heads=source_heads, source_head_relation='disjoint_lanes', native_routes=['1122:2'],
            conflicts={x.get('no'): {k:x.get(k) for k in ('link1','link2','status')}
                for x in tree.findall('./conflictAreas/conflictArea')
                if x.get('link1') in ('10494','426') or x.get('link2') in ('10494','426')},
            rationale='Lane1 exits without a head; all SC1003 heads are on lanes2-4. Preserve capacity, routing and finite receiving space; remove only unrelated p1 green gating.')
        authority['goal8_derivation'] = dict(previous=pin(previous), added_movement='SC1003_S_SC1004_to_E_SC105',
            claude_reference='upstream_worklog/02_urban_b2/diag_c3/C3_DIAGNOSIS_CHECK.md:146 also identifies lane1 as a free right turn')
        write(right/'authority.json', authority)
        config['urban']['movements']['physical_phase_authority'] = (right/'authority.json').relative_to(ROOT).as_posix()
        write(right/'config.json', config)

if __name__ == '__main__':
    main()
