"""Compare the completed two forecasts to cached residence and native observations."""
import bisect
import hashlib
import json
from pathlib import Path
from evaluation.controllers import lane_plant_runtime, obs150_observation

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
P=I/'closedloop_recorded2700_lever450_s67_service66_20261003_actuator_equivalent'
RUNS=Path('D:/VISSIM_runs/20261003_s67_vsl_observation2700')
pins={}
def read(path):
    data=path.read_bytes();pins[str(path)]=hashlib.sha256(data).hexdigest()
    return json.loads(data)
def save(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')

def main(*, replication73=False):
    global HERE,P,RUNS
    result_name='response_assessment76.json'
    snapshot_name='snapshot_errors76.json'
    seed=67
    if replication73:
        HERE=HERE.parent/'replication_s73_95'
        P=I/'closedloop_recorded2700_lever450_s73_replication95'
        RUNS=Path('D:/VISSIM_runs/20261003_s73_vsl_replication95')
        result_name='response_assessment95.json';snapshot_name='snapshot_errors95.json';seed=73
        assert read(HERE/'postprocess_status.json')['phase']=='complete_pending_assessment'
        assert read(HERE/'postprocess_plan.json')['independent_seed']==73
    else:
        assert read(HERE/'prediction_run76_actuator_equivalent.json')['stage']=='complete'
    assert not (HERE/result_name).exists()
    native=read(HERE/'analysis/summary.json'); pred=read(P/'summary.json')
    assert pred['optimizer_iterations']==0 and not pred['future_observation_inputs']
    if replication73:
        assert native['counterfactual_valid'] and native['paired_prefix_exact']
        assert native['common_start_vehicle_records_exact'] and native['replication_seed']==73
        assert not native['matched_prior_run_claimed']
        assert pred['replay_pair']['seed']==73 and pred['replay_pair']['observation_cutoff_sec']==2700
        assert pred['replay_pair']['future_states_used'] is False
    else:
        assert pred['replay_pair']['comparison_scope']['paired_native_effect_valid']
    tuning=read(HERE.parent/'rm47_service66_response/candidate_config.json')
    context=lane_plant_runtime.load_sources(tuning['freeway']['lane_plant'])
    g=read(I/'selected/port_gain/geometry.json')
    assert g['network']['sha256']=='64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
    chains={road:{int(v['link']):v for v in chain} for road,chain in g['chains'].items()}
    ramps={r['connector'] for r in g['boundaries'] if r['kind']=='ramp'}
    assert len(ramps)==8
    rows={};snapshot_rows=[]
    for arm in ('release','release_vsl90'):
        result=pred['results'][arm+'_actual']
        metrics=read(HERE/f'analysis/{arm}/area_metrics.json')
        grouped=dict(FW_E=0.,FW_W=0.,ramps=0.,other_omega=0.)
        for link,data in metrics['physical_link_residence'].items():
            if not data['inside']:continue
            key=next((road for road,links in chains.items() if int(link) in links),None)
            key=key or ('ramps' if int(link) in ramps else 'other_omega')
            grouped[key]+=data['ttt_veh_h']
        assert abs(sum(grouped.values())-metrics['ttt_veh_h'])<1e-7
        modeled={road:result['cost_by_stock']['freeway:'+road] for road in chains}
        modeled['ramps']=sum(value for key,value in result['cost_by_stock'].items() if key.startswith('ramp:'))
        modeled['other_omega']=result['ttt_omega_veh_h']-sum(modeled.values())
        totals={};sources={r:0 for r in chains};stocks={}
        folder=RUNS/arm/f'decisions_sdmpc31_g_2700_{arm}_s{seed}'
        for index,sec in enumerate((2700,2850,3000,3150)):
            raw=read(folder/f'state_{sec:06d}.json')
            assert raw['sim_sec']==sec and raw['vehicle_records']['complete']
            observed=raw['vehicle_records']['records']
            stocks[sec]={r:sum(int(v['link_no']) in links for v in observed) for r,links in chains.items()}
            # Snapshot speed/stock evidence is evaluation only, never forecast input.
            road='FW_E';bins=[[] for _ in range(31)]
            cells=sorted((c for c in g['cells'] if c['road']==road),key=lambda c:c['cell'])
            assert len(cells)==31
            ends=[c['end_m'] for c in cells]
            for vehicle in observed:
                link=int(vehicle['link_no'])
                if link in chains[road]:
                    pos=chains[road][link]['offset_m']+float(vehicle['position_m'])
                    cell=min(bisect.bisect_right(ends,pos),30)
                    bins[cell].append(float(vehicle['speed_kph']))
            physical=result['physical_cell_states'][index]
            assert physical['time_sec']==sec
            for cell,values in enumerate(bins):
                snapshot_rows.append(dict(arm=arm,time_sec=sec,cell=cell,actual_stock=len(values),
                    actual_speed_kmh=sum(values)/len(values) if values else None,
                    predicted_speed_kmh=physical['speed_kmh'][road][cell]))
            if sec==2700:continue
            derived=obs150_observation.derive(raw,context['obs150'])
            assert derived['window']==dict(start_s=sec-150,end_s=sec)
            for ref,value in derived['boundaries'].items():
                if ref.startswith(('source:','chain_end:','off_entry:','x10643_exit:')):
                    totals[ref]=totals.get(ref,0)+value['cross']
            for road in sources:sources[road]+=derived['source_boundary'][road]['admitted_window']
        flow=result['control_area']['flow_counts']
        mainline={}
        ramp_audit=read(P/'ramp_response_audit.json')['arms'][arm]
        for road in chains:
            ports=[b for b in g['boundaries'] if b['road']==road]
            ramp_ids=[b['id'] for b in ports if b['kind']=='ramp']
            off_ids=[b['connector'] for b in ports if b['kind']=='offramp']
            assert len(ramp_ids)==len(off_ids)==4
            actual=dict(source=totals['source:'+road],admitted_source_counter=sources[road],
                merge=sum(ramp_audit[r]['actual']['merge'] for r in ramp_ids),
                off=sum(totals['off_entry:'+str(c)] for c in off_ids),terminal=totals['chain_end:'+road],
                initial_stock=stocks[2700][road],final_stock=stocks[3150][road])
            actual['unexplained_balance_veh']=actual['initial_stock']+actual['source']+actual['merge']-actual['off']-actual['terminal']-actual['final_stock']
            modeled_flow=dict(source=flow['origin:'+road+'->freeway:'+road],
                merge=sum(result['ramps'][r]['merge'] for r in ramp_ids),
                off=sum(v for k,v in flow.items() if k.startswith('freeway:'+road+'->storage:')),
                terminal=flow['freeway:'+road+'->external:terminal:'+road],
                initial_stock=stocks[2700][road],
                final_stock=next(x['physical_stock'] for x in result['offramp_route_inventory_checks'] if x['time_sec']==3150 and x['road']==road))
            mainline[road]=dict(actual=actual,predicted=modeled_flow)
        rows[arm]=dict(native_full_run_components_veh_h=grouped,prediction450_components_veh_h=modeled,
                       mainline=mainline,native_boundaries450=totals)
    a,b=rows['release'],rows['release_vsl90']
    cost_delta={k:dict(actual=b['native_full_run_components_veh_h'][k]-a['native_full_run_components_veh_h'][k],
                      predicted=b['prediction450_components_veh_h'][k]-a['prediction450_components_veh_h'][k])
                for k in a['native_full_run_components_veh_h']}
    actual=native['delta_TTT_veh_h']
    modeled=pred['results']['release_vsl90_actual']['ttt_omega_veh_h']-pred['results']['release_actual']['ttt_omega_veh_h']
    assert abs(sum(x['actual'] for x in cost_delta.values())-actual)<1e-7
    response_gate=None
    model_consistency=None
    if replication73:
        model_consistency=dict(
            max_route_inventory_residual_veh=max(abs(check['max_cell_residual']) for result in pred['results'].values()
                for check in result['offramp_route_inventory_checks']),
            max_ramp_balance_residual_veh=max(abs(ramp['residual']) for result in pred['results'].values()
                for ramp in result['ramps'].values()),
            max_mainline_balance_residual_veh=max(abs(m['predicted']['initial_stock']+m['predicted']['source']+
                m['predicted']['merge']-m['predicted']['off']-m['predicted']['terminal']-m['predicted']['final_stock'])
                for row in rows.values() for m in row['mainline'].values()),
            max_TTT_partition_error_veh_h=max(abs(sum(result['cost_by_stock'].values())-result['ttt_omega_veh_h'])
                for result in pred['results'].values()))
        assert all(value<1e-7 for value in model_consistency.values()),model_consistency
        assert all(result['validation']['all_actuator_and_step_constraints_checked'] for result in pred['results'].values())
    status='MATERIAL_VSL_RESPONSE_UNDERPREDICTED_NOT_QUALIFIED'
    if replication73:
        planned=read(HERE/'plan.json')['acceptance']
        assert planned==dict(material_omega_veh_h=.5,material_sign_must_match=True,
            error_allowance='max(0.5 veh*h, 0.5*abs(actual delta))',rank_regret_max_veh_h=.5)
        material=abs(actual)>=planned['material_omega_veh_h']
        error=abs(modeled-actual);allowance=max(.5,.5*abs(actual))
        selected_vsl=modeled<0
        regret=(actual if selected_vsl else 0)-min(0.,actual)
        response_gate=dict(material=material,correct_sign=actual*modeled>0,
            absolute_error_veh_h=error,allowed_error_veh_h=allowance,
            selected=('release_vsl90' if selected_vsl else 'release'),
            native_best=('release_vsl90' if actual<0 else 'release'),regret_veh_h=regret,
            max_native_mainline_balance_veh=max(abs(m['actual']['unexplained_balance_veh'])
                for row in rows.values() for m in row['mainline'].values()))
        response_gate['passes']=material and response_gate['correct_sign'] and error<=allowance and regret<=.5
        response_gate['passes']=response_gate['passes'] and response_gate['max_native_mainline_balance_veh']<1e-7
        status=('SMALL_EFFECT_INCONCLUSIVE' if not material else 'MATERIAL_RESPONSE_PASS_NOT_FULL_QUALIFICATION'
                if response_gate['passes'] else 'MATERIAL_RESPONSE_FAIL_NOT_QUALIFIED')
    output=dict(status=status,
        contrast='Same RM release, VSL90 minus VSL110; autonomous450 from observed2700',
        actual_delta_omega_veh_h=actual,predicted_delta_omega_veh_h=modeled,
        predicted_fraction_of_native_effect=modeled/actual if abs(actual)>1e-12 else None,component_delta_veh_h=cost_delta,
        arms=rows,future_native_states='evaluation labels only, loaded after completed forecasts',
        paired_comparison_scope=pred['replay_pair'].get('comparison_scope',dict(scope='within_seed73_pair_only')),new_calibration=0,new_native=0,
        extra_fzp_metric_scans=0,forecasts=2,optimizer_iterations=0,
        limitations=['Native component levels are0..3150, model levels2700..3150. Only deltas cancel the exact common native prefix and are compared.',
                     '5s native residence includes held4.9s tail; model internal integration1s.',
                     'Normal exits include approved terminal inference; unresolved inside disappearances are excluded and separately reported.',
                     ('One new seed73 fixed-policy pair is not a full factorial, statistical robustness result or full controller qualification.' if replication73 else
                      'Two conditions at already-used seed67 are neither full factorial nor independent holdout.'),
                     'Source-admission changes and recovery are correlated effects, not a causal decomposition from these totals.',
                     'Snapshot speeds at150s intervals do not establish recovery onset/duration by themselves.'],
        input_sha256=pins)
    if replication73:
        output.update(response_gate=response_gate,model_consistency=model_consistency,
            normal_Omega_exit_delta=dict(actual=native['arms']['release_vsl90']['Omega_TTD_events']-native['arms']['release']['Omega_TTD_events'],
                predicted=pred['results']['release_vsl90_actual']['control_area']['ttd_veh']-pred['results']['release_actual']['control_area']['ttd_veh']),
            model_adopted=False,whole_goal_qualified=False,
            native_endpoint_deltas={key:native['arms']['release_vsl90'][key]-native['arms']['release'][key]
                for key in ('Omega_TTD_events','Omega_end_vehicles','native_removals','uninserted_at_end',
                    'unresolved_Omega_disappearances','native_uninserted_delay_veh_h','native_total_time_including_uninserted_veh_h')},
            native_endpoint_levels={arm:{key:native['arms'][arm][key] for key in
                ('Omega_TTD_events','Omega_end_vehicles','native_removals','unresolved_Omega_disappearances')}
                for arm in ('release','release_vsl90')},
            external_costs_are_diagnostics_only=True)
    save(HERE/snapshot_name,snapshot_rows)
    save(HERE/result_name,output)
    print(json.dumps({k:output[k] for k in ['status','actual_delta_omega_veh_h','predicted_delta_omega_veh_h','component_delta_veh_h']}))
    print(json.dumps({arm:v['mainline']['FW_E'] for arm,v in rows.items()}))

if __name__=='__main__':
    import sys
    assert sys.argv[1:] in ([],['--replication73'])
    main(replication73=sys.argv[1:]==['--replication73'])
