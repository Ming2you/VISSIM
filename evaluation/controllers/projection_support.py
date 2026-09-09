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


def _reviewed_road_downstream(key, target, evidence, links, network, cfg, detectors):
    """Validate a declared deterministic road corridor, not a nearest alias.

    This only supports an already observed transit stock. It neither grants
    signal authority nor emits the accepted movement's earlier crossing again.
    """
    if evidence.get('to_link') or evidence.get('new_shared_approach'):
        raise ValueError(f'Reviewed road path cannot mix alternative support modes: {key}')
    proof = evidence['downstream_path']
    path = proof['links']
    if (not isinstance(path, list) or len(path) < 3 or len(path) % 2 != 1
            or path[0] != key or any(not isinstance(link, str) or link not in links for link in path)
            or len(set(path)) != len(path)):
        raise ValueError(f'Invalid reviewed road path: {key}')
    heads = {node.get('lane').split()[0] for node in network.findall('./signalHeads/signalHead')}
    inputs = {node.get('link') for node in network.findall('./vehicleInputs/vehicleInput')}
    if set(path[:-1]) & (heads | inputs):
        raise ValueError(f'Reviewed transit road has a signal or input: {key}')
    outgoing, incoming = defaultdict(list), defaultdict(list)
    for connector, node in links.items():
        start = node.find('fromLinkEndPt')
        if start is not None:
            outgoing[start.get('lane').split()[0]].append(connector)
            end = node.find('toLinkEndPt')
            if end is not None:
                incoming[end.get('lane').split()[0]].append(connector)
    previous_entry = 0.0
    for index in range(0, len(path)-2, 2):
        road, connector, following = path[index:index+3]
        if links[road].find('fromLinkEndPt') is not None or outgoing[road] != [connector]:
            raise ValueError(f'Reviewed road lacks a single physical next connector: {road}')
        start, end = links[connector].find('fromLinkEndPt'), links[connector].find('toLinkEndPt')
        if (start is None or end is None or start.get('lane').split()[0] != road
                or end.get('lane').split()[0] != following
                or float(start.get('pos')) < previous_entry):
            raise ValueError(f'Disconnected or backward reviewed road path: {key}')
        previous_entry = float(end.get('pos'))
    if links[path[-1]].find('fromLinkEndPt') is not None:
        raise ValueError(f'Reviewed road terminal is not a receiving road: {key}')
    if target not in detectors.get('link_to_origins', {}).get(path[-1], []):
        raise ValueError(f'Reviewed road terminal lacks receiving storage {target}: {key}')
    source = proof['canonical_contract']
    contract_path = ROOT/source['path']
    if hashlib.sha256(contract_path.read_bytes()).hexdigest() != source['sha256']:
        raise ValueError(f'Reviewed road canonical contract fingerprint mismatch: {key}')
    contract = json.loads(contract_path.read_text(encoding='utf-8'))
    movement = proof['movement']
    spec = cfg.network.urban_movements.get(movement)
    record = contract.get('movement:'+movement, {})
    if (spec is None or spec.get('receiving_link') != target
            or record.get('status') not in ('unique', 'same_transition')):
        raise ValueError(f'Reviewed road accepted-movement receiver differs: {key}')
    turns = [turn for turn in record.get('physical_turns', [])
             if turn.get('to_link') == key and path in turn.get('destination_support_paths', [])
             and target in turn.get('destination_storage_support', [])]
    if not turns:
        raise ValueError(f'Reviewed road is not the canonical destination path: {key}')
    if set(incoming[key]) != {turn['connector'] for turn in turns}:
        raise ValueError(f'Reviewed road also receives an unclassified approach: {key}')
    first_departure = float(links[path[1]].find('fromLinkEndPt').get('pos'))
    for turn in turns:
        source_link = links.get(turn['connector'])
        start = source_link.find('fromLinkEndPt') if source_link is not None else None
        end = source_link.find('toLinkEndPt') if source_link is not None else None
        if (start is None or end is None or start.get('lane').split()[0] != turn['from_link']
                or end.get('lane').split()[0] != key or float(end.get('pos')) > first_departure):
            raise ValueError(f'Canonical arrival cannot traverse the reviewed road forward: {key}')
    for name, other in contract.items():
        other_spec = cfg.network.urban_movements.get(name.removeprefix('movement:')) if name.startswith('movement:') else None
        if other_spec and other_spec.get('receiving_link') != target and any(
                turn.get('to_link') == key for turn in other.get('physical_turns', [])):
            raise ValueError(f'Reviewed road has conflicting active movement receivers: {key}')
    native_ids = proof['native_route_ids']
    if (not isinstance(native_ids, list) or not native_ids or any(not isinstance(name, str) for name in native_ids)
            or len(set(native_ids)) != len(native_ids)):
        raise ValueError(f'Reviewed road needs explicit native path evidence: {key}')
    native = {}
    for decision in network.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic'):
        for route in decision.findall('./vehRoutSta/vehicleRouteStatic'):
            native[decision.get('no')+':'+route.get('no')] = ([decision.get('link')]
                + [node.get('key') for node in route.findall('./linkSeq/intObjectRef')] + [route.get('destLink')])
    accepted_paths = [[turn['from_link'], turn['connector']]+path for turn in turns]
    for name in native_ids:
        route = native.get(name, [])
        if not any(any(route[i:i+len(join)] == join for i in range(len(route)-len(join)+1)) for join in accepted_paths):
            raise ValueError(f'Native route does not traverse the reviewed accepted path: {key}:{name}')
    return path[-1]


def _reviewed_source_lineage(key, target, evidence, document, links, network, cfg):
    """A pre-merge connector can retain a uniquely proven upstream origin."""
    proof = evidence['source_lineage']
    source = proof['source_link']
    connector = links[key]
    start, end = connector.find('fromLinkEndPt'), connector.find('toLinkEndPt')
    if (start is None or end is None or start.get('lane').split()[0] != source
            or end.get('lane').split()[0] != evidence.get('to_link')
            or evidence.get('downstream_path') or evidence.get('new_shared_approach')):
        raise ValueError(f'Source-lineage connector path differs: {key}')
    if any(x.get('link') == source for x in network.findall('./vehicleInputs/vehicleInput')) or any(
            x.get('lane').split()[0] == source for x in network.findall('./signalHeads/signalHead')):
        raise ValueError(f'Source-lineage road has an independent input or signal: {key}')
    incoming = {link for link, node in links.items() if node.find('toLinkEndPt') is not None
                and node.find('toLinkEndPt').get('lane').split()[0] == source}
    declared = proof['upstream_receivers']
    if not declared or set(declared) != incoming:
        raise ValueError(f'Source-lineage upstream connector set differs: {key}')
    pin = proof['canonical_contract']
    raw_contract = (ROOT/pin['path']).read_bytes()
    if hashlib.sha256(raw_contract).hexdigest() != pin['sha256']:
        raise ValueError(f'Source-lineage canonical contract fingerprint differs: {key}')
    contract = json.loads(raw_contract.decode('utf-8-sig'))
    for name, record in contract.items():
        spec = cfg.network.urban_movements.get(name.removeprefix('movement:')) if name.startswith('movement:') else None
        if spec and spec.get('receiving_link') != target and any(
                turn.get('connector') in incoming for turn in record.get('physical_turns', [])):
            raise ValueError(f'Source-lineage has another active accepted receiver: {key}')
    for upstream, movement in declared.items():
        if document['link_to_storage'].get(upstream) != target:
            raise ValueError(f'Source-lineage upstream support target differs: {upstream}')
        spec = cfg.network.urban_movements.get(movement, {})
        record = contract.get('movement:'+movement, {})
        actual_from = links[upstream].find('fromLinkEndPt').get('lane').split()[0]
        if (spec.get('receiving_link') != target or record.get('status') not in ('unique', 'same_transition')
                or not any(t.get('connector') == upstream and t.get('from_link') == actual_from
                    and t.get('to_link') == source for t in record.get('physical_turns', []))):
            raise ValueError(f'Source-lineage accepted receiver differs: {upstream}')
        entry = float(links[upstream].find('toLinkEndPt').get('pos'))
        if entry > float(start.get('pos')):
            raise ValueError(f'Source-lineage incoming road would travel backwards: {upstream}')
    native = {}
    for decision in network.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic'):
        for route in decision.findall('./vehRoutSta/vehicleRouteStatic'):
            native[decision.get('no')+':'+route.get('no')] = (decision, route)
    names = proof['native_route_ids']
    if not isinstance(names, list) or not names or len(set(names)) != len(names):
        raise ValueError(f'Source-lineage needs explicit native route evidence: {key}')
    for name in names:
        decision, route = native.get(name, (None, None))
        if decision is None:
            raise ValueError(f'Source-lineage native route is absent: {name}')
        path = [decision.get('link')] + [x.get('key') for x in route.findall('./linkSeq/intObjectRef')] + [route.get('destLink')]
        if (path != [source, key] or decision.get('allVehTypes') != 'true'
                or decision.get('routeChoiceMeth') != 'STATIC' or float(decision.get('pos')) >= float(start.get('pos'))):
            raise ValueError(f'Source-lineage native route differs: {key}')


def _verified_corridor_claims(cfg, detectors, raw, document, links, records):
    """Accept only the configured, pinned physical partition and exact projection.

    A detector marker alone is not permission to suppress unresolved stock.
    The corridor configurator validates native paths before issuing its proof;
    this guard checks that the proof, source partition and projected channels
    still describe the same stocks at this particular snapshot.
    """
    claim = detectors.get('route_choice_verified_physical_stock')
    spec = getattr(cfg.network, 'route_choice_corridor', None)
    if claim is None and spec is None:
        return set()
    if not isinstance(claim, dict) or not isinstance(spec, dict):
        raise ValueError('Route-choice physical stock claim lacks configured projection')
    parts = spec.get('corridors') if spec.get('schema') == 'route-choice-corridors/v1' else [spec]
    if not isinstance(parts, list) or not parts or any(not isinstance(part, dict) for part in parts):
        raise ValueError('Route-choice physical stock has no valid corridor partitions')
    expected = {}
    for part in parts:
        proof = part.get('physical_stock_validation', {})
        source = ROOT / part['source_path']
        raw_source = source.read_bytes()
        if (proof.get('paths_validated') is not True
                or proof.get('network_sha256') != document['network']['sha256']
                or hashlib.sha256(raw_source).hexdigest() != proof.get('evidence_sha256')):
            raise ValueError('Route-choice physical stock path/source proof differs')
        evidence = json.loads(raw_source.decode('utf-8-sig'))
        fields = ('schema', 'network', 'prefix_links', 'prefix_storage', 'local_links',
                  'local_storage', 'post_stopline_projection')
        if evidence.get('schema') != 'route-choice-corridor/v1' or any(part.get(k) != evidence.get(k) for k in fields):
            raise ValueError('Route-choice physical stock partition differs from pinned evidence')
        prefix, local, post = part['prefix_links'], part['local_links'], part['post_stopline_projection']
        keys = list(prefix) + list(local) + list(post)
        if len(keys) != len(set(keys)) or any(k not in links for k in keys) or set(keys) & set(expected):
            raise ValueError('Route-choice physical stock partition overlaps or is not physical')
        expected.update({**dict.fromkeys(prefix, part['prefix_storage']),
                         **dict.fromkeys(local, part['local_storage']), **post})
    if claim != expected:
        raise ValueError('Route-choice physical stock claim differs from configured partition')
    reserved = set(detectors.get('ramp_link_to_queues', {})) | set(detectors.get('freeway_link_to_model_link', {}))
    if set(claim) & reserved:
        raise ValueError('Route-choice physical stock claim overlaps freeway/ramp projection')
    counts = Counter(str(row['link_no']) for row in records)
    for key, target in claim.items():
        if target not in cfg.network.urban_link_storage_veh:
            raise ValueError(f'Route-choice physical stock target is absent: {key}:{target}')
        if key in document['link_to_storage'] and document['link_to_storage'][key] != target:
            raise ValueError(f'Route-choice physical stock conflicts with reviewed support: {key}')
        if (detectors.get('transit_storage_projection', {}).get(key) != target
                or detectors.get('link_to_origins', {}).get(key) != [target]
                or detectors.get('link_to_movements', {}).get(key)):
            raise ValueError(f'Route-choice physical stock projection disagrees: {key}')
        if raw['local_observation'].get('link_counts', {}).get(key) != counts[key]:
            raise ValueError(f'Route-choice local/full physical stock counts disagree: {key}')
    return set(claim)


def _verified_native_input_claims(cfg, detectors, raw, document, links, records):
    claim=detectors.get('native_internal_verified_physical_stock')
    spec=getattr(cfg.network,'native_internal_inputs',None)
    if claim is None and spec is None:return set()
    if not isinstance(claim,dict) or not isinstance(spec,dict):
        raise ValueError('Native internal stock claim lacks configured projection')
    from evaluation.controllers.native_internal_input import projection_claims
    expected=projection_claims(cfg,document['network']['sha256'])
    if claim!=expected or any(key not in links for key in claim):
        raise ValueError('Native internal stock claim differs from validated source contract')
    reserved=set(detectors.get('ramp_link_to_queues',{}))|set(detectors.get('freeway_link_to_model_link',{}))
    if set(claim)&reserved or set(claim)&set(detectors.get('route_choice_verified_physical_stock',{})):
        raise ValueError('Native internal stock claim overlaps another physical partition')
    counts=Counter(str(row['link_no']) for row in records)
    for key,target in claim.items():
        if (target not in cfg.network.urban_link_storage_veh
                or (key in document['link_to_storage'] and document['link_to_storage'][key]!=target)):
            raise ValueError('Native internal stock claim target conflicts with reviewed storage')
        if (detectors.get('transit_storage_projection',{}).get(key)!=target
                or detectors.get('link_to_origins',{}).get(key)!=[target]
                or detectors.get('link_to_movements',{}).get(key)
                or raw['local_observation'].get('link_counts',{}).get(key)!=counts[key]):
            raise ValueError('Native internal stock claim projection/counts disagree')
    return set(claim)


def _verified_native_record_partitions(cfg, detectors, raw, document):
    from evaluation.controllers.native_internal_input import record_partition
    expected, proof = record_partition(cfg, raw)
    actual = detectors.get('physical_record_storage_projection', {})
    if actual != expected or detectors.get('native_internal_record_partition_proof', {}) != proof:
        raise ValueError('Native physical record partition differs from validated observations')
    reserved = (set(document['link_to_storage']) | set(detectors.get('ramp_link_to_queues', {}))
                | set(detectors.get('freeway_link_to_model_link', {}))
                | set(detectors.get('route_choice_verified_physical_stock', {})))
    if set(expected) & reserved:
        raise ValueError('Native physical record partition overlaps another projection owner')
    for link, buckets in expected.items():
        if (set(detectors.get('link_to_origins', {}).get(link, [])) != set(buckets)
                or detectors.get('link_to_movements', {}).get(link)
                or detectors.get('transit_storage_projection', {}).get(link) != 'physical_record_partition'
                or any(target not in cfg.network.urban_link_storage_veh for target in buckets)):
            raise ValueError('Native physical record partition mapping differs')
    return set(expected)


def configure(cfg, tuning, detectors, raw):
    """Return copied detector/raw data; do not alter owners or invent observations."""
    path = tuning.get('observation', {}).get('physical_support_repair')
    if path is None:
        return detectors, raw, {}
    document = json.loads((ROOT / path).read_text(encoding='utf-8-sig'))
    network = ROOT / document['network']['path']
    if hashlib.sha256(network.read_bytes()).hexdigest() != document['network']['sha256'] or snapshot_network_sha256(raw) != document['network']['sha256']:
        raise ValueError('Physical support repair network fingerprint mismatch')
    network_xml = ET.parse(network).getroot()
    links = {x.get('no'): x for x in network_xml.findall('./links/link')}
    records = complete_records(raw)
    corridor_claims = _verified_corridor_claims(cfg, detectors, raw, document, links, records)
    native_claims = _verified_native_input_claims(cfg, detectors, raw, document, links, records)
    record_partitions = _verified_native_record_partitions(cfg, detectors, raw, document)
    coverage = document.get('full_area_coverage_audit', {})
    if coverage.get('require_positive_unresolved_failure'):
        unresolved = set(coverage['unresolved_physical_links']) - corridor_claims - native_claims - record_partitions
        active = Counter(str(row['link_no']) for row in records if str(row['link_no']) in unresolved)
        if active:
            raise ValueError('Positive Omega records have unresolved physical stock support: '
                             + str(dict(sorted(active.items(), key=lambda item: int(item[0])))))
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
        if row.get('downstream_path'):
            endpoint = _reviewed_road_downstream(key, target, row, links, network_xml, cfg, detectors)
            support = detectors.get('link_to_origins', {}).get(endpoint, [])
        elif row.get('to_link'):
            actual = links[key].find('toLinkEndPt')
            if actual is None or actual.get('lane').split()[0] != row['to_link']:
                raise ValueError(f'Physical support connector endpoint changed: {key}')
            support = detectors.get('link_to_origins', {}).get(row['to_link'], [])
        else:
            support = detectors.get('link_to_origins', {}).get(key, [])
        if target not in support and not row.get('new_shared_approach'):
            raise ValueError(f'Downstream physical support does not contain {target}')
        if row.get('source_lineage'):
            _reviewed_source_lineage(key, target, row, document, links, network_xml, cfg)
    copied, observed = deepcopy(detectors), deepcopy(raw)
    metadata = {'physical_support_repair_enabled': 1.0, 'source': str(path), 'network': document['network'], 'links': {}}
    if corridor_claims:
        metadata['verified_corridor_stock_links'] = sorted(corridor_claims, key=int)
    if native_claims:
        metadata['verified_native_internal_stock_links'] = sorted(native_claims, key=int)
    if record_partitions:
        metadata['verified_native_record_partition_links'] = sorted(record_partitions, key=int)
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
