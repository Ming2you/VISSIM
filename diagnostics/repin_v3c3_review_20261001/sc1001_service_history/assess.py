"""Read completed predictions and existing native caches; no fit or simulation."""
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
C=HERE.parent/'sc1001_connection'
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
LABEL='sc1001_causal_history_routes'


def read(path):
    if str(path).endswith('.gz'):
        with gzip.open(path,'rt',encoding='utf-8') as f:return json.load(f)
    return json.loads(path.read_bytes())


def main():
    output=HERE/'assessment.json'
    if output.exists():raise FileExistsError(output)
    base=read(C/'assessment.json')
    folder=I/('closedloop_recorded2700_lever450_'+LABEL)
    new=read(folder/'summary.json')['results']
    previous=read(I/'closedloop_recorded2700_lever450_sc1001_pair3/summary.json')['results']
    first=read(I/'closedloop_recorded2700_lever450_sc1001_causal_history_pair/summary.json')['results']
    responses=[read(C/(LABEL+'_response_'+str(i)+'.json.gz')) for i in (0,1)]
    binding=read(C/(LABEL+'.json'))
    runtime=read(folder/'runtime.json')
    observation=runtime['metadata']['head_sc1001_shared']
    assert observation['end_sec']==2700
    for row in observation['service'].values():
        assert all(h['end']<=2700 for h in row['history'])
    for case,row in new.items():
        assert row['commands']==previous[case]['commands']
        assert row['physical_cell_states'][0]==previous[case]['physical_cell_states'][0]
        # Expanding source identity alone must leave physical traffic identical.
        for key in ('ttt_omega_veh_h','tracked_outside_residence_veh_h','ramps','physical_cell_states'):
            assert row[key]==first[case][key],(case,key)
        assert all(abs(r['residual'])<1e-7 for r in row['ramps'].values())
    hold=responses[0];ports={}
    for off,fw,group in (('10491','FW_W','OR_D_W'),('10481','FW_E','OR_D_E')):
        owner='storage:'+group+'_storage'
        row=dict(initial=hold['states'][0]['ports'][off],
            arrival=sum(t['vehicles'] for t in hold['transfers'] if t['target']==owner and t['source']=='freeway:'+fw),
            drain=sum(t['vehicles'] for t in hold['transfers'] if t['source']==owner),
            final=hold['states'][-1]['ports'][off])
        assert abs(row['initial']+row['arrival']-row['drain']-row['final'])<1e-7
        ports[off]={**base['ports'][off],'causal_observation':row}
    owner='storage:lane_shared_SC1001'
    head440=sum(t['vehicles'] for t in hold['transfers'] if t['source']==owner and t['end_sec']<=3140)
    head450=sum(t['vehicles'] for t in hold['transfers'] if t['source']==owner)
    entered450=sum(t['vehicles'] for t in hold['transfers'] if t['target']==owner)
    final=hold['states'][-1]['shared']
    assert abs(69+entered450-head450-final)<1e-7
    delta=lambda key:new['release_actual'][key]-new['held_actual'][key]
    cost=lambda p:sum(v for k,v in new['release_actual']['cost_by_stock'].items() if k.startswith(p))-sum(v for k,v in new['held_actual']['cost_by_stock'].items() if k.startswith(p))

    # Offline truth check uses only cached local frames strictly before cutoff.
    # It is not a future source feed and is never passed to the candidate.
    cache_path=HERE.parent/'stopline/s47_rm_hold_frames.json.gz'
    cache=read(cache_path);native_sources={}
    for stamp,rows in sorted(cache['frames'].items(),key=lambda x:float(x[0])):
        if float(stamp)>2700:break
        native_sources={k:v for k,v in native_sources.items() if k in rows}
        for k,r in rows.items():
            link=int(r[0]);decision=int(r[4] or 0)
            if link in (32,10778) or (link==129 and r[2]<239.38422422843928) or decision==1136:
                native_sources[k]='initial_city'
            elif link in (10491,10481) or decision in (1131,1132):native_sources[k]='initial_off'
    current_path=Path('D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47/lane_observations/frame_002700.json')
    current=read(current_path)
    ids={str(r[0]) for r in current['vehicles'] if r[1] in (127,10777)}
    agreed=[];mismatch=[];unknown=[]
    for k in sorted(ids,key=int):
        model=observation['sources'].get(k);actual=native_sources.get(k)
        if model is None:unknown.append(dict(vehicle=k,cached_past_source=actual))
        elif actual is None:pass
        elif model==actual:agreed.append(k)
        else:mismatch.append(dict(vehicle=k,model=model,cached_past_source=actual))
    assert not mismatch,mismatch
    quantity=[]
    for d in responses:
        served=d['quantities']['served_by_movement_veh']
        for side in ('W','E'):
            drain=sum(t['vehicles'] for t in d['transfers'] if t['source']=='storage:OR_D_'+side+'_storage')
            assert abs(drain-sum(v for k,v in served.items() if k.startswith('SC1001_off'+side+'_to_')))<1e-7
        quantity.append(sum(v['net_inflow_veh'] for v in d['quantities']['owners'].values()))
    result=dict(status='CAUSAL_SERVICE_CONNECTION_IMPROVED_NOT_GAIN_QUALIFIED',
        binding=binding['binding'],service_evidence=observation['service'],ports=ports,
        source_audit=dict(current_veh=len(ids),agreed_with_cached_past=len(agreed),mismatch=mismatch,
            unresolved=unknown,caveat='Only past 5s cached observations; fast unseen visits can remain unclassified. Runtime uses150s frames, never this cache.'),
        shared_head=dict(window=[2700,3140],native_bracket=base['shared_head']['native_count_bracket'],
            previous_model=base['shared_head']['model_departures'],current_model=head440,
            model450_entry=entered450,model450_departure=head450,
            final_model=final,final_native=base['shared_head']['final_native127_10777_veh']),
        delta_release_minus_hold=dict(omega_veh_h=delta('ttt_omega_veh_h'),FW_E_veh_h=cost('freeway:FW_E'),
            ramps_veh_h=cost('ramp:'),outside_veh_h=delta('tracked_outside_residence_veh_h'),
            native_omega_veh_h=base['rm_delta_veh_h']['actual_Omega']),
        NP_sums=quantity,source_only_change_traffic_exact=True,physical_resource_max_exceedance=max(r['resource_max_exceedance'] for r in responses),
        tests_passed=23,forecasts=4,native_runs=0,fitting_runs=0,new_fzp_scans=0,sdmpc_selections=0,
        sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            [folder/'summary.json',folder/'runtime.json',C/(LABEL+'.json'),current_path,cache_path]},
        qualification='RM rank retained; head flow closer but final inventory farther due insufficient upstream arrival. Full AD, independent response and SDMPC selection remain unqualified.')
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k in ('status','source_audit','shared_head','delta_release_minus_hold','NP_sums')},ensure_ascii=False))


if __name__=='__main__':main()
