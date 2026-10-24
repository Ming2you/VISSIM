"""Read-only native10681 lane/stage accounting to test independent buffers."""
from pathlib import Path
import sys,hashlib
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,CASES
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.state_exchange_20260920.analyze_dispersion import records

HERE=Path(__file__).resolve().parent
START,END=2400,2850


def extract(path,head,length):
    previous={};frame={};last=None;rows=[];events=[];exchanges=[];checks=0
    stats=path.stat()
    def process(t,current):
        nonlocal previous,checks
        ramp={vid:r for vid,r in current.items() if r[0]==10681}
        before={vid:r for vid,r in previous.items() if r[0]==10681}
        n=Counter(r[1] for r in ramp.values());delta=Counter()
        for vid,r in ramp.items():
            if vid in before:
                old=before[vid]
                if old[1]!=r[1]:
                    exchanges.append(dict(time_s=t,vehicle=vid,from_lane=old[1],to_lane=r[1],
                        from_position_m=old[2],position_m=r[2],speed_kmh=r[3],
                        stage='prehead' if r[2]<head else 'posthead'))
                    delta[old[1]]-=1;delta[r[1]]+=1
            elif t>START:
                assert vid in previous and previous[vid][0]==68,('Unobserved ramp arrival',t,vid,r)
                events.append(dict(time_s=t,vehicle=vid,kind='arrival',lane=r[1]));delta[r[1]]+=1
        if t>START:
            for vid,old in before.items():
                if vid not in ramp:
                    assert vid in current and current[vid][0]==2,('Unobserved ramp departure',t,vid,old)
                    events.append(dict(time_s=t,vehicle=vid,kind='departure',lane=old[1]));delta[old[1]]-=1
            oldn=Counter(r[1] for r in before.values())
            for lane in (1,2):assert n[lane]==oldn[lane]+delta[lane];checks+=1
        rows.append(dict(time_s=t,lanes=[dict(lane=g,n=n[g],
            prehead=sum(r[1]==g and r[2]<head for r in ramp.values()),
            stopped=sum(r[1]==g and r[3]<5 for r in ramp.values()),
            sum_speed=sum(r[3] for r in ramp.values() if r[1]==g),
            last50_n=sum(r[1]==g and r[2]>length-50 for r in ramp.values()),
            last50_stopped=sum(r[1]==g and r[2]>length-50 and r[3]<5 for r in ramp.values())) for g in (1,2)]))
        previous=current
    for p in records(path):
        t=int(float(p[0]))
        if t<START:continue
        if t>END:break
        if last is not None and t!=last:assert t==last+1;process(last,frame);frame={}
        last=t;link=int(p[2])
        if link in (68,10681,2):frame[int(p[1])]=(link,int(p[3]),float(p[4]),float(p[6]))
    assert last==END;process(last,frame)
    after=path.stat();assert (stats.st_size,stats.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    return dict(rows=rows,events=events,exchanges=exchanges,lane_conservation_checks=checks,
        source=dict(path=str(path.relative_to(e.ROOT)),bytes=stats.st_size,mtime_ns=stats.st_mtime_ns))


def main():
    out=HERE/'ramp_lane_inventory_v1';out.mkdir(exist_ok=True)
    if (out/'result.json').exists():raise FileExistsError('Completed result must not be overwritten')
    source=e.load(HERE/'lane_blocking_audit_v1/result.json')['results']
    head=min(e.load(H/'controller_response_v1/heads.json')['10681'].values())
    results={};pins={};checks=0
    for seed in (23,33):
        _,folder,bank,_=next(r for r in CASES if r[0]==seed)
        for arm in ('none','vsl'):
            case=f'{seed}_{arm}';data=e.ObservationData(folder if arm=='none' else bank/'observations'/arm)
            port=next(p for p in data.geometry['boundaries'] if p['connector']==10681)
            fields=extract(e.ROOT/source[case]['source'],head,port['length_m'])
            actual=[r for r in e.rows(data.folder/'port_events.csv') if r['connector']=='10681' and START<float(r['time_s'])<=END]
            expected=Counter((int(float(r['time_s'])),int(r['vehicle']),r['kind'],int(r['lane'])) for r in actual)
            assert Counter((r['time_s'],r['vehicle'],r['kind'],r['lane']) for r in fields['events'])==expected
            for row in fields['rows']:
                if row['time_s']%30:continue
                observed=Counter(int(r[2]) for r in data.port_cohorts[str(row['time_s'])]['10681'])
                for r in row['lanes']:assert r['n']==observed[r['lane']];checks+=1
            summary={}
            for g in (1,2):
                lane=[r['lanes'][g-1] for r in fields['rows'][1:]]
                ev=Counter(r['kind'] for r in fields['events'] if r['lane']==g)
                entering=sum(r['to_lane']==g for r in fields['exchanges'])
                leaving=sum(r['from_lane']==g for r in fields['exchanges'])
                initial=fields['rows'][0]['lanes'][g-1]['n'];end=lane[-1]['n']
                assert initial+ev['arrival']-ev['departure']+entering-leaving==end
                summary[str(g)]=dict(initial_n=initial,end_n=end,arrivals=ev['arrival'],departures=ev['departure'],
                    changed_into=entering,changed_out=leaving,net_exchange=entering-leaving,
                    ttt=sum(r['n'] for r in lane)/3600,prehead_ttt=sum(r['prehead'] for r in lane)/3600,
                    speed=sum(r['sum_speed'] for r in lane)/sum(r['n'] for r in lane),
                    last50_seconds_stopped=sum(r['last50_stopped']>0 for r in lane))
            directions=Counter((r['from_lane'],r['to_lane'],r['stage']) for r in fields['exchanges'])
            results[case]=dict(lanes=summary,exchange_counts=[dict(from_lane=a,to_lane=b,stage=c,count=n) for (a,b,c),n in directions.items()],
                lane_conservation_checks=fields['lane_conservation_checks'],events_exact=True)
            checks+=fields['lane_conservation_checks'];e.save(out/f'{case}.json',fields)
            p=data.folder/'port_events.csv';pins[str(p.relative_to(e.ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
            print(case,results[case],flush=True)
    for p in [Path(__file__),H/'controller_response_v1/heads.json',HERE/'lane_blocking_audit_v1/result.json',
              H/'state_exchange_20260920/analyze_dispersion.py']:
        pins[str(p.relative_to(e.ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    e.save(out/'result.json',dict(results=results,checks=checks,pins=pins,new_native_runs=0,production_adopted=False,
        scope='Actual physical lane changes inside10681,1s stock and boundary counts. Net transfers are not merge-service losses. No future observations supplied to a forecast.'))


if __name__=='__main__':main()
