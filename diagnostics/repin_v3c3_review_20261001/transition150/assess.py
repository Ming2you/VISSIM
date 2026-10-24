"""Locate148 state divergence and exactly close its executed speed budget."""
import collections
import gzip
import json
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    common.setup()
    from evaluation.controllers.freeway_fd import state_response_coefficients
    assert not (HERE/'assessment.json').exists()
    folder=HERE/'replay';status=h.read(folder/'status.json');assert status['status']=='complete_diagnostic_only' and status['forecasts']==2
    protocol=h.read(folder/'protocol.json');pins={**protocol['protected_sha256'],**protocol['input_sha256']}
    assert all(all(v.values()) for v in h.read(folder/'parity.json').values())
    assert all(h.read(folder/'preservation.json').values())
    def read(p):pins[str(p)]=h.sha(p);return h.read(p)
    mapping=read(h.F/'route_inventory/mapping31.json')['freeway_model_links']['FW_E']['segment_bounds_m']
    midpoint=sum(mapping[19:21])/2
    allterms=[];windows=[];endpoints=[];trace_summary=[];max_error=0.
    for arm in ('release','release_vsl90'):
        speeds=read(folder/f'corrected148_{arm}_speed.json.gz')+read(folder/f'corrected148_{arm}_spatial_speed.json.gz')
        flows=read(folder/f'corrected148_{arm}_trace.json.gz')
        cache=read(h.F/'flow67'/f'{arm}_frames.json.gz');frames={round(float(t),6):d for t,d in cache['frames'].items()}
        groups=collections.defaultdict(list)
        for row in speeds:
            x=row['context'];p=x['p'];assert x['armed']
            v=row['exchange_speed'];rho=row['rho'];down=row['downstream_rho'];target=row['target'];dt=row['dt_h']
            length=p['segment_length_km'];kappa=p['metanet_kappa_veh_km_lane']
            tau,nu=state_response_coefficients(x['state_response'],v,target,rho,down,x['response_rho_crit'],p['metanet_tau_h'],row['selected_nu'])
            terms=dict(lateral=v-row['old_speed'],relaxation=dt/tau*(target-v),convection=dt/length*v*(row['upstream_speed']-v),
                anticipation=-nu*dt/(tau*length)*(down-rho)/(rho+kappa))
            raw=v+terms['relaxation']+terms['convection']+terms['anticipation'];base=max(row['v_min'],raw)
            terms['metanet_floor']=base-raw
            if x['phi']>0 and x['dlam']>0:
                after=max(row['v_min'],base-x['phi']*dt*x['dlam']*max(rho,0)*v*v/(length*max(x['lanes'],1e-9)*p['rho_crit']))
            else:after=base
            terms['lane_drop']=after-base
            error=abs(after-row['pre_merge']);max_error=max(max_error,error);assert error<1e-8
            terms['merge']=row['post_merge']-row['pre_merge'];terms['exit_cap']=row['post_exit_raw']-row['post_merge'];terms['final_floor']=row['final_speed']-row['post_exit_raw']
            error=abs(sum(terms.values())-(row['final_speed']-row['old_speed']));max_error=max(max_error,error);assert error<1e-8
            item=dict(arm=arm,time_s=row['time_s'],cell=row['cell'],part=row.get('part'),lane=row['lane'],n0=row['n_veh'],old_speed=row['old_speed'],final_speed=row['final_speed'],
                rho=rho,downstream_rho=down,target=target,tau_h=tau,nu=nu,**terms)
            allterms.append(item);groups[row['cell'],row.get('part'),row['lane']].append(item)
        for key,seq in groups.items():
            seq.sort(key=lambda x:x['time_s']);assert len(seq)==450
            for a,b in zip(seq,seq[1:]):assert abs(a['final_speed']-b['old_speed'])<1e-8
            cell,part,lane=key
            for lo,hi in ((2670.1,2675.1),(2670.1,2700.1),(2670.1,2820.1),(2820.1,2970.1),(2970.1,3120.1)):
                zz=[z for z in seq if lo+1e-6<z['time_s']<=hi+1e-6];assert len(zz)==round(hi-lo)
                total={k:sum(z[k] for z in zz) for k in terms};assert abs(sum(total.values())-(zz[-1]['final_speed']-zz[0]['old_speed']))<1e-7
                windows.append(dict(arm=arm,cell=cell,part=part,lane=lane,lo=lo,hi=hi,old_speed=zz[0]['old_speed'],final_speed=zz[-1]['final_speed'],
                    target_mean=sum(z['target'] for z in zz)/len(zz),floor_seconds=sum(z['final_speed']<=5.+1e-9 for z in zz),exit_cap_seconds=sum(z['exit_cap']<-1e-9 for z in zz),terms=total))
            for time in (2670.1,2675.1,2700.1,2820.1,2970.1,3120.1):
                z=[v for v in frames[time].values() if v[0]==cell and v[3]==lane and (part is None or int(v[2]>=midpoint)==part)]
                model=seq[0] if time==2670.1 else next(r for r in seq if abs(r['time_s']-time)<1e-6)
                if time==2670.1:
                    assert model['n0']==len(z)
                    if z:assert abs(model['old_speed']-sum(v[1] for v in z)/len(z))<1e-8
                endpoints.append(dict(arm=arm,cell=cell,part=part,lane=lane,time_s=time,actual_n=len(z),actual_v=sum(v[1] for v in z)/len(z) if z else None,
                    model_v=model['old_speed'] if time==2670.1 else model['final_speed']))
        for lo,hi in ((2670.1,2675.1),(2670.1,2700.1),(2670.1,2820.1),(2820.1,2970.1),(2970.1,3120.1)):
            zz=[z for z in flows if lo+1e-6<z['time_s']<=hi+1e-6];assert len(zz)==round(hi-lo)
            trace_summary.append(dict(arm=arm,lo=lo,hi=hi,
                sums={k:sum(z[k] for z in zz) for k in ('off_request','accepted_off','storage_reduction','reciprocal_reduction','through_request','through_room','accepted_through','accepted_merge','incoming20','through21','through22')},
                means={k:sum(z[k] for z in zz)/len(zz) for k in ('lane_n','off_n','other_lane_off_n','old_speed','downstream_lane_n','downstream_speed','n22_before','v22_before')},
                first=zz[0],last=zz[-1]))
    for path,digest in pins.items():assert h.sha(path)==digest,path
    assert h.sha(protocol['STOP']['path'])==protocol['STOP']['sha256']
    assert h.sha(h.__file__)==protocol['helper_sha256']
    result=dict(status='complete_exact_replay_diagnostic',forecasts=2,max_speed_budget_error=max_error,
        initial_n_v_exact=True,windows=windows,endpoints=endpoints,trace_summary=trace_summary,
        pins_verified=len(pins),new_fits=0,new_native=0,new_FZP=0,new_9000_analysis=0,push=0,model_adopted=False,goal_complete=False)
    with gzip.open(HERE/'terms.json.gz','wt',encoding='utf-8') as f:json.dump(allterms,f,allow_nan=False)
    h.save(HERE/'assessment.json',result);h.save(HERE/'pins.json',pins)
    print('PASS initialN/v exact, speed budget',max_error,'samples',len(allterms),'pins',len(pins))
    for row in windows:
        if row['arm']=='release' and row['lane']==1 and row['cell'] in (19,20,21,22) and row['hi'] in (2675.1,2700.1):print(row)
    for row in endpoints:
        if row['arm']=='release' and row['lane']==1 and row['cell'] in (19,20,21,22) and row['time_s'] in (2670.1,2675.1,2700.1):print(row)


def lane_balance():
    """Use first30s endpoint lanes to separate hidden aggregate cancellations."""
    import csv
    assert not (HERE/'lane_balance.json').exists()
    pins=h.read(HERE/'pins.json')
    frames=h.read(h.F/'flow67/release_frames.json.gz')['frames'];frames={round(float(t),6):z for t,z in frames.items()}
    mapping=h.read(h.F/'route_inventory/mapping31.json')['freeway_model_links']['FW_E']['segment_bounds_m']
    midpoint=sum(mapping[19:21])/2;length=(mapping[20]-mapping[19])/2
    counter=collections.Counter();steps=[];rates=[]
    times=[round(2670.1+5*k,6) for k in range(7)]
    for time in times:
        z=[v for v in frames[time].values() if v[0]==19 and v[3]==1 and v[2]>=midpoint]
        rates.append(dict(time_s=time,n=len(z),v=sum(v[1] for v in z)/len(z) if z else None,request_veh_s=sum(v[1] for v in z)/(3.6*length)))
    for lo,hi in zip(times,times[1:]):
        a,b=frames[lo],frames[hi];before={k for k,v in a.items() if v[0]==20 and v[3]==1};after={k for k,v in b.items() if v[0]==20 and v[3]==1};c=collections.Counter()
        for label,ids,other in [('in',after-before,a),('out',before-after,b)]:
            for vid in ids:
                kind='unseen' if vid not in other else 'lateral' if other[vid][0]==20 else 'longitudinal'
                c[label+'_'+kind]+=1
                if vid in other and other[vid][0]!=20 and other[vid][3]!=1:c[label+'_cross_and_lanechange']+=1
        assert len(after)-len(before)==sum(c[k] for k in ('in_unseen','in_lateral','in_longitudinal'))-sum(c[k] for k in ('out_unseen','out_lateral','out_longitudinal'))
        counter.update(c);steps.append(dict(lo=lo,hi=hi,n0=len(before),n1=len(after),counts=dict(c)))
    assert counter['in_cross_and_lanechange']==counter['out_cross_and_lanechange']==counter['in_unseen']==0
    truth=h.I/'heldout67_freeway_20260930/observations/release/flows_30s.csv';pins[str(truth)]=h.sha(truth)
    with truth.open(encoding='utf-8-sig',newline='') as f:
        native=next(z for z in csv.DictReader(f) if z['road']=='FW_E' and int(z['cell'])==20 and abs(float(z['window_start_s'])-2670.1)<1e-6 and abs(float(z['window_end_s'])-2700.1)<1e-6)
    assert all(float(native[k])==0 for k in ('unexplained_entries','unexplained_losses','native_removals'))
    assert int(native['off_departures'])==counter['out_unseen']==11
    trace=h.read(HERE/'replay/corrected148_release_trace.json.gz');z=[x for x in trace if 2670.1+1e-6<x['time_s']<=2700.1+1e-6]
    model=dict(n0=z[0]['lane_n'],n1=z[-1]['next20_n'],inflow=sum(x['incoming20'] for x in z),through=sum(x['accepted_through'] for x in z),off=sum(x['accepted_off'] for x in z))
    model['net_lateral']=model['n1']-model['n0']-model['inflow']+model['through']+model['off']
    terms=dict(extra_inflow=model['inflow']-counter['in_longitudinal'],through_shortfall=counter['out_longitudinal']-model['through'],
        off_shortfall=counter['out_unseen']-model['off'],net_lateral_difference=model['net_lateral']-(counter['in_lateral']-counter['out_lateral']))
    assert abs(sum(terms.values())-(model['n1']-steps[-1]['n1']))<1e-8
    for path,digest in pins.items():assert h.sha(path)==digest,path
    result=dict(window=[2670.1,2700.1],cell20_lane1_native=dict(n0=steps[0]['n0'],n1=steps[-1]['n1'],counts=dict(counter)),
        model=model,stock_error_terms=terms,initial_source_request_exact=abs(rates[0]['request_veh_s']-z[0]['incoming20'])<1e-10,
        native_state_split19_back_request_left=sum(x['request_veh_s'] for x in rates[:-1])*5,
        native_state_split19_back_request_trapezoid=sum((a['request_veh_s']+b['request_veh_s'])*2.5 for a,b in zip(rates,rates[1:])),
        native_rates=rates,steps=steps,native30csv=native,
        limits='Endpoint transitions over5s,not full lane-change paths. No simultaneous cross/end-lane changes in this selected window.11 departures leave freeway observations and match independent cell20 off-count/no unexplained loss; no claim of subsecond individual connector timing. Native-state requests reset from observed5s states and are conditional diagnostics only,not autonomous predictions.',
        new_forecasts=0,fit=0,new_native=0,new_FZP=0)
    assert result['initial_source_request_exact']
    h.save(HERE/'lane_balance.json',result);h.save(HERE/'lane_balance_pins.json',pins)
    print('LANE20',result['cell20_lane1_native'],model,'decomposition',terms)
    print('Native-state19 request',result['native_state_split19_back_request_left'],result['native_state_split19_back_request_trapezoid'])


if __name__=='__main__':
    import sys
    if '--lane-balance' in sys.argv:lane_balance()
    else:main()
