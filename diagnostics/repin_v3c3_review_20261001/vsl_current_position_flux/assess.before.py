"""Read saved unchanged-model traces and existing native caches; no simulation."""
import csv
import gzip
import hashlib
import json
import sys
from pathlib import Path
from statistics import mean

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
pins={}
def data(p):
    raw=p.read_bytes();pins[str(p)]=hashlib.sha256(raw).hexdigest();return raw
def load(p):
    raw=data(p);return json.loads(gzip.decompress(raw) if p.suffix=='.gz' else raw)
def csvrows(p):return list(csv.DictReader(data(p).decode('utf-8-sig').splitlines()))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def main():
    assert not (HERE/'assessment.json').exists()
    protocol=load(HERE/'protocol.json')
    for p,h in protocol['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    prior=I/'closedloop_recorded2250_lever450_trace10681_service66_after43'
    current=I/'closedloop_recorded2250_lever450_vslcurrent_after43'
    nativebase=ROOT.parent/'control-full-review/diagnostics'
    arm_paths={'held_actual':nativebase/'dsd110_20260923/response_recalibration_20260924/gain_response/seed43/none',
               'vsl':nativebase/'metanet_net_gain_goal_20260924/heldout43/observations/vsl'}
    groups={};prefix_sources={};all_detail=[]
    local=load(HERE/'after43_local.json')
    parity_keys=('ttt_omega_veh_h','cost_by_stock','tracked_outside_residence_veh_h','control_area','ramps','commands','physical_cell_states')
    for index,(arm,folder) in enumerate(arm_paths.items()):
        old=load(prior/(arm+'.json'));new=load(current/(arm+'.json'))
        for k in parity_keys:assert old[k]==new[k],(arm,k)
        trace=load(HERE/f'freeway_{index}.json.gz')
        terms=trace['terms'];frames={round(r['time_sec']):r for r in trace['frames']}
        last=new['physical_cell_states'][-1]
        lengths=[n/(r*l) if r*l else None for n,r,l in zip(frames[2250]['vehicles'],frames[2250]['density'],frames[2250]['lanes'])]
        assert all(lengths)
        frames[2700]=dict(time_sec=2700,density=last['density']['FW_E'],speed=last['speed_kmh']['FW_E'],lanes=last['effective_lanes']['FW_E'],
                         vehicles=[r*l*x for r,l,x in zip(last['density']['FW_E'],last['effective_lanes']['FW_E'],lengths)])
        actual={(round(float(r['time_s'])-.1),int(r['cell'])):r for r in csvrows(folder/'cells_30s.csv') if r['road']=='FW_E' and 2250.1-1e-6<=float(r['time_s'])<=2700.1+1e-6}
        flow=[r for r in csvrows(folder/'flows_30s.csv') if r['road']=='FW_E' and 2250.1-1e-6<=float(r['window_start_s']) and float(r['window_end_s'])<=2700.1+1e-6]
        assert len(actual)==16*31 and len(flow)==15*31
        for r in flow:
            assert all(float(r[k])==0 for k in ('unexplained_entries','unexplained_losses','native_removals','conservation_residual_veh'))
        prefix_sources[arm]=[sum(float(r['source_admissions']) for r in flow if round(float(r['window_end_s'])-.1)==t) for t in range(2280,2491,30)]
        results={}
        for c in range(16,21):
            sending=[r for r in trace['resources'] if r['resource']==f'FW_E:cell:{c}' and r['kind']=='freeway_mainline_sending']
            receiving=[r for r in trace['resources'] if r['resource']==f'FW_E:cell:{c+1}' and r['kind']=='freeway_mainline_receiving_after_ramps']
            assert len(sending)==len(receiving)==450
            assert all(s['accepted_total_veh']==r['accepted_total_veh'] for s,r in zip(sending,receiving))
            snapshots=[]
            for t in range(2250,2701,30):
                a=actual[t,c];p=frames[t]
                snapshots.append(dict(time_model=t,time_native=t+.1,observed_speed=float(a['v_kmh']),predicted_speed=p['speed'][c],
                    observed_n=float(a['n_veh']),predicted_n=p['vehicles'][c]))
            ts=[r for r in terms if r['cell']==c]
            windows=[]
            for duration in (30,150,240,450):
                chosen=[r for r in ts if r['time_sec']<2250+duration]
                resource=[r for r in sending if r['end_sec']<=2250+duration]
                observed=[r for r in flow if int(r['cell'])==c and float(r['window_end_s'])<=2250.1+duration+1e-6]
                windows.append(dict(duration_sec=duration,terms={k:mean(r[k] for r in chosen) for k in
                    ('relaxation','convection','anticipation','lane_drop_raw','post_equation_change','speed_before','desired','rho','downstream_rho')},
                    model_through=sum(r['accepted_total_veh'] for r in resource),native_through=sum(float(r['downstream_crossings']) for r in observed),
                    predicted_end_n=frames[2250+duration]['vehicles'][c],native_end_n=float(actual[2250+duration,c]['n_veh'])))
            results[str(c)]=dict(receiving_binds=sum(r['available_veh']<s['available_veh']-1e-9 for s,r in zip(sending,receiving)),
                sending_unserved_veh=sum(r['available_veh']-r['accepted_total_veh'] for r in sending),
                minimum_receiving_slack_veh=min(r['available_veh']-r['accepted_total_veh'] for r in receiving),
                first30_native_change=snapshots[1]['observed_speed']-snapshots[0]['observed_speed'],
                first30_model_change=snapshots[1]['predicted_speed']-snapshots[0]['predicted_speed'],
                speed_rmse=(mean((s['predicted_speed']-s['observed_speed'])**2 for s in snapshots[1:]))**.5,
                windows=windows)
            all_detail.append(dict(arm=arm,cell=c,snapshots=snapshots))
        witness=local[index]['full_stock_witness'];transfers=local[index]['all_transfers_aggregated']
        initial=witness[0]['stock'];final=witness[-1]['stock'];errors={}
        for k in set(initial)|set(final):
            delta=sum(r['vehicles'] for r in transfers if r['target']==k)-sum(r['vehicles'] for r in transfers if r['source']==k)
            errors[k]=final.get(k,0.)-initial.get(k,0.)-delta
        assert max(map(abs,errors.values()))<1e-7
        groups[arm]=dict(exact_prior_parity_keys=parity_keys,omega_ttt=new['ttt_omega_veh_h'],east_ttt=new['cost_by_stock']['freeway:FW_E'],
            outside_ttt=new['tracked_outside_residence_veh_h'],max_stock_residual=max(map(abs,errors.values())),
            resource_max=local[index]['resource_max'],cells=results)
    assert prefix_sources['held_actual']==prefix_sources['vsl']
    deltas={}
    for c in range(16,21):
        a=groups['held_actual']['cells'][str(c)];b=groups['vsl']['cells'][str(c)]
        deltas[str(c)]=[{k:y[k]-x[k] for k in ('model_through','native_through','predicted_end_n','native_end_n')}|{'duration_sec':x['duration_sec']}
                        for x,y in zip(a['windows'],b['windows'])]
    result=dict(status='completed_unchanged_current_model_diagnosis',arms=groups,vsl_minus_held=deltas,
        source_bins_equal_to_2490=True,native_phase_offset_sec=.1,
        limitations=['Native30s grid uses .1sec phase; current exact raw observation/model clock uses integer seconds. Native and model endpoints are near-matched, not byte-identical.',
                    'Source-equal prefix is accounting context, not equal all network boundary histories.',
                    'No new calibration or independent holdout; this checks current full model, not historical route036 component.'],pins=pins)
    save(HERE/'snapshots.json',all_detail);save(HERE/'assessment.json',result)
    for arm,g in groups.items():
        print(arm,'omega',g['omega_ttt'],'east',g['east_ttt'])
        for c,r in g['cells'].items():print(c,'v30 actual/model',r['first30_native_change'],r['first30_model_change'],'receiving_binds',r['receiving_binds'],'terms30',r['windows'][0]['terms'])
    print('VSL differences',json.dumps(deltas))

def assess_prefix():
    target=HERE/'prefix_assessment.json';assert not target.exists()
    prior=load(HERE/'assessment.json');out={}
    base=ROOT.parent/'control-full-review/diagnostics'
    for index,arm in enumerate(('held_actual','vsl')):
        trace=load(HERE/f'freeway_{index}.json.gz')
        frames={round(r['time_sec']):sum(r['vehicles']) for r in trace['frames']}
        folder=base/('dsd110_20260923/response_recalibration_20260924/gain_response/seed43/none' if index==0
                     else 'metanet_net_gain_goal_20260924/heldout43/observations/vsl')
        flow=[r for r in csvrows(folder/'flows_30s.csv') if r['road']=='FW_E'
              and float(r['window_start_s'])>=2250.1-1e-6 and float(r['window_end_s'])<=2490.1+1e-6]
        assert len(flow)==31*8
        model_transfers=[r for r in trace['transfers'] if r['end_sec']<=2490]
        native_totals={k:sum(float(r[k]) for r in flow) for k in
                       ('source_admissions','ramp_merges','off_departures','terminal_exits_inferred')}
        model_totals=dict(source_admissions=sum(r['vehicles'] for r in model_transfers if r['source']=='origin:FW_E'),
            ramp_merges=sum(r['vehicles'] for r in model_transfers if r['source'].startswith('merge_pending:')),
            off_departures=sum(r['vehicles'] for r in model_transfers if r['source']=='freeway:FW_E' and r['target'].startswith('storage:')),
            terminal_exits_inferred=sum(r['vehicles'] for r in model_transfers if r['target']=='external:terminal:FW_E'))
        balance=model_totals['source_admissions']+model_totals['ramp_merges']-model_totals['off_departures']-model_totals['terminal_exits_inferred']
        assert abs(balance-(frames[2490]-frames[2250]))<1e-7
        out[arm]=dict(model_ttt_30s=sum((frames[t]+frames[t+30])*.5*30/3600 for t in range(2250,2490,30)),
            native_ttt_30s=sum((float(r['start_n_veh'])+float(r['end_n_veh']))*.5*30/3600 for r in flow),
            model_flows=model_totals,native_flows=native_totals)
    a,b=out['held_actual'],out['vsl']
    differences={k:b[k]-a[k] for k in ('model_ttt_30s','native_ttt_30s')}
    differences.update({k:{m:b[k][m]-a[k][m] for m in a[k]} for k in ('model_flows','native_flows')})
    save(target,dict(window_model=[2250,2490],window_native=[2250.1,2490.1],
        chosen_by='Existing source_realization_onset cutoff, not cost outcome; source motion diverges at2495.1. Total ramp flows equal but timing/per-ramp histories not claimed equal.',
        horizon_reinitialized=False,arms=out,vsl_minus_held=differences,pins=pins,
        assessment='Both east TTT changes are below existing0.5vehh materiality. Not wholeOmega or full450 qualification. Local flow timing mismatch remains.',
        new_forecasts=0,fit=0))
    print(json.dumps(differences))

def assess_population_response():
    """Use cached native identities only; these are accounting terms, not forces."""
    import math
    dest=HERE.parent/'vsl_population_response'
    target=dest/'assessment.json'
    assert not target.exists(),target
    protocol=load(dest/'protocol.json')
    for p,h in protocol['pins'].items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    cache=I/'baseline_reproduction_20260929/cellwise_calibration/freeway_first/cohort_early'
    native={};initial_equal={};max_error=0.;details=[]
    for seed in (29,43):
        docs={arm:load(cache/f's{seed}_{arm}_frames.json.gz') for arm in ('none','vsl')}
        assert all(d['fields']==['cell','speed_kmh','x_m','lane'] for d in docs.values())
        frames={arm:{round(float(t)-.1):row for t,row in d['frames'].items()} for arm,d in docs.items()}
        initial_equal[str(seed)]={str(t):frames['none'][t]==frames['vsl'][t] for t in (2220,2250)}
        assert initial_equal[str(seed)]['2220']
        for arm in ('none','vsl'):
            results={}
            for c in range(16,21):
                rows=[]
                for t in range(2250,2490,5):
                    all_a,all_b=frames[arm][t],frames[arm][t+5]
                    a={vid:v[1] for vid,v in all_a.items() if v[0]==c}
                    b={vid:v[1] for vid,v in all_b.items() if v[0]==c}
                    # Empty cell means have no vehicle-population identity.
                    assert a and b,(seed,arm,c,t)
                    va=math.fsum(a.values())/len(a);vb=math.fsum(b.values())/len(b)
                    stay=math.fsum(b[k]-a[k] for k in a.keys() & b.keys())/len(b)
                    incoming=math.fsum(b[k]-va for k in b.keys()-a.keys())/len(b)
                    outgoing=-math.fsum(a[k]-va for k in a.keys()-b.keys())/len(b)
                    residual=vb-va-stay-incoming-outgoing
                    max_error=max(max_error,abs(residual));assert abs(residual)<1e-10
                    rows.append(dict(time=t+.1,n_before=len(a),n_after=len(b),v_before=va,v_after=vb,
                        stay=stay,enter=incoming,leave=outgoing,composition=incoming+outgoing,
                        change=vb-va,ttt_veh_h=(len(a)+len(b))*.5*5/3600,
                        entries=len(b.keys()-a.keys()),departures=len(a.keys()-b.keys()),
                        entries_from_other_fw_cells=sum(k in all_a for k in b.keys()-a.keys()),
                        departures_seen_in_other_fw_cells=sum(k in all_b for k in a.keys()-b.keys())))
                results[str(c)]={str(duration):{key:math.fsum(r[key] for r in rows if r['time']<2250+duration)
                    for key in ('stay','enter','leave','composition','change','ttt_veh_h','entries','departures',
                                'entries_from_other_fw_cells','departures_seen_in_other_fw_cells')}
                    for duration in (30,150,240)}
                details.append(dict(seed=seed,arm=arm,cell=c,rows=rows))
            native[f'{seed}_{arm}']=results
    differences={str(seed):{str(c):{str(d):{k:native[f'{seed}_vsl'][str(c)][str(d)][k]-
                            native[f'{seed}_none'][str(c)][str(d)][k]
                       for k in native[f'{seed}_none'][str(c)][str(d)]}
                       for d in (30,150,240)} for c in range(16,21)} for seed in (29,43)}
    model={}
    for index,arm in enumerate(('none','vsl')):
        trace=load(HERE/f'freeway_{index}.json.gz');results={}
        for c in range(16,21):
            results[str(c)]={}
            for duration in (30,150,240):
                rows=[r for r in trace['terms'] if r['cell']==c and r['time_sec']<2250+duration]
                assert len(rows)==duration
                predicted_change=math.fsum(r['speed_final']-r['speed_before'] for r in rows)
                terms={key:math.fsum(r[key] for r in rows) for key in
                       ('relaxation','convection','anticipation','post_equation_change')}
                # Clamp/lane-drop corrections need not be zero.
                terms['equation_residual']=predicted_change-math.fsum(terms.values())
                terms['change']=predicted_change
                results[str(c)][str(duration)]=terms
        model[arm]=results
    model_diff={str(c):{str(d):{k:model['vsl'][str(c)][str(d)][k]-model['none'][str(c)][str(d)][k]
                     for k in model['none'][str(c)][str(d)]} for d in (30,150,240)} for c in range(16,21)}
    save(dest/'details.json',dict(native=details,model=model))
    result=dict(status='completed_cached_response_accounting',native=native,native_vsl_minus_nc=differences,
                model_seed43_vsl_minus_nc=model_diff,common_native_initial=initial_equal,
                identity_max_abs_kmh=max_error,new_forecasts=0,new_native_runs=0,fit=0,pins=pins,
                limitations=protocol['limitations'])
    save(target,result)
    print('identity residual',max_error,'initial',initial_equal)
    for seed in (29,43):
        for c in range(16,21):
            r=differences[str(seed)][str(c)]['30']
            print(seed,c,'first30 native dV/stay/composition',*[round(r[k],4) for k in ('change','stay','composition')],
                  'deltaTTT240',round(differences[str(seed)][str(c)]['240']['ttt_veh_h'],6))
    print('model43 first30',json.dumps({c:r['30'] for c,r in model_diff.items()}))


def assess_flux_position():
    """Conditional accounting only: Qout = integral(Nv/L) - change(sum(x/L))."""
    import math
    dest=HERE.parent/'vsl_population_response';target=dest/'flux_position.json'
    assert not target.exists()
    protocol=load(dest/'flux_protocol.json')
    for p,h in protocol['pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    geometry=load(I/'selected/port_gain/geometry.json')
    cells={c['cell']:c for c in geometry['cells'] if c['road']=='FW_E'}
    chosen=(16,17,19)
    assert not any(b.get('from_cell') in chosen or b.get('to_cell') in chosen
        for b in geometry['boundaries'] if b['road']=='FW_E' and b['kind'] in ('ramp','offramp'))
    cache=I/'baseline_reproduction_20260929/cellwise_calibration/freeway_first/cohort_early'
    output={}
    for seed in (29,43):
        for arm in ('none','vsl'):
            doc=load(cache/f's{seed}_{arm}_frames.json.gz')
            frames={round(float(t)-.1):r for t,r in doc['frames'].items()}
            flow=csvrows(Path(protocol['native_flow_paths'][f'{seed}_{arm}']))
            results={}
            for c in chosen:
                spec=cells[c];length=spec['length_km'];start=spec['start_m']
                moment={};spatial={}
                for t in range(2250,2491,5):
                    vehicles=[r for r in frames[t].values() if r[0]==c]
                    assert all(start-1e-6<=r[2]<=spec['end_m']+1e-6 for r in vehicles)
                    moment[t]=math.fsum((r[2]-start)/(length*1000) for r in vehicles)
                    spatial[t]=math.fsum(r[1] for r in vehicles)/length
                results[str(c)]={}
                for duration in (30,150,240):
                    selected=[r for r in flow if r['road']=='FW_E' and int(r['cell'])==c
                        and float(r['window_start_s'])>=2250.1-1e-6
                        and float(r['window_end_s'])<=2250.1+duration+1e-6]
                    assert len(selected)==duration//30
                    assert all(float(r[k])==0 for r in selected for k in
                        ('ramp_merges','off_departures','native_removals','unexplained_entries','unexplained_losses','conservation_residual_veh'))
                    q=math.fsum((spatial[t]+spatial[t+5])*2.5/3600 for t in range(2250,2250+duration,5))
                    delta=moment[2250+duration]-moment[2250]
                    observed=math.fsum(float(r['downstream_crossings']) for r in selected)
                    results[str(c)][str(duration)]=dict(observed=observed,spatial_integral=q,
                        moment_change=delta,position_accounting=q-delta,
                        spatial_error=q-observed,position_error=q-delta-observed)
            output[f'{seed}_{arm}']=results
    diff={str(seed):{str(c):{str(d):{k:output[f'{seed}_vsl'][str(c)][str(d)][k]-output[f'{seed}_none'][str(c)][str(d)][k]
                      for k in output[f'{seed}_none'][str(c)][str(d)]} for d in (30,150,240)}
          for c in chosen} for seed in (29,43)}
    save(target,dict(arms=output,vsl_minus_nc=diff,pins=pins,limitations=protocol['limitations']))
    for seed in (29,43):
        for c in chosen:
            print('flux',seed,c,diff[str(seed)][str(c)]['240'])


def assess_density_reconstruction():
    """Screen causal spatial closure from current means, without model changes."""
    import math
    from collections import Counter
    dest=HERE.parent/'vsl_density_reconstruction'
    target=dest/'assessment.json'
    assert not target.exists()
    protocol=load(dest/'protocol.json')
    for p,h in protocol['source_pins'].items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    geometry=load(I/'selected/port_gain/geometry.json')
    cells={c['cell']:c for c in geometry['cells'] if c['road']=='FW_E'}
    centers={c:(v['start_m']+v['end_m'])/2000 for c,v in cells.items()}
    cache=I/'baseline_reproduction_20260929/cellwise_calibration/freeway_first/cohort_early'
    details=[];scores={};initial={}
    def score(rows):
        a=math.sqrt(mean((r['whole']-r['actual_half'])**2 for r in rows))
        b=math.sqrt(mean((r['reconstructed']-r['actual_half'])**2 for r in rows))
        return dict(n=len(rows),whole_rmse=a,reconstructed_rmse=b,
                    improvement_fraction=1-b/a if a else 0,
                    mean_error_whole=mean(r['whole']-r['actual_half'] for r in rows),
                    mean_error_reconstructed=mean(r['reconstructed']-r['actual_half'] for r in rows),
                    nonzero_slope=sum(r['slope']!=0 for r in rows))
    for seed in (29,43):
        for arm in ('none','vsl'):
            doc=load(cache/f's{seed}_{arm}_frames.json.gz')
            assert doc['fields']==['cell','speed_kmh','x_m','lane']
            frames={round(float(t)-.1):r for t,r in doc['frames'].items()}
            if arm=='none':initial[seed]=frames[2250]
            else:assert frames[2250]==initial[seed]
            rows=[]
            for t in range(2250,2491,5):
                counts=Counter(r[0] for r in frames[t].values())
                rho={c:counts[c]/v['lane_km'] for c,v in cells.items()}
                for receiver in range(16,21):
                    j=receiver+1;spec=cells[j]
                    left=(rho[j]-rho[j-1])/(centers[j]-centers[j-1])
                    right=(rho[j+1]-rho[j])/(centers[j+1]-centers[j])
                    slope=math.copysign(min(abs(left),abs(right)),left) if left*right>0 else 0.
                    reconstructed=rho[j]-slope*spec['length_km']/4
                    # Monotone, bounded half means preserve the full-cell inventory.
                    distal=rho[j]+slope*spec['length_km']/4
                    assert min(rho[j-1],rho[j],rho[j+1])-1e-10<=reconstructed
                    assert reconstructed<=max(rho[j-1],rho[j],rho[j+1])+1e-10
                    assert min(reconstructed,distal)>=-1e-10
                    assert abs((reconstructed+distal)/2-rho[j])<1e-10
                    vehicles=[r for r in frames[t].values() if r[0]==j]
                    assert all(spec['start_m']-1e-6<=r[2]<=spec['end_m']+1e-6 for r in vehicles)
                    upstream=sum(r[2]<(spec['start_m']+spec['end_m'])/2 for r in vehicles)
                    rows.append(dict(seed=seed,arm=arm,time=t+.1,receiver=receiver,downstream=j,
                        whole=rho[j],actual_half=upstream/(spec['lane_km']/2),
                        reconstructed=reconstructed,slope=slope,left_rho=rho[j-1],right_rho=rho[j+1]))
            scores[f'{seed}_{arm}']=dict(pooled=score(rows),
                cells={str(c):score([r for r in rows if r['receiver']==c]) for c in range(16,21)})
            details.extend(rows)
    passed=all(r['pooled']['improvement_fraction']>=.1 and
               all(c['improvement_fraction']>=-.1 for c in r['cells'].values()) for r in scores.values())
    save(dest/'details.json',dict(rows=details))
    save(target,dict(status='screen_completed',candidate_passed=passed,scores=scores,
        pins=pins,new_forecasts=0,fit=0,new_native=0,limitations=protocol['limitations']))
    print('density reconstruction',json.dumps(scores),'passed',passed)


def assess_density_rollout():
    """Six bounded scalar forecasts; retain the earlier failed proxy screen."""
    import math
    dest=HERE.parent/'vsl_density_rollout';target=dest/'assessment.json'
    assert not target.exists()
    protocol=load(dest/'protocol.json')
    for p,h in protocol['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    assert load(dest/'baseline_parity.json')['passed']
    baseline_rm=load(HERE.parent/'rm47_service66_response/assessment.json')
    baseline_vsl=load(HERE/'assessment.json')
    native_vsl=load(HERE.parent/'urban66_u7/assessment.json')['native43_delta_omega_veh_h']['vsl']
    definitions=(('baseline43',2250,'density_base_after43',('held_actual','vsl')),
                 ('candidate43',2250,'density_half_after43',('held_actual','vsl')),
                 ('candidate47',2700,'density_half_after_rm47',('held_actual','release_actual')))
    results={};total_seconds=0.;worst_balance=0.;worst_resource=0.
    for label,start,suffix,arms in definitions:
        folder=I/f'closedloop_recorded{start}_lever450_{suffix}'
        mode='after43' if start==2250 else 'after_rm47'
        local=load(dest/label/(mode+'_local.json'));assert len(local)==2
        assert local[0]['full_stock_witness'][0]==local[1]['full_stock_witness'][0]
        cases={}
        for index,arm in enumerate(arms):
            point=load(folder/(arm+'.json'));total_seconds+=point['wall_sec']
            oldfolder=(I/'closedloop_recorded2250_lever450_vslcurrent_after43' if start==2250 else
                       I/'closedloop_recorded2700_lever450_service66rm47_after_rm47')
            old=load(oldfolder/(arm+'.json'))
            assert point['commands']==old['commands']
            assert point['physical_cell_states'][0]==old['physical_cell_states'][0]
            assert point['validation']['all_actuator_and_step_constraints_checked']
            witness=local[index]['full_stock_witness'];transfers=local[index]['all_transfers_aggregated']
            first,last=witness[0]['stock'],witness[-1]['stock']
            error=max(abs(last.get(k,0.)-first.get(k,0.)-
                math.fsum(r['vehicles'] for r in transfers if r['target']==k)+
                math.fsum(r['vehicles'] for r in transfers if r['source']==k)) for k in first.keys()|last.keys())
            assert error<1e-7 and local[index]['resource_max']<1e-7
            worst_balance=max(worst_balance,error);worst_resource=max(worst_resource,local[index]['resource_max'])
            trace=load(dest/label/f'freeway_{index}.json.gz');assert len(trace['terms'])==2250
            flow=dict(source=0.,merge=0.,off=0.,terminal=0.)
            for r in transfers:
                if r['target']=='freeway:FW_E':
                    key='source' if r['source']=='origin:FW_E' else 'merge'
                    assert key=='source' or r['source'].startswith('merge_pending:')
                    flow[key]+=r['vehicles']
                elif r['source']=='freeway:FW_E':
                    key='terminal' if r['target']=='external:terminal:FW_E' else 'off'
                    assert key=='terminal' or r['target'].startswith('storage:')
                    flow[key]+=r['vehicles']
            cost=point['cost_by_stock']
            cases[arm]=dict(omega=point['ttt_omega_veh_h'],east=cost['freeway:FW_E'],west=cost['freeway:FW_W'],
                ramps=math.fsum(v for k,v in cost.items() if k.startswith('ramp:')),
                outside=point['tracked_outside_residence_veh_h'],**flow,
                altered_density_calls=sum(r['density_reconstruction_delta']!=0 for r in trace['terms']),
                max_abs_density_change=max(abs(r['density_reconstruction_delta']) for r in trace['terms']),
                through={str(c):{str(duration):math.fsum(r['accepted_total_veh'] for r in trace['resources']
                    if r['kind']=='freeway_mainline_sending' and r['resource']==f'FW_E:cell:{c}'
                    and r['end_sec']<=start+duration) for duration in (150,240,450)} for c in range(16,21)})
        a,b=(cases[arm] for arm in arms)
        delta={k:b[k]-a[k] for k in ('omega','east','west','ramps','outside','source','merge','off','terminal')}
        delta['through']={c:{d:b['through'][c][d]-a['through'][c][d] for d in a['through'][c]} for c in a['through']}
        results[label]=dict(cases=cases,delta=delta)
    comparisons={}
    for c in ('16','19'):
        comparisons[c]={}
        for duration in (240,450):
            observed=next(r for r in baseline_vsl['vsl_minus_held'][c] if r['duration_sec']==duration)['native_through']
            old=results['baseline43']['delta']['through'][c][str(duration)]
            new=results['candidate43']['delta']['through'][c][str(duration)]
            comparisons[c][str(duration)]=dict(native=observed,baseline=old,candidate=new,
                baseline_abs_error=abs(old-observed),candidate_abs_error=abs(new-observed))
    rm_native=baseline_rm['release_minus_hold']['native'];rm_old=baseline_rm['release_minus_hold']['current']
    rm_new=results['candidate47']['delta']
    rm_ok=rm_new['omega']>0 and abs(rm_new['omega']-rm_native['omega'])<=abs(rm_old['omega']-rm_native['omega'])
    vsl_old=results['baseline43']['delta']['omega'];vsl_new=results['candidate43']['delta']['omega']
    save(target,dict(status='bounded_autonomous_response_completed_not_adopted',results=results,
        vsl_native_delta_omega=native_vsl,vsl_baseline_abs_cost_error=abs(vsl_old-native_vsl),
        vsl_candidate_abs_cost_error=abs(vsl_new-native_vsl),flow_comparison=comparisons,
        rm_native=rm_native,rm_baseline=rm_old,rm_direction_and_cost_error_preserved=rm_ok,
        max_stock_residual=worst_balance,max_resource_exceedance=worst_resource,
        forecasts=6,forecast_compute_sec=total_seconds,fit=0,new_native=0,new_fzp=0,
        original_proxy_screen_passed=False,protocol_amendment=protocol['protocol_amendment'],
        production_adopted=False,AD_verified=False,goal_qualified=False,pins=pins))
    print(json.dumps(dict(vsl=(native_vsl,vsl_old,vsl_new),rm=(rm_native['omega'],rm_old['omega'],rm_new['omega']),
                         flow=comparisons,conservation=worst_balance,resource=worst_resource,seconds=total_seconds)))


if __name__=='__main__':
    if '--density-rollout' in sys.argv:assess_density_rollout()
    elif '--density-reconstruction' in sys.argv:assess_density_reconstruction()
    elif '--flux-position' in sys.argv:assess_flux_position()
    elif '--population' in sys.argv:assess_population_response()
    elif '--prefix' in sys.argv:assess_prefix()
    else:main()
