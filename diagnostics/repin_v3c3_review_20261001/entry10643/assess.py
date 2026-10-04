import copy
import gzip
import hashlib
import json
import math
from pathlib import Path
from evaluation.controllers import obs150_contract as oc, offramp_routing as routing

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
pins={}
def read(path):
    raw=path.read_bytes();pins[str(path)]=hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if path.suffix=='.gz' else raw)

def main():
    assert not (HERE/'assessment.json').exists()
    native=read(HERE/'native_cohorts.json');runtime=native['route_runtime']
    p=I/'closedloop_recorded2700_select_check_trace10681_entry10643'
    b=I/'closedloop_recorded2700_select_check_trace10681_retained47_v2'
    summary=read(p/'summary.json');oldsummary=read(b/'summary.json')
    lhs=copy.deepcopy(summary);rhs=copy.deepcopy(oldsummary)
    wall=0.
    for key,row in lhs['results'].items():
        wall+=row.pop('wall_sec');rhs['results'][key].pop('wall_sec')
    assert lhs==rhs,'Observer changed existing forecast result'
    metadata=read(I/'closedloop_recorded2700_native_selected_sc1001_corrected47/analysis/ramp_response_audit.json')
    dets,digest=oc.read_detector_csv(I/'selected/obs150/obs150_detectors_v2.csv')
    groups=oc.group_boundaries(dets);cases={}
    for arm,key in [('hold','held_actual'),('selected','selected')]:
        trace=read(p/(key+'_RM_C10681_trace.json.gz'));oldtrace=read(b/(key+'_RM_C10681_trace.json.gz'))
        check=copy.deepcopy(trace)
        check['offramp_network_diagnostics']['route_runtime']=oldtrace['offramp_network_diagnostics']['route_runtime']
        check['offramp_network_diagnostics']['route_states']=oldtrace['offramp_network_diagnostics']['route_states']
        assert check==oldtrace,'Observer changed any pre-existing response trace'
        actual_runtime=trace['offramp_network_diagnostics']['route_runtime']
        assert actual_runtime==runtime,'Independently compiled route contract differs'
        snapshots=trace['offramp_network_diagnostics']['route_states']
        assert len(snapshots)==4
        raws={}
        for name,h in metadata['input_sha256'].items():
            path=Path(name)
            if arm not in path.parts:continue
            raw=read(path);assert pins[str(path)]==h;raws[int(raw['sim_sec'])]=raw
        frames={t:read(Path(raw['lane_plant_observation']['directory'])/f'frame_{t:06d}.json') for t,raw in raws.items()}
        initial_ids={v[0] for v in frames[2700]['vehicles'] if str(v[1]) in runtime['physical']}
        source_events=[];source_tails=[]
        for t in (2850,3000,3150):
            bundle=oc.load_bundle(raws[t]);window=oc.assign_window(bundle.obs,bundle.mer_rows)
            for det in groups['source:FW_E']:
                if window.tails[det.dcp_no]:
                    source_tails.append(dict(end_sec=t,detector=det.dcp_no,count=window.tails[det.dcp_no]))
                source_events.extend(dict(vehicle=e.veh,time_sec=e.t_entry) for e in window.entries[det.dcp_no])
        assert len({e['vehicle'] for e in source_events})==len(source_events)
        native_exit=native['cases'][arm]['witnesses']
        new_exits=[e for e in native_exit if e['group']=='not_in_initial_modelled_mainline']
        source_ids={e['vehicle'] for e in source_events}
        assert all(e['vehicle'] in source_ids for e in new_exits),'New exit cohort lacks physical upstream source event'
        uncertain_end=[];known_end=[]
        for v in frames[3150]['vehicles']:
            if v[0] in initial_ids or str(v[1]) not in runtime['physical']:continue
            road,pos,cell=routing._position(runtime,v[1],v[3])
            if road!='FW_E' or pos>runtime['branches']['10643']['source_chain_m']:continue
            if v[6] is None:
                uncertain_end.append(dict(vehicle=v[0],chain_m=pos,cell=cell));continue
            selected=runtime['routes'][f'{int(v[6])}:{int(v[7])}']
            if selected['target']=='10643':known_end.append(dict(vehicle=v[0],cell=cell,chain_m=pos,source_seen=v[0] in source_ids))
        missing_source_witnesses=[r for r in known_end if not r['source_seen'] and r['chain_m']>=40.]
        assert len(missing_source_witnesses)<=sum(r['count'] for r in source_tails)
        # Generations inferred from entry-station + current [0,40m) storage,
        # excluding IDs already in the initial mainline. No removals presumed.
        before_station=[v[0] for v in frames[3150]['vehicles'] if v[0] not in initial_ids and v[1]==74 and v[3]<40]
        new_source=[e for e in source_events if e['vehicle'] not in initial_ids]
        generated_lower_bound=len(new_source)+len(set(before_station)-{e['vehicle'] for e in new_source})
        target_observed=len(new_exits)+len(known_end)
        probability=runtime['inputs']['FW_E']['weights']['10643']
        snapshot_decomposition=[]
        for snap,ports in zip(snapshots,trace['offramp_network_diagnostics']['states']):
            inv=snap['inventory'];stock={}
            for row in inv['cells']['FW_E']:
                for label,n in row.items():
                    if label.endswith('|10643'):stock[label]=stock.get(label,0.)+n
            known=stock.get('observed_route:1130:1|route:1130:1|10643',0.)
            uncertain=stock.get('observed_null|route:1130:1|10643',0.)
            future=stock.get('expected_input:1098|route:1130:1|10643',0.)
            initial_exit=(35-known)+(1-uncertain)
            future_exit=ports['ports']['10643']['admitted']-initial_exit
            snapshot_decomposition.append(dict(time_sec=snap['time_sec'],initial_known_exited=35-known,
                initial_uncertain_exited=1-uncertain,future_exited=future_exit,future_retained=future,
                future_generated=future+future_exit,origin_class_stock=inv['origins']['FW_E']))
        final=snapshot_decomposition[-1]
        predicted_generated=summary['results'][key]['control_area']['flow_counts']['origin:FW_E->freeway:FW_E']
        assert abs(final['future_generated']-predicted_generated*probability)<1e-7
        # Algebraic decomposition; realized mix is diagnostic, never substituted
        # into autonomous forecasts or interpreted as a new constant route ratio.
        target_count_difference=target_observed-final['future_generated']
        remaining_difference=len(known_end)-final['future_retained']
        exit_difference=len(new_exits)-final['future_exited']
        assert abs(exit_difference-(target_count_difference-remaining_difference))<1e-7
        cases[arm]=dict(native_source_crossings_recorded=len(source_events),new_source_crossings=len(new_source),
            source_tails=source_tails,missing_source_witnesses=missing_source_witnesses,
            new_source_generated_lower_bound=generated_lower_bound,new_source_before_station=before_station,
            native_new_target_exited=len(new_exits),native_new_target_retained=known_end,
            native_new_unknown_upstream=uncertain_end,native_new_target_observed=target_observed,
            model_source_generated=predicted_generated,model_target_probability=probability,
            model_target_generated=final['future_generated'],model_new_target_exited=final['future_exited'],
            model_new_target_retained=final['future_retained'],model_snapshots=snapshot_decomposition,
            decomposition=dict(target_population_difference=target_count_difference,
                retained_difference=remaining_difference,exit_difference=exit_difference),
            all_new_exit_ids_verified_at_source=True)
        print(arm,{k:v for k,v in cases[arm].items() if k not in ('model_snapshots','native_new_target_retained','native_new_unknown_upstream')})
    out=dict(status='ENTRY_SHORTFALL_DOMINATED_BY_FUTURE_COHORT_NOT_INITIAL_ROUTE_LOSS',
        cases=cases,source_pins=pins,forecasts=2,wall_sec=wall,existing_results_exact=True,existing_trace_exact=True,
        new_native=0,new_fzp_scan=0,fit=0,goal_complete=False,
        limitations=['Future realized destination mix is diagnostic only, not a forecast input or calibrated turn ratio.',
          'Native generation is a station/storage lower bound until upstream removals and unobserved destinations are resolved.',
          'A single realized seed route fraction does not justify changing the configured route probability.',
          'Aggregate retained-mass differences do not uniquely identify travel delay; timing and destination composition may both contribute.'])
    (HERE/'assessment.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('EXACT_TWO_FORECASTS',wall)

if __name__=='__main__':main()
