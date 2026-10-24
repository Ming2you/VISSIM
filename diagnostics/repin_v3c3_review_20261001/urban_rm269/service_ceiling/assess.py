"""Compare the bounded candidate with reused actual and model records."""
import gzip,hashlib,importlib.util,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
H=HERE.parent
ROOT=HERE.parents[3]
sys.path[:0]=[str(ROOT),str(H)]
from qualify_native2400 import validate_scope
loader=importlib.util.spec_from_file_location('head_reader',H/'sc12_source/audit.py')
a=importlib.util.module_from_spec(loader);loader.loader.exec_module(a)
a.LINKS={'SC6_S':1210018302,'SC101_S':1220011503}
read=a.read

def main():
    out=HERE/'comparison.json';assert not out.exists()
    validate_scope(read(H/'native2400_analysis/summary.json'),read(H/'native2400_analysis/observed_input_qualification.json'))
    for p,d in read(HERE/'plan.json')['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==d,p
    base=read(H/'native_beta/forecast2400_checked/summary.json')['results']
    candidate=read(HERE/'forecast2400/summary.json')['results']
    late=read(HERE/'forecast3300/summary.json')['results']['applied']
    clocks=read(H/'city_response/assessment.json')
    native=read(H/'native2400_assessment.json')
    for at in (2400,3300):
        assert read(HERE/f'forecast{at}/completion.json')['status']=='complete'
        s=read(HERE/f'forecast{at}/summary.json')
        assert s['forecasts']==(2 if at==2400 else 1)
        assert s['native_runs']==s['optimizer_calls']==0 and not s['future_observation_inputs']
    for r in (*candidate.values(),late):assert r['resource_max_exceedance']<1e-7 and r['writer_validated']
    for r in candidate.values():assert r['shared_constraints']['feasible'] and r['conservation_states']==4
    phases={'SC6_S':{'p1':['SC6_S_SC12_to_N_SC103','SC6_S_SC12_to_E_SC104'],'p2':['SC6_S_SC12_to_W_SC5']},
            'SC101_S':{'p1':['SC101_S_SC1_to_N_SC2005'],'p2':['SC101_S_SC1_to_W_SC1002']}}
    comparisons=[]
    for arm in ('hold','selected'):
        for group,groups in phases.items():
            for phase,ms in groups.items():
                obs=[r['phases'][group+'_'+phase]['native_head_veh'] for r in clocks['arms'][arm]]
                old=[r['phases'][group+'_'+phase]['model_head_veh'] for r in clocks['arms'][arm]]
                new=[sum(b['by_movement'][m] for m in ms) for b in candidate[arm]['local'][group]['bins']]
                comparisons.append(dict(arm=arm,group=group,phase=phase,actual=obs,previous=old,predicted=new,
                    previous_absolute_error=sum(abs(o-n) for o,n in zip(obs,old)),
                    absolute_error=sum(abs(o-n) for o,n in zip(obs,new))))
    physical,_=a.heads_and_entries(a.ORIGINAL,3450)
    prior=json.loads(gzip.decompress(a.pin(H/'native_beta/forecast3300/applied.response.json.gz')))
    later=[]
    for group,groups in phases.items():
        for phase,ms in groups.items():
            lanes=({1,2,3} if phase=='p1' else ({4} if group=='SC6_S' else {4,5}))
            obs=sum(row['crossings'] for row in physical[group]['rows'] if int(row['lane']) in lanes)
            old=sum(t['vehicles'] for t in prior['transfers'] if t['source'] in {'movement:'+m for m in ms})
            new=sum(late['local'][group]['bins'][0]['by_movement'][m] for m in ms)
            later.append(dict(group=group,phase=phase,actual=obs,previous=old,predicted=new,
                previous_absolute_error=abs(obs-old),absolute_error=abs(obs-new)))
    delta=lambda rs:rs['selected']['omega_ttt_veh_h']-rs['hold']['omega_ttt_veh_h']
    delta_fw=lambda rs:sum(rs['selected']['costs_by_stock'].get(k,0)-v for k,v in rs['hold']['costs_by_stock'].items() if k.startswith('freeway:'))
    actual=native['delta_omega_veh_h']['actual']
    result=dict(status='complete_bounded_service_diagnostic',forecasts_completed=3,
        tests_passed=7,new_native=0,new_optimizations=0,new_fitted_parameters=1,
        delta_definition='Same initial2400state joint city/RM selected-minus-held; unchangedOmega701,450s',
        delta_omega_veh_h=dict(actual=actual,previous=delta(base),predicted=delta(candidate),
            previous_error=delta(base)-actual,error=delta(candidate)-actual),
        delta_mainline_veh_h=dict(actual=native['delta_mainline_veh_h']['actual'],previous=delta_fw(base),predicted=delta_fw(candidate)),
        incremental_merge10681_veh=dict(actual=84,predicted=candidate['selected']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681']-candidate['hold']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681']),
        head_comparisons2400=comparisons,head_comparisons3300=later,
        combined_head_absolute_error=dict(previous=sum(r['previous_absolute_error'] for r in comparisons+later),
                                          predicted=sum(r['absolute_error'] for r in comparisons+later)),
        calibration_control_gate_passed=False,runtime_pair_launched=False,shared_caps_feasible=True,
        limitations=['Unused3300 is a same-seed state, not an independent seed.',
            'SC101 right branches before the through head and is excluded from head comparisons.',
            'Only SC101 straight-head startup-inclusive rate was estimated from two past windows. Current arrival/queue inputs are unchanged from native_beta.',
            'No new native isolated city/RM experiment. Model loss/gain decomposition is not native causal attribution.',
            'Do not treat diagnostic fixed-action forecast time as whole SDMPC decision wall time.'])
    for p in (Path(__file__),HERE/'plan.json',HERE/'assessment.json',HERE/'preflight.json',HERE/'candidate.py'):a.pin(p)
    result['service_candidate']=read(HERE/'forecast2400/candidate_application.json')
    result['unused_state_service_candidate']=read(HERE/'forecast3300/candidate_application.json')
    assert result['service_candidate']['after_veh_h']==result['unused_state_service_candidate']['after_veh_h']
    result['source_pins']=a.PINS
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('source_pins','limitations','head_comparisons2400')},indent=2))

if __name__=='__main__':main()
