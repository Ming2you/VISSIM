"""Read-only physical proof for the first positive unresolved Omega observation."""
from collections import Counter, defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]


def main():
    output_path = ROOT / 'diagnostics/unresolved_projection_support_review.json'
    if output_path.exists():
        raise FileExistsError('Preserve the pinned original 45-link proof; use a new explicit review script/output for later revisions.')
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers.runtime_setup import configure_runtime
    from evaluation.controllers.projection_support import complete_records
    folder = ROOT / 'evaluation/runs/codex_area_beta0_s13_20260910/decisions_codex_area_beta0_s13_20260910'
    paths = {
        'coverage': ROOT / 'diagnostics/area_projection_coverage_635.json',
        'support': ROOT / 'diagnostics/physical_projection_support_635_proposal.json',
        'contract': ROOT / 'diagnostics/control_area_route_contract_physical_routes.json',
        'config': ROOT / 'diagnostics/area_candidate_configs/n7_area_beta0.json',
        'snapshot': folder / 'state_001050.json',
        'network': ROOT / 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx',
    }
    hashes = {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in paths.items()}
    coverage = json.loads(paths['coverage'].read_text(encoding='utf-8'))
    if hashes['network'] != coverage['network']['sha256']:
        raise ValueError('Pinned physical network differs from coverage source')
    raw = json.loads(paths['snapshot'].read_text(encoding='utf-8'))
    records = complete_records(raw)
    contract = json.loads(paths['contract'].read_text(encoding='utf-8'))
    tuning = adapter.load_optional_json(str(paths['config']))
    # Match the explicit writer declaration used by the failed live arm. This
    # process only constructs/reads a model; it never writes actuator commands.
    os.environ['RW_OFFSET_WRITER'] = tuning['actuation']['real_world_signal_control']['offset_writer']
    adapter.install_config_switches(tuning)
    calibration = adapter.load_optional_json(str(ROOT / 'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))
    calibration = adapter.deep_update(calibration, tuning.get('calibration_override', {}))
    mapping = adapter.load_optional_json(str(ROOT / tuning['mapping_json']))
    detectors = adapter.load_optional_json(str(ROOT / tuning['detector_mapping_json']))
    detectors, _ = adapter.filter_midblock_links_from_detector_mapping(detectors, tuning)
    reference = json.loads((folder / 'state_000900.json').read_text(encoding='utf-8'))
    _, _, _, _, TrafficState, _ = adapter.repo_imports(ROOT / 'vendor/NumSim-mine')
    cfg = adapter.build_config(ROOT / 'vendor/NumSim-mine', 150, reference['sim_period_sec'],
        'fast-smoke', calibration, tuning, local_observation=True, flagship=True)
    _, detectors, _ = configure_runtime(adapter, cfg, tuning, mapping, reference,
        str(folder / 'action_000001.json'), detectors, calibration, TrafficState)
    net = ET.parse(paths['network']).getroot()
    links = {node.get('no'): node for node in net.findall('./links/link')}
    heads = defaultdict(list)
    for head in net.findall('./signalHeads/signalHead'):
        heads[head.get('lane').split()[0]].append(dict(head.attrib))
    routes = []
    for decision in net.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic'):
        for route in decision.findall('./vehRoutSta/vehicleRouteStatic'):
            routes.append({'id': decision.get('no') + ':' + route.get('no'),
                'decision': dict(decision.attrib), 'route': dict(route.attrib),
                'path': [decision.get('link')] + [n.get('key') for n in route.findall('./linkSeq/intObjectRef')] + [route.get('destLink')]})
    incoming, outgoing = defaultdict(list), defaultdict(list)
    for key, node in links.items():
        fr, to = node.find('fromLinkEndPt'), node.find('toLinkEndPt')
        if fr is not None and to is not None:
            edge = {'connector': key, 'from_link': fr.get('lane').split()[0],
                    'from_pos_m': float(fr.get('pos')), 'to_link': to.get('lane').split()[0], 'to_pos_m': float(to.get('pos'))}
            outgoing[edge['from_link']].append(edge)
            incoming[edge['to_link']].append(edge)
    proposed, reviewed = {}, {}
    for key, old in coverage['unresolved'].items():
        node = links[key]
        fr, to = node.find('fromLinkEndPt'), node.find('toLinkEndPt')
        paths_here = [route for route in routes if key in route['path']]
        matches = []
        for name, row in contract.items():
            movement = name.removeprefix('movement:')
            if not name.startswith('movement:') or movement not in cfg.network.urban_movements:
                continue
            spec = cfg.network.urban_movements[movement]
            for turn in row.get('physical_turns', []):
                if turn.get('connector') == key:
                    matches.append({'movement': movement, 'contract_status': row['status'], 'turn': turn,
                                    'actual_model_receiving_link': spec.get('receiving_link'),
                                    'model_spec': {k: spec.get(k) for k in ('origin', 'kind', 'signal', 'approach', 'receiving_link')}})
        targets = {row['actual_model_receiving_link'] for row in matches}
        proof = {'prior_coverage': old, 'physical_records': [row for row in records if str(row['link_no']) == key],
                 'reference_900_count': reference['vehicle_records']['full_network_link_counts'].get(key, 0),
                 'native_routes': paths_here, 'canonical_matches': matches,
                 'heads_on_link': heads[key], 'incoming': incoming[key], 'outgoing': outgoing[key]}
        if fr is not None and to is not None:
            triple = [fr.get('lane').split()[0], key, to.get('lane').split()[0]]
            proof['physical_triplet'] = triple
            proof['source_heads'] = heads[triple[0]]
            proof['from_endpoint'] = dict(fr.attrib)
            proof['to_endpoint'] = dict(to.attrib)
            points = [(float(p.get('x')), float(p.get('y')), float(p.get('zOffset', 0)))
                      for p in node.findall('./geometry/linkPolyPts/linkPolyPoint')]
            proof['length_m'] = sum(math.dist(a, b) for a, b in zip(points, points[1:]))
            matched_routes = [route for route in paths_here if any(route['path'][i:i+3] == triple for i in range(len(route['path'])-2))]
            target = next(iter(targets)) if len(targets) == 1 else None
            proof['candidate_receiver'] = target
            # No nearest-neighbour choice: actual modeled receiver, exact native
            # triplet and actual downstream storage must agree. A connector may
            # bypass a head that remains farther along its source road; its
            # observed vehicles have nevertheless left that road already.
            valid = (matches and target in cfg.network.urban_link_storage_veh
                and target in detectors.get('link_to_origins', {}).get(triple[2], [])
                and not old.get('known_native_transfer_identity_conflicts')
                and matched_routes and not heads[key]
                and heads[triple[0]]
                and all(row['contract_status'] in ('unique', 'same_transition') for row in matches)
                and all([row['turn']['from_link'], key, row['turn']['to_link']] == triple for row in matches))
            if valid:
                passed_head = any(float(head['pos']) <= float(fr.get('pos')) for head in heads[triple[0]])
                proof.update(status='proven_post_stopline_receiver' if passed_head else 'proven_unsignalled_bypass_receiver',
                             target_storage=target, source_head_precedes_connector=passed_head)
                proposed[key] = target
            else:
                proof['status'] = 'unresolved_shared_route_cohorts' if old.get('known_native_transfer_identity_conflicts') else 'unresolved_no_unique_accepted_movement_proof'
        else:
            proof['status'] = 'unresolved_road_origin_or_route_identity'
        reviewed[key] = proof
    result = {'source_sha256': hashes, 'snapshot': str(paths['snapshot'].relative_to(ROOT)),
              'network': coverage['network'], 'reviewed_count': len(reviewed),
              'status_counts': dict(Counter(row['status'] for row in reviewed.values())),
              'proven_additions': proposed, 'remaining_unresolved': [key for key in reviewed if key not in proposed],
              'links': reviewed, 'scope': 'Existing accepted-movement receiver only; no new ownership, area membership, probability or initial entry event.'}
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: result[key] for key in ('reviewed_count', 'status_counts', 'proven_additions', 'remaining_unresolved')}, indent=2))


if __name__ == '__main__':
    main()
