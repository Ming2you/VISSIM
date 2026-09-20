"""Inspect existing partial-FIFO decisions without changing a simulated value."""
from pathlib import Path
import sys,copy,hashlib,json,csv,statistics,argparse,math
from contextlib import nullcontext
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,MODEL,CASES
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups

HERE=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--oracle',action='store_true')
    parser.add_argument('--branch-position-audit',action='store_true')
    parser.add_argument('--branch-flux-audit',action='store_true')
    parser.add_argument('--flowing-equilibrium',action='store_true');args=parser.parse_args()
    if args.branch_flux_audit:
        if args.oracle or args.flowing_equilibrium or args.branch_position_audit:parser.error('Flux audit only')
        return branch_flux_audit()
    if args.branch_position_audit:
        if args.oracle or args.flowing_equilibrium:parser.error('Position audit does not change model transitions')
        return branch_position_audit()
    if args.flowing_equilibrium and not args.oracle:parser.error('--flowing-equilibrium requires --oracle')
    out=HERE/('lane_blocking_combined_v1' if args.flowing_equilibrium else 'lane_blocking_oracle_v2' if args.oracle else 'lane_blocking_model_audit_v3');out.mkdir(exist_ok=False)
    if args.flowing_equilibrium:
        from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.lane_fd_class_check import ordinary_equilibrium
    config=HERE/'port_origin_split_v1/config.json'
    params=e.load(HERE/'port_travel_fit_v1/selected_parameters.json')['parameters']
    profile=e.load(MODEL/'port_profile.json')
    target=e.ROOT/'evaluation/controllers/physical_lane_groups.py'
    code=target.read_text(encoding='utf-8').splitlines()
    hit=[i+1 for i,line in enumerate(code) if line.strip()=='outgoing=[[0.]*len(ns) for ns in self.n]']
    assert len(hit)==1;hit=hit[0]
    results={};costs={};scores={};pins={str(target.relative_to(e.ROOT)):hashlib.sha256(target.read_bytes()).hexdigest()};exact=0
    for seed,folder,bank,start in CASES:
        if seed not in (23,33):continue
        data=e.ObservationData(folder)
        lane=e.load(H/f'lane_group_response_20260919/observations_v1/s{seed}.json')
        origin=e.load(HERE/f'port_positions_v1/s{seed}.json')
        protocol=e.load(bank/'protocol.json')
        for arm in ('none','vsl'):
            model=e.load_base_model(data.geometry,config);original=model._config
            def configured(road,override):
                value=original(road,override)
                if road=='FW_E':value.network.terminal_zero_gradient=True
                return value
            model._config=configured
            seq={'vsl':[]} if arm=='none' else protocol['candidate_bank'][arm]
            def command(t):
                i=int((t-start)//150)
                return ({}, {d:seq['vsl'][i] for d in protocol['dsd_ids']} if seq['vsl'] else {})
            w=e.window(data,model,start,'history_forecast',profile,command,port_origin_counts=origin['counts'])
            w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(start)],
                'initial_ramp_origin':origin['counts'][str(start)],'initial_off_eligible':origin['eligible_before_off'][str(start)]}}
            reference=e.load(HERE/f'terminal_probe_v1/prediction_s{seed}_open_outlet_{arm}.json')
            advance=PhysicalLaneGroups.advance;active=False
            if args.oracle:
                observed_masks=e.rows(HERE/f'lane_blocking_audit_v1/s{seed}_{arm}_lanes.csv')
                mask={(int(r['time_s']),r['connector'],int(r['mainline_lane'])-1):r['connected_queue_candidate']=='True'
                      for r in observed_masks if r['off_lane']!='0'}
                def measured_gate(self,state,control,demand,cfg,**kwargs):
                    # Diagnostic only: future measured blocking fraction, not a
                    # fitted capacity or an operationally available observation.
                    if not self.initialized_destinations:
                        assert self.port_travel is not None
                        initial=[[n-sum(v[g] for r,v in self.ramp_origin.items() if self.spec['ramp_access'][r]['cell']==i)
                                  for g,n in enumerate(ns)] for i,ns in enumerate(self.n)]
                        self._label(initial,{o:cfg.network.off_ramp_split_ratio[o] for o in self.off},self.initial_off_eligible)
                        self.initialized_destinations=True
                    if active:
                        limits=copy.deepcopy(kwargs.get('offramp_group_capacity_veh_h') or {})
                        t=int(state.time_sec)
                        assert self.sec==int(self.sec) and state.time_sec==t
                        for o,p in self.spec['off_access'].items():
                            i=p['cell'];availability=[1-sum(mask.get((sec,o,g),False) for sec in range(t,t+int(self.sec)))/self.sec
                                                     for g in range(len(self.n[i]))]
                            if min(availability)==1:continue
                            cap=limits.get(o,[kwargs['offramp_capacity_veh_h'][o]]*len(availability))
                            for g,fraction in enumerate(availability):
                                if fraction==1:continue
                                n=self.off[o][g];request=min(n,n*self.v[i][g]*self.dt/self.port_travel['off_distance_km'][o])
                                cap[g]=min(cap[g],request*fraction/self.dt)
                            limits[o]=cap
                        kwargs['offramp_group_capacity_veh_h']=limits
                    return advance(self,state,control,demand,cfg,**kwargs)
                PhysicalLaneGroups.advance=measured_gate
                try:
                    plain=e.simulate(model,w,params)
                    assert json.loads(json.dumps(plain))==reference;exact+=1
                except BaseException:
                    PhysicalLaneGroups.advance=advance
                    raise
                active=True
            trace=[];seen_intervals=set()
            def on_line(frame,event,arg):
                if event=='line' and frame.f_lineno==hit:
                    v=frame.f_locals
                    if v['road']!='FW_E':return on_line
                    # Python3.12 emits repeated events on inlined comprehensions.
                    if v['state'].time_sec in seen_intervals:return on_line
                    seen_intervals.add(v['state'].time_sec)
                    for o,p in v['self'].spec['off_access'].items():
                        i=p['cell']
                        trace.append(dict(start_s=v['state'].time_sec,cell=i,connector=o,
                            requested=list(v['offreq'][o]),accepted=list(v['offsent'][o]),
                            fifo=list(v['fifo'][i]),total_off_offer_veh=v['offramp_capacity_veh_h'][o]*v['dt'],
                            group_offer_vph=copy.deepcopy((v['offramp_group_capacity_veh_h'] or {}).get(o)),
                            group_n=list(v['before'][i]),group_v=list(v['oldv'][i]),
                            branch_n=list(v['self'].off[o])))
                return on_line
            def tracer(frame,event,arg):
                if event=='call' and frame.f_code.co_name=='advance' and Path(frame.f_code.co_filename).resolve()==target:
                    return on_line
            previous=sys.gettrace();sys.settrace(tracer)
            try:
                with ordinary_equilibrium(True) if args.flowing_equilibrium else nullcontext():
                    prediction=e.simulate(model,w,params)
            finally:
                sys.settrace(previous)
                PhysicalLaneGroups.advance=advance
            assert len(trace)==180
            if not args.oracle:
                assert json.loads(json.dumps(prediction))==reference;exact+=1
            else:
                for field in ['cells','flows']:
                    assert [r for r in prediction[field] if r['road']=='FW_W']==[r for r in reference[field] if r['road']=='FW_W']
                for r in prediction['diagnostics']['roads']:
                    assert r['continuity_residual_max_veh']<1e-7 and r['negative_density_count']==r['jam_density_exceedance_count']==0
                e.save(out/f'prediction_s{seed}_{arm}.json',prediction)
            costs[f'{seed}_{arm}']=parts(prediction)
            scores[f'{seed}_{arm}']=e.score_rollout(data,start,prediction,'FW_E')
            observed=e.rows(HERE/f'lane_blocking_audit_v1/s{seed}_{arm}_groups.csv')
            actual={(int(r['time_s']),int(r['cell']),int(r['group'])):r for r in observed}
            summary={}
            for o,p in lane['geometry']['off_access'].items():
                selected=[r for r in trace if r['connector']==o];summary[o]={}
                for g in range(3):
                    ns=[r['group_n'][g] for r in selected];vs=[r['group_v'][g] for r in selected]
                    native=[actual[int(r['start_s']),p['cell'],g] for r in selected]
                    summary[o][str(g)]=dict(steps=len(selected),restricted_steps=sum(r['fifo'][g]<1-1e-9 for r in selected),
                        zero_service_steps=sum(r['fifo'][g]<1e-9 for r in selected),mean_fifo=statistics.mean(r['fifo'][g] for r in selected),
                        predicted_mean_n=statistics.mean(ns),native_mean_n=statistics.mean(int(r['n']) for r in native),
                        predicted_vehicle_weighted_v=sum(n*v for n,v in zip(ns,vs))/sum(ns),
                        native_vehicle_weighted_v=sum(int(r['n'])*float(r['v'] or 0) for r in native)/sum(int(r['n']) for r in native),
                        predicted_off_passes=sum(r['accepted'][g] for r in selected))
            e.save(out/f's{seed}_{arm}_trace.json',trace)
            results[f'{seed}_{arm}']=summary
            print('EXACT_REPLAY',seed,arm,'10643',summary['10643'],flush=True)
    assert hashlib.sha256(target.read_bytes()).hexdigest()==pins[str(target.relative_to(e.ROOT))]
    deltas={str(seed):{k:costs[f'{seed}_vsl'][k]-costs[f'{seed}_none'][k] for k in costs[f'{seed}_none']} for seed in [23,33]}
    for row in deltas.values():row['total']=sum(row.values())
    e.save(out/'result.json',dict(results=results,full_prediction_json_exact=exact,core_pins_unchanged=pins,
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),model_changed=False,new_native_runs=0,
        diagnostic_future_mask=args.oracle,flowing_equilibrium_ablation=args.flowing_equilibrium,
        equilibrium_ablation_source_sha256=hashlib.sha256((HERE/'lane_fd_class_check.py').read_bytes()).hexdigest() if args.flowing_equilibrium else None,
        production_adopted=False,costs=costs,vsl_deltas=deltas,state_scores=scores,
        meaning='Existing partial FIFO, optionally supplied with future native connected-queue duty fractions as per-lane off-ramp receiving restrictions. No vehicle is removed. The oracle is not a causal prediction.',
        scope='Open-outlet diagnostic lane-group candidate, not the established lumped production model. Native and predicted speeds here refer to the same whole physical cell at10s starts, not the separate100m approach window.'))
    print('VSL_DELTAS',deltas,flush=True)


def branch_position_audit():
    """Separate the current pre/post-diverge stock before assessing FIFO.

    Native future frames validate departures only; they do not set a model
    state, service rate, or speed. Whole-cell outflow is compared with a
    subset of observed departures (already downstream at the interval start).
    """
    import time
    from collections import Counter
    from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.route_access_observer import geometry as route_geometry
    start,end=2400,2850;begun=time.perf_counter()
    out=HERE/'branch_position_audit_v1'
    assert (out/'source_before.json').is_file() and not (out/'result.json').exists()
    current_path=HERE/'current_mainline_route_v1/result.json';current=e.load(current_path)
    native=HERE/'route_state_native_v1'
    net=native/'none_s23/source/baseline.inpx';routes,_=route_geometry(net)
    geompath=H/'controller_response_s23_v1/none/geometry.json';geom=e.load(geompath)
    cell=next(c for c in geom['cells'] if c['road']=='FW_E' and c['cell']==8)
    port=next(p for p in geom['boundaries'] if p['connector']==10643)
    next_port=next(p for p in geom['boundaries'] if p['connector']==10682)
    a,b,branch=cell['start_m'],cell['end_m'],port['chain_pos_m']
    assert a<branch<b and cell['physical_pieces']==[dict(link=2,length_m=b-a,lanes=4)]
    assert next_port['from_cell']==9 and next_port['chain_pos_m']>b and next_port['from_link']==2
    shift=branch-port['from_pos_m'];assert abs(shift-2734.527)<1e-7
    runfolder=HERE/'urban_route_transport_space_v1_network_intent_current_limits'
    pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
          for p in (Path(__file__),current_path,net,geompath,runfolder/'protocol.json')}
    result={}
    def row(p):
        def number(value):return int(value) if value else None
        link,lane,pos,v=int(p[2]),int(p[3]),float(p[4]),float(p[6])
        rd,rn,kind=number(p[11]),number(p[12]),p[13].decode('ascii')
        path=routes.get((rd,rn)) if kind.lower()=='static' else None
        x=pos+shift if link==2 else None
        return dict(vehicle=int(p[1]),link=link,lane=lane,chain_position_m=x,
                    speed_kmh=v,length_m=float(p[10]),route_decision=rd,route_number=rn,
                    off10643_intent=(10643 in path) if path and x is not None and x<branch else None)
    for arm in ('none','vsl'):
        path=native/f'{arm}_s23/run_retry1/vissim_eval/baseline_001.fzp'
        verified=e.load(native/f'{arm}_s23/analysis/result.json');before=path.stat()
        frames={};digest=hashlib.sha256();prefix=hashlib.sha256();prefix_n=0;read_n=0
        with path.open('rb') as stream:
            for line in stream:
                digest.update(line)
                if not line[:1].isdigit():continue
                # Preserve blank final columns; their absence is meaningful.
                p=line.rstrip(b'\r\n').split(b';')
                if len(p)==21 and not p[-1]:p.pop()
                assert len(p)==20
                t=int(float(p[0]));read_n+=1
                if t<=start:prefix.update(b';'.join(p)+b'\n');prefix_n+=1
                if not start<=t<=end:continue
                frame=frames.setdefault(t,{})
                if int(p[2]) not in (2,10643,10682):continue
                v=row(p);frame[v['vehicle']]=v
        assert set(frames)==set(range(start,end+1))
        after=path.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
        assert digest.hexdigest()==verified['new_fzp_sha256']
        assert prefix.hexdigest()==current['verified_prefix_sha256'] and prefix_n==current['verified_prefix_rows']
        observed=[v for v in frames[start].values() if v['link']==2 and a<=v['chain_position_m']<b]
        original={r['vehicle']:r for r in current['current_vehicles'] if r['cell']==8}
        assert set(original)=={v['vehicle'] for v in observed}
        for v in observed:
            r=original[v['vehicle']]
            for key in ('lane','speed_kmh','length_m','route_decision','route_number','off10643_intent'):
                assert r[key]==v[key],(key,r,v)
            assert abs(r['chain_position_m']-v['chain_position_m'])<1e-7
        limits=e.load(runfolder/f'limits_{arm}.json');windows=[]
        for t in range(start,end,10):
            f=frames[t];lanes=[]
            model=next(x['ports']['10643'] for x in limits if x['time_s']==t)
            for lane in (1,2,3,4):
                inside=sorted((v for v in f.values() if v['link']==2 and v['lane']==lane and a<=v['chain_position_m']<b),key=lambda v:-v['chain_position_m'])
                pre=[v for v in inside if v['chain_position_m']<branch];post=[v for v in inside if v['chain_position_m']>=branch]
                exits=[]
                for v in post:
                    last=v;changed=False
                    for s in range(t+1,t+11):
                        nxt=frames[s].get(v['vehicle']);assert nxt is not None,('Downstream vehicle disappeared',arm,s,v)
                        assert nxt['link']==10682 or (nxt['link']==2 and nxt['chain_position_m']>=branch),('Downstream vehicle returned to exit',arm,s,v,nxt)
                        if nxt['link']==10682:
                            # The next diverge is10.29m beyond this cell. Both
                            # boundaries can be crossed between1s snapshots.
                            exits.append(dict(vehicle=v['vehicle'],time_s=s,changed_lane=changed,exit_lane=last['lane'],next_connector=10682));break
                        changed=changed or nxt['lane']!=last['lane'];last=nxt
                        if nxt['chain_position_m']>=b:
                            exits.append(dict(vehicle=v['vehicle'],time_s=s,changed_lane=changed,exit_lane=nxt['lane']));break
                def mean(xs):return statistics.mean(v['speed_kmh'] for v in xs) if xs else None
                g=min(lane-1,2)
                lanes.append(dict(lane=lane,pre_n=len(pre),post_n=len(post),pre_mean_speed_kmh=mean(pre),post_mean_speed_kmh=mean(post),
                    pre_off=sum(v['off10643_intent'] is True for v in pre),pre_unknown=sum(v['off10643_intent'] is None for v in pre),
                    initial_pre_head=pre[0] if pre else None,post_departures_next10s=exits,
                    whole_group_model_out_veh=model['mainline_out_veh'][g],model_fifo=model['fifo'][g],
                    model_group_shared=(lane>2)))
            windows.append(dict(time_s=t,lanes=lanes))
        blocked=[r['lanes'][1] for r in windows if r['lanes'][1]['model_fifo']<1e-9]
        # At later cuts model/native states have diverged. Only the first
        # interval is a matched-initial-state flow counterexample.
        result[arm]=dict(initial_lanes=windows[0]['lanes'],windows=windows,
            zero_model_fifo_windows=len(blocked),downstream_initial_cohort_exits_in_zero_fifo_windows=sum(len(r['post_departures_next10s']) for r in blocked),
            caveat='Rolling cohort exits are nonoverlapping events, but cuts after2400 are retrospective diagnostics with differing model/native states.',
            source=dict(path=str(path.relative_to(e.ROOT)),full_sha256=digest.hexdigest(),data_rows=read_n,bytes=before.st_size,mtime_ns=before.st_mtime_ns),
            prefix_sha256=prefix.hexdigest(),prefix_rows=prefix_n)
        print(arm,'initial_lane2',windows[0]['lanes'][1],flush=True)
    assert result['none']['initial_lanes']==result['vsl']['initial_lanes']
    e.save(out/'result.json',dict(arms=result,source_pins=pins,information_cutoff_s=start,
        future_observations='Validation departures only; no forecast performed or altered',
        geometry=dict(cell=8,start_m=a,end_m=b,branch_m=branch),native_new_runs=0,
        diagnosis='A blocked interior diverge applies partial FIFO to the entire canonical cell, including vehicles already past the branch.',
        production_adopted=False,qualified=False,elapsed_s=time.perf_counter()-begun))


def branch_flux_audit():
    """Matched spatial conservation, with past-only exchange-rate estimates."""
    import time
    from collections import Counter
    begin,cutoff,end=2250,2400,2850;started=time.perf_counter()
    out=HERE/'branch_flux_audit_v1';assert out.is_dir() and not (out/'result.json').exists()
    geom=e.load(H/'controller_response_s23_v1/none/geometry.json')
    cell=next(c for c in geom['cells'] if c['road']=='FW_E' and c['cell']==8)
    branch=next(p for p in geom['boundaries'] if p['connector']==10643)
    a,b,m=cell['start_m'],cell['end_m'],branch['chain_pos_m'];shift=m-branch['from_pos_m']
    keys=[(s,g) for s in ('pre','post') for g in range(3)]
    def place(v):
        if v is None or v[0]!=2 or not a<=v[2]<b:return None
        return ('pre' if v[2]<m else 'post',v[1])
    def blank():return {s:{g:Counter() for g in range(3)} for s in ('pre','post')}
    sources={};result={};histories={}
    for arm in ('none','vsl'):
        folder=HERE/f'route_state_native_v1/{arm}_s23';path=folder/'run_retry1/vissim_eval/baseline_001.fzp'
        validation=e.load(folder/'analysis/result.json');before=path.stat();digest=hashlib.sha256()
        cache_path=out/f'native_{arm}.json';cached=e.load(cache_path) if cache_path.exists() else None
        if cached:
            assert (before.st_size,before.st_mtime_ns)==(cached['source']['bytes'],cached['source']['mtime_ns'])
            assert cached['source']['sha256']==validation['new_fzp_sha256'] and cached['checks']==3600
        previous={};frame={};last=None;rows=[];checks=ambiguous=skipped=0;exposures=Counter();exchanges=Counter();alternative=Counter()
        def process(t,current):
            nonlocal previous,checks,ambiguous,skipped
            count=Counter(place(v) for v in current.values() if place(v) is not None)
            terms=blank();switches=[];amb=0;skip=0
            if previous:
                for vid in set(previous)|set(current):
                    old=previous.get(vid);new=current.get(vid);p,q=place(old),place(new)
                    if p is None and q is None:
                        if old and new and old[0]==10639 and new[0]==2 and new[2]>=b:
                            g=new[1];terms['post'][g]['merge']+=1;terms['post'][g]['out']+=1;skip+=1
                        continue
                    if p is None:
                        assert old is not None,('Unobserved entry',arm,t,vid,new)
                        if old[0]==2 and old[2]<a and q[0]=='pre':terms['pre'][q[1]]['in']+=1
                        elif old[0]==10639 and q[0]=='post':terms['post'][q[1]]['merge']+=1
                        else:raise AssertionError(('Unexpected spatial entry',arm,t,vid,old,new))
                    elif q is None:
                        assert new is not None,('Unexplained disappearance',arm,t,vid,old)
                        if p[0]=='pre' and new[0]==10643:terms['pre'][p[1]]['off']+=1
                        elif p[0]=='post' and ((new[0]==2 and new[2]>=b) or new[0]==10682):terms['post'][p[1]]['out']+=1
                        else:raise AssertionError(('Unexpected spatial exit',arm,t,vid,old,new))
                    else:
                        if p[1]!=q[1]:
                            # When both side and lane change in1s, order is
                            # unresolved. Use old-side exchange first and retain
                            # the new-side alternative for the past estimate.
                            terms[p[0]][p[1]]['lateral']-=1;terms[p[0]][q[1]]['lateral']+=1
                            switches.append((p[0],q[0],p[1],q[1]));amb+=int(p[0]!=q[0])
                        if p[0]!=q[0]:
                            assert p[0]=='pre' and q[0]=='post',('Reverse movement',arm,t,vid)
                            terms['pre'][q[1]]['cross']+=1;terms['post'][q[1]]['cross']+=1
                old_count=rows[-1]['counts']
                for s,g in keys:
                    c=terms[s][g]
                    delta=(c['in']-c['cross']-c['off']+c['lateral']) if s=='pre' else (c['merge']+c['cross']-c['out']+c['lateral'])
                    assert count[s,g]==old_count[s][g]+delta,(arm,t,s,g,count[s,g],old_count[s][g],c)
                    checks+=1
            if begin<t<=cutoff:
                for k,n in count.items():exposures[k]+=n
                # Match the existing extractor's first-history-frame rule.
                if t>begin+1:
                    for old_side,new_side,g,h in switches:
                        exchanges[old_side,g,h]+=1;alternative[new_side,g,h]+=1
            ambiguous+=amb;skipped+=skip
            rows.append(dict(time_s=t,counts={s:[count[s,g] for g in range(3)] for s in ('pre','post')},
                terms={s:[dict(terms[s][g]) for g in range(3)] for s in ('pre','post')},ambiguous_exchange_events=amb,skipped_post_entries=skip))
            previous=current
        with (nullcontext(()) if cached else path.open('rb')) as stream:
            for line in stream:
                digest.update(line)
                if not line[:1].isdigit():continue
                p=line.rstrip(b'\r\n').split(b';');t=int(float(p[0]))
                if not begin<=t<=end:continue
                if last is not None and last!=t:
                    assert t==last+1;process(last,frame);frame={}
                last=t;link=int(p[2])
                if link not in (2,10639,10643,10682):continue
                pos=float(p[4]);frame[int(p[1])]=(link,min(int(p[3])-1,2),pos+shift if link==2 else pos,float(p[6]))
        if cached:
            rows=cached['rows'];checks=cached['checks'];ambiguous=cached['ambiguous_exchange_events'];skipped=cached['skipped_post_entries']
        else:
            assert last==end;process(last,frame)
        assert len(rows)==601 and checks==3600
        after=path.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
        if not cached:assert digest.hexdigest()==validation['new_fzp_sha256']
        history={s:dict(exposure_veh_s=[exposures[s,g] for g in range(3)],
            counts=[[exchanges[s,g,h] for h in range(3)] for g in range(3)],
            alternative_counts=[[alternative[s,g,h] for h in range(3)] for g in range(3)],
            rates_per_sec=[[exchanges[s,g,h]/exposures[s,g] if exposures[s,g] else 0. for h in range(3)] for g in range(3)]) for s in ('pre','post')}
        if cached:history=cached['history']
        histories[arm]=history
        sources[arm]=dict(path=str(path.relative_to(e.ROOT)),sha256=validation['new_fzp_sha256'],bytes=before.st_size,mtime_ns=before.st_mtime_ns)
        if not cached:e.save(cache_path,dict(rows=rows,history=history,source=sources[arm],checks=checks,ambiguous_exchange_events=ambiguous,skipped_post_entries=skipped))
        pred=e.load(HERE/f'urban_route_transport_space_v1_network_intent_current_limits_partition_on_v4/prediction_{arm}.json')
        proad=next(r for r in pred['diagnostics']['roads'] if r['road']=='FW_E')
        trace=proad['branch_partition_trace'];groups={(r['time_s'],r['group']):r for r in pred['lane_groups']['FW_E'] if r['cell']==8}
        native_index={r['time_s']:r for r in rows};initial=native_index[cutoff]['counts'];prior=copy.deepcopy(initial);mrows=[]
        for t in range(cutoff+10,end+1,10):
            values=blank()
            for r in (r for r in trace if r['time_s']==t):
                g=r['group'];group=groups[t,g];cross=r['internal_cross_veh'];off=r['off_out_veh'];leave=r['mainline_out_veh'];enter=group['longitudinal_in_veh'];merge=group['merge_in_veh']
                values['pre'][g].update({'in':enter,'cross':cross,'off':off,'lateral':r['pre_n']-prior['pre'][g]-enter+cross+off})
                values['post'][g].update({'merge':merge,'cross':cross,'out':leave,'lateral':r['post_n']-prior['post'][g]-merge-cross+leave})
                prior['pre'][g]=r['pre_n'];prior['post'][g]=r['post_n']
            assert abs(sum(values[s][g]['lateral'] for s,g in keys))<1e-7
            mrows.append(dict(time_s=t,counts=copy.deepcopy(prior),terms={s:[dict(values[s][g]) for g in range(3)] for s in ('pre','post')}))
        comparison={}
        for s,g in keys:
            channels=('in','cross','off','lateral') if s=='pre' else ('merge','cross','out','lateral')
            signs={'in':1,'merge':1,'cross':-1 if s=='pre' else 1,'off':-1,'out':-1,'lateral':1}
            counts={};weighted={}
            for ch in channels:
                counts[ch]={};weighted[ch]={}
                for label,chosen in [('native',[r for r in rows if r['time_s']>cutoff]),('model',mrows)]:
                    counts[ch][label]=sum(r['terms'][s][g].get(ch,0) for r in chosen)
                    weighted[ch][label]=sum((46-math.ceil((r['time_s']-cutoff)/10))/45*r['terms'][s][g].get(ch,0)*signs[ch] for r in chosen)
                weighted[ch]['difference']=weighted[ch]['model']-weighted[ch]['native']
            means={label:statistics.mean(r['counts'][s][g] for r in chosen) for label,chosen in [('native',[native_index[t] for t in range(cutoff+10,end+1,10)]),('model',mrows)]}
            for label in ('native','model'):assert abs(initial[s][g]+sum(weighted[ch][label] for ch in channels)-means[label])<1e-7
            comparison[f'{s}:{g}']=dict(flows=counts,mean_stock_contributions=weighted,mean_n=means)
        result[arm]=comparison;e.save(out/f'model_{arm}.json',mrows)
        print(arm,'pre_group2',comparison['pre:2'],flush=True)
    assert histories['none']==histories['vsl'],'Precontrol spatial exchange changed between arms'
    original=e.load(H/'lane_group_response_20260919/observations_v1/s23.json')['cutoffs']['2400']['exchange_rates_per_sec'][8]
    combined=[[sum(histories['none'][s]['counts'][g][h] for s in ('pre','post'))/sum(histories['none'][s]['exposure_veh_s'][g] for s in ('pre','post')) for h in range(3)] for g in range(3)]
    assert all(abs(a-b)<1e-12 for row,reference in zip(combined,original) for a,b in zip(row,reference)),('Past whole-cell rate mismatch',combined,original)
    e.save(out/'result.json',dict(comparison=result,history=histories['none'],original_whole_cell_rates=original,
        past_whole_cell_rates_exact=True,past_information_cutoff_s=cutoff,future_flows_used_for_validation_only=True,
        future_conditioning_of_predictions=False,new_native_runs=0,sources=sources,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),elapsed_s=time.perf_counter()-started,
        convention='External entry uses receiving group; exit uses prior group. Within-cell simultaneous side/lane changes use old-side exchange then crossing; alternative past counts are retained. Native1s fluxes are summed into identical10s model intervals.',qualified=False))


if __name__=='__main__':main()
