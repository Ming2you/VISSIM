"""Isolate 10681 lane-buffer error with frozen mainline, not autonomous validation."""
import copy,csv,gzip,json,math,statistics
from pathlib import Path
from collections import Counter
from diagnostics.sdmpc_n31_20260924.integration_20260926 import replay_congested_component as r
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
from evaluation.controllers import lane_plant_runtime as lpr
from evaluation.controllers.physical_ramp_boundary import LaneResolvedRampBoundary

HERE=Path(__file__).resolve().parent
OUT=HERE/'lane10681'
OUT.mkdir(exist_ok=False)
cap=r.load(HERE/'capture.json');protocol=r.load(HERE/'protocol.json')
model=lpr.load_sources(protocol['manifest'])['component']
assert not model.ramp_lane_exchange and not model.ramp_lane_coupling
cases=[('none',2700.1),('rm',2700.1),('rm',4500.1),('both',4500.1)]
pins={str(Path(__file__)):r.sha(__file__)}
for p in (r.ROOT/'evaluation/controllers').glob('*.py'):pins[str(p)]=r.sha(p)
r.save(OUT/'protocol.json',dict(cases=cases,maximum_buffer_replays=12,new_full_forecasts=0,new_native=0,
    purpose='Baseline exact replay then conditional observed lane arrivals and merge budgets; no calibration.',
    limits='Observed future lane events used ONLY for cause isolation. No individual lateral-transfer stage/timing observed. Actual sampled departures used as budgets, not forced flows.',pins=pins))
rows=[];evidence=[]
for arm,t0 in cases:
    case=f'own_state150_{arm}_{int(t0)}'
    rec=next(z for z in cap['records'] if z['case']==case);data=ObservationData(rec['truth'])
    args,kw=r.read_primitive_capture(rec['input'],rec['sha256']);spec=kw['ramp_dynamics']['ramps']['RM_C10681']
    p=HERE/'predictions'/(case+'.json.gz');pins[str(p)]=r.sha(p)
    with gzip.open(p,'rt') as f:pred=json.load(f)
    baseline=[z for z in pred['ramps'] if z['ramp']=='RM_C10681']
    p=data.folder/'port_events.csv';pins[str(p)]=r.sha(p)
    with p.open(encoding='utf-8-sig',newline='') as f:
        events=[z for z in csv.DictReader(f) if z['connector']=='10681' and t0<float(z['time_s'])<=t0+150]
    assert all(z['lane'] in ['1','2'] and z['kind'] in ['arrival','departure'] for z in events)
    count=Counter((round(float(z['time_s']),6),z['kind'],int(z['lane'])) for z in events)
    head=spec['head_position_m']
    def native(t,lane):
        co=[z for z in data.port_cohorts[str(t)]['10681'] if z[2]==lane]
        return dict(pre=sum(z[0]<head for z in co),post=sum(z[0]>=head for z in co))
    initial=[native(t0,lane) for lane in [1,2]];final=[native(round(t0+150,6),lane) for lane in [1,2]]
    actual_a=[sum(z['kind']=='arrival' and int(z['lane'])==lane for z in events) for lane in [1,2]]
    actual_m=[sum(z['kind']=='departure' and int(z['lane'])==lane for z in events) for lane in [1,2]]
    # Exact whole-lane conservation determines NET exchange, not its stage/time.
    net_out=[sum(initial[i].values())+actual_a[i]-actual_m[i]-sum(final[i].values()) for i in range(2)]
    assert sum(net_out)==0
    actual_head=sum(actual_a)+sum(z['pre'] for z in initial)-sum(z['pre'] for z in final)
    geometry=dict(length_m=spec['length_m'],head_position_m=head,post_length_m=spec['length_m']-head,spacing_m=spec['spacing_m'])
    gaps=[];slow_gaps=[]
    for stamp,co in data.port_cohorts.items():
        if not t0-150<=float(stamp)<=t0:continue
        for lane in [1,2]:
            lane_co=sorted((z for z in co['10681'] if z[2]==lane and z[0]>=head),key=lambda z:z[0])
            for a,b in zip(lane_co,lane_co[1:]):
                gaps.append(b[0]-a[0])
                if max(a[1],b[1])<5:slow_gaps.append(b[0]-a[0])
    evidence.append(dict(case=case,geometry=geometry,initial=initial,actual_final=final,actual_arrivals=actual_a,
        actual_merges=actual_m,net_lane_out=net_out,actual_head_inferred=actual_head,
        past_post_spacing_median=statistics.median(gaps),past_slow_spacing_median=statistics.median(slow_gaps),
        past_slow_pairs=len(slow_gaps),captured_lane_arrival_shares=spec['lane_arrival_shares']))
    for mode in ['baseline','actual_arrivals','actual_arrivals_merges']:
        buffer=LaneResolvedRampBoundary(**copy.deepcopy(spec));receipts=[];max_parity=0.
        for i,old in enumerate(baseline):
            step=args[1][i];service=model._head_service('RM_C10681',step['ramp_head_service']['RM_C10681'],10.)
            end=round(t0+5*(i//5+1),6)
            lane_a=[count[end,'arrival',lane]/5 for lane in [1,2]]
            lane_m=[count[end,'departure',lane]/5 for lane in [1,2]]
            extra={}
            request=step['ramp_arrival_vph']['RM_C10681']/3600
            budget=old['receiving_budget_veh']
            if mode!='baseline':
                request=sum(lane_a);extra['request_arrivals_by_lane_second']=[[x] for x in lane_a]
            if mode=='actual_arrivals_merges':
                budget=sum(lane_m);extra['receiving_budget_by_lane_veh']=lane_m
            z=buffer.advance_local_interval(start_sec=old['start_sec'],duration_sec=1.,cycle_sec=10.,
                receiving_budget_veh=budget,request_arrivals_veh=request,allow_partial_cycle=True,**service,**extra)
            receipts.append(z)
            if mode=='baseline':
                for key in ['head_service_veh','accepted_merge_veh','admitted_arrivals_veh']:
                    max_parity=max(max_parity,abs(z[key]-old[key]))
                for left,right in zip(z['lane_receipts'],old['lane_receipts']):
                    for key in ['upstream_travelling_veh','head_ready_veh','downstream_travelling_veh','merge_ready_veh','connector_veh']:
                        max_parity=max(max_parity,abs(left['end'][key]-right['end'][key]))
        assert max_parity<1e-7
        lanes=[]
        for i in range(2):
            lr=[z['lane_receipts'][i] for z in receipts];end=lr[-1]['end']
            lanes.append(dict(lane=i+1,arrivals=sum(z['admitted_arrivals_veh'] for z in lr),
                head=sum(z['head_service_veh'] for z in lr),merges=sum(z['accepted_merge_veh'] for z in lr),
                pre=end['upstream_travelling_veh']+end['head_ready_veh'],
                post=end['downstream_travelling_veh']+end['merge_ready_veh'],
                unused_receiving=sum(z['unused_receiving_budget_veh'] for z in lr)))
        total={key:sum(z[key] for z in lanes) for key in ['arrivals','head','merges','pre','post']}
        actual=dict(arrivals=sum(actual_a),head=actual_head,merges=sum(actual_m),
                    pre=sum(z['pre'] for z in final),post=sum(z['post'] for z in final))
        assert abs(sum(initial[i]['pre']+initial[i]['post'] for i in range(2))+total['arrivals']-total['merges']-total['pre']-total['post'])<1e-7
        rows.append(dict(case=case,mode=mode,lanes=lanes,predicted=total,actual=actual,
            error={key:total[key]-value for key,value in actual.items()},baseline_max_difference=max_parity,
            mass_max=max(abs(z['conservation_residual_veh']) for z in receipts)))
        with gzip.open(OUT/(case+'_'+mode+'.json.gz'),'wt') as f:json.dump(receipts,f)
for p,h in pins.items():assert r.sha(p)==h
r.save(OUT/'summary.json',dict(rows=rows,evidence=evidence,pins=pins,buffer_replays=len(rows),
    baseline_parity_passed=4,new_full_forecasts=0,new_native=0,calibration=False,adopted=False,
    scope='Conditional isolated buffer with frozen saved receiving, NOT autonomous physics or gain qualification.'))
(OUT/'source_executed.py.txt').write_bytes(Path(__file__).read_bytes())
for z in rows:print(json.dumps({key:z[key] for key in ['case','mode','error']}))

