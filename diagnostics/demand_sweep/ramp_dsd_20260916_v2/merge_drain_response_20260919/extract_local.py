"""One offline FZP pass per arm; local merge lanes and off-ramp speed profiles."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.merge_drain_response_20260919.audit import *
from diagnostics.analyze_no_control_corridors import native_frames
from collections import defaultdict
import csv, time


def main():
    out=HERE/'local_native_v1';out.mkdir(exist_ok=False)
    runs=[(13,'none',H/'rules_4500_v1/run_none'),
          (33,'none',H/'state_response_20260919/native_s33_v1/run_none'),
          (33,'rm_ramp',H/'state_response_20260919/native_s33_v1/run_rm_ramp'),
          (23,'none',H/'rules_4500_s23_v1/run_none'),
          (23,'rm_ramp',H/'response_late_s23_v1/run_rm_ramp')]
    geometry=e.load(H/'controller_response_4500_v1/none/geometry.json')
    ramp=next(b for b in geometry['boundaries'] if b['id']=='RM_C10484')
    point=ramp['to_pos_m'];link=ramp['to_link']
    for seed,arm,run in runs:
        dest=out/f'{seed}_{arm}';dest.mkdir()
        path=run/'vissim_eval/baseline_001.fzp'
        receipt=e.load(run/'run.json');assert receipt['completed']
        assert e.load(run/'fixed_validation.json')['passed']
        before={};series=[];crossings=[];merges=[];speedbins=defaultdict(lambda:[0,0.,0])
        evidence={};wall=time.perf_counter()
        for sec,frame in native_frames(path,evidence,deadline=time.monotonic()+600):
            # Record all4500s once; no live COM reads and no inference from
            # upstream average density to the actual merging lane.
            local=[(veh,r) for veh,r in frame.items() if r[0]==link and point-100<=r[2]<=point+100]
            for lane in [1,2,3]:
                ls=[r for veh,r in local if r[1]==lane]
                series.append({'time_s':sec,'lane':lane,'n':len(ls),'speed_sum':sum(r[3] for r in ls),
                    'below5':sum(r[3]<5 for r in ls),'below30':sum(r[3]<30 for r in ls)})
            for veh,r in frame.items():
                prev=before.get(veh)
                if r[0]==link and prev is not None:
                    if prev[0]==link and prev[2]<point<=r[2]:
                        stamp=sec-1+(point-prev[2])/(r[2]-prev[2])
                        crossings.append({'time_s':stamp,'vehicle':veh,'lane':r[1],
                            'speed_kmh':r[3],'changed_lane':int(prev[1]!=r[1])})
                    elif prev[0]==10484:
                        merges.append({'time_s':sec,'vehicle':veh,'lane':r[1],
                            'before_speed':prev[3],'after_speed':r[3]})
                if r[0] in [10483,10682]:
                    key=((sec-1)//150*150,r[0],int(max(0,r[2])//50)*50)
                    row=speedbins[key];row[0]+=1;row[1]+=r[3];row[2]+=r[3]<5
            before=frame
        for name,rows in [('merge_lane_1s',series),('mainline_crossings',crossings),('merges',merges),
                          ('off_speed_bins',[dict(start_s=k[0],connector=k[1],position_m=k[2],samples=v[0],speed_sum=v[1],below5=v[2]) for k,v in sorted(speedbins.items())])]:
            with (dest/(name+'.csv')).open('x',newline='',encoding='utf-8') as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        write(dest/'evidence.json',{'native':str(path.relative_to(ROOT)),**evidence,
            'wall_sec':time.perf_counter()-wall,'merge_point':ramp,
            'lane_zone':'200m total:100m before and after physical ramp merge, same mainline link',
            'crossing_rule':'Front position brackets fixed merge point in consecutive1s frames; linear time interpolation; ramps excluded'})
        print('EXTRACTED',seed,arm,evidence['rows'],round(time.perf_counter()-wall,1),flush=True)


if __name__=='__main__':main()
