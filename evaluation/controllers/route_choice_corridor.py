"""Finite physical prefix, one eligible route choice, and typed local arrivals.

No external demand is created. Unknown past choices are never redrawn: live
policy fails explicitly; a separately requested diagnostic policy holds them.
The caller owns accepted source-to-prefix stock transfer. Receipt only reserves
travel and debits the same physical-turn service budget used before acceptance.
"""
from __future__ import annotations
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from evaluation.controllers.projection_support import complete_records
from evaluation.controllers.vehicle_routes import complete_vehicle_routes
from evaluation.controllers.network_provenance import snapshot_network_sha256
from evaluation.controllers.physical_movement_routes import invalidate_topology_cache, path_membership
from evaluation.controllers.control_area_objective import emit_transfer, physical_membership_from_ledger, get_ledger

ROOT = Path(__file__).resolve().parents[2]
EPS = 1e-8
_NATIVE_PROGRAMS = {}


def _positive(value, name, *, zero=False):
    x = float(value)
    if not math.isfinite(x) or x < 0 or (not zero and x == 0):
        raise ValueError(f'{name} must be finite and {"nonnegative" if zero else "positive"}')
    return x


def _length(node):
    pts = [tuple(float(p.get(k, 0)) for k in ('x', 'y', 'zOffset'))
           for p in node.findall('./geometry/linkPolyPts/linkPolyPoint')]
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def _read_pinned(row):
    path = ROOT / row['path']
    if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
        raise ValueError(f'Route corridor source fingerprint changed: {path}')
    return path


def _native_program(proof):
    """Keep immutable parser objects out of pickled candidate configurations."""
    key=(proof['sig_file']['path'],proof['sig_file']['sha256'],proof['program_no'])
    if key not in _NATIVE_PROGRAMS:
        from plant.src.vissim_strict.signal_program import parse_sig
        _NATIVE_PROGRAMS[key]=parse_sig(_read_pinned(proof['sig_file']),proof['program_no'])
    return _NATIVE_PROGRAMS[key]


def configure(cfg, tuning, raw, detectors, *, per_lane_capacity_veh_h=None):
    """Before projection. Return copied detectors; absent flag is a no-op.

    per_lane_capacity_veh_h is the *existing* canonical capacity-installation
    metadata value. It is explicit so a different normalization is not invented.
    """
    option = tuning.get('urban', {}).get('route_choice_corridor')
    if option is None:
        return detectors, {}
    if not isinstance(option, dict) or option.get('unknown_policy') not in {'error', 'hold_diagnostic'}:
        raise ValueError('route_choice_corridor requires evidence_path and explicit unknown_policy')
    if getattr(cfg.network, 'route_choice_corridor', None):
        raise ValueError('Route corridor must configure once before raw projection')
    paths = option.get('evidence_paths', [option.get('evidence_path')])
    if not isinstance(paths, list) or not paths or any(not isinstance(p,str) for p in paths) or len(paths)!=len(set(paths)):
        raise ValueError('Route corridor requires distinct explicit evidence paths')
    specs, metadata = [], {}
    for path in paths:
        detectors, detail = _configure_one(cfg, raw, detectors, dict(option,evidence_path=path), per_lane_capacity_veh_h)
        specs.append(cfg.network.route_choice_corridor)
        metadata[path] = detail
    if len(specs)==1:
        return detectors, metadata[paths[0]]
    physical, storages, turns, renames = {}, {}, {}, {}
    for spec in specs:
        table = _projection_table(spec)
        if set(physical)&set(table) or set(storages)&set(spec['capacity_veh']) or set(turns)&set(spec['turns']):
            raise ValueError('Route corridors overlap physical stock, managed storage or accepted source')
        physical.update(table); storages.update(spec['capacity_veh'])
        turns.update(spec['turns']); renames.update(spec['renames'])
    cfg.network.route_choice_corridor = {'schema':'route-choice-corridors/v1','corridors':specs,
        'capacity_veh':storages,'turns':turns,'renames':renames,'unknown_policy':option['unknown_policy']}
    return detectors, {'route_choice_corridor_enabled':1.,'route_choice_corridors':metadata,
                       'route_choice_capacities_veh':storages,'route_choice_unknown_policy':option['unknown_policy']}


def _specs(cfg):
    spec = getattr(cfg.network, 'route_choice_corridor', None)
    return [] if spec is None else spec.get('corridors', [spec])


def _projection_table(spec):
    return {**dict.fromkeys(spec['prefix_links'],spec['prefix_storage']),
            **dict.fromkeys(spec['local_links'],spec['local_storage']), **spec['post_stopline_projection']}


def _movement_spec(cfg, movement):
    return next((spec for spec in _specs(cfg) if movement in spec['turns']), None)


def generated_input_contracts(cfg):
    result={}
    for spec in _specs(cfg):
        for no,row in spec.get('generated_inputs',{}).items():
            if no in result:raise ValueError('Native input is claimed by two route corridors')
            result[no]=dict(row)
    return result


def _validate_path(path, links):
    for left,right in zip(path,path[1:]):
        a,b=links[left],links[right]
        to=a.find('toLinkEndPt'); source=b.find('fromLinkEndPt')
        if to is not None:
            if to.get('lane').split()[0]!=right: raise ValueError('Route corridor connector target changed')
        elif source is None or source.get('lane').split()[0]!=left:
            raise ValueError('Route corridor connector source changed')


def _travel_segments(path,links,lengths,final_position):
    segments=[]
    for i,key in enumerate(path):
        node=links[key]
        prior=links[path[i-1]].find('toLinkEndPt') if i else None
        start=float(prior.get('pos')) if prior is not None else 0.
        stop=final_position if i==len(path)-1 else lengths[key] if node.find('toLinkEndPt') is not None else float(links[path[i+1]].find('fromLinkEndPt').get('pos'))
        if stop<start: raise ValueError('Route corridor path would turn behind its entry position')
        segments.append({'link':key,'start':start,'stop':stop})
    return segments


def _calibrated_native_service(document,proof):
    """Load an explicitly pinned source-specific prior, never trajectory truth."""
    pin=proof.get('calibrated_discharge')
    if pin is None:return None
    calibration=json.loads(_read_pinned(pin).read_text(encoding='utf-8'))
    if (calibration.get('schema')!='native-fixed-service-calibration/v1'
            or calibration.get('selected_estimator')!='sum_gap_count / sum_block_duration_upper_sec * 3600'
            or calibration.get('network_sha256')!=document['network']['sha256']
            or calibration.get('sig_sha256')!=proof['sig_file']['sha256']
            or set(document['generated_inputs'])!={pin['input_no']}):
        raise ValueError('Native source discharge calibration identity or estimator changed')
    row=calibration['inputs'][pin['input_no']]
    expected={'physical_source':document['decision_link'],'native_decision':document['decision'],
        'controller':proof['controller'],'signal_group':proof['signal_group'],'head':proof['head'],'lanes':1}
    if any(row.get(k)!=v for k,v in expected.items()):
        raise ValueError('Native source discharge calibration belongs to another head')
    gaps=0;upper_sum=0.;lower_sum=0.;last_end=-math.inf
    for block in row['blocks']:
        ids=block['vehicle_ids'];count=block['gap_count']
        first_lo=float(block['first_crossing_lower_sec']);first_hi=float(block['first_crossing_upper_sec'])
        last_lo=float(block['last_crossing_lower_sec']);last_hi=float(block['last_crossing_upper_sec'])
        if (block['input_no']!=pin['input_no'] or not isinstance(count,int) or count<=0
                or len(ids)!=count+1 or len(set(ids))!=len(ids)
                or not last_end<=first_lo<=first_hi<=last_lo<=last_hi
                or any(first_lo<=b and last_hi>=a for a,b in calibration['excluded_time_holdouts_sec'])):
            raise ValueError('Native source discharge block overlaps, leaks holdout, or loses cohort identity')
        upper=_positive(last_hi-first_lo,'Native discharge duration upper')
        lower=_positive(last_lo-first_hi,'Native discharge duration lower',zero=True)
        if abs(upper-float(block['duration_upper_sec']))>EPS or abs(lower-float(block['duration_lower_sec']))>EPS:
            raise ValueError('Native discharge block endpoint bounds disagree')
        gaps+=count;upper_sum+=upper;lower_sum+=lower;last_end=last_hi
    if not gaps or upper_sum<=0 or lower_sum<=0:raise ValueError('Native discharge calibration has no bounded evidence')
    selected=_positive(row['selected_service_veh_h'],'Native calibrated service')
    if (row['gap_count']!=gaps or abs(row['duration_upper_sum_sec']-upper_sum)>EPS
            or abs(row['duration_lower_sum_sec']-lower_sum)>EPS
            or abs(selected-3600*gaps/upper_sum)>EPS
            or abs(row['measurement_rate_lower_veh_h']-selected)>EPS
            or abs(row['measurement_rate_upper_veh_h']-3600*gaps/lower_sum)>EPS):
        raise ValueError('Native discharge calibration summary is not the selected conservative estimator')
    return selected


def _native_generation_contract(document,tree,heads,links,cfg):
    declared=document.get('generated_inputs',{})
    owned=set(document['prefix_links'])|set(document['local_links'])
    actual={x.get('no'):x.get('link') for x in tree.findall('./vehicleInputs/vehicleInput') if x.get('link') in owned}
    if set(actual)!=set(declared):
        raise ValueError('Route corridor cannot silently ignore an independent native input')
    for no,row in declared.items():
        if (row!={'physical_source':actual[no],'storage':document['prefix_storage'],'native_decision':document['decision']}
                or actual[no]!=document['decision_link'] or document['prefix_links']!=[actual[no]]
                or document['local_links']):
            raise ValueError('Generated route source requires its exact native input and source-only prefix')
        if any(n.find('toLinkEndPt') is not None and n.find('toLinkEndPt').get('lane').split()[0]==actual[no] for n in links.values()):
            raise ValueError('Generated route source has an undeclared incoming cohort')
    proof=document.get('native_fixed_service')
    prefix_heads={key:h for key,h in heads.items() if h.get('lane','').split()[0] in document['prefix_links']}
    if proof is None:
        if prefix_heads:raise ValueError('Finite pre-choice travel cannot bypass an unmodelled signal head')
        if declared:raise ValueError('Generated native choice requires an explicit source service contract')
        return None
    if len(declared)!=1 or set(prefix_heads)!={proof['head']}:
        raise ValueError('Native route service must cover every source head exactly')
    node=prefix_heads[proof['head']];controller=tree.find(f"./signalControllers/signalController[@no='{proof['controller']}']")
    if (controller is None or controller.get('type')!='FIXEDTIME' or controller.get('active')!='true'
            or int(controller.get('progNo'))!=proof['program_no']
            or float(controller.get('offset'))!=proof['controller_offset_sec']
            or node.get('sg').split()!=[proof['controller'],proof['signal_group']]
            or node.get('lane').split()!=[document['decision_link'],'1']
            or node.get('allVehTypes')!='true' or float(node.get('complRate'))!=1
            or len(links[document['decision_link']].findall('./lanes/lane'))!=1):
        raise ValueError('Native fixed source SC/SG/head/lane identity changed')
    plan=json.loads(_read_pinned(proof['selected_plan']).read_text(encoding='utf-8-sig'))
    if proof['controller'] in plan['controllers'] or 'SC'+proof['controller'] in cfg.network.signals:
        raise ValueError('Native fixed source is selected for variable controller actuation')
    sig=_read_pinned(proof['sig_file'])
    if sig.name!=controller.get('supplyFile2','').replace('#data#',''):
        raise ValueError('Native fixed source supply file changed')
    program=_native_program(proof)
    if proof['signal_group'] not in program.sg_timelines:
        raise ValueError('Native source group has no compiled timeline')
    position=float(node.get('pos'))
    if not document['decision_position_m']<position:
        raise ValueError('Native input choice must precede its source stopline')
    result={**proof,'head_position_m':position,'lanes':1}
    calibrated=_calibrated_native_service(document,proof)
    if calibrated is not None:result['calibrated_service_veh_h']=calibrated
    return result


def _calibrated_turn_services(document, tree, links, heads, specs, per_lane):
    """One observed aggregate resource prior; no FZP or future truth at runtime."""
    pin=document.get('service_resource_calibration')
    if pin is None:return {}
    calibration=json.loads(_read_pinned(pin).read_text(encoding='utf-8'))
    if (calibration.get('schema')!='physical-shared-service-calibration/v1'
            or calibration.get('classification')!='offline_achieved_green_discharge_lower_bound'
            or calibration.get('selected_estimator')!='verified_crossing_count / full_train_native_green_seconds * 3600'
            or calibration.get('network')!=document['network'] or calibration.get('seed')!=13):
        raise ValueError('Shared service prior identity or estimator changed')
    row=calibration['resource']; connector=row['connector']; node=links[connector]
    source,target=node.find('fromLinkEndPt'),node.find('toLinkEndPt')
    lanes=len(node.findall('./lanes/lane')); first=int(source.get('lane').split()[1])
    if (source.get('lane').split()[0]!=row['source_link'] or target.get('lane').split()[0]!=row['target_link']
            or row['lanes']!=lanes or abs(_positive(row['inherited_service_veh_h'],'Inherited resource service')-lanes*per_lane)>EPS):
        raise ValueError('Shared service prior physical resource or inherited scale changed')
    upstream={str(lane):[h for h in heads.values() if h.get('lane')==row['source_link']+' '+str(lane)
                        and float(h.get('pos'))<float(source.get('pos'))] for lane in range(first,first+lanes)}
    if (set(upstream)!=set(row['head_by_lane']) or any(len(v)!=1 or v[0].get('no')!=row['head_by_lane'][k]
            or v[0].get('sg')!=row['controller']+' '+row['signal_group'] for k,v in upstream.items())):
        raise ValueError('Shared service prior does not cover the exact upstream heads')
    members=[r for r in document['incoming_turns'].values() if r['connector']==connector]
    if (len(row['members'])!=len(set(row['members'])) or set(r['keep'] for r in members)!=set(row['members'])
            or any(r['source_link']!=row['source_link'] or r['signal_controlled'] is not True
                or specs[r['keep']]['signal']!=row['signal'] or specs[r['keep']]['phase']!=row['phase'] for r in members)):
        raise ValueError('Shared service prior must cover every alias of one signal resource')
    clock=calibration['native_clock']; sc=next(s for s in tree.findall('./signalControllers/signalController') if s.get('no')==row['controller'])
    sig=(_read_pinned(document['network']).parent/sc.get('supplyFile2').removeprefix('#data#')).resolve()
    if (sc.get('type')!='FIXEDTIME' or sc.get('active')!='true' or int(sc.get('progNo'))!=clock['program_no']
            or float(sc.get('offset'))!=clock['controller_offset_sec'] or sig!=_read_pinned(clock['sig_file']).resolve()
            or clock['lsa_state_mismatch_seconds']):
        raise ValueError('Shared service prior native clock changed')
    program=_native_program(clock)
    if program.program_offset_sec!=clock['program_offset_sec'] or program.cycle_length_sec!=clock['cycle_sec']:
        raise ValueError('Shared service prior program timeline changed')
    from evaluation.controllers.fixed_signal_schedule import _union_green_overlap
    train=calibration['train']; windows=train['windows_sec']; holdouts=calibration['time_holdouts_excluded_from_fit_sec']
    if windows!=[[0,900],[1350,2700],[3150,5400]] or holdouts!=[[900,1350],[2700,3150]]:
        raise ValueError('Shared service prior must preserve the reviewed time holdouts')
    exposure=sum(_union_green_overlap(program,(row['signal_group'],),a,b,clock['controller_offset_sec']) for a,b in windows)
    events=train['events']; seen=set()
    for event in events:
        lo,hi=event['lower_sec'],event['upper_sec']; no=event['vehicle_id']; lane=str(event['lane'])
        key=(no,event['head'],lo,hi)
        if (not isinstance(no,int) or isinstance(no,bool) or no<=0 or not all(math.isfinite(x) for x in (lo,hi))
                or not 0<hi-lo<=1 or not any(a<lo<hi<b for a,b in windows)
                or lane not in row['head_by_lane'] or event['head']!=row['head_by_lane'][lane]
                or event['observed_subsequent_connector']!=connector or key in seen
                or lo<clock['lsa_first_observed_sec']
                or abs(_union_green_overlap(program,(row['signal_group'],),lo,hi,clock['controller_offset_sec'])-(hi-lo))>EPS):
            raise ValueError('Shared service prior event duplicates, leaks holdout, or loses physical/GREEN proof')
        seen.add(key)
    selected=_positive(row['selected_service_veh_h'],'Shared service prior')
    if (not events or train['crossing_events']!=len(events) or train['unique_vehicle_ids']!=len({e['vehicle_id'] for e in events})
            or abs(_positive(train['native_green_exposure_sec'],'Train exposure')-exposure)>EPS or abs(selected-3600*len(events)/exposure)>EPS
            or abs(_positive(train['achieved_green_discharge_lower_bound_veh_h'],'Train lower bound')-selected)>EPS):
        raise ValueError('Shared service prior is not the train-only aggregate lower bound')
    return {connector:{'service_veh_h':selected,'calibration':pin,'members':tuple(row['members']),
                       'classification':calibration['classification']}}


def _configure_one(cfg, raw, detectors, option, per_lane_capacity_veh_h):
    evidence_bytes = (ROOT / option['evidence_path']).read_bytes()
    document = json.loads(evidence_bytes.decode('utf-8-sig'))
    if document.get('schema') != 'route-choice-corridor/v1':
        raise ValueError('Unsupported route corridor schema')
    network = _read_pinned(document['network'])
    if snapshot_network_sha256(raw) != document['network']['sha256']:
        raise ValueError('Route corridor snapshot network differs')
    tree = ET.parse(network).getroot()
    links = {x.get('no'): x for x in tree.findall('./links/link')}
    heads = {x.get('no'): x for x in tree.findall('./signalHeads/signalHead')}
    lengths = {key: _length(node) for key, node in links.items()}
    physical = physical_membership_from_ledger(json.loads((ROOT / document['membership_path']).read_text(encoding='utf-8')))
    owned = set(document['prefix_links']) | set(document['local_links'])
    if not all(physical.get(k) is True for k in owned):
        raise ValueError('Reviewed shared and local stocks must be wholly inside Omega')
    native_service=_native_generation_contract(document,tree,heads,links,cfg)
    if set(document['prefix_links']) & set(document['local_links']) or owned & set(document['post_stopline_projection']):
        raise ValueError('Route corridor physical partitions overlap')
    continuation=document.get('shared_continuation')
    continuation_path=continuation['path'] if continuation else []
    prefix_paths={document['decision_link']:[document['decision_link']]} if document.get('generated_inputs') else {}
    for row in document['incoming_turns'].values():
        path=row.get('path',[row['source_link'],row['connector'],document['decision_link']])
        _validate_path(path,links)
        if path[0]!=row['source_link'] or path[1]!=row['connector'] or path[-1]!=document['decision_link']:
            raise ValueError('Incoming path does not cover source, physical service and decision')
        for i,key in enumerate(path[1:]):
            suffix=path[i+1:]
            if key in prefix_paths and prefix_paths[key]!=suffix:
                raise ValueError('Incoming prefix has an unresolved intermediate choice')
            prefix_paths[key]=suffix
    for key in document['prefix_links']:
        if key == document['decision_link'] or key in continuation_path or key in prefix_paths: continue
        endpoint = links[key].find('toLinkEndPt')
        if endpoint is None or endpoint.get('lane').split()[0] != document['decision_link'] or float(endpoint.get('pos')) >= document['decision_position_m']:
            raise ValueError('Prefix connector does not enter before the eligible decision')
    shared=deepcopy(getattr(cfg.network,'shared_approach',None))
    if continuation and (not shared or shared['storage']!=continuation['source_storage']):
        raise ValueError('Native69 continuation requires the configured shared69 source')
    shared_branch=shared['branches'][continuation['branch']] if continuation else None
    if continuation and (shared_branch['target']!=continuation['previous_target'] or shared_branch['physical_receiver_start']!=continuation_path[0]):
        raise ValueError('Native69 branch2 source/receiving contract changed')
    if continuation and shared_branch['path'][-2:]!=continuation_path[:2]:
        raise ValueError('Native1134 branch does not end on reviewed75 stem')
    for i,key in enumerate(continuation_path[:-1]):
        node=links[key]
        endpoint=node.find('toLinkEndPt')
        if endpoint is not None:
            if endpoint.get('lane').split()[0]!=continuation_path[i+1]:
                raise ValueError('Shared continuation connector target changed')
        else:
            outgoing=[n for n in links.values() if n.find('fromLinkEndPt') is not None and n.find('fromLinkEndPt').get('lane').split()[0]==key]
            if [n.get('no') for n in outgoing]!=[continuation_path[i+1]]:
                raise ValueError('Shared continuation road is no longer deterministic')
            if any(h.get('lane','').split()[0]==key for h in tree.findall('./signalHeads/signalHead')):
                raise ValueError('Shared continuation would bypass a signal head')
    join=links[continuation_path[-2]].find('toLinkEndPt') if continuation else None
    if continuation and float(join.get('pos'))>=document['decision_position_m']:
        raise ValueError('Shared69 enters after the native decision')
    decision = tree.find(f"./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='{document['decision']}']")
    if decision is None or decision.get('link') != document['decision_link'] or decision.get('routeChoiceMeth') != 'STATIC' or decision.get('allVehTypes') != 'true':
        raise ValueError('Native route decision identity changed')
    if not math.isclose(float(decision.get('pos')), document['decision_position_m'], abs_tol=1e-9):
        raise ValueError('Native route decision position changed')
    weights, branches = {}, {}
    for route in decision.findall('./vehRoutSta/vehicleRouteStatic'):
        key = route.get('no')
        path = [decision.get('link')] + [x.get('key') for x in route.findall('./linkSeq/intObjectRef')] + [route.get('destLink')]
        if path != document['native_paths'].get(key):
            raise ValueError('Native corridor branch path changed')
        _validate_path(path,links)
        flow = (route.get('relFlow') or '').strip()
        match = re.fullmatch(r'2 0:([0-9]+(?:\.[0-9]+)?)', flow) if flow else None
        weights[key] = _positive(1. if not flow else match.group(1) if match else float('nan'), 'native relative flow')
        connector = path[1]
        branch_pos = float(links[connector].find('fromLinkEndPt').get('pos'))
        if branch_pos <= document['decision_position_m']:
            raise ValueError('Physical branch lies before the eligible native decision')
        if native_service is not None and branch_pos<=native_service['head_position_m']:
            raise ValueError('Native generated branch would bypass its declared source service')
        details=document.get('branch_specs',{}).get(key,{
            'mode':'free_storage' if key=='1' else 'typed_queue',
            'destination':document['bypass_storage'] if key=='1' else document['local_storage'],
            'service_group':'bypass' if key=='1' else 'local'})
        if details['mode'] not in {'free_storage','typed_queue','local_free'}:
            raise ValueError('Unknown physical route branch stage')
        branches[key] = {**details,'path': path, 'connector': connector, 'branch_position_m': branch_pos,
                         'lanes': len(links[connector].findall('./lanes/lane')),
                         'destination':details['destination']}
        if document.get('generated_inputs'):
            target=links[connector].find('toLinkEndPt').get('lane').split()[0]
            if (details['mode']!='free_storage' or path not in ([document['decision_link'],connector],[document['decision_link'],connector,target])
                    or details['physical_target_link']!=target or detectors['link_to_origins'].get(target)!=[details['destination']]
                    or detectors['link_to_origins'].get(connector)!=[details['destination']]):
                raise ValueError('Native generated branch lacks its existing physical receiver')
    if set(weights) != set(document['native_paths']) or len(weights)<2:
        raise ValueError('Reviewed route choice must cover every native choice')
    for key in weights:
        branches[key]['share'] = weights[key]/sum(weights.values())
    jam = _positive(json.loads(_read_pinned(document['jam_source']).read_text(encoding='utf-8'))['jam_density_veh_km_lane'], 'jam density')
    per_lane = _positive(per_lane_capacity_veh_h, 'canonical per-lane service')
    capacities = {document['prefix_storage']: sum(lengths[k]*len(links[k].findall('./lanes/lane')) for k in document['prefix_links'])*jam/1000}
    if document['local_links']:
        capacities[document['local_storage']]=sum(lengths[k]*len(links[k].findall('./lanes/lane')) for k in document['local_links'])*jam/1000
    elif document['local_storage'] is not None or not document.get('generated_inputs'):
        raise ValueError('An empty local stock is allowed only for a declared native source choice')
    if document['prefix_storage'] in cfg.network.urban_link_storage_veh:
        raise ValueError('New prefix storage already exists')
    specs, copied = deepcopy(cfg.network.urban_movements), deepcopy(detectors)
    capmap = dict(getattr(cfg.network, 'movement_capacity_by_movement_veh_h', {}))
    renames, turns, merge_audit = {}, {}, []
    calibrated_services=_calibrated_turn_services(document,tree,links,heads,specs,per_lane)
    for _, row in document['incoming_turns'].items():
        keep, removed = row['keep'], row['remove']
        a, b = specs[keep], specs[removed]
        if any(a.get(k) != b.get(k) for k in ('signal', 'origin', 'kind', 'turn', 'phase')):
            raise ValueError('Paired east movements are no longer the same physical turn')
        if (a['receiving_link'], b['receiving_link']) != (document['local_storage'], document['bypass_storage']):
            raise ValueError('Paired east receivers changed')
        node = links[row['connector']]
        source, target = node.find('fromLinkEndPt'), node.find('toLinkEndPt')
        path=row.get('path',[row['source_link'],row['connector'],document['decision_link']])
        if source.get('lane').split()[0] != row['source_link'] or target.get('lane').split()[0] != path[2]:
            raise ValueError('Physical east-turn connector changed')
        entry = float(links[path[-2]].find('toLinkEndPt').get('pos'))
        if entry >= document['decision_position_m']:
            raise ValueError('Incoming turn bypasses the reviewed decision')
        lanes = len(node.findall('./lanes/lane'))
        source_lane=int(source.get('lane').split()[1])
        upstream_heads=[h for h in heads.values() if h.get('lane','').split()[0]==row['source_link']
            and int(h.get('lane').split()[1]) in range(source_lane,source_lane+lanes)
            and float(h.get('pos'))<=float(source.get('pos'))]
        if bool(upstream_heads)!=row['signal_controlled']:
            raise ValueError('Physical incoming service disagrees with upstream signal-head authority')
        service=calibrated_services.get(row['connector'],{}).get('service_veh_h',lanes*per_lane)
        total_beta = _positive(a['beta'], 'first beta', zero=True)+_positive(b['beta'], 'second beta', zero=True)
        merge_audit.append({'keep': keep, 'removed': removed, 'total_beta': total_beta,
                           'old_capacities_veh_h': [capmap[keep], capmap[removed]], 'single_capacity_veh_h': service})
        a.update(beta=total_beta, destination=document['prefix_storage'], receiving_link=document['prefix_storage'])
        specs.pop(removed); renames[removed] = keep
        capmap[keep] = service; capmap.pop(removed)
        turns[keep] = {**row, 'entry_position_m': entry, 'lanes': lanes, 'service_veh_h': service,
                       'path': path}
    # Merge raw per-link weights before any physical state is created.
    for key, rows in copied.get('link_to_movements', {}).items():
        combined = {}
        for row in rows:
            name = renames.get(row['movement'], row['movement'])
            if name not in combined:
                combined[name] = {**row, 'movement': name, 'weight': 0.}
            combined[name]['weight'] += float(row['weight'])
        copied['link_to_movements'][key] = list(combined.values())
    for agent in copied.get('agents', {}).values():
        if 'visible_movements' in agent:
            agent['visible_movements'] = list(dict.fromkeys(renames.get(m, m) for m in agent['visible_movements']))
    for name in document['local_movements'].values():
        if specs[name]['origin'] != document['local_storage']:
            raise ValueError('Typed local queue is not on the reviewed local receiver')
    for key,target in document['post_stopline_projection'].items():
        matches = [route for route,path in document['native_paths'].items() if path[-1]==key or (len(path)>2 and path[-2]==key)]
        if len(matches)!=1:
            raise ValueError('Post-stopline projection lacks a unique native local turn')
        route=matches[0]; native_path=document['native_paths'][route]
        node=links[key]; src=node.find('fromLinkEndPt'); dst=node.find('toLinkEndPt')
        if native_path[-1]==key:
            if branches[route]['mode']!='free_storage' or target!=branches[route]['destination'] or target not in detectors.get('link_to_origins',{}).get(key,[]):
                raise ValueError('Bypass projection lacks its existing unique receiver')
        else:
            movement=document['local_movements'].get(route) or document.get('local_free_paths',{}).get(route,{}).get('canonical_movement')
            if not movement or src.get('lane').split()[0]!=native_path[-3] or dst.get('lane').split()[0]!=native_path[-1] or specs[movement]['receiving_link']!=target:
                raise ValueError('Post-stopline canonical receiver/physical connector disagree')
            if target not in detectors.get('link_to_origins',{}).get(native_path[-1],[]):
                raise ValueError('Post-stopline receiver lacks actual downstream detector support')
    queue_positions = {}
    for key, no in document['local_queue_heads'].items():
        node = heads[no]
        if node.get('lane').split()[0] != document['native_paths'][key][-3]:
            raise ValueError('Local route queue head changed road')
        queue_positions[key] = float(node.get('pos'))
    prefix_paths.update({key:continuation_path[i:] for i,key in enumerate(continuation_path)})
    if set(prefix_paths)!=set(document['prefix_links']):
        raise ValueError('Every physical prefix link needs an explicit path to the future decision')
    travel={}
    for origin,path in prefix_paths.items():
        _validate_path(path,links)
        for key,following in zip(path,path[1:]):
            if links[key].find('toLinkEndPt') is None:
                outgoing=[node.get('no') for node in links.values() if node.find('fromLinkEndPt') is not None and node.find('fromLinkEndPt').get('lane').split()[0]==key]
                if outgoing!=[following]:
                    raise ValueError('Pre-choice intermediate road has an unresolved alternate path')
        travel[origin]=_travel_segments(path,links,lengths,document['decision_position_m'])
    local_travel={}; local_exits={}
    for key,branch in branches.items():
        if branch['mode']=='free_storage': continue
        local_path=branch['path'][1:3]
        if set(local_path)!=set(document['local_links']):
            raise ValueError('Managed local branch needs its exact physical corridor')
        incoming=[node.get('no') for node in links.values() if node.find('toLinkEndPt') is not None and node.find('toLinkEndPt').get('lane').split()[0]==local_path[-1]]
        if incoming!=[local_path[0]]:
            raise ValueError('Typed local road has another unrepresented incoming source')
        if branch['mode']=='typed_queue':
            stop=queue_positions[key]
        else:
            row=document['local_free_paths'][key]
            if row['path']!=branch['path'][1:] or row['signal_controlled'] is not False:
                raise ValueError('Local free path must be the exact unsignalled native continuation')
            node=links[row['connector']]; source=node.find('fromLinkEndPt'); target=node.find('toLinkEndPt')
            stop=float(source.get('pos')); source_road=source.get('lane').split()[0]
            if source_road!=local_path[-1] or not math.isclose(stop,row['branch_position_m'],abs_tol=1e-9) or target.get('lane').split()[0]!=row['physical_target_link']:
                raise ValueError('Local free branch geometry differs')
            lanes=len(node.findall('./lanes/lane')); first_lane=int(source.get('lane').split()[1])
            relevant=[h for h in heads.values() if h.get('lane','').split()[0]==source_road and int(h.get('lane').split()[1]) in range(first_lane,first_lane+lanes)]
            if any(float(h.get('pos'))<=stop for h in relevant):
                raise ValueError('Local free branch would bypass an upstream signal head')
            if physical.get(row['physical_target_link']) is not True:
                raise ValueError('Local free target requires a separately defined boundary crossing')
            if cfg.network.urban_movements[row['canonical_movement']]['receiving_link']!=row['target'] or detectors['link_to_origins'].get(row['physical_target_link'])!=[row['target']]:
                raise ValueError('Local free branch receiver lacks unique physical support')
            local_exits[key]={**row,'lanes':lanes,'service_veh_h':lanes*per_lane}
        local_travel[key]={origin:_travel_segments(local_path[i:],links,lengths,stop) for i,origin in enumerate(local_path)}
    if shared_branch is not None: shared_branch['target']=document['prefix_storage']
    spec = {**document, 'unknown_policy': option['unknown_policy'], 'capacity_veh': capacities,
            'lengths_m': {k:lengths[k] for k in owned}, 'branches': branches, 'turns': turns,
            'queue_positions_m': queue_positions, 'per_lane_capacity_veh_h': per_lane, 'merge_audit': merge_audit,
            'prefix_travel_segments':travel,
            'local_travel_segments':local_travel,'local_exits':local_exits,
            'local_enter_position_m': float(links[document['local_connector']].find('toLinkEndPt').get('pos')) if document['local_links'] else None,
            'area_paths': {name: path_membership(row['path'], physical) for name,row in turns.items()},
            'renames': renames, 'source_path': option['evidence_path'],
            'physical_stock_validation': {'network_sha256':document['network']['sha256'],
                'evidence_sha256':hashlib.sha256(evidence_bytes).hexdigest(),'paths_validated':True}}
    if calibrated_services:spec['calibrated_service_resources']=calibrated_services
    if native_service is not None:spec['native_fixed_service']=native_service
    cfg.network.urban_movements = specs
    cfg.network.movement_capacity_by_movement_veh_h = capmap
    cfg.network.urban_link_storage_veh = {**cfg.network.urban_link_storage_veh, **capacities}
    for field in ('off_ramp_to_movement', 'on_ramp_to_movement'):
        value = getattr(cfg.network, field, None)
        if isinstance(value, dict):
            setattr(cfg.network, field, {k:list(dict.fromkeys(renames.get(m,m) for m in v)) for k,v in value.items()})
    old_renames = dict(getattr(cfg.network, 'movement_merge_rename', {}) or {})
    cfg.network.movement_merge_rename = {k:renames.get(v,v) for k,v in old_renames.items()} | renames
    cfg.network.route_choice_corridor = spec
    cfg.network.shared_approach=shared
    invalidate_topology_cache(cfg.network)
    return copied, {'route_choice_corridor_enabled': 1., 'route_choice_merges': merge_audit,
                    'route_choice_capacities_veh': capacities, 'route_choice_unknown_policy': spec['unknown_policy']}


def prepare_projection(cfg, detectors, raw):
    spec = getattr(cfg.network, 'route_choice_corridor', None)
    if spec is None:
        return detectors, raw, {}
    table = {key:target for item in _specs(cfg) for key,target in _projection_table(item).items()}
    copied, prepared = deepcopy(detectors), deepcopy(raw)
    rows = defaultdict(list)
    for row in complete_records(raw): rows[str(row['link_no'])].append(row)
    audit = {}
    for link,target in table.items():
        if link in copied.get('freeway_link_to_model_link',{}) or link in copied.get('ramp_link_to_queues',{}):
            raise ValueError('Route-choice stock overlaps freeway/ramp projection')
        local = prepared['local_observation']; count = len(rows[link])
        if link in local.get('link_counts',{}) and local['link_counts'][link] != count:
            raise ValueError('Local/full corridor observations disagree')
        local.setdefault('link_counts',{})[link] = count
        local.setdefault('link_stopped_counts',{})[link] = sum(bool(row['stopped']) for row in rows[link])
        if count: local.setdefault('link_speeds_kph',{})[link] = sum(row['speed_kph'] for row in rows[link])/count
        audit[link] = {'vehicles':count,'old_origins':copied['link_to_origins'].get(link,[]),'target':target}
        copied['link_to_origins'][link] = [target]
        copied.setdefault('link_to_movements',{}).pop(link,None)
        copied.setdefault('transit_storage_projection',{})[link] = target
    copied['observable_links'] = sorted(set(map(str,copied.get('observable_links',[]))) | set(table),key=int)
    # The support guard may trust only this verified module claim, after configure
    # and prepare_projection ran. It must not globally delete unresolved links.
    copied['route_choice_verified_physical_stock'] = {k:v for k,v in table.items()}
    return copied, prepared, {'route_choice_physical_projection':audit}


def _routes(raw):
    return complete_vehicle_routes(raw, required=False) or {}


def _speed(state,cfg,value=None):
    from src.models.urban_queue_model import OBSERVED_SPEED_DELAY_CAP_RATIO
    nominal = _positive(cfg.network.urban_avg_speed_km_h,'nominal speed')
    return max(nominal/OBSERVED_SPEED_DELAY_CAP_RATIO, _positive(nominal if value is None else value,'observed speed',zero=True))


def _due(cfg,index,distance,speed):
    return index+max(1,math.ceil(max(0.,distance)/(speed/3.6)/cfg.simulation.T_u_sec))


def _prefix_distance(spec,link,position,route=None):
    segments=spec['prefix_travel_segments'][link]
    distance=sum(max(0.,row['stop']-(position if i==0 else row['start'])) for i,row in enumerate(segments))
    if route is not None:
        distance+=spec['branches'][route]['branch_position_m']-spec['decision_position_m']
        # On56 past the choice, only its actual residual branch distance remains.
        if link==spec['decision_link'] and position>spec['decision_position_m']:
            distance=max(0.,spec['branches'][route]['branch_position_m']-position)
    return distance


def _cohort(storage,stage,route,amount,due,*,possible=(),source='observed',speed=1.):
    return {'storage':storage,'stage':stage,'route':route,'vehicles':amount,'due':due,
            'possible_routes':list(possible),'source':source,'speed_kph':speed}


def _tracked(local,storage):
    return sum(c['vehicles'] for c in local['cohorts'] if c['storage']==storage)


def _check(state,spec):
    local=state.route_choice_corridor_state
    for storage,cap in spec['capacity_veh'].items():
        if not math.isclose(cap-state.urban_link_storage[storage],_tracked(local,storage),abs_tol=EPS):
            raise ValueError(f'Route corridor cohort/physical stock mismatch: {storage}')


def initialize(state,cfg,raw,detectors=None):
    spec=getattr(cfg.network,'route_choice_corridor',None)
    if spec is None: return {}
    if hasattr(state,'route_choice_corridor_state'): raise ValueError('Route corridor initialized twice')
    native=getattr(cfg.network,'native_internal_inputs',{}) or {}
    for no,row in generated_input_contracts(cfg).items():
        generation=native.get('inputs',{}).get(no,{})
        if (generation.get('target_kind')!='route_choice' or generation.get('target_storage')!=row['storage']
                or generation.get('physical_source')!=row['physical_source']):
            raise ValueError('Route-choice source has no matching verified native generation contract: '+no)
    current=_routes(raw); index=round(state.time_sec/cfg.simulation.T_u_sec)
    local={'cohorts':[],'last_step':index-1,'service_used_veh':{},'service_limit_veh':{},'received_veh':0.,'departed_veh':0.}
    for item in _specs(cfg):
        _initialize_one(state,cfg,raw,current,index,local,item)
    state.route_choice_corridor_state=local
    for storage in spec['capacity_veh']:
        state.urban_arrival_buffer.pop(storage,None); state.urban_storage_release_buffer.pop(storage,None)
    _check(state,spec)
    return diagnostics(state,cfg)


def _initialize_one(state,cfg,raw,current,index,local,spec):
    owned=set(spec['prefix_links'])|set(spec['local_links'])
    assignment=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    for record in complete_records(raw):
        link=str(record['link_no'])
        if link not in owned: continue
        storage=spec['prefix_storage'] if link in spec['prefix_links'] else spec['local_storage']
        if assignment.get(link,{}).get('storage:'+storage,0)<1-EPS or any(v>EPS for k,v in assignment.get(link,{}).items() if k!='storage:'+storage):
            raise ValueError('Corridor physical records have another model owner')
        pos=float(record['position_m']); speed=_speed(state,cfg,record['speed_kph'])
        observed=current.get(int(record['veh_no']),{})
        tag=str(observed.get('route_no')) if observed.get('route_decision_no')==int(spec['decision']) and observed.get('route_decision_type')=='STATIC' else None
        if tag is not None and tag not in spec['branches']: raise ValueError('Unknown native'+spec['decision']+' current route')
        prefix=storage==spec['prefix_storage']
        possible=tuple(spec['branches']) if prefix else tuple(key for key,branch in spec['branches'].items() if branch['mode']!='free_storage')
        if tag is not None and tag not in possible: raise ValueError('Current route contradicts physical branch')
        before=prefix and (link!=spec['decision_link'] or pos<spec['decision_position_m'])
        physical_tag=False
        if not prefix and tag is None and len(possible)==1:
            # A deterministic physical branch establishes the only continuation;
            # this is not a newly sampled or claimed observed static route ID.
            tag=possible[0]; physical_tag=True
        if tag is None and not before:
            if spec['unknown_policy']=='error':
                raise ValueError(f'Current{spec["decision"]} route required after choice: vehicle{record["veh_no"]} link{link} pos{pos}')
            local['cohorts'].append(_cohort(storage,'unknown',None,1.,index,possible=possible,source='unobserved_past_choice',speed=speed))
            continue
        if prefix:
            distance=_prefix_distance(spec,link,pos,tag)
            stage='prefix_tagged' if tag else 'prechoice'
        else:
            distance=_segments_distance(spec['local_travel_segments'][tag][link],pos)
            stage='local_tagged'
        cohort=_cohort(storage,stage,tag,1.,_due(cfg,index,distance,speed),source='unique_physical_branch' if physical_tag else 'observed_current_route' if tag else 'eligible_future_choice',speed=speed)
        if spec.get('native_fixed_service'):
            cohort['native_service_passed']=pos>=spec['native_fixed_service']['head_position_m']
        local['cohorts'].append(cohort)


def _segments_distance(segments,position=0.):
    return sum(max(0.,row['stop']-(position if i==0 else row['start'])) for i,row in enumerate(segments))


def diagnostics(state,cfg):
    spec=getattr(cfg.network,'route_choice_corridor',None)
    if spec is None: return {}
    local=state.route_choice_corridor_state
    known=known_legsplit_diagnostics(state,cfg)
    unknown=sum(c['vehicles'] for c in local['cohorts'] if c['stage']=='unknown') + known.get('known_wout_held_unknown_route_veh',0.)
    return {**known, 'route_choice_held_unknown_route_veh':unknown,'route_choice_prediction_route_complete':float(unknown<=EPS),
            'route_choice_unknown_policy':spec['unknown_policy'],
            'route_choice_stock_veh':{k:_tracked(local,k) for k in spec['capacity_veh']}}


def intended_departure(state,control,cfg,movement,available,urban_step_index):
    """Before receiving allocation. None delegates ordinary movements unchanged."""
    spec=_movement_spec(cfg,movement)
    if spec is None: return None
    turn=spec['turns'][movement]; local=state.route_choice_corridor_state
    if local['last_step']!=urban_step_index: raise ValueError('Route-choice admission needs current advance')
    from src.models import urban_queue_model as uqm
    fraction=uqm._phase_green_fraction(control,cfg,cfg.network.urban_movements[movement],urban_step_index=urban_step_index) if turn['signal_controlled'] else 1.
    from evaluation.controllers import local_signal_service as pool
    if pool.view(cfg) and movement in pool.view(cfg)['group_of']:
        pool.register_limit(local['service_limit_veh'], turn['connector'], turn['service_veh_h'], cfg.simulation.T_u_h, fraction)
        return pool.limit_one(available, turn['connector'], local['service_limit_veh'], local['service_used_veh'])
    budget=turn['service_veh_h']*cfg.simulation.T_u_h*float(fraction)
    prior=local['service_limit_veh'].get(turn['connector'])
    if prior is not None and not math.isclose(prior,budget,abs_tol=EPS):
        raise ValueError('Sources sharing one physical turn received inconsistent green/service budgets')
    local['service_limit_veh'][turn['connector']]=budget
    left=max(0.,budget-local['service_used_veh'].get(turn['connector'],0.))
    return min(_positive(available,'intended source availability',zero=True),left)


def receive_accepted(state,cfg,movement,vehicles,urban_step_index):
    spec=_movement_spec(cfg,movement)
    if spec is None: return False
    n=_positive(vehicles,'accepted route-choice vehicles',zero=True)
    local=state.route_choice_corridor_state; turn=spec['turns'][movement]
    if local['last_step']!=urban_step_index: raise ValueError('Receipt requires current explicit urban step')
    storage=spec['prefix_storage']
    if not math.isclose(spec['capacity_veh'][storage]-state.urban_link_storage[storage],_tracked(local,storage)+n,abs_tol=EPS):
        raise ValueError('Accepted source transfer must have occurred exactly once before receipt')
    group=turn['connector']
    ledger=get_ledger(state)
    capture=ledger is not None and ledger.captures_response
    if capture:
        service_before=local['service_used_veh'].get(group,0.)
    from evaluation.controllers import local_signal_service as pool
    if pool.view(cfg) and movement in pool.view(cfg)['group_of']:
        pool.accepted(n, group, local['service_limit_veh'], local['service_used_veh'])
        used=local['service_used_veh'][group]
    else:
        used=local['service_used_veh'].get(group,0.)+n
        limit=local['service_limit_veh'].get(group)
        if limit is None or used>limit+EPS: raise ValueError('Shared physical-turn service was not limited before acceptance')
    if capture:
        # Sequential actual receipts share the existing one-turn budget. The
        # caller has already accounted for receiver stock; do not charge it twice.
        ledger.record_resource_allocation('route_choice_incoming_service', str(group),
            max(0.,local['service_limit_veh'][group]-service_before), {'movement:'+movement:n})
    speed=_speed(state,cfg,state.urban_link_speed_kph.get(storage))
    distance=_prefix_distance(spec,group,0.)
    local['cohorts'].append(_cohort(storage,'prechoice',None,n,_due(cfg,urban_step_index,distance,speed),source=movement,speed=speed))
    local['service_used_veh'][group]=used; local['received_veh']+=n
    _check(state,spec)
    return True


def limit_intended_batch(state,cfg,intended,urban_step_index):
    """Share one physical service budget across simultaneously computed sources.

    A scalar intended query cannot reserve receiving space before the receiving
    allocator accepts flow. This batch cap therefore runs immediately before
    that allocator; receipts still debit only the eventual accepted amounts.
    """
    spec=getattr(cfg.network,'route_choice_corridor',None)
    if spec is None: return intended
    local=state.route_choice_corridor_state
    if local['last_step']!=urban_step_index: raise ValueError('Batch cap requires current explicit urban step')
    groups=defaultdict(dict)
    for movement,amount in intended.items():
        if movement in spec['turns']:
            groups[spec['turns'][movement]['connector']][movement]=_positive(amount,'batched intended flow',zero=True)
    if not groups: return intended
    from src.models import urban_queue_model as uqm
    result=dict(intended)
    for group,requests in groups.items():
        if group not in local['service_limit_veh']: raise ValueError('Batch lacks its physical intended-departure query')
        from evaluation.controllers import local_signal_service as pool
        if pool.view(cfg) and group in pool.view(cfg)['groups']:
            result.update(pool.limit_batch(requests, pool.view(cfg)['group_of'], local['service_limit_veh'], local['service_used_veh'], cfg.urban_follower.receiving_space_rule))
        else:
            remaining=max(0.,local['service_limit_veh'][group]-local['service_used_veh'].get(group,0.))
            result.update(uqm._allocate_receiving_counts(cfg.urban_follower.receiving_space_rule,requests,remaining))
    return result


def receive_shared_accepted(state,cfg,source_storage,branch,vehicles,urban_step_index):
    """Called after the one shared69→prefix accepted stock transfer, before generic scheduling."""
    spec=getattr(cfg.network,'route_choice_corridor',None)
    if spec is None: return False
    spec=next((item for item in _specs(cfg) if item.get('shared_continuation',{}).get('source_storage')==source_storage
               and item['shared_continuation']['branch']==str(branch)),None)
    if spec is None: return False
    continuation=spec['shared_continuation']
    local=state.route_choice_corridor_state; n=_positive(vehicles,'shared accepted amount',zero=True)
    if local['last_step']!=urban_step_index: raise ValueError('Advance route corridor before shared69 source')
    storage=spec['prefix_storage']
    if not math.isclose(spec['capacity_veh'][storage]-state.urban_link_storage[storage],_tracked(local,storage)+n,abs_tol=EPS):
        raise ValueError('Shared source transfer was not applied exactly once')
    speed=_speed(state,cfg,state.urban_link_speed_kph.get(storage))
    distance=_prefix_distance(spec,continuation['path'][0],0.)
    local['cohorts'].append(_cohort(storage,'prechoice',None,n,_due(cfg,urban_step_index,distance,speed),source='shared69:2',speed=speed))
    local['received_veh']+=n; _check(state,spec)
    return True


def receive_generated(state,cfg,input_no,vehicles,urban_step_index):
    """Reserve only the accepted native generation already added once to stock.

    The native input module owns demand/backlog and emits its single input event.
    It must skip generic arrival/release reservations when this receipt succeeds.
    """
    no=str(input_no)
    spec=next((s for s in _specs(cfg) if no in s.get('generated_inputs',{})),None)
    if spec is None:return False
    row=spec['generated_inputs'][no];local=state.route_choice_corridor_state
    n=_positive(vehicles,'accepted native generation',zero=True)
    if local['last_step']!=urban_step_index:raise ValueError('Advance route choice before native generation')
    storage=row['storage']
    if not math.isclose(spec['capacity_veh'][storage]-state.urban_link_storage[storage],_tracked(local,storage)+n,abs_tol=EPS):
        raise ValueError('Native generated stock must be applied exactly once before route receipt')
    speed=_speed(state,cfg,state.urban_link_speed_kph.get(storage));distance=_prefix_distance(spec,row['physical_source'],0.)
    cohort=_cohort(storage,'prechoice',None,n,_due(cfg,urban_step_index,distance,speed),source='generated_input:'+no,speed=speed)
    cohort['native_service_passed']=False
    if n:local['cohorts'].append(cohort)
    local['received_veh']+=n;_check(state,spec)
    return True


def advance(state,control,demand,cfg,urban_step_index):
    spec=getattr(cfg.network,'route_choice_corridor',None)
    if spec is None: return {}
    local=state.route_choice_corridor_state
    if urban_step_index!=local['last_step']+1: raise ValueError('Route-choice state requires sequential explicit steps')
    _check(state,spec); local['service_used_veh']={}; local['service_limit_veh']={}
    transferred={}
    for item in _specs(cfg):
        previous_gate=item.get('shared_continuation',{}).get('previous_target')
        if previous_gate and demand is not None and float(demand.urban_boundary.get(previous_gate,0.))>EPS:
            raise ValueError('Former shared69 receiver has unsupported independent external demand: '+previous_gate)
        transferred.update(_advance_one(state,control,cfg,urban_step_index,item))
    local['last_step']=urban_step_index
    _check(state,spec)
    return {**diagnostics(state,cfg),'route_choice_accepted_veh':transferred}


def _advance_one(state,control,cfg,urban_step_index,spec):
    from src.models import urban_queue_model as uqm
    local=state.route_choice_corridor_state
    ledger=get_ledger(state)
    capture=ledger is not None and ledger.captures_response
    # Only *eligible* undecided mass gets the native choice; tags do not move stock.
    updated=[]
    for cohort in local['cohorts']:
        if cohort['storage']==spec['prefix_storage'] and cohort['stage']=='prechoice' and cohort['due']<=urban_step_index:
            for key,branch in spec['branches'].items():
                distance=branch['branch_position_m']-spec['decision_position_m']
                tagged=_cohort(cohort['storage'],'prefix_tagged',key,cohort['vehicles']*branch['share'],
                    _due(cfg,urban_step_index,distance,cohort['speed_kph']),source=cohort['source'],speed=cohort['speed_kph'])
                if 'native_service_passed' in cohort:tagged['native_service_passed']=cohort['native_service_passed']
                updated.append(tagged)
        else: updated.append(cohort)
    local['cohorts']=updated; additions=[]; departed=0.; transferred=defaultdict(float); native_used=0.
    # Queue arrivals are physical storage→queue, not another demand/beta draw.
    for cohort in local['cohorts']:
        if cohort['storage'] not in spec['capacity_veh']: continue
        if cohort['due']>urban_step_index or cohort['stage'] in {'unknown','prechoice'}: continue
        route=cohort['route']; amount=cohort['vehicles']; source=cohort['storage']
        if cohort['stage']=='local_tagged' and spec['branches'][route]['mode']=='typed_queue':
            movement=spec['local_movements'][route]
            state.urban_link_storage[source]+=amount
            state.urban_movement_queue[movement]=state.urban_movement_queue.get(movement,0.)+amount
            emit_transfer(state,cfg,'storage:'+source,'movement:'+movement,amount,preserve_area=True)
            cohort['vehicles']=0.; transferred['local_queue:'+route]+=amount
            continue
        free_exit=spec['local_exits'].get(route) if cohort['stage']=='local_tagged' else None
        target=free_exit['target'] if free_exit else spec['branches'][route]['destination']
        available=uqm._effective_available_space(state,cfg,target)
        # One physical connector budget, shared by every tag using that connector.
        group='exit:'+free_exit['connector'] if free_exit else 'branch:'+spec['branches'][route]['service_group']
        service_key=group
        service=(free_exit['service_veh_h'] if free_exit else spec['per_lane_capacity_veh_h']*spec['branches'][route]['lanes'])*cfg.simulation.T_u_h
        native=spec.get('native_fixed_service')
        if native and 'calibrated_service_veh_h' in native:
            # The source head and its immediately serial branch share this one
            # physical service. Leaving a second inherited cap would negate it.
            service=native['calibrated_service_veh_h']*cfg.simulation.T_u_h
        service_available=max(0.,service-transferred[service_key])
        accepted=min(amount,available,service_available)
        crosses_native_head=native is not None and not cohort.get('native_service_passed',False)
        if crosses_native_head:
            from evaluation.controllers.fixed_signal_schedule import _union_green_overlap
            start=urban_step_index*cfg.simulation.T_u_sec
            green_sec=_union_green_overlap(_native_program(native),(native['signal_group'],),start,start+cfg.simulation.T_u_sec,native['controller_offset_sec'])
            native_rate=native.get('calibrated_service_veh_h',spec['per_lane_capacity_veh_h']*native['lanes'])
            green_service=native_rate*green_sec/3600.
            native_available=max(0.,green_service-native_used)
            accepted=min(accepted,native_available)
        if capture:
            source_key='route_choice:'+str(spec['decision'])+':'+cohort['stage']+':'+str(route)+':'+str(cohort['source'])
            sources={source_key:accepted}
            ledger.record_resource_allocation('route_choice_receiving', 'storage:'+target, available, sources)
            ledger.record_resource_allocation('route_choice_branch_service',
                str(spec['decision'])+':'+service_key, service_available, sources)
            if crosses_native_head:
                ledger.record_resource_allocation('native_fixed_head_service',
                    'SC'+str(native['controller'])+':SG'+str(native['signal_group']), native_available, sources)
        if accepted<=0: continue
        cohort['vehicles']-=accepted; state.urban_link_storage[source]+=accepted
        state.urban_link_storage[target]-=accepted
        emit_transfer(state,cfg,'storage:'+source,'storage:'+target,accepted,preserve_area=True)
        transferred[service_key]+=accepted; departed+=accepted
        if crosses_native_head:native_used+=accepted
        if free_exit or spec['branches'][route]['mode']=='free_storage':
            due=urban_step_index+uqm._link_delay_steps(state,cfg,target)
            uqm._schedule(state.urban_arrival_buffer,target,due,accepted)
            uqm._schedule(state.urban_storage_release_buffer,target,due,accepted)
        else:
            distance=_segments_distance(spec['local_travel_segments'][route][spec['local_connector']])
            additions.append(_cohort(target,'local_tagged',route,accepted,_due(cfg,urban_step_index,distance,cohort['speed_kph']),source=cohort['source'],speed=cohort['speed_kph']))
    local['cohorts']=[c for c in local['cohorts'] if c['vehicles']>0]+additions
    local['departed_veh']+=departed
    if spec.get('native_fixed_service'):
        local.setdefault('native_service_used_veh',{})[spec['decision']]=native_used
    _check(state,spec)
    return dict(transferred)


def extend_area_routes(cfg):
    spec=getattr(cfg.network,'route_choice_corridor',None)
    if spec is None: return {}
    routes=dict(cfg.network.control_area_routes)
    for removed,keep in spec['renames'].items():
        routes.pop('movement:'+removed,None); routes.pop('arrival:'+removed,None)
    for item in _specs(cfg):
        for name,row in item['area_paths'].items():
            routes['movement:'+name]={**row,'target_inside':True,'inside_to_inside':1.,'outside_to_inside':1.,
                                     'status':'verified_stopline_to_route_choice_prefix'}
    cfg.network.control_area_routes=routes
    return {'route_choice_area_entry_routes':len(spec['turns'])}


# Preserve chosen destinations inside the existing legsplit stock.
def configure_known_legsplit(cfg, tuning, state, raw):
    enabled = tuning.get('urban', {}).get('preserve_known_wout_routes', False)
    if type(enabled) is not bool:
        raise ValueError('preserve_known_wout_routes must be boolean')
    if not enabled:
        if hasattr(cfg.network, 'known_legsplit_routes'):
            delattr(cfg.network, 'known_legsplit_routes')
        return {}
    if not getattr(cfg.network, 'route_choice_corridor', None) or not cfg.network.leg_ramp_split_enabled:
        raise ValueError('Known W_out routes require canonical corridor and legsplit runtime')
    if getattr(cfg.network, 'control_area_enabled', False) is not True:
        raise ValueError('Known W_out routes require the accounted area scheduler')
    reference = tuning['urban']['known_wout_route_evidence']
    path = ROOT / reference['path']
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != reference['sha256']:
        raise ValueError('Known W_out route evidence changed')
    proof = json.loads(data)
    if proof['schema'] != 'known-wout-routes/v1':
        raise ValueError('Unsupported known W_out route schema')
    network = ROOT / proof['network']['path']
    if hashlib.sha256(network.read_bytes()).hexdigest() != proof['network']['sha256']:
        raise ValueError('Known W_out network changed')
    from evaluation.controllers.network_provenance import snapshot_network_sha256
    if snapshot_network_sha256(raw) != proof['network']['sha256']:
        raise ValueError('Known W_out snapshot network differs')
    tree = ET.parse(network).getroot()
    for key, detail in proof['native_routes'].items():
        decision_no, route_no = key.split(':')
        decision = tree.find(f"./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='{decision_no}']")
        route = decision.find(f"./vehRoutSta/vehicleRouteStatic[@no='{route_no}']")
        actual = [decision.get('link')] + [r.get('key') for r in route.findall('./linkSeq/intObjectRef')] + [route.get('destLink')]
        if actual != detail['path'] or float(route.get('destPos')) != detail['dest_pos']:
            raise ValueError('Known native W_out destination changed: ' + key)
    choice = tree.find("./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='1135']")
    if choice.get('link') != '68' or float(choice.get('pos')) != proof['choice_position_m']:
        raise ValueError('Native1135 choice plane changed')
    # Future scalar OR_F_E direct receipts have no observed vehicle IDs.
    # Their destination is a native path prior, separately from initial tags.
    direct_routes=set()
    for decision in tree.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic'):
        for route in decision.findall('./vehRoutSta/vehicleRouteStatic'):
            path=[decision.get('link')]+[r.get('key') for r in route.findall('./linkSeq/intObjectRef')]+[route.get('destLink')]
            if '10682' in path:
                direct_routes.add(decision.get('no')+':'+route.get('no'))
    if direct_routes!={'1130:3'}:
        raise ValueError('Future direct branch no longer has its unique pinned static path')
    storage = proof['storage']
    net = cfg.network
    if storage != 'SC1004_W_out' or net.offramp_direct_tail_by_offramp.get('OR_F_E') != storage:
        raise ValueError('Known W_out source ownership changed')
    prior = net.boundary_out_ramp_split.get(storage, {})
    weights = {'free':prior.get('free'), **prior.get('ramps', {})}
    destination_names = {'R_F_W':'R_F_W', 'R_F_E':'R_F_E'}
    if getattr(net, 'physical_ramp_branches', None):
        destination_names = {'R_F_W':'RM_C10646', 'R_F_E':'RM_C10681'}
        if not set(destination_names.values()) <= set(net.ramps):
            raise ValueError('Known W_out physical ramp destinations are missing')
    if (set(weights) != {'free', *destination_names.values()}
            or any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or v<0 for v in weights.values())
            or abs(sum(weights.values())-1.)>1e-9):
        raise ValueError('Known W_out needs the existing finite normalized destination prior')
    expected_targets={'1130:3':'free','1135:2':'R_F_W','1135:3':'free','1135:4':'R_F_E'}
    if {k:v['target'] for k,v in proof['native_routes'].items() if 'target' in v} != expected_targets:
        raise ValueError('Known W_out route-to-destination contract changed')
    receivers = {m:s for m,s in net.urban_movements.items() if s.get('receiving_link') == storage and s.get('beta',0)>0}
    if set(receivers) != set(proof['incoming_movements']):
        raise ValueError('Known W_out positive incoming movements changed')
    links = {r.get('no'):r for r in tree.findall('./links/link')}
    for movement, connector in proof['incoming_movements'].items():
        turn = links[connector]
        endpoint = turn.find('toLinkEndPt')
        routes = net.control_area_routes['movement:'+movement]['physical_turns']
        if (endpoint.get('lane').split()[0] != '68' or float(endpoint.get('pos')) >= proof['choice_position_m']
                or not any(str(r['connector']) == connector for r in routes)):
            raise ValueError('Known future W_out entry is not before1135: ' + movement)
    spec = {'storage':storage, 'routes':proof['native_routes'], 'choice_position_m':proof['choice_position_m'],
        'prechoice_connectors':proof['prechoice_connectors'], 'incoming_movements':proof['incoming_movements'],
        'source':dict(reference)}
    spec['routes'] = {key:{**detail, **({'target':destination_names.get(detail['target'],detail['target'])}
        if 'target' in detail else {})} for key,detail in spec['routes'].items()}
    net.known_legsplit_routes = spec
    initialize_known_legsplit(state, cfg, raw)
    return {'known_wout_routes_enabled':1., 'known_wout_initial_veh':_known_total(state),
            'known_wout_future_direct_native_path_prior':1., **diagnostics(state,cfg)}


def known_legsplit_diagnostics(state,cfg):
    if not getattr(cfg.network,'known_legsplit_routes',None):
        return {}
    local=state.known_legsplit_route_state
    unknown=sum(c['vehicles'] for c in local['cohorts'] if c['target']=='unknown')
    return {'known_wout_held_unknown_route_veh':unknown,
            'known_wout_prediction_route_complete':float(unknown<=1e-8),
            'known_wout_stock_veh':_known_total(state)}


def _known_total(state):
    return sum(c['vehicles'] for c in state.known_legsplit_route_state['cohorts'])


def _known_check(state, cfg):
    spec = getattr(cfg.network, 'known_legsplit_routes', None)
    if spec is None:
        return
    storage = spec['storage']
    n = cfg.network.urban_link_storage_veh[storage]-state.urban_link_storage[storage]
    if not math.isclose(_known_total(state), n, rel_tol=0., abs_tol=1e-7):
        raise ValueError('Known W_out aliases differ from the sole physical stock')


def _known_classify(record, route, spec):
    link = str(record['link_no']); pos = record['position_m']
    identity = (str(route['route_decision_no'])+':'+str(route['route_no'])
                if route['route_decision_type']=='STATIC' else None)
    detail = spec['routes'].get(identity)
    if detail is not None and link not in detail['path']:
        raise ValueError('Current W_out route contradicts its physical link')
    if detail is not None and 'target' in detail:
        return detail['target']
    before = link in spec['prechoice_connectors'] or (link=='68' and pos < spec['choice_position_m'])
    if before:
        return 'prechoice'
    # A missing/expired tag after the decision never becomes a new prior draw.
    return 'unknown'


def initialize_known_legsplit(state, cfg, raw):
    if hasattr(state, 'known_legsplit_route_state'):
        raise ValueError('Known W_out tags must initialize once')
    spec = cfg.network.known_legsplit_routes; storage = spec['storage']; key = 'storage:'+storage
    assignment = state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    supports = {p:a for p,a in assignment.items() if a.get(key,0)>0}
    if any(set(a)!={key} for a in supports.values()):
        raise ValueError('Known W_out records have another physical owner')
    routes = complete_vehicle_routes(raw, required=True)
    start = round(state.time_sec/cfg.simulation.T_u_sec)
    records = [r for r in complete_records(raw) if str(r['link_no']) in supports]
    n = cfg.network.urban_link_storage_veh[storage]-state.urban_link_storage[storage]
    if abs(n-len(records))>1e-7:
        raise ValueError('Known W_out records do not cover the existing stock')
    pending = {int(d):v for d,v in state.urban_storage_release_buffer.get(storage,{}).items() if int(d)>start}
    if sum(pending.values())>n+1e-7:
        raise ValueError('Known W_out reservations exceed physical stock')
    buckets = {start:max(0.,n-sum(pending.values())), **pending}
    cohorts=[]
    for r in records:
        target = _known_classify(r,routes[r['veh_no']],spec)
        # Keep the old aggregate timing; its correlation with IDs is unknown.
        # These initial fixtures have no pending stock. This is not a new travel fit.
        for due, amount in buckets.items():
            if amount>0:
                cohorts.append({'target':target,'vehicles':amount/n,'due':due,'source':'initial_current_route'})
    state.known_legsplit_route_state={'cohorts':cohorts,'plan':None,'received':0.,'departed':0.}
    _known_check(state,cfg)


def known_legsplit_receive(state,cfg,vehicles,due,*,movement=None,off_ramp=None):
    spec=getattr(cfg.network,'known_legsplit_routes',None)
    if spec is None or vehicles<=0:
        return
    if movement is not None:
        if cfg.network.urban_movements[movement].get('receiving_link')!=spec['storage']:
            return
        if movement not in spec['incoming_movements']:
            raise ValueError('Unproved positive W_out movement receipt')
        target='prechoice'
    elif off_ramp=='OR_F_E':
        # Native1130:3 is the unique pinned static path through10682. This is
        # not a recovered route ID for the aggregate freeway predictor's flow.
        target='free'
    else:
        return
    local=state.known_legsplit_route_state
    local['cohorts'].append({'target':target,'vehicles':float(vehicles),'due':int(due),
                            'source':movement or 'offramp_direct:'+off_ramp})
    local['received']+=vehicles
    _known_check(state,cfg)


def known_legsplit_requests(state,cfg,storage,reach,arrived,step):
    spec=getattr(cfg.network,'known_legsplit_routes',None)
    if spec is None or storage!=spec['storage']:
        return None
    if not all(math.isfinite(v) and v>=0 for v in (reach,arrived)) or reach>arrived+1e-7:
        raise ValueError('Known W_out request exceeds ready source stock')
    _known_check(state,cfg)
    local=state.known_legsplit_route_state
    if local['plan'] is not None:
        raise ValueError('Known W_out plan not committed before next request')
    # Existing prior values are used only for physically eligible future choices,
    # exactly once. Already chosen destinations and post-choice unknowns persist.
    prior=cfg.network.boundary_out_ramp_split[storage]
    weights={'free':prior['free'],**prior['ramps']}
    cohorts=[]
    for c in local['cohorts']:
        if c['target']=='prechoice' and c['due']<=step:
            cohorts.extend({**c,'target':target,'vehicles':c['vehicles']*weight}
                           for target,weight in weights.items() if weight>0)
        else:
            cohorts.append(c)
    local['cohorts']=cohorts
    eligible=sum(c['vehicles'] for c in cohorts if c['due']<=step)
    if abs(eligible-arrived)>1e-7:
        raise ValueError('Known W_out ready aliases differ from original release timing')
    factor=reach/arrived if arrived>0 else 0.
    requests=defaultdict(float); plan=[]
    for c in cohorts:
        if c['due']<=step and c['target']!='unknown':
            amount=c['vehicles']*factor
            requests[c['target']]+=amount
            plan.append((c,amount))
    local['plan']={'step':step,'rows':plan,'requests':dict(requests)}
    return dict(requests)


def known_legsplit_commit(state,cfg,receipts,step):
    spec=getattr(cfg.network,'known_legsplit_routes',None)
    if spec is None:
        return
    local=state.known_legsplit_route_state; plan=local['plan']
    actual=defaultdict(float)
    for source,ramp,vehicles in receipts:
        if source==spec['storage']:
            actual[ramp or 'free']+=vehicles
    if plan is None:
        if sum(actual.values())>1e-9:
            raise ValueError('Known W_out receipt without its current plan')
        _known_check(state,cfg)
        return
    if plan['step']!=step:
        raise ValueError('Known W_out receipt uses a stale plan')
    for target,amount in actual.items():
        if not math.isfinite(amount) or amount<0 or amount>plan['requests'].get(target,0.)+1e-7:
            raise ValueError('Known W_out accepted more than its requested destination')
    n=cfg.network.urban_link_storage_veh[spec['storage']]-state.urban_link_storage[spec['storage']]
    if not math.isclose(_known_total(state)-sum(actual.values()),n,rel_tol=0.,abs_tol=1e-7):
        raise ValueError('Known W_out source owner did not commit exactly these receipts')
    for c,requested in plan['rows']:
        total=plan['requests'][c['target']]
        debit=requested*actual[c['target']]/total if total else 0.
        c['vehicles']-=debit
    local['cohorts']=[c for c in local['cohorts'] if c['vehicles']>0]
    local['departed']+=sum(actual.values()); local['plan']=None
    _known_check(state,cfg)
