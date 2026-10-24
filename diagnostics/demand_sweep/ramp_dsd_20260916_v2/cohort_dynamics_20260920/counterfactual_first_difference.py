"""Locate first physical differences in the same INITIAL vehicle cohort.

No post-intervention generated ID is assumed to denote the same vehicle.
This checks possible remote stochastic divergence, not proof of its cause.
"""
from pathlib import Path
import sys,hashlib
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import downstream_wave_audit as d


def frames(path,end=2460):
    meta=(path.stat().st_size,path.stat().st_mtime_ns);result={}
    with path.open('rb') as f:
        for line in f:
            if not line[:1] or line[:1] not in b'0123456789':continue
            t=float(line.split(b';',1)[0])
            if t>end:break
            if t<2400:continue
            a=[v.strip() for v in line.rstrip(b'\r\n').split(b';')]
            record=tuple(a[:9]);vid=int(a[1])
            if int(t) not in result:result[int(t)]={}
            assert vid not in result[int(t)]
            result[int(t)][vid]=record
    assert set(result)==set(range(2400,end+1))
    assert meta==(path.stat().st_size,path.stat().st_mtime_ns)
    return result,dict(path=str(path.relative_to(d.ROOT)),size=meta[0],mtime_ns=meta[1])


def main():
    out=d.HERE/'counterfactual_first_difference_v1';out.mkdir(exist_ok=False)
    geometry=d.e.load(d.H/'controller_response_s23_v1/none/geometry.json')
    address={int(k):v[0] for k,v in geometry['addresses'].items()}
    paths={'none':d.H/'rules_4500_s23_v1/run_none/vissim_eval/baseline_001.fzp',
           'rm_ramp':d.H/'response_late_s23_v1/run_rm_ramp/vissim_eval/baseline_001.fzp'}
    series={};receipts={}
    for arm,path in paths.items():series[arm],receipts[arm]=frames(path)
    assert series['none'][2400]==series['rm_ramp'][2400]
    initial=series['none'][2400];first={};by_time=[];first_per_vehicle={}
    for t in range(2401,2461):
        grouped=Counter();missing=Counter()
        for vid,before in initial.items():
            a=series['none'][t].get(vid);b=series['rm_ramp'][t].get(vid)
            if a is None and b is None:continue
            road=address.get(int(before[2]),'non_mainline')
            if a is None or b is None:missing[road]+=1
            # Physical link/lane/position/lateral position/speed, not counters.
            if a is not None and b is not None and a[2:7]==b[2:7]:continue
            grouped[road]+=1
            record=dict(time_s=t,vehicle=vid,initial_link=int(before[2]),
                        none=[v.decode() for v in a] if a else None,
                        rm=[v.decode() for v in b] if b else None)
            if vid not in first_per_vehicle:first_per_vehicle[vid]=record
            if road not in first:first[road]=record
        by_time.append(dict(time_s=t,physical_differences_by_initial_road=dict(grouped),unmatched_presence=dict(missing)))
    d.e.save(out/'result.json',dict(status='MATCHED_INITIAL_COHORT_DIAGNOSTIC',initial_equal_rows=len(initial),
        first_by_initial_road=first,by_time=by_time,first_per_vehicle=first_per_vehicle,sources=receipts,
        comparison_columns=['link','lane','position','lateral_position','speed'],
        interpretation='A remote early difference would motivate an RNG/coupling audit, not establish a stochastic cause by itself.',
        no_new_native=True,future_inputs_to_plant=False,qualified=False,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    print('INITIAL_EQUAL',len(initial),'FIRST',first,flush=True)
    print('LAST',by_time[-1],flush=True)


if __name__=='__main__':main()
