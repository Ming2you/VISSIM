"""Closed ordinal detector events: upstream head to10681 entry timing.

These are matched vehicle observations, not a new model input or a fit.
Unmatched/censored/tail events stay unassigned; no disappearance is an exit.
"""
from pathlib import Path
from collections import Counter,defaultdict
import ctypes,hashlib,json,statistics,sys

HERE=Path(__file__).resolve().parent;H=HERE.parent;ROOT=HERE.parents[3]
sys.path[:0]=[str(ROOT),str(H)]
from evaluation.controllers import obs150_contract as oc
from evaluation.controllers.obs150_observation import check_rule_crosscheck
from qualify_native2400 import validate_scope
RUNS=Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29')
PINS={};W={68,121,10772,10625,10629,10633}
def read(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return json.loads(b)
def pin(p):PINS[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    output=HERE/'native_timing.json';assert not output.exists()
    validate_scope(read(H/'native2400_analysis/summary.json'),read(H/'native2400_analysis/observed_input_qualification.json'))
    results={}
    for arm in ('hold','selected'):
        folder=RUNS/arm/f'decisions_sdmpc31_g_2400_{arm}_s29'
        heads=defaultdict(list);arrivals=[];flows=[];snapshots={};tail_count=0
        for end in (2400,2550,2700,2850):
            raw=read(folder/f'state_{end:06}.json');b=oc.load_bundle(raw);o=b.obs
            ds,_=oc.read_detector_csv(o['detector_config']['path'],o['detector_config']['sha256'])
            oc.validate_raw(o,ds,expected_simres=10);check_rule_crosscheck(o,ds)
            for p in [Path(o['detector_config']['path']),folder/o['mer']['chunk'],folder/o['err']['chunk'],
                      folder/o['frames']['previous']['path'],folder/o['frames']['current']['path']]:pin(p)
            assigned=oc.assign_window(o,b.mer_rows)
            assert b.frame_start['complete'] and b.frame_end['complete']
            snapshots[end-150]={v[0]:v for v in b.frame_start['vehicles']}
            snapshots[end]={v[0]:v for v in b.frame_end['vehicles']}
            boundaries=oc.evaluate_boundaries(o,ds,b.frame_end,b.frame_start,b.err_rows)
            counts={}
            for d in ds:
                if d.role=='head' and ((d.link==52 and d.lane in (1,2,3)) or (d.link==66 and d.lane==4)):
                    counts[f'{d.link}:{d.lane}']=boundaries[d.boundary_ref].cross
                    for e in assigned.entries[d.dcp_no]:heads[e.veh].append(dict(t=e.t_entry,link=d.link,lane=d.lane))
                if d.boundary_ref=='ramp_arrival:RM_C10681' and end>2400:
                    assert d.pos==1. and d.orientation=='down'
                    arrivals.extend(dict(vehicle=e.veh,t=e.t_entry,window=end-150,lane=d.lane) for e in assigned.entries[d.dcp_no])
                    tail_count+=assigned.tails[d.dcp_no]
            if end>2400:flows.append(dict(start_sec=end-150,head_counts_by_lane=counts))
        initial=snapshots[2400];matched=[];unmatched=[]
        assert len({(x['vehicle'],x['t']) for x in arrivals})==len(arrivals)
        for event in arrivals:
            vid=event['vehicle'];v=initial.get(vid)
            group='initial_W_out' if v and v[1] in W else 'later_inflow'
            earlier=[x for x in heads.get(vid,[]) if x['t']<=event['t']]
            if not earlier:
                unmatched.append(dict(**event,initial_group=group,initial_link=v[1] if v else None));continue
            head=max(earlier,key=lambda x:x['t']);duration=event['t']-head['t']
            # Keep any actual route evidence seen before the head. This is
            # reported separately from the two-detector identity match.
            seen=[(t,frame[vid]) for t,frame in snapshots.items() if t<=head['t'] and vid in frame and frame[vid][1]==head['link']]
            witness=None
            if seen:
                t,x=max(seen,key=lambda y:y[0]);witness=dict(time=t,link=x[1],lane=x[2],position=x[3],decision=x[6],route=x[7],type=x[8])
            matched.append(dict(**event,initial_group=group,head=head,travel_sec=duration,source_route_witness=witness))
        bins=[]
        for start in (2400,2550,2700):
            by_source={}
            for link in (52,66):
                values=[x['travel_sec'] for x in matched if x['window']==start and x['head']['link']==link]
                by_source[str(link)]=dict(matched=len(values),median_sec=statistics.median(values) if values else None,
                                         min_sec=min(values) if values else None,max_sec=max(values) if values else None)
            bins.append(dict(start_sec=start,by_source=by_source,
                matched_later_inflow=sum(x['window']==start and x['initial_group']=='later_inflow' for x in matched),
                unmatched_by_initial_group=dict(Counter(x['initial_group'] for x in unmatched if x['window']==start))))
        results[arm]=dict(head_counts=flows,matched=matched,unmatched=unmatched,unassigned_mer_tails=tail_count,windows=bins)
    PINS[str(Path(__file__))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report=dict(status='complete',arms=results,new_rollouts=0,new_fits=0,new_native=0,fzp_scans=0,source_pins=PINS,
        limitations=['Travel time is between source head and downstream1m ramp detector, not exact boundary0m.',
        'Only vehicles crossing both observed detectors are matched; right-turn46 branches before its head and remains unmatched.',
        'Matching two detectors does not prove every intermediate link; current-route witnesses are separate.',
        'Observed duration distribution is censored by windows2250-2850; it is not an uncensored population estimate or fitted delay.',
        'Ordinal tail events and initial1m boundary corrections have no exact matched timestamps; no invented timing.',
        'Future observations are diagnostic only; never a rollout input.'])
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({a:{k:r[k] for k in ('head_counts','windows','unassigned_mer_tails')} for a,r in results.items()},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
