"""Exact initial lane inventory and ID-witnessed access in the clean150 interval."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;H=HERE.parent
PINS={}
def read(path):
    data=path.read_bytes();PINS[str(path)]=hashlib.sha256(data).hexdigest();return json.loads(data)
def main():
    assert not (HERE/'cohort_check.json').exists()
    result=read(HERE/'forecast2700_v3/summary.json')
    initial,final=result['known_initial_cohorts'],result['known_endpoint_cohorts']
    audit=read(HERE/'audit.json')['arms']['selected']
    frame=audit['snapshots'][2]
    assert frame['time_sec']==2700 and sum(c['vehicles'] for c in initial)==56
    timing=read(H/'shared_lane_space/native_timing.json')['arms']['selected']
    arrivals=[r for r in timing['matched']+timing['unmatched'] if r['window']==2700]
    ids={r['vehicle'] for r in arrivals};assert len(ids)==len(arrivals)
    key=lambda c:tuple(c['lane68']['order'])
    chosen=[c for c in initial if c['target']=='RM_C10681' and 'lane68' in c]
    assert len(chosen)==len({key(c) for c in chosen})==20
    rows=[]
    for lane in ('1','2','3','4'):
        observed=frame['lanes'][lane]
        projected=sum(c['vehicles']*c.get('lane68',{}).get('shares',{}).get(lane,0.) for c in initial)
        assert projected==observed['count']
        native_ids={v['id'] for v in observed['vehicles'] if v['decision']==1135 and v['route']==4}
        cohorts=[c for c in chosen if c['lane68']['shares'].get(lane,0)==1]
        assert len(native_ids)==sum(c['vehicles'] for c in cohorts)
        keys={key(c) for c in cohorts}
        remaining=sum(c['vehicles'] for c in final if c['source']=='initial_current_route' and c['target']=='RM_C10681'
                      and 'lane68' in c and key(c) in keys)
        assert native_ids<=ids
        rows.append(dict(initial_lane=lane,initial_stock=projected,initial_known_RM=len(native_ids),
            native_ID_verified_ramp_entries=len(native_ids&ids),native_entered_ids=sorted(native_ids&ids),
            predicted_initial_known_RM_remaining=remaining,
            predicted_initial_known_RM_entries=len(native_ids)-remaining))
    for path,digest in read(HERE/'plan.json')['source_pins'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
    output=dict(status='passed_initial_stock_projection_and_native_ID_witnesses',rows=rows,
        new_rollouts=0,new_native=0,new_fits=0,source_pins=PINS,
        conclusion='Exact2700 lane counts still leave7.23 of8 original lane4 RM vehicles in model; all8 actually enter10681 without W_out removal. Local lateral-access/recovery is insufficient beyond propagated initial error.',
        limits=['Two observed detector crossings do not reveal microscopic lane-change locations or exact gap trajectories.',
                'This diagnosis does not identify a replacement rate/formula or qualify whole450 control gain.'])
    (HERE/'cohort_check.json').write_text(json.dumps(output,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
