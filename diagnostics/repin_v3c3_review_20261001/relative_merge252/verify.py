"""Reconstruct all event quantities from the pinned raw caches independently."""
import json
import math
from collections import defaultdict
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE = Path(__file__).resolve().parent/'verified'


def main():
    done = h.read(HERE/'completion.json'); assert done['status']=='complete'
    protocol = h.read(HERE/'protocol.json'); pins = h.read(HERE/'pins.json')
    for p,d in {**pins,**protocol['protected_sha256'],protocol['STOP']['path']:protocol['STOP']['sha256']}.items():
        assert h.sha(p)==d,p
    frames={};rampframes={}
    for arm in ('hold','release','hold_vsl90','release_vsl90'):
        data=h.read(h.R/f'blocking176/{arm}_frames.json.gz')
        index={k:i for i,k in enumerate(data['fields'])}
        frames[arm]={round(float(t),1):{vid:{k:row[j] for k,j in index.items()} for vid,row in rows.items()} for t,rows in data['frames'].items()}
        rampframes[arm]={round(float(t),1):rows for t,rows in h.read(h.R/f'ramp_motion187/s67_late_{arm}_ramps.json.gz')['frames'].items()}
    errors=[];count=0;missing=0;raw=defaultdict(list)
    for r in h.read(HERE/'events.json'):
        f=frames[r['arm']][r['lo']];lane=[x['speed'] for x in f.values() if x['cell']==r['cell'] and x['lane']==1]
        assert len(lane)==r['n_lane']
        before=rampframes[r['arm']][r['lo']][r['vehicle']][2]
        assert before==r['v_ramp_before']
        if not lane:
            assert r['positive_gap_before'] is r['unit_gap_before'] is None
            missing+=1;continue
        v=math.fsum(lane)/len(lane)
        gap=(v-before+abs(v-before))/2
        errors += [abs(v-r['v_lane']),abs(gap-r['positive_gap_before']),abs(gap/r['denominator']-r['unit_gap_before'])]
        post=frames[r['arm']][r['hi']][r['vehicle']]['speed']
        postgap=(v-post+abs(v-post))/2
        errors.append(abs(postgap-r['positive_gap_after']))
        raw[r['arm'],r['connector'],r['block']].append((v,before,gap,postgap))
        count+=1
    # Pre-control30s states and merge events are exactly common across all arms.
    states=h.read(HERE/'states.json')
    common={}
    for r in states:
        if r['lo']>=2700.1:continue
        key=(r['connector'],r['lo']);comparison={k:v for k,v in r.items() if k!='arm'}
        if key in common:assert comparison==common[key]
        else:common[key]=comparison
    compact=[]
    for (arm,con,block),rows in raw.items():
        compact.append(dict(arm=arm,connector=con,block=block,events=len(rows),
            mean_pre_lane_speed=sum(x[0] for x in rows)/len(rows),
            mean_last_ramp_speed=sum(x[1] for x in rows)/len(rows),
            mean_positive_gap=sum(x[2] for x in rows)/len(rows),
            mean_positive_gap_postproxy=sum(x[3] for x in rows)/len(rows)))
    assert count+missing==646 and max(errors)<1e-10 and len(common)==12
    h.save(HERE/'unscaled_event_speeds.json',compact)
    result=dict(status='PASS',matched_event_checks=count,empty_lane_unknown=missing,
                current_and_post_speed_gap_max_error=max(errors),precontrol_common_state_keys=len(common),
                preserved=True,fits=0,forecasts=0,native=0,FZP=0,qualified=False)
    h.save(HERE/'verification.json',result);print(json.dumps(result))


if __name__=='__main__':main()
