"""Audit all635 physical members, including currently empty links, read-only."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'diagnostics')]
from probe_sc2001_corridor_replay import fixture


def main():
    existing = ROOT / 'diagnostics/physical_projection_support_635_proposal.json'
    if existing.exists() and json.loads(existing.read_text(encoding='utf-8')).get('full_area_coverage_audit', {}).get('receiver_review_20260910'):
        raise RuntimeError('This historical 170/45 builder predates the reviewed 16 receiver repairs; refusing to overwrite the current support data.')
    cfg, state, _, raw, detectors = fixture(return_detectors=True)
    area_path = ROOT/'diagnostics/control_area_membership.json'
    area = json.loads(area_path.read_text(encoding='utf-8'))
    network = ROOT/area['network']['path']
    if hashlib.sha256(network.read_bytes()).hexdigest() != area['network']['sha256']:
        raise ValueError('Area and network source differ')
    tree = ET.parse(network).getroot()
    links = {row.get('no'): row for row in tree.findall('./links/link')}
    signal_links = {row.get('lane').split()[0] for row in tree.findall('./signalHeads/signalHead')}
    input_links = {row.get('link') for row in tree.findall('./vehicleInputs/vehicleInput')}
    # Known full transfer paths can refute an apparently unique legacy alias.
    # Restrict this proof to a physical signal stopline as path source; an
    # off-ramp route may pass through another still-unserved urban stopline.
    transfer_paths = []
    for name in ['physical_movement_routes_ver2.json', 'dynamic_area_routes_ver2.json']:
        evidence = json.loads((ROOT/'diagnostics'/name).read_text(encoding='utf-8'))
        for movement, proof in evidence['by_movement'].items():
            if proof['path'][0] in signal_links:
                transfer_paths.append((movement, proof['path'], proof['expected_spec']['receiving_link']))
    original_path = ROOT/'diagnostics/physical_projection_support_ver2.json'
    proposal = json.loads(original_path.read_text(encoding='utf-8'))
    fw, ramps = detectors['freeway_link_to_model_link'], detectors['ramp_link_to_queues']
    observable = set(map(str, detectors['observable_links']))
    origins = detectors['link_to_origins']
    ledger, additions, unresolved = {}, {}, {}
    for key in area['inside_links']:
        row = {'physical_link': key, 'local_mask_enabled': key in observable,
               'existing_origins': origins.get(key, []), 'current_vehicles': raw['vehicle_records']['full_network_link_counts'].get(key, 0)}
        conflicts = [{'movement': movement, 'path': path, 'receiving_storage': receiver}
                     for movement, path, receiver in transfer_paths
                     if key in path[1:-1] and receiver not in origins.get(key, [])]
        if conflicts:
            row['known_native_transfer_identity_conflicts'] = conflicts
        if key in fw:
            row.update(status='supported_separate_freeway_chain', model_link=fw[key], reason='Counted by the VBS full freeway chain irrespective of the urban local mask.')
        elif key in ramps:
            row.update(status='supported_ramp_queue', ramps=ramps[key])
        elif key in observable:
            movements = [x['movement'] for x in detectors.get('link_to_movements', {}).get(key, []) if x['movement'] in cfg.network.urban_movements and float(x.get('weight', 0)) > 0]
            targets = [x for x in origins.get(key, []) if x in cfg.network.urban_link_storage_veh]
            if movements or targets:
                row.update(status='supported_existing_urban', movements=movements, storage_targets=targets,
                    assignment_note='Existing projection may split/merge supports; this audit does not certify every legacy route identity.')
            else:
                row.update(status='unresolved_observable_without_model_stock', reason='No active movement or existing storage target supports this local record.')
                unresolved[key] = row
        else:
            link = links[key]
            to = link.find('toLinkEndPt')
            target_link = to.get('lane').split()[0] if to is not None else key
            targets = origins.get(target_link, [])
            row.update(to_link=target_link if to is not None else None, actual_downstream_origins=targets)
            # A narrow auditable rule: existing connector support must include
            # the sole downstream road storage. Contradictions are not repaired
            # by merely trusting the next road's potentially merged alias.
            target = targets[0] if len(targets) == 1 else None
            reason = None
            if target is None:
                reason = 'Downstream physical road has multiple/no model origins; no equal split or arbitrary owner selection.'
            elif target not in cfg.network.urban_link_storage_veh:
                reason = 'Unique downstream alias is not an existing model storage.'
            elif target not in origins.get(key, []):
                reason = 'Existing connector support contradicts downstream origin; requires native movement-path proof before reassignment.'
            elif conflicts:
                reason = 'A known signal-to-receiver native path contradicts this legacy storage alias. Its shared physical corridor needs cohort/route disambiguation.'
            elif key in signal_links or (to is None and key in input_links):
                reason = 'Physical stopline/input needs its own movement/arrival timing model, not a forced transit-storage projection.'
            if reason:
                row.update(status='unresolved_physical_support', reason=reason)
                unresolved[key] = row
            else:
                row.update(status='proposed_unique_physical_storage', target_storage=target,
                    reason='Actual connector endpoint and existing source/downstream support agree on one storage.' if to is not None else
                           'Unsignalled, input-free road has one existing physical storage support.')
                additions[key] = row
                proposal['link_to_storage'][key] = target
                proposal['evidence'][key] = {'to_link': target_link} if to is not None else {}
                proposal['evidence'][key].update(reason=row['reason'], existing_origins=origins.get(key, []),
                    downstream_origins=targets, zero_vehicle_support_reviewed=True)
        ledger[key] = row
    if len(ledger) != 635 or set(ledger) != set(area['inside_links']):
        raise ValueError('All physical area members must receive exactly one coverage category')
    proposal['full_area_coverage_audit'] = {
        'source': 'diagnostics/area_projection_coverage_635.json',
        'area_membership_sha256': hashlib.sha256(area_path.read_bytes()).hexdigest(),
        'prior_support_path': str(original_path.relative_to(ROOT)),
        'prior_support_sha256': hashlib.sha256(original_path.read_bytes()).hexdigest(),
        'all_area_members_reviewed': 635, 'additional_unique_supports': len(additions),
        'unresolved_physical_links': sorted(unresolved, key=int),
        'require_positive_unresolved_failure': True,
        'policy': 'Support is determined from physical topology even when the snapshot count is zero. Unresolved IDs remain explicit and are not mapped to zero/equal shares.'}
    output = {'network': area['network'], 'area_sha256': hashlib.sha256(area_path.read_bytes()).hexdigest(),
        'counts': dict(Counter(row['status'] for row in ledger.values())), 'by_physical_link': ledger,
        'proposed_additions': additions, 'unresolved': unresolved,
        'unresolved_raw_inside_current_veh': sum(row['current_vehicles'] for row in unresolved.values()),
        'runtime_changes': 'None. Data proposal only; existing projection_support.configure can consume it.'}
    (ROOT/'diagnostics/area_projection_coverage_635.json').write_text(json.dumps(output, indent=2), encoding='utf-8')
    (ROOT/'diagnostics/physical_projection_support_635_proposal.json').write_text(json.dumps(proposal, indent=2), encoding='utf-8')
    print(json.dumps({'counts': output['counts'], 'new_supports': len(additions), 'unresolved_ids': sorted(unresolved,key=int),
        'six_new_positive_are_supported': all(key in additions for key in ['10224','10554','10774','10273','10579','10294'])}, indent=2))


if __name__ == '__main__':
    main()
