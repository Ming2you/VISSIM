"""Compare spatial gradients in21--25 with the exact eight cached records."""
import ctypes
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    assert not (HERE/'recovery_profile.json').exists()
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=ctypes.c_void_p
    kernel.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    original=h.read(HERE/'spatial.json');pins=original['pins']
    assert all(h.sha(p)==v for p,v in pins.items())
    bounds=h.read(h.F/'route_inventory/mapping31.json')['freeway_model_links']['FW_E']['segment_bounds_m']
    files=[]
    for arm in ('hold','hold_vsl90','release','release_vsl90'):files.append(('67_'+arm,h.R/f'blocking176/{arm}_frames.json.gz',2670.1))
    for arm in ('hold','hold_vsl90'):files.append(('29_'+arm,h.F/f'vsl_native_exposure/s29_late_{arm}_frames.json.gz',2670.1))
    for arm in ('none','vsl'):files.append(('43_'+arm,h.F/f'cohort_early/s43_{arm}_frames.json.gz',2220.1))
    profiles=[];initial=[];moments=[]
    for case,path,start in files:
        doc=h.read(path);ix={k:i for i,k in enumerate(doc['fields'])}
        vi=ix.get('speed',ix.get('speed_kmh'));xi=ix.get('x',ix.get('x_m'));ci=ix['cell'];li=ix['lane']
        frames={round(float(t),1):(list(a.values()) if isinstance(a,dict) else a) for t,a in doc['frames'].items()}
        for cell in range(21,26):
            left,right=bounds[cell:cell+2];mid=(left+right)/2
            for lane in (1,2,3):
                for block in range(3):
                    groups=[[],[]];differences=[];opposed=0;valid=0
                    for j in range(30):
                        t=round(start+block*150+(j+1)*5,1)
                        rs=[r for r in frames[t] if r[ci]==cell and r[li]==lane]
                        halves=[[r for r in rs if int(r[xi]>=mid)==part] for part in (0,1)]
                        assert sum(map(len,halves))==len(rs)
                        assert all(left-1e-6<=r[xi]<=right+1e-6 for r in rs)
                        for part,z in enumerate(halves):groups[part].extend(z)
                        vs=[sum(r[vi] for r in a)/len(a) if a else None for a in halves]
                        if all(v is not None for v in vs):
                            valid+=1;differences.append(vs[1]-vs[0]);opposed+=min(vs)<20 and max(vs)>60
                        moments.append(dict(case=case,cell=cell,lane=lane,block=block,time=t,
                            before_n=len(halves[0]),after_n=len(halves[1]),before_v=vs[0],after_v=vs[1]))
                    profiles.append(dict(case=case,cell=cell,lane=lane,block=block,length_m=right-left,
                        n=[len(a)/30 for a in groups],slow=[sum(r[vi]<5 for r in a)/30 for a in groups],
                        v=[sum(r[vi] for r in a)/len(a) if a else None for a in groups],
                        simultaneous_halves=valid,mean_signed_down_minus_up=sum(differences)/len(differences) if differences else None,
                        mean_abs_gradient=sum(map(abs,differences))/len(differences) if differences else None,
                        mixed_slow20_fast60_snapshots=opposed))
    # Exact same endpoint/partition definition reproduces the completed21 audit.
    for old in original['groups']:
        p=next(z for z in profiles if z['case']==old['case'] and z['cell']==21 and z['lane']==old['lane'] and z['block']==old['block'])
        part=old['part'];assert p['n'][part]==old['mean_n'] and p['slow'][part]==old['mean_slow']
        a,b=p['v'][part],old['vehicle_sample_speed'];assert (a is None and b is None) or abs(a-b)<1e-10
    assert all(h.sha(p)==v for p,v in pins.items())
    h.save(HERE/'recovery_profile.json',dict(profiles=profiles,moments=moments,cell21_original_exact=True,
        source_sha256=h.sha(__file__),input_pins=pins,
        definition='Both halves have vehicles for gradients; empty half is unknown speed, not freeflow. Fixed geometric midpoint,5s right endpoints.20/60kmh contrast is a declared descriptive screen, not a calibrated traffic threshold.',
        scope='Saved21--25 support only; no model change, calibration or rollout.'))
    print('PROFILE_COMPLETE',len(profiles),len(moments))
    for p in profiles:
        if p['case'].startswith('67_release') and p['block']==1 and p['lane']==1:print(p)


if __name__=='__main__':main()
