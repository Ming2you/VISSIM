"""Optional, network-pinned static route priors for direct/signal landing.

These are conditional route-choice inputs, not realized passage measurements.
They apply to vehicles reached by the cited static decisions; after-decision
merges and congestion can change the observed group passage ratio.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from evaluation.controllers.network_provenance import snapshot_network_sha256

ROOT = Path(__file__).resolve().parents[2]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def derive_prior(document):
    network = ROOT / document['network']['path']
    if sha256(network) != document['network']['sha256']:
        raise ValueError('Offramp route prior network hash mismatch')
    tree = ET.parse(network).getroot()
    starts = [float(x.get('start')) for x in tree.findall(".//timeIntervalSet[@no='VEHICLEROUTESTATIC']/timeInts/timeInterval")]
    if starts != [0.0]:
        raise ValueError('Static prior supports the verified single route interval starting at zero')
    decisions = tree.findall('.//vehicleRoutingDecisionStatic')
    rows = {}
    for off, spec in document['groups'].items():
        decision = next((x for x in decisions if x.get('no') == str(spec['decision'])), None)
        if decision is None or decision.get('allVehTypes') != 'true' or decision.get('routeChoiceMeth') != 'STATIC':
            raise ValueError(f'{off}: expected static decision for all vehicle types')
        if decision.get('link') != str(spec['decision_link']):
            raise ValueError(f'{off}: changed decision placement')
        targets = {str(spec['direct_connector']): 'direct', str(spec['signal_connector']): 'signal'}
        evidence, weights = [], {'direct': 0.0, 'signal': 0.0}
        for other in decisions:
            hits = []
            for route in other.findall('./vehRoutSta/vehicleRouteStatic'):
                path = [x.get('key') for x in route.findall('./linkSeq/intObjectRef')] + [route.get('destLink')]
                present = [key for key in targets if key in path]
                if len(present) > 1:
                    raise ValueError(f'{off}: a route visits both group branches; no simple conditional prior')
                if not present:
                    continue
                if other is not decision:
                    raise ValueError(f'{off}: another static decision also supplies its branches')
                raw = (route.get('relFlow') or '').strip()
                defaulted = not raw
                match = re.fullmatch(r'2 0:([0-9]+(?:\.[0-9]+)?)', raw) if raw else None
                if raw and match is None:
                    raise ValueError(f'{off}: unsupported time-dependent relative flow {raw!r}')
                weight = 1.0 if defaulted else float(match.group(1))
                branch = targets[present[0]]
                weights[branch] += weight
                evidence.append({'route': route.get('no'), 'branch': branch, 'connector': present[0],
                    'relFlow_raw': raw, 'weight': weight, 'empty_relFlow_default_one': defaulted,
                    'connector_is_destination': route.get('destLink') == present[0]})
        total = sum(weights.values())
        if total <= 0 or len(evidence) != 2:
            raise ValueError(f'{off}: expected exactly one positive branch route on each side')
        share = weights['direct'] / total
        expected = float(spec['direct_share'])
        if not math.isclose(share, expected, abs_tol=1e-12, rel_tol=0):
            raise ValueError(f'{off}: overlay share does not match pinned route weights')
        rows[off] = {'direct_share': share, 'decision': decision.attrib,
                     'interval_start_sec': 0, 'interval_end': 'end of simulation',
                     'vehicle_types': 'all', 'branch_weights': weights, 'routes': evidence,
                     'other_decisions_using_either_connector': []}
    return rows


def install(cfg, tuning, state_json=None):
    path = ((tuning.get('urban', {}) or {}).get('ramp', {}) or {}).get('offramp_direct_route_prior')
    if path is None:
        return {}
    if not isinstance(path, str) or not path.strip():
        raise ValueError('urban.ramp.offramp_direct_route_prior must name a pinned JSON source')
    source = ROOT / path
    document = json.loads(source.read_text(encoding='utf-8-sig'))
    if document.get('schema') != 'offramp-static-route-prior/v1':
        raise ValueError('Unsupported offramp static prior schema')
    if state_json is not None:
        actual = snapshot_network_sha256(state_json)
        if actual != document['network']['sha256']:
            raise ValueError('Run network hash does not match the static route prior')
    rows = derive_prior(document)
    current = getattr(cfg.network, 'offramp_direct_share_by_offramp', None)
    if not current or any(off not in current for off in rows):
        raise ValueError('Static route prior requires configured direct landing groups')
    previous = {off: float(current[off]) for off in rows}
    updated = dict(current)
    updated.update({off: row['direct_share'] for off, row in rows.items()})
    cfg.network.offramp_direct_share_by_offramp = updated
    provenance = {'source': path, 'source_sha256': sha256(source), 'network': document['network'],
                  'prior_semantics': document['prior_semantics'], 'previous_shares': previous, 'groups': rows}
    cfg.network.offramp_route_prior_provenance = provenance
    return {'offramp_route_prior_enabled': 1.0, 'offramp_route_prior_provenance': provenance}
