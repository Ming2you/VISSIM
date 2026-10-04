"""Reproduce168 lane-state snapshots from existing files without forecasting."""
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

def main():
    p=Path(__file__).resolve().parent;out=[];pins={str(Path(__file__)):h.sha(__file__)}
    def read(path):pins[str(path)]=h.sha(path);return h.read(path)
    for arm in ('release','release_vsl90'):
        d=read(h.F/f'flow67/{arm}_frames.json.gz')
        frames={round(float(t),6):[dict(zip(d['fields'],r)) for r in f.values()] for t,f in d['frames'].items()}
        paths=[('148',h.R/f'spatial_context148/forecast/training/s67_late_{arm}.json.gz')]
        paths += [(m,p/f'forecast/{m}/s67_late_{arm}.json.gz') for m in ('regional','state')]
        for mode,path in paths:
            pred=read(path);rows=pred['diagnostics']['roads'][0]['joint_lane_region']['rows']
            states={(round(r['time_s'],6),r['cell'],r['lane']):r for r in rows}
            for cell in range(19,26):
                for lane in range(1,4):
                    for dt in (5,30,150,300,450):
                        t=round(2670.1+dt,6)
                        a=[x for x in frames[t] if x['cell']==cell and x['lane']==lane]
                        r=states[t,cell,lane];n=len(a)
                        v=sum(x['speed_kmh'] for x in a)/n if n else None
                        out.append(dict(mode=mode,arm=arm,cell=cell,lane=lane,elapsed_s=dt,
                            observed_n=n,predicted_n=r['n_veh'],observed_v=v,predicted_v=r['v_kmh']))
    payload=dict(rows=out,definition='Observed5s endpoint lane stocks/speeds versus completed autonomous forecasts at same elapsed time; no future state reset or new forecasts.')
    if (p/'state_recurrence.json').exists():
        assert read(p/'state_recurrence.json')==payload
    else:h.save(p/'state_recurrence.json',payload)
    for path,digest in pins.items():assert h.sha(path)==digest,path
    h.save(p/'recurrence_verification.json',dict(status='pass',snapshots=len(out),input_sha256=pins,new_forecasts=0))
    print('PASS',len(out),'snapshots')

if __name__=='__main__':main()
