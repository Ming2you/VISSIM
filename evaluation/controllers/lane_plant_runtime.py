"""Source-pinned initialization of the opt-in complete lane plant.

Live vehicle frames supply current inventory and past exchange rates. Selected
reference files supply geometry and fixed model parameters, never future
traffic. Initialization occurs before the area ledger is seeded.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
from bisect import bisect_right
from collections import Counter,defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]


def read_pin(pin):
    path=(ROOT/pin['path']).resolve(strict=True)
    content=path.read_bytes()
    if hashlib.sha256(content).hexdigest()!=pin['sha256']:
        raise ValueError('Lane plant source changed: '+str(path))
    return path


def render_native_geometry(text,geometry):
    """Change only the four observed-cell declarations in the canonical VBS."""
    import re
    for road in ('FW_E','FW_W'):
        values={'SEG_BOUNDS':geometry['bounds'][road],
                'SEG_LENGTHS_KM':[c['length_km'] for c in geometry['cells'] if c['road']==road]}
        for suffix,numbers in values.items():
            key='RW_'+road+'_'+suffix
            replacement=key+' = "'+','.join(format(x,'.12g') for x in numbers)+'"'
            text,count=re.subn(r'^'+key+r' = "[^"\r\n]*"',lambda _:replacement,text,flags=re.MULTILINE)
            if count!=1:raise ValueError('Native geometry declaration missing/duplicated: '+key)
    return text


def load_sources(manifest):
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.canonical_harness import CanonicalFreewayModel,resolve_geometry_profile
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.extract_observations import physical_geometry
    from evaluation.controllers.physical_urban_transport import geometry as urban_geometry
    path=(ROOT/manifest).resolve(strict=True)
    document=json.loads(path.read_text(encoding='utf-8-sig'))
    if document.get('schema')!='coupled-lane-plant/v1':raise ValueError('Unsupported lane plant declaration')
    paths={key:read_pin(pin) for key,pin in document['sources'].items()}
    load=lambda key:json.loads(paths[key].read_text(encoding='utf-8-sig'))
    archived=load('geometry')
    profile=resolve_geometry_profile(archived['geometry_profile'])
    # Re-extract physical endpoints and lane lengths from this native network;
    # a metadata/hash substitution cannot qualify changed road attachments.
    geometry=physical_geometry(paths['network'],geometry_profile=profile)
    component=CanonicalFreewayModel(geometry,paths['reference_config'])
    lane=load('lane_geometry')['geometry']
    routes,exits=urban_geometry(paths['network'])
    return dict(document=document,paths=paths,component=component,geometry=geometry,
        lane_geometry={lane['road']:lane},routes=routes,exits=exits,
        parameters=load('parameters')['parameters'],port_profile=load('port_profile'),
        protocol=load('reference_protocol'),manifest_sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def observe_live(context,raw,*,use_checkpoint=True):
    from evaluation.controllers.lane_plant_observation import LanePlantObserver,load_causal_snapshot
    from evaluation.controllers.network_provenance import snapshot_network_sha256
    if snapshot_network_sha256(raw)!=context['document']['sources']['network']['sha256']:
        raise ValueError('Lane plant network differs from current native observation')
    meta=raw.get('lane_plant_observation',{})
    interval=meta.get('sample_interval_sec',1)
    expected={'directory','run_id','time_s'}|({'sample_interval_sec'} if interval!=1 else set())
    if set(meta)!=expected or meta['run_id']!=raw['run_provenance']['run_id'] or meta['time_s']!=raw['sim_sec']:
        raise ValueError('Current native state lacks its complete lane observation identity')
    if interval!=1:
        proof=json.loads(Path(raw['run_provenance']['manifest_path']).read_text(encoding='utf-8-sig'))
        if proof['signal_observation']['options'].get('sample_interval_sec',1)!=interval:
            raise ValueError('Lane sample cadence differs from config provenance')
    observer=LanePlantObserver(context['geometry'],context['lane_geometry'],context['routes'],history_sec=150,sample_interval_sec=interval)
    return load_causal_snapshot(meta['directory'],observer,int(raw['sim_sec']),
        run_id=meta['run_id'],configuration_sha256=context['manifest_sha256'],use_checkpoint=use_checkpoint)


def bind_current_routes(raw,observation):
    """Join actual same-second COM frame routes to the complete stock by ID."""
    from evaluation.controllers.projection_support import complete_records
    from evaluation.controllers.vehicle_routes import ATTRIBUTES,complete_vehicle_routes
    rows={r[0]:r for r in observation['frames'][-1]['vehicles']}
    physical=complete_records(raw)
    if set(rows)!={v['veh_no'] for v in physical}:raise ValueError('Lane/current snapshot vehicle IDs differ')
    routes=[]
    for v in physical:
        row=rows[v['veh_no']]
        if ([row[1],row[2]]!=[v['link_no'],v['lane_no']]
                or abs(row[3]-v['position_m'])>1e-5 or abs(row[4]-v['speed_kph'])>1e-5):
            raise ValueError('Lane/current snapshot positions differ')
        # COM returns route numbers as doubles. Preserve only exact integer
        # identities; fractional/non-finite numbers still fail validation.
        identity=[int(x) if type(x) is float and math.isfinite(x) and x.is_integer() else x
                  for x in row[6:8]]
        routes.append(dict(zip(ATTRIBUTES,(row[0],*identity,row[8]))))
    output=copy.deepcopy(raw)
    existing=complete_vehicle_routes(raw) if raw.get('vehicle_routes') is not None else None
    if existing is not None and existing!={v['veh_no']:v for v in routes}:
        raise ValueError('Two current route captures disagree')
    n=len(routes);sec=raw['sim_sec']
    output['vehicle_routes']=dict(schema_version='vissim-vehicle-routes-v1',complete=True,records=routes,
        source_attributes=ATTRIBUTES,record_count=n,collection_count_before=n,collection_count_after=n,
        sim_sec_before=sec,sim_sec_after=sec,derived_from_lane_frame=True)
    complete_vehicle_routes(output,required=True)
    return output


def _physical_geometry(network):
    tree=ET.parse(network).getroot()
    links={int(x.get('no')):x for x in tree.findall('./links/link')}
    dimensions={}
    for no,node in links.items():
        points=[tuple(float(p.get(k,0)) for k in ('x','y','zOffset')) for p in node.findall('./geometry/linkPolyPts/linkPolyPoint')]
        dimensions[no]=(math.fsum(math.dist(a,b) for a,b in zip(points,points[1:])),len(node.findall('./lanes/lane')))
    return tree,links,dimensions


def local_history(frames,cutoff,routes,exits,*,sample_interval_sec=1):
    """Reference10643 destination estimator, without diagnostic inflow replay.

    During native warmup, use only the observed interval since the empty start.
   10700 and all other endogenous entries are owned by the coupled network.
    """
    from evaluation.controllers.physical_urban_transport import observe
    start=max(0,cutoff-150)
    from evaluation.controllers.lane_plant_observation import sample_times
    times=sample_times(start,cutoff,sample_interval_sec)
    if set(frames)!=set(times):
        raise ValueError('Local destination history must be contiguous and causal')
    composition=[Counter(),Counter()];before={}
    for sec in times:
        now={v['vehicle']:v for v in observe(frames[sec],routes,exits)['vehicles']}
        for vid,v in before.items():
            if v['link']==10643 and vid in now and now[vid]['link']!=10643:
                composition[v['lane']-1][v['connector']]+=1
        before=now
    result=[]
    for g,counts in enumerate(composition):
        if not counts:counts.update(v['connector'] for v in before.values() if v['link']==10643 and v['lane']==g+1)
        if not counts:counts[None]=1
        total=sum(counts.values());result.append([(k,n/total) for k,n in counts.items()])
    return dict(off_composition=result,background={},exchange_rates=[],information_cutoff_s=cutoff,
                history_start_s=start,endogenous_background=True)


def initialize(context,observation,cfg,state,detectors):
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.canonical_harness import DelayedPort
    from evaluation.controllers.physical_urban_transport import observe,history_inputs,CumulativeLane,CoupledPort,FIFO,tagged
    from evaluation.controllers.lane_urban_runtime import LaneUrbanRuntime,CandidateSignalProgram
    from evaluation.controllers.lane_ramp_runtime import LaneRampRuntime
    from evaluation.controllers.lane_freeway_runtime import LaneFreewayRuntime
    from evaluation.controllers.lane_offramp_runtime import LaneOfframpRuntime
    from evaluation.controllers.control_area_objective import physical_membership_from_ledger
    from evaluation.controllers.observation_projection import audit_projection_provenance
    component=context['component'];net=cfg.network
    if cfg.simulation.T_f_sec!=1 or cfg.simulation.T_u_sec!=1:
        raise ValueError('Declare one-second full-network integration before projection')
    cutoff=int(state.time_sec)
    if observation['information_cutoff_s']!=cutoff or observation['future_traffic_inputs'] is not False:
        raise ValueError('Lane initialization requires the same current causal cutoff')
    frames={f['time_s']:f for f in observation['frames']}
    current_frame=frames[cutoff]
    tree,links,dimensions=_physical_geometry(context['paths']['network'])
    spacing=net.urban_avg_vehicle_length_m
    if spacing!=component.base.network.urban_avg_vehicle_length_m:
        raise ValueError('Lane plant and urban storage use different vehicle spacing')
    physical=physical_membership_from_ledger(json.loads(read_pin(context['document']['membership']).read_text(encoding='utf-8')))
    provenance=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    before={k:net.urban_link_storage_veh[k]-state.urban_link_storage[k] for k in net.urban_link_storage_veh}
    by_link=defaultdict(list)
    for row in current_frame['vehicles']:by_link[int(row[1])].append(row)
    old_provenance=copy.deepcopy(provenance)
    old_dedicated=copy.deepcopy(detectors.get('physical_storage_projection',{}).get('link_to_storage',{}))
    new_support={}

    def move_link(link,storage,capacity,projected_observed=None):
        counts=provenance.get(str(link),{})
        observed=len(by_link[link])
        if abs(math.fsum(counts.values())-observed)>1e-7:
            raise ValueError('Current lane/full-network projection differs on physical link '+str(link))
        for stock,n in counts.items():
            kind,key=stock.split(':',1)
            if kind=='storage':state.urban_link_storage[key]+=n
            elif kind=='movement':state.urban_movement_queue[key]-=n
            else:raise ValueError('Physical lane migration would take another owned ramp/transit stock')
        projected=observed if projected_observed is None else projected_observed
        if capacity<projected-1e-7:raise ValueError('Observed physical stock exceeds finite lane capacity')
        net.urban_link_storage_veh[storage]=capacity
        state.urban_link_storage[storage]=capacity-projected
        state.urban_arrival_buffer.pop(storage,None)
        state.urban_storage_release_buffer.pop(storage,None)
        provenance[str(link)]={'storage:'+storage:float(observed)} if observed else {}
        new_support[str(link)]=storage
        detectors.setdefault('physical_storage_projection',{}).setdefault('link_to_storage',{})[str(link)]=storage
        detectors.setdefault('link_to_origins',{})[str(link)]=[storage]
        detectors.get('link_to_movements',{}).pop(str(link),None)

    current=observe(current_frame,context['routes'],context['exits'])
    history=local_history(frames,cutoff,context['routes'],context['exits'],sample_interval_sec=observation.get('sample_interval_sec',1))
    side_current=[v for v in current['vehicles'] if v['link']==10700]
    current['vehicles']=[v for v in current['vehicles'] if v['link']!=10700]
    initial_projection=None
    if context.get('initial_spillback_projection',False):
        from evaluation.controllers.lane_initial_projection import project
        current,initial_projection=project(current,context['paths']['network'],spacing)
    wave=context['protocol']['wave_m_s']
    speed=context['protocol']['urban_free_speed_m_s']
    port=component.offramps['10643']
    off_lanes=[CumulativeLane(port['storage_capacity_veh']/2,port['length_m'],
        context['port_profile']['travel_speed_kmh']['10643'],
        [(v['position_m'],v['speed_kmh'],v['length_m']) for v in current['vehicles'] if v['link']==10643 and v['lane']==g],
        cutoff,wave) for g in (1,2)]
    coupled=CoupledPort(off_lanes,current,history,context['paths']['network'],CandidateSignalProgram(),0,
        speed,spacing,wave,lateral_access=context['protocol']['lateral_access'],
        history_exchange=context['protocol']['history_exchange'],
        continuation=context['protocol']['unrouted_continuation'])
    coupled.urban.prefer_more_receiving_space=context['protocol']['prefer_more_receiving_space']
    coupled.urban.defer_mandatory_while_forward_open=context['protocol']['defer_mandatory_while_forward_open']
    coupled.urban.defer_destinations=context['protocol']['defer_destinations']
    coupled.urban.compact_equal_behavior=True
    length,lanes=dimensions[10700]
    if lanes!=1:raise ValueError('10700 side continuation geometry changed')
    side=CumulativeLane(length/spacing,length,speed*3.6,
        [(v['position_m'],v['speed_kmh'],v['length_m']) for v in side_current],cutoff,wave)
    local=LaneUrbanRuntime(coupled,cfg,movement_by_exit={10634:'SC1004_W_to_E_SC1005',
        10635:'SC1004_W_to_N_SC1003',10642:'SC1004_W_to_S'},side_port=side,
        side_fifo=FIFO((tagged(v),1.) for v in sorted(side_current,key=lambda v:-v['position_m'])))
    state.lane_urban_runtime=local
    local.bind_service_ownership(cfg)
    for road,key in local.local_storage.items():
        cap=(side.capacity if road==10700 else math.fsum(c for (r,l,i),c in coupled.urban.cap.items() if r==road))
        projected=(sum(v['link']==road for v in current['vehicles'])
                   if initial_projection is not None and road!=10700 else None)
        move_link(road,key,cap,projected_observed=projected)
    if initial_projection is not None:
        for row in initial_projection['moves']:
            source=provenance[str(row['source_link'])]
            old='storage:'+local.local_storage[row['source_link']]
            new='storage:'+local.local_storage[row['target_link']]
            if source.get(old,0.)<row['vehicles']:raise ValueError('Projected vehicle lacks its original stock')
            source[old]-=row['vehicles']
            source[new]=source.get(new,0.)+row['vehicles']
        state.local_observation_summary['lane_initial_spillback_projection']=copy.deepcopy(initial_projection)

    groups=json.loads((ROOT/context['document']['off_groups']).read_text(encoding='utf-8'))['groups']
    descriptions={};ports={}
    for group,description in groups.items():
        for branch in ('signal','direct'):
            off=description[branch+'_connector'];row=component.offramps[off]
            storage=('lane_off_'+off if branch=='direct' else net.off_ramp_storage_link[group])
            move_link(int(off),storage,row['storage_capacity_veh'])
            descriptions[off]={**row,'storage':storage,'group':group,'direct':branch=='direct',
                'target':net.offramp_direct_tail_by_offramp[group] if branch=='direct' else None,
                'local_upstream':off=='10638'}
            if off!='10643':ports[off]=DelayedPort(row['storage_capacity_veh'],row['length_m'],
                context['port_profile']['travel_speed_kmh'][off],
                [[r[3],r[4],r[2]] for r in by_link[int(off)]],cutoff,interval_service=True)
    state.lane_offramp_runtime=LaneOfframpRuntime(ports,descriptions,coupled,physical)
    # Direct downstream tails use the existing explicit tail-exit allocator.
    # A travel reservation becoming ready must not itself erase that stock.
    net.lane_plant_tail_stores=tuple(sorted({r['target'] for r in descriptions.values()
        if r['direct'] and r['target'].endswith('_W_tail')}))

    # After a physical71 exit, its connector is wholly downstream. The old
    # aggregate stopline projection could share10635/10642 with in_SC1004_W.
    for link,target in ((10635,'SC1004_to_SC1003'),(10642,'SC1004_S_out')):
        observed=len(by_link[link]);counts=provenance.get(str(link),{})
        if abs(math.fsum(counts.values())-observed)>1e-7:raise ValueError('Local exit projection differs')
        for stock,n in counts.items():
            kind,key=stock.split(':',1)
            if kind=='storage':state.urban_link_storage[key]+=n
            elif kind=='movement':state.urban_movement_queue[key]-=n
            else:raise ValueError('Local exit has another physical stock owner')
        state.urban_link_storage[target]-=observed
        if state.urban_link_storage[target]<-1e-7:raise ValueError('Local exit overfills its downstream storage')
        provenance[str(link)]={'storage:'+target:float(observed)} if observed else {}
        detectors['link_to_origins'][str(link)]=[target]
        detectors.get('link_to_movements',{}).pop(str(link),None)
        detectors['physical_storage_projection']['link_to_storage'][str(link)]=target

    # Remove relocated connector residence from the old aggregate travel
    # schedules. Unmoved tails retain their prior timing approximation.
    for key,n0 in before.items():
        if key in new_support.values():continue
        n=net.urban_link_storage_veh[key]-state.urban_link_storage[key]
        if n0 and abs(n-n0)>1e-8:
            for name in ('urban_arrival_buffer','urban_storage_release_buffer'):
                table=getattr(state,name).get(key,{})
                getattr(state,name)[key]={t:v*n/n0 for t,v in table.items()}
        elif not n0 and n>1e-8:
            from src.models import urban_queue_model as uqm
            due=cutoff+uqm._link_delay_steps(state,cfg,key)
            if key in uqm.approach_routing(cfg):uqm._schedule(state.urban_arrival_buffer,key,due,n)
            uqm._schedule(state.urban_storage_release_buffer,key,due,n)

    _initialize_upstream(local,state,cfg,detectors,provenance,old_provenance,by_link,links,dimensions,context)
    # A moved road no longer supplies free receiving space in its old parent.
    moved_by_parent=defaultdict(float)
    for off,row in descriptions.items():
        if row['direct']:
            parent=old_dedicated.get(off,row['target'])
            length,width=dimensions[int(off)];moved_by_parent[parent]+=length*width/spacing
    for key,removed in moved_by_parent.items():
        if key==local.origin:continue
        used=net.urban_link_storage_veh[key]-state.urban_link_storage[key]
        cap=net.urban_link_storage_veh[key]-removed
        if cap<used-1e-7 or cap<=0:raise ValueError('Relocated road does not fit its remaining parent storage: '+key)
        net.urban_link_storage_veh[key]=cap;state.urban_link_storage[key]=cap-used

    for road in net.freeway_links:
        cells=[c for c in context['geometry']['cells'] if c['road']==road]
        bins=[[] for _ in cells]
        for row in current_frame['vehicles']:
            address=context['geometry']['addresses'].get(row[1],context['geometry']['addresses'].get(str(row[1])))
            if address and address[0]==road:
                p=float(address[1])+row[3]
                i=min(len(cells)-1,bisect_right(context['geometry']['bounds'][road],p)-1)
                bins[i].append(row)
        state.freeway_density[road]=[len(rows)/(c['length_km']*c['effective_lanes']) for rows,c in zip(bins,cells)]
        state.freeway_effective_lanes[road]=[c['effective_lanes'] for c in cells]
        state.freeway_speed[road]=[math.fsum(r[4] for r in rows)/len(rows) if rows else state.freeway_speed[road][i]
                                    for i,rows in enumerate(bins)]
    freeway=LaneFreewayRuntime(component,state,cfg,observation,context['parameters'],off_splits=observation['off_split_ratio'])
    for road,conf in freeway.configs.items():
        # Objective/resource consumers must see the very same cell FD and
        # anticipation parameters as each direction's physical transition.
        net.freeway_segment_params[road]=copy.deepcopy(conf.network.freeway_segment_params[road])
        if road=='FW_E':conf.network.terminal_zero_gradient=True
        for off in conf.network.off_ramps:
            conf.network.off_ramp_storage_link[off]=descriptions[off]['storage']
        conf.network.physical_vehicle_counts=True
        conf.freeway_offramp_capacity_drop.enabled=context['port_profile']['occupancy_lane_loss']
    specs={}
    heads=defaultdict(list)
    for node in tree.findall('./signalHeads/signalHead'):
        road,lane=map(int,node.get('lane').split());heads[road].append(float(node.get('pos')))
    for name,r in component.ramps.items():
        no=r['connector'];length=r['length_m']
        specs[name]=dict(connector_id=str(no),length_m=length,head_position_m=min(heads[no]),lanes=r['lanes'],
            spacing_m=spacing,travel_speed_kmh=context['port_profile']['travel_speed_kmh'][str(no)],
            time_sec=cutoff,initial_cohorts=[[v[3],v[4],v[2]] for v in by_link[no]],initial_backlog_veh=0.)
        if name in component.ramp_receiving_nodes:
            entries=Counter()
            start=max(0,cutoff-150)
            past={v[0]:v for v in frames[start]['vehicles']}
            for t in range(start+1,cutoff+1):
                now={v[0]:v for v in frames[t]['vehicles']}
                for vid,v in now.items():
                    if v[1]==no and (vid not in past or past[vid][1]!=no):entries[v[2]]+=1
                past=now
            total=math.fsum(entries.values())
            # Empty history has no identified lane share. Equal shares are an
            # explicit forecast closure for new endogenous urban arrivals.
            specs[name]['lane_arrival_shares']=[entries[i]/total if total else 1/r['lanes'] for i in range(1,r['lanes']+1)]
        net.ramp_queue_max_veh_by_ramp[name]=r['storage_capacity_veh']
        net.ramp_merge_segment_index[name]=r['to_cell']
        row=net.physical_ramp_branches['ramps'][name]
        row['storage_veh']=r['storage_capacity_veh']
        if name in component.ramp_head_service_veh_per_cycle:
            curve=component.ramp_head_service_veh_per_cycle[name]
            row['service_by_green_veh_h']={'0':0.,**{g:n*3600/10 for g,n in curve.items()}}
            row['service_capacity_veh_h']=row['service_by_green_veh_h']['10']
            net.ramp_capacity_veh_h[name]=row['service_capacity_veh_h']
    state.lane_freeway_runtime=freeway
    timetable=net.native_input_schedule
    directed={}
    for no,row in timetable['inputs'].items():
        if row['role'].startswith('freeway'):
            address=context['geometry']['addresses'].get(int(row['physical_source']),
                context['geometry']['addresses'].get(row['physical_source']))
            if address is None or address[1]!=0:raise ValueError('Native mainline input is not a modeled upstream boundary')
            directed[no]=address[0]
    if sorted(directed.values())!=sorted(net.freeway_links):
        raise ValueError('Each freeway must have exactly one declared native upstream input')
    timetable['freeway_link_by_input']=directed
    state.lane_ramp_runtime=LaneRampRuntime(component,specs,state,cycle_sec=net.physical_ramp_branches['cycle_sec'])
    local.sync_stores(state,cfg)
    state.lane_offramp_runtime.assert_mirrors(state,cfg)
    audit_projection_provenance(provenance,
        {k:net.urban_link_storage_veh[k]-state.urban_link_storage[k] for k in net.urban_link_storage_veh},
        state.urban_movement_queue,state.ramp_queue)
    net.lane_plant_enabled=True
    net.lane_plant_sources=copy.deepcopy(context['document'])
    return {'lane_plant_enabled':True,'lane_plant_observed_sec':cutoff,
        **({'lane_initial_spillback_projection':initial_projection} if initial_projection is not None else {}),
        'lane_plant_manifest_sha256':context['manifest_sha256']}


def _initialize_upstream(local,state,cfg,detectors,provenance,old_provenance,by_link,links,dimensions,context):
    """Rebuild only70/10776/10640 travel before the local lane cells.

    Native routes1134:3 are ramp-bound;1140 and1138 are city-bound. A vehicle
    already on a city branch never receives the old aggregate on-ramp beta.
    """
    from evaluation.controllers.physical_urban_transport import observe
    source=local.origin;net=cfg.network;spacing=net.urban_avg_vehicle_length_m
    support={int(link) for link,origins in detectors['link_to_origins'].items() if source in origins}
    if support-{70,10776,10640,10637}:raise ValueError('Unreviewed physical support in local upstream: '+str(support))
    support|={70,10776,10640,10637}
    movements=set(local.exits_by_movement)|{'SC1004_W_to_onE'}
    for key in movements:
        leftover=state.urban_movement_queue[key]
        assigned=math.fsum(row.get('movement:'+key,0.) for link,row in provenance.items() if int(link) in support)
        if abs(leftover-assigned)>1e-7:raise ValueError('Local upstream movement has another physical source')
        state.urban_movement_queue[key]=0.
    state.urban_arrival_buffer[source]={};state.urban_storage_release_buffer[source]={}
    state.shared_approach_state.pop('city_arrival_tags',None)
    cap=math.fsum(dimensions[link][0]*dimensions[link][1]/spacing for link in support)
    n=math.fsum(len(by_link[link]) for link in support)
    net.urban_link_storage_veh[source]=cap;state.urban_link_storage[source]=cap-n
    end70=float(links[10776].find('fromLinkEndPt').get('pos'))
    enter70=float(links[10638].find('toLinkEndPt').get('pos'))
    local.entry_paths={'city':dimensions[10640][0],'off10638':end70-enter70+dimensions[10776][0],
                       'current':0.}
    # Constant native relative flows define only future unassigned fluid.
    tree=ET.parse(context['paths']['network']).getroot()
    for entry,decision in (('city',1138),('off10638',1140)):
        d=tree.find("./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='%s']"%decision)
        values=Counter()
        for route in d.findall('./vehRoutSta/vehicleRouteStatic'):
            path=context['routes'][decision,int(route.get('no'))]
            matches=[c for c in local.movements if c in path]
            if len(matches)!=1:raise ValueError('Native local route has no unique physical exit')
            declared=route.get('relFlow','').split()
            if not declared:value=1.
            elif len(declared)==2 and declared[1].startswith('0:'):value=float(declared[1][2:])
            else:raise ValueError('Time-varying local route shares need explicit integration')
            values[local.movements[matches[0]]]+=value
        total=math.fsum(values.values())
        if total<=0:raise ValueError('Empty native local destination distribution')
        local.future_shares[entry]={m:v/total for m,v in values.items()}
    for link in support:
        observed=by_link[link]
        old=provenance.get(str(link),{})
        if abs(math.fsum(old.values())-len(observed))>1e-7:raise ValueError('Local upstream projection differs from current vehicles')
        if any(stock not in {'storage:'+source}|{'movement:'+m for m in movements} for stock in old):
            raise ValueError('Local upstream has another current stock owner')
        provenance[str(link)]={'storage:'+source:float(len(observed))} if observed else {}
        detectors['link_to_origins'][str(link)]=[source]
        detectors.get('link_to_movements',{}).pop(str(link),None)
        for v in observed:
            path=context['routes'].get((v[6],v[7])) if v[8] and v[8].lower()=='static' else None
            if path and 10639 in path:
                shares={'SC1004_W_to_onE':1.}
                end=float(links[10639].find('fromLinkEndPt').get('pos'))
                distance=(max(0.,end-v[3]) if link==70 else max(0.,dimensions[10637][0]-v[3])+
                          end-float(links[10637].find('toLinkEndPt').get('pos')))
                if link not in (70,10637):raise ValueError('Observed city connector cannot reroute to the on-ramp')
            else:
                matches=[c for c in local.movements if path and c in path]
                shares=({local.movements[matches[0]]:1.} if len(matches)==1 else
                        local.future_shares['city' if link==10640 else 'off10638'])
                distance=(max(0.,end70-v[3])+dimensions[10776][0] if link==70 else
                          max(0.,dimensions[link][0]-v[3])+(end70-float(links[10637].find('toLinkEndPt').get('pos'))+
                          dimensions[10776][0] if link==10637 else 0.))
            local.schedule_upstream(state,cfg,int(state.time_sec),1.,entry='city' if link==10640 else 'current',
                shares=shares,distance_m=distance,speed_kmh=max(v[4],net.urban_avg_speed_km_h/3.))


def bind_area(state,cfg):
    """After area routes are configured, give both road kernels that same policy."""
    if not getattr(cfg.network,'lane_plant_enabled',False):return
    for conf in state.lane_freeway_runtime.configs.values():
        for key,value in vars(cfg.network).items():
            if key.startswith('control_area_'):setattr(conf.network,key,copy.deepcopy(value))
