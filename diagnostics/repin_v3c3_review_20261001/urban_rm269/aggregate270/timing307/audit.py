"""Closed head-time and area-boundary audit. No new prediction or future input."""
from pathlib import Path
from collections import Counter
import gzip,hashlib,json,pickle
from evaluation.controllers import obs150_contract as oc

HERE=Path(__file__).resolve().parent;A=HERE.parent;H=A.parent;ROOT=HERE.parents[4]
NATIVE=Path('E:/VISSIM_analysis/20261010_urbanrm269_cityonly289')
MODEL=Path('E:/VISSIM_analysis/20261010_sc12_initial306/forecast2400_v2')
RUNS={'hold':Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold/decisions_sdmpc31_g_2400_hold_s29'),
      'city':Path('E:/VISSIM_runs/20261010_urbanrm269_cityonly289_s29/selected/decisions_sdmpc31_g_2400_selected_s29')}
GROUPS={'SC6':dict(link=1210018302,movements=['SC6_S_SC12_to_N_SC103','SC6_S_SC12_to_E_SC104']),
        'SC101':dict(link=1220011503,movements=['SC101_S_SC1_to_N_SC2005'])}
PINS={}
def pin(p):
    p=Path(p);b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return b
def read(p):return json.loads(pin(p))
def stats(rows,tails):
    # Every missing MER tail belongs to (end-1,end], per validated obs150 contract.
    known=-sum((2850-t)/3600 for t in rows)
    lower=known-sum(n*(2850-(end-1))/3600 for end,n in tails)
    upper=known-sum(n*(2850-end)/3600 for end,n in tails)
    return dict(count=len(rows)+sum(n for _,n in tails),known_count=len(rows),tails=tails,
                head_time_cost_lower=lower,head_time_cost_upper=upper,
                events=sorted(rows),count150=[sum(a<t<=a+150 for t in rows)+sum(n for end,n in tails if end==a+150) for a in (2400,2550,2700)])
def main():
    assert not (HERE/'assessment.json').exists()
    prior=read(A/'sc12_initial306/completion.json')
    assert prior['owned_forecast_process_exited'] and not prior['goal_complete']
    proof=read(NATIVE/'cached_summary.json')
    assert proof['paired_prefix_exact'] and proof['common_start_vehicle_records_exact']
    assert all(x['native_execution_passed'] for x in proof['arms'].values())
    assert read(NATIVE/'runtime_closure.json')['all_owned_processes_closed']
    old=read(A/'cityresponse290/assessment.json');summary=read(MODEL/'summary.json')
    assert summary['status']=='complete' and summary['canonical_state_error_before_projection']==0
    for p,h in summary['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    for p in ('upstream_worklog/02_urban_b2/diag_c3_r2/U7.md','upstream_worklog/02_urban_b2/diag_c3/C3_DIAGNOSIS.md'):
        pin(H.parent/p)
    cfg,_,_=pickle.loads(pin(A/'citysplit287/forecast2400/initial.pickle'))
    native={};model={};curves={};resources={}
    for arm,folder in RUNS.items():
        ev={k:[] for k in GROUPS};tails={k:[] for k in GROUPS}
        for end in (2550,2700,2850):
            raw=read(folder/f'state_{end:06}.json');bundle=oc.load_bundle(raw)
            detectors,_=oc.read_detector_csv(bundle.obs['detector_config']['path'],bundle.obs['detector_config']['sha256'])
            pin(bundle.obs['detector_config']['path']);pin(folder/bundle.obs['mer']['chunk'])
            w=oc.assign_window(bundle.obs,bundle.mer_rows)
            for k,spec in GROUPS.items():
                sg=set(cfg.network.signal_actuation_contract['nodes'][k]['phase_signal_groups']['p1'])
                wanted=[d for d in detectors if d.role=='head' and d.link==spec['link'] and oc.parse_head_ref(d.ref)[2] in sg]
                assert wanted,(k,sg)
                ev[k].extend(r.t_entry for d in wanted for r in w.entries[d.dcp_no])
                tails[k].append((end,sum(w.tails[d.dcp_no] for d in wanted)))
        native[arm]={k:stats(ev[k],tails[k]) for k in GROUPS}
        response=json.loads(gzip.decompress(pin(MODEL/(arm+'.response.json.gz'))))
        model[arm]={};curves[arm]={};resources[arm]={}
        for k,spec in GROUPS.items():
            moves={'movement:'+m for m in spec['movements']}
            rows=[r for r in response['transfers'] if r['source'] in moves and r['source']!=r['target']]
            model[arm][k]=dict(count=sum(r['vehicles'] for r in rows),
              head_time_cost_lower=-sum(r['vehicles']*(2850-r['start_sec'])/3600 for r in rows),
              head_time_cost_upper=-sum(r['vehicles']*(2850-r['end_sec'])/3600 for r in rows),
              count150=[sum(r['vehicles'] for r in rows if a<=r['start_sec']<a+150) for a in (2400,2550,2700)])
            expected=[r['actual'] for r in old['head_counts'][arm] if r['group']==k+'_S' and r['phase']=='p1']
            assert native[arm][k]['count150']==expected,(arm,k,native[arm][k],expected)
            curves[arm][k]=[dict(end=end,native_known=sum(t<=end for t in ev[k]),
                native_tail_cumulative=sum(n for e,n in tails[k] if e<=end),
                model=sum(r['vehicles'] for r in rows if r['end_sec']<=end)) for end in range(2410,2851,10)]
            resources[arm][k]=[r for r in response['resource_allocations'] if spec['link'].__str__() in r['resource']]
    delta={}
    for k in GROUPS:
        delta[k]={}
        for label,values in (('native',native),('model',model)):
            h,c=values['hold'][k],values['city'][k]
            delta[k][label]=dict(count=c['count']-h['count'],
                time_cost_lower=c['head_time_cost_lower']-h['head_time_cost_upper'],
                time_cost_upper=c['head_time_cost_upper']-h['head_time_cost_lower'])
    boundary=old['native_boundary']['delta'];total=sum(x['cost'] for x in boundary.values())
    assert abs(total-proof['delta_TTT_veh_h'])<1e-7
    diagnostic_no_admission_term=total-sum(boundary[k]['cost'] for k in
        ('observed_entry_events','appeared_inside_events','reappeared_inside_events'))
    new_model_delta=summary['results']['city']['omega_ttt_veh_h']-summary['results']['hold']['omega_ttt_veh_h']
    modeled_admission_delta=sum(sum(v[k] for k in ('entry_cost','generation_cost')) for v in
        read(A/'sc12_initial306/comparison.json')['boundary_routes']['new'].values())
    result=dict(status='complete_closed_timing_admission_diagnosis',goal_complete=False,
        previous_goal_turn='progress306_current_route_fix_and_two450_predictions',native=native,model=model,head_deltas=delta,
        cumulative10=curves,model_resource_rows=resources,native_boundary=boundary,
        omega_delta=dict(native=total,model=new_model_delta,
            native_admission_accounting_term=total-diagnostic_no_admission_term,
            native_remaining_accounting_term=diagnostic_no_admission_term,model_admission_term=modeled_admission_delta),
        source_pins=PINS,forecasts=0,new_native=0,fzp_scans=0,fits=0,
        limits=['Removing an accounting term is not a common-demand counterfactual or controller benefit estimate.',
          'Head crossings and model connector departures differ spatially; time bounds cover timestamp resolution only.',
          'Reported admission differences are measured outcomes. Their causal share is not identified.',
          'Same initial state and offered demand do not imply identical realized admissions or random-number paths.',
          'No future measured admission/head values enter any prediction.'])
    pin(Path(__file__))
    (HERE/'assessment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print('HEAD_DELTAS',delta);print('OMEGA',result['omega_delta'])
if __name__=='__main__':main()
