"""Use the existing four-arm runner with an explicit physical mesh input.

The raw refined forecasts are retained; a conservative parent aggregation is
returned only to the unchanged historical scoring helper.
"""
from pathlib import Path
import bisect, copy, contextlib, gzip, hashlib, json, math, sys, time
from collections import defaultdict
B=Path(__file__).resolve().parent;H=B.parent;K=H/'cohort_dynamics_20260920'
sys.path.insert(0,str(H.parents[2]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import urban_route_transport as u

def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')


def apply_physical_coefficients(cfg,road,values):
    """Explicit calibration inputs; no change when absent. Geometry is fixed."""
    row_keys={'v_free','rho_crit','rho_max','metanet_a_m','metanet_kappa_veh_km_lane'}
    global_keys={'metanet_delta_merge','freeway_lane_drop_phi'}
    if set(values)-row_keys-global_keys:raise ValueError('Unknown physical coefficient')
    for key,value in values.items():
        if type(value) not in (int,float) or not math.isfinite(value) or value<0 or (key in row_keys and value==0):
            raise ValueError('Invalid physical coefficient: '+key)
        setattr(cfg.network,key,value)
        if key in row_keys:
            for row in cfg.network.freeway_segment_params[road]:row[key]=value
    if not 0<cfg.network.rho_crit<cfg.network.rho_max:raise ValueError('Critical density must be below jam density')


def save_compressed(path,value):
    with gzip.open(str(path)+'.gz','wt',encoding='utf-8',compresslevel=1) as stream:
        json.dump(value,stream,ensure_ascii=False,allow_nan=False,separators=(',',':'))

def apply_regional_coefficients(cfg,road,regions):
    """Explicit FD coefficients on disjoint fixed cells; no geometry/storage edits."""
    rows=cfg.network.freeway_segment_params[road];seen=set()
    if not isinstance(regions,list) or not regions:raise ValueError('Explicit nonempty physical regions required')
    for region in regions:
        if set(region)!={'cells','coefficients'}:raise ValueError('Invalid physical region fields')
        cells=region['cells'];values=region['coefficients']
        if not isinstance(cells,list) or not cells or any(type(i) is not int or not 0<=i<len(rows) or i in seen for i in cells) or len(set(cells))!=len(cells):
            raise ValueError('Invalid or overlapping physical cells')
        if not isinstance(values,dict) or not values or set(values)-{'rho_crit','metanet_a_m'}:raise ValueError('Unsupported regional physical coefficient')
        if any(type(x) not in (int,float) or not math.isfinite(x) or x<=0 for x in values.values()):raise ValueError('Invalid regional physical value')
        for i in cells:
            if values.get('rho_crit',rows[i]['rho_crit'])>=rows[i]['rho_max']:raise ValueError('Regional critical density exceeds storage density')
        seen.update(cells)
    for region in regions:
        for i in region['cells']:rows[i].update(region['coefficients'])


def install(model,w,guard=False,mesh_input=None,replay_context=None):
    geo=load(B/('geometry_200_branch_guard.json' if guard else 'geometry_200.json'));parents=load(B/'parent_map.json')
    if mesh_input is not None:
        assert set(mesh_input)=={'geometry','parents','initial_groups'}
        paths={key:(B/value).resolve() for key,value in mesh_input.items()}
        for path in paths.values():path.relative_to(B)
        geo=load(paths['geometry']);parents=load(paths['parents'])
        for road,pmap in parents.items():
            cells=[r for r in geo['cells'] if r['road']==road]
            assert len(cells)==len(pmap) and [r['cell'] for r in cells]==list(range(len(pmap)))
            assert [r['parent_cell'] for r in cells]==pmap
    before=copy.deepcopy(w['lane_group_dynamics']['FW_E']);oldcells=dict(model.geometry_cells)
    context=load(replay_context) if replay_context is not None else None
    current=load(u.e.ROOT/context['initial'] if context else B/'initial_2400.json');bycell=defaultdict(list)
    for r in current:
        road=r['road']
        if road is None:continue
        chain=next(x for x in geo['chains'][road] if x['link']==r['link'])
        x=chain['offset_m']+r['position_m'];i=max(0,min(len(parents[road])-1,bisect.bisect_right(geo['bounds'][road],x)-1))
        c=parents[road][i];widths=before['widths'][c] if road=='FW_E' else [sum(p['lanes']*p['length_m'] for p in oldcells[road,c]['physical_pieces'])/(oldcells[road,c]['length_km']*1000)]
        group=next(g for g in range(len(widths)) if r['lane']<=sum(widths[:g+1])+1e-8)
        bycell[road,i].append({**r,'x':x,'group':group})
    oldinit={(r['road'],r['cell']):r for r in w['initial_cells']};newinit=[]
    for c in geo['cells']:
        road,i=c['road'],c['cell'];p=parents[road][i];rs=bycell[road,i]
        fallback=oldinit[road,p]['v_kmh']
        newinit.append({**oldinit[road,p],'cell':i,'n_veh':len(rs),
            'v_kmh':sum(r['speed_kmh'] for r in rs)/len(rs) if rs else fallback})
    for (road,p),old in oldinit.items():
        rs=[r for r in newinit if r['road']==road and parents[road][r['cell']]==p]
        assert sum(r['n_veh'] for r in rs)==old['n_veh'],(road,p,'Initial stock changed',sum(r['n_veh'] for r in rs),old['n_veh'])
        if old['n_veh']:
            assert abs(sum(r['n_veh']*r['v_kmh'] for r in rs)-old['n_veh']*old['v_kmh'])<1e-6,(road,p,'Initial speed moment changed')
    w['initial_cells']=newinit
    s=copy.deepcopy(before);s['widths']=[copy.deepcopy(before['widths'][p]) for p in parents['FW_E']]
    s['exchange_rates_per_sec']=[copy.deepcopy(before['exchange_rates_per_sec'][p]) for p in parents['FW_E']]
    s['matrices']=[];s['initial_groups']=[]
    for i,p in enumerate(parents['FW_E']):
        if i<len(parents['FW_E'])-1:
            if p==parents['FW_E'][i+1]:s['matrices'].append([[float(g==h) for h in range(len(s['widths'][i]))] for g in range(len(s['widths'][i]))])
            else:s['matrices'].append(copy.deepcopy(before['matrices'][p]))
        row=[]
        for group in range(len(s['widths'][i])):
            rs=[r for r in bycell['FW_E',i] if r['group']==group]
            row.append(dict(n_veh=len(rs),v_kmh=sum(r['speed_kmh'] for r in rs)/len(rs) if rs else before['initial_groups'][p][group]['v_kmh']))
        s['initial_groups'].append(row)
    route={r['vehicle']:r for r in load(u.e.ROOT/context['intent'] if context else K/'current_mainline_route_v1/result.json')['current_vehicles']}
    for name,kind in [('ramp_access','ramp'),('off_access','offramp')]:
        for key,value in s[name].items():
            port=next(p for p in geo['boundaries'] if p['kind']==kind and (p['id']==key if kind=='ramp' else str(p['connector'])==key))
            value['cell']=port['to_cell'] if kind=='ramp' else port['from_cell']
    s['initial_ramp_origin']={};s['initial_off_eligible']={}
    # Verify actual past origin IDs against the pre-existing whole-cell tags.
    for key,p in model.ramps.items():
        if p['road']!='FW_E':continue
        parent=p['to_cell'];old=[0.]*len(before['widths'][parent])
        for i,c in enumerate(parents['FW_E']):
            if c!=parent:continue
            for r in bycell['FW_E',i]:
                if r['origin']==p['connector']:old[r['group']]+=1
        assert old==before['initial_ramp_origin'][key],(key,'Past origin IDs incomplete',old,before['initial_ramp_origin'][key])
        i=s['ramp_access'][key]['cell'];s['initial_ramp_origin'][key]=[sum(r['origin']==p['connector'] and r['group']==g for r in bycell['FW_E',i]) for g in range(len(s['widths'][i]))]
    for key,p in model.offramps.items():
        if p['road']!='FW_E':continue
        i=s['off_access'][key]['cell'];s['initial_off_eligible'][key]=[sum(r['x']<p['chain_pos_m'] and r['group']==g for r in bycell['FW_E',i]) for g in range(len(s['widths'][i]))]
    stop=s['off_access']['10643']['cell'];cut=model.offramps['10643']['chain_pos_m'];beta=model.upstream_exit_inventory['10643']
    s['observed_first_exit_by_group']=[]
    for i in range(stop+1):
        values=[]
        for group in range(len(s['widths'][i])):
            rs=[r for r in bycell['FW_E',i] if r['group']==group and r['x']<cut]
            values.append(sum(beta if route[r['vehicle']]['off10643_intent'] is None else float(route[r['vehicle']]['off10643_intent']) for r in rs))
        s['observed_first_exit_by_group'].append(values)
    part={}
    for key in model.branch_partition:
        i=s['off_access'][key]['cell'];cut=model.offramps[key]['chain_pos_m'];part[key]={}
        for side in ('pre','post'):
            out=[]
            for group,row in enumerate(s['initial_groups'][i]):
                rs=[r for r in bycell['FW_E',i] if r['group']==group and (r['x']<cut)==(side=='pre')]
                out.append(dict(n_veh=len(rs),v_kmh=sum(r['speed_kmh'] for r in rs)/len(rs) if rs else row['v_kmh']))
            part[key][side]=out
    s['branch_partition_initial']=part;w['lane_group_dynamics']['FW_E']=s
    for road,pmap in parents.items():
        net=model.base.network
        original=copy.deepcopy(net.freeway_segment_params[road])
        cells=[r for r in geo['cells'] if r['road']==road]
        net.freeway_segment_params[road]=[{**original[p], 'segment_length_km':c['length_km']} for p,c in zip(pmap,cells)]
        net.freeway_segment_length_profile_km[road]=[c['length_km'] for c in cells]
        net.freeway_segment_lanes[road]=[c['lane_km']/c['length_km'] for c in cells]
        w['vsl_zone_heads'][road]=list(range(len(pmap)))
    for step in w['boundary_steps']:
        old=step['vsl_commands'];step['vsl_commands']={f'{road}__seg{i}':old[f'{road}__seg{p}'] for road,ps in parents.items() for i,p in enumerate(ps)}
    # The native DSD zone approximation is inherited exactly from each parent;
    # this test changes spatial resolution, not actuator coverage.
    model.geometry=geo;model.geometry_cells={(r['road'],r['cell']):r for r in geo['cells']}
    for name,kind in [('ramps','ramp'),('offramps','offramp')]:
        for key,old in getattr(model,name).items():
            p=next(p for p in geo['boundaries'] if p['kind']==kind and (p['id']==key if kind=='ramp' else str(p['connector'])==key))
            old.update(from_cell=p['from_cell'],to_cell=p['to_cell'])
    for road,travel in model.lane_port_travel.items():
        for key in travel['ramp_remaining_km']:
            p=model.ramps[key];c=model.geometry_cells[road,p['to_cell']];travel['ramp_remaining_km'][key]=(c['end_m']-p['chain_pos_m'])/1000
        for key in travel['off_distance_km']:
            p=model.offramps[key];c=model.geometry_cells[road,p['from_cell']];travel['off_distance_km'][key]=(p['chain_pos_m']-c['start_m'])/1000
    initial_path=paths['initial_groups'] if mesh_input is not None else B/('guard_initial_groups.json' if guard else 'refined_initial_groups.json')
    if context:
        assert mesh_input is None,'Restart currently uses the existing guarded mesh only'
        initial_path=u.e.ROOT/context['refined_initial']
    # Calibration workers share the SAME observed initial state. Do not
    # truncate this common artifact on every otherwise independent candidate.
    if initial_path.exists():assert load(initial_path)==s,'Observed initial groups changed'
    else:save(initial_path,s)
    return parents,oldcells

def aggregate(pred,parents,oldcells):
    p=copy.deepcopy(pred)
    for key,tkey in [('cells','time_s'),('flows','window_end_s'),('lane_groups','time_s')]:
        if key=='lane_groups':rows=p[key]['FW_E']
        else:rows=p[key]
        buckets=defaultdict(list)
        for r in rows:buckets[(r.get('road','FW_E'),r[tkey],parents[r.get('road','FW_E')][r['cell']],r.get('group'))].append(r)
        output=[]
        for (road,t,parent,group),rs in buckets.items():
            r=copy.deepcopy(rs[-1]);r['cell']=parent
            if key=='flows':
                for col in ('source_admissions','ramp_merges','off_departures','terminal_exits'):r[col]=sum(v[col] for v in rs)
            else:
                n=sum(v['n_veh'] for v in rs);r['n_veh']=n;r['v_kmh']=sum(v['n_veh']*v['v_kmh'] for v in rs)/n if n else r['v_kmh']
                if key=='cells':r['rho_veh_per_km_lane']=r['rho_canonical']=n/oldcells[road,parent]['lane_km']
                else:
                    for col in ('branch_veh','exchanged_veh','merge_in_veh','off_out_veh','ramp_origin_veh','upstream_exit_veh'):
                        if col in r:r[col]=sum(v[col] for v in rs)
                    # Same parent boundary flow, excluding internal transfers.
                    r['longitudinal_in_veh']=rs[0]['longitudinal_in_veh']
            output.append(r)
        if key=='lane_groups':p[key]['FW_E']=output
        else:p[key]=output
    return p

def main():
    mode=sys.argv[1];assert mode in ('reference5','reference1','refined1','refined_guard1')
    # Optional bounded local calibration uses this same mesh/physical runner.
    fit=load(Path(sys.argv[2])) if len(sys.argv)>2 else None
    replay_context=u.e.ROOT/fit['replay_context'] if fit is not None and fit.get('replay_context') else None
    if replay_context is not None:replay_context.resolve().relative_to(u.e.ROOT)
    group='calibration_v1' if fit is None else fit.get('output_group','calibration_v1')
    assert Path(group).name==group
    out=B if fit is None else B/group/fit['name']
    if fit is not None:
        assert mode=='refined_guard1' and Path(fit['name']).name==fit['name']
        out.mkdir(exist_ok=False)
    refined=mode.startswith('refined')
    original_arms=u.ARMS
    selected_arms=tuple(fit.get('arms',original_arms)) if fit is not None else original_arms
    assert selected_arms and selected_arms[0]=='none' and len(set(selected_arms))==len(selected_arms)
    assert all(a in original_arms for a in selected_arms)
    original=u.e.simulate;original_window=u.e.window;calls=0;times=[];effective=[]
    vsl_policy=fit.get('diagnostic_vsl_policy') if fit is not None else None
    if vsl_policy is not None:
        assert set(vsl_policy)=={str(i) for i in range(51,59)}
        assert all(isinstance(row,list) and len(row)==3 and all(type(x) is int and x in (80,100,120) for x in row) for row in vsl_policy.values())
        assert all(abs(b-a)<=20 for row in vsl_policy.values() for a,b in zip([120]+row,row))
        assert len({tuple(vsl_policy[str(i)]) for i in range(51,55)})==1
        assert len({tuple(vsl_policy[str(i)]) for i in range(55,59)})==1
        def policy_window(data,model,cutoff,mode,profile,commands,**kwargs):
            def selected_commands(t):
                greens,ids=commands(t)
                if ids:
                    assert set(ids)=={int(i) for i in vsl_policy}
                    interval=int((t-cutoff)//150);assert 0<=interval<3
                    ids={int(i):value[interval] for i,value in vsl_policy.items()}
                return greens,ids
            # Reuse the existing physical DSD -> parent-cell mapping. Never
            # replace ramp commands or the observed/history boundary inputs.
            result=original_window(data,model,cutoff,mode,profile,selected_commands,**kwargs)
            save(out/f'vsl_policy_{selected_arms[calls]}.json',dict(policy=vsl_policy,
                nonempty_commands_only=True,window_steps=[dict(time_s=s['window_start_s'],vsl_commands=s['vsl_commands']) for s in result['boundary_steps']]))
            return result
        u.e.window=policy_window
    def simulate(model,window,parameters):
        nonlocal calls
        fields=('base','geometry','geometry_cells','ramps','offramps','lane_port_travel')
        snapshot={k:copy.deepcopy(getattr(model,k)) for k in fields}
        original_config=model._config
        try:
            w=copy.deepcopy(window)
            if refined:parents,oldcells=install(model,w,guard=mode=='refined_guard1',mesh_input=fit.get('diagnostic_mesh') if fit is not None else None,replay_context=replay_context)
            outlet=fit.get('diagnostic_off_service') if fit is not None else None
            if outlet is not None:
                assert set(outlet)=={'mode','connectors'} and outlet['mode']=='triangular_free_outlet'
                assert outlet['connectors'] and len(set(outlet['connectors']))==len(outlet['connectors'])
                assert set(outlet['connectors'])<={'10682','10483'}
                # Optimistic diagnostic only: retain causal travel and finite
                # storage, replace the historical throughput ceiling by the
                # existing triangular-link intrinsic sending capacity. No
                # downstream traffic/merge restriction is represented here.
                wave=load(K/'off_spatial_supply_v1/result.json')['wave_m_s']
                spacing=model.base.network.urban_avg_vehicle_length_m
                receipts=[]
                for off in outlet['connectors']:
                    port=model.offramps[off];speed=w['port_dynamics']['travel_speed_kmh'][off]/3.6
                    cap=port['lanes']*speed*wave/(spacing*(speed+wave))*3600
                    previous=sorted({step['off_drain_vph'][off] for step in w['boundary_steps']})
                    for step in w['boundary_steps']:step['off_drain_vph'][off]=cap
                    receipts.append(dict(connector=off,previous_vph=previous,diagnostic_vph=cap,
                        wave_m_s=wave,spacing_m=spacing,travel_speed_m_s=speed))
                save(out/f'off_service_{selected_arms[calls]}.json',dict(ports=receipts,optimistic_free_outlet=True,
                    actual_downstream_receiving_model=False,production_adopted=False))
            if fit is not None:
                def configuration(road,values):
                    cfg=original_config(road,values)
                    if road=='FW_E':
                        for i,row in enumerate(cfg.network.freeway_segment_params[road]):
                            for region in fit.get('regions',[fit]):
                                if parents[road][i] in region['parent_cells']:
                                    row['metanet_tau_h']=region['tau_sec']*(1/3600)
                                    row['metanet_nu_km2_h']=region['nu_km2_h']
                                    row['rho_crit']*=region['rho_multiplier']
                        cfg.network.metanet_delta_merge=fit['delta_merge']
                        if 'hadiuzzaman' in fit:cfg.network.freeway_hadiuzzaman={road:copy.deepcopy(fit['hadiuzzaman'])}
                        if 'kappa' in fit:
                            cfg.network.metanet_kappa_veh_km_lane=fit['kappa']
                            for row in cfg.network.freeway_segment_params[road]:row['metanet_kappa_veh_km_lane']=fit['kappa']
                        if 'port_response' in fit:cfg.network.freeway_port_response={road:copy.deepcopy(fit['port_response'])}
                        if 'anticipation' in fit:
                            from evaluation.controllers.freeway_fd import configure_state_response
                            configure_state_response(cfg,{'freeway':{'state_response':{road:{'anticipation':fit['anticipation']}}}})
                        if 'physical_coefficients' in fit:apply_physical_coefficients(cfg,road,fit['physical_coefficients'])
                        if 'state_response' in fit:
                            from evaluation.controllers.freeway_fd import configure_state_response
                            configure_state_response(cfg,{'freeway':{'state_response':{road:fit['state_response']}}})
                        if 'regional_physical_coefficients' in fit:apply_regional_coefficients(cfg,road,fit['regional_physical_coefficients'])
                        if 'vsl_fd_response' in fit:cfg.network.freeway_vsl_fd_response={road:copy.deepcopy(fit['vsl_fd_response'])}
                        if 'receiving_speed_response' in fit:cfg.network.freeway_receiving_speed_response={road:copy.deepcopy(fit['receiving_speed_response'])}
                        if fit.get('audit_effective'):
                            effective.append(dict(arm=u.ARMS[calls],road=road,rows=copy.deepcopy(cfg.network.freeway_segment_params[road]),
                                scalar={k:getattr(cfg.network,k) for k in fit.get('physical_coefficients',{})},
                                state_response=copy.deepcopy(getattr(cfg.network,'freeway_state_response',{})),
                                receiving=copy.deepcopy(getattr(cfg.network,'freeway_hadiuzzaman',{})),
                                vsl_fd_response=copy.deepcopy(getattr(cfg.network,'freeway_vsl_fd_response',{})),
                                receiving_speed_response=copy.deepcopy(getattr(cfg.network,'freeway_receiving_speed_response',{})),
                                port_response=copy.deepcopy(getattr(cfg.network,'freeway_port_response',{}))))
                    return cfg
                model._config=configuration
            from evaluation.controllers import freeway_fd
            response_function=freeway_fd.state_response_coefficients;used={}
            response_selector=freeway_fd.cell_state_response;cell_usage={}
            recovery_usage={};response_cell=None
            literature_function=freeway_fd.literature_vsl_parameters;literature_usage={}
            def observe_literature(spec,vf,critical,shape,command,maximum):
                value=literature_function(spec,vf,critical,shape,command,maximum)
                key=json.dumps([spec,vf,critical,shape,command,maximum],sort_keys=True)
                row=literature_usage.setdefault(key,dict(calls=0,spec=copy.deepcopy(spec),
                    base=[vf,critical,shape],command=command,maximum=maximum,effective=list(value)))
                row['calls']+=1;assert row['effective']==list(value)
                return value
            if fit is not None and 'vsl_fd_response' in fit:freeway_fd.literature_vsl_parameters=observe_literature
            def observe_cell_response(net,road,index):
                nonlocal response_cell
                response_cell=index if road=='FW_E' else None
                value=response_selector(net,road,index)
                if road=='FW_E':
                    spec=(getattr(net,'freeway_state_response',{}) or {}).get(road,{})
                    local={k:v for k,v in value.items() if k!='cell_overrides'}
                    entry=cell_usage.setdefault(str(index),dict(calls=0,override=str(index) in spec.get('cell_overrides',{}),response=copy.deepcopy(local)))
                    assert entry['response']==local
                    entry['calls']+=1
                return value
            def observe_response(spec,speed,desired,rho,downstream,critical,tau,nu):
                value=response_function(spec,speed,desired,rho,downstream,critical,tau,nu)
                if 'recovery_relaxation' in spec:
                    assert response_cell is not None
                    plain={k:v for k,v in spec.items() if k!='recovery_relaxation'}
                    before=response_function(plain,speed,desired,rho,downstream,critical,tau,nu)
                    gate=desired>speed and downstream<=rho and downstream<critical
                    ceiling=spec['recovery_relaxation'].get('speed_ceiling_kmh')
                    gate=gate and (ceiling is None or speed<ceiling)
                    if not gate:assert before==value
                    pressure_error=abs(value[1]/value[0]-before[1]/before[0])
                    assert pressure_error<1e-8
                    entry=recovery_usage.setdefault(str(response_cell),dict(calls=0,eligible=0,changed=0,
                        max_pressure_coefficient_error=0.,min_speed_kmh=speed,max_speed_kmh=speed,
                        mean_speed_sum_kmh=0.,relaxation_increment_sum=0.))
                    entry['calls']+=1;entry['eligible']+=gate;entry['changed']+=before!=value
                    entry['max_pressure_coefficient_error']=max(entry['max_pressure_coefficient_error'],pressure_error)
                    entry['min_speed_kmh']=min(entry['min_speed_kmh'],speed)
                    entry['max_speed_kmh']=max(entry['max_speed_kmh'],speed)
                    entry['mean_speed_sum_kmh']+=speed
                    if gate:entry['relaxation_increment_sum']+=(desired-speed)*(1/value[0]-1/before[0])/3600
                if spec.get('anticipation'):
                    key='downstream_ge_local' if downstream>=rho else 'downstream_lt_local'
                    if fit is not None and 'state_response' in fit:
                        key+='|'+str(value[0])+'|'+str(value[1])
                    row=used.setdefault(key,{'calls':0,'nu':value[1]});row['calls']+=1
                    assert row['nu']==value[1]
                return value
            if fit is not None and ('anticipation' in fit or 'state_response' in fit):freeway_fd.state_response_coefficients=observe_response
            if fit is not None and fit.get('state_response',{}).get('cell_overrides'):
                freeway_fd.cell_state_response=observe_cell_response
            oracle_spec=fit.get('diagnostic_desired_distribution') if fit is not None else None
            probe=contextlib.nullcontext(None)
            if oracle_spec is not None:
                assert oracle_spec.get('future_data') is True
                from distribution_response import oracle
                probe=oracle(oracle_spec,u.ARMS[calls])
            limits_observer=(u.trace_mainline_limits(include_cells=True)
                if fit is not None and fit.get('diagnostic_limits') is True else contextlib.nullcontext(None))
            try:
                with probe as oracle_audit,limits_observer as limits:
                    t=time.perf_counter();p=original(model,w,parameters);times.append(time.perf_counter()-t)
            finally:
                freeway_fd.state_response_coefficients=response_function
                freeway_fd.cell_state_response=response_selector
                freeway_fd.literature_vsl_parameters=literature_function
            if limits is not None:
                assert len(limits)==450 and all(row['step_s']==1 for row in limits)
                save_compressed(out/f'limits_{u.ARMS[calls]}.json',limits)
            if oracle_audit is not None:
                save(out/f'diagnostic_desired_{u.ARMS[calls]}.json',oracle_audit)
                p['diagnostics']['future_desired_distribution']=oracle_audit
            if used:save(out/f'anticipation_{u.ARMS[calls]}.json',used)
            if cell_usage:save(out/f'cell_response_{u.ARMS[calls]}.json',cell_usage)
            if recovery_usage:save(out/f'recovery_usage_{u.ARMS[calls]}.json',recovery_usage)
            if literature_usage:save(out/f'vsl_fd_usage_{u.ARMS[calls]}.json',list(literature_usage.values()))
            if fit is not None and fit.get('compress_predictions'):save_compressed(out/f'{mode}_{u.ARMS[calls]}.json',p)
            else:save(out/f'{mode}_{u.ARMS[calls]}.json',p)
            if refined:p=aggregate(p,parents,oldcells)
            calls+=1
            return p
        finally:
            model._config=original_config
            for k,v in snapshot.items():setattr(model,k,v)
    u.e.simulate=simulate
    original_save=u.e.save
    def compact_save(path,value):
        if path.name.startswith(('prediction_','local_')):save_compressed(path,value)
        else:original_save(path,value)
    if fit is not None and fit.get('compress_predictions'):u.e.save=compact_save
    u.ARMS=selected_arms
    try:
        with (out/f'{mode}.log').open('x',encoding='utf-8') as stream,contextlib.redirect_stdout(stream):
            u.run_probe(lateral_access=True,prefer_receiving=True,trace_limits=False,
                network_exit_intent=True,current_exit_intent=True,branch_partition='on',branch_exchange='off',
                partition_context='on',transport_step=5 if mode=='reference5' else 1,
                nc_only=fit is not None and fit['nc_only'],
                output_name='segment_resolution_20260921_'+(mode if fit is None else 'cal_'+fit['name']),replay_context=replay_context)
    finally:
        u.e.simulate=original;u.e.window=original_window;u.e.save=original_save;u.ARMS=original_arms
    assert calls==(1 if fit is not None and fit['nc_only'] else len(selected_arms))
    if fit is not None and fit.get('control_response_fit'):
        protocol_path=K/('segment_resolution_20260921_cal_'+fit['name'])/'protocol.json'
        protocol=load(protocol_path)
        protocol.update(no_gain_fitting=False,control_response_fit=fit['control_response_fit'])
        save(protocol_path,protocol)
    if fit is not None and fit.get('diagnostic_desired_distribution'):
        directory=K/('segment_resolution_20260921_cal_'+fit['name'])
        for filename in ('protocol.json','result.json'):
            value=load(directory/filename)
            value.update(future_traffic_inputs=True,diagnostic_only=True,qualified=False,
                diagnostic_desired_distribution=fit['diagnostic_desired_distribution'])
            save(directory/filename,value)
    if vsl_policy is not None:
        directory=K/('segment_resolution_20260921_cal_'+fit['name'])
        for filename in ('protocol.json','result.json'):
            value=load(directory/filename);value['diagnostic_vsl_policy']=vsl_policy
            save(directory/filename,value)
    if mode=='reference5':
        for arm in u.ARMS:assert load(B/f'{mode}_{arm}.json')==load(K/f'runtime5s_20260921_step5/prediction_{arm}.json'),arm
    save(out/f'{mode}_receipt.json',dict(completed=True,forecasts=calls,seconds=times,production_adopted=False,
        future_inputs=fit is not None and bool(fit.get('diagnostic_desired_distribution')),fit=fit,
        runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    if effective:save(out/'effective_config.json',effective)
    print(mode,'complete',times,flush=True)

if __name__=='__main__':main()
