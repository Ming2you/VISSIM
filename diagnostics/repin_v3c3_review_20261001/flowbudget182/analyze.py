"""Close native/model stock errors and verify the actual shared-lane constraint."""
from pathlib import Path
import csv
from collections import defaultdict
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main(*, work=None, case='s67_late', arms=('release','release_vsl90'),
         modes=('baseline','queue'), observation_dirs=None):
    work=Path(work) if work is not None else HERE
    assert h.read(work/'forecast/status.json')['status']=='complete'
    pins={str(Path(__file__)):h.sha(__file__)}
    def read(p):pins[str(p)]=h.sha(p);return h.read(p)
    protocol=read(work/'protocol.json')
    budgets=[];constraints=[];snapshots=[];checks=defaultdict(int);errors=defaultdict(float)
    for arm in arms:
        path=(Path(observation_dirs[arm])/'flows_30s.csv' if observation_dirs is not None
              else h.I/f'heldout67_freeway_20260930/observations/{arm}/flows_30s.csv')
        pins[str(path)]=h.sha(path)
        with path.open(encoding='utf-8-sig',newline='') as f:
            truth={(round(float(z['window_end_s']),1),int(z['cell'])):{k:float(v) for k,v in z.items() if k!='road'}
                   for z in csv.DictReader(f) if z['road']=='FW_E'}
        for mode in modes:
            pred=read(work/f'forecast/{mode}/{case}_{arm}.json.gz')
            audit=read(work/f'forecast/{mode}/{case}_{arm}_audit.json.gz')
            assert all(audit['parity'].values());checks['unchanged_physical_tables']+=4
            rows={(round(z['time_s'],1),z['cell'],z['lane']):z for z in audit['rows']}
            flows={(round(z['window_end_s'],1),z['cell']):z for z in pred['flows']}
            cells={(round(z['time_s'],1),z['cell']):z for z in pred['cells']}
            for z in audit['rows']:
                residual=z['end_n']-z['n']-z['incoming']-z['merge']+z['outgoing']+z['off']-z['lateral_net']
                assert abs(residual)<1e-9;errors['lane_bookkeeping']=max(errors['lane_bookkeeping'],abs(residual))
                checks['lane_bookkeeping']+=1
            for t in sorted({z[0] for z in rows}):
                for i in (19,20,21):
                    lateral=sum(rows[t,i,g]['lateral_net'] for g in (1,2,3))
                    errors['lateral_sum']=max(errors['lateral_sum'],abs(lateral));assert abs(lateral)<1e-8
                    checks['lateral_sum']+=1
            for end in sorted({t for t,i in flows if i==20}):
                for i in (19,20,21):
                    native=truth[end,i]
                    # In this local window there are no deletion/unexplained
                    # events to hide in the ordinary physical flow balance.
                    assert all(native[k]==0 for k in ['unexplained_entries','unexplained_losses','native_removals','terminal_exits_inferred','source_admissions'])
                    nres=native['end_n_veh']-native['start_n_veh']-native['upstream_crossings']-native['ramp_merges']+native['downstream_crossings']+native['off_departures']
                    assert abs(nres)<1e-9;checks['native_balance']+=1
                    rs=[z for z in audit['rows'] if z['cell']==i and end-30-1e-6<=z['time_s']<end-1e-6]
                    assert len(rs)==90
                    for field,key in [('outgoing','downstream_crossings'),('merge','ramp_merges'),('off','off_departures')]:
                        error=abs(sum(z[field] for z in rs)-flows[end,i][key])
                        errors['trace_to_flow']=max(errors['trace_to_flow'],error);assert error<1e-8
                        checks['trace_to_flow']+=1
                    error=abs(sum(rows[round(end-1,1),i,g]['end_n'] for g in (1,2,3))-cells[end,i]['n_veh'])
                    errors['trace_to_stock']=max(errors['trace_to_stock'],error);assert error<1e-8
            for lo,hi in [(2670.1,2700.1),(2670.1,2820.1),(2820.1,2970.1),(2970.1,3120.1)]:
                ts=sorted(t for t,i in flows if i==20 and lo<t<=hi+1e-6)
                for i in (19,20,21):
                    native_first=truth[ts[0],i];native_last=truth[ts[-1],i]
                    z=dict(arm=arm,mode=mode,cell=i,start=lo,end=hi,
                        start_error=sum(rows[lo,i,g]['n'] for g in (1,2,3))-native_first['start_n_veh'],
                        end_error=cells[hi,i]['n_veh']-native_last['end_n_veh'],
                        incoming_error=sum(flows[t,i-1]['downstream_crossings']-truth[t,i]['upstream_crossings'] for t in ts),
                        merge_error=sum(flows[t,i]['ramp_merges']-truth[t,i]['ramp_merges'] for t in ts),
                        through_error=sum(flows[t,i]['downstream_crossings']-truth[t,i]['downstream_crossings'] for t in ts),
                        off_error=sum(flows[t,i]['off_departures']-truth[t,i]['off_departures'] for t in ts))
                    residual=z['end_error']-z['start_error']-z['incoming_error']-z['merge_error']+z['through_error']+z['off_error']
                    errors['inventory_error_balance']=max(errors['inventory_error_balance'],abs(residual));assert abs(residual)<1e-8
                    budgets.append(z)
            for block in range(3):
                lo=2670.1+150*block;hi=lo+150
                js=[z for z in audit['junction'] if lo-1e-6<=z['time_s']<hi-1e-6]
                assert len(js)==150
                totals=defaultdict(float)
                for j in js:
                    t=round(j['time_s'],1);local=rows[t,20,1];down=rows[t,21,1]
                    req=j['through_request_veh'];space=j['through_receiving_veh']
                    assert abs(space-down['receiving_after_merge'])<1e-9
                    assert abs(down['receiving_before_merge']-down['merge']-space)<1e-9
                    off_factor=j['off_accepted_veh']/j['off_request_veh'] if j['off_request_veh'] else 1.
                    expected=min(req*off_factor,space)
                    assert abs(expected-local['outgoing'])<1e-9
                    checks['actual_constraint']+=1
                    totals['raw_mainline_request']+=req
                    totals['right_lane_receiving']+=down['receiving_before_merge']
                    totals['accepted_merge']+=down['merge']
                    totals['remaining_for_mainline']+=space
                    totals['accepted_mainline']+=local['outgoing']
                    totals['unused_receiving']+=max(0.,space-local['outgoing'])
                    totals['receiving_binding_seconds']+=int(req>space+1e-9)
                    totals['off_requested']+=j['off_request_veh']
                    totals['off_branch_loss']+=j['off_request_veh']-j['off_before_veh']
                    totals['off_shared_loss']+=j['off_before_veh']-j['off_accepted_veh']
                    totals['off_accepted']+=j['off_accepted_veh']
                constraints.append(dict(arm=arm,mode=mode,start=lo,end=hi,**totals))
    for p,d in {**pins,**protocol['protected_sha256'],protocol['STOP']['path']:protocol['STOP']['sha256']}.items():assert h.sha(p)==d,p
    h.save(work/'analysis.json',dict(status='complete',checks=dict(checks),max_errors=dict(errors),
        inventory_budgets=budgets,constraints=constraints,input_sha256=pins,
        scope='Autonomous predictions, native observations only scoring. Local cells19--21; component transfer notOmegaTTD.',
        unchanged_physics=True,full_goal='ACTIVE_NOT_QUALIFIED'))
    for z in constraints:print(z)


def observed_supply184():
    """Cached-state diagnostic of receiving; never an operational forecast."""
    import math
    import statistics
    from evaluation.controllers import lane_plant_runtime as lpr
    from evaluation.controllers.physical_lane_groups import hadi_receiving_vph

    work=h.R/'receiving184/attempt3'
    work.mkdir(exist_ok=True)
    assert not (work/'protocol.json').exists(), 'Preserve completed/failed diagnostics'
    old=h.read(HERE/'protocol.json')
    protected=old['protected_sha256']
    pins={str(Path(__file__)):h.sha(__file__)}
    def read(path):
        pins[str(path)]=h.sha(path)
        return h.read(path)
    def csvread(path):
        pins[str(path)]=h.sha(path)
        with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
    configs={}
    for name,manifest in [('baseline',h.R/'lane_state132/eval_01/manifest.json'),
                          ('refit183',h.R/'phase_joint183/queue_validation/manifest.json')]:
        pins[str(manifest)]=h.sha(manifest)
        context=lpr.load_sources(manifest)
        for path in context['paths'].values():pins[str(path)]=h.sha(path)
        cfg=context['component']._config('FW_E',context['parameters']['by_direction']['FW_E'])
        configs[name]=(cfg,context)
    assert configs['baseline'][0].simulation.T_f_h==1/3600
    parameters={}
    for name,(cfg,_) in configs.items():
        fd=cfg.network.freeway_segment_params['FW_E'][21]
        c=fd['rho_crit'];jam=cfg.network.rho_max
        cap=c*fd['v_free']*math.exp(-1/fd['metanet_a_m'])
        parameters[name]=dict(length_km=fd['segment_length_km'],critical=c,jam=jam,
                              capacity_vph=cap,wave_kmh=cap/(jam-c))
    def budget(n,name):
        p=parameters[name]
        room=max(0.,p['jam']*p['length_km']-n)
        rate=hadi_receiving_vph(n/p['length_km'],p['jam'],p['critical'],
                                p['capacity_vph'],p['wave_kmh'],0.)
        return min(room,rate/3600.)
    windows=[(2670.1,2820.1),(2820.1,2970.1),(2970.1,3120.1)]
    arms=['hold','release','hold_vsl90','release_vsl90']
    h.save(work/'protocol.json',dict(
        previous_goal_turn='PROGRESS183: joint refit improved queue errors but failed material VSL sign.',
        question='Does the current receiving law lose the VSL response even with observed cell21 lane stocks?',
        windows=windows,parameters=parameters,
        scope='Seed67 four cached controls. Actual current states are conditioning inputs; no autonomous forecast, fitting, or production update.',
        budget=dict(forecasts=0,fits=0,native=0,FZP_reads=0),
        methods=['Apply exact1s receiving to current5s snapshot, hold fixed for5s for a quadrature diagnostic.',
                 'Both source/destination endpoint lanes are retained; crossing lane during5s is unknown.',
                 'Native connector departures supply actual merge labels. Subtracting them is a future-conditioned diagnostic only.',
                 'Compare unchanged baseline and refit183 FD on the same observed stocks, and on saved autonomous stocks.',
                 'Native30s flow tables independently check all-lane mainline crossings, ramp merges and off entries.'],
        limits=['A receiving budget is an upper bound, not a discharge prediction.',
                'Five-second snapshot quadrature and stochastic vehicle counts need not obey per-bin continuous flow limits.',
                'Matched late states are different outcomes after common initial controls, not independent causal interventions.',
                'Internal mainline/off transfers are not Omega TTD. No wholeOmega or eight-ramp qualification.'],
        protected_sha256=protected,STOP=old['STOP']))
    rows=[];native=[];checks=defaultdict(int);maxerrors=defaultdict(float)
    for arm in arms:
        data=read(h.R/f'blocking176/{arm}_frames.json.gz')
        ix={k:i for i,k in enumerate(data['fields'])};frames=data['frames']
        root=h.I/f'heldout67_freeway_20260930/observations/{arm}'
        events=csvread(root/'port_events.csv')
        flows=csvread(root/'flows_30s.csv')
        flow={(round(float(z['window_end_s']),1),int(z['cell'])):z for z in flows if z['road']=='FW_E'}
        armrows=[]
        for step in range(90):
            t=round(2670.1+step*5,1);end=round(t+5,1)
            a=frames[str(t)];b=frames[str(end)]
            lane20=[z for z in a.values() if z[ix['cell']]==20 and z[ix['lane']]==1]
            n21=[sum(z[ix['cell']]==21 and z[ix['lane']]==g for z in a.values()) for g in (1,2,3)]
            crossings=[(z,b[k]) for k,z in a.items() if k in b and z[ix['cell']]<=20 and b[k][ix['cell']]>=21]
            matrix=[[sum(z[ix['lane']]==i and w[ix['lane']]==j for z,w in crossings) for j in (1,2,3)] for i in (1,2,3)]
            assert sum(map(sum,matrix))==len(crossings)
            merge=sum(z['connector']=='10490' and z['kind']=='departure' and t<float(z['time_s'])<=end+1e-7 for z in events)
            off=sum(z['connector']=='10483' and z['kind']=='arrival' and t<float(z['time_s'])<=end+1e-7 for z in events)
            n_exit=sum(str(z[ix['nextlink']])=='10483' for z in lane20)
            v20=statistics.mean(z[ix['speed']] for z in lane20) if lane20 else 0.
            length20=configs['baseline'][0].network.freeway_segment_params['FW_E'][20]['segment_length_km']
            # The model uses the whole cell length, not the slightly shorter
            # distance from cell start to the physical branch point.
            fraction=min(1.,v20*5/3600/length20)
            exit_request=n_exit*fraction;through_request=(len(lane20)-n_exit)*fraction
            r=dict(arm=arm,time_s=t,end_s=end,n21=n21,cross_all=len(crossings),cross_lane_matrix=matrix,
                   merge=merge,off=off,n20_lane1=len(lane20),v20_lane1=v20,n20_exit=n_exit,
                   exit_request=exit_request,through_request=through_request,receiving={},conditional={})
            for name in parameters:
                supply=[5*budget(n,name) for n in n21]
                remaining=max(0.,supply[0]-merge)
                factor=min(1.,remaining/through_request) if through_request else 1.
                r['receiving'][name]=supply
                r['conditional'][name]=dict(exit_fifo=exit_request*factor,through_accepted=min(through_request,remaining),
                    merge_over_snapshot_budget=max(0.,merge-supply[0]),remaining=remaining)
            # Endpoint membership provides an exact stock ledger. It does NOT
            # identify the location/lane of every intermediate crossing.
            aa={k for k,z in a.items() if z[ix['cell']]==21 and z[ix['lane']]==1}
            bb={k for k,z in b.items() if z[ix['cell']]==21 and z[ix['lane']]==1}
            r['lane21_membership']=dict(start=len(aa),end=len(bb),entered=len(bb-aa),left=len(aa-bb),
                samecell_lateral_in=sum(k in a and a[k][ix['cell']]==21 for k in bb-aa),
                samecell_lateral_out=sum(k in b and b[k][ix['cell']]==21 for k in aa-bb))
            assert len(bb)-len(aa)==len(bb-aa)-len(aa-bb)
            checks['endpoint_stock_balance']+=1
            armrows.append(r)
        for step in range(15):
            end=round(2700.1+30*step,1)
            zs=[z for z in armrows if end-30-1e-6<=z['time_s']<end-1e-6]
            assert len(zs)==6
            for field,cell,key in [('cross_all',20,'downstream_crossings'),('merge',21,'ramp_merges'),('off',20,'off_departures')]:
                err=abs(sum(z[field] for z in zs)-float(flow[end,cell][key]))
                maxerrors['native_'+field]=max(maxerrors['native_'+field],err)
                assert err<1e-9,(arm,end,field,err)
                checks['independent_native30s_flow']+=1
        for lo,hi in windows:
            zs=[z for z in armrows if lo-1e-6<=z['time_s']<hi-1e-6];assert len(zs)==30
            item=dict(arm=arm,start=lo,end=hi,mean_n21_lane1=statistics.mean(z['n21'][0] for z in zs),
                mean_n21_by_lane=[statistics.mean(z['n21'][g] for z in zs) for g in range(3)],
                lane21_endpoint_membership={k:sum(z['lane21_membership'][k] for z in zs)
                    for k in ['entered','left','samecell_lateral_in','samecell_lateral_out']},
                cross_all=sum(z['cross_all'] for z in zs),merge=sum(z['merge'] for z in zs),off=sum(z['off'] for z in zs),
                cross_same_endpoint_lane1=sum(z['cross_lane_matrix'][0][0] for z in zs),
                cross_either_endpoint_lane1=sum(sum(z['cross_lane_matrix'][0])+sum(row[0] for row in z['cross_lane_matrix'][1:]) for z in zs),
                exit_request=sum(z['exit_request'] for z in zs),through_request=sum(z['through_request'] for z in zs),
                receiving={},conditional={})
            for name in parameters:
                item['receiving'][name]=[sum(z['receiving'][name][g] for z in zs) for g in range(3)]
                item['conditional'][name]={k:sum(z['conditional'][name][k] for z in zs) for k in zs[0]['conditional'][name]}
            native.append(item)
        rows.extend(armrows)
    autonomous=[]
    for arm in arms:
        phase=read(h.R/f'phase_joint183/queue_validation/forecast/queue/s67_late_{arm}_phase.json.gz')
        pred=read(h.R/f'phase_joint183/queue_validation/forecast/queue/s67_late_{arm}.json.gz')
        qall=[z for z in phase['events'] if z['cell']==21]
        qrows=[z for z in qall if z['lane']==1]
        ramps={round(z['start_sec'],1):z for z in pred['ramps'] if z['start']['connector_id']=='10490'}
        assert len(qrows)==len(ramps)==450
        for z in qrows:
            right_lane=budget(z['n0'],'refit183')
            receipt=ramps[round(z['time_s'],1)]
            node=receipt['receiving_node']
            # This receipt is the RAMP allocation after canonical service and
            # gap acceptance. It is not the full lane receiving budget.
            assert node['unlimited_node_canonical_budget_vph']/3600<=right_lane+1e-8
            expected=min(node['unlimited_node_canonical_budget_vph'],node['gap_supply_vph_per_lane'])/3600
            actual=receipt['receiving_budget_veh']
            error=abs(expected-actual)
            maxerrors['ramp_gap_receipt']=max(maxerrors['ramp_gap_receipt'],error)
            assert error<1e-8,(arm,z['time_s'],expected,actual)
            checks['ramp_receipt_within_lane_and_gap_supply']+=1
        sources=[('queue183',qall,'n0')]
        if arm in ('release','release_vsl90'):
            audit=read(HERE/f'forecast/baseline/s67_late_{arm}_audit.json.gz')
            ball=[z for z in audit['rows'] if z['cell']==21]
            br=[z for z in ball if z['lane']==1]
            for z in br:
                error=abs(budget(z['n'],'baseline')-z['receiving_before_merge'])
                maxerrors['reconstructed_runtime_receiving']=max(maxerrors['reconstructed_runtime_receiving'],error)
                assert error<1e-8
                checks['reconstructed_runtime_receiving']+=1
            sources.append(('baseline',ball,'n'))
        for label,zs,nkey in sources:
            for lo,hi in windows:
                all_window=[z for z in zs if lo-1e-6<=z['time_s']<hi-1e-6];assert len(all_window)==450
                window=[z for z in all_window if z['lane']==1];assert len(window)==150
                autonomous.append(dict(model=label,arm=arm,start=lo,end=hi,
                    mean_n21_lane1=statistics.mean(z[nkey] for z in window),
                    mean_n21_by_lane=[statistics.mean(z[nkey] for z in all_window if z['lane']==g) for g in (1,2,3)],
                    receiving={name:sum(budget(z[nkey],name) for z in window) for name in parameters}))
    for path,digest in {**pins,**protected,old['STOP']['path']:old['STOP']['sha256']}.items():assert h.sha(path)==digest,path
    # h.save emits plain JSON; use the matching suffix.
    h.save(work/'rows.json',rows)
    h.save(work/'analysis.json',dict(status='complete',native=native,autonomous=autonomous,checks=dict(checks),
        max_errors=dict(maxerrors),parameters=parameters,input_sha256=pins,protected_and_STOP=True,
        operational_validation=False,adopted=False,full_goal='ACTIVE_NOT_QUALIFIED'))
    for z in native:
        if z['start']==2820.1:print('NATIVE',z)
    for z in autonomous:
        if z['start']==2820.1:print('AUTONOMOUS',z)
    print('VERIFIED',dict(checks),dict(maxerrors),flush=True)


def lane_budget185():
    """Trace the first lane-stock divergence; preserve endpoint censoring."""
    import statistics
    import ast
    work=h.R/'lane_budget185'
    assert not (work/'analysis_extended.json').exists()
    protocol=h.read(h.R/'phase_joint183/audit185/protocol.json')
    protected=protocol['protected_sha256'];pins={str(Path(__file__)):h.sha(__file__)}
    def read(p):pins[str(p)]=h.sha(p);return h.read(p)
    def table(p):
        pins[str(p)]=h.sha(p)
        with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
    status=read(h.R/'phase_joint183/audit185/forecast/status.json')
    assert status==dict(status='complete',forecasts=2)
    original=ast.parse((work/'completed184_analyze.py.txt').read_text(encoding='utf-8'))
    current=ast.parse(Path(__file__).read_text(encoding='utf-8'))
    for name in ('main','observed_supply184'):
        pick=lambda tree:ast.dump(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name))
        assert pick(original)==pick(current)
    windows=[(2670.1,2700.1),(2700.1,2730.1),(2730.1,2820.1),(2820.1,2970.1),(2970.1,3120.1)]
    native=[];predicted=[];summary=[];checks=defaultdict(int);errors=defaultdict(float)
    for arm in ('release','release_vsl90'):
        data=read(h.R/f'blocking176/{arm}_frames.json.gz');ix={k:i for i,k in enumerate(data['fields'])};frames=data['frames']
        folder=h.I/f'heldout67_freeway_20260930/observations/{arm}'
        events=table(folder/'port_events.csv')
        flows={(round(float(z['window_end_s']),1),int(z['cell'])):z for z in table(folder/'flows_30s.csv') if z['road']=='FW_E'}
        rows=[]
        for step in range(90):
            t=round(2670.1+step*5,1);end=round(t+5,1);a=frames[str(t)];b=frames[str(end)]
            merge={z['vehicle'] for z in events if z['connector']=='10490' and z['kind']=='departure' and t<float(z['time_s'])<=end+1e-7}
            off={z['vehicle'] for z in events if z['connector']=='10481' and z['kind']=='arrival' and t<float(z['time_s'])<=end+1e-7}
            aa={k for k,z in a.items() if z[ix['cell']]==21 and z[ix['lane']]==1}
            bb={k for k,z in b.items() if z[ix['cell']]==21 and z[ix['lane']]==1}
            z=dict(arm=arm,start=t,end=end,start_n=len(aa),end_n=len(bb),
                start_v=statistics.mean(a[k][ix['speed']] for k in aa) if aa else None,
                upstream_enter=0,merge_enter=0,lateral_in=0,lateral_out=0,downstream_leave=0,
                unknown_in=0,unknown_out=0,boundary_lane_in=0,boundary_lane_out=0,
                merge_all=len(merge),bypass_all=0,bypass_merge=0)
            for k in bb-aa:
                if k in a and a[k][ix['cell']]==21:z['lateral_in']+=1
                elif k in a and a[k][ix['cell']]<21:
                    z['upstream_enter']+=1;z['boundary_lane_in']+=int(a[k][ix['lane']]!=1)
                elif k in merge:z['merge_enter']+=1
                else:z['unknown_in']+=1
            for k in aa-bb:
                if k in b and b[k][ix['cell']]==21:z['lateral_out']+=1
                elif k in b and b[k][ix['cell']]>21:
                    z['downstream_leave']+=1;z['boundary_lane_out']+=int(b[k][ix['lane']]!=1)
                elif k in off:z['downstream_leave']+=1
                else:z['unknown_out']+=1
            z['bypass_all']=sum(v[ix['cell']]<21 and k in b and b[k][ix['cell']]>21 for k,v in a.items())
            z['bypass_merge']=sum(k in b and b[k][ix['cell']]>21 for k in merge)
            z['member_balance']=(z['end_n']-z['start_n']-z['upstream_enter']-z['merge_enter']-z['lateral_in']-z['unknown_in']
                                 +z['downstream_leave']+z['lateral_out']+z['unknown_out'])
            assert z['member_balance']==0;checks['native_membership_balance']+=1
            rows.append(z)
        for step in range(15):
            end=round(2700.1+step*30,1)
            zs=[z for z in rows if end-30-1e-6<=z['start']<end-1e-6]
            assert sum(z['merge_all'] for z in zs)==float(flows[end,21]['ramp_merges'])
            checks['independent_merge_events']=checks['independent_merge_events']+1
        native.extend(rows)
        modelrows={}
        for model,path in [('baseline',HERE/f'forecast/baseline/s67_late_{arm}_audit.json.gz'),
            ('queue183',h.R/f'phase_joint183/audit185/forecast/queue/s67_late_{arm}_audit.json.gz')]:
            audit=read(path);assert all(audit['parity'].values());checks['exact_physical_tables']+=4
            allrows=audit['rows']
            rs=[z for z in allrows if z['cell']==21 and z['lane']==1];assert len(rs)==450
            for z in allrows:
                residual=z['end_n']-z['n']-z['incoming']-z['merge']+z['outgoing']+z['off']-z['lateral_net']
                errors['model_stock_bookkeeping']=max(errors['model_stock_bookkeeping'],abs(residual));assert abs(residual)<1e-9
                checks['model_stock_bookkeeping']+=1
            for time in sorted({z['time_s'] for z in rs}):
                lateral=sum(z['lateral_net'] for z in allrows if z['time_s']==time and z['cell']==21)
                errors['cell21_lateral_sum']=max(errors['cell21_lateral_sum'],abs(lateral));assert abs(lateral)<1e-8
                checks['cell21_lateral_sum']+=1
            modelrows[model]=rs
            for step in range(90):
                lo=round(2670.1+step*5,1);hi=round(lo+5,1)
                zs=[z for z in rs if lo-1e-6<=z['time_s']<hi-1e-6];assert len(zs)==5
                predicted.append(dict(model=model,arm=arm,start=lo,end=hi,start_n=zs[0]['n'],end_n=zs[-1]['end_n'],
                    start_v=zs[0]['v'],**{key:sum(z[key] for z in zs) for key in ('incoming','merge','outgoing','lateral_net')}))
        for lo,hi in windows:
            ns=[z for z in rows if lo-1e-6<=z['start']<hi-1e-6]
            countkeys=['upstream_enter','merge_enter','lateral_in','lateral_out','downstream_leave','unknown_in','unknown_out',
                       'boundary_lane_in','boundary_lane_out','merge_all','bypass_all','bypass_merge']
            truth=dict(start_n=ns[0]['start_n'],end_n=ns[-1]['end_n'],**{k:sum(z[k] for z in ns) for k in countkeys})
            for model,rs in modelrows.items():
                zs=[z for z in rs if lo-1e-6<=z['time_s']<hi-1e-6]
                forecast=dict(start_n=zs[0]['n'],end_n=zs[-1]['end_n'],**{k:sum(z[k] for z in zs) for k in ('incoming','merge','outgoing','lateral_net')})
                decomposition=dict(start_error=forecast['start_n']-truth['start_n'],end_error=forecast['end_n']-truth['end_n'],
                    incoming_minus_endpoint_cohort=forecast['incoming']-truth['upstream_enter'],
                    merge_minus_endpoint_cohort=forecast['merge']-truth['merge_enter'],
                    outgoing_minus_endpoint_cohort=forecast['outgoing']-truth['downstream_leave'],
                    lateral_minus_samecell_endpoints=forecast['lateral_net']-truth['lateral_in']+truth['lateral_out'],
                    native_unknown_net=truth['unknown_in']-truth['unknown_out'])
                resid=(decomposition['end_error']-decomposition['start_error']-decomposition['incoming_minus_endpoint_cohort']
                    -decomposition['merge_minus_endpoint_cohort']+decomposition['outgoing_minus_endpoint_cohort']
                    -decomposition['lateral_minus_samecell_endpoints']+decomposition['native_unknown_net'])
                errors['decomposition']=max(errors['decomposition'],abs(resid));assert abs(resid)<1e-8
                summary.append(dict(arm=arm,model=model,start=lo,end=hi,truth=truth,predicted=forecast,decomposition=decomposition,
                    interpretation='Endpoint-membership identity; gross flow and lateral attribution are censored when a vehicle crosses both cell and lane. Not causal contribution.'))
    # The pre-control observed and predicted prefixes must be common.
    for key,source in [('native',native),('predicted',predicted)]:
        a=[{k:v for k,v in z.items() if k!='arm'} for z in source if z['arm']=='release' and z['start']<2700.1]
        b=[{k:v for k,v in z.items() if k!='arm'} for z in source if z['arm']=='release_vsl90' and z['start']<2700.1]
        assert a==b,key
    # One reference arm per distinct starting state avoids treating the
    # identical pre-control prefixes as four independent observations.
    catalog=read(h.C/'data_catalog.json')['checked_records']
    refs=[next(r for r in catalog if r['case']=='s29_late' and r['arm']=='hold'),
          next(r for r in catalog if r['case']=='s43_early' and r['arm']=='none')]
    for seed in (61,67):
        folder=h.I/f'heldout{seed}_freeway_20260930'
        capture=read(folder/'capture.json')
        record=next(r for r in capture['records'] if r['arm']=='hold')
        refs.append(dict(record,case=f's{seed}_late',cutoff=capture['cutoff'],truth=str(folder/'observations/hold')))
    ramp_audit=[]
    for record in refs:
        truth=[z for z in table(Path(record['truth'])/'flows_30s.csv') if z['road']=='FW_E']
        prefix=f"{record['case']}_{record['arm']}"
        base=read(h.R/f'queue_dynamics178/forecast/baseline/{prefix}.json.gz')
        queue_folder='queue_full' if record['case']=='s29_late' else 'queue_validation'
        fitted=read(h.R/f'phase_joint183/{queue_folder}/forecast/queue/{prefix}.json.gz')
        for horizon in (30,150,450):
            lo=record['cutoff'];hi=lo+horizon
            for cell,connector in [(10,'10639'),(12,'10681'),(21,'10490'),(23,'10484')]:
                actual=sum(float(z['ramp_merges']) for z in truth if int(z['cell'])==cell and lo+1e-6<float(z['window_end_s'])<=hi+1e-6)
                values={name:sum(z['ramp_merges'] for z in obj['flows'] if z['cell']==cell and lo+1e-6<z['window_end_s']<=hi+1e-6)
                        for name,obj in [('baseline',base),('queue183',fitted)]}
                ramp_audit.append(dict(case=record['case'],arm=record['arm'],start=lo,horizon=horizon,cell=cell,connector=connector,actual=actual,**values))
    for path,digest in {**pins,**protected,protocol['STOP']['path']:protocol['STOP']['sha256']}.items():assert h.sha(path)==digest,path
    h.save(work/'analysis_extended.json',dict(status='complete',checks=dict(checks),max_errors=dict(errors),summary=summary,
        native5=native,predicted5=predicted,input_sha256=pins,precontrol_common=True,
        reference_ramp_profiles=ramp_audit,unique_reference_states=4,
        scopes=['Native same-cell lateral counts are observable endpoint net changes, not complete lane-change totals.',
                'Exact model lane bookkeeping alone is not an independent native flux comparison.',
                'Original12-window184 state mean conclusions remain;185 diagnoses two RM-release arms.'],
        autonomous_forecasts_new=2,parameters_changed=False,adopted=False,full_goal='ACTIVE_NOT_QUALIFIED'))
    for z in summary:
        if z['end']==2700.1:print(z)
    print('VERIFIED185',dict(checks),dict(errors),flush=True)


def ramp_posthead186():
    """Native stock balances distinguish head errors from posthead clearing.

    These are net head crossings inferred from 30s endpoints, not measured
    individual crossing times. No native future value enters a forecast.
    """
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import replay_congested_component as replay
    work=h.R/'ramp_posthead186'
    assert not (work/'analysis.json').exists()
    protocol=h.read(work/'protocol.json')
    pins={str(Path(__file__)):h.sha(__file__)}
    checks=defaultdict(int);errors=defaultdict(float)
    def read(path):
        path=Path(path);pins[str(path)]=h.sha(path);return h.read(path)
    def table(path):
        path=Path(path);pins[str(path)]=h.sha(path)
        with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
    def close(name,value):
        errors[name]=max(errors[name],abs(value));assert abs(value)<1e-8,(name,value)
        checks[name]+=1
    catalog=read(h.C/'data_catalog.json')['checked_records']
    refs=[next(r for r in catalog if r['case']=='s29_late' and r['arm']=='hold'),
          next(r for r in catalog if r['case']=='s43_early' and r['arm']=='none')]
    for seed in (61,67):
        folder=h.I/f'heldout{seed}_freeway_20260930';cap=read(folder/'capture.json')
        rr=next(r for r in cap['records'] if r['arm']=='hold')
        refs.append(dict(rr,case=f's{seed}_late',cutoff=cap['cutoff'],truth=str(folder/'observations/hold')))
    windows=[];summaries=[];initial=[];snapshot_rows=[]
    east=('10639','10681','10490','10484')
    for record in refs:
        folder=Path(record['truth']);manifest=read(folder/'manifest.json')
        cohorts=read(folder/'port_cohorts_30s.json')
        ports=table(folder/'ports_30s.csv');events=table(folder/'port_events.csv')
        for name in ('port_cohorts_30s.json','ports_30s.csv','port_events.csv'):
            if 'files' in manifest:
                assert h.sha(folder/name)==manifest['files'][name];checks['native_manifest']+=1
            else:
                # The older43 cache pins its source FZP, not the derived tables.
                # Current table hashes and independent event/count balances
                # remain mandatory; do not claim historical table-hash parity.
                assert record['case']=='s43_early' and 'source_fzp' in manifest and 'sha256' in manifest
                checks['historical_table_hash_unavailable']+=1
        pins[record['input']]=record['sha256']
        _,kwargs=replay.read_primitive_capture(record['input'],record['sha256'])
        specs=kwargs['ramp_dynamics']['ramps'];cut=record['cutoff']
        prefix=f"{record['case']}_{record['arm']}"
        base=read(h.R/f'queue_dynamics178/forecast/baseline/{prefix}.json.gz')
        qdir='queue_full' if record['case']=='s29_late' else 'queue_validation'
        queue=read(h.R/f'phase_joint183/{qdir}/forecast/queue/{prefix}.json.gz')
        for connector in east:
            spec=specs['RM_C'+connector];head=spec['head_position_m']
            def observed(t):
                rows=cohorts[str(round(t,1))][connector]
                assert all(0<=z[0]<=spec['length_m']+.1 and z[1]>=0 for z in rows)
                assert not any(z[0]==head for z in rows),'Exact head boundary needs an explicit tie convention'
                post=[z for z in rows if z[0]>head]
                return dict(total=len(rows),post=len(post),pre=len(rows)-len(post)),post
            actual_initial,_=observed(cut)
            assert sorted(spec['initial_cohorts'])==sorted(cohorts[str(round(cut,1))][connector])
            checks['initial_native_cohorts']+=1
            pre=[z for z in spec['initial_cohorts'] if z[0]<head]
            initial.append(dict(case=record['case'],connector=connector,head_m=head,length_m=spec['length_m'],
                upstream_nominal_kmh=spec['travel_speed_kmh'],posthead_nominal_kmh=spec.get('posthead_travel_speed_kmh',spec['travel_speed_kmh']),
                posthead_nominal_sec=(spec['length_m']-head)*3.6/spec.get('posthead_travel_speed_kmh',spec['travel_speed_kmh']),
                counts=actual_initial,initial_prehead_below5_kmh=sum(z[1]<5 for z in pre)))
            native={round(float(z['window_end_s']),1):z for z in ports if z['connector']==connector}
            for step in range(16):
                t=round(cut+step*30,1);counts,post=observed(t)
                snapshot_rows.append(dict(case=record['case'],connector=connector,time=t,**counts,
                    posthead_stopped_below5=sum(z[1]<5 for z in post),
                    posthead_position_speed_lane=post))
            forecasts={}
            for label,pred in [('baseline',base),('queue183',queue)]:
                rows=[z for z in pred['ramps'] if z['start']['connector_id']==connector]
                assert len(rows)==450
                forecasts[label]=rows
                start=rows[0]['start']
                close('initial_total',start['connector_veh']-actual_initial['total'])
                close('initial_post',start['downstream_travelling_veh']+start['merge_ready_veh']-actual_initial['post'])
                for row in rows:
                    s,e=row['start'],row['end']
                    close('model_post_balance',e['downstream_travelling_veh']+e['merge_ready_veh']-s['downstream_travelling_veh']-s['merge_ready_veh']-row['head_service_veh']+row['accepted_merge_veh'])
                    close('model_total_balance',e['connector_veh']-s['connector_veh']-row['admitted_arrivals_veh']+row['accepted_merge_veh'])
            for step in range(15):
                lo=round(cut+step*30,1);hi=round(lo+30,1);s,_=observed(lo);e,_=observed(hi);port=native[hi]
                arrivals=float(port['arrivals_veh']);merges=float(port['departures_veh'])
                assert float(port['unresolved_absences_veh'])==0
                close('native_whole_stock',e['total']-s['total']-arrivals+merges)
                close('native_start_count',s['total']-float(port['start_n_veh']))
                close('native_end_count',e['total']-float(port['end_n_veh']))
                ev=[z for z in events if z['connector']==connector and lo+1e-6<float(z['time_s'])<=hi+1e-6]
                aa=[z for z in ev if z['kind']=='arrival'];dd=[z for z in ev if z['kind']=='departure']
                assert len(aa)==arrivals and len(dd)==merges and len(ev)==len(aa)+len(dd)
                assert all(float(z['position_m'])<head for z in aa),'First ramp observation already posthead'
                checks['native_event_counts']+=1
                head_net=merges+e['post']-s['post']
                assert head_net>=0
                close('native_pre_balance',e['pre']-s['pre']-arrivals+head_net)
                truth=dict(arrivals=arrivals,head_net=head_net,merges=merges,start=s,end=e)
                for label,rows in forecasts.items():
                    rs=[z for z in rows if lo-1e-6<=z['start_sec']<hi-1e-6];assert len(rs)==30
                    def stock(z):
                        post=z['downstream_travelling_veh']+z['merge_ready_veh']
                        return dict(total=z['connector_veh'],post=post,pre=z['upstream_travelling_veh']+z['head_ready_veh'])
                    forecast=dict(arrivals=sum(z['admitted_arrivals_veh'] for z in rs),head_net=sum(z['head_service_veh'] for z in rs),
                        merges=sum(z['accepted_merge_veh'] for z in rs),start=stock(rs[0]['start']),end=stock(rs[-1]['end']),
                        head_limit=sum(z['head_service_limit_veh'] for z in rs),
                        head_zero_limit_seconds=sum(z['head_service_limit_veh']==0 for z in rs))
                    merge_error=forecast['merges']-merges;head_error=forecast['head_net']-head_net
                    post_change_error=(forecast['end']['post']-forecast['start']['post'])-(e['post']-s['post'])
                    close('merge_error_decomposition',merge_error-head_error+post_change_error)
                    windows.append(dict(case=record['case'],arm=record['arm'],connector=connector,model=label,start=lo,end=hi,
                        native=truth,predicted=forecast,merge_error=merge_error,head_error=head_error,post_change_error=post_change_error))
            for horizon in (30,150,450):
                for label in forecasts:
                    ws=[z for z in windows if z['case']==record['case'] and z['connector']==connector and z['model']==label and z['end']<=cut+horizon+1e-6]
                    agg={}
                    for key in ('native','predicted'):
                        agg[key]=dict(start=ws[0][key]['start'],end=ws[-1][key]['end'],
                            **{f:sum(z[key][f] for z in ws) for f in ('arrivals','head_net','merges')})
                    summaries.append(dict(case=record['case'],arm=record['arm'],connector=connector,model=label,horizon=horizon,
                        **agg,merge_error=sum(z['merge_error'] for z in ws),head_error=sum(z['head_error'] for z in ws),
                        post_change_error=sum(z['post_change_error'] for z in ws)))
    for path,digest in {**pins,**protocol['protected_sha256'],protocol['STOP']['path']:protocol['STOP']['sha256']}.items():assert h.sha(path)==digest,path
    result=dict(status='complete',checks=dict(checks),max_errors=dict(errors),initial=initial,snapshots=snapshot_rows,
        windows=windows,summary=summaries,input_sha256=pins,autonomous_forecasts_new=0,parameters_changed=False,adopted=False,
        limitations=['Head values are net 30s balance estimates, not observed forward-only vehicle head passage events.',
          '30s snapshots cannot establish the travel-time distribution, startup acceleration, signal phase bias or receiving delay separately.',
          'Posthead stock includes travelling vehicles and merge waiting; it is not all stopped queue.',
          'Four previously inspected initial states are distinct but not pristine heldout samples; east4 only.',
          'Seed43 historical manifest has only source-FZP hash; current derived-table hashes are pinned but historical table hashes cannot be checked.',
          'Head/posthead error decomposition is an accounting identity, not causal attribution.'],full_goal='ACTIVE_NOT_QUALIFIED')
    h.save(work/'analysis.json',result)
    for row in summaries:
        if row['connector']=='10490' and row['model']=='baseline':print(row)
    print('VERIFIED186',dict(checks),dict(errors),flush=True)


def ramp_motion187():
    """Bounded native5s ramp trajectories; crossing times remain intervals."""
    import ctypes
    import gzip
    import hashlib
    import json
    import math
    import statistics
    import time
    from diagnostics.repin_v3c3_review_20261001.blocking176.analyze import seek_time
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import replay_congested_component as replay
    work=h.R/'ramp_motion187';protocol=h.read(work/'protocol.json')
    assert not (work/'summary.json').exists()
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    started=time.perf_counter();pins={str(Path(__file__)):h.sha(__file__)};checks=defaultdict(int)
    def read(path):
        path=Path(path);pins[str(path)]=h.sha(path);return h.read(path)
    def table(path):
        path=Path(path);pins[str(path)]=h.sha(path)
        with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
    cat=read(h.C/'data_catalog.json')['checked_records']
    refs=[]
    for case,arm,root in [('s29_late','hold','20260924_release2670_s29'),('s43_early','none','20260924_bottleneck90_full_s43')]:
        refs.append(dict(next(r for r in cat if r['case']==case and r['arm']==arm),native_root=root))
    for seed in (61,67):
        folder=h.I/f'heldout{seed}_freeway_20260930';cap=read(folder/'capture.json')
        for record in cap['records']:
            if seed==61 and record['arm']!='hold':continue
            refs.append(dict(record,case=f's{seed}_late',cutoff=cap['cutoff'],truth=str(folder/'observations'/record['arm']),native_root=f'20260930_release2670_s{seed}'))
    fields=['connector','pos','speed','lane','acceleration','desired_speed']
    all_sources=[];summary=[];stockrows=[];triprows=[];censored=[];all_frames={}
    for record in refs:
        case,arm=record['case'],record['arm'];prefix=f'{case}_{arm}';lo=record['cutoff'];hi=lo+450
        fs=list((Path('D:/VISSIM_runs')/record['native_root']/arm/'run/vissim_eval').glob('*.fzp'));assert len(fs)==1
        path=fs[0];stat=path.stat();frames={round(lo+j*5,1):{} for j in range(91)};digest=hashlib.sha256();count=0
        pins[record['input']]=record['sha256'];_,kwargs=replay.read_primitive_capture(record['input'],record['sha256'])
        specs={str(s['connector_id']):s for s in kwargs['ramp_dynamics']['ramps'].values()};assert len(specs)==8
        with path.open('rb') as f:
            for line in f:
                if line.startswith(b'$VEHICLE:'):
                    ci={n:i for i,n in enumerate(line.split(b':',1)[1].strip().decode().split(';'))};body=f.tell();break
            else:raise AssertionError('No FZP header')
            begin=seek_time(f,lo,body,stat.st_size);previous=-math.inf
            for line in f:
                z=line.rstrip(b'\r\n').split(b';');t=float(z[ci['SIMSEC']]);assert t>=previous;previous=t
                if t<lo-1e-6:continue
                if t>hi+1e-6:break
                digest.update(line);count+=1
                con=z[ci['LANE\\LINK\\NO']].decode()
                if con not in specs:continue
                t=round(t,1);assert t in frames
                vid=z[ci['NO']].decode();assert vid not in frames[t]
                frames[t][vid]=[con,float(z[ci['POS']]),float(z[ci['SPEED']]),int(z[ci['LANE\\INDEX']]),float(z[ci['ACCELERATION']]),float(z[ci['DESSPEED']])]
            read_end=f.tell()
        assert path.stat().st_size==stat.st_size and path.stat().st_mtime_ns==stat.st_mtime_ns
        source=dict(case=case,arm=arm,path=str(path),bytes=stat.st_size,mtime_ns=stat.st_mtime_ns,begin_byte=begin,end_byte=read_end,
                    window_sha256=digest.hexdigest(),all_network_rows=count,ramp_rows=sum(map(len,frames.values())))
        if case=='s67_late':
            old=read(h.R/f'blocking176/{arm}_frames.json.gz')['source']
            assert source['window_sha256']==old['window_sha256'] and count==old['all_network_window_rows']
            checks['full_native_window_hash176']+=1
        truth=Path(record['truth']);co=read(truth/'port_cohorts_30s.json');events=table(truth/'port_events.csv')
        for t,frame in frames.items():
            if abs((t-lo)%30)<1e-6 or abs((t-lo)%30-30)<1e-6:
                for con in specs:
                    actual=sorted([[z[1],z[2],z[3]] for z in frame.values() if z[0]==con])
                    assert actual==sorted(co[str(t)][con]),(case,arm,t,con)
                    checks['native30_cohort_parity']+=1
        departures={(round(float(z['time_s']),1),z['vehicle']):z for z in events if z['kind']=='departure' and z['connector'] in specs and lo+1e-6<float(z['time_s'])<=hi+1e-6}
        arrivals={(round(float(z['time_s']),1),z['vehicle']):z for z in events if z['kind']=='arrival' and z['connector'] in specs and lo+1e-6<float(z['time_s'])<=hi+1e-6}
        heads={};complete=[];head_count=defaultdict(int);left=defaultdict(int);backward=[];visits=defaultdict(int)
        local_arrivals=local_departures=0
        for j in range(90):
            t=round(lo+j*5,1);end=round(t+5,1);a,b=frames[t],frames[end]
            interval_heads=defaultdict(int)
            for vid in set(a)|set(b):
                za,zb=a.get(vid),b.get(vid)
                if za and zb:assert za[0]==zb[0]
                z=za or zb;con=z[0];head=specs[con]['head_position_m']
                if za and zb and zb[1]<za[1]-.01:backward.append((t,vid,za,zb))
                if not za:
                    assert (end,vid) in arrivals and arrivals[end,vid]['connector']==con
                    checks['arrival_identity']+=1
                    local_arrivals+=1
                if not zb:
                    assert (end,vid) in departures and departures[end,vid]['connector']==con
                    checks['departure_identity']+=1
                    local_departures+=1
                crossed=(not za or za[1]<=head) and (not zb or zb[1]>head)
                if crossed:
                    assert vid not in heads
                    visits[vid]+=1
                    heads[vid]=dict(connector=con,visit=visits[vid],lower=t,upper=end,
                        before=None if za is None else za[1:],after=None if zb is None else zb[1:])
                    head_count[con]+=1
                    interval_heads[con]+=1
                if not zb:
                    ev=departures[end,vid]
                    assert abs(float(ev['lower_time_s'])-t)<1e-6 and abs(float(ev['upper_time_s'])-end)<1e-6
                    if vid in heads:
                        hh=heads.pop(vid);assert hh['connector']==con
                        nominal=(specs[con]['length_m']-head)*3.6/specs[con].get('posthead_travel_speed_kmh',specs[con]['travel_speed_kmh'])
                        complete.append(dict(case=case,arm=arm,vehicle=vid,connector=con,head=hh,
                            merge_lower=t,merge_upper=end,travel_lower=max(0.,t-hh['upper']),travel_upper=end-hh['lower'],
                            nominal_free_travel_sec=nominal,last_ramp_position_m=za[1],last_ramp_speed_kmh=za[2]))
                    else:left[con]+=1
            for con,spec in specs.items():
                head=spec['head_position_m'];old=sum(z[0]==con and z[1]>head for z in a.values());new=sum(z[0]==con and z[1]>head for z in b.values())
                dep=sum(ev['connector']==con for (tm,vid),ev in departures.items() if tm==end)
                nh=interval_heads[con]
                assert new-old==nh-dep,(prefix,con,t,old,new,nh,dep)
                checks['native5_posthead_balance']+=1
        assert not backward,backward[:2]
        assert local_arrivals==len(arrivals) and local_departures==len(departures)
        checks['repeated_vehicle_head_visits']+=sum(n-1 for n in visits.values())
        for vid,hh in heads.items():
            if vid in frames[hi]:
                censored.append(dict(case=case,arm=arm,vehicle=vid,connector=hh['connector'],kind='right',elapsed_lower=hi-hh['upper'],head=hh))
        pred=read(h.R/f'queue_dynamics178/forecast/baseline/{prefix}.json.gz')
        for con,spec in specs.items():
            pp=[z for z in pred['ramps'] if z['start']['connector_id']==con]
            states={} if not pp else {round(z['end_sec'],1):z['end'] for z in pp}
            if pp:states[lo]=pp[0]['start']
            ss=[]
            for t,frame in frames.items():
                post=[z for z in frame.values() if z[0]==con and z[1]>spec['head_position_m']]
                model=None if not pp else states[t]['downstream_travelling_veh']+states[t]['merge_ready_veh']
                row=dict(case=case,arm=arm,connector=con,time=t,posthead=len(post),slow5=sum(z[2]<5 for z in post),
                    baseline_posthead=model,mean_speed=None if not post else statistics.mean(z[2] for z in post))
                stockrows.append(row);ss.append(row)
            trips=[z for z in complete if z['connector']==con]
            avg=lambda xs:statistics.mean(xs) if xs else None
            summary.append(dict(case=case,arm=arm,connector=con,paired_trips=len(trips),left_censored_departures=left[con],right_censored_trips=sum(z['case']==case and z['arm']==arm and z['connector']==con for z in censored),
                nominal_travel_sec=(spec['length_m']-spec['head_position_m'])*3.6/spec.get('posthead_travel_speed_kmh',spec['travel_speed_kmh']),
                definitely_longer_than_nominal=sum(z['travel_lower']>z['nominal_free_travel_sec']+1e-6 for z in trips),
                definitely_shorter_than_nominal=sum(z['travel_upper']<z['nominal_free_travel_sec']-1e-6 for z in trips),
                mean_lower=avg([z['travel_lower'] for z in trips]),mean_upper=avg([z['travel_upper'] for z in trips]),
                posthead_mean_native5_left=avg([z['posthead'] for z in ss[:-1]]),posthead_mean_model5_left=None if not pp else avg([z['baseline_posthead'] for z in ss[:-1]]),
                slow5_mean_native5_left=avg([z['slow5'] for z in ss[:-1]])))
        all_sources.append(source);all_frames[prefix]=frames;triprows.extend(complete)
        with gzip.open(work/f'{prefix}_ramps.json.gz','wt',encoding='utf8') as f:json.dump(dict(fields=fields,frames=frames,source=source),f,ensure_ascii=False)
        print('EXTRACTED187',prefix,source['ramp_rows'],len(complete),'trips',flush=True)
    first=all_frames['s67_late_hold']
    for arm in ('release','hold_vsl90','release_vsl90'):
        for t in first:
            if t<2700:assert first[t]==all_frames['s67_late_'+arm][t];checks['common_initial_frames']+=1
    for path,digest in {**pins,**protocol['protected_sha256'],protocol['STOP']['path']:protocol['STOP']['sha256']}.items():assert h.sha(path)==digest,path
    h.save(work/'trips.json',dict(complete_interval_censored=triprows,right_censored=censored))
    h.save(work/'stocks.json',stockrows)
    h.save(work/'summary.json',dict(status='complete',rows=summary,checks=dict(checks),sources=all_sources,input_sha256=pins,elapsed_s=time.perf_counter()-started,
        limitations=['Head and merge time bounds each have5s resolution; paired travel bounds can be10s wide.',
          'Left/right censored cases retained separately; completed-only travel means can be selection biased.',
          'Five-second stock means sample two phases of10s meters, not continuous exact TTT.',
          'Native8 ramps; baseline prediction only connectors present in saved model receipts. No wholeOmega qualification.',
          'A travel time above nominal includes acceleration and receiving wait; it is not a direct acceleration-parameter estimate.'],
        new_forecasts=0,new_native=0,fit=False,adopted=False,full_goal='ACTIVE_NOT_QUALIFIED'))
    print('COMPLETE187',dict(checks),time.perf_counter()-started,flush=True)


def conditional_merge188():
    """Forced posthead input diagnostics, never an autonomous forecast."""
    import copy
    import math
    from evaluation.controllers import lane_plant_runtime as lpr
    from evaluation.controllers.physical_ramp_boundary import gap_acceptance_supply_vph
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import replay_congested_component as replay
    work=h.R/'conditional_merge188';assert not (work/'summary.json').exists()
    protocol=h.read(work/'protocol.json');pins={str(Path(__file__)):h.sha(__file__)}
    def read(p):pins[str(p)]=h.sha(p);return h.read(p)
    context=lpr.load_sources(h.R/'lane_state132/eval_01/manifest.json');model=context['component']
    for p in context['paths'].values():pins[str(p)]=h.sha(p)
    from evaluation.controllers import area_freeway_accounting as accounting,physical_lane_groups as lanes
    frozen=read(h.R/'spatial_context148/forecast/executed_function_sources.json')
    namespace={};exec(compile(frozen['RouteLaneRegion'],'188_frozen_lane_supply','exec'),lanes.__dict__,namespace)
    cls=namespace['RouteLaneRegion']
    cfg=model._config('FW_E',context['parameters']['by_direction']['FW_E']);net=cfg.network
    assert cfg.simulation.T_f_sec==1 and not getattr(net,'vsl_fd_two_branch',False)
    ramp='RM_C10490';con='10490';node=model.ramp_receiving_nodes[ramp]
    assert set(node)=={'critical_gap_sec','followup_sec','lane_arrival_history_sec'} and not model.ramp_lane_coupling
    methods=model.rollout.__func__.__globals__
    state=methods['TrafficState'].initial(cfg);control=methods['ControlAction'].uncontrolled(cfg)
    lengths=[p['segment_length_km'] for p in net.freeway_segment_params['FW_E']]
    net.freeway_segments_per_link=31
    # Only call the frozen supply method, not a new allocator or state update.
    net.offramp_route_inventory={'merges':{ramp:{'cell':21}}}
    receiver=cls.__new__(cls);receiver.road='FW_E';receiver.lengths=lengths
    receiver.ramp_access={ramp:0};receiver.receiving_cells=[21]
    capture=read(h.I/'heldout67_freeway_20260930/capture.json')
    trips=read(h.R/'ramp_motion187/trips.json')
    results=[];traces=[];budgets=[];checks=defaultdict(int);maximum=defaultdict(float)
    for record in capture['records']:
        arm=record['arm'];case='s67_late';pins[record['input']]=record['sha256']
        args,kw=replay.read_primitive_capture(record['input'],record['sha256'])
        spec=kw['ramp_dynamics']['ramps'][ramp];lo=capture['cutoff'];hi=lo+450
        pred=read(h.R/f'queue_dynamics178/forecast/baseline/{case}_{arm}.json.gz')
        rr=[z for z in pred['ramps'] if z['start']['connector_id']==con];assert len(rr)==450
        main=read(h.R/f'blocking176/{arm}_frames.json.gz');ix={key:i for i,key in enumerate(main['fields'])}
        native=read(h.R/f'ramp_motion187/{case}_{arm}_ramps.json.gz')['frames']
        native_head=[z['head'] for z in trips['complete_interval_censored'] if z['case']==case and z['arm']==arm and z['connector']==con]
        native_head += [z['head'] for z in trips['right_censored'] if z['case']==case and z['arm']==arm and z['connector']==con]
        head={kind:[0.]*450 for kind in ('first_bucket','last_bucket')}
        for hh in native_head:
            first=round(hh['lower']-lo);last=round(hh['upper']-lo)-1
            assert last-first==4 and 0<=first<=last<450
            head['first_bucket'][first]+=1;head['last_bucket'][last]+=1
        predicted_rates=[z['receiving_budget_veh'] for z in rr];observed_rates=[]
        for sec,step in enumerate(args[1]):
            t=round(lo+sec,1);obs_t=round(lo+(sec//5)*5,1)
            frame=main['frames'][str(obs_t)]
            nn=[0.]*31;vv=[0.]*31
            for row in frame.values():
                i=int(row[ix['cell']]);nn[i]+=1;vv[i]+=row[ix['speed']]
            state.time_sec=t
            state.freeway_density['FW_E']=[nn[i]/(lengths[i]*net.freeway_segment_lanes['FW_E'][i]) for i in range(31)]
            state.freeway_speed['FW_E']=[vv[i]/nn[i] if nn[i] else net.freeway_segment_params['FW_E'][i]['v_free'] for i in range(31)]
            for r in net.ramps:
                cap=net.ramp_capacity_veh_h[r];state.ramp_queue[r]=math.nextafter(cap/3600.,math.inf);control.ramp_metering[r]=cap
            if 'vsl_commands' in step:control.vsl.update(step['vsl_commands'])
            net.off_ramp_split_ratio={o:float(step['off_split_ratio'][o]) for o in net.off_ramps}
            demand=methods['DemandStep']({'FW_E':float(step['source_demand_vph']['FW_E'])},{},{})
            canonical=accounting._mn.compute_ramp_release_flows(state,control,demand,cfg,include_current_arrivals=False)[0][ramp]
            right=sum(row[ix['cell']]==21 and row[ix['lane']]==1 for row in frame.values())
            receiver.stocks={21:[{'observed':right}]}
            shared=receiver.ramp_supply(ramp,cfg)
            split=sum(net.off_ramp_split_ratio[o] for o in net.off_ramps if net.off_ramp_segment_index[o]==20)
            conflict=state.freeway_density['FW_E'][20]*state.freeway_speed['FW_E'][20]*(1-split)
            gap=gap_acceptance_supply_vph(conflict,node['critical_gap_sec'],node['followup_sec'])
            value=min(canonical,shared,gap)/3600.;observed_rates.append(value)
            budgets.append(dict(arm=arm,time=t,observed_at=obs_t,canonical=canonical/3600.,shared=shared/3600.,gap=gap/3600.,
                observed_state_budget=value,autonomous_budget=predicted_rates[sec],right_n=right,conflict_vph=conflict))
        assert len(observed_rates)==450
        def run(heads,rates):
            nominal=spec.get('posthead_travel_speed_kmh',spec['travel_speed_kmh'])/3.6
            travel=(spec['length_m']-spec['head_position_m'])/nominal
            queue=[];ready=0.
            for pos,speed,lane in spec['initial_cohorts']:
                if pos<=spec['head_position_m']:continue
                if pos>=spec['length_m']:ready+=1.
                else:queue.append((lo+(spec['length_m']-pos)/nominal,1.))
            start=sum(n for _,n in queue)+ready;entered=departed=0.;out=[]
            capacity=(spec['length_m']-spec['head_position_m'])*spec['lanes']/spec['spacing_m']
            for i,(hh,budget) in enumerate(zip(heads,rates)):
                end=lo+i+1
                before=ready+sum(n for _,n in queue)
                ready+=sum(n for eta,n in queue if eta<=end)
                queue=[(eta,n) for eta,n in queue if eta>end]
                merged=min(ready,budget);ready-=merged;departed+=merged
                if hh:queue.append((end+travel,hh))
                entered+=hh;post=ready+sum(n for _,n in queue)
                residual=start+entered-departed-post
                maximum['mass']=max(maximum['mass'],abs(residual));assert abs(residual)<1e-9
                out.append(dict(time=round(end,1),post=post,ready=ready,travelling=post-ready,merge=merged,
                    cumulative_merge=departed,head=hh,start_post=before,storage_excess=max(0.,post-capacity)))
            return out
        tests=[('saved_head_saved_budget',[z['head_service_veh'] for z in rr],predicted_rates)]
        tests += [(timing+'_'+label,heads,rates) for timing,heads in head.items() for label,rates in [('saved_budget',predicted_rates),('observed_state_budget',observed_rates)]]
        for label,heads,rates in tests:
            rows=run(heads,rates)
            if label=='saved_head_saved_budget':
                for actual,expected in zip(rows,rr):
                    for key,v in [('post',expected['end']['downstream_travelling_veh']+expected['end']['merge_ready_veh']),('merge',expected['accepted_merge_veh']),('ready',expected['end']['merge_ready_veh'])]:
                        error=abs(actual[key]-v);maximum['saved_parity']=max(maximum['saved_parity'],error);assert error<1e-9
                        checks['saved_trace_parity']+=1
            states={z['time']:z['post'] for z in rows};states[lo]=rows[0]['start_post']
            times=[round(lo+5*j,1) for j in range(90)]
            observed_post=[sum(z[0]==con and z[1]>spec['head_position_m'] for z in native[str(t)].values()) for t in times]
            result=dict(arm=arm,mode=label,head_total=sum(heads),merge_total=rows[-1]['cumulative_merge'],post_end=rows[-1]['post'],
                mean_post5=sum(states[t] for t in times)/90,actual_mean_post5=sum(observed_post)/90,
                max_storage_excess=max(z['storage_excess'] for z in rows),prefixes=[])
            for horizon in (30,150,450):
                end=round(lo+horizon,1);row=rows[horizon-1]
                actual_post=sum(z[0]==con and z[1]>spec['head_position_m'] for z in native[str(end)].values())
                result['prefixes'].append(dict(horizon=horizon,post=row['post'],merge=row['cumulative_merge'],actual_post=actual_post))
            results.append(result);traces.append(dict(arm=arm,mode=label,rows=rows))
        print('CONDITIONAL188',arm,[dict(mode=z['mode'],mean=z['mean_post5'],actual=z['actual_mean_post5']) for z in results if z['arm']==arm],flush=True)
    for path,digest in {**pins,**protocol['protected_sha256'],protocol['STOP']['path']:protocol['STOP']['sha256']}.items():assert h.sha(path)==digest,path
    h.save(work/'traces.json',traces);h.save(work/'budgets.json',budgets)
    h.save(work/'summary.json',dict(status='complete',rows=results,checks=dict(checks),max_errors=dict(maximum),input_sha256=pins,
        limits=['All native head/state conditioning uses future labels for attribution only, not prediction inputs.',
          'First/last1s head buckets reflect5s timing uncertainty; not exact native crossing times.',
          'Five-second current states are held for5s; receivers do not react to counterfactual merges.',
          'Forced head input bypasses head-service model; any posthead storage excess is reported, never clipped.',
          'Nominal distance travel remains unchanged; no acceleration or microscopic gap model is validated.'],
        autonomous_forecasts=0,fit=False,new_native=0,adopted=False,qualified=False,full_goal='ACTIVE_NOT_QUALIFIED'))
    print('VERIFIED188',dict(checks),dict(maximum),flush=True)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--observed-supply184',action='store_true')
    parser.add_argument('--lane-budget185',action='store_true')
    parser.add_argument('--ramp-posthead186',action='store_true')
    parser.add_argument('--ramp-motion187',action='store_true')
    parser.add_argument('--conditional-merge188',action='store_true')
    args=parser.parse_args()
    assert sum((args.observed_supply184,args.lane_budget185,args.ramp_posthead186,args.ramp_motion187,args.conditional_merge188))<=1
    if args.conditional_merge188:conditional_merge188()
    elif args.ramp_motion187:ramp_motion187()
    elif args.ramp_posthead186:ramp_posthead186()
    elif args.lane_budget185:lane_budget185()
    elif args.observed_supply184:observed_supply184()
    else:main()
