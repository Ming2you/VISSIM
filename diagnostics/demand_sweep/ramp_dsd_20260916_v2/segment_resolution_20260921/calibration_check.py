"""Post-selection evidence; does not launch or select calibration candidates."""
import json
from pathlib import Path
import calibrate as c
from prepare import table, save

B=c.B;O=c.O;ROOT=c.ROOT;K=B.parent/'cohort_dynamics_20260920'

def main():
    selected=c.load(O/'local_selected.json')
    name='local_selected_actions' if 'regions' in selected['parameters'] else 'selected_actions'
    pred=c.load(O/name/'refined_guard1_none.json');old=c.load(B/'refined_guard1_none.json')
    # Frozen NC fit candidate and subsequently executed NC must be identical.
    assert pred==c.load(O/selected['name']/'refined_guard1_none.json')
    assert c.load(O/'v2_t12_n35/refined_guard1_none.json')==old
    metrics=[]
    for label,parents in [('F10643_10681',[8,9]),('D10481_10490_10484',[12,13,14]),('all_calibration_cells',c.TARGET)]:
        cells=[i for i,p in enumerate(c.PARENTS) if p in parents]
        for period,lo,hi in [('training',0,10),('late_temporal_check',10,15)]:
            for version,p in [('before',old),('selected',pred)]:
                metrics.append(dict(region=label,period=period,version=version,**c.score(p,lo,hi,cells)))
    table(O/'state_metrics.csv',metrics)
    local=[]
    for i,parent in enumerate(c.PARENTS):
        if parent not in c.TARGET:continue
        cell=next(x for x in c.G['cells'] if x['road']=='FW_E' and x['cell']==i)
        a=c.score(old,10,15,[i]);z=c.score(pred,10,15,[i])
        local.append(dict(cell=i,parent_cell=parent,start_m=cell['start_m'],end_m=cell['end_m'],
            before_speed_rmse=a['speed_rmse_kmh'],selected_speed_rmse=z['speed_rmse_kmh'],
            before_q_rmse=a['boundary_q_rmse_vph'],selected_q_rmse=z['boundary_q_rmse_vph'],
            before_n_rmse=a['group_n_rmse_veh'],selected_n_rmse=z['group_n_rmse_veh']))
    table(O/'late_local_errors.csv',local)
    result=c.load(K/('segment_resolution_20260921_cal_'+name)/'result.json')
    before=c.load(K/'segment_resolution_20260921_refined_guard1/result.json')
    # Previously completed actual component residence from the same2400-2850
    # experiment. Kept out of both NC-only selection protocols.
    actual_path=B.parent/'response_chain_20260921/qualification.json'
    actual_evidence=c.load(actual_path)['gains']
    actual={arm:r['actual']['total'] for arm,r in actual_evidence.items()}
    gains=[dict(arm=a,actual_delta_ttt_veh_h=actual[a],before_delta_ttt_veh_h=before['deltas'][a]['total'],
        selected_delta_ttt_veh_h=result['deltas'][a]['total'],
        selected_mainline=result['deltas'][a]['mainline'],
        selected_on=result['deltas'][a]['on'],selected_off=result['deltas'][a]['off']) for a in actual]
    table(O/'gain_check.csv',gains)
    numerical=[];west_exact=[]
    for arm in ('none','rm_ramp','vsl','both'):
        p=c.load(O/name/f'refined_guard1_{arm}.json');base=c.load(B/f'refined_guard1_{arm}.json')
        check=c.screen(p);assert check['passed'];numerical.append(dict(arm=arm,**check))
        for key in ('cells','flows'):
            assert [r for r in p[key] if r['road']=='FW_W']==[r for r in base[key] if r['road']=='FW_W']
        west_exact.append(arm)
    pin_checks=0
    runner_sources=[B/'run.py',O/'run_round1.py.txt',O/'run.py_float_before.txt']
    completed=0;seconds=0.
    for receipt_path in O.glob('*/refined_guard1_receipt.json'):
        receipt=c.load(receipt_path);assert any(c.sha(p)==receipt['runner_sha256'] for p in runner_sources)
        completed+=receipt['forecasts'];seconds+=sum(receipt['seconds'])
        protocol=c.load(K/('segment_resolution_20260921_cal_'+receipt['fit']['name'])/'protocol.json')
        for source,pin in protocol['source_pins'].items():
            assert c.sha(ROOT/source)==pin;pin_checks+=1
    for protocol_file,aliases in [(O/'protocol.json',{'calibrate.py':O/'calibrate_round1.py.txt','run.py':O/'run_round1.py.txt'}),
                                  (O/'local_protocol.json',{})]:
        for source,pin in c.load(protocol_file)['source_pins'].items():
            p=ROOT/source
            if c.sha(p)!=pin:p=aliases[p.name]
            assert c.sha(p)==pin;pin_checks+=1
    train_before=c.score(old);train_after=c.score(pred)
    late_before=c.score(old,10,15);late_after=c.score(pred,10,15)
    invariant=c.load(B/'validation.json')
    assert invariant['all_ports']==16 and invariant['max_ports_per_cell']==1
    candidate_records=c.load(O/'candidates.json')+c.load(O/'local_candidates.json')[1:]
    outside=[i for i,p in enumerate(c.PARENTS) if p not in c.TARGET and i!=30]
    out_before=c.score(old,10,15,outside);out_after=c.score(pred,10,15,outside)
    summary=dict(status='NC_ONLY_LOCAL_FIT_DONE_GAIN_NOT_QUALIFIED',selected=selected['parameters'],
        training_before=train_before,training_after=train_after,late_before=late_before,late_after=late_after,
        untouched_cell_late_before=out_before,untouched_cell_late_after=out_after,
        gains=gains,numerical=numerical,west_forecasts_exact=west_exact,baseline_hook_full_json_exact=True,
        total_completed_forecasts=completed,calibration_candidates=len(candidate_records),
        invalid_candidates=[r['name'] for r in candidate_records if not r['numerics']['passed']],
        initial_float_mismatch_forecasts_preserved=2,total_forecast_seconds=seconds,source_pins_verified=pin_checks,
        new_native_runs=0,production_adopted=False,fresh_seed_or_initial_state_validation=False,
        fit_only_nc_2400_2700=True,first_selection_frozen_before_action_runs=True,
        record_step_default_s=5,diagnostic_internal_step_s=1,horizon_s=450,
        scope='East mainline plus four on/four off connectors; not complete Omega or closed-loop improvement.',
        observation_proof=c.load(O/'observation_proof.json'),
        artifacts={str(p.relative_to(ROOT)):c.sha(p) for p in [Path(__file__),actual_path,O/'state_metrics.csv',O/'gain_check.csv',O/'local_selected.json',O/'protocol.json',O/'local_protocol.json',O/'observed_none.npz']})
    save(O/'validation.json',summary)
    print(json.dumps({k:summary[k] for k in ('status','training_before','training_after','late_before','late_after','gains','total_completed_forecasts','source_pins_verified')},indent=2))

if __name__=='__main__':main()
