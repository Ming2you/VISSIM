"""Evidence for the spatial exchange trial; no calibration or native execution."""
from pathlib import Path
import copy,hashlib,json,math,statistics,sys
HERE=Path(__file__).resolve().parent.parent
ROOT=HERE.parents[3]
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,value):
    with p.open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False)
archives={}
for value in load(HERE/'partition_exchange_work_v1/source_before.json').values():
    path=ROOT/value['archive'];assert sha(path)==value['sha256'];archives[value['sha256']]=path
path=HERE/'partition_exchange_work_v1/runner_on_v1.py.txt';archives[sha(path)]=path
names=['partition_exchange_v1','partition_exchange_off_partition_on_v1','partition_exchange_off_partition_off_v1']
pins=[];exact=0;urban=0;interfaces=0;residual=0.;results={}
for name in names:
    folder=HERE/name;protocol=load(folder/'protocol.json');result=load(folder/'result.json')
    assert result['source_pins_verified'] and not result['future_traffic_inputs']
    for relative,digest in protocol['source_pins'].items():
        original=ROOT/relative
        resolved=original if sha(original)==digest else archives[digest]
        assert sha(resolved)==digest
        pins.append(dict(run=name,path=relative,sha256=digest,resolved=str(resolved.relative_to(ROOT))))
    for arm,summary in result['summaries'].items():
        pred=load(folder/f'prediction_{arm}.json')
        if name!='partition_exchange_v1':
            mode='on' if '_on_' in name else 'off'
            old=HERE/f'urban_route_transport_space_v1_network_intent_current_limits_partition_{mode}_v4'/f'prediction_{arm}.json'
            assert pred==load(old);exact+=1
        road=next(r for r in pred['diagnostics']['roads'] if r['road']=='FW_E')
        residual=max(residual,road.get('branch_partition_continuity_residual_max_veh',0.))
        urban+=summary['urban_checks'];interfaces+=summary['checks']['lane_interface_checks']
    results[name]=dict(deltas=result['deltas'],nc_score=result['summaries']['none']['score']['objective'])

comparison={}
for arm in ('none','vsl'):
    native=load(HERE/f'branch_flux_audit_v1/native_{arm}.json')['rows']
    initial=next(r['counts'] for r in native if r['time_s']==2400)
    pred=load(HERE/f'partition_exchange_v1/prediction_{arm}.json')
    road=next(r for r in pred['diagnostics']['roads'] if r['road']=='FW_E')
    trace={(r['time_s'],r['group']):r for r in road['branch_partition_trace']}
    group={(r['time_s'],r['group']):r for r in pred['lane_groups']['FW_E'] if r['cell']==8}
    prior=copy.deepcopy(initial);rows=[]
    for t in range(2410,2851,10):
        terms={s:[] for s in ('pre','post')}
        for g in range(3):
            r=trace[t,g];q=group[t,g];cross=r['internal_cross_veh'];off=r['off_out_veh'];leave=r['mainline_out_veh']
            enter=q['longitudinal_in_veh'];merge=q['merge_in_veh']
            terms['pre'].append(dict(inflow=enter,cross=cross,off=off,lateral=r['pre_n']-prior['pre'][g]-enter+cross+off))
            terms['post'].append(dict(merge=merge,cross=cross,out=leave,lateral=r['post_n']-prior['post'][g]-merge-cross+leave))
            prior['pre'][g]=r['pre_n'];prior['post'][g]=r['post_n']
        for s in ('pre','post'):assert abs(sum(x['lateral'] for x in terms[s]))<1e-7
        rows.append(dict(time_s=t,counts=copy.deepcopy(prior),terms=terms))
    comparison[arm]={}
    for side in ('pre','post'):
        signs={'inflow':1,'cross':-1,'off':-1,'lateral':1} if side=='pre' else {'merge':1,'cross':1,'out':-1,'lateral':1}
        for g in range(3):
            flows={};weighted={};means={}
            for label,chosen in [('native',[r for r in native if r['time_s']>2400]),('model',rows)]:
                flows[label]={ch:sum(r['terms'][side][g].get('in' if ch=='inflow' and label=='native' else ch,0.) for r in chosen) for ch in signs}
                weighted[label]={ch:sum((46-math.ceil((r['time_s']-2400)/10))/45*sign*r['terms'][side][g].get('in' if ch=='inflow' and label=='native' else ch,0.) for r in chosen) for ch,sign in signs.items()}
                means[label]=statistics.mean(r['counts'][side][g] for r in chosen if r['time_s']%10==0)
                assert abs(initial[side][g]+sum(weighted[label].values())-means[label])<1e-7
            values=[trace[t,g] for t in range(2410,2851,10)]
            comparison[arm][f'{side}:{g}']=dict(flows=flows,weighted=weighted,mean_n=means,
                model_weighted_speed=sum(r[side+'_n']*r[side+'_v'] for r in values)/sum(r[side+'_n'] for r in values))
    save(HERE/f'partition_exchange_work_v1/model_flux_{arm}.json',rows)
evidence=dict(status='SPATIAL_EXCHANGE_TESTED_NOT_GAIN_QUALIFIED',valid_450s_forecasts=12,
    disabled_full_json_exact=exact,urban_conservation_checks=urban,lane_interface_checks=interfaces,
    partition_residual_max=residual,source_pin_checks=len(pins),source_resolutions=pins,
    cases=results,flux_comparison=comparison,future_inputs=False,new_native_runs=0,production_adopted=False,qualified=False)
save(HERE/'partition_exchange_work_v1/verification.json',evidence)
print(json.dumps(dict(cases=results,flux=comparison['none']['pre:2'],checks=dict(exact=exact,pins=len(pins),urban=urban,interfaces=interfaces)),indent=2))
