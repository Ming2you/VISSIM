"""Predict entrance vehicle restart from the CURRENT downstream moving front.

One parameter (pair startup lag) is reused from NC13 stopped-pair observations.
No future drainage, control gain fitting, network changes or native runs.
This audits a startup-wave mechanism, not a full off-ramp capacity model.
"""
from pathlib import Path
import sys,hashlib,statistics
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e

HERE=Path(__file__).resolve().parent


def predict(vehicles,lane,lag):
    rows=sorted((p,vid,v) for vid,l,p,v in vehicles if l==lane)
    if not rows or rows[0][0]>=6 or rows[0][2]>=5:return None
    entry=rows[0];stopped=1;previous=entry
    for row in rows[1:]:
        if row[0]-previous[0]>20:
            return dict(status='gap_interrupts_queue',vehicle=entry[1],stopped_chain=stopped,
                        entry_pos=entry[0],front_pos=row[0],current_gap=row[0]-previous[0])
        if row[2]>=5:
            return dict(status='moving_front_observed',vehicle=entry[1],stopped_chain=stopped,
                        entry_pos=entry[0],front_pos=row[0],front_speed=row[2],
                        predicted_restart_delay_s=lag*stopped)
        stopped+=1;previous=row
    return dict(status='no_moving_front_in_connector',vehicle=entry[1],stopped_chain=stopped,
                entry_pos=entry[0],front_pos=previous[0])


def main():
    out=HERE/'off_queue_release_v1';out.mkdir(exist_ok=False)
    source=HERE/'off_space_wave_v2/result.json';wave=e.load(source)
    train=[r['lag_s'] for r in wave['results']['13']['events'] if r['lane']==2 and
           1050<=r['leader_start_s']<3300 and r['lag_s']>0 and r['stopped_gap_m']<=20]
    lag=statistics.median(train)
    pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),source]}
    result={}
    for seed in (13,23,33):
        path=HERE/f'off_space_wave_v2/s{seed}_frames.json'
        data=e.load(path);pins[str(path.relative_to(e.ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
        frames={r['time_s']:r['vehicles'] for r in data['frames']}
        lookup={t:{vid:(l,p,v) for vid,l,p,v in vehicles} for t,vehicles in frames.items()}
        samples=[]
        for t in range(1050,4201,10):
            for lane in (1,2):
                prediction=predict(frames[t],lane,lag)
                if prediction is None:continue
                vid=prediction['vehicle'];restart=None;departed=None;changed=None
                # Future frames are truth labels only, never passed to predict.
                for future in range(t+1,t+151):
                    row=lookup[future].get(vid)
                    if row is None:departed=future-t;break
                    if row[0]!=lane:changed=future-t;break
                    if row[2]>=5:restart=future-t;break
                samples.append(dict(time_s=t,lane=lane,**prediction,actual_restart_s=restart,
                    departed_without_observed_restart_s=departed,lane_change_before_restart_s=changed,
                    right_censored_150s=restart is None and departed is None and changed is None))
        summary={}
        for subset,selected in [('all',samples),('after_training', [r for r in samples if r['time_s']>=3300])]:
            comparable=[r for r in selected if r['status']=='moving_front_observed' and r['actual_restart_s'] is not None]
            capped=[r for r in selected if r['status']=='moving_front_observed' and r['departed_without_observed_restart_s'] is None and r['lane_change_before_restart_s'] is None]
            strata={}
            for name,lo,hi in [('1..5',1,5),('6..15',6,15),('16+',16,1000)]:
                rows=[r for r in comparable if lo<=r['stopped_chain']<=hi]
                strata[name]=dict(samples=len(rows),mean_chain=statistics.mean(r['stopped_chain'] for r in rows) if rows else None,
                    mean_actual_delay=statistics.mean(r['actual_restart_s'] for r in rows) if rows else None,
                    mean_predicted_delay=statistics.mean(r['predicted_restart_delay_s'] for r in rows) if rows else None)
            summary[subset]=dict(samples=len(selected),status_counts=dict(Counter(r['status'] for r in selected)),
                comparable=len(comparable),censored_moving_front=sum(r['right_censored_150s'] for r in capped),
                moving_front_restart_mae_s=statistics.mean(abs(r['predicted_restart_delay_s']-r['actual_restart_s']) for r in comparable) if comparable else None,
                constant_pair_lag_mae_s=statistics.mean(abs(lag-r['actual_restart_s']) for r in comparable) if comparable else None,
                capped_at150_mae_s=statistics.mean(abs(min(150,r['predicted_restart_delay_s'])-(r['actual_restart_s'] or 150)) for r in capped) if capped else None,
                by_chain=strata)
        result[str(seed)]=dict(summary=summary,samples=samples)
        print(seed,summary,flush=True)
    for p,pin in pins.items():assert hashlib.sha256((e.ROOT/p).read_bytes()).hexdigest()==pin
    e.save(out/'result.json',dict(results=result,pair_lag_s=lag,training_events=len(train),pins=pins,
        no_gain_fitting=True,new_native_runs=0,causal_inputs='Current same-lane positions/speeds only. Future frames are restart/censor labels.',
        limitations=['Overlapping10s observations are not independent episodes.',
            'A moving entrance vehicle does not prove receiving capacity or complete clearance.',
            'No moving front means downstream service must be predicted; do not silently assume immediate opening.',
            'Queue continuity uses the existing20m and5km/h observation definitions, not fitted capacity parameters.'],
        production_adopted=False,qualified=False))


if __name__=='__main__':main()
