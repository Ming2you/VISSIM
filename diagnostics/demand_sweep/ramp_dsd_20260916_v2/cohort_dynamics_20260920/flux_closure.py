"""Native point outflow versus spatial Nv/L, without another simulation.

The within-interval velocities are an offline closure diagnostic, not causal
forecast inputs. Counts at each cell boundary are not unique network exits.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,CASES
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.state_exchange_20260920.analyze_dispersion import records
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.extract_observations import Observer
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.lane_group_response_20260919.extract import group
from collections import defaultdict,Counter
import csv
import time
import argparse
import math
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent

# These contiguous regions have no sources, ramps, exits or lane-count changes.
# The resolution experiment isolates longitudinal transport, not a control law.
REGIONS={'before10643':(5,8),'after10682':(10,12),'downstream':(15,20)}


def off_exit_routes(geometry):
    """Resolve a1s frame that skips a very short receiving-link remainder."""
    root=ET.parse(H/'source_dsd/baseline.inpx').getroot();links={int(n.get('no')):n for n in root.findall('./links/link')}
    routes={}
    for p in geometry['boundaries']:
        if p['road']!='FW_E' or p['kind']!='offramp':continue
        end=links[p['connector']].find('toLinkEndPt')
        assert int(end.get('lane').split()[0])==p['to_link']
        assert abs(float(end.get('pos'))-p['to_pos_m'])<1e-8
        routes[p['connector']]={}
        for link,node in links.items():
            begin=node.find('fromLinkEndPt')
            if begin is None or int(begin.get('lane').split()[0])!=p['to_link']:continue
            gap=float(begin.get('pos'))-p['to_pos_m']
            if gap>=0:routes[p['connector']][link]=p['length_m'],gap
    return routes


def skipped_off_exit(old,now,routes):
    if now is None or now[0] not in routes.get(old[0],{}):return False
    length,gap=routes[old[0]][now[0]]
    distance=max(0.,length-old[1])+gap+now[1]
    return distance<=max(old[2],now[2])/3.6+3.


def resolution_fields(path, geometry, start=2400, end=2850):
    observer=Observer(geometry);bounds=geometry['bounds']['FW_E']
    for name,(a,b) in REGIONS.items():
        assert not any(p['road']=='FW_E' and bounds[a]<p['chain_pos_m']<bounds[b]
                       for p in geometry['boundaries']),name
        cells=[c for c in geometry['cells'] if c['road']=='FW_E' and a<=c['cell']<b]
        assert len({round(c['effective_lanes'],6) for c in cells})==1,name
    rows={name:[] for name in REGIONS};previous={};frame={};last=None
    def process(t,current):
        nonlocal previous
        for name,(a,b) in REGIONS.items():
            n=[0.]*(4*(b-a));vs=[0.]*len(n);arrivals=departures=0;unexplained=0
            for vid,loc in current.items():
                if a<=loc[0]<b:
                    c,x,v=loc;part=min(3,int(4*(x-bounds[c])/(bounds[c+1]-bounds[c])))
                    j=4*(c-a)+part;n[j]+=1;vs[j]+=v
                    if t>start and not (vid in previous and a<=previous[vid][0]<b):
                        if vid not in previous or previous[vid][0]>=a:unexplained+=1
                        else:arrivals+=1
            if t>start:
                for vid,loc in previous.items():
                    if a<=loc[0]<b and not (vid in current and a<=current[vid][0]<b):
                        if vid not in current or current[vid][0]<b:unexplained+=1
                        else:departures+=1
            assert unexplained==0,(name,t,unexplained)
            if rows[name]:
                assert sum(n)==sum(rows[name][-1]['n'])+arrivals-departures,(name,t)
            rows[name].append({'t':t,'n':n,'v_sum':vs,'in':arrivals,'out':departures})
        previous=current
    for p in records(path):
        t=int(float(p[0]))
        if t<start:continue
        if t>end:break
        if last is not None and last!=t:
            assert t==last+1;process(last,frame);frame={}
        last=t
        loc=observer.locate((int(p[2]),int(p[3]),float(p[4]),float(p[6])))
        if loc and loc[0]=='FW_E':frame[int(p[1])]=(loc[1],loc[2],float(p[6]))
    assert last==end;process(last,frame)
    return rows


def transport(fields, lengths, parts, step):
    """Conservative upwind advection conditioned on future actual speed/input.

    No fitted parameters, inventory resets, receiving bonus or disappearance.
    Empty observed bins retain their last speed, initialized from current coarse
    speed. Measured boundary entries are supplied as actual accepted entries.
    Storage violations are reported, not hidden by deleting/rejecting vehicles.
    """
    assert parts in (1,2,4) and step in (1,10)
    stride=4//parts;size=len(fields[0]['n'])//stride
    def aggregate(row,key):return [sum(row[key][i:i+stride]) for i in range(0,len(row[key]),stride)]
    n=aggregate(fields[0],'n');initial=sum(n);v=[]
    for i in range(size):
        native_n=n[i];c=i//parts
        coarse_n=sum(fields[0]['n'][c*4:c*4+4])
        assert native_n or coarse_n,'No initial speed for entirely empty coarse cell'
        v.append(aggregate(fields[0],'v_sum')[i]/native_n if native_n else
                 sum(fields[0]['v_sum'][c*4:c*4+4])/coarse_n)
    lens=[l/parts for l in lengths for _ in range(parts)]
    ttt=outgoing=entered=0.;max_residual=max_cfl=max_density=0.;trace=[]
    for k in range(0,len(fields)-1,step):
        row=fields[k];native_n=aggregate(row,'n');native_vsum=aggregate(row,'v_sum')
        v=[s/a if a else old for a,s,old in zip(native_n,native_vsum,v)]
        dt=min(step,len(fields)-1-k)
        cfl=[speed*dt/3600/l for speed,l in zip(v,lens)]
        max_cfl=max(max_cfl,max(cfl))
        sending=[min(stock,stock*f) for stock,f in zip(n,cfl)]
        arrival=sum(r['in'] for r in fields[k+1:k+dt+1])
        n=[stock-q+(sending[i-1] if i else arrival) for i,(stock,q) in enumerate(zip(n,sending))]
        assert min(n)>=-1e-9
        entered+=arrival;outgoing+=sending[-1];ttt+=sum(n)*dt/3600
        residual=sum(n)-initial-entered+outgoing
        max_residual=max(max_residual,abs(residual))
        assert abs(residual)<1e-7
        max_density=max(max_density,max(stock/l for stock,l in zip(n,lens)))
        trace.append({'t':fields[k+dt]['t'],'n':sum(n),'observed_n':sum(fields[k+dt]['n'])})
    # Per-cell density is all-lane; caller compares it to physical lanes*jam.
    return {'ttt_veh_h':ttt,'observed_ttt_veh_h':sum(sum(r['n']) for r in fields[1:])/3600,
            'end_n':sum(n),'observed_end_n':sum(fields[-1]['n']),
            'out':outgoing,'observed_out':sum(r['out'] for r in fields[1:]),
            'n_rmse':math.sqrt(sum((r['n']-r['observed_n'])**2 for r in trace)/len(trace)),
            'max_conservation_residual':max_residual,'max_cfl':max_cfl,
            'max_alllane_density':max_density,'trace':trace}


def resolution_experiment(out, cases):
    results={};sources={}
    for seed,arms in cases.items():
        geometry=e.ObservationData(next(r[1] for r in CASES if r[0]==seed)).geometry
        results[seed]={};bounds=geometry['bounds']['FW_E']
        for arm,run in arms.items():
            path=run/'vissim_eval/baseline_001.fzp';before=path.stat()
            fields=resolution_fields(path,geometry)
            after=path.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
            e.save(out/f'fields_s{seed}_{arm}.json',fields);results[seed][arm]={}
            for name,(a,b) in REGIONS.items():
                lengths=[(bounds[c+1]-bounds[c])/1000 for c in range(a,b)]
                results[seed][arm][name]={f'parts{p}_dt{dt}':transport(fields[name],lengths,p,dt)
                                        for p,dt in [(1,10),(1,1),(2,1),(4,1)]}
            sources[f'{seed}_{arm}']={'source':str(run.relative_to(e.ROOT)),'bytes':before.st_size,
                                     'mtime_ns':before.st_mtime_ns,'unexplained_transitions':0}
            print('RESOLUTION',seed,arm,flush=True)
    e.save(out/'results.json',results);e.save(out/'protocol.json',{
        'status':'DIAGNOSTIC_ONLY_FUTURE_SPEED_AND_BOUNDARY_INPUT',
        'scope':'Port-free all-lane stretches;450s conservative transport, no causal control prediction',
        'future_inventory_resets':0,'fitted_parameters':0,'native_runs_started':0,
        'sources':sources,'regions':REGIONS,'grid_parts':[1,2,4],'step_sec':[1,10]})


def component_balance(path, geometry, start=2400, end=2850):
    """Native residence identity with each external interface separately counted."""
    observer=Observer(geometry)
    ports={int(p['connector']):p for p in geometry['boundaries']
           if p['road']=='FW_E' and p['kind'] in ('ramp','offramp')}
    source_links={int(p['to_link']) for p in geometry['boundaries'] if p['road']=='FW_E' and p['kind']=='source'}
    terminal=geometry['chains']['FW_E'][-1];terminal_link=int(terminal['link'])
    exit_routes=off_exit_routes(geometry)
    previous={};frame={};last=None;initial=None;ttt=0.;moments=Counter();counts=Counter();unknown=[]
    origins={};cohort_residence=Counter();initial_ids=set()
    trace=[]
    bytime=defaultdict(Counter)
    def process(t,current):
        nonlocal previous,initial,ttt
        inside={vid:r for vid,r in current.items() if r[4] is not None}
        prior={vid:r for vid,r in previous.items() if r[4] is not None}
        if t==start:
            initial=len(inside);initial_ids.update(inside)
            origins.update({vid:'initial_'+r[4] for vid,r in inside.items()})
        else:
            ttt+=len(inside)/3600
            for vid,r in inside.items():
                if vid in prior:continue
                link,pos,speed,loc,kind=r
                if kind=='on':name='on_arrival_'+str(link)
                elif kind=='main' and link in source_links and (vid not in previous or previous[vid][1]<0):name='main_source'
                else:unknown.append([t,vid,'entry',r,previous.get(vid)]);name='unknown_entry'
                counts[name]+=1;moments[name]+=(end-t+1)/3600;bytime[t][name]+=1
                origins.setdefault(vid,'entered_'+name)
            for vid,r in prior.items():
                if vid in inside:continue
                link,pos,speed,loc,kind=r;now=current.get(vid)
                if kind=='off' and now and (now[0]==ports[link]['to_link'] or skipped_off_exit(r,now,exit_routes)):
                    name='off_departure_'+str(link)
                elif kind=='main' and link==terminal_link and now is None and pos+speed/3.6+3>=terminal['length_m']:
                    name='main_terminal_inferred'
                else:unknown.append([t,vid,'exit',r,now]);name='unknown_exit'
                counts[name]+=1;moments[name]-=(end-t+1)/3600;bytime[t][name]-=1
            assert len(inside)-len(prior)==sum(bytime[t].values())
            for vid in inside:cohort_residence[origins[vid]]+=1/3600
            if t%30==0:
                trace.append({'time_s':t,'cumulative_ttt_veh_h':ttt,
                    'signed_interface_moments':dict(moments),'cohort_residence_veh_h':dict(cohort_residence)})
        previous=current
    for p in records(path):
        t=int(float(p[0]))
        if t<start:continue
        if t>end:break
        if last is not None and last!=t:
            assert t==last+1;process(last,frame);frame={}
        last=t;link=int(p[2]);pos=float(p[4]);speed=float(p[6]);loc=observer.locate((link,int(p[3]),pos,speed))
        kind=('main' if loc and loc[0]=='FW_E' else
              ('on' if ports[link]['kind']=='ramp' else 'off') if link in ports else None)
        frame[int(p[1])]=(link,pos,speed,loc,kind)
    assert last==end;process(last,frame)
    residual=ttt-initial*(end-start)/3600-sum(moments.values())
    assert abs(residual)<1e-8
    return {'ttt_veh_h':ttt,'initial_veh':initial,'end_veh':sum(r[4] is not None for r in frame.values()),
            'counts':dict(counts),'signed_time_moments_veh_h':dict(moments),'residence_identity_residual':residual,
            'unexplained_events':unknown,'cohort_residence_veh_h':dict(cohort_residence),
            'initial_vehicle_ids':sorted(initial_ids),'cumulative_30s_trace':trace}


def balance_experiment(out,cases):
    results={};summary={}
    for seed,arms in cases.items():
        observation_folder=(HERE/'fresh_s43_v1/observations/none' if seed==43 else next(r[1] for r in CASES if r[0]==seed))
        geometry=e.ObservationData(observation_folder).geometry
        results[seed]={}
        for arm,run in arms.items():
            result=component_balance(run/'vissim_eval/baseline_001.fzp',geometry)
            e.save(out/f's{seed}_{arm}.json',result);results[seed][arm]=result
            print('BALANCE',seed,arm,result['ttt_veh_h'],'unknown',len(result['unexplained_events']),flush=True)
        nc=results[seed]['none'];summary[seed]={}
        for arm,r in results[seed].items():
            if arm=='none':continue
            assert r['initial_veh']==nc['initial_veh']
            assert r['initial_vehicle_ids']==nc['initial_vehicle_ids']
            keys=r['signed_time_moments_veh_h'].keys()|nc['signed_time_moments_veh_h'].keys()
            delta={k:r['signed_time_moments_veh_h'].get(k,0)-nc['signed_time_moments_veh_h'].get(k,0) for k in keys}
            actual=r['ttt_veh_h']-nc['ttt_veh_h'];assert abs(actual-sum(delta.values()))<1e-8
            summary[seed][arm]={'delta_ttt':actual,'signed_interface_delta':delta,
                'unexplained_events':len(r['unexplained_events'])+len(nc['unexplained_events']),
                'cohort_residence_delta':{k:r['cohort_residence_veh_h'].get(k,0)-nc['cohort_residence_veh_h'].get(k,0)
                    for k in r['cohort_residence_veh_h'].keys()|nc['cohort_residence_veh_h'].keys()}}
    e.save(out/'summary.json',summary)


def extract(path,geometry,start=2400,end=2850,include_moments=False):
    observer=Observer(geometry);cells={c['cell']:c for c in geometry['cells'] if c['road']=='FW_E'}
    off={b['connector'] for b in geometry['boundaries'] if b['road']=='FW_E' and b['kind']=='offramp'}
    previous={};frame={};last=None;measured=Counter();integral=Counter();tail=Counter();snapshots={};unknown=Counter()
    main_out=Counter();off_out=Counter();linear_n=Counter();linear_v=Counter();linear_snapshots={}
    half=Counter();velocity_snapshots={};half_snapshots={}
    def process(t,current):
        nonlocal previous
        k=10*((t-1)//10);moments=Counter();spatial=defaultdict(lambda:[0.,0.,0.,0.]);half_frame=defaultdict(lambda:[0.,0.])
        for vid,(link,loc,g,v) in current.items():
            if loc:
                c=loc[1]
                moments[c,g]+=v
                if include_moments:
                    x=(loc[2]-cells[c]['start_m'])/(1000*cells[c]['length_km'])
                    s=spatial[c,g];s[0]+=1;s[1]+=x;s[2]+=v;s[3]+=v*x
                    if x>=.5:
                        half_frame[c,g][0]+=1;half_frame[c,g][1]+=v
                        if t>start:half[k,c,g]+=v/3600/(cells[c]['length_km']/2)
                if t>start:
                    integral[k,c,g]+=v/3600/cells[c]['length_km']
                    if loc[2]>=cells[c]['end_m']-100.:
                        tail[k,c,g]+=v/3600/min(.1,cells[c]['length_km'])
            if t<=start or vid not in previous:continue
            oldlink,oldloc,oldg,oldv=previous[vid]
            if not oldloc:continue
            c=oldloc[1]
            if loc and loc[1]!=c:
                if loc[1]!=c+1:unknown['nonadjacent_cell_transition']+=1
                else:measured[k,c,oldg]+=1;main_out[k,c,oldg]+=1
            elif not loc and link in off:measured[k,c,oldg]+=1;off_out[k,c,oldg]+=1
        if include_moments:
            for (c,g),(n,nx,vs,vx) in spatial.items():
                # Nonnegative linear reconstruction. No fitted gain factor:
                # rho(x)=N/L*(1+a*(2x/L-1)), a=clip(6*mean(x/L)-3,-1,1).
                factor_n=min(2.,max(0.,6*nx/n-2.))
                factor_v=min(2.,max(0.,6*vx/vs-2.)) if vs else 0.
                q=vs/3600/cells[c]['length_km']
                if t>start:
                    linear_n[k,c,g]+=q*factor_n
                    linear_v[k,c,g]+=q*factor_v
                if t%10==0:
                    linear_snapshots[t,c,g]=min(n,10*q*factor_n)
                    velocity_snapshots[t,c,g]=min(n,10*q*factor_v)
                    half_snapshots[t,c,g]=10*half_frame[c,g][1]/3600/(cells[c]['length_km']/2)
        if t%10==0:snapshots[t]=dict(moments)
        previous=current
    for p in records(path):
        t=int(float(p[0]))
        if t<start:continue
        if t>end:break
        if last is not None and t!=last:
            assert t==last+1
            process(last,frame);frame={}
        last=t;link=int(p[2])
        if link not in observer.addresses and link not in off:continue
        lane=int(p[3]);v=float(p[6]);loc=observer.locate((link,lane,float(p[4]),v))
        if loc and loc[0]!='FW_E':continue
        frame[int(p[1])]=(link,loc,group(loc[1],lane) if loc else None,v)
    assert last==end;process(last,frame)
    keys={(t,c,g) for t,c,g in (set(integral)|set(measured)) if 5<=c<=19}
    rows=[{'time_s':t,'cell':c,'group':g,'observed_out':measured[t,c,g],
        'spatial_flux_integral':integral[t,c,g],
        'tail100m_flux_integral':tail[t,c,g],
        'snapshot_uniform_sending':snapshots[t].get((c,g),0)*10/3600/cells[c]['length_km'],
        **({'observed_mainline_out':main_out[t,c,g],'observed_off_out':off_out[t,c,g],
            'position_linear_flux_integral':linear_n[t,c,g],'velocity_position_linear_flux_integral':linear_v[t,c,g],
            'snapshot_position_linear_sending':linear_snapshots.get((t,c,g),0.),
            'halfcell_flux_integral':half[t,c,g],
            'snapshot_velocity_position_sending':velocity_snapshots.get((t,c,g),0.),
            'snapshot_halfcell_flux':half_snapshots.get((t,c,g),0.)} if include_moments else {})}
        for t,c,g in sorted(keys)]
    return rows,dict(unknown)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='flux_closure_v2')
    parser.add_argument('--moments',action='store_true')
    parser.add_argument('--transport-resolution',action='store_true')
    parser.add_argument('--component-balance',action='store_true')
    parser.add_argument('--rm-balance',action='store_true')
    args=parser.parse_args()
    out=HERE/args.output;out.mkdir(exist_ok=False);allrows={};sources={};begun=time.perf_counter()
    state=H/'state_exchange_20260920'
    cases={23:{'none':HERE/'native_v1/none_s23/run','vsl':H/'dsd_response_20260920/native_v2/run_retry1'},
           33:{'none':HERE/'native_v1/none_s33/run','spread_only':state/'dispersion_seed33_v1/spread_only/run'}}
    if args.transport_resolution:
        resolution_experiment(out,cases);return
    if args.rm_balance:
        cases={23:{'none':HERE/'native_v1/none_s23/run','rm_ramp':H/'response_late_s23_v1/run_rm_ramp'},
               33:{'none':HERE/'native_v1/none_s33/run','rm_ramp':H/'state_response_20260919/native_s33_v1/run_rm_ramp'},
               43:{a:HERE/'fresh_s43_v1'/a/'run' for a in ['none','rm_ramp']}}
    if args.component_balance or args.rm_balance:
        balance_experiment(out,cases);return
    for seed,arms in cases.items():
        geometry=e.ObservationData(next(r[1] for r in CASES if r[0]==seed)).geometry
        allrows[seed]={}
        for arm,run in arms.items():
            rows,unknown=extract(run/'vissim_eval/baseline_001.fzp',geometry,include_moments=args.moments)
            with (out/f's{seed}_{arm}.csv').open('x',encoding='utf-8',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
            allrows[seed][arm]=rows;sources[f'{seed}_{arm}']={'source':str(run.relative_to(e.ROOT)),'unknown':unknown}
            print('EXTRACTED',seed,arm,len(rows),round(time.perf_counter()-begun,1),flush=True)
    summary={}
    for seed,arms in allrows.items():
        summary[seed]={}
        for arm,rows in arms.items():
            totals=defaultdict(Counter)
            for r in rows:
                for k in r.keys()-{'time_s','cell','group'}:
                    totals[r['cell']][k]+=r[k]
            summary[seed][arm]=dict(totals)
    e.save(out/'summary.json',summary);e.save(out/'sources.json',sources)


if __name__=='__main__':main()
