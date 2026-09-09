"""Declared internal vehicle generation into an existing finite transit stock.

The native input schedule is desired demand. Only admitted vehicles are added
to model/area inventory; blocked demand is kept separately. This never fills an
external gate or redraws the existing receiver's downstream turn proportions.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from copy import deepcopy
import csv
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from evaluation.controllers.network_provenance import snapshot_network_sha256
from evaluation.controllers.projection_support import complete_records
from evaluation.controllers.control_area_objective import emit_input, physical_membership_from_ledger
from evaluation.controllers.shared_approach import demand_amount

ROOT = Path(__file__).resolve().parents[2]


def _read(pin):
    path = ROOT/pin['path']
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != pin['sha256']:
        raise ValueError(f'Native internal input source fingerprint differs: {path}')
    return path


def _csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as file:
        return list(csv.DictReader(line for line in file if not line.startswith('#')))


def _finite(value, name):
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError(f'Native internal input {name} must be finite and nonnegative')
    return result


def _signal_authority(cfg, no):
    authority = getattr(cfg.network, 'native_input_signal_authority', None)
    if not isinstance(authority, dict):
        raise ValueError('Native selected-signal input lacks configured authority')
    evidence = json.loads(_read({'path': authority['source_path'],
                                'sha256': authority['source_sha256']}).read_text(encoding='utf-8-sig'))
    proof = authority.get('inputs', {}).get(no)
    original = evidence.get('inputs', {}).get(no)
    if (not isinstance(proof, dict) or not isinstance(original, dict)
            or not proof.get('source_contract_validated')
            or any(proof.get(key) != value for key, value in original.items())
            or authority['network_sha256'] != evidence['network']['sha256']):
        raise ValueError('Native selected-signal authority fingerprint/contract differs')
    expected = {head['lane'].split()[1]: float(head['pos']) for head in original['source_heads']}
    if proof.get('head_position_by_lane_m') != expected:
        raise ValueError('Native selected-signal lane positions differ')
    from evaluation.controllers.physical_movement_routes import path_membership
    physical=physical_membership_from_ledger(json.loads(_read(evidence['membership']).read_text(encoding='utf-8-sig')))
    route=path_membership(original['physical_path'],physical)
    route.update(from_link=original['physical_source'],connector=original['connector'],to_link=original['physical_path'][-1])
    expected_route={'status':'unique','source_inside':True,'target_inside':True,'physical_turns':[route],
                    'outward_crossings_per_vehicle':0,'inward_crossings_per_vehicle':0}
    if proof.get('movement_area_route')!=expected_route:
        raise ValueError('Native selected-signal area path differs')
    return authority, proof


def _projection_table(row):
    if row.get('kind') == 'selected_signal_source':
        return dict(row['physical_projection_to_storage'])
    return dict.fromkeys(row['physical_projection_links'], row['target_storage'])


def record_partition(cfg, raw):
    """Return full-link storage moments from actual lane/position observations."""
    spec = getattr(cfg.network, 'native_internal_inputs', None)
    if spec is None:
        return {}, {}
    records = complete_records(raw)
    result, metadata = {}, {}
    for no, row in spec['inputs'].items():
        if row.get('kind') != 'selected_signal_source':
            continue
        authority, proof = _signal_authority(cfg, no)
        source = proof['physical_source']
        if source in result:
            raise ValueError('Native physical record partitions overlap')
        if authority['network_sha256'] != spec['network_sha256']:
            raise ValueError('Native record partition has another network')
        partitions = {target: {'count': 0., 'stopped_count': 0., 'speed_sum_kph': 0.}
                      for target in (proof['pre_head_storage'], proof['post_head_storage'])}
        for vehicle in records:
            if str(vehicle['link_no']) != source:
                continue
            lane = str(vehicle['lane_no'])
            if lane not in proof['head_position_by_lane_m']:
                raise ValueError('Native source record has an unverified signal lane')
            target = proof['pre_head_storage'] if float(vehicle['position_m']) <= proof['head_position_by_lane_m'][lane] else proof['post_head_storage']
            bucket = partitions[target]
            bucket['count'] += 1.
            bucket['stopped_count'] += float(bool(vehicle['stopped']))
            bucket['speed_sum_kph'] += float(vehicle['speed_kph'])
        result[source] = partitions
        metadata[source] = {'input_no': no, 'network_sha256': authority['network_sha256'],
                            'source_path': authority['source_path'], 'source_sha256': authority['source_sha256']}
    return result, metadata


def empirical_source_choice(proof, source, forward, tree, links, raw):
    calibration=json.loads(_read(proof['calibration']).read_text(encoding='utf-8-sig'))
    input_no=proof['input_no'];topology=calibration.get('topology',{}).get(source,{})
    measured=calibration.get('inputs',{}).get(input_no,{}).get('all_0_5400',{})
    observed_branches=measured.get('branches',[])
    selected_connector=proof['connector'];sample=proof['resolved_source_vehicles']
    calibration_networks={value for key,value in calibration.get('source_sha256',{}).items()
                          if key.replace('\\','/').endswith('.inpx')}
    if (calibration.get('schema')!='native-input-observed-branch-calibration/v1'
            or calibration.get('seed')!=proof['calibration_seed']
            or calibration_networks!={snapshot_network_sha256(raw)}
            or proof.get('prior_probability')!=1. or proof.get('validation_scope')!='offline_seed13_requires_seed14_holdout'
            or topology.get('input_no')!=input_no or topology.get('source')!=source
            or topology.get('incoming_connectors') or topology.get('static_decisions')
            or any(x.get('link')==source for x in tree.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic'))
            or {x['connector'] for x in topology.get('outgoing',[])}!=forward
            or {x['connector'] for x in observed_branches}!=forward
            or measured.get('source_observed_unique_ids')!=sample or measured.get('resolved_ids')!=sample
            or not sample or measured.get('unresolved_or_censored_ids')!=0
            or any(measured.get(key) for key in ('not_first_seen_on_source_ids','repeated_source_after_departure_ids',
                'source_gap_ids','departure_gap_above_1_sec_ids'))
            or any(x['count']!=(sample if x['connector']==selected_connector else 0) for x in observed_branches)
            or selected_connector not in forward):
        raise ValueError('Empirical native source prior lacks complete pinned cohort evidence')
    for branch in topology['outgoing']:
        connector=links[branch['connector']]
        if (connector.find('toLinkEndPt').get('lane').split()[0]!=branch['target']
                or float(connector.find('fromLinkEndPt').get('pos'))!=branch['from_pos_m']):
            raise ValueError('Empirical source prior topology changed')
    return {selected_connector}


def _common_approach(row, cfg, raw, links, tree, contract, physical, claimed):
    """Validate one source's complete path family to one existing approach.

    This admits generation before its first selected stopline. It never uses a
    native decision upstream of the input merge as that input's route prior.
    Existing approach routing remains a declared approximation of future turns.
    """
    source, target = row['physical_source'], row['target_storage']
    paths = row['approach_paths']
    if (not paths or row['approach_path'] != paths[0] or
            len({tuple(path) for path in paths}) != len(paths)):
        raise ValueError('Common native approach paths are missing or duplicated')
    terminal = paths[0][-1]
    if target not in cfg.network.urban_link_storage_veh:
        raise ValueError('Common native target is not an existing storage')
    if _finite(raw['demand']['urban_volume_vph_by_gate'].get(target, 0), 'existing gate forecast') != 0:
        raise ValueError('Common native target already has external gate demand')
    plan = json.loads(_read(row['selected_plan']).read_text(encoding='utf-8-sig'))
    controllers = plan['controllers']
    selected = {(sc, str(group)) for sc, controller in controllers.items()
                for groups in controller['phase_signal_groups'].values() for group in groups}
    heads = {x.get('no'): x for x in tree.findall('./signalHeads/signalHead')}
    expected_heads = {key for key, x in heads.items()
        if x.get('lane').split()[0] == terminal and tuple(x.get('sg').split()) in selected}
    if not expected_heads or set(row['approach_heads']) != expected_heads:
        raise ValueError('Common native approach selected heads differ')
    if any(heads[key].get('allVehTypes') != 'true' or float(heads[key].get('complRate')) != 1
           for key in expected_heads):
        raise ValueError('Common native approach has restricted head authority')
    entries, chosen, lengths, excluded_heads = defaultdict(list), defaultdict(set), [], set()
    for path in paths:
        if (path[0] != source or path[-1] != terminal or len(path) % 2 != 1
                or any(key not in links or physical.get(key) is not True for key in path)):
            raise ValueError('Common native path has different source/stopline or leaves Omega')
        previous_entry, distance = 0., 0.
        for road, connector, following in zip(path[::2], path[1::2], path[2::2]):
            x = links[connector]; a, b = x.find('fromLinkEndPt'), x.find('toLinkEndPt')
            if (a is None or b is None or a.get('lane').split()[0] != road
                    or b.get('lane').split()[0] != following or float(a.get('pos')) < previous_entry):
                raise ValueError('Disconnected/backward common native path')
            entries[road].append(previous_entry); chosen[road].add(connector)
            for key, head in heads.items():
                if head.get('lane').split()[0] == road and previous_entry <= float(head.get('pos')) <= float(a.get('pos')):
                    if tuple(head.get('sg').split()) in selected:
                        raise ValueError(f'Common native path crosses another selected signal first: source={source} head={key} sg={head.get("sg")} road={road}')
                    excluded_heads.add(key)
            points = [tuple(float(p.get(k, 0)) for k in ('x', 'y', 'zOffset'))
                      for p in x.findall('./geometry/linkPolyPts/linkPolyPoint')]
            distance += float(a.get('pos'))-previous_entry+sum(math.dist(u, v) for u, v in zip(points, points[1:]))
            previous_entry = float(b.get('pos'))
        stop = min(float(heads[key].get('pos')) for key in expected_heads)
        if stop < previous_entry:
            raise ValueError('Common native stopline is behind its entry')
        if any(x.find('fromLinkEndPt') is not None and
               x.find('fromLinkEndPt').get('lane').split()[0] == terminal and
               previous_entry <= float(x.find('fromLinkEndPt').get('pos')) < stop for x in links.values()):
            raise ValueError('Common native approach has a pre-head bypass')
        lengths.append(distance+stop-previous_entry)
    coverage = row['branch_coverage']
    if set(coverage) != set(chosen):
        raise ValueError('Common native branch coverage road set differs')
    for road, connectors in chosen.items():
        forward = {key for key, x in links.items() if x.find('fromLinkEndPt') is not None
            and x.find('fromLinkEndPt').get('lane').split()[0] == road
            and float(x.find('fromLinkEndPt').get('pos')) >= min(entries[road])}
        proof = coverage[road]
        if proof['basis'] == 'all_forward_connectors':
            allowed = forward
        elif proof['basis'] == 'native_decision':
            decision = tree.find(f"./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='{proof['decision']}']")
            if (decision is None or decision.get('link') != road or decision.get('allVehTypes') != 'true'
                    or decision.get('routeChoiceMeth') != 'STATIC' or
                    not max(entries[road]) <= float(decision.get('pos')) <= min(float(links[c].find('fromLinkEndPt').get('pos')) for c in forward)):
                raise ValueError('Common native decision is absent, restricted or behind the input merge')
            native_paths = [[road]+[x.get('key') for x in route.findall('./linkSeq/intObjectRef')]+[route.get('destLink')]
                            for route in decision.findall('./vehRoutSta/vehicleRouteStatic')]
            allowed = {path[1] for path in native_paths}
            if not native_paths or not allowed <= forward:
                raise ValueError('Common native decision selects an invalid connector')
        elif proof['basis'] == 'empirical_source_choice':
            if road!=source:raise ValueError('Empirical branch evidence is source-only')
            allowed=empirical_source_choice(proof,source,forward,tree,links,raw)
        else:
            raise ValueError('Unknown common native branch evidence')
        if connectors != allowed:
            raise ValueError('Common native paths omit or invent a possible branch')
    for number in row.get('ignored_upstream_decisions', []):
        decision = tree.find(f"./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='{number}']")
        if (decision is None or decision.get('link') not in entries or
                float(decision.get('pos')) >= min(entries[decision.get('link')])):
            raise ValueError('Declared upstream decision is not behind the input merge')
    for movement in row['target_movements']:
        spec = cfg.network.urban_movements.get(movement, {})
        if spec.get('origin') != target or not any(t.get('from_link') == terminal
                for t in contract.get('movement:'+movement, {}).get('physical_turns', [])):
            raise ValueError('Common native target lacks its canonical stopline')
    if {name for name, spec in cfg.network.urban_movements.items() if spec.get('origin') == target} != set(row['target_movements']):
        raise ValueError('Common native target has unreviewed movements')
    supports = set(row['physical_projection_links'])
    if supports != {source, paths[0][1]} or any(path[1] != paths[0][1] for path in paths) or claimed & supports:
        raise ValueError('Common native initial physical partition differs')
    claimed.update(supports)
    return {'minimum_approach_distance_m': min(lengths),
            'path_distance_bounds_m': [min(lengths), max(lengths)],
            'intermediate_unselected_heads': sorted(excluded_heads), 'source_contract_validated': True}


def configure(cfg, tuning, raw, detectors):
    source_path = tuning.get('urban', {}).get('native_internal_inputs')
    if source_path is None:
        if tuning.get('prediction', {}).get('native_input_schedule', False):
            raise ValueError('Native input schedule forecast requires a validated native input declaration')
        return {}
    if getattr(cfg.network, 'native_internal_inputs', None) is not None:
        raise ValueError('Native internal inputs must configure once before projection')
    evidence_bytes = (ROOT/source_path).read_bytes()
    evidence = json.loads(evidence_bytes.decode('utf-8-sig'))
    if evidence.get('schema') != 'native-internal-inputs/v1':
        raise ValueError('Unsupported native internal input contract')
    if sum(row.get('kind')=='native_choice_prehead' for row in evidence['inputs'].values())>1:
        raise ValueError('One native pre-head resource supports only one declared source subset')
    network_path = _read(evidence['network'])
    if snapshot_network_sha256(raw) != evidence['network']['sha256']:
        raise ValueError('Native internal input snapshot network differs')
    tree = ET.parse(network_path).getroot()
    links = {x.get('no'):x for x in tree.findall('./links/link')}
    physical = physical_membership_from_ledger(json.loads(_read(evidence['membership']).read_text(encoding='utf-8-sig')))
    manifest_path = Path(raw['run_provenance']['manifest_path'])
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes.decode('utf-8-sig'))
    if manifest['run_id'] != raw['run_provenance']['run_id']:
        raise ValueError('Native internal input manifest belongs to another run')
    files = manifest['files']
    pins = [('gate_map','urban_input_gate_map'), ('input_roles','vehicle_input_roles'), ('demand_profile','demand_profile')]
    for key, recorded in pins:
        _read(evidence[key])
        if files[recorded]['sha256'] != evidence[key]['sha256']:
            raise ValueError(f'Native internal input run {key} source differs')
    if raw.get('demand', {}).get('demand_profile') != 'real_world_inpx_time_profile_scaled':
        raise ValueError('Native internal input needs the reviewed all-interval runner profile')
    gates = {x['no']:x for x in _csv(ROOT/evidence['gate_map']['path'])}
    roles = {x['no']:x['role'].strip().lower() for x in _csv(ROOT/evidence['input_roles']['path'])}
    profile = {x['role'].strip().lower():_finite(x['multiplier'],'profile multiplier') for x in _csv(ROOT/evidence['demand_profile']['path'])}
    scale = _finite(manifest['demand_scale'],'demand scale')
    inputs = {x.get('no'):x for x in tree.findall('./vehicleInputs/vehicleInput')}

    def schedule(no):
        if no not in roles:
            raise ValueError(f'Native internal input role absent: {no}')
        factor = scale*profile.get('no:'+no, profile.get(roles[no],profile.get('__default__',1.)))
        rows = []
        for x in inputs[no].findall('./timeIntVehVols/timeIntervalVehVolume'):
            time = x.get('timeInt').split()
            if time[0] != '1' or x.get('cont') != 'false' or x.get('volType') not in {'STOCHASTIC','EXACT'}:
                raise ValueError('Unsupported native internal demand schedule semantics')
            rows.append({'start_sec':_finite(time[1],'interval start')/1000,
                         'rate_veh_h':_finite(x.get('volume'),'native volume')*factor,
                         'raw_rate_veh_h':float(x.get('volume')), 'factor':factor})
        if not rows or rows[0]['start_sec'] != 0 or any(a['start_sec']>=b['start_sec'] for a,b in zip(rows,rows[1:])):
            raise ValueError('Native internal input intervals are unordered or missing')
        return rows

    # The runner reports the same original-volume × role/no override × scale
    # aggregate. This guards against using an unrelated live demand profile.
    expected_internal = sum(demand_amount(schedule(no),raw['sim_sec'],raw['sim_sec']+1)*3600
        for no,gate in gates.items() if gate['status']=='internal' and no in inputs)
    observed_internal = raw['demand'].get('urban_internal_volume_vph')
    if observed_internal is None or not math.isclose(float(observed_internal),expected_internal,abs_tol=1e-6):
        raise ValueError('Native internal input scaled schedule differs from live internal-demand aggregate')
    records, specs, claimed = complete_records(raw), {}, set()
    contract = json.loads(_read(evidence['canonical_contract']).read_text(encoding='utf-8-sig'))
    for no, row in evidence['inputs'].items():
        source,target,path = row['physical_source'],row['target_storage'],row['approach_path']
        vi,gate = inputs.get(no),gates.get(no,{})
        if (vi is None or vi.get('link') != source or gate.get('link') != source
                or gate.get('status') != 'internal' or gate.get('gate')):
            raise ValueError('Native internal input is not the reviewed unmapped internal source')
        if any(x.find('toLinkEndPt') is not None and x.find('toLinkEndPt').get('lane').split()[0]==source for x in links.values()):
            raise ValueError('Native internal source also receives existing vehicles')
        if sum(x.get('link')==source for x in inputs.values()) != 1:
            raise ValueError('Native internal source has another vehicle input')
        if row.get('kind') == 'selected_signal_source':
            authority, proof = _signal_authority(cfg, no)
            expected_table = {proof['connector']: proof['post_head_storage']}
            if (authority['network_sha256'] != evidence['network']['sha256']
                    or source != proof['physical_source'] or target != proof['pre_head_storage']
                    or path != [source] or row.get('physical_projection_to_storage') != expected_table
                    or set(row['physical_projection_links']) != set(expected_table)
                    or claimed & (set(expected_table) | {source})
                    or not all(physical.get(key) is True for key in proof['physical_path'])
                    or cfg.network.urban_movements.get(proof['kept_movement'], {}).get('origin') != target):
                raise ValueError('Native selected-signal input differs from its validated partition')
            claimed.update(set(expected_table) | {source})
            specs[no] = {**row, 'schedule': schedule(no), 'source_contract_validated': True,
                         'minimum_approach_distance_m': max(proof['head_position_by_lane_m'].values())}
            continue
        if row.get('target_kind') == 'route_choice':
            from evaluation.controllers.route_choice_corridor import generated_input_contracts
            delegated = generated_input_contracts(cfg).get(no)
            if (delegated != {'physical_source': source, 'storage': target,
                              'native_decision': row.get('source_decision')}
                    or target not in cfg.network.urban_link_storage_veh
                    or row['physical_projection_links'] or path != [source]
                    or physical.get(source) is not True):
                raise ValueError('Native generated route input differs from its validated corridor')
            specs[no] = {**row, 'schedule': schedule(no), 'source_contract_validated': True,
                         'minimum_approach_distance_m': 0., 'projection_owner': 'route_choice_corridor'}
            continue
        if row.get('kind') in {'native_fixed_route','native_choice_prehead'}:
            if row['kind']=='native_fixed_route':
                from evaluation.controllers import native_input_routes as helper
            else:
                from evaluation.controllers import native_input_prehead as helper
            validated = helper.configure_input(cfg, row, tree, links, physical, contract, raw)
            if not isinstance(validated, dict) or not validated.get('source_contract_validated'):
                raise ValueError('Native fixed route input lacks its validated source contract')
            supports = set(row['physical_projection_links'])
            if claimed & supports:
                raise ValueError('Native fixed route input overlaps another input')
            claimed.update(supports)
            specs[no] = {**row, 'schedule': schedule(no), **validated}
            continue
        if row.get('validation') == 'common_approach':
            validated = _common_approach(row, cfg, raw, links, tree, contract, physical, claimed)
            specs[no] = {**row, 'schedule': schedule(no), **validated}
            continue
        if target not in cfg.network.urban_link_storage_veh or target not in cfg.network.boundary_in_links:
            raise ValueError('Native internal target is not an existing approach storage')
        if _finite(raw['demand']['urban_volume_vph_by_gate'].get(target,0),'existing gate forecast') != 0:
            raise ValueError('Native internal target already has external gate demand')
        if path[0] != source or len(path)%2!=1 or any(k not in links for k in path):
            raise ValueError('Invalid native internal input approach path')
        previous_entry, length = 0., 0.
        for road,connector,following in zip(path[::2],path[1::2],path[2::2]):
            x=links[connector];a,b=x.find('fromLinkEndPt'),x.find('toLinkEndPt')
            if (a is None or b is None or a.get('lane').split()[0]!=road or b.get('lane').split()[0]!=following
                    or float(a.get('pos'))<previous_entry):
                raise ValueError('Disconnected/backward native internal input path')
            pts=[tuple(float(p.get(k,0)) for k in ('x','y','zOffset')) for p in x.findall('./geometry/linkPolyPts/linkPolyPoint')]
            length+=float(a.get('pos'))-previous_entry+sum(math.dist(u,v) for u,v in zip(pts,pts[1:]))
            previous_entry=float(b.get('pos'))
        heads={x.get('no'):x for x in tree.findall('./signalHeads/signalHead')}
        approach_heads=[heads.get(key) for key in row['approach_heads']]
        if not approach_heads or any(x is None or x.get('lane').split()[0]!=path[-1] for x in approach_heads):
            raise ValueError('Native internal approach head differs')
        stop=min(float(x.get('pos')) for x in approach_heads)
        if stop<previous_entry:raise ValueError('Native internal receiving head is behind its entry')
        length+=stop-previous_entry
        decision=tree.find(f"./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='{row['source_decision']}']")
        routes=decision.findall('./vehRoutSta/vehicleRouteStatic') if decision is not None else []
        if (decision is None or decision.get('link')!=source or decision.get('allVehTypes')!='true'
                or decision.get('routeChoiceMeth')!='STATIC' or len(routes)!=1
                or routes[0].get('destLink')!=path[1] or routes[0].findall('./linkSeq/intObjectRef')):
            raise ValueError('Native internal source lacks its single selected connector')
        downstream=tree.find(f"./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='{row['downstream_decision']}']")
        if downstream is None or downstream.get('link')!=path[2]:
            raise ValueError('Native internal downstream routing source differs')
        for route in downstream.findall('./vehRoutSta/vehicleRouteStatic'):
            native_path=[downstream.get('link')]+[x.get('key') for x in route.findall('./linkSeq/intObjectRef')]+[route.get('destLink')]
            if native_path[:len(path)-2] != path[2:]:
                raise ValueError('Native internal downstream routes do not share the declared approach')
        for movement in row['target_movements']:
            spec=cfg.network.urban_movements.get(movement,{})
            route=contract.get('movement:'+movement,{})
            if spec.get('origin')!=target or not any(t.get('from_link')==path[-1] for t in route.get('physical_turns',[])):
                raise ValueError('Native internal origin lacks the declared canonical stopline')
        if {name for name,spec in cfg.network.urban_movements.items() if spec.get('origin')==target}!=set(row['target_movements']):
            raise ValueError('Native internal target has additional unreviewed movements')
        supports=row['physical_projection_links']
        if set(supports)!={source,path[1]} or claimed & set(supports) or not all(physical.get(k) is True for k in path):
            raise ValueError('Native internal projection/approach is not a disjoint inside partition')
        claimed.update(supports)
        specs[no]={**row,'schedule':schedule(no),'minimum_approach_distance_m':length,
            'source_contract_validated':True}
    cfg.network.native_internal_inputs={'schema':'native-internal-inputs-runtime/v1','inputs':specs,
        'source_path':source_path,'source_sha256':hashlib.sha256(evidence_bytes).hexdigest(),
        'network_sha256':evidence['network']['sha256'],'run_manifest_sha256':hashlib.sha256(manifest_bytes).hexdigest(),
        'demand_scale':scale,'observed_internal_demand_veh_h':observed_internal,
        'expected_internal_demand_veh_h':expected_internal}
    if tuning.get('prediction', {}).get('native_input_schedule', False):
        cfg.network.native_input_schedule = {'schema': 'native-input-schedule/v1',
            'run_id': manifest['run_id'], 'network_sha256': evidence['network']['sha256'],
            'inputs': {no: {'physical_source': inputs[no].get('link'), 'role': roles[no],
                'gate': gates.get(no, {}).get('gate', ''), 'status': gates.get(no, {}).get('status', ''),
                'schedule': schedule(no)} for no in inputs}}
    metadata = {'native_internal_inputs':deepcopy(cfg.network.native_internal_inputs)}
    if hasattr(cfg.network, 'native_input_schedule'):
        metadata['native_input_schedule_inputs'] = len(cfg.network.native_input_schedule['inputs'])
    return metadata


def prepare_projection(cfg, detectors, raw):
    spec=getattr(cfg.network,'native_internal_inputs',None)
    if spec is None: return detectors,raw,{}
    copied,prepared=deepcopy(detectors),deepcopy(raw)
    rows=defaultdict(list)
    for row in complete_records(raw): rows[str(row['link_no'])].append(row)
    table={link:target for s in spec['inputs'].values() for link,target in _projection_table(s).items()}
    for link,target in table.items():
        if link in copied.get('ramp_link_to_queues',{}) or link in copied.get('freeway_link_to_model_link',{}):
            raise ValueError('Native internal input overlaps freeway/ramp projection')
        local=prepared['local_observation'];count=len(rows[link])
        if link in local.get('link_counts',{}) and local['link_counts'][link]!=count:
            raise ValueError('Native internal local/full records disagree')
        local.setdefault('link_counts',{})[link]=count
        local.setdefault('link_stopped_counts',{})[link]=sum(bool(r['stopped']) for r in rows[link])
        if count:local.setdefault('link_speeds_kph',{})[link]=sum(r['speed_kph'] for r in rows[link])/count
        copied.setdefault('link_to_origins',{})[link]=[target]
        copied.setdefault('link_to_movements',{}).pop(link,None)
        copied.setdefault('transit_storage_projection',{})[link]=target
    copied['observable_links']=sorted(set(map(str,copied.get('observable_links',[])))|set(table),key=int)
    copied['native_internal_verified_physical_stock']=table
    partitions,proof=record_partition(cfg,raw)
    for link,buckets in partitions.items():
        count=sum(r['count'] for r in buckets.values())
        local=prepared['local_observation']
        if link in local.get('link_counts',{}) and local['link_counts'][link]!=count:
            raise ValueError('Native partition local/full records disagree')
        local.setdefault('link_counts',{})[link]=count
        local.setdefault('link_stopped_counts',{})[link]=sum(r['stopped_count'] for r in buckets.values())
        if count:local.setdefault('link_speeds_kph',{})[link]=sum(r['speed_sum_kph'] for r in buckets.values())/count
        copied.setdefault('link_to_origins',{})[link]=list(buckets)
        copied.setdefault('link_to_movements',{}).pop(link,None)
        copied.setdefault('transit_storage_projection',{})[link]='physical_record_partition'
    if partitions:
        copied['physical_record_storage_projection']=partitions
        copied['native_internal_record_partition_proof']=proof
        copied['observable_links']=sorted(set(copied['observable_links'])|set(partitions),key=int)
    return copied,prepared,{'native_internal_projection':table,'native_internal_record_partitions':partitions}


def projection_claims(cfg, network_sha256):
    spec=getattr(cfg.network,'native_internal_inputs',None)
    if spec is None:return {}
    raw=(ROOT/spec['source_path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=spec['source_sha256'] or spec['network_sha256']!=network_sha256:
        raise ValueError('Native internal verified stock source differs')
    evidence=json.loads(raw.decode('utf-8-sig'))
    expected={}
    if set(spec['inputs'])!=set(evidence['inputs']):raise ValueError('Native internal verified input set differs')
    for no,row in spec['inputs'].items():
        proof=evidence['inputs'][no]
        if not row.get('source_contract_validated') or any(row.get(k)!=v for k,v in proof.items()):
            raise ValueError('Native internal verified stock contract differs')
        for link,target in _projection_table(row).items():
            if link in expected:raise ValueError('Native internal physical partitions overlap')
            expected[link]=target
    return expected


def initialize(state,cfg,raw,detectors):
    spec=getattr(cfg.network,'native_internal_inputs',None)
    if spec is None:return {}
    if hasattr(state,'native_internal_input_state'):raise ValueError('Native internal input initialized twice')
    assignment=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    counts=Counter(str(r['link_no']) for r in complete_records(raw))
    for link,target in projection_claims(cfg,spec['network_sha256']).items():
        if counts[link] and assignment.get(link)!={'storage:'+target:float(counts[link])}:
            raise ValueError('Native internal initial record has another stock assignment')
    partitions,proof_metadata=record_partition(cfg,raw)
    if partitions != detectors.get('physical_record_storage_projection',{}):
        raise ValueError('Native initial record partition was not projected')
    for link,buckets in partitions.items():
        expected={'storage:'+target:row['count'] for target,row in buckets.items() if row['count']}
        if assignment.get(link,{}) != expected:
            raise ValueError('Native initial signal stock was clipped or assigned differently')
    reservations={}
    if partitions:
        from src.models import urban_queue_model as uqm
        step=int(round(state.time_sec/cfg.simulation.T_u_sec));dt=cfg.simulation.T_u_sec
        for source,metadata in proof_metadata.items():
            _,proof=_signal_authority(cfg,metadata['input_no']);target=proof['pre_head_storage']
            count=partitions[source][target]['count']
            occupied=cfg.network.urban_link_storage_veh[target]-state.urban_link_storage[target]
            other=sum(values.get('storage:'+target,0.) for link,values in assignment.items() if link!=source)
            if not math.isclose(occupied,count,abs_tol=1e-8) or other:
                raise ValueError('Native pre-head stock is not exclusively observed on its source')
            for name in ('urban_arrival_buffer','urban_storage_release_buffer'):
                if not math.isclose(sum(getattr(state,name).get(target,{}).values()),count,abs_tol=1e-8):
                    raise ValueError('Native pre-head initial paired reservation differs from stock')
            due={}
            for vehicle in complete_records(raw):
                if str(vehicle['link_no'])!=source:continue
                distance=proof['head_position_by_lane_m'][str(vehicle['lane_no'])]-float(vehicle['position_m'])
                if distance<0:continue
                speed=max(float(vehicle['speed_kph']),cfg.network.urban_avg_speed_km_h/uqm.OBSERVED_SPEED_DELAY_CAP_RATIO)
                ready=step+max(1,math.ceil(distance/(speed/3.6)/dt))
                due[ready]=due.get(ready,0.)+1.
            state.urban_arrival_buffer[target]=dict(due)
            state.urban_storage_release_buffer[target]=dict(due)
            reservations[target]=dict(due)
    state.native_internal_input_state={'last_step':int(round(state.time_sec/cfg.simulation.T_u_sec))-1,
        'inputs':{no:{'desired_veh':0.,'admitted_veh':0.,'unadmitted_demand_veh':0.} for no in spec['inputs']}}
    # Existing transit buffers already reserve initial receiver occupancy once.
    metadata={'native_internal_initialized_inputs':list(spec['inputs'])}
    if reservations:metadata['native_pre_head_initial_ready_by_step']=reservations
    return metadata


def extend_area_routes(cfg):
    spec=getattr(cfg.network,'native_internal_inputs',None)
    if spec is None:return {}
    routes=dict(cfg.network.control_area_routes)
    for no,row in spec['inputs'].items():
        routes['input:internal:'+no]={'target_inside':True,'event_kind':'native_internal_generation',
            'physical_link':row['physical_source'],'target_storage':row['target_storage']}
        if row.get('kind') == 'selected_signal_source':
            _,proof=_signal_authority(cfg,no)
            routes['movement:'+proof['kept_movement']]=deepcopy(proof['movement_area_route'])
            routes['arrival:'+proof['kept_movement']]={'status':'unique','source_inside':True,
                'target_inside':True,'outward_crossings_per_vehicle':0,'inward_crossings_per_vehicle':0,
                'physical_link':proof['physical_source']}
    cfg.network.control_area_routes=routes
    return {'native_internal_generation_routes':len(spec['inputs'])}


def advance(state,control,demand,cfg,urban_step_index):
    spec=getattr(cfg.network,'native_internal_inputs',None)
    if spec is None:return {}
    local=getattr(state,'native_internal_input_state',None)
    if local is None or urban_step_index!=local['last_step']+1:
        raise ValueError('Native internal input requires initialized sequential candidate state')
    from src.models import urban_queue_model as uqm
    dt=cfg.simulation.T_u_sec; output={}
    for no,row in spec['inputs'].items():
        target=row['target_storage'];stats=local['inputs'][no]
        if float(demand.urban_boundary.get(target,0))!=0:
            raise ValueError('Native internal input would duplicate an external forecast')
        desired=demand_amount(row['schedule'],urban_step_index*dt,(urban_step_index+1)*dt)
        stats['desired_veh']+=desired;stats['unadmitted_demand_veh']+=desired
        admitted=min(stats['unadmitted_demand_veh'],uqm._effective_available_space(state,cfg,target))
        if admitted:
            state.urban_link_storage[target]-=admitted
            emit_input(state,cfg,'storage:'+target,admitted,route_key='input:internal:'+no)
            delegated = False
            if row.get('target_kind') == 'route_choice':
                from evaluation.controllers.route_choice_corridor import receive_generated
                delegated = receive_generated(state,cfg,no,admitted,urban_step_index)
                if not delegated:
                    raise ValueError('Native route input has no generated cohort receiver')
            elif row.get('kind') == 'native_fixed_route':
                from evaluation.controllers.native_input_routes import receive_generated
                delegated = receive_generated(state,cfg,no,admitted,urban_step_index)
                if not delegated:
                    raise ValueError('Native fixed route input has no generated cohort receiver')
            elif row.get('kind') == 'native_choice_prehead':
                from evaluation.controllers.native_input_prehead import receive_generated
                delegated = receive_generated(state,cfg,no,admitted,urban_step_index)
                if not delegated:
                    raise ValueError('Native pre-head input has no generated cohort receiver')
            # Existing receiver dynamics apply after generation. The measured
            # road path supplies a lower travel-time bound, not a new beta split.
            if not delegated:
                speed=max(float(state.urban_link_speed_kph.get(target,cfg.network.urban_avg_speed_km_h)),
                          cfg.network.urban_avg_speed_km_h/uqm.OBSERVED_SPEED_DELAY_CAP_RATIO)
                delay=max(1,uqm._link_delay_steps(state,cfg,target),math.ceil(row['minimum_approach_distance_m']/(speed/3.6)/dt))
                uqm._schedule(state.urban_arrival_buffer,target,urban_step_index+delay,admitted)
                uqm._schedule(state.urban_storage_release_buffer,target,urban_step_index+delay,admitted)
            stats['admitted_veh']+=admitted;stats['unadmitted_demand_veh']-=admitted
        if not math.isclose(stats['desired_veh'],stats['admitted_veh']+stats['unadmitted_demand_veh'],abs_tol=1e-8):
            raise AssertionError('Native internal desired/admitted/backlog accounting differs')
        output[no]={'desired_veh':desired,'generated_inside_veh':admitted,
                    'boundary_entry_veh':0.,'unadmitted_demand_veh':stats['unadmitted_demand_veh']}
    local['last_step']=urban_step_index
    return {'native_internal_input_step':output}
