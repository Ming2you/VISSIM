"""Native10681 point headways and unchanged-gap-law opportunity audit.

Front crossings are linearly interpolated between consecutive1s positions.
They identify flow timing, not microscopic driver gap acceptance or causality.
"""
from pathlib import Path
import sys,math,hashlib,statistics
from bisect import bisect_left,bisect_right
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,CASES
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.state_exchange_20260920.analyze_dispersion import records
from evaluation.controllers.physical_ramp_boundary import gap_acceptance_supply_vph

HERE=Path(__file__).resolve().parent


def extract(path,port,head,start,end):
    before_stat=path.stat();previous={};frame={};last=None;crossings=[];merges=[];local=[]
    point=port['to_pos_m'];length=port['length_m']
    def process(t,current):
        nonlocal previous
        for g in (1,2):
            ramps=[r for r in current.values() if r[0]==10681 and r[1]==g]
            main=[r for r in current.values() if r[0]==2 and r[1]==g and abs(r[2]-point)<=50]
            terminal=[r for r in ramps if r[2]>=length-50]
            local.append(dict(time_s=t,lane=g,posthead_n=sum(r[2]>head for r in ramps),
                terminal_n=len(terminal),terminal_stopped=sum(r[3]<5 for r in terminal),
                terminal_front_distance=min([length-r[2] for r in terminal],default=None),
                main_n=len(main),main_speed_sum=sum(r[3] for r in main),main_stopped=sum(r[3]<5 for r in main)))
        if previous:
            for vid,r in current.items():
                old=previous.get(vid)
                if r[0]!=2 or old is None:continue
                if old[0]==2 and old[2]<point<=r[2]:
                    assert r[2]>old[2]
                    stamp=t-1+(point-old[2])/(r[2]-old[2]);assert t-1<stamp<=t
                    crossings.append(dict(time_s=stamp,frame_sec=t,vehicle=vid,lane=r[1],old_lane=old[1],
                        lane_changed=old[1]!=r[1],speed_before=old[3],speed_after=r[3]))
                elif old[0]==10681:
                    pre=length-old[2];post=r[2]-point
                    valid=pre>=0 and post>=0 and pre+post>0
                    stamp=t-1+pre/(pre+post) if valid else None
                    if valid:assert t-1<=stamp<=t
                    merges.append(dict(time_s=stamp,frame_sec=t,vehicle=vid,ramp_lane=old[1],main_lane=r[1],
                        speed_before=old[3],speed_after=r[3],interpolation_valid=valid,
                        distance_before=pre,distance_after=post))
        previous=current
    for p in records(path):
        t=int(float(p[0]))
        if t<start:continue
        if t>end:break
        if last is not None and t!=last:assert t==last+1;process(last,frame);frame={}
        last=t;link=int(p[2])
        if link in (10681,2):frame[int(p[1])]=(link,int(p[3]),float(p[4]),float(p[6]))
    assert last==end;process(last,frame)
    after=path.stat();assert (before_stat.st_size,before_stat.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    return dict(crossings=crossings,merges=merges,local=local,port=port,head_position_m=head,start=start,end=end,
        source=dict(path=str(path.relative_to(e.ROOT)),bytes=before_stat.st_size,mtime_ns=before_stat.st_mtime_ns))


def opportunities(crossings,tc,tf,start,end):
    times=sorted(r['time_s'] for r in crossings);slots=[]
    assert times and times[0]<start and times[-1]>end,('Censored outer headway',start,end)
    for a,b in zip(times,times[1:]):
        k=0
        while a+tc+k*tf<=b:
            t=a+tc+k*tf;k+=1
            if start<t<=end:slots.append(t)
    assert all(b-a>=tf-1e-8 for a,b in zip(slots,slots[1:]))
    return slots


def summarize(fields,tc,tf,start,end):
    result={};slot_rows=[]
    local={(r['time_s'],r['lane']):r for r in fields['local']}
    for lane in (1,2):
        crossing=sorted([r for r in fields['crossings'] if r['lane']==lane],key=lambda r:r['time_s'])
        slots=opportunities(crossing,tc,tf,start,end)
        clean=[r for r in crossing if not r['lane_changed']]
        clean_slots=opportunities(clean,tc,tf,start,end)
        times=[r['time_s'] for r in crossing];pairs=[]
        for merge in fields['merges']:
            if merge['ramp_lane']!=lane or not start<merge['frame_sec']<=end:continue
            t=merge['time_s']
            if t is None:continue
            j=bisect_right(times,t)
            if not 0<j<len(times):continue
            a,b=crossing[j-1],crossing[j]
            pairs.append(dict(**merge,preceding_time=a['time_s'],following_time=b['time_s'],
                mainline_gap=b['time_s']-a['time_s'],lead_headway=t-a['time_s'],lag_headway=b['time_s']-t,
                gap_lower=b['frame_sec']-1-a['frame_sec'],gap_upper=b['frame_sec']-(a['frame_sec']-1),
                adjacent_ambiguous_lane=a['lane_changed'] or b['lane_changed'],
                target_lane_matches=merge['main_lane']==lane,
                prior_terminal_stopped=local[merge['frame_sec']-1,lane]['terminal_stopped']))
        bins=[]
        for lo in range(start,end,150):
            hi=min(end,lo+150);count=sum(lo<r['time_s']<=hi for r in crossing)
            headways=[b-a for a,b in zip(times,times[1:]) if lo<b<=hi]
            q=count*3600/(hi-lo)
            passed=[r for r in fields['merges'] if r['ramp_lane']==lane and lo<r['frame_sec']<=hi]
            bins.append(dict(start=lo,end=hi,mainline_passes=count,mainline_q=q,
                headway_mean=statistics.mean(headways),headway_cv=statistics.pstdev(headways)/statistics.mean(headways),
                changed_lane_crossings=sum(lo<r['time_s']<=hi and r['lane_changed'] for r in crossing),
                actual_merges=len(passed),gap_slots=sum(lo<t<=hi for t in slots),
                gap_slots_excluding_ambiguous_mainline=sum(lo<t<=hi for t in clean_slots),
                poisson_opportunities=gap_acceptance_supply_vph(q,tc,tf)*(hi-lo)/3600,
                seconds_with_terminal_queue=sum(local[t,lane]['terminal_stopped']>0 for t in range(lo,hi))))
        result[str(lane)]=dict(bins=bins,merge_gap_pairs=pairs,total_actual_merges=sum(r['actual_merges'] for r in bins),
            total_slots=len(slots),total_poisson=sum(r['poisson_opportunities'] for r in bins),
            interpolation_valid_merges=len(pairs),target_lane_mismatch=sum(not r['target_lane_matches'] for r in pairs),
            merges_with_interpolated_gap_below_tc=sum(r['mainline_gap']<tc for r in pairs),
            statement='Interpolated front-headway assignment is not proof of accepted clear gap; mainline lane changes and1s ordering can confound it.')
        slot_rows.extend(dict(lane=lane,time_s=t) for t in slots)
    return result,slot_rows


def main():
    out=HERE/'merge10681_gap_v1';out.mkdir(exist_ok=False)
    config=HERE/'ramp_exchange_v1/evaluation/config.json';spec=e.load(config)['freeway']['physical_ramp_receiving_nodes']['RM_C10681']
    head=min(e.load(H/'controller_response_v1/heads.json')['10681'].values())
    sources=e.load(HERE/'lane_blocking_audit_v1/result.json')['results'];result={};checks=0
    pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [Path(__file__),config,H/'controller_response_v1/heads.json',H/'state_exchange_20260920/analyze_dispersion.py',
         e.ROOT/'evaluation/controllers/physical_ramp_boundary.py']}
    for seed in (13,23,33):
        _,folder,bank,_=next(r for r in CASES if r[0]==seed)
        for arm in (('none',) if seed==13 else ('none','vsl')):
            f=folder if arm=='none' else bank/'observations'/arm;data=e.ObservationData(f)
            port=next(r for r in data.geometry['boundaries'] if r['connector']==10681)
            path=(Path(e.load(f/'manifest.json')['source_run'])/'vissim_eval/baseline_001.fzp' if seed==13 else e.ROOT/sources[f'{seed}_{arm}']['source'])
            start,end=(900,2100) if seed==13 else (2400,2850)
            fields=extract(path,port,head,start-100,end+100)
            expected=Counter((int(float(r['time_s'])),int(r['vehicle']),int(r['lane'])) for r in e.rows(f/'port_events.csv')
                if r['connector']=='10681' and r['kind']=='departure' and start<float(r['time_s'])<=end)
            actual=Counter((r['frame_sec'],r['vehicle'],r['ramp_lane']) for r in fields['merges'] if start<r['frame_sec']<=end)
            assert actual==expected;checks+=sum(actual.values())
            values,slots=summarize(fields,spec['critical_gap_sec'],spec['followup_sec'],start,end)
            case=f'{seed}_{arm}';result[case]=values
            e.save(out/f'{case}_fields.json',fields);e.save(out/f'{case}_slots.json',slots)
            print(case,values['2']['bins'],'total',values['2']['total_actual_merges'],values['2']['total_slots'],flush=True)
            p=f/'port_events.csv';pins[str(p.relative_to(e.ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    for p,pin in pins.items():assert hashlib.sha256((e.ROOT/p).read_bytes()).hexdigest()==pin
    e.save(out/'result.json',dict(results=result,pins=pins,exact_merge_event_checks=checks,new_native_runs=0,fit_evaluations=0,
        coefficient_source=dict(critical_sec=spec['critical_gap_sec'],followup_sec=spec['followup_sec']),
        scope='Actual future headways at physical10681 merge. Slot ceiling only; eligibility/arrival/space still needed. Excluding ambiguous mainline events is a sensitivity ceiling, not a correction.',
        qualified=False,production_adopted=False))


if __name__=='__main__':main()
