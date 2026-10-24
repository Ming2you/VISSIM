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
from bisect import bisect_right
from collections import defaultdict
from copy import deepcopy

from evaluation.controllers.network_provenance import snapshot_network_sha256

ROOT = Path(__file__).resolve().parents[2]
_MISSED_TARGET = 'missed_target:'


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


def inventory_enabled(cfg):
    return getattr(cfg.network, 'offramp_route_inventory', None) is not None


def _pinned(pin):
    content = (ROOT / pin['path']).read_bytes()
    if hashlib.sha256(content).hexdigest() != pin['sha256']:
        raise ValueError('Offramp inventory source hash mismatch: ' + pin['path'])
    return content


def _position(runtime, physical, position):
    row = runtime['physical'].get(str(physical))
    if row is None or not math.isfinite(float(position)) or float(position) < 0:
        raise ValueError('Offramp route position is outside the reviewed freeway chain')
    fw, offset = row
    chain = offset + float(position)
    bounds = runtime['bounds'][fw]
    if chain > bounds[-1] + 1.0:
        raise ValueError('Offramp route position exceeds the reviewed chain')
    return fw, chain, min(len(bounds)-2, max(0, bisect_right(bounds, chain)-1))


def _weight(route):
    raw = (route.get('relFlow') or '').strip()
    match = re.fullmatch(r'2 0:([0-9]+(?:\.[0-9]+)?)', raw) if raw else None
    if raw and match is None:
        raise ValueError('Offramp inventory supports constant static route weights only')
    value = float(match.group(1)) if raw else 1.0
    if not math.isfinite(value) or value < 0:
        raise ValueError('Invalid static route weight')
    return value


def compile_inventory(document, mapping):
    """Compile only the reviewed freeway choices, exits and merge continuations.

    Future choices are expanded once as conditional expected mass. No observed
    current route is resampled. This is equivalent to drawing at the future
    decision for the current route-independent cell dynamics and constant
    native probabilities; it does not claim future realized vehicle routes.
    """
    if document.get('schema') != 'offramp-route-inventory/v1':
        raise ValueError('Unsupported off-ramp inventory schema')
    pinned_mapping = json.loads(_pinned(document['mapping']))
    if any(pinned_mapping.get(k) != mapping.get(k) for k in
           ('freeway_model_links', 'ramp_meters', 'model_topology_overrides')):
        raise ValueError('Offramp inventory and writer geometry differ')
    tree = ET.fromstring(_pinned(document['network']))
    intervals = tree.findall(".//timeIntervalSet[@no='VEHICLEROUTESTATIC']/timeInts/timeInterval")
    if (len(intervals) != 1 or float(intervals[0].get('start')) != 0.
            or set(intervals[0].attrib) != {'start'}):
        raise ValueError('Offramp inventory requires one constant route interval from zero')
    runtime = {'schema': 'offramp-route-inventory-runtime/v1', 'physical': {},
               'bounds': {}, 'branches': {}, 'decisions': {}, 'routes': {},
               'inputs': {}, 'merges': {}, 'network': deepcopy(document['network']),
               'mapping': deepcopy(document['mapping'])}
    for fw, row in mapping['freeway_model_links'].items():
        bounds = list(map(float, row['segment_bounds_m']))
        if len(bounds) < 2 or bounds[0] != 0 or any(a >= b for a,b in zip(bounds,bounds[1:])):
            raise ValueError('Invalid freeway cell bounds')
        runtime['bounds'][fw] = bounds
        for physical, offset in zip(row['chain_links'], row['chain_offsets_m']):
            if str(physical) in runtime['physical']:
                raise ValueError('Freeway physical chains overlap')
            runtime['physical'][str(physical)] = (fw, float(offset))
    links = {x.get('no'): x for x in tree.findall('./links/link')}
    wanted = set()
    for group, spec in document['groups'].items():
        wanted.add(str(spec['decision']))
        for branch in ('signal', 'direct'):
            connector = str(spec[branch + '_connector'])
            start = links[connector].find('fromLinkEndPt')
            fw, chain, cell = _position(runtime, start.get('lane').split()[0], start.get('pos'))
            if connector in runtime['branches']:
                raise ValueError('Duplicate off-ramp physical branch')
            runtime['branches'][connector] = {'group': group, 'branch': branch,
                'freeway': fw, 'source_cell': cell, 'source_chain_m': chain,
                'decision': str(spec['decision'])}
    if len(runtime['branches']) != 8 or len(wanted) != 4:
        raise ValueError('Exactly eight reviewed branches and four decisions required')
    decisions = tree.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic')
    for decision in decisions:
        no = decision.get('no')
        if no in wanted:
            if (decision.get('allVehTypes') != 'true' or decision.get('routeChoiceMeth') != 'STATIC'
                    or decision.get('combineStaRoutDec') != 'true'):
                raise ValueError('Reviewed off-ramp decision semantics changed')
            expected_link = next(s['decision_link'] for s in document['groups'].values() if str(s['decision']) == no)
            if decision.get('link') != str(expected_link):
                raise ValueError('Reviewed off-ramp decision physical source changed')
            fw, chain, cell = _position(runtime, decision.get('link'), decision.get('pos'))
            runtime['decisions'][no] = {'freeway': fw, 'chain_m': chain, 'cell': cell, 'routes': []}
        for route in decision.findall('./vehRoutSta/vehicleRouteStatic'):
            key = no + ':' + route.get('no')
            path = [decision.get('link')] + [x.get('key') for x in route.findall('./linkSeq/intObjectRef')]
            path.append(route.get('destLink'))
            path = [p for i,p in enumerate(path) if i == 0 or p != path[i-1]]
            if not any(p in runtime['physical'] for p in path):
                continue
            if len(set(path)) != len(path):
                raise ValueError('Offramp inventory does not support looping native routes')
            hits = [p for p in path if p in runtime['branches']]
            if len(hits) > 1 or (hits and runtime['branches'][hits[0]]['decision'] != no):
                raise ValueError('Unreviewed route also supplies an off-ramp branch')
            end = None
            if route.get('destLink') in runtime['physical']:
                fw, chain, _ = _position(runtime, route.get('destLink'), route.get('destPos'))
                end = (fw, chain)
            runtime['routes'][key] = {'path': path, 'target': hits[0] if hits else None,
                'end': end, 'weight': _weight(route), 'decision': no}
            if no in wanted:
                runtime['decisions'][no]['routes'].append(key)
    if set(runtime['decisions']) != wanted:
        raise ValueError('Reviewed static decisions are missing')
    # A mainline decision absent from the contract would silently change the
    # next eligible choice. Refuse it instead of skipping over it.
    for decision in decisions:
        if decision.get('link') in runtime['physical'] and decision.get('no') not in wanted:
            raise ValueError('Additional mainline static decision needs review')
    for no, decision in runtime['decisions'].items():
        if not decision['routes'] or math.fsum(runtime['routes'][k]['weight'] for k in decision['routes']) <= 0:
            raise ValueError('Static decision has no positive complete route distribution')
        _future_distribution(runtime, decision['freeway'], decision['chain_m']-1e-8)
    for node in tree.findall('./vehicleInputs/vehicleInput'):
        if node.get('link') in runtime['physical']:
            fw, chain, cell = _position(runtime, node.get('link'), 0)
            if cell != 0 or fw in runtime['inputs']:
                raise ValueError('One reviewed upstream native input per freeway required')
            runtime['inputs'][fw] = {'input': node.get('no'), 'physical_source': node.get('link'),
                'weights': _future_distribution(runtime, fw, chain)}
    if set(runtime['inputs']) != set(runtime['bounds']):
        raise ValueError('Missing native mainline input origin')
    for meter in mapping['ramp_meters']:
        connector = str(meter['connector'])
        end = links[connector].find('toLinkEndPt')
        fw, chain, cell = _position(runtime, end.get('lane').split()[0], end.get('pos'))
        if fw != meter['to_model_link'] or cell != meter['to_model_segment_index']:
            raise ValueError('Physical merge and canonical cell disagree')
        paths = [r for r in runtime['routes'].values() if connector in r['path']]
        distributions = [_route_distribution(runtime, r, fw, chain) for r in paths]
        if not distributions or any(x != distributions[0] for x in distributions[1:]):
            raise ValueError('Merge source continuations differ; explicit route stock is required')
        runtime['merges'][meter['id']] = {'freeway': fw, 'cell': cell,
            'weights': distributions[0], 'source_routes': sorted(k for k,r in runtime['routes'].items() if connector in r['path'])}
    return runtime


def _route_distribution(runtime, route, fw, position, visited=()):
    target = route['target']
    if target:
        branch = runtime['branches'][target]
        if branch['freeway'] != fw or branch['source_chain_m'] < position:
            raise ValueError('Observed route target is behind its freeway position')
        return {target: 1.0}
    end = route['end']
    if end is None or end[0] != fw:
        raise ValueError('Reviewed mainline route lacks its native continuation end')
    return _future_distribution(runtime, fw, max(position, end[1]), visited)


def _future_distribution(runtime, fw, after, visited=()):
    choices = [(d['chain_m'], no) for no,d in runtime['decisions'].items()
               if d['freeway'] == fw and d['chain_m'] > after]
    if not choices:
        return {'terminal': 1.0}
    _, no = min(choices)
    if no in visited:
        raise ValueError('Native route continuation loops before its next decision')
    decision = runtime['decisions'][no]
    total = math.fsum(runtime['routes'][key]['weight'] for key in decision['routes'])
    if total <= 0:
        raise ValueError('Future static decision lacks a positive complete distribution')
    result = defaultdict(float)
    for key in decision['routes']:
        route = runtime['routes'][key]
        for target, share in _route_distribution(runtime, route, fw, decision['chain_m'], (*visited, no)).items():
            result[target] += route['weight'] / total * share
    return dict(sorted(result.items()))


def configure_inventory(cfg, tuning, state_json, mapping):
    path = (tuning.get('freeway', {}) or {}).get('offramp_route_inventory')
    if path is None:
        return {}
    if not isinstance(path, str) or not path:
        raise ValueError('freeway.offramp_route_inventory must name a pinned contract')
    document = json.loads((ROOT / path).read_text(encoding='utf-8-sig'))
    if snapshot_network_sha256(state_json) != document['network']['sha256']:
        raise ValueError('Offramp route inventory and observed network differ')
    if not tuning.get('control_area_objective', {}).get('enabled'):
        raise ValueError('Route inventory requires the canonical coupled control-area predictor')
    runtime = compile_inventory(document, mapping)
    net = cfg.network
    if set(runtime['merges']) != set(net.ramps):
        raise ValueError('Route inventory requires all eight physical ramp reservoirs')
    if set(document['groups']) != set(net.off_ramps):
        raise ValueError('Offramp inventory group catalog differs')
    for branch in runtime['branches'].values():
        off = branch['group']
        branch['receiver'] = (net.off_ramp_storage_link[off] if branch['branch'] == 'signal'
                              else net.offramp_direct_tail_by_offramp[off])
        if (net.off_ramp_from_freeway[off] != branch['freeway']
                or branch['receiver'] not in net.urban_link_storage_veh):
            raise ValueError('Offramp branch does not have its existing destination stock')
    if len({b['receiver'] for b in runtime['branches'].values()}) != len(runtime['branches']):
        raise ValueError('Offramp inventory requires eight distinct reviewed receiving stocks')
    schedule = getattr(net, 'native_input_schedule', {})
    if schedule.get('schema') != 'native-input-schedule/v1' or schedule['network_sha256'] != document['network']['sha256']:
        raise ValueError('Route inventory requires the validated native input schedule')
    for row in runtime['inputs'].values():
        source = schedule['inputs'].get(row['input'], {})
        if source.get('physical_source') != row['physical_source'] or not source.get('role', '').startswith('freeway'):
            raise ValueError('Freeway origin differs from the native input forecast source')
    runtime['source'] = path
    runtime['source_sha256'] = sha256(ROOT / path)
    net.offramp_route_inventory = runtime
    return {'offramp_route_inventory_enabled': 1., 'offramp_route_inventory_source': path,
        'offramp_route_inventory_semantics': 'Observed current routes retained; constant future eligible choices expanded once as expected mass; accepted-flow cell advection',
        'offramp_route_inventory_branches': deepcopy(runtime['branches'])}


def _add(target, source, amount=1.):
    for key, value in source.items():
        target[key] = target.get(key, 0.) + float(value) * amount


def _classes(prefix, weights):
    return {prefix + '|' + target: share for target,share in weights.items() if share > 0}


def _update_missed_target_diagnostics(state):
    inv = state.offramp_route_inventory_state
    diagnostic = inv.get('missed_target_diagnostics')
    if diagnostic is None:
        return
    def missed(row):
        return math.fsum(value for key,value in row.items()
                         if key.rsplit('|',1)[-1].startswith(_MISSED_TARGET))
    diagnostic['current_missed_target_veh'] = math.fsum(
        missed(row) for rows in inv['cells'].values() for row in rows)
    diagnostic['terminal_censored_veh'] = math.fsum(
        missed(rows[-1]) for rows in inv['cells'].values())


def initialize_inventory(state, cfg, raw):
    if not inventory_enabled(cfg):
        return {}
    from evaluation.controllers.projection_support import complete_records
    from evaluation.controllers.vehicle_routes import complete_vehicle_routes
    from evaluation.controllers.area_freeway_accounting import continuity_vehicle_counts
    runtime = cfg.network.offramp_route_inventory
    observed = complete_vehicle_routes(raw, required=True)
    cells = {fw: [{} for _ in bounds[:-1]] for fw,bounds in runtime['bounds'].items()}
    known = null = 0
    missed = []
    for physical in complete_records(raw):
        if str(physical['link_no']) not in runtime['physical']:
            continue
        fw, position, cell = _position(runtime, physical['link_no'], physical['position_m'])
        route = observed[physical['veh_no']]
        if route['route_decision_no'] is None:
            weights = _future_distribution(runtime, fw, position)
            prefix = 'observed_null'
            null += 1
        else:
            key = str(route['route_decision_no']) + ':' + str(route['route_no'])
            selected = runtime['routes'].get(key)
            if route['route_decision_type'].upper() != 'STATIC' or selected is None:
                raise ValueError('Observed freeway route is outside the compiled native paths')
            prefix = 'observed_route:' + key
            target = selected['target']
            branch = runtime['branches'].get(target)
            if branch and branch['freeway'] == fw and branch['source_chain_m'] < position:
                # Native can retain a STATIC route after missing its connector.
                # Preserve this observed identity and mass, not a new destination
                # or NULL eligibility. Its forward fate remains unconfirmed even
                # if another decision lies ahead; do not redraw that choice.
                weights = {_MISSED_TARGET + target: 1.}
                missed.append({'veh_no': physical['veh_no'], 'route': key, 'target': target,
                    'freeway': fw, 'cell': cell, 'link_no': physical['link_no'],
                    'position_m': physical['position_m'], 'chain_m': position,
                    'target_source_chain_m': branch['source_chain_m'],
                    'past_target_m': position - branch['source_chain_m'],
                    'physical_link_on_selected_route': str(physical['link_no']) in selected['path']})
            else:
                if str(physical['link_no']) not in selected['path']:
                    raise ValueError('Observed freeway route is outside the compiled native paths')
                weights = _route_distribution(runtime, selected, fw, position)
            known += 1
        _add(cells[fw][cell], _classes(prefix, weights))
    origins = {fw: _classes('expected_input:' + row['input'], row['weights'])
               for fw,row in runtime['inputs'].items()}
    for fw, row in origins.items():
        for key in row:
            row[key] *= float(state.mainline_origin_queue.get(fw, 0.))
    state.offramp_route_inventory_state = {'schema': 'offramp-route-stock/v1', 'cells': cells, 'origins': origins}
    if missed:
        state.offramp_route_inventory_state['missed_target_diagnostics'] = {
            'observed_missed_target_veh': len(missed),
            'policy': 'Observed route retained; accepted forward transport only; no branch redraw or normal terminal TD; final-cell stock remains censored'}
        _update_missed_target_diagnostics(state)
    assert_inventory(state, cfg, continuity_vehicle_counts(state, cfg))
    metadata = {'offramp_route_inventory_initial_known_veh': known,
                'offramp_route_inventory_initial_null_veh': null}
    if missed:
        metadata.update(offramp_route_inventory_initial_missed_target_veh=len(missed),
            offramp_route_inventory_initial_missed_targets=missed,
            offramp_route_inventory_missed_target_diagnostics=deepcopy(
                state.offramp_route_inventory_state['missed_target_diagnostics']))
    return metadata


def assert_inventory(state, cfg, counts):
    inv = state.offramp_route_inventory_state
    runtime = cfg.network.offramp_route_inventory
    if inv.get('schema') != 'offramp-route-stock/v1' or set(inv['cells']) != set(counts):
        raise ValueError('Invalid passive freeway route inventory')
    for fw, rows in inv['cells'].items():
        if len(rows) != len(counts[fw]):
            raise ValueError('Route inventory cell count differs')
        for i, (row, amount) in enumerate(zip(rows, counts[fw])):
            for key, value in row.items():
                target = key.rsplit('|',1)[-1]
                if not math.isfinite(value) or value < -1e-9:
                    raise ValueError('Negative or nonfinite route inventory')
                if target.startswith(_MISSED_TARGET):
                    branch = runtime['branches'].get(target[len(_MISSED_TARGET):])
                    if branch is None or branch['freeway'] != fw or branch['source_cell'] > i:
                        raise ValueError('Unconfirmed missed target is not behind its current cell')
                elif target != 'terminal' and (target not in runtime['branches'] or
                        runtime['branches'][target]['freeway'] != fw or
                        runtime['branches'][target]['source_cell'] < i):
                    raise ValueError('Route target passed its physical source cell')
            if not math.isclose(math.fsum(row.values()), amount, abs_tol=1e-7, rel_tol=1e-10):
                raise ValueError(f'Route inventory is not the existing freeway stock partition: {fw}:{i}')
        if any(not math.isfinite(value) or value < -1e-9 for value in inv['origins'][fw].values()):
            raise ValueError('Negative or nonfinite route origin inventory')
        if not math.isclose(math.fsum(inv['origins'][fw].values()), state.mainline_origin_queue[fw], abs_tol=1e-7, rel_tol=1e-10):
            raise ValueError('Route inventory origin queue partition differs')


def branch_capacities(state, cfg, duration_h):
    from src.models import urban_queue_model as queue_model
    if duration_h <= 0:
        raise ValueError('Positive branch receiving interval required')
    result = {key: queue_model._effective_available_space(state, cfg, row['receiver']) / duration_h
              for key,row in cfg.network.offramp_route_inventory['branches'].items()}
    if any(not math.isfinite(value) or value < 0 for value in result.values()):
        raise ValueError('Offramp receiving stock must be finite and nonnegative')
    return result


def validate_origin_demand(state, cfg, demand):
    """Keep native source quantities and the existing forecast totals identical."""
    if not inventory_enabled(cfg):
        return
    from evaluation.controllers.shared_approach import demand_amount
    start = float(state.time_sec)
    end = start + float(cfg.simulation.control_interval)
    if not math.isfinite(start) or end <= start:
        raise ValueError('Offramp native source forecast needs a finite control interval')
    schedule = cfg.network.native_input_schedule['inputs']
    for fw, source in cfg.network.offramp_route_inventory['inputs'].items():
        expected = demand_amount(schedule[source['input']]['schedule'], start, end)*3600./(end-start)
        actual = demand.freeway_mainline.get(fw)
        if actual is None or not math.isfinite(actual) or not math.isclose(actual, expected, abs_tol=1e-6, rel_tol=1e-10):
            raise ValueError('Freeway forecast differs from its declared native input source: ' + fw)


def sending_requests(state, cfg, fw, flows, duration_h):
    """Route-specific demand; blocked target mass never becomes through demand."""
    runtime = cfg.network.offramp_route_inventory
    branch = {key: 0. for key,row in runtime['branches'].items() if row['freeway'] == fw}
    mainline = []
    for i, (flow, stock) in enumerate(zip(flows, state.offramp_route_inventory_state['cells'][fw])):
        total = math.fsum(stock.values())
        demand = min(max(0., flow), total/duration_h)
        off = censored = 0.
        for key, amount in stock.items():
            target = key.rsplit('|',1)[-1]
            if target in branch and runtime['branches'][target]['source_cell'] == i:
                value = demand * amount / total if total else 0.
                branch[target] += value
                off += value
            elif i == len(flows)-1 and target.startswith(_MISSED_TARGET):
                censored += amount
        sending = max(0., demand-off)
        if censored:
            # Censoring is uncertainty accounting, not a physical blockage or
            # a claim on shared terminal capacity. Normal stock can use all
            # otherwise available service without a missed-stock multiplier.
            terminal_stock = math.fsum(amount for key,amount in stock.items()
                                      if key.rsplit('|',1)[-1] == 'terminal')
            sending = min(sending, terminal_stock/duration_h)
        mainline.append(sending)
    return mainline, branch


def advance_inventory(state, cfg, fw, *, mainline, terminal, offramps, entry,
                      generated, merges, duration_h):
    """Advect the old partition using only flows accepted by the cell allocator."""
    runtime = cfg.network.offramp_route_inventory
    inv = state.offramp_route_inventory_state
    old = inv['cells'][fw]
    new = [dict(row) for row in old]
    for i, row in enumerate(old):
        through = {}
        targets = defaultdict(dict)
        for key, amount in row.items():
            target = key.rsplit('|',1)[-1]
            if target in runtime['branches'] and runtime['branches'][target]['source_cell'] == i:
                targets[target][key] = amount
            elif i != len(old)-1 or not target.startswith(_MISSED_TARGET):
                through[key] = amount
        movements = [(through, (mainline[i] if i < len(old)-1 else terminal)*duration_h, i+1)]
        movements.extend((values, offramps.get(target,0.)*duration_h, None) for target,values in targets.items())
        for composition, amount, receiver in movements:
            total = math.fsum(composition.values())
            if amount > total + 1e-7 or amount < -1e-9:
                raise ValueError('Accepted route flow exceeds its class stock')
            if total and amount:
                fraction = min(1., amount/total)
                _add(new[i], composition, -fraction)
                if receiver is not None and receiver < len(old):
                    _add(new[receiver], composition, fraction)
    source = runtime['inputs'][fw]
    origin = inv['origins'][fw]
    _add(origin, _classes('expected_input:' + source['input'], source['weights']), generated*duration_h)
    total = math.fsum(origin.values())
    amount = entry*duration_h
    if amount > total + 1e-7:
        raise ValueError('Accepted mainline entry exceeds its source inventory')
    if total and amount:
        admission = {key: value*min(1., amount/total) for key,value in origin.items()}
        _add(origin, admission, -1.)
        _add(new[0], admission)
    for ramp, flow in merges.items():
        source = runtime['merges'][ramp]
        if source['freeway'] == fw:
            _add(new[source['cell']], _classes('expected_merge:' + ramp, source['weights']), flow*duration_h)
    inv['cells'][fw] = [{key: max(0., value) for key,value in row.items() if value != 0.} for row in new]
    _update_missed_target_diagnostics(state)
