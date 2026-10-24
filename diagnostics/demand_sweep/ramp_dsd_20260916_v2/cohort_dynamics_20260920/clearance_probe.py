"""Conditional post-head replay to test a moving-space gap hypothesis.

Uses actual future local mainline states and head crossings ONLY to identify
the receiving closure. Not a causal450s forecast or a controller implementation.
No reward fitting: select on seed13 no-control absolute queue/exit observations.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,MODEL
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.canonical_harness import DelayedPort
from evaluation.controllers.physical_ramp_boundary import gap_acceptance_supply_vph
from collections import Counter
from bisect import bisect_right
import statistics,math,hashlib
import argparse,csv,heapq

HERE=Path(__file__).resolve().parent
LOCAL=H/'merge_drain_response_20260919/local_native_v1'


def prepare(seed,arm,folder,starts,local_folder=LOCAL):
    data=e.ObservationData(folder);cohorts=data.port_cohorts
    heads=Counter(int(float(r['time_s'])) for r in e.rows(folder/'head_crossings.csv') if r['ramp']=='10484')
    exits=Counter(int(float(r['time_s'])) for r in e.rows(folder/'port_events.csv') if r['connector']=='10484' and r['kind']=='departure')
    stocks={int(r['time_s']):int(r['posthead_n']) for r in e.rows(folder/'head_stock_1s.csv') if r['ramp']=='10484'}
    loc={int(r['time_s']):r for r in e.rows(local_folder/f'{seed}_{arm}/merge_lane_1s.csv') if r['lane']=='1'}
    crossing=sorted(float(r['time_s']) for r in e.rows(LOCAL/f'{seed}_{arm}/mainline_crossings.csv') if r['lane']=='1')
    config=e.load(HERE/'port_origin_split_v1/config.json')
    # Read the current physical buffer spec once; the isolated post-head part
    # uses exactly the same geometry/travel/spacing and initial positions.
    model=e.load_base_model(data.geometry,HERE/'port_origin_split_v1/config.json')
    origins=e.load(HERE/f'port_positions_v1/s{seed}.json')
    w=e.window(data,model,900,'history_forecast',e.load(MODEL/'port_profile.json'),lambda _: ({},{}),port_origin_counts=origins['counts'])
    spec=w['ramp_dynamics']['ramps']['RM_C10484'];head=spec['head_position_m']
    length=spec['length_m']-head;travel=spec.get('posthead_travel_speed_kmh',spec['travel_speed_kmh'])
    result=[]
    for start in starts:
        init=[[max(0.,p-head),v,lane] for p,v,lane in cohorts[str(start)]['10484'] if p>head]
        assert len(init)==stocks[start]
        n=len(init);cum=0;trace=[];inputs=[]
        for t in range(start,start+450):
            n+=heads[t+1]-exits[t+1];cum+=exits[t+1]
            assert n==stocks[t+1],(seed,arm,t,n,stocks[t+1])
            row=loc[t];population=int(row['n'])
            speed=float(row['speed_sum'])/population if population else 0.
            q=(bisect_right(crossing,t)-bisect_right(crossing,t-30))*120.
            inputs.append({'q':q,'v':speed,'local_n':population,'head':heads[t+1]})
            trace.append({'time_s':t+1,'n':n,'cumulative_exits':cum})
        observed={'ttt':sum(r['n'] for r in trace)/3600,'end_n':n,'exits':cum,'trace':trace}
        result.append({'seed':seed,'arm':arm,'start':start,'initial':init,'length':length,'speed':travel,
            'capacity':length/spec['spacing_m'],'inputs':inputs,'observed':observed,
            'crossings':[t for t in crossing if start-100<t<start+550]})
    return result


def extract_local50():
    from diagnostics.demand_sweep.ramp_dsd_20260916_v2.state_exchange_20260920.analyze_dispersion import records
    out=HERE/'clearance_local50_v1';out.mkdir(exist_ok=False)
    cases=[(13,'none',H/'rules_4500_v1/run_none',4500),
        (23,'none',H/'rules_4500_s23_v1/run_none',2850),
        (23,'rm_ramp',H/'response_late_s23_v1/run_rm_ramp',2850),
        (33,'none',H/'state_response_20260919/native_s33_v1/run_none',2850),
        (33,'rm_ramp',H/'state_response_20260919/native_s33_v1/run_rm_ramp',2850)]
    for seed,arm,run,end in cases:
        evidence=e.load(LOCAL/f'{seed}_{arm}/evidence.json');point=evidence['merge_point']['to_pos_m'];link=evidence['merge_point']['to_link']
        start=900 if seed==13 else 2400;moments={t:[0,0.,0,0] for t in range(start,end+1)}
        path=run/'vissim_eval/baseline_001.fzp';before=path.stat();last=None
        for p in records(path):
            sec=int(float(p[0]))
            if sec>end:break
            last=sec
            if sec<start or int(p[2])!=link or int(p[3])!=1:continue
            pos=float(p[4]);v=float(p[6])
            if abs(pos-point)<=25.:
                r=moments[sec];r[0]+=1;r[1]+=v;r[2]+=v<5;r[3]+=v<30
        assert last==end
        after=path.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
        folder=out/f'{seed}_{arm}';folder.mkdir()
        with (folder/'merge_lane_1s.csv').open('x',newline='',encoding='utf-8') as stream:
            writer=csv.writer(stream);writer.writerow(['time_s','lane','n','speed_sum','below5','below30'])
            writer.writerows([t,1,*r] for t,r in moments.items())
        e.save(folder/'evidence.json',{'source':str(path.relative_to(e.ROOT)),'bytes':before.st_size,'mtime_ns':before.st_mtime_ns,
            'existing_source_sha256':evidence['file_sha256'],'scope':'Lane1,25m before/after physical10484 merge; no new native run',
            'point_m':point,'link':link,'start_s':start,'end_s':end})
        print('LOCAL50',seed,arm,len(moments),flush=True)


def supply(q,v,n,tc,tf,clearance):
    if clearance and n:
        if v<=0:return 0.
        extra=clearance/(v/3.6)
    else:extra=0.
    return min(1800.,gap_acceptance_supply_vph(q,tc+extra,tf+extra))


def replay(case,parameters,keep=False):
    tc,tf,clearance=parameters
    buf=DelayedPort(case['capacity'],case['length'],case['speed'],case['initial'],case['start'],interval_service=True)
    errors=[];trace=[];max_residual=0.;overstorage=False
    for i,row in enumerate(case['inputs']):
        t=case['start']+i;rate=supply(row['q'],row['v'],row['local_n'],tc,tf,clearance)
        buf.release(t,1.,rate)
        if buf.stock+row['head']>buf.capacity+1e-7:
            overstorage=True;break
        buf.accept(t+1,row['head'])
        obs=case['observed']['trace'][i]
        errors.append(((buf.stock-obs['n'])/5.)**2+((buf.departed-obs['cumulative_exits'])/10.)**2)
        residual=buf.stock-buf.initial-buf.admitted+buf.departed
        max_residual=max(max_residual,abs(residual));assert max_residual<1e-7
        if keep:trace.append({'time_s':t+1,'n':buf.stock,'observed_n':obs['n'],
            'cumulative_exits':buf.departed,'observed_cumulative_exits':obs['cumulative_exits'],'supply_vph':rate})
    predicted={'ttt':buf.residence_veh_h,'end_n':buf.stock,'exits':buf.departed}
    loss=(statistics.mean(errors)+((predicted['ttt']-case['observed']['ttt'])/.25)**2) if not overstorage else None
    return {'loss':loss,'overstorage':overstorage,'predicted':predicted,
        'observed':{k:v for k,v in case['observed'].items() if k!='trace'},'trace':trace,'conservation_max':max_residual}


def replay_gaps(case,parameters,keep=False):
    """Diagnostic discrete gap opportunities; actual future conflicts are known.

    One vehicle per opportunity, global opportunity spacing >= followup >=2s.
    Fixed physical post-head travel, no resets or discarded queued vehicles.
    """
    tc,tf=parameters;assert tc>=tf>=2.
    start=case['start'];end=start+450;events=[];n=len(case['initial']);initial=n
    ready=arrived=departed=0.;ttt=0.;clock=start;trace=[];errors=[];max_residual=0.
    for p,v,lane in case['initial']:
        heapq.heappush(events,(start+max(0.,case['length']-p)*3.6/case['speed'],0,'ready'))
    for i,r in enumerate(case['inputs']):
        for _ in range(r['head']):heapq.heappush(events,(start+i+1,1,'head'))
        heapq.heappush(events,(start+i+1,3,'sample'))
    last_slot=None;slots=0
    for a,b in zip(case['crossings'],case['crossings'][1:]):
        k=0
        while a+tc+k*tf<=b:
            slot=a+tc+k*tf;k+=1
            if not start<slot<=end:continue
            if last_slot is not None:assert slot-last_slot>=tf-1e-8
            last_slot=slot;slots+=1;heapq.heappush(events,(slot,2,'service'))
    overflow=False
    while events:
        t,_,kind=heapq.heappop(events)
        if t>end:break
        ttt+=n*(t-clock)/3600;clock=t
        if kind=='ready':ready+=1
        elif kind=='head':
            arrived+=1;n+=1
            if n>case['capacity']+1e-7:overflow=True;break
            heapq.heappush(events,(t+case['length']*3.6/case['speed'],0,'ready'))
        elif kind=='service':
            amount=min(ready,1.);ready-=amount;n-=amount;departed+=amount
        else:
            obs=case['observed']['trace'][int(t-start)-1]
            errors.append(((n-obs['n'])/5.)**2+((departed-obs['cumulative_exits'])/10.)**2)
            if keep:trace.append({'time_s':t,'n':n,'observed_n':obs['n'],
                'cumulative_exits':departed,'observed_cumulative_exits':obs['cumulative_exits']})
        max_residual=max(max_residual,abs(n-initial-arrived+departed));assert max_residual<1e-8
    loss=statistics.mean(errors)+((ttt-case['observed']['ttt'])/.25)**2 if not overflow else None
    return {'loss':loss,'overstorage':overflow,'predicted':{'ttt':ttt,'end_n':n,'exits':departed},
        'observed':{k:v for k,v in case['observed'].items() if k!='trace'},'trace':trace,
        'conservation_max':max_residual,'service_opportunities':slots}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--extract-local50',action='store_true')
    parser.add_argument('--local50',action='store_true');parser.add_argument('--gap-timing',action='store_true');args=parser.parse_args()
    if args.extract_local50:extract_local50();return
    out=HERE/('gap_timing_conditional_v1' if args.gap_timing else 'clearance_conditional_local50_v1' if args.local50 else 'clearance_conditional_v1');out.mkdir(exist_ok=False)
    local_folder=HERE/'clearance_local50_v1' if args.local50 else LOCAL
    protocol={'status':'EXPLORATORY_CONDITIONAL_NOT_QUALIFIED','training':'Seed13 NC only; no treatment benefit in selection',
        'validation':'Previously inspected23/33 NC/RM pairs; not a fresh holdout',
        'inputs':f'Actual future head crossings +1s local{50 if args.local50 else 200}m lane1 N/speed and trailing30s crossing rate',
        'formula':'tc_eff=tc+ell/(v/3.6), tf_eff=tf+ell/(v/3.6); zero service if occupied lane stands still; no extra clearance if locally empty',
        'interpretation':'Effective space-clearing hypothesis, not measured vehicle length or an established validated law',
        'fixed':'Current post-head geometry, travel speed, finite storage, waiting cost; upper service1800veh/h',
        'no_future_stock_resets':True,'native_runs_started':0,'core_changes':False}
    if args.gap_timing:
        protocol.update(inputs='Actual future head crossings and mainline lane1 point crossings; fixed travel speed.',
            formula='One merge opportunity at each preceding mainline crossing +tc+k*tf before the next conflict, unused opportunities expire.',
            interpretation='Discrete gap scheduling diagnosis; current native1s front crossings interpolate time and do not resolve exact car-following gap acceptance.')
    e.save(out/'protocol.json',protocol)
    train=prepare(13,'none',H/'controller_response_4500_v1/none',[900,1350,1800,2250,2700,3150,3600,4050],local_folder)
    train_results=[]
    candidates=([(tc,tf) for tf in [2.,2.5,3.] for tc in [tf,tf+.5,tf+1.]] if args.gap_timing else
        [(tc,tf,ell) for tf in [1.5,2.,2.5] for tc in [tf,tf+.5,tf+1.] for ell in [0.,3.,6.,9.]])
    runner=replay_gaps if args.gap_timing else replay
    for parameters in candidates:
        rows=[runner(c,parameters) for c in train]
        loss=statistics.mean(r['loss'] for r in rows) if all(r['loss'] is not None for r in rows) else None
        train_results.append({'parameters':parameters,'loss':loss,'cases':rows})
    eligible=[r for r in train_results if r['loss'] is not None]
    if not eligible:raise ValueError('No candidate passed finite storage')
    selected=min(eligible,key=lambda r:r['loss'])
    positive=[r for r in eligible if len(r['parameters'])==3 and r['parameters'][2]>0]
    variants={'existing':(2.5,2.5) if args.gap_timing else (2.5,2.5,0.),'best_training':selected['parameters']}
    if positive:variants['best_positive_clearance']=min(positive,key=lambda r:r['loss'])['parameters']
    e.save(out/'training.json',{'candidates':train_results,'selected':selected['parameters'],'variants':variants})
    print('TRAIN',[(k,v) for k,v in variants.items()],selected['loss'],flush=True)
    validation={}
    for seed in [23,33]:
        nc=(H/'controller_response_s23_v1/none' if seed==23 else H/'state_response_20260919/native_s33_v1/observations/none')
        rm=(H/'response_late_s23_v1/observations/rm_ramp' if seed==23 else H/'state_response_20260919/native_s33_v1/observations/rm_ramp')
        cases={arm:prepare(seed,arm,folder,[2400],local_folder)[0] for arm,folder in [('none',nc),('rm_ramp',rm)]}
        validation[str(seed)]={}
        for name,parameters in variants.items():
            arms={arm:runner(case,parameters,True) for arm,case in cases.items()}
            delta={k:arms['rm_ramp']['predicted'][k]-arms['none']['predicted'][k] for k in ['ttt','end_n','exits']}
            actual={k:arms['rm_ramp']['observed'][k]-arms['none']['observed'][k] for k in ['ttt','end_n','exits']}
            validation[str(seed)][name]={'parameters':parameters,'arms':arms,'delta':delta,'actual_delta':actual}
            print(seed,name,delta,actual,flush=True)
    e.save(out/'validation.json',validation)
    e.save(out/'source_pins.json',{str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [Path(__file__),e.CAL/'canonical_harness.py',e.ROOT/'evaluation/controllers/physical_ramp_boundary.py',HERE/'port_origin_split_v1/config.json']})


if __name__=='__main__':main()
