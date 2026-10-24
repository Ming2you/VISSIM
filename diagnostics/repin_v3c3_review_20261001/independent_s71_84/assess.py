"""Assess completed seed71 outputs; no FZP read, forecast, fitting or simulator."""
import hashlib
import bisect
import gzip
import itertools
import json
import math
from pathlib import Path
import sys

D=Path(__file__).resolve().parent
ROOT=D.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
ARMS=('nc','rm','vsl','both')
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def score(actual,predicted,threshold):
    assert set(actual)==set(predicted)==set(ARMS)
    assert threshold>0 and all(math.isfinite(x) for x in (*actual.values(),*predicted.values()))
    pairs={}
    for baseline,arm in itertools.combinations(ARMS,2):
        a=actual[arm]-actual[baseline];p=predicted[arm]-predicted[baseline]
        material=abs(a)>=threshold
        tolerance=max(threshold,.5*abs(a))
        pairs[arm+' minus '+baseline]=dict(actual_delta_veh_h=a,predicted_delta_veh_h=p,
            prediction_error_veh_h=p-a,material=material,allowed_error_veh_h=tolerance,
            passed=(a*p>0 and abs(p-a)<=tolerance) if material else None)
    selected=min(ARMS,key=lambda a:predicted[a]);best=min(ARMS,key=lambda a:actual[a])
    regret=actual[selected]-actual[best]
    primary=[v for k,v in pairs.items() if k.endswith(' minus nc') and v['material']]
    return dict(contrasts=pairs,predicted_choice=selected,actual_choice=best,
        actual_regret_veh_h=regret,regret_passed=regret<=threshold,
        material_nc_contrasts=len(primary),
        primary_response_passed=all(v['passed'] for v in primary) if primary else None,
        all_pair_material_response_passed=all(v['passed'] for v in pairs.values() if v['material'])
            if any(v['material'] for v in pairs.values()) else None,
        predictive_effect_gate=(all(v['passed'] for v in primary) and regret<=threshold) if primary else None)


def self_test():
    a=dict(nc=0,rm=-2,vsl=1,both=-3)
    assert score(a,a,.5)['predictive_effect_gate'] is True
    wrong=dict(a,vsl=-1)
    assert score(a,wrong,.5)['primary_response_passed'] is False
    weak=dict(a,rm=-.01)
    assert score(a,weak,.5)['contrasts']['rm minus nc']['passed'] is False
    adverse=dict(a,nc=-4)
    assert score(a,adverse,.5)['regret_passed'] is False
    small=dict(nc=0,rm=-.1,vsl=.1,both=-.2)
    assert score(small,small,.5)['predictive_effect_gate'] is None
    border=dict(nc=0,rm=-.5,vsl=.5,both=-1)
    assert score(border,border,.5)['material_nc_contrasts']==3
    try:score(dict(a,rm=float('nan')),a,.5)
    except AssertionError:pass
    else:raise AssertionError('Nonfinite score accepted')
    print('Assessment logic: 7 synthetic checks PASS; no native outcomes read')


def main():
    assert not (D/'assessment.json').exists(), 'Preserve previous assessment'
    status=load(D/'postprocess_status.json')
    assert status['phase']=='complete_pending_assessment', status
    plan=load(D/'plan.json');post=load(D/'postprocess_plan.json')
    for p,h in post['source_pins'].items():assert sha(Path(p))==h,p
    assert sha(D/'candidate_config.json')==post['config_sha256']
    assert sha(Path(plan['old_STOP']['path']))==plan['old_STOP']['sha256']
    for p,h in plan['model_pins'].items():assert sha(Path(p))==post['source_pins'].get(p,h),p
    native_path=I/'native_rm_observation2700_s71_four84/analysis/summary.json'
    native=load(native_path);out=Path(post['forecast_output']);report=load(out/'summary.json')
    assert native['counterfactual_valid'] and native['paired_prefix_exact'] and native['common_start_vehicle_records_exact']
    assert (native['start_sec'],native['end_sec'])==(2250,2700)
    assert report['start_sec']==2250 and report['duration_sec']==450
    assert report['optimizer_iterations']==0 and not report['native_started'] and not report['future_observation_inputs']
    assert report['prediction_conditioned_on_executed_commands']
    assert tuple(report['results'])==('held_actual','rm','vsl','both')
    mapping=dict(nc='held_actual',rm='rm',vsl='vsl',both='both')
    rows={arm:load(out/(case+'.json')) for arm,case in mapping.items()}
    local=load(D/'after71_local.json')
    assert len(local)==4 and all(len(p['full_stock_witness'])==4 for p in local)
    assert max(p['resource_max'] for p in local)<1e-7
    assert all(p['full_stock_witness'][0]==local[0]['full_stock_witness'][0] for p in local)
    ramps=load(out/'ramp_response_audit.json')
    assert set(ramps['arms'])==set(ARMS) and ramps['new_model_predictions']==0 and ramps['fzp_rescans']==0
    actual={a:native['arms'][a]['TTT_0_2700_veh_h'] for a in ARMS}
    predicted={a:rows[a]['ttt_omega_veh_h'] for a in ARMS}
    grading=score(actual,predicted,plan['materiality_veh_h'])
    table={}
    for a,row in rows.items():
        assert row['executed_control_blocks']==[0,1,2] and row['validation']['all_actuator_and_step_constraints_checked']
        assert abs(sum(row['cost_by_stock'].values())-row['ttt_omega_veh_h'])<1e-7
        assert max(abs(r['residual']) for r in row['ramps'].values())<1e-7
        assert row['physical_cell_states'][0]==rows['nc']['physical_cell_states'][0]
        for block,command in enumerate(row['commands']):
            for key in ('green_times','offsets'):assert command[key]==rows['nc']['commands'][block][key]
            for ramp,value in command['meters'].items():
                previous=10 if block==0 else row['commands'][block-1]['meters'][ramp]
                assert abs(value-previous)<=2
        n=native['arms'][a];nc=native['arms']['nc'];bc=rows['nc']['cost_by_stock']
        delta_cost={k:v-bc[k] for k,v in row['cost_by_stock'].items()}
        table[a]=dict(native_window_omega_veh_h=n['TTT_2250p1_2700_veh_h'],
            predicted_window_omega_veh_h=row['ttt_omega_veh_h'],
            actual_delta_omega_veh_h=actual[a]-actual['nc'],predicted_delta_omega_veh_h=predicted[a]-predicted['nc'],
            native_delta_outside_observed_veh_h=n['outside_Omega_residence_veh_h']-nc['outside_Omega_residence_veh_h'],
            native_delta_uninserted_delay_veh_h=n['native_uninserted_delay_veh_h']-nc['native_uninserted_delay_veh_h'],
            native_delta_total_including_uninserted_veh_h=n['native_total_time_including_uninserted_veh_h']-nc['native_total_time_including_uninserted_veh_h'],
            model_delta_tracked_outside_veh_h=row['tracked_outside_residence_veh_h']-rows['nc']['tracked_outside_residence_veh_h'],
            model_delta_cost_by_stock=delta_cost,
            normal_omega_exit_events=n['Omega_TTD_events'],end_omega_vehicles=n['Omega_end_vehicles'],
            native_removals=n['native_removals'],unresolved_disappearances=n['unresolved_Omega_disappearances'],
            ramps=ramps['arms'][a])
    inputs=(native_path,out/'summary.json',out/'ramp_response_audit.json',D/'after71_local.json',*(out/(case+'.json') for case in mapping.values()))
    result=dict(status='complete_cost_assessment',seed=71,fit_calls=0,new_native_runs=0,new_forecasts=0,
        fzp_rescans=0,controller_or_9000_qualified=False,grading=grading,arms=table,
        all_saved_model_stocks_checked=True,resource_max=max(p['resource_max'] for p in local),
        forecast_compute_seconds=sum(r['wall_sec'] for r in rows.values()),
        limitations=['Independent seed at one fixed-command state; does not erase earlier43/47/67 failures.',
            'Native window2250.1..2700 versus model2250..2700; effect comparisons use full native paired costs with exact shared prefix.',
            'Same prefix does not imply identical future inserted vehicle counts or composition.',
            'Native entire-network time plus uninserted delay and tracked model outside cost have distinct scopes.',
            'Off-ramp/mainline flow and recovery diagnostics still need causal assessment; cost-score pass alone is insufficient.',
            'Small effects are unresolved, not forced gain signs; no material excitation yields no gain-validation pass.'],
        evidence_pins={str(p):sha(p) for p in inputs})
    (D/'assessment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],grading=grading),allow_nan=False))


def flow_assessment():
    """Reuse native obs150 and the already saved model response; no new rollout."""
    sys.path.insert(0,str(ROOT))
    from evaluation.controllers import obs150_contract as oc
    from evaluation.controllers.obs150_observation import check_rule_crosscheck
    from diagnostics.repin_v3c3_review_20261001.s67_policy_response81.assess_flow82 import cell_flux
    assert not (D/'flow_assessment.json').exists()
    assert load(D/'postprocess_status.json')['phase']=='complete_pending_assessment'
    assert load(D/'assessment.json')['status']=='complete_cost_assessment'
    post=load(D/'postprocess_plan.json');out=Path(post['forecast_output'])
    runs=Path('D:/VISSIM_runs/20261003_independent_s71_four84')
    assert not (runs/'STOP').exists()
    evidence={}
    def read(p):evidence[str(p)]=sha(p);return load(p)
    geo=read(I/'selected/port_gain/geometry.json')
    assert geo['network']['sha256']==load(D/'plan.json')['network_sha256']
    chains={road:{int(v['link']):v for v in rows} for road,rows in geo['chains'].items()}
    cells={road:sorted((v for v in geo['cells'] if v['road']==road),key=lambda v:v['cell']) for road in chains}
    assert all([v['cell'] for v in c]==list(range(31)) for c in cells.values())
    ramp_audit=read(out/'ramp_response_audit.json')
    local=read(D/'after71_local.json');mapping=dict(nc='held_actual',rm='rm',vsl='vsl',both='both')
    cases={};flux_rows=[];snapshots=[]
    for number,(arm,name) in enumerate(mapping.items()):
        prediction=read(out/(name+'.json'))
        trace_path=out/(name+'_RM_C10681_trace.json.gz');evidence[str(trace_path)]=sha(trace_path)
        off=json.load(gzip.open(trace_path,'rt',encoding='utf-8'))['offramp_network_diagnostics']
        folder=runs/arm/f'decisions_sdmpc31_g_2250_{arm}_s71'
        actual={};offstock={};totals={};removed=[]
        for sec in (2250,2400,2550,2700):
            raw=read(folder/f'state_{sec:06d}.json')
            assert raw['sim_sec']==sec and raw['vehicle_records']['complete']
            vehicles=raw['vehicle_records']['records']
            offstock[sec]={key:sum(int(v['link_no'])==int(key) for v in vehicles) for key in off['descriptions']}
            actual[sec]={}
            for road in chains:
                ends=[c['end_m'] for c in cells[road]];bins=[[] for _ in range(31)]
                for vehicle in vehicles:
                    link=int(vehicle['link_no'])
                    if link in chains[road]:
                        pos=chains[road][link]['offset_m']+float(vehicle['position_m'])
                        bins[min(bisect.bisect_right(ends,pos),30)].append(float(vehicle['speed_kph']))
                actual[sec][road]=[len(v) for v in bins]
                model=next(s for s in prediction['physical_cell_states'] if s['time_sec']==sec)
                pn=[max(0.,rho)*max(lane,1e-9)*(cell['end_m']-cell['start_m'])/1000
                    for rho,lane,cell in zip(model['density'][road],model['effective_lanes'][road],cells[road])]
                witness=next(s['stock'] for s in local[number]['full_stock_witness'] if s['time_sec']==sec)
                assert abs(sum(pn)-witness['freeway:'+road])<1e-7
                if sec==2250:assert max(abs(p-a) for p,a in zip(pn,actual[sec][road]))<1e-7
                for c,values in enumerate(bins):
                    snapshots.append(dict(arm=arm,road=road,time_sec=sec,cell=c,
                        native_stock=len(values),predicted_stock=pn[c],
                        native_speed_kmh=sum(values)/len(values) if values else None,
                        predicted_speed_kmh=model['speed_kmh'][road][c]))
            if sec==2250:continue
            obs=raw['obs150'];detectors,_=oc.read_detector_csv(obs['detector_config']['path'],obs['detector_config']['sha256'])
            oc.validate_raw(obs,detectors,expected_simres=10);check_rule_crosscheck(obs,detectors)
            bundle=oc.load_bundle(raw)
            boundaries=oc.evaluate_boundaries(obs,detectors,bundle.frame_end,bundle.frame_start,bundle.err_rows)
            assert obs['window']==dict(start_s=sec-150,end_s=sec)
            for ref,value in boundaries.items():totals[ref]=totals.get(ref,0)+value.cross
            removed.extend(oc.window_removals(bundle.err_rows,sec-150,sec))
        transfers=local[number]['all_transfers_aggregated']
        flow=lambda source,target:sum(v['vehicles'] for v in transfers if v['source']==source and v['target']==target)
        port_results={}
        for key,desc in off['descriptions'].items():
            count=sum(int(v['link'])==int(key) for v in removed)
            initial=offstock[2250][key];ending=offstock[2700][key];entry=totals['off_entry:'+key]
            drain=initial+entry-count-ending
            assert drain>=0
            first=off['states'][0]['ports'][key];last=off['states'][-1]['ports'][key]
            assert abs(first['stock']-initial)<1e-7
            assert abs(last['stock']-initial-last['admitted']+last['departed'])<1e-7
            port_results[key]=dict(actual=dict(initial_stock=initial,entry=entry,drain=drain,removals=count,final_stock=ending),
                predicted=dict(initial_stock=first['stock'],entry=last['admitted'],drain=last['departed'],final_stock=last['stock']))
        road_results={}
        for road in chains:
            assert not [v for v in removed if int(v['link']) in chains[road]], 'Mainline removals require explicit cell assignment before flux reconstruction'
            ports=[b for b in geo['boundaries'] if b['road']==road]
            ramp_ports=[b for b in ports if b['kind']=='ramp'];exit_ports=[b for b in ports if b['kind']=='offramp']
            am={b['to_cell']:ramp_audit['arms'][arm][b['id']]['actual']['merge'] for b in ramp_ports}
            pm={b['to_cell']:prediction['ramps'][b['id']]['merge'] for b in ramp_ports}
            ae={b['from_cell']:port_results[str(b['connector'])]['actual']['entry'] for b in exit_ports}
            pe={b['from_cell']:port_results[str(b['connector'])]['predicted']['entry'] for b in exit_ports}
            an0,an1=actual[2250][road],actual[2700][road]
            pn0=[r['predicted_stock'] for r in snapshots if r['arm']==arm and r['road']==road and r['time_sec']==2250]
            pn1=[r['predicted_stock'] for r in snapshots if r['arm']==arm and r['road']==road and r['time_sec']==2700]
            source=totals['source:'+road];terminal=totals['chain_end:'+road]
            psource=flow('origin:'+road,'freeway:'+road);pterminal=flow('freeway:'+road,'external:terminal:'+road)
            af=cell_flux(an0,an1,source,terminal,am,ae);pf=cell_flux(pn0,pn1,psource,pterminal,pm,pe)
            road_results[road]=dict(actual_source=source,predicted_source=psource,actual_terminal=terminal,predicted_terminal=pterminal,
                actual_merge=sum(am.values()),predicted_merge=sum(pm.values()),actual_off_entry=sum(ae.values()),predicted_off_entry=sum(pe.values()),
                actual_initial_stock=sum(an0),predicted_initial_stock=sum(pn0),actual_final_stock=sum(an1),predicted_final_stock=sum(pn1))
            for cell in range(31):
                incoming=pf[cell-1]-af[cell-1]+pm.get(cell,0)-am.get(cell,0)
                outgoing=pf[cell]-af[cell]+pe.get(cell,0)-ae.get(cell,0)
                residual=(pn1[cell]-an1[cell])-(pn0[cell]-an0[cell]+incoming-outgoing)
                assert abs(residual)<1e-7
                flux_rows.append(dict(arm=arm,road=road,cell=cell,actual_through=af[cell],predicted_through=pf[cell],
                    incoming_error=incoming,outgoing_error=outgoing,stock_error=pn1[cell]-an1[cell],residual=residual))
        cases[arm]=dict(roads=road_results,offramps=port_results)
    assert all(sha(Path(p))==h for p,h in evidence.items())
    result=dict(status='complete_cached_flow_assessment',cases=cases,cell_flux=flux_rows,snapshots=snapshots,
        max_balance_error=max(abs(r['residual']) for r in flux_rows),new_forecasts=0,new_native=0,fzp_reads=0,
        limitations=['Cell through-flow inferred by continuity, not a direct detector observation.',
            '150s snapshots cannot identify exact onset/recovery timing.',
            'Off-ramp drain inferred from connector stock, entry and removal counts; initial physical/model scope checked.',
            'Future native states are evaluation targets only. Source and composition differences remain part of the response.'],inputs_sha256=evidence)
    (D/'flow_assessment.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],max_balance_error=result['max_balance_error'],cells=len(flux_rows))))


def cohort_assessment():
    """Attribute observed boundary crossings to the common initial population.

    Reuse hash-verified MER chunks/frames; no FZP, forecast or parameter fitting.
    Individual crossing counts use the same detector-offset identity as obs150.
    Crossing times inside detector-offset segments are not inferred.
    """
    from collections import Counter, defaultdict
    sys.path.insert(0,str(ROOT))
    from evaluation.controllers import obs150_contract as oc
    from evaluation.controllers import obs150_capture as capture
    from evaluation.controllers.obs150_observation import check_rule_crosscheck
    assert not (D/'cohort_assessment.json').exists()
    assert load(D/'completion.json')['status']=='COMPLETE_INDEPENDENT_VALIDATION_FAILED_NOT_QUALIFIED'
    flow=load(D/'flow_assessment.json');geo=load(I/'selected/port_gain/geometry.json')
    chain={int(r['link']) for r in geo['chains']['FW_E']}
    runs=Path('D:/VISSIM_runs/20261003_independent_s71_four84')
    pins={};cases={};common=None;late_records=[]
    for arm in ARMS:
        folder=runs/arm/f'decisions_sdmpc31_g_2250_{arm}_s71'
        crossings=defaultdict(Counter);initial=None;removed_ids=set()
        bundles={};by_ordinal=defaultdict(dict)
        for sec in (2250,2400,2550,2700):
            path=folder/f'state_{sec:06d}.json';pins[str(path)]=sha(path);raw=load(path)
            bundles[sec]=oc.load_bundle(raw)
        last=bundles[2700].obs['mer'];source=Path(last['source']);pins[str(source)]=sha(source)
        table,_=oc.read_detector_csv(bundles[2700].obs['detector_config']['path'])
        with source.open('rb') as handle:
            size=source.stat().st_size;header=capture._mer_header(handle,size)
            capture._check_header_points(header['points'],table,True)
            seq=capture._count_lines(handle,header['data_start'],last['byte_end'])
            handle.seek(last['byte_end']);tail=handle.read()
        assert not tail or tail.endswith(b'\n'),'Finalized MER has an incomplete row'
        counters={int(k):v for k,v in last['records_cum_by_dcp'].items()}
        extra,_=capture.parse_mer_rows(tail,header['columns'],seq,set(counters),counters)
        all_rows=[v for bundle in bundles.values() for v in bundle.mer_rows]+extra
        for event in all_rows:
            if event.ordinal is None:continue
            old=by_ordinal[event.dcp].get(event.ordinal)
            assert old is None or old==event,'Conflicting MER identity'
            by_ordinal[event.dcp][event.ordinal]=event
        for sec,bundle in bundles.items():
            obs=bundle.obs
            rows,_=oc.read_detector_csv(obs['detector_config']['path'],obs['detector_config']['sha256'])
            oc.validate_raw(obs,rows,expected_simres=10);check_rule_crosscheck(obs,rows)
            if sec==2250:
                initial={v[0]:v for v in bundle.frame_end['vehicles']}
                if common is None:common=initial
                else:assert initial==common,'Initial population differs'
                continue
            assigned=oc.assign_window(obs,bundle.mer_rows)
            terms=oc.evaluate_boundaries(obs,rows,bundle.frame_end,bundle.frame_start,bundle.err_rows)
            groups=defaultdict(list)
            for row in rows:
                if row.boundary_ref in ('source:FW_E','chain_end:FW_E') or (row.role=='off_entry' and
                    any(b['road']=='FW_E' and b['kind']=='offramp' and str(b['connector'])==row.ref for b in geo['boundaries'])):
                    groups[row.boundary_ref].append(row)
            for ref,detectors in groups.items():
                events=[]
                for r in detectors:
                    high=obs['detectors_cum'][str(r.dcp_no)];low=high-obs['detectors'][str(r.dcp_no)]
                    missing=[n for n in range(low+1,high+1) if n not in by_ordinal[r.dcp_no]]
                    assert not missing,(arm,sec,ref,'Unresolved finalized MER ordinals',missing)
                    selected=[by_ordinal[r.dcp_no][n] for n in range(low+1,high+1)]
                    present=assigned.entries[r.dcp_no]
                    assert all(event in selected for event in present)
                    assert len(selected)-len(present)==assigned.tails[r.dcp_no]
                    events.extend(selected)
                    if assigned.tails[r.dcp_no]:late_records.append(dict(arm=arm,time_sec=sec,boundary=ref,
                        dcp=r.dcp_no,resolved_tail=assigned.tails[r.dcp_no]))
                count=Counter(event.veh for event in events)
                assert sum(count.values())==terms[ref].vehs
                orientation=detectors[0].orientation
                before=set().union(*(oc.vehicles_in_segment(bundle.frame_start['vehicles'],r.segment,orientation) for r in detectors)) if orientation!='at' else set()
                after=set().union(*(oc.vehicles_in_segment(bundle.frame_end['vehicles'],r.segment,orientation) for r in detectors)) if orientation!='at' else set()
                removed=terms[ref].removed_vehicles
                if orientation=='up':
                    count.update(before);count.subtract(after);count.subtract(removed)
                elif orientation=='down':
                    count.update(after);count.subtract(before);count.update(removed)
                else:assert orientation=='at'
                assert min(count.values(),default=0)>=0,(arm,sec,ref,'Negative individual crossing')
                assert sum(count.values())==terms[ref].cross
                crossings[ref].update({k:v for k,v in count.items() if v})
            removed_ids.update(r['vehicle_id'] for r in oc.window_removals(bundle.err_rows,sec-150,sec) if int(r['link']) in chain)
        initial_east={no for no,v in initial.items() if v[1] in chain}
        ending_east={v[0] for v in bundle.frame_end['vehicles'] if v[1] in chain}
        def category(no):
            return 'initial_east' if no in initial_east else 'initial_elsewhere' if no in initial else 'post_cutoff_population'
        summary={}
        exit_refs=[ref for ref in crossings if ref=='chain_end:FW_E' or ref.startswith('off_entry:')]
        by_vehicle=defaultdict(list)
        for ref,counter in crossings.items():
            summary[ref]=dict(Counter({k:sum(n for no,n in counter.items() if category(no)==k)
                for k in ('initial_east','initial_elsewhere','post_cutoff_population')}))
            if ref in exit_refs:
                for no,n in counter.items():
                    if no in initial_east:by_vehicle[no].extend([ref]*n)
        expected=flow['cases'][arm]['roads']['FW_E']
        assert sum(crossings['chain_end:FW_E'].values())==expected['actual_terminal']
        assert sum(crossings['source:FW_E'].values())==expected['actual_source']
        for ref in exit_refs:
            if ref.startswith('off_entry:'):
                assert sum(crossings[ref].values())==flow['cases'][arm]['offramps'][ref.split(':')[1]]['actual']['entry']
        represented=set(by_vehicle)|ending_east|removed_ids
        unknown=initial_east-represented
        assert not unknown,(arm,'Unclassified initial east vehicle',sorted(unknown))
        overlap=(set(by_vehicle)&ending_east)|{no for no,exits in by_vehicle.items() if len(exits)>1}
        cases[arm]=dict(initial_east_vehicles=len(initial_east),crossings_by_population=summary,
            final_east_by_population=dict(Counter(category(no) for no in ending_east)),
            initial_exit_by_vehicle=dict(by_vehicle),initial_remaining=sorted(initial_east&ending_east),
            removed_initial=sorted(initial_east&removed_ids),multiple_exit_or_return_initial=sorted(overlap))
    comparisons={}
    for baseline,arm in (('nc','rm'),('nc','vsl'),('rm','both')):
        a=cases[baseline];b=cases[arm]
        assert not a['multiple_exit_or_return_initial'] and not b['multiple_exit_or_return_initial']
        dest=lambda row,no:row['initial_exit_by_vehicle'].get(no,['remaining' if no in row['initial_remaining'] else 'removed'])[0]
        ids={no for no,v in common.items() if v[1] in chain}
        transitions=Counter((dest(a,no),dest(b,no)) for no in ids)
        delta={ref:{k:b['crossings_by_population'][ref][k]-value for k,value in rows.items()}
            for ref,rows in a['crossings_by_population'].items()}
        comparisons[arm+' minus '+baseline]=dict(boundary_delta_by_population=delta,
            initial_destination_transitions=[dict(baseline=k[0],candidate=k[1],vehicles=v) for k,v in sorted(transitions.items())])
    assert all(sha(Path(p))==h for p,h in pins.items())
    result=dict(status='COMPLETE_NATIVE_COHORT_BOUNDARY_DIAGNOSIS',arms=cases,comparisons=comparisons,resolved_late_mer=late_records,
        input_sha256=pins,new_forecasts=0,new_native=0,fzp_rescans=0,fit=0,
        limitations=['Initial population membership is exact; post-cutoff vehicle IDs are not matched across arms.',
            'Native interval boundary counts use MER plus detector-offset inventory/removal identities.',
            'Late MER identities are filled from later hash-verified chunks and finalized-file bytes, by native entry ordinal; original observation bundles are not changed.',
            'No exact crossing time or cohort TTT is inferred from 150s frames.',
            'Common initial vehicles remain affected by later traffic; this is not an isolated causal capacity estimate.',
            'Diagnostic only; no future observation becomes a plant input.'])
    (D/'cohort_assessment.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],comparisons=comparisons)))


if __name__=='__main__':
    if sys.argv[1:]==['--self-test']:self_test()
    elif sys.argv[1:]==['--flow']:flow_assessment()
    elif sys.argv[1:]==['--cohort']:cohort_assessment()
    else:
        assert not sys.argv[1:]
        main()
