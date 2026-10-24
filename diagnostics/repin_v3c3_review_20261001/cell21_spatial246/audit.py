"""Saved within-cell21 spatial support, before deciding a smaller mesh."""
import ctypes
import json
import math
from pathlib import Path
import time
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    assert not (HERE/'spatial.json').exists()
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=ctypes.c_void_p
    kernel.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    started=time.perf_counter();mapping=h.F/'route_inventory/mapping31.json'
    bounds=h.read(mapping)['freeway_model_links']['FW_E']['segment_bounds_m']
    left,right=bounds[21:23];mid=(left+right)/2
    files=[]
    for arm in ('hold','hold_vsl90','release','release_vsl90'):
        files.append(('67_'+arm,h.R/f'blocking176/{arm}_frames.json.gz',2670.1))
    for arm in ('hold','hold_vsl90'):
        files.append(('29_'+arm,h.F/f'vsl_native_exposure/s29_late_{arm}_frames.json.gz',2670.1))
    for arm in ('none','vsl'):
        files.append(('43_'+arm,h.F/f'cohort_early/s43_{arm}_frames.json.gz',2220.1))
    pins={str(p):h.sha(p) for p in [Path(__file__),mapping,*[r[1] for r in files]]}
    groups=[];initial={};checks=0
    for case,path,start in files:
        doc=h.read(path);ix={k:i for i,k in enumerate(doc['fields'])}
        vi=ix.get('speed',ix.get('speed_kmh'));xi=ix.get('x',ix.get('x_m'));ci=ix['cell'];li=ix['lane']
        frames={round(float(t),1):(list(a.values()) if isinstance(a,dict) else a) for t,a in doc['frames'].items()}
        data={(block,lane,part):[] for block in range(3) for lane in (1,2,3) for part in (0,1)}
        initial[case]=[]
        for step in range(91):
            t=round(start+5*step,1);rows=[r for r in frames[t] if r[ci]==21]
            assert all(left-1e-6<=r[xi]<=right+1e-6 for r in rows)
            partitions={(lane,part):[r for r in rows if r[li]==lane and int(r[xi]>=mid)==part] for lane in (1,2,3) for part in (0,1)}
            assert sum(map(len,partitions.values()))==len(rows);checks+=1
            if step==0:
                initial[case]=[dict(lane=l,part=p,n=len(rs),v=sum(r[vi] for r in rs)/len(rs) if rs else None) for (l,p),rs in partitions.items()]
                continue
            for (lane,part),rs in partitions.items():
                data[(step-1)//30,lane,part].append(dict(n=len(rs),slow=sum(r[vi]<5 for r in rs),speed_sum=sum(r[vi] for r in rs)))
        for (block,lane,part),rs in data.items():
            assert len(rs)==30;n=sum(r['n'] for r in rs)
            groups.append(dict(case=case,block=block,lane=lane,part=part,mean_n=n/30,
                mean_slow=sum(r['slow'] for r in rs)/30,vehicle_sample_speed=sum(r['speed_sum'] for r in rs)/n if n else None))
    assert all(h.sha(p)==v for p,v in pins.items())
    h.save(HERE/'spatial.json',dict(cell21=dict(start_m=left,end_m=right,length_m=right-left,mid_m=mid,half_length_m=(right-left)/2),
        interval='right5s endpoints, three150s blocks; current positions only, not exact event residence',groups=groups,initial=initial,
        partition_checks=checks,pins=pins,seconds=time.perf_counter()-started,
        limitation='Fixed midpoint chosen before inspection; descriptive state partition, not dynamic-model or benefit qualification.'))
    print(json.dumps(dict(checks=checks,groups=len(groups),length=right-left,seconds=time.perf_counter()-started)))
    for r in groups:
        if r['case'].startswith('67_release') and r['lane']==1 and r['block']==1:print(json.dumps(r))


if __name__=='__main__':main()
