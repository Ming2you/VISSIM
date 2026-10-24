"""Small cached snapshot context; lane-change state is NOT an event counter."""
from collections import Counter
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    rows=[];pins={}
    for arm in ('hold','release','hold_vsl90','release_vsl90'):
        p=h.R/'blocking176'/f'{arm}_frames.json.gz';pins[str(p)]=h.sha(p)
        d=h.read(p);ix={k:i for i,k in enumerate(d['fields'])}
        activity=Counter();slow=Counter();interaction=Counter();frames=0
        for t,fr in d['frames'].items():
            if not 2820.1<float(t)<=2970.1:continue
            frames+=1
            for z in fr.values():
                if z[ix['cell']] not in range(19,26):continue
                state=str(z[ix['lnchg']]);activity[state]+=1
                if z[ix['speed']]<5:slow[state]+=1
                if z[ix['cell']]==20 and z[ix['lane']]==1 and z[ix['speed']]<5:
                    interaction[str(z[ix['interaction']])]+=1
        assert frames==30
        rows.append(dict(arm=arm,frames=frames,vehicle_snapshots=sum(activity.values()),lane_change_state=dict(activity),
                         slow_vehicle_snapshots=dict(slow),cell20_lane1_slow_interaction=dict(interaction)))
    for p,digest in pins.items():assert h.sha(p)==digest
    h.save(HERE/'native_context.json',dict(rows=rows,input_sha256=pins,
        scope='Native cached ending5s snapshots2820.1<t<=2970.1, eastcells19-25. No FZP/native execution.',
        limitations='Counts are repeated vehicle snapshots of current LNCHG, not unique vehicles/events. Similar activity totals do not rule out differences in location, timing, lane-change initiation, duration or prior downstream propagation. Not an independent causal effect estimate.'))
    print(rows)


if __name__=='__main__':main()
