"""Locate paired initial-car delay changes in the completed matched RM runs.

Retrospective evidence only. Newly born numeric IDs are never paired. No native
run or model prediction is launched, and nothing is passed to a forecast.
"""
from pathlib import Path
from collections import Counter
import bisect
import hashlib
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import marginal_boundary_timing as a

K, e = Path(__file__).resolve().parent, a.m.e
OUT = K / 'matched_cohort_response_v1'


def analyze(path, geometry):
    chain = {r['link']:r for r in geometry['chains']['FW_E']}
    ports = {r['connector']:r for r in geometry['boundaries'] if r['road']=='FW_E' and r['kind'] in ('ramp','offramp')}
    bounds = [r['end_m'] for r in geometry['cells'] if r['road']=='FW_E']
    before = path.stat()
    initial = None
    cars = {}
    trace = []
    for t, frame in a.frames(path, set(chain)|set(ports)):
        main = {v:r for v,r in frame.items() if r['link'] in chain}
        if t == a.START:
            initial = main
            cars = {v:dict(initial=r, initial_cell=min(20,max(0,bisect.bisect_right(bounds,chain[r['link']]['offset_m']+r['pos']))),
                           cell_seconds=[0]*21, residence_s=0, trajectory=[]) for v,r in main.items()}
        for vid, car in cars.items():
            row = main.get(vid)
            if row is None:
                car['trajectory'].append(None)
                continue
            x = chain[row['link']]['offset_m']+row['pos']
            cell = min(20,max(0,bisect.bisect_right(bounds,x)))
            car['trajectory'].append([round(x,6),row['speed'],row['lane'],cell])
            if t>a.START:
                car['cell_seconds'][cell] += 1
                car['residence_s'] += 1
        trace.append(dict(time_s=t,n=len(main),initial_n=len(cars.keys()&main.keys())))
    assert t==a.END and len(trace)==451
    assert all(len(v['trajectory'])==451 for v in cars.values())
    assert sum(v['residence_s'] for v in cars.values())==sum(r['initial_n'] for r in trace[1:])
    assert (before.st_size,before.st_mtime_ns)==(path.stat().st_size,path.stat().st_mtime_ns)
    return dict(initial_frame=initial,cars=cars,trace=trace,
        source_receipt=dict(path=path.relative_to(e.ROOT).as_posix(),bytes=before.st_size,mtime_ns=before.st_mtime_ns))


def compare(reference, controlled):
    assert reference['initial_frame']==controlled['initial_frame']
    groups = {str(c):dict(initial_n=0,delta_residence_s=0,downstream14_20_delta_s=0,
        delta_by_cell_s=[0]*21,first_difference_s=None,first_position5m_difference_s=None,
        first_difference_example=None,improved_vehicles=0,worsened_vehicles=0,unchanged_vehicles=0) for c in range(21)}
    pairs=[]
    for vid, base in reference['cars'].items():
        alt=controlled['cars'][vid]
        delta=alt['residence_s']-base['residence_s']
        row=groups[str(base['initial_cell'])]
        row['initial_n']+=1;row['delta_residence_s']+=delta
        row['downstream14_20_delta_s']+=sum(alt['cell_seconds'][14:])-sum(base['cell_seconds'][14:])
        row['improved_vehicles' if delta<0 else 'worsened_vehicles' if delta>0 else 'unchanged_vehicles']+=1
        cell_deltas=[x-y for x,y in zip(alt['cell_seconds'],base['cell_seconds'])]
        row['delta_by_cell_s']=[x+y for x,y in zip(row['delta_by_cell_s'],cell_deltas)]
        first=first5=None
        for j,(x,y) in enumerate(zip(base['trajectory'],alt['trajectory'])):
            if x!=y and first is None:
                first=a.START+j
                if row['first_difference_s'] is None or first<row['first_difference_s']:
                    row['first_difference_s']=first
                    row['first_difference_example']=dict(vehicle=vid,reference=x,controlled=y)
            if x is not None and y is not None and abs(x[0]-y[0])>=5 and first5 is None:
                first5=a.START+j
                if row['first_position5m_difference_s'] is None or first5<row['first_position5m_difference_s']:
                    row['first_position5m_difference_s']=first5
        pairs.append(dict(vehicle=vid,initial_cell=base['initial_cell'],delta_residence_s=delta,
            delta_by_cell_s=cell_deltas,first_difference_s=first,first_position5m_difference_s=first5))
    assert sum(r['delta_residence_s'] for r in groups.values())==sum(v['delta_residence_s'] for v in pairs)
    return dict(groups=groups,pairs=pairs,initial_cohort_delta_veh_h=sum(v['delta_residence_s'] for v in pairs)/3600,
        mainline_delta_veh_h=sum(b['n']-a0['n'] for a0,b in zip(reference['trace'][1:],controlled['trace'][1:]))/3600,
        delta_by_cell_veh_h=[sum(v['delta_by_cell_s'][c] for v in pairs)/3600 for c in range(21)])


def main():
    OUT.mkdir(exist_ok=False)
    sources=[Path(__file__),Path(a.__file__)]
    summaries={}
    for seed in (23,33):
        bank=a.m.BANK if seed==23 else K.parent/'state_response_20260919/native_s33_v1'
        geometry_path=bank/('observations/rm8/geometry.json' if seed==23 else 'observations/rm_ramp/geometry.json')
        geometry=e.load(geometry_path)
        fresh=K/('matched_meter_midpoint_v1' if seed==23 else 'matched_meter_midpoint_s33_v2')
        runs={arm:(bank/('run_'+arm) if seed==23 and arm!='rm6' or arm=='rm_ramp' else fresh/('run_'+arm))
              for arm in ('rm8','rm6','rm_ramp')}
        actual_path=fresh/('result_v2.json' if seed==23 else 'result.json')
        actual=e.load(actual_path)
        sources.extend([geometry_path,actual_path])
        cases={}
        for arm,run in runs.items():
            result=analyze(run/'vissim_eval/baseline_001.fzp',geometry)
            expected=actual['actual'][arm]['component']['mainline']
            assert abs(sum(r['n'] for r in result['trace'][1:])/3600-expected)<1e-8
            cases[arm]=result
            e.save(OUT/f's{seed}_{arm}.json',result)
            print(json.dumps(dict(seed=seed,arm=arm,initial_n=len(result['cars']))),flush=True)
        summaries[str(seed)]={arm:compare(cases['rm8'],cases[arm]) for arm in ('rm6','rm_ramp')}
        for arm,result in summaries[str(seed)].items():
            assert abs(result['mainline_delta_veh_h']-actual['actual_deltas_vs_g8'][arm]['mainline'])<1e-8
        # Both commands are identical through2700; check every initial-car row.
        assert all(v['trajectory'][:151]==cases['rm_ramp']['cars'][vid]['trajectory'][:151]
                   for vid,v in cases['rm6']['cars'].items())
        e.save(OUT/f'result_s{seed}.json',summaries[str(seed)])
    e.save(OUT/'result.json',dict(qualified=False,native_started=False,forecasts_recomputed=False,
        purpose='Retrospective paired initial-cohort location and propagation evidence',
        future_inputs=False,initial_vehicle_frames_exact=True,mild_strong_first150s_exact=True,
        cases=summaries,source_pins={p.relative_to(e.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}))
    print('COMPLETE',flush=True)


if __name__=='__main__':main()
