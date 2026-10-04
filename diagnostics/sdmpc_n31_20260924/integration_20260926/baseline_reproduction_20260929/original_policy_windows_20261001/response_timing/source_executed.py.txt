"""Original policy response timing, cached observations only; no model fitting."""
import csv
import hashlib
import json
from pathlib import Path
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData

HERE=Path(__file__).resolve().parent
OUT=HERE/'response_timing'
OUT.mkdir(exist_ok=False)
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read_csv(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
capture=load(HERE/'capture.json');pins={}
arms=['none','bottleneck90','rm','both'];data={};cmd={};areas={}
original=Path(next(z['truth'] for z in capture['records'] if z['arm']=='rm')).parent
for arm in arms:
    folder=Path(next(z['truth'] for z in capture['records'] if z['arm']==arm))
    data[arm]=ObservationData(folder)
    for name in ['cells_30s.csv','flows_30s.csv','ports_30s.csv','boundaries_30s.csv']:
        p=folder/name;pins[str(p)]=sha(p)
    p=HERE/(arm+'_commands.json');pins[str(p)]=sha(p)
    cmd[arm]={float(k):v for k,v in load(p).items()}
    p=original/arm/'area_timeseries.csv';pins[str(p)]=sha(p)
    areas[arm]={float(z['sim_sec']):z for z in read_csv(p)}
performance=load(original/'summary.json')['performance']
for arm in arms:
    last=areas[arm][9000.0]
    truth=next(z for z in performance if z['arm']==arm)
    assert abs(float(last['ttt_veh_h_cumulative'])-truth['TTT_veh_h'])<1e-7
def action(arm,t):return cmd[arm][max(x for x in cmd[arm] if x<=t)]
def stocks(d,t,road='FW_E'):
    return [z['n_veh'] for z in sorted((z for z in d.cells[t] if z['road']==road),key=lambda z:z['cell'])]
def port_n(d,t,kind):
    return sum(float(z['end_n_veh']) for (s,c),z in d.ports.items() if s==t and z['road']=='FW_E' and z['kind']==kind)
def state(d,t):
    return dict(mainline=sum(stocks(d,t)),on=port_n(d,t,'ramp'),off=port_n(d,t,'offramp'))
def window(d,start,end):
    times=[round(start+x,6) for x in range(0,round(end-start)+1,30)]
    assert times[-1]==end
    ns={t:state(d,t) for t in times}
    costs={k:sum((ns[a][k]+ns[b][k])*(b-a)/7200 for a,b in zip(times,times[1:])) for k in ns[start]}
    costs['component']=sum(costs.values())
    count=dict(source=0.,merge=0.,off=0.,terminal=0.,unknown_in=0.,unknown_out=0.,removed=0.)
    weighted=dict.fromkeys(count,0.)
    cellthrough=dict.fromkeys([19,22,23,25,30],0.)
    residual=0.
    mapping={'source':'source_admissions','merge':'ramp_merges','off':'off_departures','terminal':'terminal_exits_inferred',
             'unknown_in':'unexplained_entries','unknown_out':'unexplained_losses','removed':'native_removals'}
    for t in times[1:]:
        f=[d.flows[t,'FW_E',i] for i in range(31)]
        weight=(end-t+15)/3600
        for k,key in mapping.items():
            value=sum(float(z[key]) for z in f);count[k]+=value;weighted[k]+=value*weight
        for z in f:
            balance=float(z['start_n_veh'])+float(z['upstream_crossings'])+float(z['source_admissions'])+float(z['ramp_merges'])+float(z['unexplained_entries'])-float(z['off_departures'])-float(z['downstream_crossings'])-float(z['terminal_exits_inferred'])-float(z['native_removals'])-float(z['unexplained_losses'])-float(z['end_n_veh'])
            residual=max(residual,abs(balance))
        for i in cellthrough:cellthrough[i]+=float(f[i]['downstream_crossings'])+float(f[i]['terminal_exits_inferred'])
    closure=ns[start]['mainline']*(end-start)/3600+weighted['source']+weighted['merge']+weighted['unknown_in']-weighted['off']-weighted['terminal']-weighted['unknown_out']-weighted['removed']
    assert residual<1e-7 and abs(closure-costs['mainline'])<1e-7,(residual,closure,costs)
    return dict(costs=costs,flows=count,weighted=weighted,through=cellthrough,initial=ns[start],end=ns[end],mass_residual=residual)
pairs=[]
for ref,arm in [('none','rm'),('bottleneck90','both')]:
    x,y=data[ref],data[arm]
    first=next(t for t in sorted(set(cmd[ref])|set(cmd[arm])) if action(ref,t)!=action(arm,t))
    assert first==1350.
    # At1320.1 all earlier recorded mainline and connector state/flow arrays match.
    start=1320.1
    prefix={}
    for name,key in [('cells','time'),('flows','tuple'),('ports','tuple'),('port_cohorts','string')]:
        left=getattr(x,name);right=getattr(y,name)
        cutoff=lambda k:float(k) if key in ('time','string') else k[0]
        ls={k:v for k,v in left.items() if cutoff(k)<=start}
        rs={k:v for k,v in right.items() if cutoff(k)<=start}
        prefix[name]=ls==rs
    assert all(prefix.values()),prefix
    assert all(action(ref,t)==action(arm,t) for t in sorted(set(cmd[ref])|set(cmd[arm])) if t<first)
    cumulative=[];blocks=[]
    for end in [1770.1,2070.1,2220.1,2670.1,3120.1,3570.1,4470.1,5370.1,6270.1,8970.1]:
        a,b=window(x,start,end),window(y,start,end)
        delta=lambda field:{k:b[field][k]-a[field][k] for k in a[field]}
        cumulative.append(dict(start=start,end=end,cost_delta=delta('costs'),flow_delta=delta('flows'),weighted_flow_delta=delta('weighted'),
            cell_through_delta=delta('through'),omega_delta=float(areas[arm][end]['ttt_veh_h_cumulative'])-float(areas[ref][end]['ttt_veh_h_cumulative']),
            max_mass_residual=max(a['mass_residual'],b['mass_residual'])))
    for startblock in range(1320,8521,450):
        aa,bb=round(startblock+.1,6),round(startblock+450+.1,6)
        a,b=window(x,aa,bb),window(y,aa,bb)
        delta=lambda field:{k:b[field][k]-a[field][k] for k in a[field]}
        blocks.append(dict(start=aa,end=bb,cost_delta=delta('costs'),flow_delta=delta('flows'),cell_through_delta=delta('through'),
            inherited_mainline_stock_delta=b['initial']['mainline']-a['initial']['mainline']))
    pairs.append(dict(reference=ref,arm=arm,first_different_command=first,last_checked_common_initial=start,
        prefix_equal=prefix,cumulative=cumulative,blocks450=blocks))
assert all(sha(Path(p))==h for p,h in pins.items())
result=dict(pairs=pairs,pins=pins,new_forecasts=0,new_native=0,new_fzp_reads=0,calibration=False,
    scope='East31 mainline/on/off connector; Omega from existing5s area ledger. Not19link scope.',
    semantics='Cumulative policy contrasts share verified recorded prefix; late blocks inherit different states. Flow attribution is an accounting identity, not isolated causal mechanism.',
    disappearance='Unknown entries/losses and known deletion retained explicitly; none counted as normal completion.')
(OUT/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'source_executed.py.txt').write_bytes(Path(__file__).read_bytes())
for pair in pairs:
    print(pair['reference'],pair['arm'])
    for z in pair['cumulative']:print(z['end'],z['cost_delta'],z['flow_delta'],'omega',z['omega_delta'])
    print('BLOCKS',[(z['start'],round(z['cost_delta']['mainline'],3),round(z['cost_delta']['component'],3),z['inherited_mainline_stock_delta']) for z in pair['blocks450']])

