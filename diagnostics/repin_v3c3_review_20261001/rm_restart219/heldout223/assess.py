"""Saved seed47 response comparison; no fits, forecasts, COM or FZP."""
import gzip
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
INTEGRATION=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_bytes())
def sums(item):
    stocks=item['cost_by_stock']
    assert abs(math.fsum(stocks.values())-item['ttt_omega_veh_h'])<1e-7
    result={k:stocks['freeway:'+k] for k in ('FW_E','FW_W')}
    result['eight_ramps']=math.fsum(v for k,v in stocks.items() if k.startswith('ramp:'))
    result['other_Omega']=item['ttt_omega_veh_h']-math.fsum(result.values())
    return result

def main():
    from evaluation.controllers import obs150_contract as oc
    protocol=read(HERE/'protocol.json');pins={}
    for p,h in protocol['source_sha256'].items():assert sha(ROOT/p)==h,p
    for row in protocol['models'].values():assert sha(Path(row['config']))==row['sha256']
    assert sha(Path(protocol['STOP']['path']))==protocol['STOP']['sha256']
    old=ROOT/'diagnostics/repin_v3c3_review_20261001/corrected_s47_neighbors'
    native=read(old/'native_boundary_assessment.json')
    for row in native['input_sha256'].values():assert sha(Path(row['path']))==row['sha256']
    audit_path=INTEGRATION/'closedloop_recorded2700_native_selected_sc1001_corrected47/analysis/ramp_response_audit.json'
    audit=read(audit_path);pins[str(audit_path)]=sha(audit_path)
    models={};commands=None;initials=None
    for model, spec in protocol['models'].items():
        folder=INTEGRATION/('closedloop_recorded2700_select_check_trace10681_'+spec['label'])
        summary_path=folder/'summary.json';summary=read(summary_path);pins[str(summary_path)]=sha(summary_path)
        cases=summary['results'];assert set(cases)=={'held_actual','selected'}
        assert summary['duration_sec']==450 and summary['optimizer_iterations']==0 and not summary['native_started'] and not summary['future_observation_inputs']
        current_commands={k:v['commands'] for k,v in cases.items()}
        if commands is None:commands=current_commands
        else:assert commands==current_commands,'Evaluation models changed commands'
        per_case={}
        for case, item in cases.items():
            assert item['saved_state_stock_witness']['passed']
            if case=='held_actual':
                assert item['validation']['all_actuator_and_step_constraints_checked']
            else:
                binding=item['validation']
                assert binding['schema']=='joint-written-command-binding/v1'
                assert binding['prewrite_binding_passed'] and binding['written_command_binding_passed']
                for field in ('action_json','action_csv'):
                    assert sha(Path(binding[field]['path']))==binding[field]['sha256']
            assert item['max_resource_exceedance_veh']<1e-7
            native_case='hold' if case=='held_actual' else 'selected'
            ramp_errors={}
            for ramp,row in item['ramps'].items():
                actual=audit['arms'][native_case][ramp]['actual']
                assert abs(row['residual'])<1e-7
                assert abs(actual['initial_stock']+row['arrival']-row['merge']-row['final_stock'])<1e-7
                ramp_errors[ramp]={k:row[k]-actual[k] for k in ('arrival','merge','final_stock')}
            trace_path=folder/(case+'_RM_C10681_trace.json.gz')
            pins[str(trace_path)]=sha(trace_path)
            trace=json.loads(gzip.decompress(trace_path.read_bytes()))
            if initials is None:initials=trace['initial_stock']
            else:assert initials==trace['initial_stock']
            assert len(trace['lane_interval_receipts'])==450
            end=initials['connector_veh'];pre=initials['upstream_travelling_veh']+initials['head_ready_veh'];post=end-pre
            windows=[]
            for j,start in enumerate((2700,2850,3000)):
                transfers=[t for t in trace['transfers'] if start<=t['start_sec']<start+150]
                arrival=math.fsum(t['vehicles'] for t in transfers if t.get('target')=='ramp:RM_C10681')
                rec=[t['receipt'] for t in trace['lane_interval_receipts'] if start<=t['receipt']['start_sec']<start+150]
                assert len(rec)==150
                head=math.fsum(x['head_service_veh'] for x in rec);merge=math.fsum(x['accepted_merge_veh'] for x in rec)
                end+=arrival-merge;pre+=arrival-head;post+=head-merge
                assert min(end,pre,post)>-1e-7 and abs(end-pre-post)<1e-7
                predicted=dict(arrival=arrival,head=head,merge=merge,final_stock=end,prehead=pre,posthead=post)
                actual=audit['arms'][native_case]['RM_C10681']['actual']['windows'][j]
                lanes=[]
                for lane_index in (0,1):
                    lr=[x['lane_receipts'][lane_index] for x in rec]
                    lanes.append(dict(lane_index=lane_index,
                        head=math.fsum(x['head_service_veh'] for x in lr),
                        merge=math.fsum(x['accepted_merge_veh'] for x in lr),
                        receiving_budget=math.fsum(x['receiving_budget_veh'] for x in lr),
                        unused_receiving=math.fsum(x['unused_receiving_budget_veh'] for x in lr),
                        receiving_binding_seconds=sum(abs(x['accepted_merge_veh']-x['receiving_budget_veh'])<1e-8 for x in lr),
                        end_head_queue=lr[-1]['end']['head_ready_veh'],
                        end_merge_queue=lr[-1]['end']['merge_ready_veh']))
                assert abs(math.fsum(x['merge'] for x in lanes)-merge)<1e-7
                windows.append(dict(start_sec=start,predicted=predicted,actual=actual,model_lanes=lanes,
                    errors={k:predicted[k]-actual[k] for k in ('arrival','head','merge','final_stock')}))
            assert abs(end-item['ramps']['RM_C10681']['final_stock'])<1e-7
            per_case[case]=dict(wall_sec=item['wall_sec'],ttt=item['ttt_omega_veh_h'],tracked_outside=item['tracked_outside_residence_veh_h'],
                cost_groups=sums(item),ramps=item['ramps'],ramp_errors=ramp_errors,ramp10681_windows=windows)
        a,b=per_case['held_actual'],per_case['selected']
        delta=b['ttt']-a['ttt'];by_group={k:b['cost_groups'][k]-a['cost_groups'][k] for k in a['cost_groups']}
        models[model]=dict(cases=per_case,delta_omega=delta,
            delta_error=delta-native['actual_omega_delta_veh_h'],delta_by_group=by_group,
            delta_group_error={k:by_group[k]-v for k,v in native['actual_delta_veh_h'].items()},
            tracked_outside_delta=b['tracked_outside']-a['tracked_outside'],
            ramp_response={r:{k:b['ramps'][r][k]-a['ramps'][r][k] for k in ('arrival','merge','final_stock')} for r in a['ramps']})
    command_changes=[]
    for held,selected in zip(commands['held_actual'],commands['selected']):
        changed={field:[key for key in held[field] if held[field][key]!=selected[field][key]] for field in held}
        assert not changed['meters'] and not changed['vsl']
        assert changed['green_times'] and changed['offsets']
        command_changes.append(changed)
    coverage=[]
    prior=read(old/'arrival10681_native_paths.json')
    for path,digest in prior['input_sha256'].items():
        if not path.endswith('.json'):continue
        p=Path(path);assert sha(p)==digest;pins[path]=digest
        raw=read(p);bundle=oc.load_bundle(raw);rows=[v for v in bundle.frame_end['vehicles'] if v[1]==46]
        unknown=[v[0] for v in rows if v[3]>=16.47897 and (v[6]!=1125 or v[7] not in (1,2,3) or v[8]!='STATIC')]
        assert not unknown
        coverage.append(dict(path=path,sim_sec=raw['sim_sec'],vehicles=len(rows),
            routes=dict(Counter(str(v[6:9]) for v in rows)),unresolved_after_choice_ids=unknown))
    result=dict(status='COMPLETE_BOUNDED_HELDOUT_RESPONSE_NOT_GAIN_QUALIFICATION',seed=47,start_sec=2700,horizon_sec=450,
        forecasts=4,prediction_wall_sec=sum(c['wall_sec'] for m in models.values() for c in m['cases'].values()),
        fit=0,optimizer=0,new_native=0,FZP=0,same_commands=True,same_initial_ramp_inventory=True,
        actual_delta_omega=native['actual_omega_delta_veh_h'],actual_delta_by_group=native['actual_delta_veh_h'],
        outside_scope=native['outside_scope_separate'],models=models,route_coverage=coverage,input_sha256=pins,
        command_changes=command_changes,actual_changed_levers=['green_times','offsets'],meters_and_vsl_identical=True,
        limitations=['Verified command audit: only city green/offset change. All eight RM and VSL commands are identical in all three blocks. This is not an RM/VSL causal test.',
                    'Only observed route choice plus the existing kinematic ETA changed; no parameter fitting.',
                    'Native outside/uninserted and tracked model outside have different coverage.',
                    'This is one seed47 state, not full controller or all-condition gain qualification.'])
    (HERE/'assessment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],seconds=result['prediction_wall_sec'],actual_delta=result['actual_delta_omega'],models={k:{field:v[field] for field in ('delta_omega','delta_error','delta_by_group')} for k,v in models.items()})))

if __name__=='__main__':main()
