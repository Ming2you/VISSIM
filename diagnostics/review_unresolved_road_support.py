"""Read-only geometry/accepted-movement evidence for currently unresolved roads."""
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'diagnostics'), str(ROOT/'vendor/NumSim-mine')]


def main():
    from diagnostics.probe_model_area_integration import build_projected
    run = 'codex_area_beta0_retry_s13_20260910'
    folder = ROOT/'evaluation/runs'/run/('decisions_'+run)
    config = ROOT/'diagnostics/area_candidate_configs/n7_area_beta0.json'
    cfg, _, detectors, _, _, _, _ = build_projected(config,
        folder/'state_001200.json', folder/'action_001050.json', fixture_inputs=False)
    paths = {'config': config, 'reference_snapshot': folder/'state_001200.json',
        'snapshot': folder/'state_001350.json', 'previous_action': folder/'action_001200.json',
        'network': ROOT/'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx',
        'contract': ROOT/'diagnostics/control_area_route_contract_physical_routes.json',
        'original_review': ROOT/'diagnostics/unresolved_projection_support_review.json',
        'support': ROOT/'diagnostics/physical_projection_support_635_proposal.json'}
    review = json.loads(paths['original_review'].read_text(encoding='utf-8'))
    contract = json.loads(paths['contract'].read_text(encoding='utf-8'))
    actual = json.loads(paths['snapshot'].read_text(encoding='utf-8'))
    net = ET.parse(paths['network']).getroot()
    inputs = {i.get('link'): dict(i.attrib) for i in net.findall('./vehicleInputs/vehicleInput')}
    rows = {}
    for key, old in review['links'].items():
        if old['status'] != 'unresolved_road_origin_or_route_identity':
            continue
        matches = []
        for name, record in contract.items():
            movement = name.removeprefix('movement:')
            if not name.startswith('movement:') or movement not in cfg.network.urban_movements:
                continue
            for turn in record.get('physical_turns', []):
                support_paths = turn.get('destination_support_paths', [])
                if key in (turn.get('from_link'), turn.get('to_link')) or any(key in p for p in support_paths):
                    matches.append({'movement': movement, 'status': record['status'],
                        'actual_spec': cfg.network.urban_movements[movement],
                        'from_link': turn.get('from_link'), 'to_link': turn.get('to_link'),
                        'destination_support_paths': support_paths,
                        'destination_storage_support': turn.get('destination_storage_support'),
                        'physical_turn': turn})
        row = {'physical_link': key, 'origins': detectors.get('link_to_origins', {}).get(key, []),
            'movement_channels': detectors.get('link_to_movements', {}).get(key, []),
            'heads': old['heads_on_link'], 'input': inputs.get(key),
            'incoming': old['incoming'], 'outgoing': old['outgoing'],
            'native_routes': old['native_routes'], 'canonical_matches': matches,
            'records_1350': [v for v in actual['vehicle_records']['records'] if str(v['link_no']) == key],
            'downstream_origins': {edge['to_link']: detectors.get('link_to_origins', {}).get(edge['to_link'], []) for edge in old['outgoing']}}
        rows[key] = row
        print(json.dumps({k: row[k] for k in ('physical_link', 'origins', 'heads', 'input', 'outgoing', 'downstream_origins', 'canonical_matches')}, ensure_ascii=False))
    output = {'source_sha256': {name: hashlib.sha256(p.read_bytes()).hexdigest() for name, p in paths.items()},
        'source_paths': {name: p.relative_to(ROOT).as_posix() for name, p in paths.items()},
        'road_count': len(rows), 'roads': rows,
        'scope': 'Diagnostic evidence only; no mapping, membership, stock, demand or route probability is changed.'}
    target = ROOT/'diagnostics/unresolved_road_support_review_1350.json'
    if target.exists():
        raise FileExistsError('Keep the original read-only road evidence')
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
