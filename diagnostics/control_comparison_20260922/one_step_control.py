"""One observed congested state, three frozen plants, small RM/VSL decision."""
from pathlib import Path
import copy, csv, hashlib, importlib.util, itertools, json, statistics, sys, time
import xml.etree.ElementTree as ET
import probe_model_choice as base

ROOT, HERE, CAL, BASE, Q = base.ROOT, base.HERE, base.CAL, base.BASE, base.Q
OUT=HERE/'one_step_control'
CUTOFF=2700.1


def prepare():
    path=ROOT/'diagnostics/offramp_dynamic_20260922/study.py'
    spec=importlib.util.spec_from_file_location('port_review',path)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    data,correction=helper.corrected_data()
    policy=base.load(Q/'rules/prepared_rm/rule_policy.json')
    tree=ET.parse(Q/'rules/prepared_rm/network/baseline.inpx')
    heads={}
    for mid,m in policy['meters'].items():
        rows=tree.findall(f"./signalHeads/signalHead[@sg='{m['sc']} 1']")
        assert rows and all(int(x.get('lane').split()[0])==m['connector'] for x in rows)
        heads[mid]=min(float(x.get('pos')) for x in rows)
    lengths={str(b['connector']):b['length_m'] for b in data.definitions.values() if b['kind'] in ('ramp','offramp')}
    samples={c:[] for c in lengths}
    for row in helper.table(data.folder/'port_events.csv'):
        c=row['connector']
        if c in samples and row['kind']=='departure' and float(row['time_s'])<=900 and row['residence_s'] and float(row['residence_s'])>0:
            samples[c].append(lengths[c]*3.6/float(row['residence_s']))
    assert all(samples.values())
    speed={c:statistics.median(v) for c,v in samples.items()}
    profile={'occupancy_lane_loss':True,'travel_speed_kmh':speed,'entry_capacity_mode':'storage_and_proxy'}
    bindings=base.load(HERE/'model_choice_probe/summary.json')['bindings']
    for c,b in zip(data.geometry['cells'],bindings):
        assert all(c[k]==b[k] for k in ('road','cell','start_m','end_m'))
    return data,policy,heads,speed,profile,bindings


def make_window(data,model,policy,heads,speed,profile):
    w=base.build_window(data,CUTOFF,'history_forecast',profile,model_step_sec=1)
    w['ramp_dynamics']={'schema':'physical-ramp-boundary/v1','local_step_sec':1,'meter_cycle_sec':10,'ramps':{}}
    ends=[round(CUTOFF-150+i,6) for i in range(30,151,30)]
    arrivals={};inputs=[]
    for mid,r in model.ramps.items():
        c=str(r['connector']); cohorts=data.port_cohorts[str(CUTOFF)][c]
        recent=[data.ports[t,c] for t in ends]
        assert all(float(x['unresolved_absences_veh'])==0 for x in recent)
        arrivals[mid]=sum(float(x['arrivals_veh']) for x in recent)*24
        w['ramp_dynamics']['ramps'][mid]=dict(connector_id=c,length_m=r['length_m'],head_position_m=heads[mid],
            lanes=r['lanes'],spacing_m=model.base.network.urban_avg_vehicle_length_m,
            travel_speed_kmh=speed[c],time_sec=CUTOFF,initial_cohorts=cohorts,initial_backlog_veh=0.)
        cfg=model._config(r['road'],{})
        inputs.append(dict(ramp=mid,road=r['road'],initial_connector_veh=len(cohorts),
            initial_before_head_veh=sum(v[0]<=heads[mid] for v in cohorts),arrival_vph=arrivals[mid],
            observed_merge_vph=sum(float(x['departures_veh']) for x in recent)*24,
            g8_nominal_service_vph=policy['meters'][mid]['table']['8'],
            original_merge_capacity_vph=cfg.network.ramp_capacity_veh_h[mid],travel_speed_kmh=speed[c]))
    for s in w['boundary_steps']:s['ramp_arrival_vph']=dict(arrivals)
    return w,inputs


def predict(model,w,params,policy,bindings,road,rm,vsl):
    steps=copy.deepcopy(w['boundary_steps'])
    for s in steps:
        k=min(2,int((s['window_start_s']-CUTOFF+1e-7)//150))
        s['ramp_head_service']={}
        for mid in model.ramps:
            g=10-2*(k+1) if mid==rm else None
            service=policy['meters'][mid]['table'][str(10 if g is None else g)]/360
            s['ramp_head_service'][mid]=dict(service_veh=service,mode='OFF' if g is None else 'GREEN',green_sec=g)
        s['vsl_commands']={f"{b['road']}__seg{b['cell']}":120-20*(k+1) if b['zone']==vsl and vsl is not None else 120
                           for b in bindings}
    heads={r:list(range(len([c for c in bindings if c['road']==r]))) for r in model.roads}
    pred=model.rollout(w['initial_cells'],steps,params,w['initial_origin_queue'],roads=[road],
        port_dynamics=w['port_dynamics'],ramp_dynamics=w['ramp_dynamics'],vsl_zone_heads=heads,residence_audit=True)
    d=pred['diagnostics']['roads'][0]
    assert d['density_projection_count']==d['jam_density_exceedance_count']==d['negative_density_count']==0
    assert d['continuity_residual_max_veh']<1e-6
    ramps={};outside_wait=0.;checks=0
    for x in pred['ramps']:
        assert abs(x['conservation_residual_veh'])<1e-7
        assert x['accepted_merge_veh']<=x['receiving_budget_veh']+1e-7
        for local in x['local_receipts']:
            assert abs(local['conservation_residual_veh'])<1e-7
            checks+=1
        outside_wait+=x['start']['outside_component_backlog_veh']*x['duration_sec']/3600
        s=ramps.setdefault(x['ramp'],dict(merges150=0.,merges450=0.,head150=0.,head450=0.,ramp_TTT=0.,backlog_end=0.,stock_end=0.))
        if x['end_sec']<=CUTOFF+150+1e-7:
            s['merges150']+=x['accepted_merge_veh'];s['head150']+=x['head_service_veh']
        s['merges450']+=x['accepted_merge_veh'];s['head450']+=x['head_service_veh']
        s['ramp_TTT']+=x['connector_ttt_veh_h'];s['backlog_end']=x['end']['outside_component_backlog_veh']
        s['stock_end']=x['end']['connector_veh']
    assert all(abs(p['conservation_residual_veh'])<1e-7 for p in pred['ports'])
    # Newly rejected admitted-interface requests; pre-existing outside queue is
    # not represented by this component. Use the actual1s step, never a fixed10.
    backlog=0.;source_wait=0.
    for i in range(15):
        a=round(CUTOFF+30*i,6);b=round(a+30,6)
        requested=sum(s['source_demand_vph'][road]/3600 for s in steps if a-1e-7<=s['window_start_s']<b-1e-7)
        admitted=sum(f['source_admissions'] for f in pred['flows'] if abs(f['window_end_s']-b)<1e-7)
        after=max(0.,backlog+requested-admitted);source_wait+=(backlog+after)*30/7200;backlog=after
    cost=dict(mainline=d['model_residence_10s_veh_h'],on_ramps=d['ramp_connector_residence_local_1s_veh_h'],
        off_ramps=d['off_connector_residence_event_veh_h'],upstream_ramp_wait=outside_wait,source_wait=source_wait)
    assert abs(cost['on_ramps']-sum(s['ramp_TTT'] for s in ramps.values()))<1e-8
    return dict(road=road,rm=rm,vsl=vsl,cost=cost,total=sum(cost.values()),ramps=ramps,local_checks=checks,
        vsl_binding_cell_seconds=sum(x['desired_speed_binding_samples'] for x in d['vsl_binding_audit']['cells']),
        mainline_conservation_max=d['continuity_residual_max_veh'],terminal_stock=d['final_n_veh'])


def main():
    OUT.mkdir(exist_ok=True); started=time.perf_counter()
    data,policy,heads,speed,profile,bindings=prepare()
    parameters=base.load(BASE/'family_parameters.json'); results=[]; decisions=[]; pins={}
    base.save(OUT/'initial_state.json',dict(cutoff_s=CUTOFF,cells=data.cells[CUTOFF],head_positions=heads,
        travel_speed_kmh=speed,travel_speed_training_end_s=900,
        off_policy='Existing conserved storage+travel; retain original inflow proxy cap and past150s drainage proxy',
        control_horizon_s=450,first_move_s=150,green_sequence=[8,6,4],vsl_sequence=[100,80,60]))
    for family in ('boundary','hadi','wang'):
        cfg=base.load(BASE/(family+'_config.json'))
        # Existing optional off storage hook, common to all candidates, so the
        # objective includes off-connector waiting instead of deleting it.
        cfg['freeway']['physical_offramp_interval_service']=True
        cfg_path=OUT/(family+'_config.json');base.save(cfg_path,cfg)
        model=base.load_base_model(data.geometry,cfg_path)
        w,inputs=make_window(data,model,policy,heads,speed,profile)
        if family=='boundary':base.table(OUT/'ramp_inputs.csv',inputs)
        cache={};family_started=time.perf_counter()
        for road in model.roads:
            rm_options=[None]+[m for m,r in model.ramps.items() if r['road']==road]
            vsl_options=[None]+[z for z in policy['zone_dsds'] if z.startswith(road)]
            for rm,vsl in itertools.product(rm_options,vsl_options):
                cache[road,rm,vsl]=predict(model,w,parameters[family],policy,bindings,road,rm,vsl)
            print(family,road,'25 local candidate forecasts complete',flush=True)
        family_rows=[]
        for rm,vsl in itertools.product([None]+list(model.ramps),[None]+list(policy['zone_dsds'])):
            parts=[cache[road,rm if rm and model.ramps[rm]['road']==road else None,
                         vsl if vsl and vsl.startswith(road) else None] for road in model.roads]
            row=dict(family=family,rm=rm,vsl=vsl,total=sum(p['total'] for p in parts),
                cost={k:sum(p['cost'][k] for p in parts) for k in parts[0]['cost']},
                ramps={mid:s for p in parts for mid,s in p['ramps'].items()},
                binding_cell_seconds=sum(p['vsl_binding_cell_seconds'] for p in parts))
            family_rows.append(row)
        hold=family_rows[0]
        for r in family_rows:
            r['delta_total']=r['total']-hold['total']
            r['delta_cost']={k:r['cost'][k]-hold['cost'][k] for k in r['cost']}
            r['delta_merges150']=sum(s['merges150']-hold['ramps'][m]['merges150'] for m,s in r['ramps'].items())
            r['delta_merges450']=sum(s['merges450']-hold['ramps'][m]['merges450'] for m,s in r['ramps'].items())
        for arm in ('rm','vsl','both'):
            eligible=[r for r in family_rows if (arm!='rm' or r['vsl'] is None) and (arm!='vsl' or r['rm'] is None)]
            chosen=min(eligible,key=lambda r:r['total'])
            decisions.append(dict(family=family,arm=arm,rm=chosen['rm'],vsl=chosen['vsl'],
                first_green_sec=8 if chosen['rm'] else None,first_vsl_kph=100 if chosen['vsl'] else None,
                delta_total=chosen['delta_total'],improvement_pct=-chosen['delta_total']/hold['total']*100,
                delta_cost=chosen['delta_cost'],delta_merges150=chosen['delta_merges150'],
                delta_merges450=chosen['delta_merges450'],candidates=len(eligible)))
        base.save(OUT/(family+'_roads.json'),list(cache.values()))
        base.save(OUT/(family+'_candidates.json'),family_rows)
        pins.update(model.provenance['model_files']);pins[str(cfg_path)]=base.sha256(cfg_path)
        results+=family_rows
        print(family,'selections',json.dumps(decisions[-3:]),'seconds',round(time.perf_counter()-family_started,2),flush=True)
    for p in (Path(__file__),CAL/'canonical_harness.py',CAL/'boundary_factory.py',BASE/'family_parameters.json',
              ROOT/'evaluation/controllers/physical_ramp_boundary.py'):
        pins[str(p)]=base.sha256(p)
    base.save(OUT/'summary.json',dict(cutoff_s=CUTOFF,decisions=decisions,road_forecasts=150,global_candidates=243,
        candidate_scope='One of8 meters and/or one of8 VSL zones; exhaustive81 in this restricted set; two freeway directions independent.',
        controller='Small centralized offline selection by component vehicle-hours; NOT full GNE, no NP/NUF or full urban Omega objective.',
        timing='Observe2700.1; first command at2700.1, choose first150s of450s plan. Fractional native phase retained.',
        objective='Mainline +8on/off connectors + incremental upstream ramp/source waiting, unit vehicle-hour weights.',
        baseline='Same endogenous ramp/off models, native meters OFF and VSL120. No model reset within450s.',
        limitations=['Ramp demand is past150s connector arrivals, not a coupled upstream destination/urban forecast.',
            'Initial upstream ramp backlog outside connector is unobserved, set0 for this incremental component comparison.',
            'Off entry/drainage use past-flow proxies; auxiliary dynamics newly connected for all three, not recalibrated or production adopted.',
            'Signal service uses existing nominal g-to-service curve; travel speed pre900 complete-traversal median.',
            'No actual VISSIM branch rerun; model selection is not verified native benefit.',
            'Single-region VSL spatial projection does not model individual vehicles retaining DSD desired speed.'],
        elapsed_sec=time.perf_counter()-started,pins=pins))
    base.table(OUT/'decisions.csv',[{k:(json.dumps(v) if isinstance(v,dict) else v) for k,v in d.items()} for d in decisions])
    print('COMPLETE',round(time.perf_counter()-started,2),flush=True)


if __name__=='__main__':main()
