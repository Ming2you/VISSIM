"""Observed stopped-stock balance; no microscopic cause labels or model fit."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'lane_interaction110/frames.json.gz'
REGIONS={'approach16_20':range(16,21),'merge21_23':range(21,24),
         'recovery24_25':range(24,26),'all16_25':range(16,26)}


def save(name,value):
    (HERE/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def main():
    assert not (HERE/'results.json').exists(), 'Reuse completed result'
    save('protocol.json',dict(
        previous_goal_turn='PROGRESS:111 implemented/calibrated minimal literature proxy, rejected on other-state gain; production restored.',
        source=str(SOURCE),sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        thresholds_kmh=[1,5],regions={k:list(v) for k,v in REGIONS.items()},
        balance='B_next=B+new_stops-restarts+stopped_entries-stopped_exits',
        observation='5second frames2700.1..3145.1;445seconds. Final block145s, not450s complete.',
        exposures='Common-vehicle starting status times5s; observed five-second transition probabilities, not continuous hazard or exact dwell time.',
        limitations=['May miss multiple state transitions within5s.','Stopping is not proof of mandatory lane changing.',
                    'Integral decomposition is bookkeeping, not a causal allocation or future predictor.',
                    'No future observations are introduced into the plant.','No new fitted coefficients or native runs.']))
    with gzip.open(SOURCE,'rt',encoding='utf-8') as f:data=json.load(f)
    cases=data['cases'];names=['release','release_vsl90']
    assert [f['t'] for f in cases[names[0]]['frames']]==[f['t'] for f in cases[names[1]]['frames']]
    def focus(frame,region):return {vid:r for vid,r in frame['rows'].items() if r['cell'] in region}
    initial=[focus(cases[n]['frames'][0],REGIONS['all16_25']) for n in names]
    assert initial[0]==initial[1]
    result=[];windows=[];comparisons=[]
    for region,cells in REGIONS.items():
        for threshold in (1,5):
            for arm in names:
                frames=cases[arm]['frames'];start=frames[0]['t'];end=frames[-1]['t']
                total=Counter();weighted=Counter();observations=[];area=0.;balances=[]
                for old,new in zip(frames,frames[1:]):
                    a,b=focus(old,cells),focus(new,cells);dt=new['t']-old['t'];assert abs(dt-5)<1e-7
                    low_a={v for v,r in a.items() if r['speed']<threshold}
                    low_b={v for v,r in b.items() if r['speed']<threshold}
                    common=a.keys()&b.keys()
                    stops=(low_b-low_a)&common;restarts=(low_a-low_b)&common
                    incoming=low_b-a.keys();outgoing=low_a-b.keys()
                    counts=dict(new_stops=len(stops),restarts=len(restarts),stopped_entries=len(incoming),stopped_exits=len(outgoing))
                    change=counts['new_stops']-counts['restarts']+counts['stopped_entries']-counts['stopped_exits']
                    balances.append(len(low_b)-len(low_a)-change);assert balances[-1]==0
                    total.update(counts)
                    total['stopped_common_exposure_sec']+=len(low_a&common)*dt
                    total['moving_common_exposure_sec']+=len(common-low_a)*dt
                    for key in counts:weighted[key]+=counts[key]*(end-new['t']+dt/2)*(1 if key in ('new_stops','stopped_entries') else -1)
                    area+=(len(low_a)+len(low_b))*dt/2
                    observations.append(dict(start_sec=old['t'],end_sec=new['t'],start_low=len(low_a),end_low=len(low_b),**counts))
                initial_low=sum(r['speed']<threshold for r in focus(frames[0],cells).values())
                assert abs(area-initial_low*(end-start)-sum(weighted.values()))<1e-7
                row=dict(region=region,threshold_kmh=threshold,arm=arm,seconds=end-start,
                         initial_low=initial_low,end_low=observations[-1]['end_low'],
                         mean_low_veh=area/(end-start),low_vehicle_hours=area/3600,counts=dict(total),
                         observed_stop_probability5s=total['new_stops']/(total['moving_common_exposure_sec']/5) if total['moving_common_exposure_sec'] else None,
                         observed_restart_probability5s=total['restarts']/(total['stopped_common_exposure_sec']/5) if total['stopped_common_exposure_sec'] else None,
                         stock_integral_terms_veh_h={k:v/3600 for k,v in weighted.items()},
                         balance_max_error=max(map(abs,balances)))
                result.append(row)
                for left,right in ((start,start+150),(start+150,start+300),(start+300,end)):
                    rows=[r for r in observations if r['start_sec']>=left-1e-6 and r['end_sec']<=right+1e-6]
                    assert len(rows)==round((right-left)/5)
                    counts={k:sum(r[k] for r in rows) for k in ('new_stops','restarts','stopped_entries','stopped_exits')}
                    windows.append(dict(region=region,threshold_kmh=threshold,arm=arm,start=left,end=right,
                                        mean_low_veh=sum((r['start_low']+r['end_low'])*2.5 for r in rows)/(right-left),**counts))
            a,b=result[-2:]
            comparisons.append(dict(region=region,threshold_kmh=threshold,
                mean_low_reduction_fraction=1-b['mean_low_veh']/a['mean_low_veh'] if a['mean_low_veh'] else None,
                observed_stop_probability5s=[a['observed_stop_probability5s'],b['observed_stop_probability5s']],
                observed_restart_probability5s=[a['observed_restart_probability5s'],b['observed_restart_probability5s']],
                delta_low_vehicle_hours=b['low_vehicle_hours']-a['low_vehicle_hours'],
                delta_integral_terms={k:b['stock_integral_terms_veh_h'][k]-a['stock_integral_terms_veh_h'][k] for k in a['stock_integral_terms_veh_h']}))
    save('results.json',dict(rows=result,comparisons=comparisons,windows=windows,
                              same_initial=True,observation_balances=16*89,all_balances_exact=True))
    for row in result:
        if row['threshold_kmh']==5:
            print(json.dumps({k:v for k,v in row.items() if k not in ('stock_integral_terms_veh_h',)},ensure_ascii=False))


if __name__=='__main__':main()
