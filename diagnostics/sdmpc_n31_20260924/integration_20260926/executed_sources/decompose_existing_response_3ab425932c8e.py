"""Reconcile saved common-state control-cost differences with conserved fluxes."""
import argparse
import csv
import gzip
import json
import hashlib
from pathlib import Path
from collections import defaultdict

HERE=Path(__file__).resolve().parent
H=HERE.parents[1]/'heldout53_response_v2'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--case',choices=('seed53','seed47'),default='seed53')
parser.add_argument('--prediction-set',choices=('baseline','tau4'),default='tau4')
opts=parser.parse_args()
arms=('hold','release','hold_vsl90','release_vsl90')
records={}
if opts.case=='seed47':
    capture=json.loads((HERE.parents[1]/'decision_response/capture.json').read_text(encoding='utf-8'))
    records={x['arm']:x for x in capture['records'] if x['case']=='s47_late'}
    arms=('hold','release_10484')
START=2670.1;END=3120.1
def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def window(xs):return [x for x in xs if START+1e-5<float(x['window_end_s'])<=END+1e-5 and x['road']=='FW_E']
def integral(seq):
    vs=sorted(seq)
    assert len(vs)==16
    return sum((n+m)*(b-a)/7200 for (a,n),(b,m) in zip(vs,vs[1:]))
out={};spatial=[];pins={};initial_states={};initial_port_states={};closure=[]
for arm in arms:
    pred_path=H/f'candidate/{arm}_prediction.json.gz'
    truth=H/f'observations/{arm}'
    if records:
        pred_path=HERE.parent/f'recovery_response/{opts.prediction_set}/s47_late_{arm}.json.gz'
        truth=Path(records[arm]['truth'])
    manifest=json.loads((truth/'manifest.json').read_text(encoding='utf-8'))
    for name in ('flows_30s.csv','ports_30s.csv','cells_30s.csv','geometry.json'):
        digest=hashlib.sha256((truth/name).read_bytes()).hexdigest()
        assert digest==manifest['files'][name],(arm,name)
        pins[str(truth/name)]=digest
    pins[str(pred_path)]=hashlib.sha256(pred_path.read_bytes()).hexdigest()
    with gzip.open(pred_path,'rt',encoding='utf-8') as f:pred=json.load(f)
    native=window(rows(truth/'flows_30s.csv'))
    ports=window(rows(truth/'ports_30s.csv'))
    cells=rows(truth/'cells_30s.csv')
    geometry=json.loads((truth/'geometry.json').read_text(encoding='utf-8'))
    lengths={int(x['cell']):float(x['length_km']) for x in geometry['cells'] if x['road']=='FW_E'}
    initial_port_states[arm]={x['connector']:float(x['start_n_veh']) for x in ports if abs(float(x['window_start_s'])-START)<1e-5}
    initial_states[arm]={str(x['cell']):(float(x['n_veh']),float(x['v_kmh']) if x['v_kmh'] else None)
        for x in cells if x['road']=='FW_E' and abs(float(x['time_s'])-START)<1e-5}
    assert len(native)==465 and len(ports)==120
    assert all(abs(float(x['conservation_residual_veh']))<1e-7 and float(x['unresolved_absences_veh'])==0 for x in ports)
    assert all(abs(float(x['conservation_residual_veh']))<1e-7 for x in native)
    port_cost={};off_flows={};port_boundary={}
    for no in sorted({x['connector'] for x in ports}):
        ps=sorted([x for x in ports if x['connector']==no],key=lambda x:float(x['window_end_s']))
        assert len(ps)==15
        series=[(START,float(ps[0]['start_n_veh']))]+[(float(x['window_end_s']),float(x['end_n_veh'])) for x in ps]
        is_ramp=ps[0]['kind']=='ramp'
        series_p=[(START,float(ps[0]['start_n_veh']))]
        cumulative_pred=[(START,0.,0.)]
        for t,_ in series[1:]:
            vals=[x['end']['connector_veh'] for x in pred['ramps'] if x['ramp']=='RM_C'+no and abs(x['end_sec']-t)<1e-5] if is_ramp else [x['n_veh'] for x in pred['ports'] if x['connector']==no and abs(x['time_s']-t)<1e-5]
            assert len(vals)==1,(arm,no,t)
            series_p.append((t,vals[0]))
            if is_ramp:
                receipt=next(x for x in pred['ramps'] if x['ramp']=='RM_C'+no and abs(x['end_sec']-t)<1e-5)
                cumulative_pred.append((t,receipt['end']['cumulative_admitted_veh'],receipt['end']['cumulative_merge_veh']))
            else:
                receipt=next(x for x in pred['ports'] if x['connector']==no and abs(x['time_s']-t)<1e-5)
                cumulative_pred.append((t,receipt['admitted_veh'],receipt['departed_veh']))
        boundary={}
        for key,idx in [('arrivals',1),('departures',2)]:
            boundary[key]={'native':sum(float(x[key+'_veh'])*(END-(float(x['window_start_s'])+float(x['window_end_s']))/2)/3600 for x in ps),
                'predicted':sum((b[idx]-a[idx])*(END-(a[0]+b[0])/2)/3600 for a,b in zip(cumulative_pred,cumulative_pred[1:]))}
        port_boundary[no]=dict(kind=ps[0]['kind'],**boundary)
        port_cost[no]=dict(kind=ps[0]['kind'],native=integral(series),predicted=integral(series_p),
            native_arrivals=sum(float(x['arrivals_veh']) for x in ps),native_departures=sum(float(x['departures_veh']) for x in ps))
        if not is_ramp:
            p=next(x for x in pred['ports'] if x['connector']==no and abs(x['time_s']-END)<1e-5)
            port_cost[no].update(predicted_arrivals=p['admitted_veh'],predicted_departures=p['departed_veh'])
    weighted={};totals={}
    mapping={'source_admissions':('source_admissions',1),'ramp_merges':('ramp_merges',1),
        'off_departures':('off_departures',-1),'terminal_exits':('terminal_exits_inferred',-1)}
    for key,(native_key,sign) in mapping.items():
        weighted[key]={};totals[key]={}
        for kind,data,k in [('predicted',pred['flows'],key),('native',native,native_key)]:
            weighted[key][kind]=sum(sign*float(x[k])*(END-(float(x['window_start_s'])+float(x['window_end_s']))/2)/3600 for x in data)
            totals[key][kind]=sum(float(x[k]) for x in data)
    # observed_births is already included in source_admissions, not extra mass.
    extra={k:sum(float(x[k]) for x in native) for k in ('unexplained_entries','unexplained_losses','native_removals')}
    assert not any(extra.values()),(arm,extra)
    main_native=integral([(t,sum(float(x['n_veh']) for x in cells if x['road']=='FW_E' and abs(float(x['time_s'])-t)<1e-5)) for t in [round(START+j*30,6) for j in range(16)]])
    initial=sum(float(x['n_veh']) for x in cells if x['road']=='FW_E' and abs(float(x['time_s'])-START)<1e-5)
    main_pred=integral([(START,initial)]+[(t,sum(x['n_veh'] for x in pred['cells'] if abs(x['time_s']-t)<1e-5)) for t in [round(START+j*30,6) for j in range(1,16)]])
    for kind,value in [('native',main_native),('predicted',main_pred)]:
        assert abs(value-initial*(END-START)/3600-sum(v[kind] for v in weighted.values()))<1e-7,(arm,kind)
    component_boundary={}
    for kind in ('native','predicted'):
        component_boundary[kind]=dict(source=weighted['source_admissions'][kind],
            ramp_approach=sum(x['arrivals'][kind] for x in port_boundary.values() if x['kind']=='ramp'),
            off_drain=-sum(x['departures'][kind] for x in port_boundary.values() if x['kind']!='ramp'),
            terminal=weighted['terminal_exits'][kind])
        expected=initial*(END-START)/3600+sum(component_boundary[kind].values())
        initial_ports=sum(float(x['start_n_veh']) for x in ports if abs(float(x['window_start_s'])-START)<1e-5)
        observed=(main_native if kind=='native' else main_pred)+sum(x[kind] for x in port_cost.values())
        assert abs(expected+initial_ports*(END-START)/3600-observed)<1e-7,(arm,kind,observed,expected)
    out[arm]=dict(port_cost=port_cost,weighted_main_flux=weighted,main_flow_counts=totals,component_boundary=component_boundary,
        main_ttt={'native':main_native,'predicted':main_pred},main_conservation_reconciled=True,native_unexplained_or_removal_counts=extra)
    for kind,fs,cs in [('native',native,cells),('predicted',pred['flows'],pred['cells'])]:
        for cell in range(31):
            state_seq=[x for x in cs if x['road']=='FW_E' and int(x['cell'])==cell and START-1e-5<=float(x['time_s'])<=END+1e-5]
            if kind=='predicted':
                initial_row=next(x for x in cells if x['road']=='FW_E' and int(x['cell'])==cell and abs(float(x['time_s'])-START)<1e-5)
                state_seq=[initial_row]+state_seq
            state_seq=sorted(state_seq,key=lambda x:float(x['time_s']))
            assert len(state_seq)==16
            nq=[(float(x['time_s']),float(x['n_veh'])*float(x['v_kmh'])/lengths[cell]) for x in state_seq]
            reconstructed=sum((a[1]+b[1])*(b[0]-a[0])/7200 for a,b in zip(nq,nq[1:]))
            actual_exit=sum(float(x['downstream_crossings'])+float(x['off_departures'])+float(x.get('terminal_exits_inferred',x.get('terminal_exits',0))) for x in fs if int(x['cell'])==cell)
            closure.append(dict(arm=arm,kind=kind,cell=cell,length_km=lengths[cell],
                snapshot_nv_exit_veh=reconstructed,recorded_exit_veh=actual_exit,
                note='30s trapezoid of snapshot N*v/L, diagnostic approximation only; not a true boundary measurement'))
            for j in range(3):
                a=START+j*150;b=a+150
                selected=[x for x in fs if int(x['cell'])==cell and a+1e-5<float(x['window_end_s'])<=b+1e-5]
                states=[x for x in cs if x['road']=='FW_E' and int(x['cell'])==cell and a+1e-5<float(x['time_s'])<=b+1e-5]
                assert len(selected)==len(states)==5
                total_n=sum(float(x['n_veh']) for x in states)
                spatial.append(dict(arm=arm,kind=kind,cell=cell,start_sec=a,end_sec=b,
                    downstream_veh=sum(float(x['downstream_crossings']) for x in selected),
                    ramp_merge_veh=sum(float(x['ramp_merges']) for x in selected),
                    off_departure_veh=sum(float(x['off_departures']) for x in selected),
                    mean_n_veh=total_n/5,
                    vehicle_weighted_speed_kmh=sum(float(x['n_veh'])*float(x['v_kmh']) for x in states if x['v_kmh']!='')/total_n if total_n else None,
                    mean_density=sum(float(x['rho_veh_per_km_lane']) for x in states)/5))
base=out['hold']
assert all(v==initial_states['hold'] for v in initial_states.values())
assert all(v==initial_port_states['hold'] for v in initial_port_states.values())
for arm,d in out.items():
    d['delta_port_cost']={no:{kind:z[kind]-base['port_cost'][no][kind] for kind in ('native','predicted')} for no,z in d['port_cost'].items()}
    d['delta_weighted_main_flux']={key:{kind:z[kind]-base['weighted_main_flux'][key][kind] for kind in ('native','predicted')} for key,z in d['weighted_main_flux'].items()}
    d['delta_main_flow_counts']={key:{kind:z[kind]-base['main_flow_counts'][key][kind] for kind in ('native','predicted')} for key,z in d['main_flow_counts'].items()}
    d['delta_component_boundary']={kind:{k:v-base['component_boundary'][kind][k] for k,v in parts.items()} for kind,parts in d['component_boundary'].items()}
    d['delta_component_ttt']={kind:sum(d['delta_component_boundary'][kind].values()) for kind in ('native','predicted')}
lookup={(x['kind'],x['cell'],x['start_sec']):x for x in spatial if x['arm']=='hold'}
for x in spatial:
    ref=lookup[x['kind'],x['cell'],x['start_sec']]
    for key in ('downstream_veh','ramp_merge_veh','off_departure_veh','mean_n_veh','vehicle_weighted_speed_kmh','mean_density'):
        x['delta_'+key]=x[key]-ref[key] if x[key] is not None and ref[key] is not None else None
closure_lookup={(x['kind'],x['cell']):x for x in closure if x['arm']=='hold'}
for x in closure:
    ref=closure_lookup[x['kind'],x['cell']]
    for key in ('snapshot_nv_exit_veh','recorded_exit_veh'):
        x['delta_'+key]=x[key]-ref[key]
target=HERE/'existing_response_decomposition_v2.json'
if records:
    target=HERE.parent/f'recovery_response/seed47_audit/{opts.prediction_set}_decomposition_v2.json'
assert not target.exists(),target
target.parent.mkdir(parents=True,exist_ok=True)
target.write_text(json.dumps(dict(results=out,spatial=spatial,flow_closure=closure,pins=pins,common_initial_mainline_state_exact=True,common_initial_port_stock_exact=True,
    scope='East31+8ports,450s; exact30s stock/flux accounting. No new fit/native. This is not whole Omega.',
    case=opts.case,prediction_set=opts.prediction_set if records else 'delta4_E2',new_rollouts=0),indent=2),encoding='utf-8')
with target.with_suffix('.csv').open('w',encoding='utf-8',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(spatial[0]));writer.writeheader();writer.writerows(spatial)
for arm in arms[1:]:
    print(arm,json.dumps({k:v for k,v in out[arm].items() if k.startswith('delta')}))
