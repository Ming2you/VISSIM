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
        total_beta = _positive(a['beta'], 'first beta', zero=True)+_positive(b['beta'], 'second beta', zero=True)
        merge_audit.append({'keep': keep, 'removed': removed, 'total_beta': total_beta,
                           'old_capacities_veh_h': [capmap[keep], capmap[removed]], 'single_capacity_veh_h': lanes*per_lane})
        a.update(beta=total_beta, destination=document['prefix_storage'], receiving_link=document['prefix_storage'])
        specs.pop(removed); renames[removed] = keep
        capmap[keep] = lanes*per_lane; capmap.pop(removed)
        turns[keep] = {**row, 'entry_position_m': entry, 'lanes': lanes, 'service_veh_h': lanes*per_lane,
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
