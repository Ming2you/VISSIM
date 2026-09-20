"""Conserved lane transport identification inside the actual10484 merge cell.

Actual future speed, accepted upstream/merge entries and lane-change fractions
are supplied as diagnostic exposures. No future inventory reset or gain fit.
This is an identification calculation, not another production plant/adapter.
"""
from pathlib import Path
import sys,math,hashlib,time
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,CASES
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.state_exchange_20260920.analyze_dispersion import records
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.extract_observations import Observer

HERE=Path(__file__).resolve().parent
START,END=2400,2850


def grids(geometry):
    cell=next(c for c in geometry['cells'] if c['road']=='FW_E' and c['cell']==14)
    port=next(p for p in geometry['boundaries'] if p['connector']==10484)
    a,b,m=cell['start_m'],cell['end_m'],port['chain_pos_m']
    assert a<m<b and cell['canonical_segment_lanes']==3
    assert [p['connector'] for p in geometry['boundaries'] if p['road']=='FW_E' and a<p['chain_pos_m']<b]==[10484]
    return {1:[a,b],2:[a,m,b],4:[a,(a+m)/2,m,(m+b)/2,b]},cell,port


def extract(path,geometry):
    observer=Observer(geometry);edges,cell,port=grids(geometry);bins=edges[4];rows=[]
    previous={};frame={};last=None;balance_checks=0
    wanted={p['link'] for c in geometry['cells'] if c['road']=='FW_E' and c['cell'] in (13,14,15) for p in c['physical_pieces']}|{10484}
    def loc_bin(x):
        assert bins[0]<=x<bins[-1]
        return next(i for i in range(4) if x<bins[i+1])
    def process(t,current):
        nonlocal previous,balance_checks
        n=[[0]*3 for _ in range(4)];vs=[[0.]*3 for _ in range(4)]
        source=[0]*3;merge=[0]*3;out=[0]*3;exchanges=Counter()
        for vid,r in current.items():
            link,lane,x,v,c=r
            if c!=14:continue
            i=loc_bin(x);n[i][lane-1]+=1;vs[i][lane-1]+=v
            if t==START:continue
            old=previous.get(vid);assert old is not None,('Unobserved cell entry',t,vid,r)
            if old[4]==14:
                if old[1]!=lane:exchanges[loc_bin(old[2]),old[1]-1,lane-1]+=1
            elif old[4]==13:source[lane-1]+=1
            elif old[0]==10484:
                assert lane==1 and link==port['to_link'];merge[lane-1]+=1
            else:raise AssertionError(('Unexpected entry',t,vid,old,r))
        if t>START:
            for vid,old in previous.items():
                if old[4]!=14:continue
                r=current.get(vid)
                assert r is not None,('Missing cell vehicle',t,vid,old)
                if r[4]!=14:
                    assert r[4]==15,('Unexpected cell exit',t,vid,old,r)
                    out[old[1]-1]+=1
            prior=rows[-1]['n']
            for g in range(3):
                net=sum(q for (i,a,b),q in exchanges.items() if b==g)-sum(q for (i,a,b),q in exchanges.items() if a==g)
                assert sum(r[g] for r in n)==sum(r[g] for r in prior)+source[g]+merge[g]-out[g]+net
                balance_checks+=1
        rows.append(dict(t=t,n=n,v_sum=vs,source=source,merge=merge,out=out,
            exchange=[dict(bin=i,from_lane=a,to_lane=b,n=q) for (i,a,b),q in exchanges.items()]))
        previous=current
    before=path.stat()
    for p in records(path):
        t=int(float(p[0]))
        if t<START:continue
        if t>END:break
        if last is not None and t!=last:
            assert t==last+1;process(last,frame);frame={}
        last=t;link=int(p[2])
        if link not in wanted:continue
        lane=int(p[3]);pos=float(p[4]);v=float(p[6]);loc=observer.locate((link,lane,pos,v))
        c=loc[1] if loc and loc[0]=='FW_E' else None
        if c in (13,14,15) or link==10484:
            frame[int(p[1])]=(link,lane,loc[2] if c is not None else pos,v,c)
    assert last==END;process(last,frame)
    after=path.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    return dict(rows=rows,edges=edges,cell=cell,merge=port,native_lane_conservation_checks=balance_checks,
        source=dict(path=str(path.relative_to(e.ROOT)),bytes=before.st_size,mtime_ns=before.st_mtime_ns),
        definition='Lane changes within14 assigned at previous position before longitudinal movement; boundary entry uses receiving lane, exit uses previous lane. No post-intervention cross-run vehicle matching.')


def transport(data,parts):
    fields=data['rows'];edges=data['edges'][str(parts)] if str(parts) in data['edges'] else data['edges'][parts]
    stride=4//parts
    def aggregate(row,key):return [[sum(row[key][j][g] for j in range(i*stride,(i+1)*stride)) for g in range(3)] for i in range(parts)]
    n=aggregate(fields[0],'n');initial=sum(map(sum,n));initial_lanes=[sum(r[g] for r in n) for g in range(3)]
    lens=[(edges[i+1]-edges[i])/1000 for i in range(parts)]
    sums=aggregate(fields[0],'v_sum');vel=[]
    for i in range(parts):
        lane_v=[]
        for g in range(3):
            lane_n=initial_lanes[g];assert lane_n>0
            lane_v.append(sums[i][g]/n[i][g] if n[i][g] else sum(r[g] for r in sums)/lane_n)
        vel.append(lane_v)
    costs=[0.]*3;source=merge=outgoing=0.;trace=[];max_residual=max_density=max_cfl=0.;out_lanes=[0.]*3
    for j in range(450):
        now,nxt=fields[j:j+2];obs_n=aggregate(now,'n');obs_v=aggregate(now,'v_sum')
        vel=[[obs_v[i][g]/obs_n[i][g] if obs_n[i][g] else vel[i][g] for g in range(3)] for i in range(parts)]
        # Observed future switching fractions are exposures, not fixed actual
        # transfer amounts. Apply to predicted donor stocks, never reset them.
        changes=Counter((r['bin']//stride,r['from_lane'],r['to_lane']) for r in [])
        for r in nxt['exchange']:changes[r['bin']//stride,r['from_lane'],r['to_lane']]+=r['n']
        moving=[[0.]*3 for _ in range(parts)];incoming=[[0.]*3 for _ in range(parts)]
        for (i,a,b),q in changes.items():
            assert obs_n[i][a]>0
            amount=n[i][a]*q/obs_n[i][a];moving[i][a]+=amount;incoming[i][b]+=amount
        for i in range(parts):
            for g in range(3):assert moving[i][g]<=n[i][g]+1e-8
        n=[[n[i][g]-moving[i][g]+incoming[i][g] for g in range(3)] for i in range(parts)]
        cfl=[[v/3600/lens[i] for v in vel[i]] for i in range(parts)];max_cfl=max(max_cfl,max(map(max,cfl)))
        assert max_cfl<=1+1e-9
        sending=[[n[i][g]*cfl[i][g] for g in range(3)] for i in range(parts)]
        m=0 if parts==1 else parts//2
        n=[[n[i][g]-sending[i][g]+(sending[i-1][g] if i else nxt['source'][g])+
            (nxt['merge'][g] if i==m else 0.) for g in range(3)] for i in range(parts)]
        for g in range(3):costs[g]+=sum(r[g] for r in n)/3600;out_lanes[g]+=sending[-1][g]
        source+=sum(nxt['source']);merge+=sum(nxt['merge']);outgoing+=sum(sending[-1])
        residual=sum(map(sum,n))-initial-source-merge+outgoing;max_residual=max(max_residual,abs(residual));assert abs(residual)<1e-7
        assert min(map(min,n))>=-1e-9
        max_density=max(max_density,max(n[i][g]/lens[i] for i in range(parts) for g in range(3)))
        trace.append(dict(time_s=nxt['t'],n_by_lane=[sum(r[g] for r in n) for g in range(3)],
            observed_n_by_lane=[sum(r[g] for r in nxt['n']) for g in range(3)],
            cumulative_out_by_lane=list(out_lanes),ttt_by_lane=list(costs)))
    actual_costs=[sum(sum(r[g] for r in f['n']) for f in fields[1:])/3600 for g in range(3)]
    return dict(parts=parts,ttt=sum(costs),ttt_by_lane=costs,observed_ttt=sum(actual_costs),observed_ttt_by_lane=actual_costs,
        departures=outgoing,observed_departures=sum(sum(f['out']) for f in fields[1:]),
        upstream_entries=source,accepted_native_merges=merge,end_n=sum(map(sum,n)),observed_end_n=sum(map(sum,fields[-1]['n'])),
        n_rmse=math.sqrt(sum((sum(r['n_by_lane'])-sum(r['observed_n_by_lane']))**2 for r in trace)/len(trace)),
        conservation_max=max_residual,max_cfl=max_cfl,max_lane_density=max_density,trace=trace,
        caveat='Supply-free advection identification. No receiving capacity imposed; density is reported and cannot be used as a qualified storage model. Future velocities, accepted inflows/merges and lateral fractions are diagnostic inputs.')


def main():
    out=HERE/'merge_cell_transport_v1';out.mkdir(exist_ok=False);begun=time.perf_counter();result={};pins={}
    for seed in (23,33):
        case=next(r for r in CASES if r[0]==seed);geometry=e.ObservationData(case[1]).geometry;result[str(seed)]={}
        for arm in ('none','rm10484'):
            run=HERE/f'native_v1/none_s{seed}/run' if arm=='none' else HERE/f'direct10484_s{seed}_v1/rm10484/run'
            data=extract(run/'vissim_eval/baseline_001.fzp',geometry)
            e.save(out/f'fields_s{seed}_{arm}.json',data)
            sourcefolder=case[1] if arm=='none' else HERE/f'direct10484_s{seed}_v1/observations/rm10484'
            # Independent already-extracted boundary count and cell stock checks.
            observed=e.ObservationData(sourcefolder)
            for r in data['rows']:
                if r['t']%30==0:
                    expected=next(x['n_veh'] for x in observed.cells[r['t']] if x['road']=='FW_E' and x['cell']==14)
                    assert sum(map(sum,r['n']))==expected
            result[str(seed)][arm]={str(p):transport(data,p) for p in (1,2,4)}
            print(seed,arm,{p:{k:v for k,v in row.items() if k in ['ttt','observed_ttt','n_rmse','max_lane_density','departures','observed_departures']} for p,row in result[str(seed)][arm].items()},'elapsed',round(time.perf_counter()-begun,1),flush=True)
    for p in [Path(__file__),HERE/'flux_closure.py',H/'state_exchange_20260920/analyze_dispersion.py']:
        pins[str(p.relative_to(e.ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    deltas={s:{p:dict(predicted=arms['rm10484'][p]['ttt']-arms['none'][p]['ttt'],actual=arms['rm10484'][p]['observed_ttt']-arms['none'][p]['observed_ttt'],
        predicted_by_lane=[a-b for a,b in zip(arms['rm10484'][p]['ttt_by_lane'],arms['none'][p]['ttt_by_lane'])],
        actual_by_lane=[a-b for a,b in zip(arms['rm10484'][p]['observed_ttt_by_lane'],arms['none'][p]['observed_ttt_by_lane'])]) for p in arms['none']} for s,arms in result.items()}
    e.save(out/'result.json',dict(results=result,deltas=deltas,pins=pins,new_native_runs=0,future_inputs=True,qualified=False,production_adopted=False,
        scope='One493m cell14,3 physical lanes, exact merge location for2/4 parts. Boundary flows and speeds conditioned on each native arm; local identification only, not a full component forecast.'))
    print('DELTAS',deltas,flush=True)


if __name__=='__main__':main()
