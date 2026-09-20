"""Split observed paired arrival-time shifts from downstream travel delays."""
from pathlib import Path
import hashlib
import json
import statistics
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import matched_cohort_response as c

K,e=c.K,c.e
OUT=K/'matched_passage_response_v1'


def passage(car,points):
    trajectory=car['trajectory'];result={}
    for name,position in points.items():
        for index,row in enumerate(trajectory):
            if row is not None and row[0]>=position:
                result[name]=dict(t=2550+index,v=row[1],lane=row[2]);break
    return result


def stats(values):
    return dict(n=len(values),mean=statistics.mean(values) if values else None,
        median=statistics.median(values) if values else None,min=min(values,default=None),max=max(values,default=None))


def main():
    OUT.mkdir(exist_ok=False)
    gp=K/'matched_meter_midpoint_s33_v2/observations/rm8/geometry.json';geometry=e.load(gp)
    cells={r['cell']:r for r in geometry['cells'] if r['road']=='FW_E'}
    points={'merge10490':next(r['chain_pos_m'] for r in geometry['boundaries'] if r['connector']==10490),
            'merge10484':next(r['chain_pos_m'] for r in geometry['boundaries'] if r['connector']==10484),
            'start16':cells[16]['start_m'],'start20':cells[20]['start_m']}
    labels=list(points);results={};sources=[Path(__file__),Path(c.__file__),gp]
    for seed in (23,33):
        bank={}
        for arm in ('rm8','rm6','rm_ramp'):
            path=c.OUT/f's{seed}_{arm}.json';bank[arm]=e.load(path);sources.append(path)
        results[str(seed)]={}
        for arm in ('rm6','rm_ramp'):
            paired=[]
            for vid,base in bank['rm8']['cars'].items():
                if base['initial_cell']>12:continue
                controlled=bank[arm]['cars'][vid]
                a,b=passage(base,points),passage(controlled,points)
                if len(a)<len(points) or len(b)<len(points):continue
                # Only continuously observed mainline passages: no exit/reentry shortcut.
                for car,row in ((base,a),(controlled,b)):
                    assert all(v is not None for v in car['trajectory'][row['merge10490']['t']-2550:row['start20']['t']-2550+1])
                shifts={p:b[p]['t']-a[p]['t'] for p in points}
                legs={x+'_'+y:shifts[y]-shifts[x] for x,y in zip(labels,labels[1:])}
                assert sum(legs.values())==shifts['start20']-shifts['merge10490']
                paired.append(dict(vehicle=int(vid),baseline=a,controlled=b,arrival_shifts_s=shifts,
                                   travel_time_shifts_s=legs,speed_shifts_kmh={p:b[p]['v']-a[p]['v'] for p in points}))
            row=dict(matched_completed_passages=len(paired),
                arrival_shifts_s={p:stats([r['arrival_shifts_s'][p] for r in paired]) for p in points},
                travel_time_shifts_s={x+'_'+y:stats([r['travel_time_shifts_s'][x+'_'+y] for r in paired]) for x,y in zip(labels,labels[1:])},
                speed_shifts_kmh={p:stats([r['speed_shifts_kmh'][p] for r in paired]) for p in points},pairs=paired)
            results[str(seed)][arm]=row
            print(json.dumps(dict(seed=seed,arm=arm,n=len(paired),arrival={p:r['mean'] for p,r in row['arrival_shifts_s'].items()},
                travel={p:r['mean'] for p,r in row['travel_time_shifts_s'].items()},speed={p:r['mean'] for p,r in row['speed_shifts_kmh'].items()})),flush=True)
    e.save(OUT/'result.json',dict(qualified=False,future_inputs_to_model=False,new_native_runs=0,points_m=points,cases=results,
        limitations=['Post-run explanation,not a forecast or new calibration.',
            'Initial cells0-12 only; both runs must reach all four points by3000. Completion conditioning excludes censored/exit vehicles.',
            'Do not substitute these conditional mean travel times for full-component TTT or a causal contribution estimate.',
            'Native1s frame crossing times; no subsecond interpolation or interaction-target inference.'],
        source_pins={p.relative_to(e.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}))


if __name__=='__main__':main()
