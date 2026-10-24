"""Past-only head-to-ramp lane evidence. No future observations or rollout."""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from evaluation.controllers import obs150_contract as oc

HERE=Path(__file__).resolve().parent
RECORDING=Path('D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47')

def main():
    heads=defaultdict(list); arrivals=[]; pins={}; tails=[]; run_id=None
    for end in (2250,2400,2550,2700):
        p=RECORDING/f'state_{end:06d}.json'; data=p.read_bytes(); pins[str(p)]=hashlib.sha256(data).hexdigest()
        raw=json.loads(data); assert raw['sim_sec']==end<=2700
        bundle=oc.load_bundle(raw)
        if run_id is None:run_id=bundle.obs['run_id']
        assert bundle.obs['run_id']==run_id
        rows,_=oc.read_detector_csv(bundle.obs['detector_config']['path'],bundle.obs['detector_config']['sha256'])
        assignment=oc.assign_window(bundle.obs,bundle.mer_rows)
        for d in rows:
            if d.role=='head' and d.link in (52,66,46):
                tails.append(dict(end=end,role=d.role,link=d.link,lane=d.lane,count=assignment.tails[d.dcp_no]))
                for r in assignment.entries[d.dcp_no]:heads[r.veh].append((r.t_entry,d.link,d.lane))
            if d.role=='ramp_arrival' and d.link==10681 and end>2250:
                tails.append(dict(end=end,role=d.role,link=d.link,lane=d.lane,count=assignment.tails[d.dcp_no]))
                arrivals.extend(dict(veh=r.veh,time=r.t_entry,lane=d.lane) for r in assignment.entries[d.dcp_no])
    assert not any(r['count'] for r in tails), 'A causal lane prior requires complete saved endpoints'
    pairs=[]
    for e in sorted(arrivals,key=lambda r:r['time']):
        preceding=[h for h in heads[e['veh']] if h[0]<=e['time']]
        source=max(preceding) if preceding else None
        pairs.append(dict(**e,origin_link=None if source is None else source[1],
            head_time=None if source is None else source[0],head_lane=None if source is None else source[2]))
    summaries={}
    for width in (150,450):
        subset=[p for p in pairs if 2700-width<p['time']<=2700]
        groups=defaultdict(Counter)
        for e in subset:groups[str(e['origin_link'])][str(e['lane'])]+=1
        summaries[str(width)]={k:dict(lane_counts=dict(v),count=sum(v.values()),lane1_share=v['1']/sum(v.values())) for k,v in groups.items()}
        counts=Counter(e['lane'] for e in subset)
        summaries[str(width)]['all']=dict(count=sum(counts.values()),lane_counts=dict(counts),lane1_share=counts[1]/sum(counts.values()))
    out=dict(status='COMPLETE_CAUSAL_EVIDENCE_ONLY',cutoff_sec=2700,arrival_history_start_sec=2250,head_history_start_sec=2100,
        full_forecasts=0,local_replays=0,new_native=0,FZP=0,fit=0,future_observations=False,
        run_id=run_id,input_sha256=pins,tail_counts=tails,windows=summaries,pairs=pairs,
        limitations=['Prior completed trips only; long trips and unmatched source heads remain explicit.',
                    'Endpoint lane association does not prove an intermediate lane-change model or native mainline receiving budget.',
                    'No future lane fractions substituted and no candidate adopted.'])
    (HERE/'causal_arrival_origins.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=out['status'],windows=summaries)))

if __name__=='__main__':main()
