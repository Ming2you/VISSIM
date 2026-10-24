"""Matched VSL continuation through the existing conserved diagnostic runner."""
from pathlib import Path
from collections import defaultdict,Counter
import bisect,copy,gzip,hashlib,json,math,sys,subprocess,time
import vsl_strength as s
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.lane_group_response_20260919 import extract as lanes
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.route_access_observer import geometry as routes_from
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.extract_observations import Observer,PortObserver
c=s.c;B=s.B;K=s.K;ROOT=s.ROOT;H=B.parent
O=B/'vsl_restart_v1';START=2550


def frames(path,proof):
    digest=hashlib.sha256();stamp=path.stat();t=None;current={}
    with path.open('rb') as f:
        for line in f:
            digest.update(line)
            if not line[:1].isdigit():continue
            a=line.rstrip(b'\r\n').split(b';')
            if len(a)==21 and not a[-1]:a.pop()
            assert len(a)==20
            sec=float(a[0]);assert sec.is_integer();sec=int(sec)
            if t is not None and sec!=t:
                assert sec==t+1;yield t,current;current={}
            t=sec;vid=int(a[1]);assert vid not in current;current[vid]=a
    yield t,current
    assert (stamp.st_size,stamp.st_mtime_ns)==(path.stat().st_size,path.stat().st_mtime_ns)
    proof.update(sha256=digest.hexdigest(),bytes=stamp.st_size)


def prepare():
    from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import urban_route_transport as u
    bank=K/'route_state_native_v1/vsl_s23';source=bank/'run_retry1/vissim_eval/baseline_001.fzp'
    network=bank/'source/baseline.inpx';geometry=copy.deepcopy(c.load(H/'controller_response_s23_v1/none/geometry.json'))
    assert all(len([x for x in geometry['cells'] if x['road']==road])==21 for road in ('FW_E','FW_W'))
    proof_expected=c.load(bank/'analysis/result.json');assert proof_expected['passed']
    folder=O/'observations';folder.mkdir(exist_ok=False)
    s.save(folder/'geometry.json',geometry)
    errors=c.load(s.O/'both100_errors.json')
    removals=[v for f in errors for v in f['events'] if v['kind']=='lane_change_removal']
    observer=Observer(geometry,removals,interval_sec=1);ports=PortObserver(geometry,interval_sec=1)
    lane_geometry=copy.deepcopy(c.load(H/'lane_group_response_20260919/observations_v1/s23.json')['geometry'])
    widths=lane_geometry['widths'];split={i for i,w in enumerate(widths) if len(w)>1}
    routes,_=routes_from(network);branch=next(x['chain_pos_m'] for x in geometry['boundaries'] if x['connector']==10643)
    on={p['connector']:p for p in geometry['boundaries'] if p['kind']=='ramp'}
    off={str(p['connector']):p for p in geometry['boundaries'] if p['kind']=='offramp' and p['road']=='FW_E'}
    origins={};snapshots={};details={};exposure=Counter();changes=Counter();previous={};proof={}
    for sec,raw in frames(source,proof):
        basic={vid:(int(a[2]),int(a[3]),float(a[4]),float(a[6])) for vid,a in raw.items()}
        observer.advance(sec,basic);ports.advance(sec,basic)
        if sec>START:continue  # Future records populate scoring tables only.
        for vid,r in basic.items():
            if r[0] in on:origins[vid]=r[0]
        if sec<START-150:continue
        located={};rows=[];current=[]
        for vid,r in basic.items():
            loc=observer.locate(r)
            road=loc[0] if loc else None
            current.append(dict(vehicle=vid,link=r[0],lane=r[1],position_m=r[2],speed_kmh=r[3],road=road,origin=origins.get(vid)))
            if road!='FW_E':continue
            cell,x=loc[1:];g=lanes.group(cell,r[1],split);located[vid]=(r[0],cell,g)
            if sec>START-150:
                exposure[cell,g]+=1
                old=previous.get(vid)
                if old and old[:2]==(r[0],cell) and old[2]!=g:changes[cell,old[2],g]+=1
            a=raw[vid];num=lambda z:int(z) if z else None
            rd,rn,kind=num(a[11]),num(a[12]),a[13].decode('ascii') or None
            path=routes.get((rd,rn)) if kind and kind.lower()=='static' else None
            rows.append(dict(vehicle=vid,link=r[0],lane=r[1],position_m=r[2],chain_position_m=x,cell=cell,group=g,
                speed_kmh=r[3],length_m=float(a[10]),route_decision=rd,route_number=rn,route_type=kind,assigned_path=path,
                pre_off10643=x<branch,off10643_intent=(10643 in path) if path and x<branch else None,origin=origins.get(vid)))
        if sec in (START-150,START):snapshots[str(sec)]=rows;details[str(sec)]=current
        previous=located
    assert observer.sec==3000 and proof['sha256']==proof_expected['new_fzp_sha256']
    for name,rows in [('cells_30s',observer.cells),('flows_30s',observer.flows),('boundaries_30s',observer.boundary_rows),('ports_30s',ports.rows),('port_events',ports.events)]:s.table(folder/(name+'.csv'),rows)
    s.save(folder/'port_cohorts_30s.json',ports.snapshots)
    current=snapshots[str(START)];groups=[];rates=[]
    for cell,ws in enumerate(widths):
        selected=[r for r in current if r['cell']==cell]
        target=next(r for r in observer.cells if r['time_s']==START and r['road']=='FW_E' and r['cell']==cell)
        assert len(selected)==target['n_veh']
        groups.append([dict(n_veh=sum(r['group']==g for r in selected),
            v_kmh=sum(r['speed_kmh'] for r in selected if r['group']==g)/sum(r['group']==g for r in selected) if any(r['group']==g for r in selected) else None) for g in range(len(ws))])
        rates.append([[changes[cell,g,h]/exposure[cell,g] if exposure[cell,g] else 0. for h in range(len(ws))] for g in range(len(ws))])
    lane=dict(geometry=lane_geometry,cutoffs={str(START):dict(initial_groups=groups,exchange_rates_per_sec=rates,observation_end_s=START,history_start_s=START-150)})
    counts={};eligible={}
    for t,rows in snapshots.items():
        counts[t]={p['id']:[sum(r['cell']==p['to_cell'] and r['group']==g and r['origin']==p['connector'] for r in rows) for g in range(len(widths[p['to_cell']]))] for p in on.values() if p['road']=='FW_E'}
        eligible[t]={key:[sum(r['cell']==p['from_cell'] and r['group']==g and r['chain_position_m']<p['chain_pos_m'] for r in rows) for g in range(len(widths[p['from_cell']]))] for key,p in off.items()}
    pre={}
    for cell in range(9):
        for group in range(len(widths[cell])):
            rs=[r for r in current if r['cell']==cell and r['group']==group and r['pre_off10643']]
            pre[f'{cell}:{group}']=dict(n=len(rs),known_off=sum(r['off10643_intent'] is True for r in rs),known_through=sum(r['off10643_intent'] is False for r in rs),unknown=sum(r['off10643_intent'] is None for r in rs))
    s.save(O/'lane.json',lane);s.save(O/'origin.json',dict(counts=counts,eligible_before_off=eligible))
    s.save(O/'intent.json',dict(information_cutoff_s=START,future_route_observations_used=False,current_vehicles=current,current_pre_branch_groups=pre))
    s.save(O/'initial.json',details[str(START)])
    s.save(O/'commands.json',dict(dsd_ids=list(range(51,59)),candidate_bank={'none':dict(green=[],vsl=[100]*3),'vsl':dict(green=[],vsl=[80]*3)},
        baseline_label='none means hold existing100, not no-control',previous_actual_vsl=100,previous_actual_since_s=2400))
    relative=lambda p:str(p.relative_to(ROOT))
    context=dict(cutoff_s=START,seed=23,future_traffic_inputs=False,bank=relative(bank),data=relative(folder),
        **{key:relative(O/(key+'.json')) for key in ('lane','origin','intent','commands','initial')},refined_initial=relative(O/'refined_initial.json'))
    s.save(O/'context.json',context)
    source_paths=[Path(__file__),source,network,bank/'analysis/result.json',O/'context.json']
    s.save(O/'preparation.json',dict(native=proof,source_pins={relative(p):s.sha(p) for p in source_paths},
        current_s=START,history_start_s=START-150,initial_mainline_veh={road:sum(r['road']==road for r in details[str(START)]) for road in ('FW_E','FW_W')},
        original_geometry=True,no_future_in_restart_inputs=True,scoring_tables_extend_to3000=True,qualified=False))
    print('Prepared matched2550 state from verified both100 native',flush=True)


def run():
    spec=copy.deepcopy(c.load(s.v.O/'vr_hadi_fd_cap_r2_validation.json'))
    spec.update(name='restart_both2550',output_group=O.name,arms=['none','vsl'],replay_context=str((O/'context.json').relative_to(ROOT)))
    path=O/'restart_both2550.json';s.save(path,spec)
    with (O/'restart_process.log').open('x',encoding='utf-8') as log:
        subprocess.run([sys.executable,'-B','-X','utf8',str(B/'run.py'),'refined_guard1',str(path)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    print('Matched2550 forecasts complete',flush=True)


def analyze():
    """Native future samples are labels, never passed back to the forecasts."""
    prior=c.load(s.O/'native_comparison.json')['native_pins']
    sources={'none':K/'route_state_native_v1/vsl_s23/run_retry1/vissim_eval/baseline_001.fzp',
             'vsl':s.O/'both80/run/vissim_eval/baseline_001.fzp'}
    expected={ROOT/p:digest for p,digest in prior.items()}
    geom=c.G;widths=c.load(O/'refined_initial.json')['widths'];chain={p['link']:p['offset_m'] for p in geom['chains']['FW_E']}
    bounds=geom['bounds']['FW_E'];ports={p['connector']:('on' if p['kind']=='ramp' else 'off') for p in geom['boundaries'] if p['road']=='FW_E' and p['kind'] in ('ramp','offramp')}
    actual={};native_costs={};native_pins={}
    for arm,path in sources.items():
        digest=hashlib.sha256();stock=defaultdict(Counter);groups=defaultdict(lambda:defaultdict(lambda:[0,0.]));stamp=path.stat()
        with path.open('rb') as f:
            for line in f:
                digest.update(line)
                if not line[:1].isdigit():continue
                t=float(line.split(b';',1)[0])
                if not START<=t<=3000 or t%5:continue
                a=line.rstrip(b'\r\n').split(b';');t=int(t);link=int(a[2]);pos=float(a[4]);lane=int(a[3])
                if link in chain:
                    x=chain[link]+pos
                    if x>=0:
                        # Match canonical Observer.locate: last-cell stock
                        # includes the short physical terminal-link overhang.
                        # Keep its cost separate for the geometric comparison.
                        i=min(len(bounds)-2,bisect.bisect_right(bounds,x)-1);g=next(g for g in range(len(widths[i])) if lane<=sum(widths[i][:g+1])+1e-8)
                        groups[t][i,g][0]+=1;groups[t][i,g][1]+=float(a[6]);stock[t]['mainline']+=1
                        if x>=bounds[-1]:stock[t]['terminal_overhang']+=1
                if link in ports:stock[t][ports[link]]+=1;stock[t][str(link)]+=1
        assert digest.hexdigest()==expected[path] and (stamp.st_size,stamp.st_mtime_ns)==(path.stat().st_size,path.stat().st_mtime_ns)
        assert set(stock)==set(range(START,3001,5))
        actual[arm]=groups;native_costs[arm]=stock;native_pins[str(path.relative_to(ROOT))]=digest.hexdigest()
    assert actual['none'][START]==actual['vsl'][START] and native_costs['none'][START]==native_costs['vsl'][START]
    initial=c.load(O/'refined_initial.json')['initial_groups']
    for i,gs in enumerate(initial):
        for g,row in enumerate(gs):
            n,m=actual['none'][START][i,g];assert n==row['n_veh'],('Initial group mismatch',i,g,n,row)
            if n:assert abs(m/n-row['v_kmh'])<1e-9
    preds={arm:s.f.load_prediction(O/'restart_both2550'/f'refined_guard1_{arm}.json') for arm in ('none','vsl')}
    old={arm:s.f.load_prediction(s.O/('vs_both100' if arm=='none' else 'vs_both80')/'refined_guard1_vsl.json') for arm in ('none','vsl')}
    for arm in preds:assert c.screen(preds[arm])['passed']
    def cost(pred,end):
        return dict(mainline=sum(r['n_veh']*5/3600 for r in pred['lane_groups']['FW_E'] if START<r['time_s']<=end and r['time_s']%5==0),
            on=sum(r['end']['connector_veh']*5/3600 for r in pred['ramps'] if r['road']=='FW_E' and START<r['end_sec']<=end and r['end_sec']%5==0),
            off=sum(r['n_veh']*5/3600 for r in pred['ports'] if r['road']=='FW_E' and START<r['time_s']<=end and r['time_s']%5==0))
    def delta(values):
        out={k:values['vsl'][k]-values['none'][k] for k in ('mainline','on','off')};out['total']=sum(out.values());return out
    costs=[];scores=[];port_differences=[]
    for end in (2580,2700,2850,3000):
        truth={a:{kind:sum(row[kind]*5/3600 for t,row in native_costs[a].items() if START<t<=end) for kind in ('mainline','on','off')} for a in preds}
        values={a:cost(preds[a],end) for a in preds}
        geometric=copy.deepcopy(truth)
        for arm in preds:geometric[arm]['mainline']-=sum(row['terminal_overhang']*5/3600 for t,row in native_costs[arm].items() if START<t<=end)
        row=dict(start=START,end=end,actual=delta(truth),actual_geometric=delta(geometric),restart=delta(values),actual_absolute=truth,restart_absolute=values)
        if end<=2850:row['without_restart']=delta({a:cost(old[a],end) for a in preds})
        costs.append(row)
        for connector,kind in ports.items():
            if kind!='off':continue
            key=str(connector);truth_cost={a:sum(r[key]*5/3600 for t,r in native_costs[a].items() if START<t<=end) for a in preds}
            pred_rows={a:[r for r in p['ports'] if r['road']=='FW_E' and r['connector']==key and START<r['time_s']<=end and r['time_s']%5==0] for a,p in preds.items()}
            forecast_cost={a:sum(r['n_veh']*5/3600 for r in rs) for a,rs in pred_rows.items()}
            entries={a:next(r for r in rs if r['time_s']==end) for a,rs in pred_rows.items()}
            port_differences.append(dict(end=end,connector=connector,actual_delta_ttt=truth_cost['vsl']-truth_cost['none'],
                predicted_delta_ttt=forecast_cost['vsl']-forecast_cost['none'],
                actual_end_delta_n=native_costs['vsl'][end][key]-native_costs['none'][end][key],
                predicted_end_delta_n=entries['vsl']['n_veh']-entries['none']['n_veh'],
                predicted_delta_admissions=entries['vsl']['admitted_veh']-entries['none']['admitted_veh'],
                predicted_delta_departures=entries['vsl']['departed_veh']-entries['none']['departed_veh']))
        for label,source in [('restart',preds)]+([('without_restart',old)] if end<=2850 else []):
            for arm,p in source.items():
                errors=[[],[]]
                for r in p['lane_groups']['FW_E']:
                    t=r['time_s']
                    if not START<t<=end or t%5:continue
                    n,m=actual[arm][int(t)][r['cell'],r['group']];errors[0].append(r['n_veh']-n)
                    if n:errors[1].append(r['v_kmh']-m/n)
                rmse=lambda xs:math.sqrt(sum(x*x for x in xs)/len(xs))
                scores.append(dict(case=label,arm=arm,end=end,stock_rmse=rmse(errors[0]),speed_rmse=rmse(errors[1]),speed_samples=len(errors[1])))
    gate=c.load(O/'default_and_native_gate.json')
    for key,x in gate['actual_marginal'].items():assert abs(costs[-1]['actual_geometric'][key]-x)<1e-9
    for field in ('cells','flows','ramps','ports'):
        assert [r for r in preds['none'][field] if r['road']=='FW_W']==[r for r in preds['vsl'][field] if r['road']=='FW_W']
    s.save(O/'port_differences.json',port_differences)
    s.save(O/'native_common5s.json',dict(source_pins=native_pins,stocks=native_costs,
        groups={a:{t:[dict(cell=i,group=g,n=v[0],moment=v[1]) for (i,g),v in gs.items()] for t,gs in times.items()} for a,times in actual.items()}))
    s.save(O/'analysis.json',dict(costs=costs,scores=scores,numerics={a:c.screen(p) for a,p in preds.items()},initial_groups_exact=True,
        native_pins=native_pins,window=[START,3000],future_inputs=False,coefficients_fitted=False,qualified=False,production_adopted=False,
        scope='Existing Observer east mainline (nonnegative position, terminal overhang in last cell)+4on+4off; baseline holds100, intervention80. Also report strict geometric cost separately. Not NC comparison or full Omega.',
        terminal_overhang_initial_veh=native_costs['none'][START]['terminal_overhang']))
    print(json.dumps(dict(costs=[{k:v for k,v in r.items() if k not in ('actual_absolute','restart_absolute')} for r in costs],scores=scores),indent=2))


if __name__=='__main__':{'prepare':prepare,'run':run,'analyze':analyze}[sys.argv[1]]()
