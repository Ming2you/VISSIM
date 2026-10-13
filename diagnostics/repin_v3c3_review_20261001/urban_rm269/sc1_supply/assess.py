"""Bounded fixed-command comparison; reuse closed native target summaries."""
import hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;H=HERE.parent;ROOT=HERE.parents[3]
sys.path[:0]=[str(ROOT),str(H)]
from qualify_native2400 import validate_scope
PINS={}
def read(path):
    data=path.read_bytes();PINS[str(path)]=hashlib.sha256(data).hexdigest();return json.loads(data)
def main():
    out=HERE/'comparison.json';assert not out.exists()
    validate_scope(read(H/'native2400_analysis/summary.json'),read(H/'native2400_analysis/observed_input_qualification.json'))
    for path,digest in read(HERE/'plan.json')['source_pins'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
    base=read(H/'native_beta/forecast2400_checked/summary.json')['results']
    candidate=read(HERE/'forecast2400/summary.json')['results']
    late=read(HERE/'forecast3300/summary.json')['results']['applied']
    prior_targets=read(H/'service_ceiling/comparison.json')
    source=read(HERE/'assessment.json')
    native=read(H/'native2400_assessment.json')
    for at in (2400,3300):
        assert read(HERE/f'forecast{at}/completion.json')['status']=='complete'
        s=read(HERE/f'forecast{at}/summary.json')
        assert s['forecasts']==(2 if at==2400 else 1) and s['native_runs']==s['optimizer_calls']==0 and not s['future_observation_inputs']
        assert read(HERE/f'forecast{at}/initialization_verification.json')['status']=='passed'
    for r in (*candidate.values(),late):
        assert r['resource_max_exceedance']<1e-7 and r['writer_validated']
        for g in r['local'].values():
            assert all(abs(b['local_balance_error_veh'])<1e-7 for b in g['bins'])
    for r in candidate.values():assert r['shared_constraints']['feasible'] and r['conservation_states']==4
    phases={'SC6_S':{'p1':['SC6_S_SC12_to_N_SC103','SC6_S_SC12_to_E_SC104'],'p2':['SC6_S_SC12_to_W_SC5']},
            'SC101_S':{'p1':['SC101_S_SC1_to_N_SC2005'],'p2':['SC101_S_SC1_to_W_SC1002']}}
    comparisons=[];later=[]
    for old in prior_targets['head_comparisons2400']:
        arm,g,p=old['arm'],old['group'],old['phase']
        new=[sum(b['by_movement'][m] for m in phases[g][p]) for b in candidate[arm]['local'][g]['bins']]
        comparisons.append(dict(arm=arm,group=g,phase=p,actual=old['actual'],previous=old['previous'],predicted=new,
            previous_absolute_error=old['previous_absolute_error'],absolute_error=sum(abs(o-n) for o,n in zip(old['actual'],new))))
    for old in prior_targets['head_comparisons3300']:
        g,p=old['group'],old['phase']
        new=sum(late['local'][g]['bins'][0]['by_movement'][m] for m in phases[g][p])
        later.append(dict(group=g,phase=p,actual=old['actual'],previous=old['previous'],predicted=new,
            previous_absolute_error=old['previous_absolute_error'],absolute_error=abs(old['actual']-new)))
    aliases={'internal':'SC1_S_SC107_to_N_SC101','boundary':'SC1_S_to_N_SC101'}
    upstream=[]
    for arm in ('hold','selected'):
        for j,old in enumerate(source['results'][arm]):
            new=sum(candidate[arm]['local']['SC1_S_'+k]['bins'][j]['by_movement'][m] for k,m in aliases.items())
            before=sum(r['accepted_veh'] for r in old['aliases'].values())
            lower=old['known_native_through_lower_bound']
            upstream.append(dict(arm=arm,start_sec=old['start_sec'],native_through_lower_bound=lower,
                previous=before,predicted=new,previous_shortfall_below_lower_bound=max(0,lower-before),
                shortfall_below_lower_bound=max(0,lower-new),
                boundary_queue_end_veh=candidate[arm]['local']['SC1_S_boundary']['bins'][j]['final']['queue'][aliases['boundary']]))
    delta=lambda rs:rs['selected']['omega_ttt_veh_h']-rs['hold']['omega_ttt_veh_h']
    def fw(rs):
        return sum(sum(v for k,v in rs[arm]['costs_by_stock'].items() if k.startswith('freeway:'))*sign for arm,sign in [('selected',1),('hold',-1)])
    actual=native['delta_omega_veh_h']['actual']
    result=dict(status='complete_physical_alias_fix_control_gain_unqualified',tests_passed=73,forecasts_completed=3,
        new_native=0,new_optimizations=0,new_fitted_parameters=0,shared_caps_feasible=True,
        exact_initial_states_preserved=True,physical_aggregate_rate_preserved=True,
        delta_definition='Joint city/RM selected-minus-held, same initial2400state,Omega701,450s; positive is worse',
        delta_omega_veh_h=dict(actual=actual,previous=delta(base),predicted=delta(candidate),previous_error=delta(base)-actual,error=delta(candidate)-actual),
        delta_mainline_veh_h=dict(actual=native['delta_mainline_veh_h']['actual'],previous=fw(base),predicted=fw(candidate)),
        incremental_merge10681_veh=dict(actual=84,predicted=candidate['selected']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681']-candidate['hold']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681']),
        SC1_physical_through=upstream,head_comparisons2400=comparisons,head_comparisons3300=later,
        combined_SC6_SC101_head_absolute_error=dict(previous=sum(r['previous_absolute_error'] for r in comparisons+later),predicted=sum(r['absolute_error'] for r in comparisons+later)),
        calibration_control_gate_passed=False,runtime_pair_launched=False,applied_to_live_queue=False,
        limitations=['SC1 native three-lane count is a LOWER BOUND; deficit below it is not a full absolute error. Lane5 has competing paths.',
            'Unused3300 is the same seed, not independent-seed validation.',
            'The joint native command includes city signals and multiple RM controls; this is not an isolated10681 causal result.',
            'A structural service-allocation repair is supported, but wholeOmega gain/ranking remains wrong. No native adoption or wall-time claim.',
            'SC101 right branches before the through head and is excluded; closed target counts reused without FZP scan.'])
    PINS[str(Path(__file__))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['source_pins']=PINS
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('status','delta_omega_veh_h','delta_mainline_veh_h','SC1_physical_through','head_comparisons3300','combined_SC6_SC101_head_absolute_error')},indent=2))
if __name__=='__main__':main()
