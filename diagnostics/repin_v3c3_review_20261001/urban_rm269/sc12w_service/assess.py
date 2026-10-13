"""Assess three predeclared fixed forecasts using already qualified native targets."""
import hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;H=HERE.parent
sys.path.insert(0,str(H))
from qualify_native2400 import validate_scope
PINS={}
def read(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return json.loads(b)
def main():
    out=HERE/'comparison.json';assert not out.exists()
    validate_scope(read(H/'native2400_analysis/summary.json'),read(H/'native2400_analysis/observed_input_qualification.json'))
    for p,d in read(HERE/'plan.json')['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==d,p
    baseline=read(H/'sc1_supply/forecast2400/summary.json')['results']
    previous=read(H/'sc1_supply/comparison.json')
    proof=read(H/'sc6_transport/route_qualification.json')['arms']
    candidate=read(HERE/'forecast2400_checked/summary.json')['results']
    late=read(HERE/'forecast3300/summary.json')['results']['applied']
    native=read(H/'native2400_assessment.json')
    for directory,depth,count in [('forecast2400_checked',3,2),('forecast3300',1,1)]:
        assert read(HERE/directory/'completion.json')['status']=='complete'
        s=read(HERE/directory/'summary.json')
        assert s['depth']==depth and s['forecasts']==count and s['native_runs']==s['optimizer_calls']==0 and not s['future_observation_inputs']
        assert read(HERE/directory/'initialization_verification.json')['status']=='passed'
        for r in s['results'].values():
            assert r['conservation_states']==depth+1 and r['writer_validated'] and r['resource_max_exceedance']<1e-7
            assert all(abs(b['local_balance_error_veh'])<1e-7 for g in r['local'].values() for b in g['bins'])
            if depth==3:assert r['shared_constraints']['feasible']
    phases={'SC6_S':{'p1':['SC6_S_SC12_to_N_SC103','SC6_S_SC12_to_E_SC104'],'p2':['SC6_S_SC12_to_W_SC5']},
            'SC101_S':{'p1':['SC101_S_SC1_to_N_SC2005'],'p2':['SC101_S_SC1_to_W_SC1002']}}
    heads=[];later=[]
    for old in previous['head_comparisons2400']:
        g,p=old['group'],old['phase'];new=[sum(b['by_movement'][m] for m in phases[g][p]) for b in candidate[old['arm']]['local'][g]['bins']]
        heads.append(dict(arm=old['arm'],group=g,phase=p,actual=old['actual'],previous=old['predicted'],predicted=new,
            previous_absolute_error=old['absolute_error'],absolute_error=sum(abs(a-b) for a,b in zip(old['actual'],new))))
    for old in previous['head_comparisons3300']:
        g,p=old['group'],old['phase'];new=sum(late['local'][g]['bins'][0]['by_movement'][m] for m in phases[g][p])
        later.append(dict(group=g,phase=p,actual=old['actual'],previous=old['predicted'],predicted=new,
            previous_absolute_error=old['absolute_error'],absolute_error=abs(old['actual']-new)))
    direct=[]
    for arm in ('hold','selected'):
        predicted=sum(b['by_movement'][m] for k,m in [('internal','SC12_W_SC11_to_N_SC6'),('boundary','SC12_W_to_N_SC6')]
            for b in candidate[arm]['local']['SC12_W_'+k]['bins'])
        known=proof[arm]['observed_chosen_direct_turn_lower_bound'];old=proof[arm]['model_direct_turn_departures']
        direct.append(dict(arm=arm,known_chosen_route_lower_bound=known,previous=old,predicted=predicted,
            previous_deficit_below_lower_bound=max(0,known-old),deficit_below_lower_bound=max(0,known-predicted),
            not_a_full_direct_turn_count=True))
    delta=lambda r:r['selected']['omega_ttt_veh_h']-r['hold']['omega_ttt_veh_h']
    fw=lambda r:sum(sign*sum(v for k,v in r[a]['costs_by_stock'].items() if k.startswith('freeway:')) for a,sign in [('selected',1),('hold',-1)])
    actual=native['delta_omega_veh_h']['actual']
    old_error=abs(delta(baseline)-actual);new_error=abs(delta(candidate)-actual)
    local_gain=sum(r['previous_absolute_error']-r['absolute_error'] for r in heads)
    late_gain=sum(r['previous_absolute_error']-r['absolute_error'] for r in later)
    retain=local_gain>0 and late_gain>=-1e-7 and new_error<old_error
    result=dict(status='complete_bounded_candidate',forecasts_completed=3,tests_passed=9,new_native=0,new_optimizations=0,
        new_rate_estimates=1,rate_veh_h=960,exact_initial_state_preserved=True,shared_caps_feasible=True,
        delta_definition='Joint city/RM selected-minus-held; same initial2400state, Omega701,450s; positive is worse',
        delta_omega_veh_h=dict(actual=actual,previous=delta(baseline),predicted=delta(candidate),previous_error=delta(baseline)-actual,error=delta(candidate)-actual),
        delta_mainline_veh_h=dict(actual=native['delta_mainline_veh_h']['actual'],previous=fw(baseline),predicted=fw(candidate)),
        incremental_merge10681_veh=dict(actual=84,predicted=candidate['selected']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681']-candidate['hold']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681']),
        direct_SC12W=direct,head_comparisons2400=heads,head_comparisons3300=later,
        head_error_reduction_veh=dict(at2400=local_gain,unused3300=late_gain),
        ad_retention_gate=retain,calibration_control_gate_passed=False,applied_to_live_queue=False,runtime_pair_launched=False,
        limitations=['Past typed counts support achieved lower rates, not universal saturation; this is one diagnostic candidate.',
            'Future direct-turn evidence is a chosen-route subset lower bound, not a full10242 count.',
            '3300 is an unused same-seed state, not independent seed validation.',
            'Selected changes city signals and multiple RM controls; not an isolated10681 causal effect.',
            'No production/native adoption or full SDMPC wall-time claim.'])
    PINS[str(Path(__file__))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();result['source_pins']=PINS
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('delta_omega_veh_h','delta_mainline_veh_h','direct_SC12W','head_error_reduction_veh','ad_retention_gate')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
