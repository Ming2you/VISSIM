"""Extract normal off-ramp space/queue motion and measure start-wave delays.

Existing native recordings only. Pair identity and lane adjacency must survive
from a joint stop to both starts. These are observations, not a capacity fit.
"""
from pathlib import Path
import sys
import argparse
import hashlib
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,CASES
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.off_entry_space_audit import quantiles

HERE=Path(__file__).resolve().parent


def extract(seed,folder,bank):
    manifest=e.load(folder/'manifest.json');run=Path(manifest['source_run'])
    if not run.is_absolute():run=(e.ROOT/run).resolve()
    receipt=e.load(run/'run.json');assert receipt['completed']
    path=run/'vissim_eval/baseline_001.fzp';before=path.stat()
    data=e.ObservationData(folder)
    expected={kind:{(int(float(r['time_s'])),int(r['vehicle'])) for r in e.rows(folder/'port_events.csv')
                    if r['connector']=='10643' and r['kind']==kind} for kind in ('arrival','departure')}
    frames=[];current={};last=None;previous={};checks=0;snapshots=0
    digest=hashlib.sha256()
    def finish(t,vehicles):
        nonlocal previous,checks,snapshots
        if not 900<=t<=4500:return
        if frames:
            assert t==frames[-1]['time_s']+1
            arrived=set(vehicles)-set(previous);left=set(previous)-set(vehicles)
            assert all((t,v) in expected['arrival'] for v in arrived),(seed,t,'arrival')
            assert all((t,v) in expected['departure'] for v in left),(seed,t,'departure')
            assert len(vehicles)-len(previous)==len(arrived)-len(left)
            checks+=1
        if t%30==0:
            known=sorted((float(p),float(v),int(l)) for p,v,l in data.port_cohorts[str(t)]['10643'])
            actual=sorted((p,v,l) for l,p,v in vehicles.values())
            assert known==actual,(seed,t,'existing snapshot changed');snapshots+=1
        frames.append({'time_s':t,'vehicles':[[vid,*row] for vid,row in sorted(vehicles.items())]})
        previous=vehicles
    with path.open('rb') as stream:
        for line in stream:
            digest.update(line)
            if not line[:1].isdigit():continue
            parts=line.rstrip(b'\r\n;').split(b';');t=int(float(parts[0]))
            if last is not None and t!=last:
                finish(last,current);current={}
            last=t
            if 900<=t<=4500 and parts[2]==b'10643':
                vid=int(parts[1]);assert vid not in current
                current[vid]=(int(parts[3]),float(parts[4]),float(parts[6]))
    if last is not None:finish(last,current)
    after=path.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    assert frames[0]['time_s']==900 and frames[-1]['time_s']==4500
    assert digest.hexdigest()==manifest['fzp']['file_sha256']
    return {'seed':seed,'source':str(path.relative_to(e.ROOT)),'sha256':digest.hexdigest(),
            'bytes':before.st_size,'normal_event_checks':checks,'snapshot_matches':snapshots,'frames':frames}


def wave_events(frames):
    active={};events=[];censored=Counter()
    for frame in frames:
        t=frame['time_s'];groups={l:sorted((p,vid,v) for vid,lane,p,v in frame['vehicles'] if lane==l) for l in (1,2)}
        pairs={}
        for lane,rows in groups.items():
            for follower,leader in zip(rows,rows[1:]):
                pairs[lane,leader[1],follower[1]]=(leader,follower)
        for key,a in active.items():
            if key not in pairs and a.get('leader_start') is not None:censored['adjacency_lost_after_leader_start']+=1
        next_active={}
        for key,(leader,follower) in pairs.items():
            a=active.get(key,{'streak':0,'armed':False,'leader_start':None})
            lp,li,lv=leader;fp,fi,fv=follower
            if lv<1 and fv<1:
                if a['leader_start'] is not None:
                    censored['leader_stopped_again_before_follower_start']+=1
                    a={'streak':0,'armed':False,'leader_start':None}
                a['streak']+=1
                if a['streak']>=3:
                    a.update(armed=True,gap_m=lp-fp,joint_stop_s=t)
            else:
                a['streak']=0
            if a['armed']:
                if a['leader_start'] is None and lv>=5:
                    a.update(leader_start=t,queue_n=sum(v<5 for _,_,v in groups[key[0]]),stock=len(groups[key[0]]))
                if fv>=5:
                    if a['leader_start'] is None:censored['follower_starts_before_leader']+=1
                    else:
                        lag=t-a['leader_start']
                        events.append({'lane':key[0],'leader':li,'follower':fi,
                            'leader_start_s':a['leader_start'],'follower_start_s':t,'lag_s':lag,
                            'stopped_gap_m':a['gap_m'],'stopped_queue_n':a['queue_n'],'lane_stock':a['stock'],
                            'backward_wave_m_s':a['gap_m']/lag if lag>0 else None})
                    a={'streak':0,'armed':False,'leader_start':None}
                elif a['leader_start'] is not None and t-a['leader_start']>60:
                    censored['lag_over60']+=1;a={'streak':0,'armed':False,'leader_start':None}
            next_active[key]=a
        active=next_active
    return events,dict(censored)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',default='off_space_wave_v1');args=ap.parse_args()
    out=HERE/args.output;out.mkdir(exist_ok=False)
    result={}
    for seed,folder,bank,start in CASES:
        recording=extract(seed,folder,bank);e.save(out/f's{seed}_frames.json',recording)
        events,censored=wave_events(recording['frames'])
        summary={}
        for lane in (1,2):
            rows=[r for r in events if r['lane']==lane]
            useful=[r for r in rows if r['lag_s']>0 and r['stopped_gap_m']<=20]
            summary[str(lane)]={'events':len(rows),'zero_lag_at_1s_resolution':sum(r['lag_s']==0 for r in rows),
                'positive_lag_adjacent_within20m':len(useful),'lag_s':quantiles([r['lag_s'] for r in useful]),
                'wave_m_s':quantiles([r['backward_wave_m_s'] for r in useful]),
                'by_queue':{label:{'n':len(selected),'lag_s':quantiles([r['lag_s'] for r in selected])}
                    for label,selected in [(label,[r for r in useful if lo<=r['stopped_queue_n']<=hi])
                        for label,lo,hi in [('0..15',0,15),('16..30',16,30),('31+',31,1000)]]}}
        result[str(seed)]={'summary':summary,'events':events,'censored':censored,
                          'normal_event_checks':recording['normal_event_checks'],'snapshot_matches':recording['snapshot_matches']}
        print(seed,summary,flush=True)
    e.save(out/'result.json',{'results':result,'scope':'NC10643 only; normal events verified against prior native extraction',
        'new_native_runs':0,'parameter_fit':False,'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'definition':'Same-lane adjacent pair jointly below1km/h for>=3s; leader then follower reaches5km/h, without losing adjacency. Zero-lag events retained but not converted to infinite wave speed.',
        'caveat':'One-second threshold crossing and heterogeneous headways; pair start delay is not whole-link travel time or proof of a constant LWR wave speed.'})


if __name__=='__main__':main()
