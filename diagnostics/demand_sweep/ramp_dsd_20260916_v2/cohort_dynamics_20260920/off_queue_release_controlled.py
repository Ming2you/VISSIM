"""Apply the frozen current-queue restart prediction to existing controlled arms."""
from pathlib import Path
import sys,hashlib,statistics
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,CASES,ARMS
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.state_exchange_20260920.analyze_dispersion import records
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.off_queue_release import predict

HERE=Path(__file__).resolve().parent


def extract(folder,start=2250,end=3000):
    data=e.ObservationData(folder);manifest=e.load(folder/'manifest.json')
    run=Path(manifest['source_run']);run=run if run.is_absolute() else e.ROOT/run
    assert e.load(run/'run.json')['completed']
    path=run/'vissim_eval/baseline_001.fzp';before=path.stat()
    expected={kind:Counter((int(float(r['time_s'])),int(r['vehicle'])) for r in e.rows(folder/'port_events.csv')
        if r['connector']=='10643' and r['kind']==kind and start<float(r['time_s'])<=end) for kind in ('arrival','departure')}
    frames={};frame=[];last=None
    for row in records(path):
        t=int(float(row[0]))
        if t<start:continue
        if t>end:break
        if last is not None and t!=last:
            assert t==last+1;frames[last]=frame;frame=[]
        last=t
        if int(row[2])==10643:frame.append([int(row[1]),int(row[3]),float(row[4]),float(row[6])])
    assert last==end;frames[last]=frame
    seen={kind:Counter() for kind in expected};previous=None;stock_checks=0
    for t,rows in frames.items():
        ids={r[0] for r in rows};assert len(ids)==len(rows)
        if previous is not None:
            seen['arrival'].update((t,v) for v in ids-previous)
            seen['departure'].update((t,v) for v in previous-ids)
        if t%30==0:
            observed=sorted((float(p),float(v),int(l)) for p,v,l in data.port_cohorts[str(t)]['10643'])
            assert observed==sorted((p,v,l) for vid,l,p,v in rows);stock_checks+=1
        previous=ids
    assert seen==expected
    after=path.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    return dict(source=str(path.relative_to(e.ROOT)),bytes=before.st_size,mtime_ns=before.st_mtime_ns,
        source_manifest=str((folder/'manifest.json').relative_to(e.ROOT)),
        event_checks=sum(sum(r.values()) for r in seen.values()),stock_checks=stock_checks,
        frames=[dict(time_s=t,vehicles=rows) for t,rows in frames.items()])


def score(frames,lag):
    bytime={r['time_s']:r['vehicles'] for r in frames}
    lookup={t:{vid:(l,p,v) for vid,l,p,v in rows} for t,rows in bytime.items()}
    samples=[]
    for t in range(2400,2851,10):
        for lane in (1,2):
            p=predict(bytime[t],lane,lag)
            if p is None:continue
            restart=None;change=None;depart=None
            for future in range(t+1,t+151):
                r=lookup[future].get(p['vehicle'])
                if r is None:depart=future-t;break
                if r[0]!=lane:change=future-t;break
                if r[2]>=5:restart=future-t;break
            samples.append(dict(time_s=t,lane=lane,**p,actual_restart_s=restart,
                lane_change_before_restart_s=change,departed_without_observed_restart_s=depart,
                right_censored_150s=restart is None and change is None and depart is None))
    selected=[r for r in samples if r['status']=='moving_front_observed' and r['actual_restart_s'] is not None]
    return dict(samples=samples,status_counts=dict(Counter(r['status'] for r in samples)),comparable=len(selected),
        restart_mae_s=statistics.mean(abs(r['predicted_restart_delay_s']-r['actual_restart_s']) for r in selected) if selected else None,
        constant_pair_lag_mae_s=statistics.mean(abs(lag-r['actual_restart_s']) for r in selected) if selected else None,
        predicted_still_stopped_next10s=sum(r['predicted_restart_delay_s']>10 for r in selected),
        actual_still_stopped_next10s=sum(r['actual_restart_s']>10 for r in selected),
        next10s_stop_classification_errors=sum((r['predicted_restart_delay_s']>10)!=(r['actual_restart_s']>10) for r in selected),
        scope='Reinitialized current snapshot forecasts; correlated10s starts. Restart is not proof of entry clearance/capacity.')


def main():
    out=HERE/'off_queue_release_controlled_v1';out.mkdir(exist_ok=False)
    prior=e.load(HERE/'off_queue_release_v1/result.json');lag=prior['pair_lag_s'];assert lag==2
    files=[Path(__file__),HERE/'off_queue_release.py',HERE/'off_queue_release_v1/result.json']
    pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    e.save(out/'protocol.json',dict(pins=pins,lag_s=lag,frozen_from='seed13 NC1050..3300 stopped pair median',
        cases='Existing23/33 NC/RM/VSL/both,2400..2850. No fitting or extra native runs.',
        inputs='Only current positions/speeds; future frames label restart/censor, not inputs.'))
    result={}
    for seed,folder,bank,start in CASES:
        if seed not in (23,33):continue
        for arm in ARMS:
            if arm=='none':fields=e.load(HERE/f'off_space_wave_v2/s{seed}_frames.json')
            else:
                fields=extract(bank/'observations'/arm)
                e.save(out/f's{seed}_{arm}_frames.json',fields)
            row=score(fields['frames'],lag);result[f'{seed}_{arm}']=row
            print(seed,arm,{k:v for k,v in row.items() if k!='samples'},flush=True)
    for file,pin in pins.items():assert hashlib.sha256((e.ROOT/file).read_bytes()).hexdigest()==pin
    e.save(out/'result.json',dict(results=result,lag_s=lag,new_native_runs=0,no_gain_fitting=True,
        production_adopted=False,qualified=False,source_pins_verified=True))


if __name__=='__main__':main()
