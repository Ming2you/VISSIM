"""Check the startup-law mismatch: fitted rest<1, previously counted rest<5.

No coefficient search: reuse2s pair lag and the original training rest threshold.
Controlled seeds are development evidence, not an unused validation set.
"""
from pathlib import Path
import sys,hashlib,statistics
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e

HERE=Path(__file__).resolve().parent


def current_front(vehicles,lane):
    rows=sorted((p,vid,v) for vid,l,p,v in vehicles if l==lane)
    if not rows or rows[0][0]>=6 or rows[0][2]>=5:return None
    for i,(p,vid,v) in enumerate(rows):
        if i and p-rows[i-1][0]>20:return None
        if v>=1:return dict(stopped_chain=i,predicted_restart_delay_s=2*i,front_pos=p,front_speed=v,
                            vehicle=rows[0][1],entry_pos=rows[0][0])
    return None


def summarize(samples):
    eligible=[r for r in samples if r['new'] is not None and r['actual_restart_s'] is not None]
    unique={}
    for r in samples:unique.setdefault((r['lane'],r['vehicle']),r)
    def score(rows):
        rows=[r for r in rows if r['new'] is not None and r['actual_restart_s'] is not None]
        return dict(samples=len(rows),old_mae_s=statistics.mean(abs(r['predicted_restart_delay_s']-r['actual_restart_s']) for r in rows) if rows else None,
            corrected_rest_mae_s=statistics.mean(abs(r['new']['predicted_restart_delay_s']-r['actual_restart_s']) for r in rows) if rows else None,
            old_next10s_errors=sum((r['predicted_restart_delay_s']>10)!=(r['actual_restart_s']>10) for r in rows),
            corrected_next10s_errors=sum((r['new']['predicted_restart_delay_s']>10)!=(r['actual_restart_s']>10) for r in rows))
    return dict(all=score(samples),first_per_vehicle=score(unique.values()),
        unknown_current_front=sum(r['new'] is None for r in samples),samples=samples)


def main():
    out=HERE/'off_queue_rest_front_v1';out.mkdir(exist_ok=False)
    prior=e.load(HERE/'off_queue_release_v1/result.json');controlled=e.load(HERE/'off_queue_release_controlled_v1/result.json')
    assert prior['pair_lag_s']==2
    pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [Path(__file__),HERE/'off_queue_release_v1/result.json',HERE/'off_queue_release_controlled_v1/result.json']}
    results={}
    cases=[('13_none_training',prior['results']['13']['samples'],HERE/'off_space_wave_v2/s13_frames.json')]
    for case,row in controlled['results'].items():
        seed,arm=case.split('_',1)
        path=HERE/(f'off_space_wave_v2/s{seed}_frames.json' if arm=='none' else f'off_queue_release_controlled_v1/s{seed}_{arm}_frames.json')
        cases.append((case,row['samples'],path))
    for case,samples,path in cases:
        pins[str(path.relative_to(e.ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
        frames={r['time_s']:r['vehicles'] for r in e.load(path)['frames']}
        rows=[]
        for r in samples:
            if r['status']!='moving_front_observed':continue
            if case=='13_none_training' and r['time_s']>=3300:continue
            p=current_front(frames[r['time_s']],r['lane'])
            if p:assert p['vehicle']==r['vehicle']
            rows.append(dict(**r,new=p))
        results[case]=summarize(rows)
        print(case,{k:v for k,v in results[case].items() if k!='samples'},flush=True)
    for p,pin in pins.items():assert hashlib.sha256((e.ROOT/p).read_bytes()).hexdigest()==pin
    e.save(out/'result.json',dict(results=results,pins=pins,qualified=False,production_adopted=False,new_native_runs=0,
        interpretation='Count rest<1km/h, matching pair-delay calibration; earlier5km/h chain included already-moving creep.2s unchanged. Restart target remains5km/h, so acceleration/phase residual is unresolved.',
        caveats=['Already inspected controlled states, no fresh holdout.', 'Current front is not a prediction of future reopening/onset or receiving capacity.',
            'Spacing holes, creeping and lane changes can open space before the threshold restart.']))


if __name__=='__main__':main()
