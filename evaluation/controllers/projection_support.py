"""Recover explicitly reviewed local observations from complete physical records."""
from __future__ import annotations
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from evaluation.controllers.network_provenance import snapshot_network_sha256

ROOT = Path(__file__).resolve().parents[2]


def complete_records(raw):
    envelope = raw.get('vehicle_records') or {}
    records = envelope.get('records')
    if envelope.get('complete') is not True or not isinstance(records, list):
        raise ValueError('Physical support repair requires a complete vehicle snapshot')
    if any(envelope.get(key) != len(records) for key in ('collection_count_before', 'collection_count_after', 'record_count')):
        raise ValueError('Physical support record counts disagree')
    if any(envelope.get(key) != raw['sim_sec'] for key in ('capture_sim_sec_before', 'capture_sim_sec_after')):
        raise ValueError('Physical support snapshot was not paused at its declared time')
    ids, counts = set(), Counter()
    for row in records:
        if row['veh_no'] in ids:
            raise ValueError('Physical support snapshot repeats a vehicle ID')
        ids.add(row['veh_no'])
        counts[str(row['link_no'])] += 1
        if not math.isfinite(float(row['position_m'])) or not math.isfinite(float(row['speed_kph'])) or float(row['speed_kph']) < 0:
            raise ValueError('Invalid physical position or speed')
    expected = {str(k): int(v) for k, v in envelope['full_network_link_counts'].items() if v}
    if dict(counts) != expected:
        raise ValueError('Physical support records do not match full-link counts')
    return records


def configure(cfg, tuning, detectors, raw):
    """Return copied detector/raw data; do not alter owners or invent observations."""
    path = tuning.get('observation', {}).get('physical_support_repair')
    if path is None:
        return detectors, raw, {}
    document = json.loads((ROOT / path).read_text(encoding='utf-8-sig'))
    network = ROOT / document['network']['path']
    if hashlib.sha256(network.read_bytes()).hexdigest() != document['network']['sha256'] or snapshot_network_sha256(raw) != document['network']['sha256']:
        raise ValueError('Physical support repair network fingerprint mismatch')
    links = {x.get('no'): x for x in ET.parse(network).getroot().findall('./links/link')}
    records = complete_records(raw)
    by_link = defaultdict(list)
    for row in records:
        by_link[str(row['link_no'])].append(row)
    table = document['link_to_storage']
    reserved = set(detectors.get('ramp_link_to_queues', {})) | set(detectors.get('freeway_link_to_model_link', {}))
    if set(table) & reserved:
        raise ValueError('Physical support repair cannot replace freeway or ramp observation channels')
    for key, target in table.items():
        if target not in cfg.network.urban_link_storage_veh:
            raise ValueError(f'Physical support target storage is absent: {target}')
        row = document['evidence'][key]
        if row.get('to_link'):
            actual = links[key].find('toLinkEndPt')
            if actual is None or actual.get('lane').split()[0] != row['to_link']:
                raise ValueError(f'Physical support connector endpoint changed: {key}')
            support = detectors.get('link_to_origins', {}).get(row['to_link'], [])
        else:
            support = detectors.get('link_to_origins', {}).get(key, [])
        if target not in support and not row.get('new_shared_approach'):
            raise ValueError(f'Downstream physical support does not contain {target}')
    copied, observed = deepcopy(detectors), deepcopy(raw)
    metadata = {'physical_support_repair_enabled': 1.0, 'source': str(path), 'network': document['network'], 'links': {}}
    local = observed['local_observation']
    marker = dict(copied.get('transit_storage_projection', {}))
    for key, target in table.items():
        rows = by_link[key]
        count = len(rows)
        prior = local.get('link_counts', {}).get(key)
        if prior is not None and float(prior) != count:
            raise ValueError(f'Local and full physical counts disagree on reviewed link {key}')
        local.setdefault('link_counts', {})[key] = count
        local.setdefault('link_stopped_counts', {})[key] = sum(bool(row['stopped']) for row in rows)
        if count:
            local.setdefault('link_speeds_kph', {})[key] = sum(float(row['speed_kph']) for row in rows) / count
        copied.setdefault('link_to_origins', {})[key] = [target]
        copied.setdefault('link_to_movements', {}).pop(key, None)
        marker[key] = target
        metadata['links'][key] = {'target': target, 'snapshot_vehicles': count, 'restored_count_channel': prior is None,
                                  'previous_origins': detectors.get('link_to_origins', {}).get(key, [])}
    copied['transit_storage_projection'] = marker
    copied['observable_links'] = sorted(set(map(str, copied.get('observable_links', []))) | set(table), key=int)
    copied['physical_support_repair_provenance'] = metadata
    return copied, observed, metadata
