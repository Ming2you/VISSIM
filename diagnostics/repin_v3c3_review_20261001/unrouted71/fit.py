"""One causal, state-conditioned compatible-lane exchange candidate."""
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from evaluation.controllers.physical_urban_transport import ReceivingEnvelope,observe,geometry,unassigned_continuation

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
REVIEW=HERE.parent


def main():
    assert not (HERE/'fit.json').exists()
    source=REVIEW/'lane10643_native/rows.json.gz'
    cache=json.loads(gzip.decompress(source.read_bytes()))
    prior=json.loads((REVIEW/'merge126_allocation/assessment.json').read_bytes())
    g=prior['models']['baseline_hold']['geometry']
    manifest=json.loads((REVIEW/'retained10638/candidate_manifest.json').read_bytes())
    network=ROOT/manifest['sources']['network']['path']
    assert hashlib.sha256(network.read_bytes()).hexdigest()==manifest['sources']['network']['sha256']
    routes,exits=geometry(network)
    epochs=defaultdict(list)
    for r in cache['rows']:
        if 2550<=r[0]<2700 and r[2]==71:
            epochs[r[0]].append([r[1],r[2],r[3],r[4],r[5],r[13],r[6],r[7],r[8],r[9],r[10],r[11],r[12],None,None])
    times=sorted(epochs)
    assert len(times)==30
    weights={};observations={};exposure=0.;events=[];unsupported=[]
    edges=g['edges']['71'];max_projection=0.
    for t in times:
        obs=observe({'time_s':t,'vehicles':epochs[t]},routes,exits)
        observations[t]={v['vehicle']:v for v in obs['vehicles']}
        fractions={};room={}
        for lane in range(1,6):
            cars=sorted((v for v in obs['vehicles'] if v['lane']==lane),key=lambda v:v['position_m'])
            env=ReceivingEnvelope(edges[-1],g['spacing'],g['speed'],g['wave'],[min(edges[-1],v['position_m']) for v in cars])
            max_projection=max(max_projection,env.projection_max_m)
            for cell,(a,b) in enumerate(zip(edges,edges[1:])):
                n=0.
                for v,pos in zip(cars,env.positions):
                    fraction=max(0.,min(b,pos)-max(a,pos-g['spacing']))/g['spacing']
                    fractions[v['vehicle'],cell]=fraction;n+=fraction
                room[lane,cell]=max(0.,min(g['capacity_rate'],g['wave']/(b-a)*((b-a)/g['spacing']-n)))
        for vid,v in observations[t].items():
            dest=v['connector'];lane=v['lane']
            if not unassigned_continuation(v,routes):continue
            for other in (lane-1,lane+1):
                if not 1 <= other <= 5:continue
                weight=sum(fractions[vid,c]*max(0.,room[other,c]-room[lane,c])/g['capacity_rate'] for c in range(len(edges)-1))
                weights[t,vid,other]=weight
                if t<times[-1]:exposure+=5*weight
    for a,b in zip(times,times[1:]):
        assert abs(b-a-5)<1e-6
        for vid,v in observations[a].items():
            new=observations[b].get(vid)
            if not new or new['lane']==v['lane'] or new['connector']!=v['connector']:continue
            key=(a,vid,new['lane'])
            if key not in weights:continue
            row=dict(vehicle=vid,start=a,end=b,from_lane=v['lane'],to_lane=new['lane'],destination=v['connector'],weight=weights[key])
            (events if weights[key]>1e-9 else unsupported).append(row)
    assert exposure>0 and events
    out=dict(status='single_past_only_fit_not_qualified',coefficient_per_s=len(events)/exposure,
        formula='lambda_ij = alpha * max(0, R_j - R_i) / q_max; only adjacent lanes of route-free continuation vehicles on71; no assigned destination is changed',
        fit_window=[times[0],times[-1]],information_cutoff=2700,weighted_exposure_veh_s=exposure,
        supported_events=events,unsupported_pressure_direction_events=unsupported,max_projection_m=max_projection,
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),network_sha256=manifest['sources']['network']['sha256'],
        limitations=['5s changes are not an exact event census or instantaneous hazard estimate.',
          'Future native rows never used for fitting; only seed47 before2700.',
          'One coefficient shared by unassigned71 adjacent lanes in both directions; no fixed turn fraction; sparse-data candidate only.'])
    (HERE/'fit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(out,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
