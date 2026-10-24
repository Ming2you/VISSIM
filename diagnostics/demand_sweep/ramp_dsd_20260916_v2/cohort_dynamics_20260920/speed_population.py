"""Realizable speed/acceleration-phase populations: bounded local pilot.

No canonical adapter change. NativeNC transitions determine a stochastic
speed-state kernel. Positive populations conserve vehicles and derive moments.
"""
from pathlib import Path
from collections import defaultdict,Counter
import sys,bisect,math,hashlib,argparse,xml.etree.ElementTree as ET
from itertools import product
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import compact_lane_state as m
d=m.d;g=m.g
STEP=10.
MIN_SUPPORT=30.


def grid_from_network(path,spacing=STEP):
    root=ET.parse(path).getroot()
    max_desired=max(float(x.get('x')) for x in root.findall('./desSpeedDistributions/desSpeedDistribution/speedDistrDatPts/speedDistributionDataPoint'))
    # Keep the same enclosing upper bound when comparing numerical spacing.
    return np.arange(0,math.ceil(max_desired/STEP)*STEP+spacing/2,spacing),max_desired


def encode(v,phase,grid):
    assert -1e-9<=v<=grid[-1]+1e-9,('outside_grid',v)
    spacing=grid[1]-grid[0]
    j=min(len(grid)-1,int(v//spacing));frac=(v-grid[j])/spacing
    if j==len(grid)-1 or frac<1e-14:return [(phase*len(grid)+j,1.)]
    return [(phase*len(grid)+j,1-frac),(phase*len(grid)+j+1,frac)]


def transition_targets(node,before,after,next_phase,grid,kind):
    if kind=='absolute':return encode(after,next_phase,grid)
    if kind!='increment':raise ValueError(kind)
    # Translate the observed change through a bounded affine map. The
    # barycentric current weights retain the EXACT observed next mean, while
    # zero observed change gives identity in speed space. No clipping or
    # controlled-cost fitting is used to repair the old absolute-row mixing.
    current=grid[node%len(grid)]
    if after<before:
        assert before>0
        mapped=current*after/before
    elif after>before:
        assert before<grid[-1]
        mapped=current+(after-before)*(grid[-1]-current)/(grid[-1]-before)
    else:mapped=current
    return encode(mapped,next_phase,grid)


def phase(current,previous,edges=(-1.,1.)):
    if previous is None:return bisect.bisect_right(edges,0.)
    return bisect.bisect_right(edges,current-previous)


def moments(pop,grid):
    assert len(pop)%len(grid)==0
    speeds=np.tile(grid,len(pop)//len(grid));n=float(pop.sum())
    if n<=1e-12:return dict(n=0.,v=0.,sd=0.)
    avg=float(pop@speeds/n);variance=float(pop@(speeds*speeds)/n-avg*avg)
    assert variance>=-1e-8
    return dict(n=n,v=avg,sd=math.sqrt(max(0.,variance)))


def contexts(stats,c,geo,mode='basic'):
    r=stats[c];down=stats[c+1] if c<20 else r
    rho=r['n']/(geo[c]['length_km']*geo[c]['effective_lanes'])
    base=(bisect.bisect_right((15.,30.,50.),rho),bisect.bisect_right((-10.,10.),down['v']-r['v']))
    if mode=='basic':return base
    if mode=='mean_speed':return base+(bisect.bisect_right((30.,60.,90.),r['v']),)
    raise ValueError(mode)


def extract(frames,geometry,grid,train,kind='absolute',history_edges=(-1.,1.),context_mode='basic',train_range=(930,2099)):
    geo={r['cell']:r for r in geometry['cells'] if r['road']=='FW_E'}
    shifts={r['link']:r['offset_m'] for r in geometry['chains']['FW_E']}
    bounds=[geo[c]['end_m'] for c in sorted(geo)];size=(len(history_edges)+1)*len(grid)
    tables=[defaultdict(lambda:np.zeros(size)) for _ in range(3 if context_mode=='basic' else 4)]
    populations={};native={};counts=Counter();previous={}
    for t in sorted(frames):
        frame=frames[t];address={};ps={c:np.zeros(size) for c in range(14,21)};groups=defaultdict(list)
        for vid,row in frame.items():
            c=min(20,bisect.bisect_right(bounds,shifts[row['link']]+row['pos']));address[vid]=c
            if c<14:continue
            before=previous.get(vid);ph=phase(row['v'],before['v'] if before else None,history_edges)
            for k,w in encode(row['v'],ph,grid):ps[c][k]+=w
            groups[c].append(row['v'])
        stats={}
        for c in ps:
            vs=groups[c];n=len(vs);assert n
            avg=sum(vs)/n;sd2=sum((v-avg)**2 for v in vs)/n
            stats[c]=dict(n=float(n),v=avg,sd=math.sqrt(sd2));derived=moments(ps[c],grid)
            assert abs(derived['n']-n)<1e-8 and abs(derived['v']-avg)<1e-8
            inflation=derived['sd']**2-sd2
            assert -1e-7<=inflation<=(grid[1]-grid[0])**2/4+1e-7
            counts['representation_checks']+=1
        populations[t]=ps;native[t]=stats
        if train and train_range[0]<=t<=train_range[1]:
            nxt=frames[t+1]
            for vid,row in frame.items():
                c=address[vid]
                if c not in m.CELLS:continue
                if vid not in nxt:counts['training_next_row_censored']+=1;continue
                before=previous.get(vid);ph=phase(row['v'],before['v'] if before else None,history_edges)
                ph_next=phase(nxt[vid]['v'],row['v'],history_edges);context=contexts(stats,c,geo,context_mode)
                mapped_mean=0.
                for current,w0 in encode(row['v'],ph,grid):
                    target=transition_targets(current,row['v'],nxt[vid]['v'],ph_next,grid,kind)
                    mapped_mean+=w0*sum(w*grid[j%len(grid)] for j,w in target)
                    keys=((current%len(grid),),(current,),(*context,current)) if context_mode=='basic' else ((current%len(grid),),(current,),(context[2],current),(*context,current))
                    for bank,key in zip(tables,keys):
                        for future,w1 in target:bank[key][future]+=w0*w1
                assert abs(mapped_mean-nxt[vid]['v'])<1e-8
                counts['training_vehicle_transitions']+=1
        previous=frame
    return populations,native,tables,dict(counts)


def compile_kernel(tables,grid,phase_count=3,context_mode='basic'):
    size=phase_count*len(grid);result={};fallback=Counter()
    domains=(range(4),range(3)) if context_mode=='basic' else (range(4),range(3),range(4))
    for context in product(*domains):
            P=np.zeros((size,size))
            for current in range(size):
                options=((2,(*context,current)),(1,(current,)),(0,(current%len(grid),))) if context_mode=='basic' else ((3,(*context,current)),(2,(context[2],current)),(1,(current,)),(0,(current%len(grid),)))
                for level,key in options:
                    values=tables[level].get(key)
                    if values is not None and values.sum()>=MIN_SUPPORT:
                        P[current]=values/values.sum();fallback[level]+=1;break
                else:P[current,current]=1.;fallback['identity']+=1
            assert np.all(P>=0) and np.allclose(P.sum(axis=1),1.,atol=1e-12)
            result[context]=P
    return result,dict(fallback)


def step(old,rate,queue,geo,rho_max,grid,kernels,context_mode='basic'):
    stats={c:moments(p,grid) for c,p in old.items()};speeds=np.tile(grid,len(old[14])//len(grid))
    outgoing={c:old[c]*speeds/(geo[c]['length_km']*3600) for c in m.CELLS}
    space={c:max(0.,rho_max*geo[c]['length_km']*geo[c]['effective_lanes']-stats[c]['n']) for c in m.CELLS}
    for c in m.CELLS:
        assert np.all(outgoing[c]<=old[c]+1e-12)
        if c<20 and outgoing[c].sum()>space[c+1]:outgoing[c]*=space[c+1]/outgoing[c].sum()
    accepted=min(queue+rate,space[15]);newqueue=queue+rate-accepted
    source=old[14]*speeds
    if source.sum()==0:
        assert accepted<1e-12, 'Positive inflow with no moving source population'
        source=np.zeros_like(source)
    else:source*=accepted/source.sum()
    new={14:old[14].copy()};reacted_out={}
    for c in m.CELLS:
        P=kernels[contexts(stats,c,geo,context_mode)]
        new[c]=(old[c]-outgoing[c])@P
        reacted_out[c]=outgoing[c]@P
    for c in m.CELLS:new[c]+=source if c==15 else reacted_out[c-1]
    exits=float(outgoing[20].sum())
    for c in m.CELLS:
        assert np.all(new[c]>=-1e-10)
        assert new[c].sum()<=rho_max*geo[c]['length_km']*geo[c]['effective_lanes']+1e-8
        obs=moments(new[c],grid)
        assert obs['sd']**2<=obs['v']*(grid[-1]-obs['v'])+1e-7
    residual=sum(p.sum() for c,p in new.items() if c in m.CELLS)+newqueue+exits-sum(old[c].sum() for c in m.CELLS)-queue-rate
    assert abs(residual)<1e-8
    return new,newqueue,exits


def rollout(initial,rate,geo,rho_max,grid,kernels,horizon=30,context_mode='basic'):
    state={c:p.copy() for c,p in initial.items()};queue=0.;exits=0.;trace=[]
    n0=sum(state[c].sum() for c in m.CELLS)
    for dt in range(1,horizon+1):
        state,queue,q=step(state,rate,queue,geo,rho_max,grid,kernels,context_mode);exits+=q
        residual=sum(state[c].sum() for c in m.CELLS)+queue+exits-n0-dt*rate
        assert abs(residual)<1e-7
        trace.append(dict(step=dt,states={c:moments(p,grid) for c,p in state.items()},inlet_queue=queue,mass_residual=float(residual)))
    return trace,state


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--kind',choices=('absolute','increment'),default='increment')
    parser.add_argument('--spacing',type=float,choices=(10.,5.),default=10.)
    parser.add_argument('--phase-bins',type=int,choices=(3,5),default=3)
    parser.add_argument('--context',choices=('basic','mean_speed'),default='basic')
    args=parser.parse_args()
    history_edges=(-1.,1.) if args.phase_bins==3 else (-7.2,-1.,1.,7.2)
    suffix='' if args.phase_bins==3 else '_phase5'
    if args.context!='basic':suffix+='_'+args.context
    out=d.HERE/f'speed_population_{args.kind}_s{args.spacing:g}{suffix}_v1';out.mkdir(exist_ok=False)
    gp=d.H/'controller_response_s23_v1/none/geometry.json';geometry=d.e.load(gp)
    geo={r['cell']:r for r in geometry['cells'] if r['road']=='FW_E'}
    network=d.H/'source_dsd/baseline.inpx';grid,max_desired=grid_from_network(network,args.spacing)
    old_source=d.HERE/'compact_lane_state_v1/result.json';rho_max=d.e.load(old_source)['rho_max']
    aggregate_source=d.HERE/'compact_lane_state_v1/states.json';known=d.e.load(aggregate_source)
    banks={};receipts={};counts={};initials={};runs=[];conditional={};quantization_checks=0
    for arm in ('none','rm_ramp','vsl','both'):
        path=(d.H/'rules_4500_s23_v1/run_none/vissim_eval/baseline_001.fzp' if arm=='none'
              else d.H/'response_late_s23_v1'/f'run_{arm}/vissim_eval/baseline_001.fzp')
        frames,receipts[arm]=g.read(path,False,899 if arm=='none' else 2249)
        ps,native,tables,counts[arm]=extract(frames,geometry,grid,arm=='none',args.kind,history_edges,args.context);del frames
        entry={int(t):v for t,v in known[arm]['entry'].items()}
        for t,rows in native.items():
            for c,r in rows.items():
                prior=known[arm]['states'][str(t)][str(c)]
                assert r['n']==prior['n'] and abs(r['v']-prior['v'])<1e-8;quantization_checks+=1
        if arm=='none':
            kernels,fallback=compile_kernel(tables,grid,args.phase_bins,args.context)
            kernel_doc={str(k):v.tolist() for k,v in kernels.items()}
            d.e.save(out/'model.json',dict(grid=grid.tolist(),max_native_desired_speed=max_desired,kernels=kernel_doc,
                transition_kind=args.kind,spacing_kmh=args.spacing,history_edges_kmh=list(history_edges),context_mode=args.context,
                fallback_rows=fallback,min_support=MIN_SUPPORT,train_start=930,train_last_cutoff=2099,train_last_label=2100,
                tables=[{str(k):v.tolist() for k,v in bank.items()} for bank in tables]))
        intervals=[('control',2400,2850)]+([('time_validation',2100,2400)] if arm=='none' else [])
        for label,lo,hi in intervals:
            ev=[];en=[]
            for t in range(lo,hi):
                rate=sum(entry[s] for s in range(t-29,t+1))/30
                nxt,queue,exits=step(ps[t],rate,0.,geo,rho_max,grid,kernels,args.context)
                for c in m.CELLS:
                    r=moments(nxt[c],grid);ev.append(r['v']-native[t+1][c]['v']);en.append(r['n']-native[t+1][c]['n'])
            conditional[arm,label]=dict(n=len(ev),speed_rmse=math.sqrt(sum(x*x for x in ev)/len(ev)),n_mae=sum(abs(x) for x in en)/len(en))
        initials[arm]={}
        for start in (2280,2400,2550,2700):
            rate=sum(entry[t] for t in range(start-29,start+1))/30
            trace,state=rollout(ps[start],rate,geo,rho_max,grid,kernels,context_mode=args.context)
            ev=[];en=[]
            for row in trace:
                for c in m.CELLS:ev.append(row['states'][c]['v']-native[start+row['step']][c]['v']);en.append(row['states'][c]['n']-native[start+row['step']][c]['n'])
            runs.append(dict(arm=arm,start_s=start,status='completed',speed_rmse=math.sqrt(sum(x*x for x in ev)/len(ev)),
                n_mae=sum(abs(x) for x in en)/len(en),max_mass_residual=max(abs(r['mass_residual']) for r in trace),
                final_queue=trace[-1]['inlet_queue'],final_states=trace[-1]['states']))
            initials[arm][str(start)]=dict(populations={str(c):p.tolist() for c,p in ps[start].items()},rate=rate)
        print('SCORED',arm,[(r['start_s'],round(r['speed_rmse'],3)) for r in runs if r['arm']==arm],flush=True)
        del ps,native
    d.e.save(out/'initials.json',initials)
    paths=[Path(__file__),Path(g.__file__),gp,network,old_source,aggregate_source,out/'model.json',out/'initials.json']
    d.e.save(out/'result.json',dict(status='REALIZABLE_SPEED_POPULATION_LOCAL_GATE_NOT_QUALIFIED',
        transition_kind=args.kind,spacing_kmh=args.spacing,history_edges_kmh=list(history_edges),context_mode=args.context,grid=grid.tolist(),counts=counts,quantization_snapshot_checks=quantization_checks,
        conditional={str(k):v for k,v in conditional.items()},autonomous_runs=runs,source_receipts=receipts,
        pins={str(p.relative_to(d.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        limitations=['Local6-cell30s pilot, upstream control response and off-ramp costs not yet connected.',
            'Nonnegative stochastic transitions and conserved speed-dependent transport guarantee feasible moments, not accurate dynamics.',
            f'{args.spacing:g}km/h barycentric grid preserves counts and mean exactly; initial variance inflation bounded by{args.spacing**2/4:g}(km/h)^2. Repeated remapping can still diffuse velocities.',
            f'Kernel context={args.context}: density/downstream mean-speed difference, optionally current cell mean speed, own speed node and acceleration phase; no exact gaps/order.',
            'The grid maximum210km/h encloses the native desired-speed distributions; unsupported recorded speeds fail instead of clipping.',
            'Frozen current upstream population and past30s flow only in autonomous rollout; no future observations.',
            'Training and all tests use inspected seed23. No independent holdout, full450s or gain qualification.'],
        qualified=False,production_changes=0,new_native_runs=0))
    print('CONDITIONAL',conditional,flush=True)


if __name__=='__main__':main()
